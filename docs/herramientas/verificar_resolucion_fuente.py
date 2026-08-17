"""Comprueba si una fuente climatica distingue entre los distritos del canton.

POR QUE EXISTE

La incidencia I-05: NASA POWER devuelve exactamente el mismo valor para dos puntos
opuestos del canton, porque sirve MERRA-2 en celdas de unos 68 x 55 km y el canton
entero cabe en una sola. Con esa fuente, sequia y lluvia intensa darian el mismo
riesgo en los ocho distritos por construccion y no por hallazgo.

La decision D-15 adopto CHIRPS para precipitacion, **condicionada** a repetir el
mismo test sobre la fuente nueva antes de escribir el extractor. Una resolucion
nominal mejor no es prueba de diferenciacion real: hay que mostrarlo.

Esta herramienta hace ese test, y sirve para cualquier fuente futura.

QUE HACE

  1. Lee los ocho distritos de `geo.distrito` y calcula un punto representativo
     por distrito con ST_PointOnSurface, que garantiza que el punto cae dentro.
  2. Informa la extension real del canton y en cuantas celdas cae, para la malla
     que se le indique.
  3. Si se le pasa --fuente, consulta esa fuente para cada punto y compara.

QUE NO HACE

No decide por vos. Imprime los valores y el veredicto; confirmar o sustituir la
decision D-15 es una decision de arquitectura y va al registro.

USO

    python docs/herramientas/verificar_resolucion_fuente.py
    python docs/herramientas/verificar_resolucion_fuente.py --malla 0.05
    python docs/herramientas/verificar_resolucion_fuente.py --fuente chirps \\
        --desde 2024-09-01 --hasta 2024-09-07

Requiere la base levantada y las geometrias de H1.3 cargadas.
"""

from __future__ import annotations

import argparse
import math
import sys
from datetime import date, datetime

# Mallas conocidas: paso en grados y donde esta anclada.
#
# EL ANCLAJE IMPORTA Y NO ES UN DETALLE. Dos mallas del mismo paso pueden asignar
# un punto a celdas distintas segun donde caigan sus bordes:
#
#   "centro"  los centros de celda caen en multiplos del paso desde -180 y -90,
#             asi que los bordes quedan a medio paso. Es el caso de MERRA-2.
#   "borde"   los bordes caen en multiplos del paso. Es el caso de CHIRPS, cuyos
#             centros estan en -179.975, -179.925, y asi.
#
# La primera version de esta herramienta asumio "borde" para todo, y daba que los
# dos puntos de la incidencia I-05 caian en celdas distintas de POWER. La fuente
# les habia devuelto el mismo valor: la herramienta estaba mal, no el dato. Con el
# anclaje correcto, los dos puntos caen en la misma celda, que es lo observado.
#
# Por eso `autoprueba()` contrasta la logica contra esa observacion real antes de
# usarla.
MALLAS = {
    "power": (0.625, 0.5, "centro"),  # MERRA-2, la que sirve NASA POWER
    "chirps": (0.05, 0.05, "borde"),
    "era5-land": (0.1, 0.1, "centro"),  # lo que entrega el CDS por API
}

# Los dos puntos que Cesar consulto el 16 de agosto y que POWER devolvio
# identicos hasta el ultimo decimal. Ver incidencia I-05.
OBSERVACION_I05 = ((-85.03, 10.42), (-84.87, 10.53))

SQL_PUNTOS = """
    SELECT codigo,
           nombre,
           ST_X(ST_PointOnSurface(geometria)) AS lon,
           ST_Y(ST_PointOnSurface(geometria)) AS lat
      FROM geo.distrito
     ORDER BY codigo
"""

SQL_EXTENSION = """
    SELECT ST_XMin(e), ST_XMax(e), ST_YMin(e), ST_YMax(e)
      FROM (SELECT ST_Extent(geometria) AS e FROM geo.distrito) t
"""


def celda(
    lon: float, lat: float, paso_lon: float, paso_lat: float, anclaje: str = "borde"
) -> tuple[int, int]:
    """
    Indice de celda de una malla regular.

    Con anclaje "borde" los limites caen en multiplos del paso, asi que se
    redondea hacia abajo. Con anclaje "centro" son los centros los que caen en
    multiplos, los limites quedan a medio paso, y hay que redondear al mas
    cercano.
    """
    ajustar = math.floor if anclaje == "borde" else round
    return ajustar((lon + 180) / paso_lon), ajustar((lat + 90) / paso_lat)


