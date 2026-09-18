"""
Carga de la serie larga del canton. Historia H1.16, issue #299. Decision D-47.

QUE HACE

Descarga la precipitacion diaria del canton entero desde 1950 y la escribe en
`crudo.serie_canton` (migracion 020). Un solo punto, una sola peticion, una fila
por dia y **sin distrito**.

El uso es uno y esta escrito en D-47: contar episodios de sequia sobre la serie
larga en H3.11. No alimenta el nivel de riesgo, ni el SPI de la tarjeta, ni la
matriz de caracteristicas.

EL PUNTO DEL CANTON SALE DE LA BASE, NO DEL CODIGO

`ST_PointOnSurface(ST_Union(...))` sobre `geo.distrito`, con la misma funcion que
H3.9 uso para las columnas geograficas. Un par de coordenadas escrito a mano
seria un dato sin procedencia, y este proyecto ya tuvo esa discusion con las
geometrias en H1.3.

`ST_PointOnSurface` y no `ST_Centroid` por una razon: el canton rodea el Lago
Arenal y el centroide de una figura con esa forma puede caer sobre el agua.
`PointOnSurface` garantiza un punto **dentro** del poligono.

IDEMPOTENTE

`ON CONFLICT (fecha) DO UPDATE`. Correrla dos veces deja la tabla igual que
correrla una. La clave natural es la fecha, porque la serie es del canton: si
algun dia hubiera dos filas para el mismo dia, una de las dos seria de otro
lugar y eso es justo lo que D-47 prohibe.

UNA SOLA TRANSACCION, A DIFERENCIA DE `cargar_mediciones`

Alla la unidad es el distrito porque son ocho descargas largas. Aca la descarga
es una sola peticion: o entran los dias del rango entero o no entra ninguno. La
corrida del 2026-09-14 trajo 28.011 dias en 3,25 s.

    python -m backend.etl.cargar_serie_canton --sin-escribir
    python -m backend.etl.cargar_serie_canton --bitacora serie-canton.txt
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.etl import bitacora  # noqa: E402
from backend.etl.fuentes.open_meteo import (  # noqa: E402
    ATRIBUCION,
    MODELO,
    PRIMER_ANIO,
    ExtractorOpenMeteoCanton,
)
from basedatos.conexion import ErrorConexion, conectar  # noqa: E402

#: El punto representativo del canton, de la base y no del codigo.
SQL_PUNTO = """
    SELECT ST_Y(punto) AS lat, ST_X(punto) AS lon
      FROM (
            SELECT ST_PointOnSurface(ST_Union(geometria)) AS punto
              FROM geo.distrito
           ) AS canton
"""

SQL_INSERTAR = """
    INSERT INTO crudo.serie_canton (
        fecha, precipitacion_mm, modelo,
        celda_lat, celda_lon, punto_lat, punto_lon
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (fecha) DO UPDATE SET
        precipitacion_mm = EXCLUDED.precipitacion_mm,
        modelo           = EXCLUDED.modelo,
        celda_lat        = EXCLUDED.celda_lat,
        celda_lon        = EXCLUDED.celda_lon,
        punto_lat        = EXCLUDED.punto_lat,
        punto_lon        = EXCLUDED.punto_lon,
        descargado_en    = now()
"""

#: ERA5 se publica con unos cinco dias de atraso. Pedir hasta hoy devuelve la
#: cola en `null`, y esos nulos son ausencia real: se guardan igual (D-07).
ATRASO_DIAS = 5


def punto_del_canton(conexion) -> tuple[float, float]:
    with conexion.cursor() as cursor:
        cursor.execute(SQL_PUNTO)
        fila = cursor.fetchone()
    if fila is None or fila[0] is None:
        raise RuntimeError(
            "geo.distrito no devolvio un punto para el canton. Sin geometrias no hay "
            "de donde sacar la coordenada, y no se inventa."
        )
    return float(fila[0]), float(fila[1])


def escribir(conexion, filas) -> int:
    parametros = [
        (
            f.fecha,
            f.precipitacion_mm,
            f.modelo,
            f.celda_lat,
            f.celda_lon,
            f.punto_lat,
            f.punto_lon,
        )
        for f in filas
    ]
    with conexion.cursor() as cursor:
        cursor.executemany(SQL_INSERTAR, parametros)
    return len(parametros)


def main() -> int:
    hoy = date.today()
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    analizador.add_argument("--desde", default=f"{PRIMER_ANIO}-01-01")
    analizador.add_argument("--hasta", default=(hoy - timedelta(days=ATRASO_DIAS)).isoformat())
    analizador.add_argument("--modelo", default=MODELO)
    analizador.add_argument(
        "--sin-escribir",
        action="store_true",
        help="descarga y cuenta, no toca la base",
    )
    analizador.add_argument("--bitacora", default=None)
    argumentos = analizador.parse_args()

    desde = date.fromisoformat(argumentos.desde)
    hasta = date.fromisoformat(argumentos.hasta)

    with bitacora.abrir(argumentos.bitacora) as registrar:
        registrar("Serie larga del canton · H1.16 · D-47")
        registrar(f"  rango   {desde} a {hasta}")
        registrar(f"  modelo  {argumentos.modelo}")

        try:
            with conectar() as conexion:
                lat, lon = punto_del_canton(conexion)
                registrar(f"  punto   {lat:.6f}, {lon:.6f}  (ST_PointOnSurface de geo.distrito)")

                extractor = ExtractorOpenMeteoCanton(
                    punto_lat=lat, punto_lon=lon, modelo=argumentos.modelo
                )

                arranque = time.monotonic()
                filas = extractor.consultar(desde, hasta)
                tardanza = time.monotonic() - arranque

                con_dato = sum(1 for f in filas if f.precipitacion_mm is not None)
                registrar(f"  celda   {filas[0].celda_lat}, {filas[0].celda_lon}")
                registrar(
                    f"  dias    {len(filas)}  con dato {con_dato}  sin dato "
                    f"{len(filas) - con_dato}"
                )
                registrar(f"  peticiones {extractor.peticiones}  en {tardanza:.2f} s")

                if argumentos.sin_escribir:
                    registrar("\n  --sin-escribir: no se toco la base.")
                    return 0

                escritas = escribir(conexion, filas)
                conexion.commit()
                registrar(f"\n  escritas {escritas} filas en crudo.serie_canton")
        except ErrorConexion as causa:
            registrar(f"\nFALLO de conexion: {causa}")
            return 1
        except Exception as causa:  # noqa: BLE001
            registrar(f"\nFALLO: {causa}")
            return 1

        registrar(f"\n  {ATRIBUCION}")
        registrar("  Ninguna fila lleva codigo_distrito: la tabla no tiene esa columna (CA-9).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
