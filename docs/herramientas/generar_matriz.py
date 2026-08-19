"""Genera docs/05-matriz-trazabilidad.md desde las fuentes que ya existen.

POR QUE EXISTE

La matriz era el archivo mas conflictivo del repositorio. La tocaban las cuatro
personas, casi siempre en el mismo bloque de filas, y **ninguna herramienta la
comprobaba**. En dos dias produjo:

    tres conflictos de fusion, todos en las filas de la epica E2
    tres duenos desfasados: H2.2, H2.3 y H8.2
    cuatro historias cerradas sin fila: H6.4, H8.5, H8.6 y H10.8

El defecto de los duenos no fue cosmetico: le quito trabajo del plato a una
persona durante un dia, porque leyo la matriz y dio por ajenas dos historias
suyas.

LA SOLUCION NO ES TENER MAS CUIDADO

La matriz **deja de escribirse a mano**. Pasa a generarse desde cuatro fuentes que
ya existen y que nadie comparte:

    docs/backlog.csv          dueno y rubrica de cada historia
    docs/tareas/<persona>.md  si esta cerrada. Cada quien edita solo la suya
    docs/trazabilidad.csv     requisito, modulo y prueba. Solo lo edita el PM
    docs/evidencias/          el archivo de evidencia, si existe en disco

Nadie mas vuelve a editar la matriz. Quien cierra una historia marca `[x]` en su
propio archivo y sube su evidencia; la fila aparece sola.

**Los conflictos que queden se resuelven regenerando**, no fusionando a mano:

    git checkout --ours docs/05-matriz-trazabilidad.md
    python docs/herramientas/generar_matriz.py

Es la misma idea que `ruff format`: un archivo derivado no se discute, se vuelve a
producir.

QUE COMPRUEBA verificar_estado.py

Que el archivo del repositorio sea identico al que produce esta herramienta. Si
alguien lo edita a mano, el CI lo detecta, igual que `ruff format --check`.

Uso:
    python docs/herramientas/generar_matriz.py            escribe el archivo
    python docs/herramientas/generar_matriz.py --revisar  solo informa si esta al dia
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

DESTINO = RAIZ / "docs" / "05-matriz-trazabilidad.md"
PERSONAS = ("alejandro", "cesar", "luna", "avril")

PATRON_CERRADA = re.compile(r"^- \[x\] \*\*(H[0-9.]+[a-z]?)\*\*", re.M)

ENCABEZADO = """# Matriz de trazabilidad

Liga cada requisito con el modulo que lo implementa, la prueba que lo verifica, la
metrica que lo demuestra y el criterio de rubrica al que responde.

> **Este archivo se genera. No se edita a mano.**
>
>     python docs/herramientas/generar_matriz.py
>
> Sale de `docs/backlog.csv` (dueno y rubrica), de `docs/tareas/<persona>.md` (si
> la historia esta cerrada), de `docs/trazabilidad.csv` (requisito, modulo y
> prueba) y de los archivos que existan en `docs/evidencias/`.
>
> Para cambiar una fila se cambia la fuente, no la tabla. Si aparece un conflicto
> de fusion aqui, se resuelve regenerando:
>
>     git checkout --ours docs/05-matriz-trazabilidad.md
>     python docs/herramientas/generar_matriz.py
>
> `docs/herramientas/verificar_estado.py` comprueba en el CI que la tabla
> corresponda a sus fuentes.

Estados: Pendiente · En progreso · Implementado · Verificado · Con evidencia

