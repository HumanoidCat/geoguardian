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

SOBRE EL MODO DE OPERACION

`Salud.modo` no se escribe a mano. Se deriva de que implementacion devolvio esta
funcion, porque un literal 'simulado' seguiria diciendo lo mismo el dia que haya
datos reales, que es justo el escenario que ese campo existe para evitar.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

from contratos.enums import ModoOperacion
from contratos.repositorio import Repositorio
from contratos.simulados.datos import RepositorioSimulado

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


def obtener_repositorio() -> Repositorio:
    """
    Devuelve la implementacion activa, elegida por configuracion.

        GEOGUARDIAN_REPOSITORIO=postgres   -> RepositorioPostgres
        cualquier otra cosa, o sin definir -> RepositorioSimulado

    **EL SIMULADO SIGUE SIENDO EL VALOR POR OMISION, Y ES DELIBERADO.**

    H6.2 dejo el repositorio contra PostgreSQL funcionando, pero solo seis de sus
    dieciseis metodos tienen tabla detras. Entre los diez que faltan estan
    `obtener_riesgo` y `obtener_riesgos_por_fecha`, que son los que alimentan las
    coropletas del visor: activarlo hoy por omision romperia el visor de Avril.

    Lo que H6.2 demuestra es que **la sustitucion funciona sin tocar un endpoint**.
    El dia que existan las tablas, esto pasa a `postgres` y nada mas cambia. Ver la
    cabecera de `repositorio_postgres.py` para la lista de que falta y quien lo trae.
    """
    if os.getenv(VARIABLE_REPOSITORIO, "").strip().lower() == "postgres":
        log.info("Repositorio contra PostgreSQL, elegido por %s", VARIABLE_REPOSITORIO)
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
