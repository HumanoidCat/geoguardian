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
    gh issue list --state all --limit 300 --json number,title,state,stateReason > issues.json
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
    # `utf-8-sig` y no `utf-8`: en PowerShell, redirigir la salida de `gh` a un
    # archivo escribe una marca BOM al principio, y `json.loads` revienta con
    # `Unexpected UTF-8 BOM`. En Linux no aparece, asi que el CI pasaba en verde
    # y este control no corria en ninguna maquina del equipo. `utf-8-sig` lee
    # bien los dos casos: si no hay BOM, se comporta igual que `utf-8`.
    #
    # Reportado por Avril el 2026-09-02. Es el mismo defecto que ya tenia
    # backlog.csv veinte lineas mas arriba, y la cuarta vez que aparece en el
    # proyecto: ver la incidencia sobre controles que solo corren en el CI.
    datos = json.loads(ruta.read_text(encoding="utf-8-sig"))
    por_historia: dict[str, list[dict]] = {}
    sin_historia: list[dict] = []

    for issue in datos:
        encontrado = PATRON_TITULO.match(issue.get("title", ""))
        if encontrado:
            por_historia.setdefault(encontrado.group(1), []).append(issue)
        else:
            sin_historia.append(issue)

    return por_historia, sin_historia


RAMAS_CON_SENTIDO = ("dev", "main")


def rama_actual() -> str | None:
    """La rama del arbol de trabajo, o del CI si corre alli."""
    import os
    import subprocess

    # En GitHub Actions el checkout puede quedar en HEAD suelto, asi que el
    # nombre viene por variable de entorno.
    if desde_el_ci := os.environ.get("GITHUB_REF_NAME"):
        return desde_el_ci

    try:
        salida = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=RAIZ,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return salida.stdout.strip() or None if salida.returncode == 0 else None


