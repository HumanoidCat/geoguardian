"""Comprueba que el estado de avance sea el mismo en todos los lugares que lo declaran.

POR QUE EXISTE

El backlog, `docs/backlog.csv`, **no registra que historias estan terminadas**, y
es deliberado: si lo registrara habria un cuarto lugar donde el estado puede
desfasarse.

Hoy el avance vive en dos sitios dentro del repositorio, y en las issues de GitHub
fuera de el:

    docs/tareas/<persona>.md        la marca [x] con fecha. ES LA FUENTE DE VERDAD.
    docs/05-matriz-trazabilidad.md  vista generada. Desde el 18 de agosto no se
                                    edita a mano: la produce generar_matriz.py
    issues de GitHub                las cierra cada quien al mergear su PR

Nada comprobaba que los dos primeros coincidieran. La auditoria del 18 de agosto
encontro **cuatro historias cerradas que no estaban en la matriz** —H6.4, H8.5,
H8.6 y H10.8— y dos filas con el dueno equivocado. El segundo defecto le quito
trabajo del plato a una persona durante un dia: leyo la matriz, vio que dos
historias suyas figuraban a nombre de otro y las dio por ajenas.

QUE COMPRUEBA

1. Toda historia marcada [x] tiene fila en la matriz.
2. Toda fila de la matriz marcada "Con evidencia" corresponde a una historia [x].
3. El archivo de evidencia que la matriz declara existe en disco.
4. El dueno que declara la matriz es el del backlog.
5. Ninguna historia esta marcada [x] en el archivo de dos personas.
6. Toda historia marcada [x] existe en el backlog.
7. La matriz corresponde a sus fuentes, o sea que nadie la edito a mano.

QUE NO COMPRUEBA

Las issues de GitHub, que viven fuera del repositorio. Se cierran solas al mergear
el Pull Request que las enlaza con `Closes #N`.

Tampoco comprueba que el trabajo este bien hecho. Comprueba que los documentos
digan lo mismo.

Uso:
    python docs/herramientas/verificar_estado.py

Sale con codigo 1 si algo no coincide, para poder correrlo en CI.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

PERSONAS = ("alejandro", "cesar", "luna", "avril")

# Las lineas de tarea reales empiezan en columna cero. El bloque de instrucciones
# de los archivos de tareas incluye un ejemplo indentado marcado [x] a proposito,
# y contarlo fue uno de los defectos que originaron el verificador de
# documentacion. Ver docs/11-ceremonias-scrum.md, acta 12.
PATRON_CERRADA = re.compile(
    r"^- \[x\] \*\*(H[0-9.]+[a-z]?)\*\*[^\n]*?\((\d{4}-\d{2}-\d{2})\)", re.M
)

# En la matriz, una historia terminada se marca con "Con evidencia" en la ultima
# columna. Puede llevar texto detras: una salvedad, una reejecucion pendiente.
MARCA_TERMINADA = "Con evidencia"


def historias_del_backlog() -> dict[str, dict[str, str]]:
    with (RAIZ / "docs" / "backlog.csv").open(encoding="utf-8-sig") as archivo:
        return {fila["id"]: fila for fila in csv.DictReader(archivo)}


def historias_cerradas() -> dict[str, tuple[str, str]]:
    """Identificador -> (persona, fecha). La fuente de verdad del avance."""
    cerradas: dict[str, tuple[str, str]] = {}
    duplicadas: list[str] = []

    for persona in PERSONAS:
        texto = (RAIZ / "docs" / "tareas" / f"{persona}.md").read_text(encoding="utf-8")
        for identificador, fecha in PATRON_CERRADA.findall(texto):
            if identificador in cerradas:
                duplicadas.append(identificador)
            cerradas[identificador] = (persona, fecha)

    if duplicadas:
        # No se puede seguir: no se sabe de quien es la historia.
        raise SystemExit(f"ERROR: historias marcadas por dos personas: {sorted(set(duplicadas))}")

    return cerradas


def filas_de_la_matriz() -> dict[str, dict[str, str]]:
    """Identificador -> {dueno, estado, evidencia}."""
    texto = (RAIZ / "docs" / "05-matriz-trazabilidad.md").read_text(encoding="utf-8")
    filas: dict[str, dict[str, str]] = {}

    for linea in texto.splitlines():
        # `| H` tambien abre la fila de encabezado, que empieza con "| Historia".
        # Se exige el formato de identificador: H, digitos, puntos y quiza una
        # letra al final, como H10.5a.
        if not re.match(r"^\| H\d[\d.]*[a-z]? \|", linea):
            continue
        celdas = [c.strip() for c in linea.split("|")]
        # | id | requisito | modulo | prueba | evidencia | rubrica | dueno | estado |
        if len(celdas) < 9:
            continue
        filas[celdas[1]] = {
            "evidencia": celdas[5],
            "dueno": celdas[7],
            "estado": celdas[8],
        }

    return filas


def main() -> int:
    backlog = historias_del_backlog()
    cerradas = historias_cerradas()
    matriz = filas_de_la_matriz()

    problemas: list[str] = []

    # 1. Toda historia cerrada tiene fila en la matriz.
    for identificador in sorted(cerradas):
        if identificador not in matriz:
            persona, fecha = cerradas[identificador]
            problemas.append(
                f"{identificador} esta cerrada por {persona} el {fecha} "
                "y no tiene fila en la matriz de trazabilidad"
            )

    # 2. Toda fila terminada corresponde a una historia cerrada.
    for identificador, fila in sorted(matriz.items()):
        if MARCA_TERMINADA in fila["estado"] and identificador not in cerradas:
            problemas.append(
                f"{identificador} figura como '{MARCA_TERMINADA}' en la matriz "
                "y no esta marcada en el archivo de tareas de nadie"
            )

    # 3. Cada archivo de evidencia declarado existe.
    #
    # La celda puede traer VARIAS rutas separadas por `<br>`: una historia puede
    # tener mas de una evidencia, y desde el 20 de agosto la matriz las lista
    # todas en vez de quedarse con la primera por orden alfabetico. Antes de ese
    # cambio, H5.1 tenia dos y solo una figuraba en la tabla.
    for identificador, fila in sorted(matriz.items()):
        for ruta in fila["evidencia"].split("<br>"):
            ruta = ruta.strip()
            if ruta.endswith(".md") and not (RAIZ / ruta).exists():
                problemas.append(
                    f"{identificador} declara la evidencia {ruta} y el archivo no existe"
                )

    # 4. El dueno coincide con el del backlog.
    for identificador, fila in sorted(matriz.items()):
        if identificador not in backlog:
            problemas.append(f"{identificador} tiene fila en la matriz y no esta en el backlog")
            continue
        esperado = backlog[identificador]["responsable"]
        if fila["dueno"].lower() != esperado.lower():
            problemas.append(
                f"{identificador}: la matriz dice dueno '{fila['dueno']}' "
                f"y el backlog dice '{esperado}'"
            )

    # 6. Toda historia cerrada existe en el backlog.
    for identificador in sorted(cerradas):
        if identificador not in backlog:
            problemas.append(f"{identificador} esta marcada como cerrada y no existe en el backlog")

    # 7. La matriz corresponde a sus fuentes.
    #
    # Desde que la matriz se genera, editarla a mano es un defecto: el proximo que
    # regenere pisa el cambio sin enterarse. Se comprueba igual que
    # `ruff format --check`, comparando contra lo que produce la herramienta.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from generar_matriz import DESTINO, construir  # noqa: PLC0415

    if DESTINO.read_text(encoding="utf-8") != construir():
        problemas.append(
            "docs/05-matriz-trazabilidad.md no corresponde a sus fuentes. "
            "Se genera, no se edita a mano: correr "
            "python docs/herramientas/generar_matriz.py"
        )

    # ----------------------------------------------------------------------- #
    # Informe                                                                   #
    # ----------------------------------------------------------------------- #

    print("\nEstado de avance, calculado desde el repositorio\n")

    puntos_totales = sum(int(f["puntos"]) for f in backlog.values())
    puntos_hechos = sum(int(backlog[h]["puntos"]) for h in cerradas if h in backlog)

    print(f"  historias: {len(cerradas)} de {len(backlog)}")
    print(
        f"  puntos   : {puntos_hechos} de {puntos_totales} "
        f"({puntos_hechos / puntos_totales * 100:.1f} %)"
    )

    print("\n  por persona:")
    por_persona = Counter(persona for persona, _ in cerradas.values())
    for persona in PERSONAS:
        asignadas = sum(1 for f in backlog.values() if f["responsable"] == persona)
        pts = sum(
            int(backlog[h]["puntos"]) for h in cerradas if backlog[h]["responsable"] == persona
        )
        print(
            f"    {persona:10} {por_persona[persona]:>2} de {asignadas:>2} historias, {pts:>3} pts"
        )

    print("\n  por sprint del backlog:")
    for sprint in ("S0", "S1", "S2", "S3", "S4"):
        del_sprint = [i for i, f in backlog.items() if f["sprint"] == sprint]
        hechas = [i for i in del_sprint if i in cerradas]
        pts_sprint = sum(int(backlog[i]["puntos"]) for i in del_sprint)
        pts_hechos = sum(int(backlog[i]["puntos"]) for i in hechas)
        print(
            f"    {sprint}  {len(hechas):>2} de {len(del_sprint):>2} historias, "
            f"{pts_hechos:>3} de {pts_sprint:>3} pts"
        )

    if problemas:
        print(f"\n{len(problemas)} discrepancias:\n")
        for problema in problemas:
            print(f"  - {problema}")
        print(
            "\nEl avance real es el de docs/tareas/, que es donde cada quien marca su\n"
            "propio trabajo. La matriz es una vista y se corrige contra el."
        )
        return 1

    print("\nEl estado coincide en el backlog, en los archivos de tareas y en la matriz.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
