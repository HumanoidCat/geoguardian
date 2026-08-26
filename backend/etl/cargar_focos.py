"""
Carga de focos de calor. Dueno: Cesar. Historia H1.2, issue #36.

QUE HACE

Baja el historico de FIRMS de 2001 a 2024, se queda con lo que cae en la caja
envolvente del canton, y lo escribe en `crudo.foco_calor` asignandole a cada
deteccion su distrito.

DONDE OCURRE EL ANALISIS ESPACIAL, Y POR QUE AQUI

El contrato `ExtractorFocosCalor` dice que el extractor **no** hace analisis
espacial: solo trae lo que cae en el area de estudio, y el filtrado por distrito
ocurre despues, en la capa que conoce las geometrias.

Esa capa es esta. La asignacion se hace con `ST_Contains` dentro del INSERT, no en
Python: PostGIS ya tiene los poligonos y sabe hacerlo, y traerlos a Python para
repetir el calculo seria mover megabytes para llegar al mismo sitio.

LA CAJA NO SE ESCRIBE A MANO

Sale de `ST_Extent` sobre los ocho distritos. Si el IGN corrige un limite, la caja
se ajusta sola. Escribirla como constante seria un numero que envejece en silencio.

QUE SE GUARDA Y QUE NO

Se guardan **todos** los focos de la caja, no solo los de dentro del canton. Los que
caen fuera quedan con `codigo_distrito` nulo, que el contrato admite
explicitamente. Son el efecto de que la caja es un rectangulo y el canton no:
guardarlos permite ver ese borde y comprobar que el conteo de dentro es el que
se midio.

UNA SOLA TRANSACCION, Y AQUI SI ES CIERTO

Son unos cientos de filas y la escritura no espera por la red: la descarga ya
termino cuando empieza. Una transaccion para todo es la unidad correcta.

La conexion se abre con `autocommit=True` **a proposito**. Con la conexion en modo
transaccion, cualquier consulta previa abre una transaccion implicita y el
`conexion.transaction()` de mas abajo se vuelve un punto de retorno dentro de ella
en vez de una transaccion propia. Eso ya paso en `cargar_mediciones.py`: los ocho
distritos quedaron en una sola transaccion y se detecto porque `descargado_en`
tenia un unico valor para todos. Ver la evidencia de H1.1.

USO

    python -m backend.etl.cargar_focos
    python -m backend.etl.cargar_focos --desde 2012-01-01 --hasta 2024-12-31
    python -m backend.etl.cargar_focos --registro evidencia-h12-carga.txt
    python -m backend.etl.cargar_focos --solo-comprobar   # no toca la base
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from datetime import date, datetime
from pathlib import Path

from basedatos.conexion import ErrorConexion, conectar

from . import bitacora
from .fuentes.firms import ErrorFirms, ExtractorFirms, FocoBruto

# Ventana del archivo historico. Arranca en 2001 y no en 2000 porque MODIS Terra
# empezo a operar a finales de 2000 y el primer anio esta incompleto; el conteo de
# R16 se hizo sobre 2001-2024 y se mantiene para que los numeros sean comparables.
DESDE = date(2001, 1, 1)
HASTA = date(2024, 12, 31)

CODIGO_CANTON = 508

RUTA_PROCEDENCIA = (
    Path(__file__).resolve().parents[2] / "basedatos" / "ddl" / "procedencia-focos.md"
)

SQL_CAJA = """
    SELECT ST_XMin(e), ST_YMin(e), ST_XMax(e), ST_YMax(e)
      FROM (SELECT ST_Extent(geometria) AS e
              FROM geo.distrito
             WHERE codigo_canton = %s) AS caja
