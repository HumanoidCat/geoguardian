"""
Deja escrito CONTRA QUE BASE corrio un guion de conteo, y permite apuntarlo a otra.

POR QUE EXISTE

Los conteos de `contar_ingesta.py` y `contar_riesgo.py` son la evidencia del
**CA-4 de H11.6**: se corren contra las dos puntas -la base local y la
publicada- y tienen que dar lo mismo.

Una salida que no dice a que base le pregunto **no puede demostrar eso**. Dos
corridas contra la misma base se ven exactamente igual que dos corridas contra
bases distintas que coinciden; y la primera version se ve mejor, porque siempre
cuadra.

Paso el 2026-09-05, armando la evidencia de H11.6: la corrida que tenia que ser
contra la nube salio contra la base local, por estar en la ventana equivocada.
Las cifras coincidian -por supuesto que coincidian- y la unica senal fue un
`KeyError` de un comando distinto que iba en el mismo bloque. Sin esa
casualidad, la evidencia habria quedado archivada. Es la incidencia **I-38**.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import dotenv_values

CLAVES = (
    "POSTGRES_HOST_LOCAL",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
)


class ErrorDestino(Exception):
    """El archivo de destino no sirve para apuntar a ningun lado."""


def agregar_argumento(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--destino",
        type=Path,
        default=None,
        metavar="ARCHIVO",
        help="archivo tipo .env con la base a la que preguntar (por omision, la de .env)",
    )


def apuntar_a(archivo: Path | None) -> None:
    """
    Pone en el entorno las claves del archivo, para que `conectar()` las use.

    Exige **las cinco**. Heredar una sola de `.env` es como se termina
    preguntandole a la base equivocada: host de la nube con la base local, o al
    reves. Si falta alguna, se planta y dice cual.
    """
    if archivo is None:
        return
    valores = dotenv_values(archivo)
    if not valores:
        raise ErrorDestino(f"{archivo} no existe o esta vacio")
    faltan = [c for c in CLAVES if not (valores.get(c) or "").strip()]
    if faltan:
        raise ErrorDestino(
            f"{archivo} no declara: {', '.join(faltan)}.\n"
            "Tienen que estar las cinco. Heredar de .env es como se le pregunta "
            "a la base equivocada sin enterarse."
        )
    for clave in CLAVES:
        os.environ[clave] = valores[clave].strip()


def encabezado(conexion) -> str:
    """Una linea que identifica la base, tomada de la conexion, no de las variables."""
    with conexion.cursor() as cursor:
        cursor.execute(
            "SELECT current_database(), current_user, "
            "coalesce(host(inet_server_addr())::text, 'local'), inet_server_port()"
        )
        base, usuario, servidor, puerto = cursor.fetchone()
    return f"base {base} en {servidor}:{puerto} como {usuario}"
