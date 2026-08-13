"""
Aplicador de migraciones de DDL. Dueno: Cesar. Historia H1.3, issue #37.

POR QUE EXISTE

Los scripts de infra/docker/init-db/ los ejecuta la imagen de PostgreSQL una sola
vez, cuando el volumen de datos esta vacio. Si se modifican despues, no vuelven a
correr: haria falta `docker compose down -v`, que borra todos los datos. Depender
de eso cada vez que cambie una tabla no es viable.

Este modulo aplica el DDL de basedatos/ddl/ sobre una base ya arrancada.

COMO FUNCIONA

  1. Lista los archivos .sql de basedatos/ddl/ ordenados por su prefijo numerico.
  2. Consulta control.migracion para saber cuales ya se aplicaron.
  3. Aplica solo los pendientes, en orden, CADA UNO EN SU PROPIA TRANSACCION.
  4. Registra cada aplicacion con la suma SHA-256 del archivo.

Si una migracion falla, su transaccion se revierte entera y el proceso se detiene
sin aplicar las siguientes. No quedan estados a medias.

Si un archivo YA APLICADO cambio de contenido, el proceso se detiene con error
antes de tocar nada. Esa es la regla de que una migracion aplicada no se edita,
convertida en algo que la herramienta hace cumplir en vez de una convencion que
se olvida.

Es idempotente: correrlo dos veces seguidas no reaplica nada y no falla.

USO

    python -m basedatos.aplicar_migraciones
    python -m basedatos.aplicar_migraciones --verificar   # no aplica, solo informa
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg

from basedatos.conexion import ErrorConexion, conectar

DIRECTORIO_DDL = Path(__file__).resolve().parent / "ddl"

# 001_control_migracion.sql -> numero 1
PATRON_ARCHIVO = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")

# La migracion 001 crea control.migracion. Antes de aplicarla la tabla no existe,
# asi que la consulta del registro tiene que tolerar su ausencia.
SQL_REGISTRO_EXISTE = """
    SELECT to_regclass('control.migracion') IS NOT NULL
"""

SQL_APLICADAS = """
    SELECT numero, archivo, suma_sha256
      FROM control.migracion
     ORDER BY numero
"""

SQL_REGISTRAR = """
    INSERT INTO control.migracion (numero, archivo, suma_sha256)
    VALUES (%(numero)s, %(archivo)s, %(suma)s)