def main() -> int:
    p = argparse.ArgumentParser(description="Cruza el tablero de GitHub con el repositorio.")
    p.add_argument("--issues", type=Path, required=True, help="volcado de `gh issue list --json`")
    p.add_argument(
        "--comandos",
        action="store_true",
        help="imprime los `gh issue close` que hacen falta, listos para pegar",
    )
    p.add_argument(
        "--sin-importar-la-rama",
        action="store_true",
        help="corre igual desde una rama de trabajo, sabiendo que el resultado no vale",
    )
    p.add_argument(
        "--corregir",
        action="store_true",
        help=(
            "cierra por `gh` las issues de historias ya marcadas [x], en vez de "
            "solo reclamarlas. Las otras tres discrepancias se siguen reportando."
        ),
    )
    args = p.parse_args()

    # ----------------------------------------------------------------------- #
    # De que rama se lee el avance, y por que importa
    # ----------------------------------------------------------------------- #
    #
    # Las historias cerradas se leen de `docs/tareas/` DEL ARBOL DE TRABAJO. El
    # tablero, en cambio, es uno solo para todo el repositorio. Cruzar los dos
    # solo tiene sentido si el arbol esta al dia.
    #
    # Corrido desde una rama de trabajo el resultado no es neutro: es un VERDE
    # FALSO. Una historia que ya se cerro en `dev` figura sin marcar en la rama
    # vieja, asi que el verificador no reclama que su issue siga abierta.
    #
    # Paso el 25 de agosto: parado en una rama anterior a H1.2, dijo "el tablero
    # coincide con el repositorio" mientras la issue #36 seguia abierta con la
    # historia cerrada. Desde `dev` salio en rojo de inmediato.
    #
    # Un control que da verde cuando deberia dar rojo es peor que no tenerlo,
    # porque genera confianza. Por eso se planta en vez de advertir.
    rama = rama_actual()
    if rama and rama not in RAMAS_CON_SENTIDO and not args.sin_importar_la_rama:
        print(f"\nEstas en la rama `{rama}`, y este verificador solo dice la verdad")
        print("desde `dev` o `main`.\n")
        print("El avance se lee de docs/tareas/ del arbol de trabajo, y el tablero")
        print("es uno solo. Desde una rama atrasada, una historia ya cerrada figura")
        print("sin marcar y el verificador NO reclama su issue abierta: da verde")
        print("cuando deberia dar rojo.\n")
        print("    git checkout dev && git pull\n")
        print("Si sabes lo que haces y aun asi lo queres correr:\n")
        print("    --sin-importar-la-rama\n")
        return 1

    ruta = args.issues if args.issues.is_absolute() else Path.cwd() / args.issues
    if not ruta.exists():
        print(f"\nNo existe {ruta}. Se genera con:\n")
        print(
            "    gh issue list --state all --limit 300 --json number,title,state,stateReason > issues.json\n"
        )
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
    #
    #    SALVO que se haya cerrado como NOT_PLANNED, que es como GitHub marca
    #    "duplicada", "no se va a hacer" o "se abrio por error". Esa distincion
    #    la aporta `stateReason` y hay que pedirla en el volcado.
    #
    #    Se agrego el 24 de agosto: al deduplicar las dos issues de H6.0 -habia
    #    una abierta y otra cerrada para la misma historia- cerrar la sobrante
    #    dejaba una "cerrada sin historia marcada" que no era un defecto sino la
    #    limpieza misma. El verificador acusaba el arreglo.
    for identificador, issues in sorted(por_historia.items()):
        if identificador in cerradas or identificador not in backlog:
            continue
        for issue in issues:
            if issue.get("state", "").upper() != "CLOSED":
                continue
            if (issue.get("stateReason") or "").upper() == "NOT_PLANNED":
                continue
            problemas.append(
                f"la issue #{issue['number']} de {identificador} esta cerrada "
                "y la historia no esta marcada [x] en docs/tareas/"
            )

    # 3. Historias sin issue.
    sin_issue = sorted(h for h in backlog if h not in por_historia)
    for identificador in sin_issue:
        problemas.append(f"{identificador} esta en el backlog y no tiene issue en el tablero")

    # 4. Duplicadas. Una descartada como NOT_PLANNED ya no cuenta: es
    #    precisamente como se resuelve una duplicacion.
    for identificador, issues in sorted(por_historia.items()):
        vigentes = [i for i in issues if (i.get("stateReason") or "").upper() != "NOT_PLANNED"]
        if len(vigentes) > 1:
            numeros = ", ".join(f"#{i['number']}" for i in vigentes)
            problemas.append(
                f"{identificador} tiene mas de una issue vigente: {numeros}. "
                "La sobrante se cierra con `--reason 'not planned'`"
            )

    # ----------------------------------------------------------------------- #

    print("\nEl tablero de GitHub contra el repositorio")
    print(f"  rama leida             : {rama or 'no se pudo determinar'}\n")

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

    # ----------------------------------------------------------------------- #
    # Corregir en vez de reclamar
    # ----------------------------------------------------------------------- #
    #
    # SOLO ESTA DISCREPANCIA SE CORRIGE SOLA, Y HAY UNA RAZON
    #
    # "Historia marcada [x], issue abierta" es la unica de las cuatro donde el
    # arreglo correcto no admite duda: **manda `docs/tareas/`**, y eso ya esta
    # decidido en `docs/15-cerrar-una-historia.md`. Cerrar la issue no decide
    # nada, ejecuta una decision tomada.
    #
    # Las otras tres siguen fallando y esperando a una persona:
    #
    #   - issue cerrada sin historia marcada  -> el tablero adelanta al repo, y
    #                                            marcarla seria hacer mentir a la
    #                                            fuente de verdad
    #   - historia sin issue                  -> hay que redactarle un cuerpo
    #   - dos issues para la misma historia   -> hay que elegir cual sobra
    #
    # POR QUE EXISTE ESTO
    #
    # Con `Closes #N` inerte en `dev` -GitHub solo cierra al fusionar a la rama
    # por omision- **toda fusion de una historia a `dev` dejaba el CI en rojo
    # hasta que alguien se acordaba de cerrar la issue a mano**. Y no habia orden
    # que lo evitara: cerrar antes de fusionar dispara la discrepancia contraria.
    #
    # Paso con #165, con #170, y le iba a pasar a cada persona del equipo esta
    # semana. Un control que exige un ritual manual despues de cada merge no se
    # cumple: se desactiva mentalmente, y entonces deja de avisar cuando importa.
    if args.corregir and hay_que_cerrar:
        import subprocess

        print(f"\n  {len(hay_que_cerrar)} issues por cerrar. Cerrandolas:\n")
        for identificador, issue in hay_que_cerrar:
            motivo = (
                f"Cerrada automaticamente al fusionar {identificador} a `dev`.\n\n"
                "La historia esta marcada [x] en `docs/tareas/`, que es la fuente de "
                "verdad del avance segun `docs/15-cerrar-una-historia.md`.\n\n"
                "Se cierra desde el CI porque `Closes #N` solo dispara al fusionar a "
                "`main`, y entre un merge a `dev` y el siguiente el tablero mostraba "
                "abiertas historias ya cerradas."
            )
            try:
                r = subprocess.run(
                    ["gh", "issue", "close", str(issue["number"]), "--comment", motivo],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except FileNotFoundError:
                # Pasa corriendolo a mano en una maquina sin `gh`. En el runner
                # viene instalado. Se dice y se sigue reclamando, que es el
                # comportamiento de antes: nunca se traga la discrepancia.
                print("    `gh` no esta instalado. Las discrepancias se reportan sin corregir.")
                print("    Instalarlo desde https://cli.github.com o usar --comandos.\n")
                break
            except subprocess.SubprocessError as error:
                print(f"    #{issue['number']:<5} {identificador:8} FALLO: {error}")
                continue

            estado = "cerrada" if r.returncode == 0 else f"FALLO: {r.stderr.strip()[:60]}"
            print(f"    #{issue['number']:<5} {identificador:8} {estado}")
            if r.returncode == 0:
                problemas.remove(
                    f"{identificador} esta marcada [x] y su issue #{issue['number']} sigue abierta"
                )

    elif args.comandos and hay_que_cerrar:
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
