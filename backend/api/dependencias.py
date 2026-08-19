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

from functools import lru_cache

from contratos.enums import ModoOperacion
from contratos.repositorio import Repositorio
from contratos.simulados.datos import RepositorioSimulado


@lru_cache(maxsize=1)
def _repositorio_simulado() -> RepositorioSimulado:
    """
    Una sola instancia para toda la vida del proceso.

    Importa porque `RepositorioSimulado` emite un aviso en el registro cada vez
    que se construye, y porque usa una semilla fija: instanciarlo por peticion
    reiniciaria su generador y dos llamadas iguales devolverian cosas distintas.
    """
    return RepositorioSimulado()


def obtener_repositorio() -> Repositorio:
    """
    Devuelve la implementacion activa del repositorio.

    Hoy es el simulado. En H6.2 pasara a ser el de PostgreSQL, decidiendo aqui
    segun la configuracion, y ningun endpoint cambia.
    """
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