"""

PIE = """
Completar con el resto del backlog conforme entren al sprint: se agrega la fila a
`docs/trazabilidad.csv` y se regenera.
"""


def leer_csv(ruta: Path) -> list[dict[str, str]]:
    with ruta.open(encoding="utf-8-sig") as archivo:
        return list(csv.DictReader(archivo))


def historias_cerradas() -> set[str]:
    cerradas: set[str] = set()
    for persona in PERSONAS:
        texto = (RAIZ / "docs" / "tareas" / f"{persona}.md").read_text(encoding="utf-8")
        cerradas |= set(PATRON_CERRADA.findall(texto))
    return cerradas


def rubrica_del_backlog(fila: dict[str, str]) -> str:
    encontrado = re.search(r"Rubrica o objetivo: (.+)", fila["cuerpo"])
    return encontrado.group(1).strip() if encontrado else "?"


def evidencia_de(identificador: str, carpeta: str) -> str:
    """
    El archivo de evidencia si existe en disco; si no, la carpeta destino.

    Se busca en disco en lugar de escribirlo a mano porque el nombre del archivo
    lo elige quien cierra la historia, y la matriz declaraba rutas que no
    existian.
    """
    directorio = RAIZ / carpeta
    if directorio.is_dir():
        for archivo in sorted(directorio.glob(f"{identificador}-*.md")):
            # Los criterios de aceptacion NO son la evidencia de la historia: se
            # escriben ANTES de implementar y pertenecen a la Definition of
            # Ready. La evidencia es lo que demuestra que quedo hecha.
            if archivo.name.endswith("-criterios-aceptacion.md"):
                continue
            return archivo.relative_to(RAIZ).as_posix()
    return carpeta


def estado_de(identificador: str, cerradas: set[str], nota: str) -> str:
    if identificador in cerradas:
        return f"**Con evidencia** · {nota}" if nota else "**Con evidencia**"
    return nota if nota else "Pendiente"


def construir() -> str:
    backlog = {fila["id"]: fila for fila in leer_csv(RAIZ / "docs" / "backlog.csv")}
    detalle = leer_csv(RAIZ / "docs" / "trazabilidad.csv")
    cerradas = historias_cerradas()

    lineas = [
        "| Historia | Requisito | Modulo | Prueba | Evidencia | Rubrica | Dueno | Estado |",
        "|---|---|---|---|---|---|---|---|",
    ]

    faltan_en_backlog = []

    for fila in detalle:
        identificador = fila["id"]
        del_backlog = backlog.get(identificador)
        if del_backlog is None:
            faltan_en_backlog.append(identificador)
            continue

        rubrica = fila["rubrica"] or rubrica_del_backlog(del_backlog)
        dueno = del_backlog["responsable"].capitalize()

        lineas.append(
            "| {} | {} | {} | {} | {} | {} | {} | {} |".format(
                identificador,
                fila["requisito"],
                fila["modulo"],
                fila["prueba"],
                evidencia_de(identificador, fila["carpeta_evidencia"]),
                rubrica,
                dueno,
                estado_de(identificador, cerradas, fila["nota_estado"]),
            )
        )

    if faltan_en_backlog:
        raise SystemExit(
            f"ERROR: docs/trazabilidad.csv declara historias que no estan en el "
            f"backlog: {faltan_en_backlog}"
        )

    # Toda historia cerrada tiene que tener fila. Si falta, es que nadie la
    # agrego a trazabilidad.csv, y generar en silencio la dejaria fuera.
    sin_fila = sorted(cerradas - {f["id"] for f in detalle})
    if sin_fila:
        raise SystemExit(
            f"ERROR: hay historias cerradas sin fila en docs/trazabilidad.csv: "
            f"{sin_fila}. Agregarlas ahi y volver a generar."
        )

    return ENCABEZADO + "\n".join(lineas) + "\n" + PIE


def main() -> int:
    contenido = construir()
    revisar = "--revisar" in sys.argv

    actual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else ""

    if actual == contenido:
        print("La matriz esta al dia con sus fuentes.")
        return 0

    if revisar:
        print(
            "La matriz NO corresponde a sus fuentes.\n\n"
            "Regenerar con:\n"
            "    python docs/herramientas/generar_matriz.py\n\n"
            "Si el cambio que querias hacer es de contenido, va en la fuente:\n"
            "  - dueno o rubrica          -> docs/backlog.csv\n"
            "  - historia cerrada         -> docs/tareas/<persona>.md\n"
            "  - requisito, modulo, prueba -> docs/trazabilidad.csv\n"
            "  - archivo de evidencia     -> subirlo a docs/evidencias/"
        )
        return 1

    DESTINO.write_text(contenido, encoding="utf-8")
    print(f"Matriz regenerada: {contenido.count(chr(10) + '| H')} filas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
