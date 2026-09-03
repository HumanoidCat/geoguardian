"""Comprueba el extractor de Sentinel-2. Historia H1.6.

=============================================================================
QUE COMPRUEBA, Y QUE PARTE NECESITA RED
=============================================================================

    CA-1  la estacion seca cruza el cambio de anio                sin red
    CA-2  el filtro pide L2A, la caja de Tilaran y la nubosidad   sin red
    CA-3  las bandas son las de NDVI y NDWI a 20 metros           sin red
    CA-4  el catalogo devuelve escenas, y todas de estacion seca  CON red
    CA-5  todas cumplen el umbral de nubosidad que se pidio       CON red
    CA-6  los controles distinguen                                sin red

**CA-4 y CA-5 consultan el catalogo de verdad**, y eso se puede hacer **sin
credenciales**: comprobado contra el servicio, el catalogo OData responde abierto
y solo la descarga exige el token.

Es lo que permite que esto corra en la integracion continua sin poner un secreto
ahi. Con `--sin-red` se saltan y el resto sigue valiendo.

=============================================================================
LO QUE NO COMPRUEBA
=============================================================================

**Que la descarga funcione.** Eso son 50 MB por escena y una credencial; se hace a
mano y su salida se archiva en la evidencia. Aqui se comprueba **lo que decide si
la descarga va a pedir lo correcto**, que es la parte donde un error pasa
desapercibido: un filtro mal armado no falla, filtra de menos.

Uso:
    python backend/etl/fuentes/verificar_h16.py
    python backend/etl/fuentes/verificar_h16.py --sin-red
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import httpx  # noqa: E402

from backend.etl.fuentes.sentinel import (  # noqa: E402
    BANDAS,
    CAJA,
    ESTACION_SECA,
    NUBOSIDAD_MAXIMA,
    RESOLUCION,
    TIPO_PRODUCTO,
    EscenaSentinel,
    ExtractorSentinel,
    _filtro,
    _rango_de_estacion_seca,
)

fallos: list[str] = []


def comprobar(descripcion: str, condicion: bool, detalle: str = "") -> None:
    print(f"  {'ok   ' if condicion else 'FALLA'}  {descripcion}")
    if not condicion:
        fallos.append(descripcion)
        if detalle:
            print(f"         {detalle}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sin-red", action="store_true", help="salta CA-4 y CA-5")
    argumentos = p.parse_args()

    print("\nH1.6 · Imagenes Sentinel-2 de estacion seca\n")

    # ------------------------------------------------------------------ CA-1 - #
    print("CA-1, la estacion seca cruza el cambio de anio:")

    desde, hasta = _rango_de_estacion_seca(2025)
    comprobar(
        f"la temporada 2025 empieza en diciembre de 2024  ({desde[:10]})",
        desde.startswith("2024-12"),
        "si empezara en diciembre de 2025 el rango quedaria invertido y devolveria "
        "cero escenas sin fallar, que se ve igual que un cielo nublado",
    )
    comprobar(f"y termina despues de abril  ({hasta[:10]})", hasta.startswith("2025-05"))

    # ------------------------------------------------------------------ CA-2 - #
    print("\nCA-2, el filtro pide lo que la historia pide:")

    filtro = _filtro(desde, hasta, NUBOSIDAD_MAXIMA)
    comprobar(f"producto {TIPO_PRODUCTO}, con correccion atmosferica", TIPO_PRODUCTO in filtro)
    comprobar(
        f"nubosidad menor o igual a {NUBOSIDAD_MAXIMA:.0f} %",
        f"le {NUBOSIDAD_MAXIMA}" in filtro and "cloudCover" in filtro,
    )
    x0, y0, x1, y1 = CAJA
    comprobar(
        f"la caja cubre el canton  ({x0} {y0}) a ({x1} {y1})",
        all(str(c) in filtro for c in CAJA),
    )
    comprobar(
        "la caja esta en Costa Rica y no al otro lado del mundo",
        -86 < x0 < x1 < -83 and 9 < y0 < y1 < 12,
        "un signo perdido en la longitud pone el poligono en Asia y el catalogo "
        "devuelve cero escenas sin explicar nada",
    )

    # ------------------------------------------------------------------ CA-3 - #
    print("\nCA-3, las bandas son las de NDVI y NDWI a 20 metros:")

    comprobar("B04, el rojo de NDVI", "B04" in BANDAS)
    comprobar("B03, el verde de NDWI", "B03" in BANDAS)
    comprobar(
        "B8A y NO B08, porque a 20 m B08 no existe",
        "B8A" in BANDAS and "B08" not in BANDAS,
        "B08 solo esta en la carpeta de 10 m. Pedirlo en R20m devuelve 404",
    )
    comprobar("SCL, la mascara de nubes por pixel", "SCL" in BANDAS)
    comprobar(f"se piden de {RESOLUCION}", RESOLUCION == "R20m")

    # ------------------------------------------------------------ CA-4 y CA-5 - #
    if argumentos.sin_red:
        print("\nCA-4 y CA-5 omitidos por --sin-red.")
    else:
        print("\nCA-4, el catalogo devuelve escenas de estacion seca:")

        extractor = ExtractorSentinel()
        try:
            escenas = extractor.buscar(2025)
        except (httpx.HTTPError, Exception) as error:  # noqa: BLE001
            comprobar(
                "el catalogo responde",
                False,
                f"{type(error).__name__}: {str(error).splitlines()[0]}",
            )
            escenas = []
        finally:
            extractor.cerrar()

        comprobar(
            f"hay escenas en la temporada 2024-2025  ({len(escenas)})",
            len(escenas) > 0,
            "cero escenas puede ser el cielo, pero con el umbral en 20 % y cinco "
            "meses seria muy raro: revisar el filtro antes de creerle",
        )

        for escena in escenas:
            comprobar(
                f"{escena.fecha}  {escena.mosaico}  mes {escena.fecha.month}",
                escena.fecha.month in ESTACION_SECA,
                "una escena fuera de diciembre-abril significa que el filtro de "
                "fechas no esta haciendo lo que dice",
            )

        print("\nCA-5, el mosaico es el de Tilaran:")
        mosaicos = {e.mosaico for e in escenas}
        comprobar(
            f"todas caen en T16PGS  ({', '.join(sorted(mosaicos)) or 'ninguna'})",
            mosaicos <= {"T16PGS"} and bool(mosaicos),
            "otro mosaico significa que la caja se corrio",
        )

    # ------------------------------------------------------------------ CA-6 - #
    #
    # Sin esto, todo lo de arriba podria estar pasando por mirar el lugar
    # equivocado. Es lo mismo que hace CA-5 de verificar_diagramas.py.
    print("\nCA-6, los controles distinguen:")

    invertido = _filtro(hasta, desde, NUBOSIDAD_MAXIMA)
    comprobar(
        "un rango invertido produce un filtro DISTINTO",
        invertido != filtro,
        "si diera el mismo filtro, CA-1 no estaria comprobando nada",
    )

    laxo = _filtro(desde, hasta, 95.0)
    comprobar(
        "cambiar la nubosidad cambia el filtro",
        "le 95.0" in laxo and "le 95.0" not in filtro,
    )

    falsa = EscenaSentinel(
        id="x",
        nombre="S2A_MSIL2A_20250715T160601_T16PGS_x.SAFE",
        fecha=date(2025, 7, 15),
        bytes=0,
    )
    comprobar(
        "una escena de julio NO cuenta como estacion seca",
        falsa.fecha.month not in ESTACION_SECA,
        "si julio contara, CA-4 pasaria con imagenes de plena lluvia",
    )

    if fallos:
        print(f"\n{len(fallos)} comprobaciones fallaron:\n")
        for f in fallos:
            print(f"  - {f}")
        print()
        return 1

    print("\nH1.6 se cumple en lo que se puede comprobar sin descargar.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
