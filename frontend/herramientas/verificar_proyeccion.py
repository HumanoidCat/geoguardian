"""
Verifica la transformacion WGS84 -> CRTM05 del visor contra una implementacion
independiente.

Por que existe: escribir las formulas de Transversa de Mercator a mano es
razonable solo si algo comprueba que estan bien. Esto lo comprueba.

Corre el modulo del visor con `node`, calcula lo mismo con `pyproj` y compara.
Las dos implementaciones quedan vivas: si alguien toca las formulas, esto falla.

  1. Los puntos de control ANALITICOS, que valen por definicion de la proyeccion
     y no dependen de pyproj.
  2. Los puntos de control REALES: los ocho distritos y los bordes del canton.
  3. Que el punto representativo de cada distrito caiga DENTRO de su poligono.

Uso, desde la raiz del repositorio y con el entorno virtual activo:

    python frontend/herramientas/verificar_proyeccion.py

Historia H5.6. Rubrica de Computacion Grafica, criterio CG-1.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
MODULO = RAIZ / "frontend" / "src" / "datos" / "proyeccion.js"
GEOMETRIA = RAIZ / "frontend" / "src" / "datos" / "geometria.js"
DISTRITOS = RAIZ / "frontend" / "public" / "simulados" / "distritos.geojson"

EPSG_CRTM05 = 8908

# Alejandro midio la diferencia entre la serie de Snyder sobre GRS80 y pyproj en
# seis puntos: el maximo fue 0,0053 mm, y eso muy fuera del canton. PROJ no
# aplica desplazamiento de datum entre 4326 y 8908 porque CR-SIRGAS esta
# alineado con el marco global; lo unico que difiere es el aplanamiento, en
# 1,5 x 10^-9.
#
# Por eso el umbral no es una tolerancia elegida a ojo para que quepa el error:
# **por encima de un milimetro hay un defecto en las formulas**, no una
# propiedad de la geodesia.
TOLERANCIA_MM = 1.0

fallos: list[str] = []


def exigir(condicion: bool, descripcion: str, detalle: str = "") -> None:
    marca = "OK   " if condicion else "FALLA"
    print(f"  {marca} {descripcion}{('  ' + detalle) if detalle else ''}")
    if not condicion:
        fallos.append(descripcion)


# --------------------------------------------------------------------------- #
# Ejecutar el modulo del visor                                                  #
# --------------------------------------------------------------------------- #


def _correr_en_node(cuerpo: str, entrada: object) -> object:
    """
    Corre un fragmento de JavaScript que importa un modulo del visor.

    Se importa el modulo real, no una copia: comprobar una transcripcion no
    comprobaria nada. Es el mismo criterio por el que verificar_escala.py lee los
    colores de tokens.css en vez de tenerlos escritos.

    **Los datos van por archivo y no por la linea de comandos.** Windows corta la
    linea alrededor de los 8000 caracteres, y las ocho geometrias del canton
    pesan mucho mas: cada distrito tiene del orden de mil vertices. El sintoma es
    un `WinError 206` que no menciona el tamano en ningun lado.

    **Y las rutas se pasan con `as_uri()`.** El cargador de modulos de Node exige
    `file:///C:/...` en Windows y rechaza `C:/...`. En Linux la ruta suelta
    funciona, asi que los dos defectos solo aparecen de un lado.
    """
    with tempfile.TemporaryDirectory() as carpeta:
        archivo = Path(carpeta) / "entrada.json"
        archivo.write_text(json.dumps(entrada), encoding="utf-8")

        guion = (
            "import { readFileSync } from 'node:fs'\n"
            f"const entrada = JSON.parse(readFileSync({json.dumps(str(archivo))}, 'utf-8'))\n"
            f"{cuerpo}\n"
        )

        try:
            salida = subprocess.run(
                ["node", "--input-type=module", "-e", guion],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError:
            raise SystemExit(
                "ERROR: no se encontro `node`. Hace falta para correr el modulo del visor."
            ) from None
        except subprocess.CalledProcessError as fallo:
            raise SystemExit(f"ERROR: el modulo del visor no corrio.\n{fallo.stderr}") from None

    return json.loads(salida.stdout)


def proyectar_con_el_visor(puntos: list[tuple[float, float]]) -> list[dict[str, float]]:
    """Corre `aCRTM05` del visor y devuelve sus resultados."""
    return _correr_en_node(
        f"import {{ aCRTM05 }} from {json.dumps(MODULO.as_uri())}\n"
        "console.log(JSON.stringify(entrada.map(([lon, lat]) => aCRTM05(lon, lat))))",
        puntos,
    )


def punto_en_superficie_del_visor(geometrias: list[dict]) -> list[dict | None]:
    """Lo mismo para `puntoEnSuperficie`, del modulo de geometria."""
    return _correr_en_node(
        f"import {{ puntoEnSuperficie }} from {json.dumps(GEOMETRIA.as_uri())}\n"
        "console.log(JSON.stringify(entrada.map(puntoEnSuperficie)))",
        geometrias,
    )


# --------------------------------------------------------------------------- #
# Geometria, para comprobar la contencion                                       #
# --------------------------------------------------------------------------- #


def anillos_exteriores(geometria: dict) -> list[list[list[float]]]:
    if geometria["type"] == "Polygon":
        return [geometria["coordinates"][0]]
    if geometria["type"] == "MultiPolygon":
        return [p[0] for p in geometria["coordinates"]]
    return []


def dentro(punto: tuple[float, float], anillos: list) -> bool:
    """Cruce de rayos. Implementacion propia y distinta de la del visor."""
    x, y = punto
    adentro = False
    for anillo in anillos:
        for i in range(len(anillo) - 1):
            x0, y0 = anillo[i]
            x1, y1 = anillo[i + 1]
            if (y0 > y) != (y1 > y):
                corte = (x1 - x0) * (y - y0) / (y1 - y0) + x0
                if x < corte:
                    adentro = not adentro
    return adentro


# --------------------------------------------------------------------------- #


def main() -> None:
    try:
        from pyproj import Transformer
    except ImportError:
        raise SystemExit(
            "ERROR: falta pyproj. Esta en requirements.txt: activa el entorno virtual."
        ) from None

    if not DISTRITOS.exists():
        raise SystemExit(
            f"ERROR: no existe {DISTRITOS.relative_to(RAIZ)}. "
            "Corre primero frontend/herramientas/exportar_simulados.py"
        )

    coleccion = json.loads(DISTRITOS.read_text(encoding="utf-8"))
    rasgos = coleccion["features"]

    print(f"Modulo verificado: {MODULO.relative_to(RAIZ)}")
    print(f"Referencia independiente: pyproj, EPSG:4326 -> EPSG:{EPSG_CRTM05}")

    # ----------------------------------------------------------------------- #
    # 1. Puntos de control analiticos                                          #
    # ----------------------------------------------------------------------- #
    print("\nPuntos de control analiticos, que no dependen de pyproj:")

    en_meridiano = [(-84.0, lat) for lat in (8.0, 10.0, 10.47, 11.5)]
    resultados = proyectar_con_el_visor(en_meridiano)
    for (_, lat), r in zip(en_meridiano, resultados, strict=True):
        exigir(
            abs(r["este"] - 500000.0) < 1e-6,
            f"en el meridiano central, a {lat} grados de latitud, el este es 500000",
            f"{r['este']:.6f}",
        )

    # El factor de escala vive en el eje norte: y no es la distancia al ecuador,
    # es esa distancia por 0.9999. Se comprueba que la razon sea exactamente esa.
    ecuador = proyectar_con_el_visor([(-84.0, 0.0)])[0]
    exigir(
        abs(ecuador["norte"]) < 1e-6 and abs(ecuador["este"] - 500000.0) < 1e-6,
        "el origen de la proyeccion cae en (500000, 0)",
        f"({ecuador['este']:.6f}, {ecuador['norte']:.6f})",
    )

    # ----------------------------------------------------------------------- #
    # 2. Puntos de control reales, contra pyproj                               #
    # ----------------------------------------------------------------------- #
    transformador = Transformer.from_crs("EPSG:4326", f"EPSG:{EPSG_CRTM05}", always_xy=True)

    puntos: list[tuple[float, float]] = []
    nombres: list[str] = []

    for rasgo in rasgos:
        anillos = anillos_exteriores(rasgo["geometry"])
        xs = [p[0] for a in anillos for p in a]
        ys = [p[1] for a in anillos for p in a]
        puntos.append((sum(xs) / len(xs), sum(ys) / len(ys)))
        nombres.append(rasgo["properties"]["nombre"])

    # Los bordes del canton: son los que mas se alejan del meridiano central, y
    # ahi es donde la serie de Snyder se degradaria si lo hiciera.
    todos_x = [p[0] for r in rasgos for a in anillos_exteriores(r["geometry"]) for p in a]
    todos_y = [p[1] for r in rasgos for a in anillos_exteriores(r["geometry"]) for p in a]
    for etiqueta, punto in (
        ("borde oeste", (min(todos_x), sum(todos_y) / len(todos_y))),
        ("borde este", (max(todos_x), sum(todos_y) / len(todos_y))),
        ("borde sur", (sum(todos_x) / len(todos_x), min(todos_y))),
        ("borde norte", (sum(todos_x) / len(todos_x), max(todos_y))),
    ):
        puntos.append(punto)
        nombres.append(etiqueta)

    del_visor = proyectar_con_el_visor(puntos)

    print(f"\nContra pyproj, en {len(puntos)} puntos (maximo permitido: {TOLERANCIA_MM} mm):")
    peor = 0.0
    for nombre, (lon, lat), mio in zip(nombres, puntos, del_visor, strict=True):
        este, norte = transformador.transform(lon, lat)
        dif_mm = max(abs(mio["este"] - este), abs(mio["norte"] - norte)) * 1000
        peor = max(peor, dif_mm)
        exigir(dif_mm < TOLERANCIA_MM, f"{nombre}", f"{dif_mm:.6f} mm")

    print(f"\n  Diferencia maxima: {peor:.6f} mm")

    # ----------------------------------------------------------------------- #
    # 3. El punto representativo cae dentro de su distrito                     #
    # ----------------------------------------------------------------------- #
    print("\nEl punto que se muestra de cada distrito cae dentro del distrito:")

    geometrias = [r["geometry"] for r in rasgos]
    representativos = punto_en_superficie_del_visor(geometrias)

    for rasgo, punto in zip(rasgos, representativos, strict=True):
        nombre = rasgo["properties"]["nombre"]
        if punto is None:
            exigir(False, f"{nombre}: el visor no pudo calcular un punto", "")
            continue
        anillos = anillos_exteriores(rasgo["geometry"])
        exigir(
            dentro((punto["longitud"], punto["latitud"]), anillos),
            nombre,
            f"{punto['latitud']:.6f}, {punto['longitud']:.6f}",
        )

    if fallos:
        print(f"\n{len(fallos)} verificaciones fallaron:")
        for fallo in fallos:
            print(f"  - {fallo}")
        sys.exit(1)

    print("\nTodas las verificaciones pasaron.")


if __name__ == "__main__":
    main()