def autoprueba() -> bool:
    """
    Comprueba la logica de celdas contra una observacion real antes de usarla.

    NASA POWER devolvio valores identicos para los dos puntos de la incidencia
    I-05. Si esta herramienta dice que caen en celdas distintas, la herramienta
    esta mal: el dato observado manda.
    """
    paso_lon, paso_lat, anclaje = MALLAS["power"]
    a, b = (celda(*p, paso_lon, paso_lat, anclaje) for p in OBSERVACION_I05)

    if a != b:
        print(
            "AUTOPRUEBA FALLIDA: la herramienta dice que los dos puntos de I-05\n"
            f"  caen en celdas distintas de POWER ({a} y {b}), pero la fuente les\n"
            "  devolvio el mismo valor. La logica de celdas esta mal; no se puede\n"
            "  confiar en el resto de la salida.",
            file=sys.stderr,
        )
        return False
    return True


def informe_geografico(cursor, malla: str) -> list[tuple]:
    paso_lon, paso_lat, anclaje = MALLAS[malla]

    cursor.execute(SQL_EXTENSION)
    oeste, este, sur, norte = cursor.fetchone()
    lat_media = (sur + norte) / 2
    ancho = (este - oeste) * 111.320 * math.cos(math.radians(lat_media))
    alto = (norte - sur) * 110.574

    print("\nEXTENSION REAL DEL CANTON")
    print(f"  oeste {oeste:.5f}   este  {este:.5f}")
    print(f"  sur   {sur:.5f}    norte {norte:.5f}")
    print(f"  {ancho:.1f} km de ancho por {alto:.1f} km de alto")
    print(f"  caja envolvente: {ancho * alto:.0f} km2")
    print("\n  El area medida en H1.3 es 669,23 km2. La caja envolvente no puede")
    print("  ser menor que el area: si lo es, el numero esta mal.")
    if ancho * alto < 669.23:
        print("  *** LA CAJA ES MENOR QUE EL AREA. Revisar la carga. ***")

    cursor.execute(SQL_PUNTOS)
    distritos = cursor.fetchall()

    print(
        f"\nPUNTOS REPRESENTATIVOS Y CELDA EN LA MALLA '{malla}' "
        f"({paso_lon} x {paso_lat} grados, anclada al {anclaje})"
    )
    celdas = {}
    for codigo, nombre, lon, lat in distritos:
        c = celda(lon, lat, paso_lon, paso_lat, anclaje)
        celdas.setdefault(c, []).append(codigo)
        print(f"  {codigo}  {nombre:<18} {lon:>10.5f} {lat:>9.5f}   celda {c}")

    print(f"\n  Los ocho distritos caen en {len(celdas)} celda(s) distintas.")
    if len(celdas) == 1:
        print("  *** LA FUENTE NO PUEDE DIFERENCIAR ENTRE DISTRITOS. ***")
        print("  Todos los distritos comparten celda: cualquier variable de esta")
        print("  fuente sera identica en los ocho, por construccion.")
    else:
        repetidas = {c: d for c, d in celdas.items() if len(d) > 1}
        if repetidas:
            print("  Distritos que comparten celda, y por lo tanto valor:")
            for c, d in repetidas.items():
                print(f"    celda {c}: {', '.join(d)}")
        else:
            print("  Cada distrito cae en una celda propia.")

    return distritos