"""

# El distrito se resuelve aqui, con la geometria, y no en Python. ST_Contains
# devuelve NULL cuando el punto no cae en ninguno, que es lo que el contrato
# espera para una deteccion fuera de los ocho.
SQL_INSERTAR = """
    INSERT INTO crudo.foco_calor (
        producto, satelite, fecha, hora_utc, latitud, longitud,
        codigo_distrito,
        confianza, confianza_bruta,
        brillo_k, brillo_largo_k, banda_origen,
        frp_mw, tipo, dia_noche,
        descargado_en
    )
    VALUES (
        %(producto)s, %(satelite)s, %(fecha)s, %(hora_utc)s, %(latitud)s, %(longitud)s,
        (SELECT d.codigo
           FROM geo.distrito d
          WHERE d.codigo_canton = %(codigo_canton)s
            AND ST_Contains(d.geometria, ST_SetSRID(ST_MakePoint(%(longitud)s, %(latitud)s), 4326))
          LIMIT 1),
        %(confianza)s, %(confianza_bruta)s,
        %(brillo_k)s, %(brillo_largo_k)s, %(banda_origen)s,
        %(frp_mw)s, %(tipo)s, %(dia_noche)s,
        now()
    )
    ON CONFLICT (producto, satelite, fecha, hora_utc, latitud, longitud) DO UPDATE SET
        codigo_distrito = EXCLUDED.codigo_distrito,
        confianza       = EXCLUDED.confianza,
        confianza_bruta = EXCLUDED.confianza_bruta,
        brillo_k        = EXCLUDED.brillo_k,
        brillo_largo_k  = EXCLUDED.brillo_largo_k,
        banda_origen    = EXCLUDED.banda_origen,
        frp_mw          = EXCLUDED.frp_mw,
        tipo            = EXCLUDED.tipo,
        dia_noche       = EXCLUDED.dia_noche,
        descargado_en   = EXCLUDED.descargado_en
