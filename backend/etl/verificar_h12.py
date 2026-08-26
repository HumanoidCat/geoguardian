"""
Verificador de los focos de calor. Dueno: Cesar. Historia H1.2, issue #36.

Cada criterio se comprueba ejecutando. Los que hablan de la tabla consultan la
tabla; los que hablan del extractor lo instancian.

EL CRITERIO QUE IMPORTA MAS

CA-8 reproduce la medicion que cerro el riesgo R16: **242 focos dentro del canton
y el reparto por distrito**. Si ese numero cambia sin que nadie toque el codigo, o
la fuente reproceso su archivo o el filtro espacial dejo de hacer lo que hacia. Las
dos cosas hay que saberlas.

USO

    python -m backend.etl.verificar_h12
    python -m backend.etl.verificar_h12 --registro evidencia-h12-verificacion.txt
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date

from basedatos.conexion import ErrorConexion, conectar
from contratos.esquemas import FocoCalor
from contratos.fuentes import ExtractorFocosCalor

from . import bitacora
from .cargar_focos import CODIGO_CANTON, DESDE, HASTA, caja_del_canton
from .fuentes.firms import (
    CORTE_ALTA,
    CORTE_BAJA,
    ULTIMO_ANIO_ARCHIVO,
    ErrorFirms,
    ExtractorFirms,
    categoria_confianza,
)

# La medicion de R16, del 20 de agosto de 2026. Ver
# docs/evidencias/bases-de-datos/H1.2-focos-calor.md
FOCOS_ESPERADOS = 242
REPARTO_ESPERADO = {
    "50801": 15,
    "50802": 7,
    "50803": 5,
    "50804": 83,
    "50805": 65,
    "50806": 65,
    "50807": 1,
    "50808": 1,
}


@dataclass
class Resultado:
    criterio: str
    titulo: str
    cumple: bool
    detalle: list[str] = field(default_factory=list)


class _FuenteCaida:
    """Cliente que siempre falla, para CA-3 sin tocar la red."""

    def head(self, *_a, **_k):
        import httpx

        raise httpx.ConnectError("caida a proposito")

    def get(self, *_a, **_k):
        import httpx

        raise httpx.ConnectError("caida a proposito")

    def close(self) -> None:
        pass


CAJA_PRUEBA = (-85.0468, 10.32079, -84.76609, 10.65175)


# --------------------------------------------------------------------------- #
# Sin base y sin red                                                            #
# --------------------------------------------------------------------------- #


def ca1_protocolo() -> Resultado:
    import inspect

    extractor = ExtractorFirms(CAJA_PRUEBA)
    cumple = isinstance(extractor, ExtractorFocosCalor)
    firma = list(inspect.signature(extractor.extraer).parameters)
    esperados = ["desde", "hasta"]
    extractor.cerrar()

    return Resultado(
        "CA-1",
        "El extractor cumple el protocolo ExtractorFocosCalor",
        cumple and firma == esperados,
        [
            f"  isinstance(extractor, ExtractorFocosCalor): {cumple}",
            f"  parametros de extraer: {firma} (esperado {esperados})",
        ],
    )


def ca2_cortes_confianza() -> Resultado:
    """
    Los cortes de MODIS a categoria son los del manual, no los del equipo.

    Tabla 10 de Giglio, Schroeder, Hall y Justice, MODIS Collection 6 Active Fire
    Product User's Guide, Revision C, diciembre de 2020.
    """
    casos = [
        ("modis", "0", "baja"),
        ("modis", str(CORTE_BAJA - 1), "baja"),
        ("modis", str(CORTE_BAJA), "nominal"),
        ("modis", str(CORTE_ALTA - 1), "nominal"),
        ("modis", str(CORTE_ALTA), "alta"),
        ("modis", "100", "alta"),
        ("viirs-snpp", "l", "baja"),
        ("viirs-snpp", "n", "nominal"),
        ("viirs-snpp", "h", "alta"),
    ]
    detalle, ok = [], True
    for producto, crudo, esperado in casos:
        obtenido, bruta = categoria_confianza(producto, crudo)
        bien = obtenido == esperado
        detalle.append(
            f"  {producto:<11} {crudo!r:>5} -> {obtenido:<8} bruta={bruta} "
            f"... {'ok' if bien else 'MAL'}"
        )
        ok = ok and bien

    # Una letra que VIIRS no declara tiene que detener la carga, no adivinar.
    try:
        categoria_confianza("viirs-snpp", "x")
        detalle.append("  letra desconocida en VIIRS: NO se detuvo, MAL")
        ok = False
    except ErrorFirms:
        detalle.append("  letra desconocida en VIIRS: se detiene ... ok")

    return Resultado("CA-2", "Los cortes de confianza son los del manual del producto", ok, detalle)


def ca3_disponible() -> Resultado:
    """Con la fuente caida devuelve falso, no lanza excepcion."""
    caido = ExtractorFirms(CAJA_PRUEBA, cliente=_FuenteCaida())
    try:
        obtenido = caido.disponible()
    except Exception as error:  # noqa: BLE001 - el criterio es que NO lance
        return Resultado(
            "CA-3", "disponible() no lanza", False, [f"  lanzo {type(error).__name__}"]
        )

    return Resultado(
        "CA-3",
        "disponible() devuelve falso ante una fuente caida, sin lanzar",
        obtenido is False,
        [f"  con la fuente caida devuelve {obtenido}, esperado False"],
    )


def ca4_caja_y_traduccion() -> Resultado:
    """
    El extractor filtra por caja y no hace analisis espacial.

    Y la traduccion al contrato pierde la confianza de VIIRS a proposito, porque
    el esquema la declara entera y VIIRS no da un entero. Se comprueba para que
    quede escrito que es una perdida conocida y no un descuido.
    """
    from .fuentes.firms import FocoBruto

    extractor = ExtractorFirms(CAJA_PRUEBA)
    dentro = extractor._dentro(-84.95, 10.47)
    fuera = extractor._dentro(-83.0, 9.9)
    extractor.cerrar()

    viirs = FocoBruto(
        producto="viirs-snpp",
        satelite="N",
        fecha=date(2020, 4, 1),
        hora_utc=1830,
        latitud=10.47,
        longitud=-84.95,
        confianza="nominal",
        confianza_bruta=None,
        brillo_k=330.0,
        brillo_largo_k=295.0,
        banda_origen="viirs_i4",
        frp_mw=5.0,
        tipo=0,
        dia_noche="D",
    )
    traducido = viirs.a_foco_calor()
    es_contrato = isinstance(traducido, FocoCalor)

    return Resultado(
        "CA-4",
        "Filtra por caja, no asigna distrito, y la traduccion al contrato es la declarada",
        dentro and not fuera and es_contrato and traducido.codigo_distrito is None,
        [
            f"  punto dentro de la caja: {dentro}",
            f"  punto fuera de la caja: {fuera} (esperado False)",
            f"  la traduccion es un FocoCalor del contrato: {es_contrato}",
            f"  codigo_distrito que devuelve el extractor: {traducido.codigo_distrito!r}"
            " (el contrato dice que lo asigna el repositorio)",
            f"  confianza de un foco VIIRS en el contrato: {traducido.confianza!r}"
            " (nula a proposito: el esquema la pide entera)",
        ],
    )


def ca5_tope_del_archivo() -> Resultado:
    """Pedir mas alla de 2024 se detiene con el motivo, no devuelve menos en silencio."""
    extractor = ExtractorFirms(CAJA_PRUEBA)
    try:
        extractor.descargar(date(2001, 1, 1), date(ULTIMO_ANIO_ARCHIVO + 1, 1, 1))
        detalle, ok = ["  NO se detuvo, MAL"], False
    except ErrorFirms as error:
        detalle, ok = [f"  se detiene: {str(error)[:100]}..."], True
    finally:
        extractor.cerrar()

    return Resultado(
        "CA-5", f"El archivo llega a {ULTIMO_ANIO_ARCHIVO} y pedir mas se detiene", ok, detalle
    )


# --------------------------------------------------------------------------- #
# Contra la tabla                                                               #
# --------------------------------------------------------------------------- #


def ca6_caja_generada(conexion) -> Resultado:
    """La caja sale de PostGIS, no de una constante escrita a mano."""
    caja = caja_del_canton(conexion)
    razonable = -85.5 < caja[0] < caja[2] < -84.5 and 10.0 < caja[1] < caja[3] < 11.0
    return Resultado(
        "CA-6",
        "La caja del canton la calcula ST_Extent",
        razonable,
        [
            f"  oeste {caja[0]:.5f}  sur {caja[1]:.5f}  este {caja[2]:.5f}  norte {caja[3]:.5f}",
            f"  ancho {caja[2] - caja[0]:.5f} grados, alto {caja[3] - caja[1]:.5f} grados",
        ],
    )


def ca7_integridad(cursor) -> Resultado:
    """Las restricciones del DDL, comprobadas contra los datos que hay."""
    pruebas = {
        "confianza fuera del vocabulario": "confianza NOT IN ('baja','nominal','alta')",
        "confianza bruta en VIIRS": "producto <> 'modis' AND confianza_bruta IS NOT NULL",
        "categoria incoherente con el entero": (
            "confianza_bruta IS NOT NULL AND NOT ("
            f"(confianza='baja' AND confianza_bruta < {CORTE_BAJA}) OR "
            f"(confianza='nominal' AND confianza_bruta >= {CORTE_BAJA} "
            f"AND confianza_bruta < {CORTE_ALTA}) OR "
            f"(confianza='alta' AND confianza_bruta >= {CORTE_ALTA}))"
        ),
        "banda de origen desconocida": "banda_origen NOT IN ('modis_21_22','viirs_i4')",
        "brillo no positivo": "brillo_k IS NOT NULL AND brillo_k <= 0",
        "potencia negativa": "frp_mw IS NOT NULL AND frp_mw < 0",
        "fecha fuera de la ventana": f"fecha < DATE '{DESDE}' OR fecha > DATE '{HASTA}'",
    }
    detalle, ok = [], True
    for titulo, condicion in pruebas.items():
        cursor.execute(f"SELECT count(*) FROM crudo.foco_calor WHERE {condicion}")
        (cuenta,) = cursor.fetchone()
        detalle.append(f"  {titulo}: {cuenta} filas ... {'ok' if cuenta == 0 else 'MAL'}")
        ok = ok and cuenta == 0
    return Resultado("CA-7", "Los datos respetan lo que el DDL declara", ok, detalle)


def ca8_reproduce_r16(cursor) -> Resultado:
    """
    El conteo que cerro R16 se reproduce.

    Es el criterio central: si este numero cambia sin que nadie toque el codigo,
    o FIRMS reproceso su archivo o el filtro espacial dejo de funcionar.
    """
    cursor.execute(
        """
        SELECT d.codigo, d.nombre, count(f.*)
          FROM geo.distrito d
          LEFT JOIN crudo.foco_calor f ON f.codigo_distrito = d.codigo
         WHERE d.codigo_canton = %s
         GROUP BY d.codigo, d.nombre
         ORDER BY d.codigo
        """,
        (CODIGO_CANTON,),
    )
    filas = cursor.fetchall()
    obtenido = {codigo: cuenta for codigo, _, cuenta in filas}
    total = sum(obtenido.values())

    detalle = [f"  total dentro del canton: {total} (esperado {FOCOS_ESPERADOS})"]
    ok = total == FOCOS_ESPERADOS
    for codigo, nombre, cuenta in filas:
        esperado = REPARTO_ESPERADO.get(codigo)
        bien = cuenta == esperado
        detalle.append(
            f"  {codigo} {nombre:<18} {cuenta:>4}  esperado {esperado:>4} ... "
            f"{'ok' if bien else 'MAL'}"
        )
        ok = ok and bien

    if not ok:
        detalle.append(
            "  Si el codigo no cambio, comprobar si FIRMS reproceso el archivo "
            "historico antes de tocar nada."
        )
    return Resultado("CA-8", "Se reproduce la medicion de R16", ok, detalle)


def ca9_tipos_y_productos(cursor) -> Resultado:
    """Los dos productos estan, y los focos son de vegetacion y no del volcan."""
    cursor.execute("SELECT producto, count(*) FROM crudo.foco_calor GROUP BY producto ORDER BY 1")
    productos = dict(cursor.fetchall())
    cursor.execute(
        "SELECT tipo, count(*) FROM crudo.foco_calor WHERE codigo_distrito IS NOT NULL"
        " GROUP BY tipo ORDER BY 1"
    )
    tipos = dict(cursor.fetchall())

    hay_dos = len(productos) == 2
    solo_vegetacion = set(tipos) <= {0}
    return Resultado(
        "CA-9",
        "Los dos productos entran y los focos del canton son de vegetacion",
        hay_dos and solo_vegetacion,
        [
            f"  por producto: {productos}",
            f"  tipos dentro del canton: {tipos} (0 = vegetacion, 1 = volcan)",
            "  el volcan Arenal no contamina la serie" if solo_vegetacion else "  HAY TIPOS NO 0",
        ],
    )


def ca10_fuera_del_canton(cursor) -> Resultado:
    """
    Los focos de la caja que caen fuera del canton se guardan con distrito nulo.

    El contrato lo admite explicitamente. Guardarlos deja ver el borde entre el
    rectangulo y el poligono en vez de esconderlo.
    """
    cursor.execute(
        """
        SELECT count(*) FILTER (WHERE codigo_distrito IS NOT NULL),
               count(*) FILTER (WHERE codigo_distrito IS NULL),
               count(*)
          FROM crudo.foco_calor
        """
    )
    dentro, fuera, total = cursor.fetchone()
    return Resultado(
        "CA-10",
        "Un foco fuera de los ocho distritos se guarda con distrito nulo",
        total == dentro + fuera and fuera > 0,
        [
            f"  en la caja: {total}",
            f"  con distrito: {dentro}",
            f"  fuera del canton: {fuera}",
            "  la caja es un rectangulo y el canton no: la diferencia es el borde",
        ],
    )


def ca11_idempotencia(cursor) -> Resultado:
    """La clave natural es la que sostiene el ON CONFLICT."""
    cursor.execute(
        """
        SELECT a.attname
          FROM pg_constraint c
          JOIN pg_class t ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
          JOIN unnest(c.conkey) WITH ORDINALITY AS k(attnum, orden) ON true
          JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum
         WHERE n.nspname = 'crudo' AND t.relname = 'foco_calor' AND c.contype = 'p'
         ORDER BY k.orden
        """
    )
    clave = [f[0] for f in cursor.fetchall()]
    esperada = ["producto", "satelite", "fecha", "hora_utc", "latitud", "longitud"]
    return Resultado(
        "CA-11",
        "La clave natural sostiene la idempotencia",
        clave == esperada,
        [f"  clave primaria: {clave}", f"  esperada:        {esperada}"],
    )


def ca12_una_transaccion(cursor) -> Resultado:
    """
    Toda la carga entra en una transaccion, y aqui eso es lo correcto.

    `now()` en PostgreSQL devuelve la hora de inicio de la transaccion, asi que un
    unico valor de `descargado_en` demuestra que fue una sola. En H1.1 el mismo
    indicio delato lo contrario: alli se documentaba una transaccion por distrito
    y habia una para todo.
    """
    cursor.execute("SELECT count(DISTINCT descargado_en), count(*) FROM crudo.foco_calor")
    distintos, total = cursor.fetchone()
    return Resultado(
        "CA-12",
        "La carga ocurre en una sola transaccion, que es la unidad correcta aqui",
        distintos == 1 and total > 0,
        [
            f"  valores distintos de descargado_en: {distintos} (esperado 1)",
            f"  filas: {total}",
        ],
    )


def ca13_procedencia() -> Resultado:
    from .cargar_focos import RUTA_PROCEDENCIA

    existe = RUTA_PROCEDENCIA.exists()
    detalle = [f"  {RUTA_PROCEDENCIA}: {'existe' if existe else 'no existe'}"]
    if existe:
        texto = RUTA_PROCEDENCIA.read_text(encoding="utf-8")
        for exigido in ("Fuente:", "Ventana:", "Caja:", "Focos en la caja"):
            presente = exigido in texto
            detalle.append(f"  contiene {exigido!r}: {presente}")
            existe = existe and presente
    else:
        detalle.append("  se genera al correr cargar_focos")
    return Resultado("CA-13", "Queda registrado de donde salieron los focos", existe, detalle)


# --------------------------------------------------------------------------- #


def main(argumentos: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description="Verifica los criterios de H1.2")
    analizador.add_argument(
        "--registro", help="Archivo donde guardar la salida completa, para la evidencia"
    )
    opciones = analizador.parse_args(argumentos)

    with bitacora.abrir(opciones.registro) as registrar:
        return _verificar(registrar)


def _verificar(registrar) -> int:
    registrar("Verificacion de los focos de calor de H1.2 (issue #36)")
    registrar("=" * 74)
    registrar(f"Ventana: {DESDE} a {HASTA}")
    registrar(f"Focos esperados dentro del canton: {FOCOS_ESPERADOS}")

    resultados = [
        ca1_protocolo(),
        ca2_cortes_confianza(),
        ca3_disponible(),
        ca4_caja_y_traduccion(),
        ca5_tope_del_archivo(),
    ]

    try:
        with conectar(autocommit=True) as conexion, conexion.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM crudo.foco_calor")
            (cargados,) = cursor.fetchone()
            registrar(f"Filas en la tabla: {cargados}")

            resultados.append(ca6_caja_generada(conexion))
            resultados.append(ca11_idempotencia(cursor))
            if cargados:
                resultados.append(ca7_integridad(cursor))
                resultados.append(ca8_reproduce_r16(cursor))
                resultados.append(ca9_tipos_y_productos(cursor))
                resultados.append(ca10_fuera_del_canton(cursor))
                resultados.append(ca12_una_transaccion(cursor))
            else:
                registrar(
                    "\nAVISO: crudo.foco_calor esta vacia. CA-7 a CA-10 y CA-12 no se "
                    "pueden comprobar sin datos cargados."
                )
    except ErrorConexion as error:
        registrar(f"ERROR: {error}")
        return 1

    resultados.append(ca13_procedencia())

    for r in resultados:
        registrar(f"\n{r.criterio} · {r.titulo} ... {'CUMPLE' if r.cumple else 'NO CUMPLE'}")
        for linea in r.detalle:
            registrar(linea)

    fallidos = [r for r in resultados if not r.cumple]
    registrar("\n" + "=" * 74)
    if fallidos:
        registrar("NO CUMPLEN: " + ", ".join(r.criterio for r in fallidos))
        return 1
    registrar("Los criterios verificados aqui se cumplen.")
    registrar("Falta CA-14, que se verifica por fuera: levantar sobre volumen vacio.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
