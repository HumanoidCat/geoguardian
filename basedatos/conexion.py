"""
Conexion a PostgreSQL. Dueno: Cesar. Historia H1.3, issue #37.

Un solo lugar para armar la cadena y abrir la conexion. Antes esto estaba
duplicado en el aplicador de migraciones y en el cargador, y una correccion en
uno no llegaba al otro.

POR QUE ESPERA A QUE LA BASE ARRANQUE

La Definition of Done de la issue exige que todo funcione desde
`docker compose up` en una maquina limpia. Sobre un volumen vacio, PostgreSQL
tarda entre veinte segundos y un minuto en inicializarse: crea el cluster y
ejecuta los scripts de infra/docker/init-db/. Durante ese lapso el puerto ya esta
publicado, asi que la conexion se establece y el servidor la cierra enseguida:

    connection failed: server closed the connection unexpectedly

Si las herramientas fallan ahi, cualquiera que siga los pasos del README a
velocidad normal se estrella, y la historia no cumple su propia Definition of
Done. Por eso `conectar` reintenta durante un tiempo acotado en vez de rendirse
al primer intento.
"""

from __future__ import annotations

import os
import time

import psycopg
from dotenv import load_dotenv

# Tiempo maximo esperando a que la base acepte conexiones. Un minuto y medio
# cubre con holgura la inicializacion de un volumen vacio.
ESPERA_MAXIMA = 90.0
INTERVALO = 2.0


class ErrorConexion(Exception):
    """No se pudo construir la cadena o alcanzar la base."""


def cadena_conexion() -> str:
    """
    Arma la cadena de conexion desde .env.

    Los valores por defecto son los MISMOS que declara docker-compose.yml:

        POSTGRES_DB:       ${POSTGRES_DB:-geoguardian}
        POSTGRES_USER:     ${POSTGRES_USER:-geoguardian}
        POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?...}   <- sin defecto, obligatoria

    Tienen que coincidir: si estos guiones exigieran un usuario que compose deja
    en su valor por defecto, se conectarian como alguien que la base no creo.
    docker-compose.yml es archivo compartido, asi que la fuente de verdad es el y
    este modulo lo refleja.

    POSTGRES_HOST vale 'db' en .env, que es el nombre del servicio dentro de la
    red de Docker. Estos guiones corren desde la maquina anfitriona, fuera de esa
    red, asi que usan el puerto publicado en localhost.
    """
    load_dotenv()

    contrasena = os.getenv("POSTGRES_PASSWORD")
    if not contrasena:
        raise ErrorConexion(
            "Falta POSTGRES_PASSWORD en .env. Es la unica variable de conexion sin "
            "valor por defecto, tanto aqui como en docker-compose.yml."
        )

    return (
        f"host={os.getenv('POSTGRES_HOST_LOCAL', 'localhost')} "
        f"port={os.getenv('POSTGRES_PORT') or '5432'} "
        f"dbname={os.getenv('POSTGRES_DB') or 'geoguardian'} "
        f"user={os.getenv('POSTGRES_USER') or 'geoguardian'} "
        f"password={contrasena}"
    )


def conectar(
    autocommit: bool = False,
    espera_maxima: float = ESPERA_MAXIMA,
) -> psycopg.Connection:
    """
    Abre una conexion, reintentando mientras la base termina de arrancar.

    Reintenta solo ante OperationalError, que es la familia de fallos de
    disponibilidad: servidor que aun no acepta conexiones, que cierra la conexion
    a medias, o que todavia no resolvio el nombre. Cualquier otro error se
    propaga sin reintentar: una contrasena equivocada no mejora esperando.
    """
    cadena = cadena_conexion()
    limite = time.monotonic() + espera_maxima
    ultimo: psycopg.OperationalError | None = None
    aviso_mostrado = False

    while True:
        try:
            conexion = psycopg.connect(cadena, autocommit=autocommit)
        except psycopg.OperationalError as error:
            ultimo = error
        else:
            # Cierra la linea de puntos para que la salida siguiente no quede
            # pegada al aviso. Esa salida va a la evidencia del Pull Request.
            if aviso_mostrado:
                print(" listo.")
            return conexion

        if time.monotonic() >= limite:
            break

        if aviso_mostrado:
            print(".", end="", flush=True)
        else:
            print(
                "La base todavia no acepta conexiones. Es normal justo despues "
                "de 'docker compose up' sobre un volumen vacio.\n"
                f"Reintentando hasta {espera_maxima:.0f} segundos",
                end="",
                flush=True,
            )
            aviso_mostrado = True

        time.sleep(INTERVALO)

    if aviso_mostrado:
        print()

    raise ErrorConexion(
        f"No se pudo conectar a la base despues de {espera_maxima:.0f} segundos.\n"
        f"{ultimo}\n"
        "Comproba el estado del contenedor: docker compose ps"
    )
