"""
Genera la capa del Lago Arenal y su nota de procedencia, a partir del WFS del SNIT.

Por que existe: `frontend/public/geo/lago-arenal.geojson` y su
`procedencia-lago-arenal.md` son artefactos derivados. Se regeneran con este
guion y no se editan a mano, igual que la matriz de trazabilidad. Quien quiera
cambiar la tolerancia o el origen cambia esto, no el resultado.

El servicio devuelve **EPSG:5367 (CRTM05) si no se le pide otra cosa**. Sin
`srsName=EPSG:4326` las coordenadas salen en metros proyectados y Leaflet las
coloca en el Golfo de Guinea. Por eso el parametro va explicito en la peticion.

La simplificacion es Douglas-Peucker escrito aca, sin dependencias: el proyecto
no arrastra una biblioteca de geometria por un poligono.

Uso, desde la raiz del repositorio:

    python frontend/herramientas/generar_lago.py                # descarga del SNIT
    python frontend/herramientas/generar_lago.py --crudo a.json # usa una copia
    python frontend/herramientas/generar_lago.py --medir        # solo la tabla

Historia H14.3. Rubrica de Computacion Grafica, CG-1.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DESTINO = RAIZ / "frontend" / "public" / "geo" / "lago-arenal.geojson"
PROCEDENCIA = RAIZ / "frontend" / "public" / "geo" / "procedencia-lago-arenal.md"

SERVICIO = "https://geos.snitcr.go.cr/be/IGN_25/wfs"
CAPA = "IGN_25:cuerposdeagua_25k"
FILTRO = "nombre='Embalse de Arenal'"
PETICION = (
    f"{SERVICIO}?service=WFS&version=2.0.0&request=GetFeature"
    f"&typeNames={CAPA}&outputFormat=application/json"
    f"&srsName=EPSG:4326&CQL_FILTER=nombre%3D%27Embalse%20de%20Arenal%27"
)

# 0.0002 grados, unos 22 m a esta latitud. Elegida midiendo, no a ojo: ver la
# tabla que imprime --medir y el apartado "Simplificacion" de la procedencia.
TOLERANCIA = 0.0002
LATITUD = 10.5
DECIMALES = 5
VERTICES_MINIMOS = 4


def metros(grados: float) -> float:
    return grados * 111320 * math.cos(math.radians(LATITUD))


def _douglas_peucker(puntos: list[list[float]], tolerancia: float) -> list[list[float]]:
    if len(puntos) < 3:
        return puntos[:]
    guardar = [False] * len(puntos)
    guardar[0] = guardar[-1] = True
    pila = [(0, len(puntos) - 1)]
    while pila:
        i, j = pila.pop()
        ax, ay = puntos[i]
        bx, by = puntos[j]
        dx, dy = bx - ax, by - ay
        norma = math.hypot(dx, dy)
        peor, corte = -1.0, -1
        for m in range(i + 1, j):
            px, py = puntos[m]
            if norma == 0:
                distancia = math.hypot(px - ax, py - ay)
            else:
                distancia = abs(dy * px - dx * py + bx * ay - by * ax) / norma
            if distancia > peor:
                peor, corte = distancia, m
        if peor > tolerancia and corte != -1:
            guardar[corte] = True
            pila.append((i, corte))
            pila.append((corte, j))
    return [punto for punto, sigue in zip(puntos, guardar, strict=True) if sigue]


def simplificar(anillos: list, tolerancia: float) -> list:
    """Simplifica cada anillo y descarta los que dejan de ser un poligono.

    Un anillo tiene que cerrar, asi que si Douglas-Peucker le quito el punto
    final se vuelve a poner. Los que quedan con menos de cuatro vertices son
    islas que a la escala del canton no ocupan ni un pixel.
    """
    salida = []
    for anillo in anillos:
        simple = _douglas_peucker(anillo, tolerancia)
        if simple[0] != simple[-1]:
            simple = [*simple, simple[0]]
        if len(simple) >= VERTICES_MINIMOS:
            salida.append([[round(x, DECIMALES), round(y, DECIMALES)] for x, y in simple])
    return salida


def descargar() -> bytes:
    print(f"Descargando de {SERVICIO} ...")
    with urllib.request.urlopen(PETICION, timeout=120) as respuesta:  # noqa: S310
        return respuesta.read()


def tabla_de_tolerancias(anillos: list) -> None:
    original = sum(len(anillo) for anillo in anillos)
    print(f"\noriginal: {len(anillos)} anillos, {original:,} vertices\n")
    print(f"{'tolerancia':>12} {'metros':>7} {'anillos':>8} {'vertices':>9} {'reduccion':>10}")
    for tolerancia in (0.00005, 0.0001, 0.0002, 0.0003, 0.0005, 0.001):
        simple = simplificar(anillos, tolerancia)
        vertices = sum(len(anillo) for anillo in simple)
        print(
            f"{tolerancia:>12.5f} {metros(tolerancia):>7.0f} {len(simple):>8} "
            f"{vertices:>9,} {100 - 100 * vertices / original:>9.1f}%"
        )


def escribir_procedencia(datos: dict) -> None:
    PROCEDENCIA.write_text(PLANTILLA.format(**datos), encoding="utf-8")


PLANTILLA = """# Procedencia del Lago Arenal

Generado por `frontend/herramientas/generar_lago.py` a partir de la descarga
cruda del SNIT. Historia H14.3. **Artefacto derivado: no editar a mano.**

## Descarga

