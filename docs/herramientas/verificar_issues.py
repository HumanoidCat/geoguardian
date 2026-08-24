"""Comprueba que el tablero de GitHub diga lo mismo que el repositorio.

POR QUE EXISTE

`verificar_estado.py` declara explicitamente que **no** comprueba las issues:

    QUE NO COMPRUEBA
    Las issues de GitHub, que viven fuera del repositorio. Se cierran solas al
    mergear el Pull Request que las enlaza con `Closes #N`.

Esa suposicion es falsa en la practica. `docs/plantillas/como-llenar-el-pr.md`
ya advertia el modo de fallo:

    | "Cierra H10.1" en vez de `Closes #23` | La issue queda abierta y el tablero miente |

**La convencion estaba escrita y nada la comprobaba.** El resultado es el mismo
que produjo la auditoria del 18 de agosto en la matriz: tres lugares que declaran
el avance y ninguna maquina que los cruce. El tablero es el unico que quedaba sin
vigilar, y es justo el que mira quien no lee el repositorio.

POR QUE NO CONSULTA GITHUB DIRECTAMENTE

Recibe un **volcado** en JSON en vez de llamar a la API. Tres razones:

  1. Se puede correr sin red y sin credenciales, asi que se puede probar.
  2. En el CI, `gh` ya viene autenticado con GITHUB_TOKEN.
  3. El volcado queda como evidencia de que dice quien lo genero.

QUE COMPRUEBA

  1. Toda historia marcada [x] tiene su issue CERRADA.
  2. Toda issue cerrada corresponde a una historia marcada [x].
  3. Toda historia del backlog tiene issue.
  4. No hay dos issues para la misma historia.

QUE NO COMPRUEBA

Que el trabajo este bien hecho, ni las columnas del tablero de proyecto, que la
API de issues no expone.

Uso:
    gh issue list --state all --limit 300 --json number,title,state > issues.json
    python docs/herramientas/verificar_issues.py --issues issues.json

    # y para que imprima los comandos de cierre en vez de solo quejarse:
    python docs/herramientas/verificar_issues.py --issues issues.json --comandos

Sale con codigo 1 si el tablero y el repositorio no coinciden.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

PERSONAS = ("alejandro", "cesar", "luna", "avril")

# Misma expresion que verificar_estado.py: la linea de tarea real empieza en la
# columna cero, para no contar el ejemplo indentado del bloque de instrucciones.
PATRON_CERRADA = re.compile(r"^- \[x\] \*\*(H[0-9.]+[a-z]?)\*\*", re.M)

# El identificador dentro del titulo de la issue. Se ancla al principio porque
# los titulos se generaron como "H1.9 Funciones PL/pgSQL...".
PATRON_TITULO = re.compile(r"^\s*(H\d[\d.]*[a-z]?)\b")


def historias_del_backlog() -> set[str]:
    with (RAIZ / "docs" / "backlog.csv").open(encoding="utf-8-sig") as archivo:
        return {fila["id"] for fila in csv.DictReader(archivo)}


def historias_cerradas() -> set[str]:
    cerradas: set[str] = set()
    for persona in PERSONAS:
        texto = (RAIZ / "docs" / "tareas" / f"{persona}.md").read_text(encoding="utf-8")
        cerradas.update(PATRON_CERRADA.findall(texto))
    return cerradas


def leer_issues(ruta: Path) -> tuple[dict[str, list[dict]], list[dict]]:
    """Identificador -> issues, y las que no declaran ninguno."""
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    por_historia: dict[str, list[dict]] = {}
    sin_historia: list[dict] = []

    for issue in datos:
        encontrado = PATRON_TITULO.match(issue.get("title", ""))
        if encontrado:
            por_historia.setdefault(encontrado.group(1), []).append(issue)
        else:
            sin_historia.append(issue)

    return por_historia, sin_historia


def main() -> int:
    p = argparse.ArgumentParser(description="Cruza el tablero de GitHub con el repositorio.")
    p.add_argument("--issues", type=Path, required=True, help="volcado de `gh issue list --json`")
    p.add_argument(
        "--comandos",
        action="store_true",
        help="imprime los `gh issue close` que hacen falta, listos para pegar",
    )
    args = p.parse_args()

    ruta = args.issues if args.issues.is_absolute() else Path.cwd() / args.issues
    if not ruta.exists():
        print(f"\nNo existe {ruta}. Se genera con:\n")
        print("    gh issue list --state all --limit 300 --json number,title,state > issues.json\n")
        return 1

    backlog = historias_del_backlog()
    cerradas = historias_cerradas()
    por_historia, sin_historia = leer_issues(ruta)

    problemas: list[str] = []
    hay_que_cerrar: list[tuple[str, dict]] = []

    # 1. Historia cerrada, issue abierta. Es el caso frecuente y el que hace
    #    mentir al tablero.
    for identificador in sorted(cerradas):
        for issue in por_historia.get(identificador, []):
            if issue.get("state", "").upper() == "OPEN":
                hay_que_cerrar.append((identificador, issue))
                problemas.append(
                    f"{identificador} esta marcada [x] y su issue #{issue['number']} sigue abierta"
                )

    # 2. Issue cerrada sin que la historia lo este. El tablero adelanta al
    #    repositorio, que es peor: alguien puede darla por hecha.
    for identificador, issues in sorted(por_historia.items()):
        if identificador in cerradas or identificador not in backlog:
            continue
        for issue in issues:
            if issue.get("state", "").upper() == "CLOSED":
                problemas.append(
                    f"la issue #{issue['number']} de {identificador} esta cerrada "
                    "y la historia no esta marcada [x] en docs/tareas/"
                )

    # 3. Historias sin issue.
    sin_issue = sorted(h for h in backlog if h not in por_historia)
    for identificador in sin_issue:
        problemas.append(f"{identificador} esta en el backlog y no tiene issue en el tablero")

    # 4. Duplicadas.
    for identificador, issues in sorted(por_historia.items()):
        if len(issues) > 1:
            numeros = ", ".join(f"#{i['number']}" for i in issues)
            problemas.append(f"{identificador} tiene mas de una issue: {numeros}")

    # ----------------------------------------------------------------------- #

    print("\nEl tablero de GitHub contra el repositorio\n")

    abiertas = sum(
        1 for lista in por_historia.values() for i in lista if i.get("state", "").upper() == "OPEN"
    )
    print(
        f"  issues leidas          : {sum(len(v) for v in por_historia.values()) + len(sin_historia)}"
    )
    print(f"  con historia declarada : {sum(len(v) for v in por_historia.values())}")
    print(f"  abiertas               : {abiertas}")
    print(f"  historias marcadas [x] : {len(cerradas)}")

    if sin_historia:
        print(f"\n  {len(sin_historia)} issues no declaran historia en el titulo, y se ignoran:")
        for issue in sin_historia[:5]:
            print(f"    #{issue['number']}  {issue.get('title', '')[:58]}")
        if len(sin_historia) > 5:
            print(f"    ... y {len(sin_historia) - 5} mas")

    if args.comandos and hay_que_cerrar:
        print(f"\n  {len(hay_que_cerrar)} issues por cerrar. Los comandos:\n")
        for identificador, issue in hay_que_cerrar:
            print(
                f'    gh issue close {issue["number"]} '
                f'--comment "Cerrada por {identificador}, marcada en docs/tareas/. '
                'El Pull Request no llevaba Closes #N."'
            )

    if problemas:
        print(f"\n{len(problemas)} discrepancias:\n")
        for problema in problemas:
            print(f"  - {problema}")
        print(
            "\nEl avance real es el de docs/tareas/. El tablero se corrige contra el,\n"
            "nunca al reves. Con --comandos salen los `gh issue close` listos."
        )
        return 1

    print("\nEl tablero coincide con el repositorio.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
