"""
Carga de series climaticas diarias. Dueno: Cesar. Historia H1.1, issue #35.

QUE HACE

Descarga la ventana 1991-2025 para los ocho distritos de Tilaran y la escribe en
`crudo.medicion_diaria`. La precipitacion viene de CHIRPS y el resto de POWER,
por la decision D-15.

REEJECUTABLE E IDEMPOTENTE

Es lo que pide el titulo de la historia, y son dos cosas distintas:

  - **Reejecutable**: se puede volver a correr sin limpiar nada antes. La carga
    va por distrito, cada uno en su propia transaccion, asi que si el quinto
    falla los cuatro anteriores quedan escritos y solo hay que repetir desde ahi.
  - **Idempotente**: correrla dos veces deja la tabla igual que correrla una.
    Lo garantiza `ON CONFLICT (codigo_distrito, fecha) DO UPDATE`: la clave
    natural es la del contrato, y una segunda pasada actualiza en vez de
    duplicar. El verificador lo comprueba contando filas antes y despues.

POR QUE UNA TRANSACCION POR DISTRITO Y NO UNA SOLA PARA TODO

En H1.3 la carga entera cabe en una transaccion: son nueve geometrias y tarda
segundos. Aqui son ocho distritos x 12.784 dias y las descargas de CHIRPS se
encolan del lado del servidor. Una sola transaccion tendria que mantenerse
abierta durante toda la descarga, bloqueando la tabla mientras el proceso espera
por la red. La unidad correcta es el distrito: o entran sus 12.784 dias, o no
entra ninguno.

LOS HUECOS SE CONSERVAN

Un dia sin dato entra con sus columnas en NULL. No se omite la fila ni se pone
cero: cero milimetros es un dia sin lluvia y NULL es un dia sin medicion, y
confundirlos arruina el calculo del SPI. Imputar es H1.4.

USO

    python -m backend.etl.cargar_mediciones
    python -m backend.etl.cargar_mediciones --desde 2024-01-01 --hasta 2024-01-31
    python -m backend.etl.cargar_mediciones --distrito 50801
    python -m backend.etl.cargar_mediciones --solo-comprobar   # no toca la base
    python -m backend.etl.cargar_mediciones --registro evidencia-h11-carga.txt

`--registro` guarda la salida completa en un archivo, ademas de mostrarla. Lo
escribe el guion y no la terminal porque capturarla desde PowerShell fallo dos
veces: `Start-Transcript` no registra comandos nativos en la version 5.1, y una
tuberia con `Tee-Object` dejo un archivo sin una sola linea de Python.
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from datetime import date, datetime
from pathlib import Path

from basedatos.conexion import ErrorConexion, conectar
from contratos.esquemas import MedicionDiaria

from . import bitacora
from .fuentes.chirps import ErrorChirps, ExtractorChirps
from .fuentes.hibrido import ExtractorHibrido, territorios_desde_base
from .fuentes.power import ErrorPower, ExtractorPower

# Ventana de la historia. El inicio es 1991 porque es el primer anio que cubren
# las dos fuentes: CHIRPS arranca en 1981 y POWER en 1981, pero el charter pide
# 35 anios completos hasta el cierre de 2025.
DESDE = date(1991, 1, 1)
HASTA = date(2025, 12, 31)

CODIGO_CANTON = 508

RUTA_PROCEDENCIA = (
    Path(__file__).resolve().parents[2] / "basedatos" / "ddl" / "procedencia-mediciones.md"
)

SQL_INSERTAR = """
    INSERT INTO crudo.medicion_diaria (
        codigo_distrito, fecha,
        temp_max_c, temp_min_c, temp_media_c,
        humedad_relativa_pct, viento_ms, radiacion_mj_m2,
        precipitacion_mm,
        fuente_precipitacion, fuente_resto,
        descargado_en
    )
    VALUES (
        %(codigo_distrito)s, %(fecha)s,
        %(temp_max_c)s, %(temp_min_c)s, %(temp_media_c)s,
        %(humedad_relativa_pct)s, %(viento_ms)s, %(radiacion_mj_m2)s,
        %(precipitacion_mm)s,
        'chirps', 'power',
        now()
    )
    ON CONFLICT (codigo_distrito, fecha) DO UPDATE SET
        temp_max_c           = EXCLUDED.temp_max_c,
        temp_min_c           = EXCLUDED.temp_min_c,
        temp_media_c         = EXCLUDED.temp_media_c,
        humedad_relativa_pct = EXCLUDED.humedad_relativa_pct,
        viento_ms            = EXCLUDED.viento_ms,
        radiacion_mj_m2      = EXCLUDED.radiacion_mj_m2,
        precipitacion_mm     = EXCLUDED.precipitacion_mm,
        fuente_precipitacion = EXCLUDED.fuente_precipitacion,
        fuente_resto         = EXCLUDED.fuente_resto,
        descargado_en        = EXCLUDED.descargado_en
