"""
Mide hasta que fecha sirve hoy cada producto que H1.14 quiere ingerir.

Es el punto 2 de los criterios de H1.14: antes de escribir la ingesta se
comprueba contra el servicio real que producto hay y con que latencia, en vez
de suponerlo. El catalogo publicado de ClimateSERV (pagina "develop-api",
leida el 2026-09-03) ofrece:

    0   UCSB CHIRPS Rainfall   final, con estaciones
    90  UCSB CHIRP Rainfall    sin estaciones, sale antes

y NO ofrece el "CHIRPS preliminar" que nombra D-26: ese lo publica CHC como
GeoTIFF y ClimateSERV no lo sirve. Lo que este guion mide es cuanto llega hoy
cada uno de los dos, sobre el mismo cuadro minimo que usa `disponible()`.

Para incendio mide la API por area de FIRMS, que es la unica que cubre el anio
en curso (el archivo por pais termina en 2024, comprobado en H1.2). Necesita
`FIRMS_MAP_KEY` en `.env`; la clave se lee del entorno y no se imprime.

Uso, desde la raiz del repositorio y con el entorno activado:
    python docs/herramientas/medir_productos_ingesta.py
    python docs/herramientas/medir_productos_ingesta.py --dias 75
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from backend.etl.fuentes import chirps  # noqa: E402
from backend.etl.fuentes.chirps import (  # noqa: E402
    PRODUCTOS,
    TIPO_DATO,
    TIPO_DATO_CHIRP,
    ErrorChirps,
    ExtractorChirps,
)
from backend.etl.fuentes.power import ExtractorPower  # noqa: E402

# El mismo cuadro que usa ExtractorChirps.disponible(): una celda en Tilaran.
CUADRO = {
    "type": "Polygon",
    "coordinates": [
        [[-84.95, 10.48], [-84.94, 10.48], [-84.94, 10.49], [-84.95, 10.49], [-84.95, 10.48]]
    ],
}

# Caja del canton, la misma que acotan los CHECK de crudo.foco_calor (005).
CAJA_FIRMS = "-85.2,10.2,-84.6,10.8"
FUENTES_FIRMS = ("MODIS_NRT", "VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT")
FIRMS_AREA = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


def medir_chirps(tipo_dato: str, desde: date, hasta: date) -> None:
    extractor = ExtractorChirps(tipo_dato=tipo_dato)
    try:
        valores = extractor.consultar(CUADRO, desde, hasta)
    except (ErrorChirps, httpx.HTTPError) as error:
        print(f"  tipo {tipo_dato} ({PRODUCTOS[tipo_dato]}): FALLO {error}")
        return
    finally:
        extractor.cerrar()

    con_dato = sorted(f for f, v in valores.items() if v is not None)
    nulos = sum(1 for v in valores.values() if v is None)
    ultimo = con_dato[-1] if con_dato else None
    latencia = (hasta - ultimo).days if ultimo else None
    print(
        f"  tipo {tipo_dato} ({PRODUCTOS[tipo_dato]}): {len(valores)} fechas devueltas, "
        f"{nulos} nulas, ultima con dato {ultimo}, latencia {latencia} dias respecto a {hasta}"
    )


def medir_power(desde: date, hasta: date) -> None:
    extractor = ExtractorPower()
    try:
        respuesta = extractor.consultar(-84.95, 10.48, desde, hasta)
    except Exception as error:  # noqa: BLE001 - es una medicion, se reporta y sigue
        print(f"  POWER: FALLO {type(error).__name__}: {error}")
        return
    finally:
        extractor.cerrar()

    serie = respuesta.series.get("T2M", {})
    con_dato = sorted(f for f, v in serie.items() if v is not None)
    ultimo = con_dato[-1] if con_dato else None
    latencia = (hasta - ultimo).days if ultimo else None
    print(
        f"  POWER T2M: {len(serie)} fechas, ultima con dato {ultimo}, "
        f"latencia {latencia} dias respecto a {hasta}"
    )


def medir_firms(hasta: date) -> None:
    clave = os.environ.get("FIRMS_MAP_KEY", "").strip()
    if not clave:
        print("  FIRMS: sin FIRMS_MAP_KEY en el entorno; no se mide")
        return

    with httpx.Client(timeout=60.0, follow_redirects=True) as cliente:
        # Hasta que dia sirve cada fuente, segun el servicio. Es lo que la
        # ingesta usa para decidir que dias pide en SP y cuales en NRT.
        try:
            respuesta = cliente.get(
                f"{FIRMS_AREA.replace('/area/csv', '')}/data_availability/csv/{clave}/ALL"
            )
            texto = respuesta.text
            if respuesta.status_code == 200 and not texto.lstrip().startswith("<"):
                print("  data_availability:")
                for linea in texto.strip().splitlines():
                    print(f"    {linea}")
            else:
                print(f"  data_availability: HTTP {respuesta.status_code}, cuerpo: {texto[:120]!r}")
        except httpx.HTTPError as error:
            print(f"  data_availability: FALLO {type(error).__name__}")

        for fuente in FUENTES_FIRMS:
            url = f"{FIRMS_AREA}/{clave}/{fuente}/{CAJA_FIRMS}/5/{hasta.isoformat()}"
            try:
                respuesta = cliente.get(url)
            except httpx.HTTPError as error:
                print(f"  FIRMS {fuente}: FALLO {type(error).__name__}")
                continue
            texto = respuesta.text
            if respuesta.status_code != 200 or "latitude" not in texto[:300]:
                # Sin la URL: lleva la clave.
                print(f"  FIRMS {fuente}: HTTP {respuesta.status_code}, cuerpo: {texto[:120]!r}")
                continue
            filas = list(csv.DictReader(io.StringIO(texto)))
            columnas = list(filas[0].keys()) if filas else texto.splitlines()[0].split(",")
            fechas = sorted({f["acq_date"] for f in filas})
            versiones = sorted({f.get("version", "") for f in filas})
            print(
                f"  FIRMS {fuente}: {len(filas)} focos en la caja en los 5 dias hasta {hasta}; "
                f"fechas {fechas[:1]}..{fechas[-1:]}; version={versiones}; "
                f"columnas={columnas}"
            )


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    analizador.add_argument("--dias", type=int, default=75, help="Ventana hacia atras")
    analizador.add_argument(
        "--solo",
        choices=("chirps", "chirp", "power", "firms"),
        action="append",
        help="Medir solo esa fuente. Repetible.",
    )
    analizador.add_argument(
        "--intentos",
        type=int,
        default=chirps.INTENTOS_MAXIMOS,
        help=f"Cuantas veces esperar el resultado de ClimateSERV (3 s cada una; {chirps.INTENTOS_MAXIMOS})",
    )
    opciones = analizador.parse_args()
    chirps.INTENTOS_MAXIMOS = opciones.intentos
    solo = set(opciones.solo or ("chirps", "chirp", "power", "firms"))

    load_dotenv(RAIZ / ".env")
    hasta = date.today() - timedelta(days=1)
    desde = hasta - timedelta(days=opciones.dias)

    print(f"Ventana medida: {desde} a {hasta} (hoy es {date.today()})")
    if solo & {"chirps", "chirp"}:
        print(f"ClimateSERV (esperando hasta {opciones.intentos * 3} s por resultado):")
        for tipo in (TIPO_DATO, TIPO_DATO_CHIRP):
            if PRODUCTOS[tipo] in solo:
                medir_chirps(tipo, desde, hasta)
    if "power" in solo:
        print("NASA POWER:")
        medir_power(desde, hasta)
    if "firms" in solo:
        print("FIRMS, API por area (ultimos 5 dias):")
        medir_firms(hasta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
