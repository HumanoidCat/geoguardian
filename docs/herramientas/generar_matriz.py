"""Genera los artefactos derivados de la documentacion.

Produce dos cosas, las dos desde las mismas fuentes:

    docs/05-matriz-trazabilidad.md   la tabla completa
    docs/08-backlog.md               la linea de avance, solo esa linea


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

LA LINEA DE AVANCE

`docs/08-backlog.md` declara cuantas historias van cerradas. Era una cifra
derivada mantenida a mano, y eso rompia el CI de quien cerrara la siguiente
historia **sin haber roto nada**: el verificador de documentacion la comprueba y
el numero cambia cada vez que cualquiera marca `[x]`.

Lo detecto Cesar el 19 de agosto al cerrar H1.8, y quedo demostrado enseguida: sus
dos Pull Requests escribieron la misma linea con el mismo valor, cada uno correcto
por separado, y al integrarse los dos el numero real pasaba a ser otro. Ver la
incidencia **I-07**.

Ahora la escribe esta herramienta, que es la que ya hay que correr al cerrar una
historia porque la matriz tambien cambia. No agrega ningun paso.

Uso:
    python docs/herramientas/generar_matriz.py            escribe los archivos
    python docs/herramientas/generar_matriz.py --revisar  solo informa si estan al dia
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

DESTINO = RAIZ / "docs" / "05-matriz-trazabilidad.md"
BACKLOG_MD = RAIZ / "docs" / "08-backlog.md"

# La linea de avance de docs/08-backlog.md. Era una cifra derivada mantenida a
# mano, y por eso rompia el CI de quien cerrara la siguiente historia sin haber
# roto nada. Lo detecto Cesar el 19 de agosto al cerrar H1.8. Ver incidencia
# I-07 y decision D-20, que es el mismo principio.
PATRON_AVANCE = re.compile(
    r"^Al .+?: \*\*\d+ historias cerradas de \d+\*\*, \d+ puntos de \d+\.$", re.M
)

# Marca de conflicto de fusion sin resolver. Son exactamente siete caracteres:
# `<<<<<<< ` y `>>>>>>> ` llevan el nombre de la rama detras, y `=======` va solo
# en su linea. Anclar el separador al final del renglon es lo que evita los falsos
# positivos con las lineas de separacion de las salidas de los verificadores, que
# en las evidencias tienen 66 y 74 caracteres. Lo preciso Cesar el 19 de agosto.
PATRON_CONFLICTO = re.compile(r"^(<{7} |={7}$|>{7} )", re.M)

MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)  # fmt: skip
PERSONAS = ("alejandro", "cesar", "luna", "avril")

PATRON_CERRADA = re.compile(r"^- \[x\] \*\*(H[0-9.]+[a-z]?)\*\*", re.M)
PATRON_CERRADA_CON_FECHA = re.compile(
    r"^- \[x\] \*\*(H[0-9.]+[a-z]?)\*\*[^\n]*?\((\d{4}-\d{2}-\d{2})\)", re.M
)

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


def linea_de_avance() -> str:
    """
    La cifra de avance, con la fecha de la ultima historia cerrada.

    Se fecha con el ultimo cierre y no con el dia de hoy a proposito: si llevara
    la fecha actual, regenerar sin haber cerrado nada produciria un cambio en el
    archivo, y el CI empezaria a fallar por el paso del tiempo.
    """
    backlog = {fila["id"]: fila for fila in leer_csv(RAIZ / "docs" / "backlog.csv")}
    cerradas: dict[str, str] = {}

    for persona in PERSONAS:
        texto = (RAIZ / "docs" / "tareas" / f"{persona}.md").read_text(encoding="utf-8")
        for identificador, fecha in PATRON_CERRADA_CON_FECHA.findall(texto):
            cerradas[identificador] = fecha

    puntos = sum(int(backlog[h]["puntos"]) for h in cerradas if h in backlog)
    ultima = max(cerradas.values()) if cerradas else "0000-00-00"
    anio, mes, dia = ultima.split("-")
    fecha = f"{int(dia)} de {MESES[int(mes) - 1]} de {anio}"

    return (
        f"Al {fecha}: **{len(cerradas)} historias cerradas de {len(backlog)}**, "
        f"{puntos} puntos de {sum(int(f['puntos']) for f in backlog.values())}."
    )


def sin_marcas_de_conflicto(ruta: Path) -> None:
    """
    Se niega a trabajar sobre un archivo con un conflicto sin resolver.

    Sin esta comprobacion la herramienta tenia un punto ciego: sustituia la linea
    que coincidia y, si el bloque en conflicto contenia dos versiones identicas,
    el resultado era igual al de entrada. Informaba "al dia" con las tres marcas
    todavia dentro del archivo.

    Lo encontro Cesar el 19 de agosto, al seguir la instruccion de regenerar en
    lugar de fusionar a mano y comprobar que no lo arreglaba.
    """
    encontrado = PATRON_CONFLICTO.search(ruta.read_text(encoding="utf-8"))
    if encontrado:
        linea = ruta.read_text(encoding="utf-8")[: encontrado.start()].count("\n") + 1
        raise SystemExit(
            f"ERROR: {ruta.relative_to(RAIZ).as_posix()} tiene una marca de conflicto "
            f"sin resolver en la linea {linea}.\n"
            "Regenerar no lo arregla: hay que quitar las tres lineas de marca primero.\n"
            'Para encontrarlas todas:  git grep -nE "^(<{7} |={7}$|>{7} )"'
        )


def escribir_avance(revisar: bool) -> bool:
    """Sustituye la linea de avance en docs/08-backlog.md. Devuelve si estaba al dia."""
    sin_marcas_de_conflicto(BACKLOG_MD)
    texto = BACKLOG_MD.read_text(encoding="utf-8")
    esperada = linea_de_avance()

    if not PATRON_AVANCE.search(texto):
        raise SystemExit(
            f"ERROR: no se encontro la linea de avance en {BACKLOG_MD.name}. "
            "Tiene que existir una linea con la forma "
            "'Al <fecha>: **N historias cerradas de M**, P puntos de Q.'"
        )

    nuevo = PATRON_AVANCE.sub(esperada.replace("\\", "\\\\"), texto)
    if nuevo == texto:
        return True

    if not revisar:
        BACKLOG_MD.write_text(nuevo, encoding="utf-8")
    return False


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
    if DESTINO.exists():
        sin_marcas_de_conflicto(DESTINO)
    contenido = construir()
    revisar = "--revisar" in sys.argv

    actual = DESTINO.read_text(encoding="utf-8") if DESTINO.exists() else ""
    avance_al_dia = escribir_avance(revisar)

    if actual == contenido and avance_al_dia:
        print("La matriz y la linea de avance estan al dia con sus fuentes.")
        return 0

    if actual == contenido and not avance_al_dia:
        if revisar:
            print(
                "La linea de avance de docs/08-backlog.md no corresponde.\n"
                "Regenerar con: python docs/herramientas/generar_matriz.py"
            )
            return 1
        print(f"Linea de avance actualizada: {linea_de_avance()}")
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
    if not avance_al_dia:
        print(f"Linea de avance actualizada: {linea_de_avance()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