| Dato | Valor |
|---|---|
| Fecha | {fecha} |
| Servicio | {servicio} |
| Capa | `{capa}` ("Cuerpos de Agua 1:25mil") |
| Filtro | `{filtro}` |
| Sistema de coordenadas pedido | EPSG:4326 |
| Entidades devueltas | 1 (`numberMatched: 1`) |

Es el **mismo servicio del SNIT** que H1.3 uso para los limites distritales, en su
espacio de trabajo de 1:25.000. Se descarto `IGN_5:hidrografia_5000` (1:5.000):
mas detalle del que la vista cantonal puede mostrar, y mas peso.

    {peticion}

**El servicio devuelve EPSG:5367 (CRTM05) si no se le pide otra cosa.** Sin
`srsName=EPSG:4326` las coordenadas salen en metros proyectados y Leaflet las
coloca en el Golfo de Guinea. Queda escrito porque no es evidente.

## Lo que dice la fuente

| Campo | Valor |
|---|---|
| `nombre` | {nombre} |
| `nom_objeto` | {nom_objeto} |
| `codigo` | {codigo} |
| `area` | {area:,.0f} m2 ({area_km:.1f} km2) |
| `perimetro` | {perimetro:,.0f} m |
| `origen` | {origen} |

El nombre oficial es **Embalse de Arenal**. En el visor se muestra como **Lago
Arenal**, que es como lo nombra la gente del canton; el oficial queda en
`nombre_oficial` para que la fuente se pueda rastrear.

## Simplificacion

Douglas-Peucker con tolerancia **{tolerancia}** grados, unos **{tolerancia_m:.0f} m**
a esta latitud.

| | Anillos | Vertices | Bytes |
|---|---|---|---|
| Original | {anillos_orig} | {vertices_orig:,} | {bytes_orig:,} |
| Publicado | {anillos_pub} | {vertices_pub:,} | {bytes_pub:,} |

Reduccion del {reduccion:.1f} % de los vertices. La tolerancia se eligio
**midiendo, no a ojo**: a la escala a la que el visor muestra el canton -unos
50 m por pixel en escritorio y 106 en telefono- {tolerancia_m:.0f} m es menos de
medio pixel, y a ocho veces ese acercamiento la linea simplificada sigue pegada
a la original. Con 55 m, en cambio, las ensenadas se cortan en linea recta y se
nota. La tabla completa la imprime este mismo guion con `--medir`, y la
comparacion visual esta en la evidencia de la historia.

Los {anillos_perdidos} anillos que se pierden son islas de menos de cuatro
vertices tras simplificar: a esta escala no ocupan ni un pixel.

## Sumas de verificacion

    crudo      sha256  {sha_crudo}
    publicado  sha256  {sha_publicado}

## Licencia y uso

Datos del Sistema Nacional de Informacion Territorial (SNIT), Instituto
Geografico Nacional de Costa Rica. Uso academico. **El SNIT prohibe el uso
comercial**; si el proyecto cambiara de licencia, esta capa se sustituye por la
de OpenStreetMap (ODbL, con atribucion).
"""


def main() -> None:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("--crudo", type=Path, help="copia local de la respuesta del WFS")
    analizador.add_argument("--medir", action="store_true", help="solo la tabla de tolerancias")
    opciones = analizador.parse_args()

    bruto = opciones.crudo.read_bytes() if opciones.crudo else descargar()
    coleccion = json.loads(bruto)
    rasgo = coleccion["features"][0]
    propiedades = rasgo["properties"]
    anillos = rasgo["geometry"]["coordinates"]

    if opciones.medir:
        tabla_de_tolerancias(anillos)
        return

    simple = simplificar(anillos, TOLERANCIA)
    salida = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "nombre": "Lago Arenal",
                    "nombre_oficial": propiedades["nombre"],
                    "codigo": propiedades["codigo"],
                    "area_m2": propiedades["area"],
                    "fuente": f"{CAPA} (SNIT, Instituto Geografico Nacional)",
                },
                "geometry": {"type": "Polygon", "coordinates": simple},
            }
        ],
    }
    texto = json.dumps(salida, separators=(",", ":"), ensure_ascii=False)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(texto, encoding="utf-8")

    vertices_orig = sum(len(anillo) for anillo in anillos)
    vertices_pub = sum(len(anillo) for anillo in simple)
    escribir_procedencia(
        {
            "fecha": datetime.date.today().isoformat(),
            "servicio": SERVICIO,
            "capa": CAPA,
            "filtro": FILTRO,
            "peticion": PETICION,
            "nombre": propiedades["nombre"],
            "nom_objeto": propiedades["nom_objeto"],
            "codigo": propiedades["codigo"],
            "area": propiedades["area"],
            "area_km": propiedades["area"] / 1e6,
            "perimetro": propiedades["perimetro"],
            "origen": propiedades["origen"],
            "tolerancia": TOLERANCIA,
            "tolerancia_m": metros(TOLERANCIA),
            "anillos_orig": len(anillos),
            "vertices_orig": vertices_orig,
            "bytes_orig": len(bruto),
            "anillos_pub": len(simple),
            "vertices_pub": vertices_pub,
            "bytes_pub": len(texto.encode("utf-8")),
            "reduccion": 100 - 100 * vertices_pub / vertices_orig,
            "anillos_perdidos": len(anillos) - len(simple),
            "sha_crudo": hashlib.sha256(bruto).hexdigest(),
            "sha_publicado": hashlib.sha256(texto.encode("utf-8")).hexdigest(),
        }
    )
    print(f"escrito {DESTINO.relative_to(RAIZ)}: {len(texto):,} bytes, {vertices_pub:,} vertices")
    print(f"escrito {PROCEDENCIA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
