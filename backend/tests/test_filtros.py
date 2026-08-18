"""
Pruebas del filtro de ruido. Historia H2.1.

Las mismas funciones se corren contra el modulo real y contra el simulado de
`contratos/simulados/senales.py`, porque las dos implementaciones deben cumplir
el mismo contrato. Si una prueba pasa con uno y falla con el otro, el contrato
no esta bien especificado o una de las dos lo incumple.

Corresponden al caso `test_filtrar_ruido_preserva_huecos` planificado en
`docs/investigacion/plan-pruebas.md`, seccion 3.3.
"""

from __future__ import annotations

import pytest

from backend.senales.filtros import FiltroSavitzkyGolay, _tramos_continuos
from contratos.senales import ProcesadorSenales
from contratos.simulados.senales import ProcesadorSenalesSimulado

# Se prueban las dos implementaciones con las mismas funciones.
IMPLEMENTACIONES = [FiltroSavitzkyGolay(), ProcesadorSenalesSimulado()]
IDS = ["real", "simulado"]


@pytest.fixture(params=IMPLEMENTACIONES, ids=IDS)
def procesador(request):
    return request.param


# --------------------------------------------------------------------------- #
# Invariante 1 del proyecto: los huecos se preservan                            #
# --------------------------------------------------------------------------- #


def test_filtrar_ruido_preserva_huecos(procesador):
    """Una posicion que entra como None sale como None. Prioridad 1 del plan."""
    serie: list[float | None] = [1.0, 2.0, None, 4.0, 5.0, None, 7.0, 8.0, 9.0]

    salida = procesador.filtrar_ruido(serie, 3)

    posiciones_entrada = [i for i, v in enumerate(serie) if v is None]
    posiciones_salida = [i for i, v in enumerate(salida) if v is None]
    assert posiciones_salida == posiciones_entrada


def test_filtrar_ruido_no_cambia_el_largo(procesador):
    """La salida tiene una posicion por cada posicion de la entrada."""
    serie: list[float | None] = [1.0, None, 3.0, 4.0, 5.0]

    assert len(procesador.filtrar_ruido(serie, 3)) == len(serie)


def test_filtrar_ruido_serie_toda_vacia(procesador):
    """Una serie sin ningun dato sale igual, sin lanzar."""
    serie: list[float | None] = [None] * 10

    assert procesador.filtrar_ruido(serie, 3) == serie


def test_filtrar_ruido_serie_vacia(procesador):
    """Una serie de largo cero no es un error."""
    assert procesador.filtrar_ruido([], 3) == []


# --------------------------------------------------------------------------- #
# Comportamiento propio de Savitzky-Golay                                       #
# --------------------------------------------------------------------------- #


def test_savgol_preserva_mejor_el_maximo_que_la_media_movil():
    """
    El motivo por el que se eligio este filtro, comprobado.

    Un pico aislado de precipitacion sobre una serie plana. La media movil del
    simulado lo aplasta; Savitzky-Golay conserva mucha mas altura. Importa
    porque los umbrales de lluvia intensa se definen sobre percentiles P95 y
    P99: achatar los picos los sesga hacia abajo.
    """
    serie: list[float | None] = [0.0] * 6 + [100.0] + [0.0] * 6
    i_pico = 6

    con_savgol = FiltroSavitzkyGolay().filtrar_ruido(serie, 5)
    con_media_movil = ProcesadorSenalesSimulado().filtrar_ruido(serie, 5)

    assert con_savgol[i_pico] > con_media_movil[i_pico]


def test_filtrar_ruido_rechaza_ventana_par():
    """Una ventana par no puede estar centrada."""
    with pytest.raises(ValueError, match="impar"):
        FiltroSavitzkyGolay().filtrar_ruido([1.0, 2.0, 3.0], 4)


def test_filtrar_ruido_rechaza_ventana_menor_que_el_orden():
    """Con menos muestras que el orden del polinomio el ajuste no esta determinado."""
    with pytest.raises(ValueError, match="orden"):
        FiltroSavitzkyGolay(orden=3).filtrar_ruido([1.0, 2.0, 3.0], 3)


def test_tramo_mas_corto_que_la_ventana_no_se_filtra():
    """
    Un tramo corto se devuelve tal cual, no se filtra con ventana reducida.

    Es deliberado: cambiar la ventana segun el tramo produciria un suavizado no
    uniforme a lo largo de la serie.
    """
    serie: list[float | None] = [1.0, 9.0, 1.0, None, 1.0, 5.0, 1.0, 5.0, 1.0, 5.0, 1.0]

    salida = FiltroSavitzkyGolay().filtrar_ruido(serie, 7)

    assert salida[0:3] == [1.0, 9.0, 1.0]


def test_no_se_interpola_a_traves_de_un_hueco():
    """
    Los tramos separados por un hueco se filtran por separado.

    Si el filtro cruzara el hueco, el valor del ultimo dia antes del hueco
    quedaria influido por dias que no son sus vecinos reales.
    """
    izquierda: list[float | None] = [10.0] * 9
    derecha: list[float | None] = [0.0] * 9
    serie = izquierda + [None] + derecha

    salida = FiltroSavitzkyGolay().filtrar_ruido(serie, 7)

    assert salida[8] == pytest.approx(10.0, abs=1e-9)
    assert salida[10] == pytest.approx(0.0, abs=1e-9)


# --------------------------------------------------------------------------- #
# Contrato y utilidades                                                         #
# --------------------------------------------------------------------------- #


def test_la_firma_coincide_con_la_del_contrato():
    """
    El metodo existe y acepta los argumentos que declara el contrato.

    No se comprueba `isinstance(..., ProcesadorSenales)` a proposito: esta clase
    implementa solo `filtrar_ruido`, y el protocolo exige ademas `espectro`,
    `spi`, `anomalia` y `remuestrear`, que corresponden a H2.2, H2.3, H2.4 y
    H2.6. La verificacion estructural completa se agrega cuando exista la
    implementacion de los cinco metodos; hacerla ahora daria un fallo que no
    indica ningun defecto de esta historia.
    """
    import inspect

    firma_real = inspect.signature(FiltroSavitzkyGolay().filtrar_ruido)
    firma_contrato = inspect.signature(ProcesadorSenales.filtrar_ruido)

    parametros_reales = [p for p in firma_real.parameters]
    parametros_contrato = [p for p in firma_contrato.parameters if p != "self"]

    assert parametros_reales == parametros_contrato


@pytest.mark.parametrize(
    "serie, esperado",
    [
        ([1.0, 2.0, 3.0], [(0, 3)]),
        ([None, 1.0, 2.0], [(1, 3)]),
        ([1.0, None, 3.0], [(0, 1), (2, 3)]),
        ([None, None], []),
        ([], []),
    ],
)
def test_tramos_continuos(serie, esperado):
    assert _tramos_continuos(serie) == esperado
