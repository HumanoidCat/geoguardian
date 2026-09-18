"""
Pruebas de `/salud` con la base caida. Incidencia I-61.

POR QUE ESTE ARCHIVO EXISTE

I-61 no lo encontro ninguna prueba: lo encontro el CA-3 de H8.3, que fue la
primera comprobacion del proyecto que corrio `/salud` con PostgreSQL **detenido
de verdad**. Los tres controles que miraban ese endpoint -CA-1 y CA-8 de H6.1,
CA-7 con el repositorio falso- corren con algo que responde del otro lado:
**ninguno ejercita la rama que el endpoint fue escrito para cubrir**, asi que los
tres podian estar en verde mientras el unico caso que importa estaba roto.

Estas pruebas apagan la base. No hay base que apagar -no se necesita ninguna-:
se usa un repositorio escrito a mano que se comporta como el real cuando
PostgreSQL no contesta, que es `esta_viva()` atrapando y `ultima_ingesta()`
propagando.

NO SE IMPORTA NINGUNA IMPLEMENTACION CONCRETA, y no es casualidad: el CA-6 de
`verificar_h61.py` marca a quien lo haga. Los dobles de abajo cumplen lo que
`estado_de` usa y nada mas.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from backend.api.aplicacion import crear_aplicacion
from backend.api.dependencias import (
    EstadoDeLaBase,
    estado_de,
    obtener_repositorio,
    ultima_ingesta_de,
)

CUANDO = datetime(2026, 9, 17, 4, 30, 0)


class ConexionCerrada(Exception):
    """Lo que viaja cuando la conexion murio.

    Se imita en vez de importar `psycopg.OperationalError` para que estas pruebas
    no dependan del controlador: lo que se prueba es la composicion, no psycopg.
    """


class BaseCaida:
    """El repositorio real con PostgreSQL apagado.

    Reproduce las dos decisiones que, por separado, son correctas: `esta_viva()`
    atrapa y devuelve False; `ultima_ingesta()` propaga, por I-41.

    Cuenta si le preguntaron por la ingesta, porque **esa es la afirmacion del
    arreglo**: no es que se atrape el error, es que no se hace la pregunta.
    """

    def __init__(self) -> None:
        self.le_preguntaron_por_la_ingesta = False

    def esta_viva(self) -> bool:
        return False

    def ultima_ingesta(self) -> datetime | None:
        self.le_preguntaron_por_la_ingesta = True
        raise ConexionCerrada("the connection is closed")


class BaseViva:
    """La base contesta. `cuando` es None para «nunca corrio una ingesta»."""

    def __init__(self, cuando: datetime | None = CUANDO) -> None:
        self._cuando = cuando
        self.le_preguntaron_por_la_ingesta = False

    def esta_viva(self) -> bool:
        return True

    def ultima_ingesta(self) -> datetime | None:
        self.le_preguntaron_por_la_ingesta = True
        return self._cuando


def cliente_con(repositorio) -> TestClient:
    aplicacion = crear_aplicacion()
    aplicacion.dependency_overrides[obtener_repositorio] = lambda: repositorio
    return TestClient(aplicacion)


# ===========================================================================
# LA COMPOSICION
# ===========================================================================


def test_con_la_base_caida_el_estado_no_lanza():
    """El arreglo, en una linea: componer los dos campos ya no revienta."""
    assert estado_de(BaseCaida()) == EstadoDeLaBase(conectada=False, ultima_ingesta=None)


def test_con_la_base_caida_no_se_le_pregunta_por_la_ingesta():
    """La afirmacion exacta del arreglo, y no una parecida.

    No se atrapa el error de `ultima_ingesta()`: **no se hace la pregunta**. La
    diferencia importa, porque atraparlo convertiria un `permission denied` sobre
    `control.bitacora_etl` en «no hay base», que es una mentira distinta.
    """
    repositorio = BaseCaida()
    estado_de(repositorio)
    assert repositorio.le_preguntaron_por_la_ingesta is False


def test_con_la_base_viva_la_fecha_se_sirve():
    assert estado_de(BaseViva()) == EstadoDeLaBase(conectada=True, ultima_ingesta=CUANDO)


def test_con_la_base_viva_y_sin_ingestas_el_campo_va_null():
    """La segunda fila de la tabla del contrato: `true` + `null` = nunca corrio.

    Es distinto de la tercera -`false` + `null` = no se pudo saber- y por eso el
    par de campos alcanza sin agregar ninguno nuevo.
    """
    assert estado_de(BaseViva(cuando=None)) == EstadoDeLaBase(conectada=True, ultima_ingesta=None)


def test_el_metodo_suelto_sigue_propagando_a_proposito():
    """SABOTAJE. Lo que el arreglo NO hizo, congelado para que nadie lo «arregle».

    `ultima_ingesta_de` tiene que seguir lanzando cuando la base no contesta: es
    I-41, y ademas `obtener_indices` depende de eso -su docstring dice que servir
    el indice guardado con la base caida diria que el dato esta al dia sin poder
    saberlo-.

    Si alguien decide «simplificar» metiendo un `try/except` ahi adentro, /salud
    va a seguir pasando y /indices va a empezar a mentir. Esta prueba se pone en
    rojo antes.
    """
    with pytest.raises(ConexionCerrada):
        ultima_ingesta_de(BaseCaida())


# ===========================================================================
# EL ENDPOINT, QUE ES DONDE SE VEIA EL 500
# ===========================================================================


def test_salud_responde_200_con_la_base_caida():
    """El defecto de I-61, medido donde se manifestaba.

    Antes del arreglo esto era un 500 y el visor se quedaba sin respuesta.
    """
    respuesta = cliente_con(BaseCaida()).get("/salud")
    assert respuesta.status_code == 200


def test_salud_no_afirma_que_hay_base_cuando_no_la_hay():
    cuerpo = cliente_con(BaseCaida()).get("/salud").json()
    assert cuerpo["base_datos_conectada"] is False
    assert cuerpo["ultima_ingesta"] is None


def test_salud_con_la_base_viva_no_cambio():
    """El arreglo no puede alterar la respuesta cuando todo esta bien."""
    cuerpo = cliente_con(BaseViva()).get("/salud").json()
    assert cuerpo["base_datos_conectada"] is True
    assert cuerpo["ultima_ingesta"] is not None
    assert cuerpo["modo"] == "real"