"""


class ErrorCargaMediciones(Exception):
    """Falla que impide continuar."""


def escribir(conexion, mediciones: list[MedicionDiaria], fallar: bool = False) -> int:
    """
    Escribe las mediciones de un distrito en una transaccion.

    `executemany` con la sentencia preparada una sola vez: son mas de doce mil
    filas por distrito y mandarlas de a una multiplica los viajes de ida y vuelta
    sin ganar nada.

    Con `fallar`, lanza la excepcion **dentro** de la transaccion y despues de
    haber insertado las filas. Es lo que hace comprobable el criterio CA-12: si
    la transaccion no envolviera bien la escritura, esas doce mil filas quedarian
    en la tabla. Se provoca a proposito en vez de esperar a un corte real, porque
    un criterio que solo se puede verificar cuando algo se rompe solo no se
    verifica nunca.
    """
    parametros = [
        {
            "codigo_distrito": m.codigo_distrito,
            "fecha": m.fecha,
            "temp_max_c": m.temp_max_c,
            "temp_min_c": m.temp_min_c,
            "temp_media_c": m.temp_media_c,
            "humedad_relativa_pct": m.humedad_relativa_pct,
            "viento_ms": m.viento_ms,
            "radiacion_mj_m2": m.radiacion_mj_m2,
            "precipitacion_mm": m.precipitacion_mm,
        }
        for m in mediciones
    ]

    with conexion.transaction(), conexion.cursor() as cursor:
        cursor.executemany(SQL_INSERTAR, parametros)
        if fallar:
            raise ErrorCargaMediciones(
                f"Interrupcion provocada con --fallar-en, tras insertar "
                f"{len(parametros)} filas y antes de confirmar. "
                "Ninguna de esas filas debe quedar en la tabla."
            )

    return len(parametros)


def _resumen(mediciones: list[MedicionDiaria]) -> dict[str, int]:
    """Cuenta huecos por variable. Es la evidencia de que no se rellenaron."""
    campos = (
        "temp_max_c",
        "temp_min_c",
        "temp_media_c",
        "humedad_relativa_pct",
        "viento_ms",
        "radiacion_mj_m2",
        "precipitacion_mm",
    )
    return {campo: sum(1 for m in mediciones if getattr(m, campo) is None) for campo in campos}


def escribir_procedencia(lineas: list[str]) -> None:
    """Deja el rastro de la descarga junto al DDL, como hizo H1.3."""
    RUTA_PROCEDENCIA.parent.mkdir(parents=True, exist_ok=True)
    RUTA_PROCEDENCIA.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def principal(argumentos: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        description="Carga series climaticas diarias en crudo.medicion_diaria"
    )
    analizador.add_argument("--desde", default=DESDE.isoformat())
    analizador.add_argument("--hasta", default=HASTA.isoformat())
    analizador.add_argument(
        "--distrito",
        action="append",
        help="Codigo de distrito. Repetible. Por defecto, los ocho.",
    )
    analizador.add_argument(
        "--solo-comprobar",
        action="store_true",
        help="Comprueba que las dos fuentes responden y no escribe nada",
    )
    analizador.add_argument(
        "--registro",
        help="Archivo donde guardar la salida completa, para la evidencia del PR",
    )
    analizador.add_argument(
        "--fallar-en",
        metavar="CODIGO",
        help=(
            "CA-12: aborta al llegar a ese distrito, despues de descargarlo y "
            "antes de confirmar su transaccion. Sirve para comprobar que una "
            "carga interrumpida no deja series parciales."
        ),
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
    power = ExtractorPower()
    chirps = ExtractorChirps()
    arranque = time.monotonic()

    try:
        with conectar() as conexion:
            territorios = territorios_desde_base(conexion, CODIGO_CANTON)

            if opciones.distrito:
                pedidos = set(opciones.distrito)
                desconocidos = pedidos - {t.codigo for t in territorios}
                if desconocidos:
                    registrar(f"Distritos desconocidos: {sorted(desconocidos)}")
                    return 2
                territorios = [t for t in territorios if t.codigo in pedidos]

            extractor = ExtractorHibrido(
                territorios, power=power, chirps=chirps, registrar=registrar
            )

            registrar(f"Fuente: {extractor.nombre}")
            registrar(f"Ventana: {desde} a {hasta}")
            registrar(f"Distritos: {len(territorios)}")
            registrar(f"Inicio: {datetime.now().astimezone().isoformat(timespec='seconds')}")

            if not extractor.disponible():
                registrar(
                    "Alguna de las dos fuentes no responde. No se carga nada: "
                    "media descarga produce una tabla que parece cargada y no lo esta."
                )
                return 1
            registrar("Las dos fuentes responden.")

            if opciones.solo_comprobar:
                return 0

            lineas = [
                "# Procedencia de las series climaticas",
                "",
                "Generado por `backend/etl/cargar_mediciones.py`. No editar a mano.",
                "",
                f"- Fuente: {extractor.nombre}",
                f"- Ventana: {desde} a {hasta}",
                f"- Momento: {datetime.now().astimezone().isoformat(timespec='seconds')}",
                "",
                "| Distrito | Nombre | Filas | Sin lluvia | Sin temperatura | Segundos |",
                "|---|---|---|---|---|---|",
            ]

            total = 0
            for numero, territorio in enumerate(territorios, start=1):
                registrar(
                    f"\n--- {numero}/{len(territorios)} · "
                    f"{territorio.codigo} {territorio.nombre} ---"
                )
                empezado = time.monotonic()
                mediciones = extractor.extraer(territorio.codigo, desde, hasta)
                huecos = _resumen(mediciones)
                filas = escribir(
                    conexion, mediciones, fallar=territorio.codigo == opciones.fallar_en
                )
                tardo = time.monotonic() - empezado
                total += filas
                registrar(f"escritas {filas} filas en {tardo:.1f} s; huecos {huecos}")
                lineas.append(
                    f"| {territorio.codigo} | {territorio.nombre} | {filas} | "
                    f"{huecos['precipitacion_mm']} | {huecos['temp_media_c']} | {tardo:.1f} |"
                )

            duracion = time.monotonic() - arranque
            lineas += [
                "",
                f"Total de filas escritas: {total} en {duracion:.1f} segundos",
                "",
                "Los dias sin dato quedan con sus columnas en NULL. No se imputa",
                "nada aqui: eso es H1.4, y necesita los huecos intactos para poder",
                "medir cuantos habia.",
            ]
            escribir_procedencia(lineas)

            registrar(f"\nTotal: {total} filas en {duracion:.1f} segundos")
            registrar(f"Procedencia: {RUTA_PROCEDENCIA}")
            return 0

    except (ErrorConexion, ErrorPower, ErrorChirps, ErrorCargaMediciones) as error:
        registrar(f"\nFALLO: {error}")
        return 1
    except Exception:
        # Cualquier otra falla tambien tiene que quedar en la bitacora, porque si
        # solo va a la consola se pierde y la evidencia queda muda sobre lo que
        # paso. Se vuelve a lanzar para no disimular un defecto.
        registrar("\nFALLO INESPERADO:\n" + traceback.format_exc())
        raise
    finally:
        power.cerrar()
        chirps.cerrar()


if __name__ == "__main__":
    raise SystemExit(principal())
