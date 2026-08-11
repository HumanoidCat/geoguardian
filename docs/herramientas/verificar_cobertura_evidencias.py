"""Comprueba que toda historia del backlog tenga carpeta de evidencia destino.

Lee el mapa rubrica -> carpeta desde la tabla de docs/evidencias/README.md, lo
cruza contra las etiquetas de cada historia del backlog y reporta las que
quedarian sin destino. Una historia sin destino no puede cumplir el paso de la
Definition of Done que exige archivar evidencia.

Uso:
    python docs/herramientas/verificar_cobertura_evidencias.py <ruta-a-issues.csv>

El backlog vive en gestion/issues.csv, fuera de este repositorio, por eso la
ruta se pasa como argumento.

Sale con codigo 1 si alguna historia queda sin carpeta destino.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path


def leer_mapa(readme: Path) -> dict[str, str]:
    """Extrae rubrica -> carpeta de la tabla del indice.

    Acepta rangos escritos como 'CG-1 a CG-6' y listas separadas por coma.
    """
    mapa: dict[str, str] = {}
    for linea in readme.read_text(encoding="utf-8").splitlines():
        celdas = [c.strip() for c in linea.split("|")[1:-1]]
        if len(celdas) != 2:
            continue
        rubricas, carpeta = celdas
        carpeta = carpeta.strip("`/")
        if carpeta in ("Carpeta", "---") or not carpeta:
            continue

        rango = re.fullmatch(r"([A-Z]+)-(\d+) a [A-Z]+-(\d+)", rubricas)
        if rango:
            prefijo, desde, hasta = rango.groups()
            for n in range(int(desde), int(hasta) + 1):
                mapa[f"{prefijo}-{n}"] = carpeta
            continue

        for rubrica in (r.strip() for r in rubricas.split(",")):
            if rubrica:
                mapa[rubrica] = carpeta
    return mapa


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1

    raiz = Path(__file__).resolve().parents[2]
    readme = raiz / "docs" / "evidencias" / "README.md"
    csv_backlog = Path(sys.argv[1])

    for archivo in (readme, csv_backlog):
        if not archivo.exists():
            print(f"No se encuentra {archivo}")
            return 1

    mapa = leer_mapa(readme)
    print(f"Rubricas mapeadas en el indice: {len(mapa)}")

    carpetas_reales = {p.name for p in (raiz / "docs" / "evidencias").iterdir() if p.is_dir()}
    huerfanas = sorted(set(mapa.values()) - carpetas_reales)
    if huerfanas:
        print(f"FALLO: el indice apunta a carpetas que no existen: {huerfanas}")
        return 1

    conteo: Counter[str] = Counter()
    sin_destino: list[str] = []

    with csv_backlog.open(encoding="utf-8-sig") as f:
        for fila in csv.DictReader(f):
            etiquetas = [e.strip() for e in fila["etiquetas"].split(",")]
            destino = next((mapa[e] for e in etiquetas if e in mapa), None)
            if destino is None:
                sin_destino.append(fila["id"])
            else:
                conteo[destino] += 1

    total = sum(conteo.values()) + len(sin_destino)
    print(f"historias totales: {total}")
    for carpeta, n in sorted(conteo.items()):
        print(f"  {carpeta:24s} {n:3d}")
    print(f"historias sin carpeta destino: {len(sin_destino)} {sin_destino}")

    if sin_destino:
        print("\nFALLO: hay historias que no pueden archivar evidencia.")
        return 1

    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