def consultar_chirps(lon: float, lat: float, desde: date, hasta: date) -> list[float]:
    """
    Precipitacion diaria de CHIRPS para un punto, via ClimateSERV.

    Se aisla en una funcion para que cambiar de proveedor no toque el resto.
    Requiere `httpx`, que ya esta en requirements.txt.
    """
    import httpx

    lado = 0.01  # cuadro minimo alrededor del punto; ClimateSERV pide poligono
    geometria = {
        "type": "Polygon",
        "coordinates": [
            [
                [lon - lado, lat - lado],
                [lon + lado, lat - lado],
                [lon + lado, lat + lado],
                [lon - lado, lat + lado],
                [lon - lado, lat - lado],
            ]
        ],
    }

    with httpx.Client(timeout=120.0) as cliente:
        envio = cliente.get(
            "https://climateserv.servirglobal.net/api/submitDataRequest/",
            params={
                "datatype": 0,  # CHIRPS precipitacion diaria
                "begintime": desde.strftime("%m/%d/%Y"),
                "endtime": hasta.strftime("%m/%d/%Y"),
                "intervaltype": 0,
                "operationtype": 5,  # promedio sobre el poligono
                "geometry": __import__("json").dumps(geometria),
            },
        )
        envio.raise_for_status()
        identificador = envio.json()[0]

        import time

        for _ in range(60):
            progreso = cliente.get(
                "https://climateserv.servirglobal.net/api/getDataRequestProgress/",
                params={"id": identificador},
            )
            if progreso.json() and progreso.json()[0] == 100:
                break
            time.sleep(2)

        datos = cliente.get(
            "https://climateserv.servirglobal.net/api/getDataFromRequest/",
            params={"id": identificador},
        )
        datos.raise_for_status()

    return [d["value"]["avg"] for d in datos.json()["data"]]


def prueba_de_diferenciacion(distritos, fuente: str, desde: date, hasta: date) -> None:
    if fuente != "chirps":
        print(f"\nLa consulta a '{fuente}' no esta implementada en esta herramienta.")
        print("El informe geografico de arriba ya dice si la malla puede diferenciar.")
        return

    print(f"\nCONSULTANDO {fuente.upper()} del {desde} al {hasta}")
    print("  Puede tardar un par de minutos: son ocho consultas encoladas.\n")

    series = {}
    for codigo, nombre, lon, lat in distritos:
        try:
            series[codigo] = consultar_chirps(lon, lat, desde, hasta)
            print(f"  {codigo} {nombre:<18} {len(series[codigo])} dias")
        except Exception as error:  # noqa: BLE001
            print(f"  {codigo} {nombre:<18} FALLO: {error}")
            return

    print("\nVALORES POR DISTRITO Y DIA (mm)")
    dias = min(len(v) for v in series.values())
    for i in range(dias):
        fila = "  ".join(f"{series[c][i]:6.2f}" for c in sorted(series))
        print(f"  dia {i + 1}:  {fila}")

    print("\nVEREDICTO")
    identicos = all(len({round(series[c][i], 4) for c in series}) == 1 for i in range(dias))
    if identicos:
        print("  *** TODOS LOS DISTRITOS DEVUELVEN EL MISMO VALOR. ***")
        print("  Esta fuente tampoco diferencia. D-15 tendria que pasar a")
        print("  Sustituida y hay que volver a decidir.")
    else:
        rangos = [
            max(series[c][i] for c in series) - min(series[c][i] for c in series)
            for i in range(dias)
        ]
        print(
            f"  Los valores difieren entre distritos. Rango maximo en un dia:"
            f" {max(rangos):.2f} mm"
        )
        print("  D-15 queda confirmada. Pegar esta salida en la evidencia de H1.1.")


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analizador.add_argument(
        "--malla",
        default="power",
        choices=sorted(MALLAS),
        help="malla contra la que comparar (por defecto: power)",
    )
    analizador.add_argument(
        "--fuente", choices=["chirps"], help="consultar la fuente de verdad, no solo la malla"
    )
    analizador.add_argument("--desde", default="2024-09-01")
    analizador.add_argument("--hasta", default="2024-09-07")
    argumentos = analizador.parse_args()

    if not autoprueba():
        return 1

    try:
        from basedatos.conexion import ErrorConexion, conectar
    except ImportError as error:
        print(f"No se pudo importar la conexion: {error}", file=sys.stderr)
        print("Correr desde la raiz del repositorio.", file=sys.stderr)
        return 1

    try:
        with conectar() as conexion, conexion.cursor() as cursor:
            distritos = informe_geografico(cursor, argumentos.malla)
    except ErrorConexion as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        return 1

    if argumentos.fuente:
        prueba_de_diferenciacion(
            distritos,
            argumentos.fuente,
            datetime.strptime(argumentos.desde, "%Y-%m-%d").date(),
            datetime.strptime(argumentos.hasta, "%Y-%m-%d").date(),
        )

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
