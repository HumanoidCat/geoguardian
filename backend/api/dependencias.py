"""
Resolucion de dependencias. Dueno: Cesar. Historia H6.1, issue #59.

ESTE ES EL UNICO ARCHIVO QUE SABE QUE IMPLEMENTACION DE `Repositorio` SE USA.

Los modulos de rutas dependen del PROTOCOLO `contratos.repositorio.Repositorio`,
nunca de una clase concreta. Cuando H6.2 traiga el repositorio contra PostgreSQL,
se cambia el cuerpo de `obtener_repositorio` y **no se toca ni un endpoint**.

Si en cambio las rutas importaran `RepositorioSimulado` directamente, H6.2
obligaria a editar todos los archivos de rutas, que es exactamente lo que el
patron existe para evitar. El criterio CA-6 comprueba que ese import no exista, y
el CA-7 comprueba que sustituir la implementacion funcione de verdad.

H8.3 se apoya en la misma costura: la cache entra aqui, envolviendo el
repositorio, y ningun endpoint se entera. Es CA-2 de esa historia.

SOBRE EL MODO DE OPERACION

`Salud.modo` no se escribe a mano. Se deriva de que implementacion devolvio esta
funcion, porque un literal 'simulado' seguiria diciendo lo mismo el dia que haya
datos reales, que es justo el escenario que ese campo existe para evitar.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

from contratos.enums import ModoOperacion
from contratos.repositorio import Repositorio
from contratos.simulados.datos import RepositorioSimulado

from .cache import (
    VARIABLE_ENCENDIDA,
    RepositorioConCache,
    cache_encendida,
    crear_cache,
)
from .repositorio_postgres import RepositorioPostgres

log = logging.getLogger(__name__)

# Variable que elige la implementacion. Vacia o distinta de 'postgres' deja el
# simulado, que es el valor por omision a proposito. Ver mas abajo.
VARIABLE_REPOSITORIO = "GEOGUARDIAN_REPOSITORIO"


@lru_cache(maxsize=1)
def _repositorio_simulado() -> RepositorioSimulado:
    """
    Una sola instancia para toda la vida del proceso.

    Importa porque `RepositorioSimulado` emite un aviso en el registro cada vez
    que se construye, y porque usa una semilla fija: instanciarlo por peticion
    reiniciaria su generador y dos llamadas iguales devolverian cosas distintas.
    """
    return RepositorioSimulado()


@lru_cache(maxsize=1)
def _repositorio_postgres() -> RepositorioPostgres:
    """Una sola conexion para toda la vida del proceso, como el simulado."""
    return RepositorioPostgres()


@lru_cache(maxsize=1)
def _repositorio_postgres_cacheado() -> RepositorioConCache:
    """
    Una sola cache para toda la vida del proceso.

    `lru_cache` por la misma razon que las dos fabricas de arriba: una cache
    construida por peticion no seria una cache, seria un diccionario vacio.

    De aca sale ademas el techo de consumo. La cache vive en el proceso, asi que
    con varios trabajadores de `uvicorn` hay varias caches y el consumo se
    multiplica. CA-8 lo mide y CA-9 lo demuestra.

    **EL SIMULADO NO SE ENVUELVE, Y NO ES UN OLVIDO.** `modo_de` y
    `base_conectada`, aqui abajo, preguntan `isinstance(repositorio,
    RepositorioSimulado)`. Un envoltorio no es un `RepositorioSimulado`, asi que
    envolverlo haria que /salud respondiera `modo: real` mientras sirve datos
    inventados. Seria **I-41 por tercera vez**: un campo de /salud que dice lo
    que era cierto en otro momento. Ademas no habria nada que ahorrar: el
    simulado no tiene base detras.
    """
    cache = crear_cache()
    log.info("Cache de la API encendida. %s", cache.resumen())
    return RepositorioConCache(_repositorio_postgres(), cache)


def obtener_repositorio() -> Repositorio:
    """
    Devuelve la implementacion activa, elegida por configuracion.

        GEOGUARDIAN_REPOSITORIO=postgres   -> RepositorioPostgres, con cache
        cualquier otra cosa, o sin definir -> RepositorioSimulado, sin cache

    **EL SIMULADO SIGUE SIENDO EL VALOR POR OMISION, Y ES DELIBERADO.**

    H6.2 dejo el repositorio contra PostgreSQL funcionando, pero solo seis de sus
    dieciseis metodos tienen tabla detras. Entre los diez que faltan estan
    `obtener_riesgo` y `obtener_riesgos_por_fecha`, que son los que alimentan las
    coropletas del visor: activarlo hoy por omision romperia el visor de Avril.

    Lo que H6.2 demuestra es que **la sustitucion funciona sin tocar un endpoint**.
    El dia que existan las tablas, esto pasa a `postgres` y nada mas cambia. Ver la
    cabecera de `repositorio_postgres.py` para la lista de que falta y quien lo trae.

    SOBRE LA CACHE (H8.3)

    La cache envuelve **solo** al repositorio contra PostgreSQL. El simulado no se
    envuelve, por lo que explica `_repositorio_postgres_cacheado`.

    `GEOGUARDIAN_CACHE=0` la apaga y el sistema se comporta como antes de H8.3.
    Es la salida si algun dia la cache resulta ser el problema, y es como se mide
    la linea base (CA-12).
    """
    if os.getenv(VARIABLE_REPOSITORIO, "").strip().lower() == "postgres":
        log.info("Repositorio contra PostgreSQL, elegido por %s", VARIABLE_REPOSITORIO)
        if cache_encendida():
            return _repositorio_postgres_cacheado()
        log.info("Cache apagada por %s", VARIABLE_ENCENDIDA)
        return _repositorio_postgres()
    return _repositorio_simulado()


def modo_de(repositorio: Repositorio) -> ModoOperacion:
    """
    Deduce el modo de operacion a partir de la implementacion recibida.

    Se pregunta por la implementacion y no por una variable de entorno para que la
    respuesta de /salud no pueda mentir: si lo que responde es el simulado, el
    campo dice simulado aunque alguien haya configurado otra cosa.
    """
    if isinstance(repositorio, RepositorioSimulado):
        return ModoOperacion.SIMULADO
    return ModoOperacion.REAL


def base_conectada(repositorio: Repositorio) -> bool:
    """
    Si hay una base de datos contestando detras de este repositorio.

    **Se pregunta a la implementacion, por la misma razon que `modo_de`.** Hasta
    el 2026-09-05 este valor era la constante `False` escrita en `rutas.py`, con
    un comentario que decia que era la respuesta honesta porque H6.1 no abria
    conexion. Lo era. H6.2 cerro el 2026-08-27 y nadie volvio a la constante: la
    API sirvio datos reales de PostgreSQL durante nueve dias declarando que no
    tenia base. Ver I-41.

    El simulado responde `False` y es cierto: no hay ninguna base detras.
    """
    if isinstance(repositorio, RepositorioSimulado):
        return False
    return repositorio.esta_viva()


def ultima_ingesta_de(repositorio: Repositorio) -> datetime | None:
    """
    Cuando termino la ultima ingesta exitosa, o None si nunca corrio.

    Con el simulado devuelve None, y tambien es cierto: no hay ETL detras. El
    contrato define None como «nunca se ejecuto», asi que las dos respuestas
    dicen lo mismo por razones distintas y las dos son verdad.
    """
    if isinstance(repositorio, RepositorioSimulado):
        return None
    return repositorio.ultima_ingesta()


@dataclass(frozen=True)
class EstadoDeLaBase:
    """
    Los dos campos de /salud que hablan de la base, **juntos porque no son
    independientes**.

    Viajaban sueltos y cada uno era correcto. Lo que fallaba era ponerlos en la
    misma respuesta: ver `estado_de` e I-61.
    """

    conectada: bool
    ultima_ingesta: datetime | None


def estado_de(repositorio: Repositorio) -> EstadoDeLaBase:
    """
    Los dos campos de la base, preguntados **en orden**. Arregla I-61.

    EL DEFECTO QUE ESTO CIERRA

    `esta_viva()` atrapa y devuelve False -«/salud tiene que poder decir que
    no»-. `ultima_ingesta()` propaga, a proposito, porque devolver None ante un
    error diria «nunca corrio», que es la mentira de I-41. **Las dos decisiones
    son correctas.** Llamadas dentro del mismo `Salud(...)`, la que propaga mata
    la respuesta entera antes de que la que atrapa llegue a servir de algo, y con
    la base caida /salud devolvia 500: justo el unico caso para el que ese
    endpoint existe.

    Decision del PM del 2026-09-17, y **no toca el contrato**: si no hay base, no
    se pregunta por la ingesta. El par de campos ya desambigua sin inventar nada:

        conectada=True   + una fecha  -> la ultima ingesta exitosa
        conectada=True   + None       -> nunca corrio una ingesta
        conectada=False  + None       -> no se pudo saber: no hay base

    POR QUE ACA Y NO EN `rutas.py`

    Porque el defecto **es** la composicion, y una regla de orden escrita en el
    llamador la vuelve a romper el proximo llamador. Aca no hay orden que
    recordar: hay una funcion que devuelve las dos cosas.

    LO QUE NO SE HACE, Y ESTA DECIDIDO

    No se atrapa la excepcion de `ultima_ingesta()` cuando la base SI contesta.
    `repositorio_postgres.py` ya explica por que: un `permission denied` sobre
    `control.bitacora_etl` reportado como «base no conectada» seria una respuesta
    falsa distinta de la que se esta arreglando. Si la base contesta y la consulta
    falla, eso es un defecto y tiene que verse.

    **Ventana declarada:** si la base muere entre las dos llamadas, /salud vuelve
    a dar 500. Es una carrera estrecha, y se declara en vez de taparla con un
    `except` ancho que se tragaria lo de arriba.
    """
    conectada = base_conectada(repositorio)
    if not conectada:
        # No se pregunta por la ingesta: sin base, la respuesta honesta a «cuando
        # fue la ultima» es que no se puede saber, y eso es `None` con
        # `conectada` en False. No es lo mismo que «nunca corrio».
        return EstadoDeLaBase(conectada=False, ultima_ingesta=None)
    return EstadoDeLaBase(conectada=True, ultima_ingesta=ultima_ingesta_de(repositorio))
