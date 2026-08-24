"""Comprueba los criterios de aceptacion de H11.5, el visor publicado.

POR QUE EXISTE

GitHub Pages sirve el visor en `https://<usuario>.github.io/geoguardian/`, un
**subdirectorio**. Toda ruta absoluta de raiz se rompe ahi, y se rompe **en
silencio**: el archivo se pide, devuelve 404, y el visor se queda sin datos sin
mostrar ningun error.

En el sitio publicado eso es peor que en local, porque **el respaldo estatico es
el unico origen que existe**: no hay API a la que caer.

Medido antes de arreglarlo, sirviendo el `dist` desde un subdirectorio:

    /geoguardian/            ->  200
    /simulados/salud.json    ->  404   <- lo que el bundle pedia

QUE COMPRUEBA, Y SOBRE QUE

Sobre el **artefacto construido**, no sobre el codigo fuente. Es deliberado: en
`cliente.js` la ruta se ve bien; el defecto solo aparece en el bundle y solo
importa al servirlo desde otro sitio. Comprobar el fuente daria verde con el
defecto puesto.

    CA-1  index.html no referencia nada con ruta absoluta de raiz
    CA-2  el bundle no pide /simulados/... absoluto, y el respaldo existe
    CA-3  la ruta de la API queda intacta, para que falle y se caiga al respaldo
    CA-5  el despliegue es un job del ci.yml, no un servicio externo
    CA-6  solo se publica desde main
    CA-7  el visor declara que los datos son simulados

CA-4 -que `npm run dev` siga sirviendo en la raiz- no se comprueba aqui: es una
propiedad del servidor de desarrollo y se verifica levantandolo.

Uso:
    python docs/herramientas/verificar_h115.py --dist frontend/dist

Sale con codigo 1 si algo no se cumple, para poder correrlo en CI.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

fallos: list[str] = []


def comprobar(descripcion: str, condicion: bool, detalle: str = "") -> None:
    print(f"  {'OK  ' if condicion else 'FALLO'}  {descripcion}")
    if not condicion:
        fallos.append(descripcion)
        if detalle:
            print(f"        {detalle}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dist", type=Path, default=RAIZ / "frontend" / "dist")
    args = p.parse_args()

    dist = args.dist if args.dist.is_absolute() else RAIZ / args.dist

    print("\nCriterios de aceptacion de H11.5\n")

    if not dist.is_dir():
        print(f"  No existe {dist}. Hay que construir primero:\n")
        print("      cd frontend && npm run build\n")
        return 1

    # ---------------------------------------------------------------- CA-1 -- #
    print("CA-1, el visor carga desde un subdirectorio:")

    indice = dist / "index.html"
    comprobar("existe index.html en el dist", indice.exists())
    if not indice.exists():
        return 1

    html = indice.read_text(encoding="utf-8")
    referencias = re.findall(r'(?:src|href)="([^"]+)"', html)
    absolutas = [r for r in referencias if r.startswith("/")]

    comprobar(
        "index.html no referencia nada con ruta absoluta de raiz",
        not absolutas,
        f"absolutas encontradas: {absolutas}. Falta `base` en vite.config.js",
    )
    comprobar("index.html referencia algo", bool(referencias))

    # Cada referencia relativa tiene que existir de verdad dentro del dist.
    faltantes = [
        r
        for r in referencias
        if not r.startswith(("http", "//")) and not (dist / r.lstrip("./")).exists()
    ]
    comprobar(
        "cada archivo que index.html referencia existe en el dist",
        not faltantes,
        f"no estan: {faltantes}",
    )

    # ---------------------------------------------------------------- CA-2 -- #
    print("\nCA-2, el respaldo estatico se encuentra:")

    bundles = sorted((dist / "assets").glob("*.js")) if (dist / "assets").is_dir() else []
    comprobar("hay al menos un bundle de JavaScript", bool(bundles))

    codigo = "\n".join(b.read_text(encoding="utf-8", errors="replace") for b in bundles)

    # El defecto exacto: la cadena '/simulados/...' escrita como absoluta. Se
    # busca con la comilla o la comilla invertida delante, para no confundirla
    # con `${BASE}simulados/...`, que es la forma correcta.
    absolutas_respaldo = re.findall(r"""["'`]/simulados/[^"'`]*""", codigo)
    comprobar(
        "el bundle no pide /simulados/ con ruta absoluta de raiz",
        not absolutas_respaldo,
        f"encontrado: {sorted(set(absolutas_respaldo))}. "
        "Tienen que colgar de import.meta.env.BASE_URL",
    )
    comprobar(
        "el bundle si menciona el respaldo, o sea que sigue existiendo",
        "simulados/salud.json" in codigo,
        "si no aparece, alguien quito la degradacion de D-23",
    )

    for nombre in (
        "salud.json",
        "distritos.geojson",
        "riesgos-sequia.json",
        "riesgos-incendio.json",
        "riesgos-lluvia_intensa.json",
    ):
        comprobar(f"el dist trae simulados/{nombre}", (dist / "simulados" / nombre).exists())

    salud = dist / "simulados" / "salud.json"
    if salud.exists():
        modo = json.loads(salud.read_text(encoding="utf-8")).get("modo")
        comprobar("el respaldo declara modo simulado", modo == "simulado", f"dice {modo!r}")

    # ---------------------------------------------------------------- CA-3 -- #
    print("\nCA-3, la llamada a la API falla y el visor cae al respaldo:")

    comprobar(
        "la ruta de la API sigue siendo absoluta de raiz",
        '"/api"' in codigo or "`/api`" in codigo or "'/api'" in codigo,
        "es lo correcto: en el sitio publicado /api no existe, devuelve 404 y "
        "negociar() cae al respaldo. Si colgara de BASE_URL seguiria sin existir, "
        "pero la intencion quedaria confusa",
    )

    # ---------------------------------------------------------- CA-5 y CA-6 -- #
    print("\nCA-5 y CA-6, el despliegue vive en el repositorio y solo sale de main:")

    flujo = (RAIZ / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    comprobar("el ci.yml tiene el trabajo publicar-visor", "publicar-visor:" in flujo)
    comprobar(
        "solo publica desde main",
        "github.ref == 'refs/heads/main'" in flujo,
        "sin esa condicion, cualquier PR a medio revisar queda en la URL publica",
    )
    comprobar("usa deploy-pages, no un servicio externo", "actions/deploy-pages" in flujo)
    comprobar(
        "el despliegue espera a que el frontend y la gestion esten en verde",
        "needs: [frontend, gestion]" in flujo,
    )

    # ---------------------------------------------------------------- CA-7 -- #
    print("\nCA-7, el sitio declara que los datos son simulados:")

    comprobar(
        "el bundle trae el aviso de datos simulados",
        "simulad" in codigo.lower(),
        "es una pagina publica de riesgo climatico: si no dice que los numeros "
        "son inventados, es un problema serio",
    )

    if fallos:
        print(f"\n{len(fallos)} criterios fallaron:\n")
        for f in fallos:
            print(f"  - {f}")
        print()
        return 1

    print("\nLos criterios de H11.5 se cumplen.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
