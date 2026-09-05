"""
Restaura un respaldo en una base DISTINTA. Dueno: Cesar. Historia H1.10, issue #42.

NUNCA RESTAURA SOBRE LA BASE DE TRABAJO

El destino por omision es `geoguardian_restaurada` y hay que pedir explicitamente
otro nombre. Una prueba de restauracion que puede destruir la base de trabajo es
peor que no tenerla: se corre una vez, sale mal, y ya no hay contra que comparar.

Si el destino coincide con `POSTGRES_DB`, el programa se planta y no restaura.

LOS DOS PASOS, Y POR QUE NO SON TRES

    1. `003_seguridad_roles`  los roles tienen que existir ANTES
    2. `pg_restore`           trae extensiones, esquemas, objetos y datos

**El volcado se basta solo para todo lo demas, y esto esta medido.** La primera
version de este programa corria `01-extensiones.sql` antes de restaurar, por
analogia con lo que se descubrio en H1.15 -que **ninguna migracion numerada crea
las extensiones ni los cuatro esquemas**: los crea `init-db`, una sola vez, sobre
un volumen vacio-.

Esa analogia era falsa, y `pg_restore` lo dijo:

    pg_restore: error: could not execute query: ERROR: schema "analitico" already exists
    Command was: CREATE SCHEMA analitico;

`pg_restore --list` sobre el volcado lo confirma: trae las entradas SCHEMA de los
cuatro esquemas y las EXTENSION de postgis, postgis_raster y pg_stat_statements,
con sus COMMENT y sus ACL.

**Las migraciones y un volcado son dos artefactos distintos con distinta
autosuficiencia.** Las migraciones asumen una base ya inicializada; el volcado se
describe entero a si mismo. Preparar el destino a mano le pisa el terreno.

POR QUE `--no-owner`, Y QUE SIGNIFICA

Tanto el volcado como la restauracion usan `--no-owner`: los objetos quedan a
nombre de quien restaura, no de sus duenos originales.

**Es una decision, no un descuido, y cambia algo.** H1.8 establecio duenos y
privilegios minimos; una restauracion con `--no-owner` los reasigna en bloque. Se
elige asi porque el dueno depende del cluster de destino y, sin la bandera, una
restauracion en un cluster donde ese rol no existe falla por una razon que no
tiene que ver con los datos.

**Los GRANT si viajan** -son las entradas ACL del volcado-, asi que los permisos
de `geoguardian_api` y `geoguardian_etl` se restauran. Lo que cambia es la
propiedad, no el acceso. Si alguna vez importa que los duenos vuelvan tal cual,
la bandera se quita y el paso 1 pasa a exigir tambien que existan esos duenos.

EL PASO 1 SIGUE HACIENDO FALTA, Y POR ESO ES UN PASO

**`pg_dump` de una base no incluye los roles**: los roles son del cluster, no de
la base. En el listado de arriba se ven las entradas ACL -los GRANT de
`003_seguridad_roles.sql`- y esas nombran a `geoguardian_api` y `geoguardian_etl`
sin traer su definicion.

Este programa comprueba que existan y **se niega a seguir si faltan**, en vez de
restaurar algo a medias y devolver cero.

USO

    python -m basedatos.restaurar basedatos/respaldos/geoguardian-2026....dump
    python -m basedatos.restaurar <archivo> --destino otra_base
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from basedatos.respaldar import configuracion, en_contenedor  # noqa: E402

DESTINO_POR_OMISION = "geoguardian_restaurada"
ROLES_EXIGIDOS = ("geoguardian_api", "geoguardian_etl")


class ErrorRestauracion(Exception):
    """No se pudo restaurar."""


def sql(orden: str, base: str, cfg: dict[str, str]) -> str:
    """Corre una sentencia con psql dentro del contenedor y devuelve su salida."""
    resultado = en_contenedor(
        ["psql", "-v", "ON_ERROR_STOP=1", "-tA", "-U", cfg["usuario"], "-d", base, "-c", orden],
        cfg["contrasena"],
    )
    if resultado.returncode != 0:
        raise ErrorRestauracion(
            f"psql fallo sobre `{base}`:\n{resultado.stderr.decode('utf-8', 'replace').strip()}"
        )
    return resultado.stdout.decode("utf-8", "replace").strip()


def comprobar_roles(cfg: dict[str, str]) -> None:
    existentes = set(
        sql(
            "SELECT rolname FROM pg_roles WHERE rolname LIKE 'geoguardian%'",
            "postgres",
            cfg,
        ).splitlines()
    )
    faltantes = [r for r in ROLES_EXIGIDOS if r not in existentes]
    if faltantes:
        raise ErrorRestauracion(
            f"Faltan roles en el cluster: {', '.join(faltantes)}.\n"
            "El respaldo NO los contiene, y es deliberado: exportarlos con\n"
            "pg_dumpall --roles-only incluiria sus contrasenas cifradas.\n\n"
            "Corre primero, contra la base de trabajo:\n"
            "    python -m basedatos.aplicar_migraciones\n"
            "que aplica 003_seguridad_roles.sql y los crea."
        )
    print(f"  roles presentes: {', '.join(ROLES_EXIGIDOS)}")


def recrear_base(destino: str, cfg: dict[str, str]) -> None:
    # WITH (FORCE) cierra las conexiones abiertas contra el destino. Sin eso, una
    # sesion olvidada en un cliente grafico hace fallar el DROP y la prueba
    # quedaria roja por una razon que no tiene que ver con el respaldo.
    sql(f'DROP DATABASE IF EXISTS "{destino}" WITH (FORCE)', "postgres", cfg)
    sql(f'CREATE DATABASE "{destino}"', "postgres", cfg)
    print(f"  base `{destino}` recreada vacia")


def listar(archivo: Path) -> None:
    """
    Muestra que trae el volcado, sin restaurar nada.

    Sirve para decidir con evidencia y no por suposicion que hace falta preparar
    en el destino. Fue lo que demostro que el volcado ya trae los esquemas y las
    extensiones, y que prepararlos a mano le pisa el terreno a pg_restore.
    """
    cfg = configuracion()
    resultado = en_contenedor(
        ["pg_restore", "--list"], cfg["contrasena"], entrada=archivo.read_bytes()
    )
    if resultado.returncode != 0:
        raise ErrorRestauracion(resultado.stderr.decode("utf-8", "replace").strip())

    lineas = resultado.stdout.decode("utf-8", "replace").splitlines()
    interesantes = [ln for ln in lineas if " SCHEMA " in ln or " EXTENSION " in ln]

    print(f"{len(lineas)} entradas en el volcado. Esquemas y extensiones:\n")
    for ln in interesantes:
        print(f"  {ln.strip()}")
    if not interesantes:
        print("  ninguna. El volcado NO trae esquemas ni extensiones.")


def restaurar(archivo: Path, destino: str = DESTINO_POR_OMISION, forzar: bool = False) -> None:
    cfg = configuracion()

    if destino == cfg["base"] and not forzar:
        raise ErrorRestauracion(
            f"El destino `{destino}` es la base de trabajo.\n\n"
            "Por omision este programa NO restaura encima de ella: una prueba de\n"
            "restauracion que puede destruir la base de trabajo se corre una vez,\n"
            "sale mal, y ya no hay contra que comparar.\n\n"
            "Pero el dia que la base se pierda de verdad hay que poder recuperarla,\n"
            "y una herramienta que no sabe hacerlo obliga a improvisar comandos que\n"
            "nadie corrio nunca. Para ese caso:\n\n"
            f"    python -m basedatos.restaurar <archivo> --destino {destino} --forzar\n\n"
            "Eso BORRA la base actual y la reemplaza por el respaldo. Antes de\n"
            "correrlo, tomate un respaldo del estado actual aunque parezca perdido."
        )

    if destino == cfg["base"]:
        print("=" * 70)
        print("ATENCION: se va a BORRAR la base de trabajo y reemplazarla por el")
        print(f"respaldo. Base: {destino}. Esto no se puede deshacer.")
        print("=" * 70)
        print()
    if not archivo.exists():
        raise ErrorRestauracion(f"No existe el archivo {archivo}")

    print(f"Archivo: {archivo}  ({archivo.stat().st_size:,} bytes)")
    print(f"Destino: {destino}\n")

    print("1. Roles del cluster")
    comprobar_roles(cfg)

    print("2. Base de destino, vacia")
    recrear_base(destino, cfg)

    print("3. pg_restore: extensiones, esquemas, objetos y datos")
    resultado = en_contenedor(
        ["pg_restore", "--no-owner", "--exit-on-error", "-U", cfg["usuario"], "-d", destino],
        cfg["contrasena"],
        entrada=archivo.read_bytes(),
    )
    if resultado.returncode != 0:
        raise ErrorRestauracion(
            "pg_restore fallo. Con --exit-on-error se detiene en el primer\n"
            "problema en vez de seguir y terminar en cero habiendo omitido objetos.\n\n"
            f"{resultado.stderr.decode('utf-8', 'replace').strip()}"
        )

    aviso = resultado.stderr.decode("utf-8", "replace").strip()
    if aviso:
        print("  pg_restore dijo:")
        for linea in aviso.splitlines():
            print(f"    {linea}")

    tablas = sql(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema IN ('geo','crudo','analitico','control')",
        destino,
        cfg,
    )
    print(f"  restaurada. {tablas} tablas en los cuatro esquemas")
    print(f"\nLa base `{destino}` queda creada para poder inspeccionarla.")
    print("No se toco la base de trabajo en ningun momento.")


def main() -> int:
    analizador = argparse.ArgumentParser(
        description="Restaura un respaldo en una base distinta de la de trabajo."
    )
    analizador.add_argument("archivo", type=Path, help="El .dump a restaurar.")
    analizador.add_argument(
        "--destino",
        default=DESTINO_POR_OMISION,
        help=f"Nombre de la base de destino. Por omision {DESTINO_POR_OMISION}.",
    )
    analizador.add_argument(
        "--forzar",
        action="store_true",
        help="Permite restaurar SOBRE la base de trabajo. Borra lo que haya. Solo para una recuperacion real.",
    )
    analizador.add_argument(
        "--listar",
        action="store_true",
        help="Solo muestra que trae el volcado. No restaura nada.",
    )
    argumentos = analizador.parse_args()

    try:
        if argumentos.listar:
            listar(argumentos.archivo)
        else:
            restaurar(argumentos.archivo, argumentos.destino, argumentos.forzar)
    except ErrorRestauracion as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
