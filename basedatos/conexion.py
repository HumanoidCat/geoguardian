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

# Fallos en los que el servidor CONTESTO. No mejoran esperando: reintentar solo
# agrega noventa segundos antes de decir lo mismo.
#
# Se comparan por TEXTO porque en un fallo de conexion psycopg no expone el
# sqlstate: ni `error.sqlstate` ni `error.diag.sqlstate` traen nada, porque no
# hay conexion todavia y no hay diagnostico estructurado que leer. Medido contra
# PostgreSQL 16 con psycopg 3.3.5, en seis situaciones distintas. Por eso
# `except OperationalError` a secas no puede separar "el servidor no esta" de
# "el servidor contesto que no": los mete a los dos en la misma clase.
#
# LA LISTA ES DE PERMANENTES A PROPOSITO. Lo que no este aca sigue reintentando,
# que es el comportamiento historico. Un olvido cuesta espera de mas; la regla
# al reves -reintentar solo lo que este en una lista de transitorios- convertiria
# cualquier olvido en un fallo inmediato sobre algo que si se iba a resolver
# solo. En particular `FATAL: the database system is starting up`, que es
# exactamente lo que este reintento existe para cubrir, no esta en la lista y por
# lo tanto se reintenta.
PERMANENTES = (
    "does not exist",  # la base o el rol
    "password authentication failed",
    "no password supplied",
    "no pg_hba.conf entry",
)

# Hosts que significan "la base corre en esta maquina, probablemente en
# docker compose". Sirven para no mandar a mirar `docker compose ps` cuando la
# base esta en otro continente.
HOSTS_LOCALES = frozenset({"localhost", "127.0.0.1", "::1", "db"})


def _contesto_el_servidor(error: psycopg.OperationalError) -> bool:
    """Un mensaje con FATAL -o fe_sendauth- viene del servidor, no de la red."""
    texto = str(error)
    return "FATAL" in texto or "fe_sendauth" in texto


def _es_permanente(error: psycopg.OperationalError) -> bool:
    return _contesto_el_servidor(error) and any(m in str(error) for m in PERMANENTES)


def _base_local() -> bool:
    return os.getenv("POSTGRES_HOST_LOCAL", "localhost") in HOSTS_LOCALES


def _pista_de_disponibilidad() -> str:
    if _base_local():
        return "Comproba el estado del contenedor: docker compose ps"
    return (
        "La base no es local: comproba que el servicio este arriba donde lo "
        "publicaste y que el puerto siga abierto."
    )


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
            # El servidor esta arriba y contesto que no. Esperar no lo arregla.
            #
            # Se envuelve en ErrorConexion y no se deja salir el OperationalError
            # crudo: los seis modulos que llaman a conectar() capturan
            # ErrorConexion y nada mas, asi que propagar otra clase les cambiaria
            # un mensaje limpio por un rastro de pila.
            if _es_permanente(error):
                if aviso_mostrado:
                    print()
                raise ErrorConexion(
                    "El servidor respondio y rechazo la conexion; esperar no lo arregla.\n"
                    f"{error}\n"
                    "Revisa el nombre de la base, el usuario y la contrasena."
                ) from error
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
            razon = (
                "Es normal justo despues de 'docker compose up' sobre un volumen vacio."
                if _base_local()
                else "El servidor todavia no responde."
            )
            print(
                f"La base todavia no acepta conexiones. {razon}\n"
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
        f"{_pista_de_disponibilidad()}"
    )
