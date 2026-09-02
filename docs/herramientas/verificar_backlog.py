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

    # Se cuenta aparte de `defectos` porque no es un defecto de dependencia y el
    # mensaje de abajo diria algo falso. Las dos cosas hacen fallar igual.
    tabla_desfasada = tabla_de_carga_coincide(filas)

    if defectos:
        print("\nFALLO: el backlog tiene dependencias que no se pueden cumplir.")
        return 1
    if tabla_desfasada:
        print("\nFALLO: las tablas de carga no coinciden con backlog.csv.")
        return 1
    print("\nOK")
    return 0


# --------------------------------------------------------------------------- #
# La tabla que leen las personas                                              #
# --------------------------------------------------------------------------- #
# `docs/08-backlog.md` publica la misma carga en una tabla, y es la que alguien
# abre cuando quiere saber quien tiene cuanto. Hasta el 2026-08-30 **nada la
# comprobaba**: este verificador lee `backlog.csv` y nunca miro el Markdown.
#
# Se desfaso. La fila de Cesar decia 158.6 h y 128 puntos cuando el CSV daba
# 161.5 y 131; la de Avril, 114.6 y 94 contra 117.5 y 97. Y la fila **Equipo**
# si estaba al dia -633.9 y 434-, o sea que la tabla **no cuadraba consigo
# misma**: las filas sumaban 628.1 h y 428 puntos.
#
# El mecanismo se deduce del sintoma: los totales se regeneraron desde el CSV y
# las filas por persona se dejaron a mano. Es el reparto lo que se desfasa,
# nunca el total, porque el total es lo unico que alguien recalcula.
#
# Importa mas que otras cifras porque esta tabla es con la que se discute quien
# esta sobrecargado. Una fila corta por tres puntos no se nota y cambia la
# conversacion.
PATRON_FILA = re.compile(r"^\| (Alejandro|Cesar|Luna|Avril) \|(.+?)\| ([\d.]+) \| (\d+) \|$", re.M)


def tabla_de_carga_coincide(filas: list[dict]) -> int:
    ruta = Path(__file__).resolve().parents[1] / "08-backlog.md"
    if not ruta.exists():
        return 0

    puntos: dict[str, float] = defaultdict(float)
    totales: dict[str, float] = defaultdict(float)
    for fila in filas:
        puntos[fila["responsable"]] += float(fila["puntos"])
        totales[fila["responsable"]] += float(fila["horas"])

    encontradas = PATRON_FILA.findall(ruta.read_text(encoding="utf-8"))
    if not encontradas:
        print("\nLa tabla de carga de 08-backlog.md no se pudo leer: cambio el formato.")
        return 1

    malas = []
    for nombre, _, total, pts in encontradas:
        clave = nombre.lower()
        if abs(float(total) - totales[clave]) > 0.05 or int(pts) != round(puntos[clave]):
            malas.append(
                f"  - {nombre}: la tabla dice {total} h y {pts} pts; "
                f"el CSV da {totales[clave]:.1f} h y {puntos[clave]:.0f} pts"
            )

    # --------------------------------------------------------------------- #
    # Y LOS ARCHIVOS DE TAREAS, QUE TAMPOCO TENIAN NADA MIRANDO              #
    # --------------------------------------------------------------------- #
    # Lo encontro Cesar el 2026-09-01, revisando el PR #211. `cesar.md` decia
    # «125 puntos · 154 horas» cuando el CSV daba 96 y 124.2, y su tabla de
    # carga decia S3 39.2 h contra los 47.0 de la seccion. Dos causas distintas
    # y ninguna vigilada: los 7.8 h de H1.14, agregada por D-26 sin tocar la
    # tabla, y el traspaso de D-33, que actualizo los encabezados de sprint y no
    # el resumen de arriba.
    #
    # El control de mas arriba cruzaba el CSV contra `08-backlog.md` y se
    # detenia ahi. **Cada persona lee su propio archivo, no la tabla del
    # backlog**, asi que el numero que de verdad se mira era el unico sin
    # comprobar. Es el mismo defecto de I-16 en otro archivo: se vigilaba una de
    # las apariciones de la cifra.
    for persona in sorted(totales):
        ruta_persona = Path(__file__).resolve().parents[1] / "tareas" / f"{persona}.md"
        if not ruta_persona.exists():
            continue
        texto = ruta_persona.read_text(encoding="utf-8")
        declara = re.search(r"\*\*Total asignado:\*\* ([\d.]+) puntos · ([\d.]+) horas", texto)
        if not declara:
            malas.append(f"  - {persona}.md no declara su total asignado")
            continue
        if abs(float(declara.group(2)) - totales[persona]) > 0.05 or int(
            float(declara.group(1))
        ) != round(puntos[persona]):
            malas.append(
                f"  - tareas/{persona}.md dice {declara.group(1)} pts y "
                f"{declara.group(2)} h; el CSV da {puntos[persona]:.0f} y "
                f"{totales[persona]:.1f}"
            )
        for sprint, horas_md in re.findall(r"\| (S\d) \| semanas [\d-]+ \| ([\d.]+) \|", texto):
            real = sum(
                float(f["horas"])
                for f in filas
                if f["responsable"] == persona and f["sprint"] == sprint
            )
            if abs(float(horas_md) - real) > 0.05:
                malas.append(
                    f"  - tareas/{persona}.md, {sprint}: la tabla dice {horas_md} h "
                    f"y el CSV da {real:.1f}"
                )

    print(
        f"\nTabla de carga de 08-backlog.md y de docs/tareas/: {len(encontradas)} filas y 4 archivos"
    )
    if malas:
        print("  no coinciden con backlog.csv:")
        print("\n".join(malas))
        print("\n  El CSV es la fuente. Se corrige la tabla, nunca al reves.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