"""


@dataclass(frozen=True)
class Migracion:
    """Un archivo de migracion en disco."""

    numero: int
    archivo: str
    ruta: Path
    suma: str

    @property
    def etiqueta(self) -> str:
        return f"{self.numero:03d} {self.archivo}"


class ErrorMigracion(Exception):
    """Falla que obliga a detener el proceso sin aplicar nada mas."""


def leer_migraciones(directorio: Path = DIRECTORIO_DDL) -> list[Migracion]:
    """
    Lee los archivos de migracion del directorio, ordenados por numero.

    Ignora cualquier archivo que no siga el patron NNN_nombre.sql. Eso permite
    dejar notas en la misma carpeta (por ejemplo el archivo de procedencia de las
    geometrias) sin que el aplicador intente ejecutarlas.
    """
    if not directorio.is_dir():
        raise ErrorMigracion(f"No existe el directorio de migraciones: {directorio}")

    encontradas: dict[int, Migracion] = {}

    for ruta in sorted(directorio.iterdir()):
        coincidencia = PATRON_ARCHIVO.match(ruta.name)
        if coincidencia is None:
            continue

        numero = int(coincidencia.group(1))
        contenido = ruta.read_bytes()
        suma = hashlib.sha256(contenido).hexdigest()

        if numero in encontradas:
            raise ErrorMigracion(
                f"Numero de migracion repetido: {numero:03d} lo usan "
                f"{encontradas[numero].archivo} y {ruta.name}"
            )

        encontradas[numero] = Migracion(numero=numero, archivo=ruta.name, ruta=ruta, suma=suma)

    return [encontradas[numero] for numero in sorted(encontradas)]


def leer_aplicadas(conexion: psycopg.Connection) -> dict[int, tuple[str, str]]:
    """
    Devuelve {numero: (archivo, suma)} de lo ya aplicado.

    Si control.migracion todavia no existe, devuelve un diccionario vacio: es el
    caso de la primera corrida, donde la migracion 001 es la que crea la tabla.
    """
    with conexion.cursor() as cursor:
        cursor.execute(SQL_REGISTRO_EXISTE)
        fila = cursor.fetchone()
        if fila is None or not fila[0]:
            return {}

        cursor.execute(SQL_APLICADAS)
        return {numero: (archivo, suma) for numero, archivo, suma in cursor.fetchall()}


def comprobar_integridad(
    migraciones: list[Migracion], aplicadas: dict[int, tuple[str, str]]
) -> None:
    """
    Verifica que ningun archivo ya aplicado haya cambiado.

    Se corre ANTES de aplicar nada. Si un archivo aplicado fue editado, el estado
    de esta base y el de cualquier otra dejan de ser comparables, y seguir
    aplicando migraciones encima solo agrava el problema.
    """
    problemas: list[str] = []
    en_disco = {migracion.numero: migracion for migracion in migraciones}

    for numero, (archivo, suma) in sorted(aplicadas.items()):
        migracion = en_disco.get(numero)

        if migracion is None:
            problemas.append(
                f"  {numero:03d} {archivo}: registrada en la base pero no esta en disco"
            )
            continue

        if migracion.archivo != archivo:
            problemas.append(
                f"  {numero:03d}: se aplico como '{archivo}' y ahora el archivo "
                f"se llama '{migracion.archivo}'"
            )
            continue

        if migracion.suma != suma:
            problemas.append(
                f"  {numero:03d} {archivo}: el contenido cambio despues de aplicarse\n"
                f"      suma registrada: {suma}\n"
                f"      suma actual:     {migracion.suma}"
            )

    if problemas:
        raise ErrorMigracion(
            "Hay migraciones ya aplicadas que no coinciden con el disco:\n"
            + "\n".join(problemas)
            + "\n\nUna migracion aplicada no se edita. Revertí el cambio y creá "
            "un archivo nuevo con el siguiente numero."
        )


def aplicar_una(conexion: psycopg.Connection, migracion: Migracion) -> None:
    """
    Aplica una migracion dentro de su propia transaccion.

    El bloque `with conexion.transaction()` confirma al salir sin excepcion y
    revierte si algo falla. El registro en control.migracion va DENTRO de la
    misma transaccion: o queda el DDL y su registro, o no queda ninguno de los
    dos. Registrar por fuera permitiria que la tabla existiera sin constar como
    aplicada, o al reves.
    """
    sql = migracion.ruta.read_text(encoding="utf-8")

    with conexion.transaction(), conexion.cursor() as cursor:
        cursor.execute(sql)
        cursor.execute(
            SQL_REGISTRAR,
            {
                "numero": migracion.numero,
                "archivo": migracion.archivo,
                "suma": migracion.suma,
            },
        )


def aplicar(solo_verificar: bool = False) -> int:
    """
    Aplica las migraciones pendientes. Devuelve el codigo de salida del proceso.
    """
    migraciones = leer_migraciones()

    if not migraciones:
        print(f"No hay migraciones en {DIRECTORIO_DDL}")
        return 0

    with conectar(autocommit=True) as conexion:
        aplicadas = leer_aplicadas(conexion)
        comprobar_integridad(migraciones, aplicadas)

        pendientes = [m for m in migraciones if m.numero not in aplicadas]

        print(f"Migraciones en disco:  {len(migraciones)}")
        print(f"Ya aplicadas:          {len(aplicadas)}")
        print(f"Pendientes:            {len(pendientes)}")

        if not pendientes:
            print("\nNada que aplicar. La base esta al dia.")
            return 0

        if solo_verificar:
            print("\nPendientes de aplicar:")
            for migracion in pendientes:
                print(f"  {migracion.etiqueta}")
            print("\nModo verificacion: no se aplico nada.")
            return 0

        print()
        for migracion in pendientes:
            print(f"Aplicando {migracion.etiqueta} ...", end=" ", flush=True)
            try:
                aplicar_una(conexion, migracion)
            except psycopg.Error as error:
                print("FALLO")
                raise ErrorMigracion(
                    f"La migracion {migracion.etiqueta} fallo y se revirtio entera.\n"
                    f"No se aplico ninguna migracion posterior.\n\n{error}"
                ) from error
            print("ok")

        print(f"\nAplicadas {len(pendientes)} migraciones.")

    return 0


def main() -> int:
    analizador = argparse.ArgumentParser(
        description="Aplica las migraciones de DDL de basedatos/ddl/ sobre la base."
    )
    analizador.add_argument(
        "--verificar",
        action="store_true",
        help="Informa que migraciones faltan sin aplicar ninguna.",
    )
    argumentos = analizador.parse_args()

    try:
        return aplicar(solo_verificar=argumentos.verificar)
    except (ErrorMigracion, ErrorConexion) as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
