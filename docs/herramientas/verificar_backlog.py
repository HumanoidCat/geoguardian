"""Comprueba que el backlog sea internamente consistente.

Cruza cada historia contra las dependencias que declara y detecta lo que nadie
miro durante cuatro semanas:

  1. Dependencias hacia historias que no existen.
  2. Dependencias hacia sprints POSTERIORES, que son imposibles de cumplir.
  3. Dependencias circulares.
  4. Sprint declarado en el cuerpo distinto del de la columna.
  5. Historias que superan la capacidad comprometida por persona y sprint.

Ademas informa, sin marcar error, las dependencias cruzadas dentro del mismo
sprint entre personas distintas: no son defectos, pero son los puntos donde
alguien se queda esperando.

Uso:
    python docs/herramientas/verificar_backlog.py
    python docs/herramientas/verificar_backlog.py <ruta-a-un-csv>

Sin argumento usa docs/backlog.csv, que es la copia versionada del backlog.
Sale con codigo 1 si hay algun defecto. Corre en CI.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

ORDEN = {"S0": 0, "S1": 1, "S2": 2, "S3": 3, "S4": 4}
SEMANAS = {"S0": "2-3", "S1": "4-5", "S2": "6-7", "S3": "8-9", "S4": "10-11"}
HORAS_POR_PERSONA_POR_SPRINT = 36.0  # 18 h/semana x 2 semanas


def dependencias(cuerpo: str) -> list[str]:
    m = re.search(r"Depende de:\s*(.+)", cuerpo)
    if not m:
        return []
    return [x.strip() for x in re.split(r"[,y]+", m.group(1)) if re.match(r"^H\d", x.strip())]


def ciclos(grafo: dict[str, list[str]]) -> list[list[str]]:
    encontrados: list[list[str]] = []
    estado: dict[str, int] = {}

    def visitar(n: str, camino: list[str]) -> None:
        estado[n] = 1
        for m in grafo.get(n, []):
            if estado.get(m) == 1:
                encontrados.append([*camino[camino.index(m) :], n, m])
            elif estado.get(m, 0) == 0:
                visitar(m, [*camino, m])
        estado[n] = 2

    for n in grafo:
        if estado.get(n, 0) == 0:
            visitar(n, [n])
    return encontrados


def main() -> int:
    if len(sys.argv) == 2:
        ruta = Path(sys.argv[1])
    elif len(sys.argv) == 1:
        ruta = Path(__file__).resolve().parents[1] / "backlog.csv"
    else:
        print(__doc__)
        return 1
    if not ruta.exists():
        print(f"No se encuentra {ruta}")
        return 1

    with ruta.open(encoding="utf-8-sig") as f:
        filas = list(csv.DictReader(f))
    H = {r["id"]: r for r in filas}
    print(f"Historias en el backlog: {len(filas)}\n")

    defectos: list[str] = []

    # 1, 2 y 4
    grafo: dict[str, list[str]] = {}
    for r in filas:
        deps = dependencias(r["cuerpo"])
        grafo[r["id"]] = [d for d in deps if d in H]

        m = re.search(r"Sprint:\s*(S\d)", r["cuerpo"])
        if m and m.group(1) != r["sprint"]:
            defectos.append(
                f"{r['id']}: la columna dice {r['sprint']} y el cuerpo dice {m.group(1)}"
            )

        for d in deps:
            if d not in H:
                defectos.append(f"{r['id']}: depende de {d}, que no existe en el backlog")
            elif ORDEN[H[d]["sprint"]] > ORDEN[r["sprint"]]:
                defectos.append(
                    f"{r['id']} ({r['sprint']}) depende de {d}, que esta en "
                    f"{H[d]['sprint']}: imposible de cumplir"
                )

    # 3
    for c in ciclos(grafo):
        defectos.append("dependencia circular: " + " -> ".join(c))

    # 5
    carga: dict[tuple[str, str], float] = defaultdict(float)
    for r in filas:
        carga[(r["responsable"], r["sprint"])] += float(r["horas"])
    excesos = {k: v for k, v in carga.items() if v > HORAS_POR_PERSONA_POR_SPRINT}

    if defectos:
        print(f"DEFECTOS: {len(defectos)}")
        for d in defectos:
            print(f"  - {d}")
    else:
        print("Sin defectos de dependencia.")

    print("\nCarga por persona y sprint (limite comprometido: 36 h):")
    personas = sorted({r["responsable"] for r in filas})
    print("           " + "".join(f"{s:>9s}" for s in ORDEN))
    for p in personas:
        fila = "".join(
            f"{carga[(p, s)]:>8.1f}{'*' if carga[(p, s)] > HORAS_POR_PERSONA_POR_SPRINT else ' '}"
            for s in ORDEN
        )
        print(f"  {p:9s}{fila}")
    if excesos:
        print("\n  * por encima del compromiso de 18 h por semana:")
        for (p, s), v in sorted(excesos.items()):
            print(f"      {p} en {s}: {v:.1f} h, {v - HORAS_POR_PERSONA_POR_SPRINT:+.1f} h")

    # Informativo, no es defecto
    cruzadas = [
        (r["id"], r["responsable"], d, H[d]["responsable"], r["sprint"])
        for r in filas
        for d in dependencias(r["cuerpo"])
        if d in H and H[d]["sprint"] == r["sprint"] and H[d]["responsable"] != r["responsable"]
    ]
    print(f"\nDependencias cruzadas dentro del mismo sprint: {len(cruzadas)}")
    for h, rp, d, rd, s in cruzadas:
        print(f"  {s}  {h:8s} ({rp}) espera a {d:8s} ({rd})")

    if defectos:
        print("\nFALLO: el backlog tiene dependencias que no se pueden cumplir.")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