"""


class ErrorCargaFocos(Exception):
    """Falla que impide continuar."""


def caja_del_canton(conexion, codigo_canton: int = CODIGO_CANTON) -> tuple[float, ...]:
    """Caja envolvente de los ocho distritos, calculada por PostGIS."""
    with conexion.cursor() as cursor:
        cursor.execute(SQL_CAJA, (codigo_canton,))
        fila = cursor.fetchone()

    if fila is None or fila[0] is None:
        raise ErrorCargaFocos(
            f"No hay distritos del canton {codigo_canton} en geo.distrito. "
            "H1.2 depende de H1.3: corre primero backend/etl/cargar_distritos.py"
        )
    return tuple(float(v) for v in fila)


def escribir(conexion, focos: list[FocoBruto]) -> int:
    """Escribe todos los focos en una transaccion."""
    parametros = [
        {
            "producto": f.producto,
            "satelite": f.satelite,
            "fecha": f.fecha,
            "hora_utc": f.hora_utc,
            "latitud": f.latitud,
            "longitud": f.longitud,
            "codigo_canton": CODIGO_CANTON,
            "confianza": f.confianza,
            "confianza_bruta": f.confianza_bruta,
            "brillo_k": f.brillo_k,
            "brillo_largo_k": f.brillo_largo_k,
            "banda_origen": f.banda_origen,
            "frp_mw": f.frp_mw,
            "tipo": f.tipo,
            "dia_noche": f.dia_noche,
        }
        for f in focos
    ]

    with conexion.transaction(), conexion.cursor() as cursor:
        cursor.executemany(SQL_INSERTAR, parametros)

    return len(parametros)


def escribir_procedencia(lineas: list[str]) -> None:
    """Deja el rastro de la descarga junto al DDL, como H1.1 y H1.3."""
    RUTA_PROCEDENCIA.parent.mkdir(parents=True, exist_ok=True)
    RUTA_PROCEDENCIA.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def principal(argumentos: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        description="Carga focos de calor de FIRMS en crudo.foco_calor"
    )
    analizador.add_argument("--desde", default=DESDE.isoformat())
    analizador.add_argument("--hasta", default=HASTA.isoformat())
    analizador.add_argument(
        "--solo-comprobar",
        action="store_true",
        help="Comprueba que la fuente responde y no escribe nada",
    )
    analizador.add_argument(
        "--registro",
        help="Archivo donde guardar la salida completa, para la evidencia del PR",
    )
    opciones = analizador.parse_args(argumentos)

    desde = datetime.strptime(opciones.desde, "%Y-%m-%d").date()
    hasta = datetime.strptime(opciones.hasta, "%Y-%m-%d").date()
    if hasta < desde:
        print("El rango termina antes de empezar", file=sys.stderr)
        return 2

    with bitacora.abrir(opciones.registro) as registrar:
        return _cargar(opciones, desde, hasta, registrar)


def _cargar(opciones, desde: date, hasta: date, registrar) -> int:
    """Hace el trabajo. Separado de `principal` para que la bitacora lo envuelva."""
    arranque = time.monotonic()
    extractor = None

    try:
        # autocommit=True: ver el encabezado del modulo. Sin esto, la consulta de
        # la caja abre una transaccion implicita y la de mas abajo deja de ser
        # una transaccion propia.
        with conectar(autocommit=True) as conexion:
            caja = caja_del_canton(conexion)
            extractor = ExtractorFirms(caja)

            registrar(f"Fuente: {extractor.nombre}")
            registrar(f"Ventana: {desde} a {hasta}")
            registrar(
                "Caja del canton, calculada con ST_Extent: "
                f"oeste {caja[0]:.5f}  sur {caja[1]:.5f}  este {caja[2]:.5f}  norte {caja[3]:.5f}"
            )
            registrar(f"Inicio: {datetime.now().astimezone().isoformat(timespec='seconds')}")

            if not extractor.disponible():
                registrar("El archivo historico de FIRMS no responde. No se carga nada.")
                return 1
            registrar("La fuente responde.")

            if opciones.solo_comprobar:
                return 0

            registrar("\n--- descarga ---")
            focos = extractor.descargar(desde, hasta, registrar=registrar)
            registrar(f"\nfocos dentro de la caja: {len(focos)}")

            filas = escribir(conexion, focos)
            duracion = time.monotonic() - arranque

            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT count(*) FILTER (WHERE codigo_distrito IS NOT NULL),
                           count(*) FILTER (WHERE codigo_distrito IS NULL),
                           count(*)
                      FROM crudo.foco_calor
                    """
                )
                dentro, fuera, total = cursor.fetchone()

                cursor.execute(
                    """
                    SELECT d.codigo, d.nombre, count(f.*)
                      FROM geo.distrito d
                      LEFT JOIN crudo.foco_calor f ON f.codigo_distrito = d.codigo
                     WHERE d.codigo_canton = %s
                     GROUP BY d.codigo, d.nombre
                     ORDER BY count(f.*) DESC
                    """,
                    (CODIGO_CANTON,),
                )
                por_distrito = cursor.fetchall()

            registrar(f"escritas {filas} filas en {duracion:.1f} s")
            registrar(f"\nen la tabla: {total}  con distrito: {dentro}  fuera del canton: {fuera}")
            registrar("\npor distrito:")
            for codigo, nombre, cuenta in por_distrito:
                registrar(f"  {codigo} {nombre:<18} {cuenta}")

            lineas = [
                "# Procedencia de los focos de calor",
                "",
                "Generado por `backend/etl/cargar_focos.py`. No editar a mano.",
                "",
                f"- Fuente: {extractor.nombre}",
                "- Archivo historico por pais, sin autenticacion",
                f"- Ventana: {desde} a {hasta}",
                f"- Momento: {datetime.now().astimezone().isoformat(timespec='seconds')}",
                f"- Caja: {caja[0]:.5f}, {caja[1]:.5f}, {caja[2]:.5f}, {caja[3]:.5f}",
                "",
                f"Focos en la caja: {total}. Dentro del canton: {dentro}. Fuera: {fuera}.",
                "",
                "| Distrito | Nombre | Focos |",
                "|---|---|---|",
                *(f"| {c} | {n} | {v} |" for c, n, v in por_distrito),
                "",
                "Los focos fuera del canton se guardan con `codigo_distrito` nulo. La caja",
                "es un rectangulo y el canton no, asi que la diferencia es el borde.",
                "",
                "Cortes de confianza: Tabla 10 de Giglio, Schroeder, Hall y Justice,",
                "MODIS Collection 6 Active Fire Product User's Guide, Revision C,",
                "University of Maryland, diciembre de 2020.",
            ]
            escribir_procedencia(lineas)
            registrar(f"\nProcedencia: {RUTA_PROCEDENCIA}")
            return 0

    except (ErrorConexion, ErrorFirms, ErrorCargaFocos) as error:
        registrar(f"\nFALLO: {error}")
        return 1
    except Exception:
        registrar("\nFALLO INESPERADO:\n" + traceback.format_exc())
        raise
    finally:
        if extractor is not None:
            extractor.cerrar()


if __name__ == "__main__":
    raise SystemExit(principal())
