"""
Pruebas del analisis espectral. Historia H2.2.

Las pruebas de forma y las de deteccion de ciclos corren contra las dos
implementaciones, la real y el simulado, porque las dos deben cumplir el mismo
contrato.

Siguiendo el aviso del docstring del simulado, la deteccion se comprueba
**por casillero**: se verifica que el casillero dominante sea el mas cercano a
la frecuencia buscada, no que el periodo valga 365 exacto. La resolucion en
frecuencia hace que el pico caiga en el casillero vecino, y eso es correcto.

Cubre el caso `test_espectro_lanza_valueerror_con_huecos` planificado en
`docs/investigacion/plan-pruebas.md`, seccion 3.3.
"""

from __future__ import annotations

import math
import random

import pytest

from backend.senales.espectro import (
    DIAS_POR_ANO,
    FRECUENCIA_ANUAL,
    FRECUENCIA_SEMIANUAL,
    AnalizadorEspectral,
    casillero_mas_cercano,
    picos_principales,
    razon_semianual_anual,
)
from contratos.simulados.senales import ProcesadorSenalesSimulado

SEMILLA = 20260819
ANIOS = 8
DIAS = int(ANIOS * DIAS_POR_ANO)


@pytest.fixture(
    params=[AnalizadorEspectral(), ProcesadorSenalesSimulado()],
    ids=["real", "simulado"],
)
def procesador(request):
    return request.param


def _onda(periodo: float, amplitud: float, dias: int = DIAS) -> list[float]:
    return [amplitud * math.sin(2 * math.pi * d / periodo) for d in range(dias)]


@pytest.fixture
def serie_anual() -> list[float | None]:
    """Un ciclo anual limpio, sin nada mas."""
    return list(_onda(DIAS_POR_ANO, 10.0))


@pytest.fixture
def serie_bimodal() -> list[float | None]:
    """
    Ciclo anual mas un semianual de la mitad de amplitud, con algo de ruido.

    Reproduce la forma del regimen del Pacifico: dos maximos de lluvia
    separados por la pausa del veranillo.
    """
    rnd = random.Random(SEMILLA)
    anual = _onda(DIAS_POR_ANO, 10.0)
    semianual = _onda(DIAS_POR_ANO / 2, 5.0)
    return [a + s + rnd.gauss(0, 0.5) for a, s in zip(anual, semianual, strict=True)]


# --------------------------------------------------------------------------- #
# El contrato: huecos y validaciones                                            #
# --------------------------------------------------------------------------- #


def test_espectro_lanza_valueerror_con_huecos(procesador, serie_anual):
    """
    Prioridad 1 del plan: interpolar en silencio antes de una transformada
    introduce componentes espectrales que no estan en el dato.
    """
    serie = list(serie_anual)
    serie[100] = None
    serie[200] = None

    with pytest.raises(ValueError) as error:
        procesador.espectro(serie, 1.0)

    # El mensaje debe decir cuantos faltan, para saber si es un hueco aislado
    # o media serie.
    assert "2" in str(error.value)


def test_espectro_rechaza_frecuencia_de_muestreo_no_positiva(procesador, serie_anual):
    with pytest.raises(ValueError):
        procesador.espectro(serie_anual, 0)


def test_espectro_rechaza_serie_demasiado_corta(procesador):
    with pytest.raises(ValueError):
        procesador.espectro([1.0], 1.0)


def test_las_dos_listas_tienen_el_mismo_largo(procesador, serie_anual):
    frecuencias, magnitudes = procesador.espectro(serie_anual, 1.0)

    assert len(frecuencias) == len(magnitudes)


# --------------------------------------------------------------------------- #
# Deteccion de ciclos                                                           #
# --------------------------------------------------------------------------- #


def test_detecta_el_ciclo_anual(procesador, serie_anual):
    """
    Sobre una onda anual pura, el casillero dominante debe ser el mas cercano a
    la frecuencia anual.

    Se comprueba por casillero y no por periodo: con series de pocos anios el
    pico cae en el casillero vecino a 365 dias, y eso es correcto.
    """
    frecuencias, magnitudes = procesador.espectro(serie_anual, 1.0)

    dominante = max(range(1, len(magnitudes)), key=lambda i: magnitudes[i])

    assert dominante == casillero_mas_cercano(frecuencias, FRECUENCIA_ANUAL)


def test_la_media_no_domina_el_espectro(procesador):
    """
    Se resta la media antes de transformar.

    Sin eso, sobre una serie con media grande la componente continua dominaria
    y el ciclo anual quedaria invisible. La precipitacion siempre tiene media
    positiva, asi que este caso no es teorico.
    """
    serie: list[float | None] = [v + 1000.0 for v in _onda(DIAS_POR_ANO, 10.0)]

    frecuencias, magnitudes = procesador.espectro(serie, 1.0)
    dominante = max(range(1, len(magnitudes)), key=lambda i: magnitudes[i])

    assert dominante == casillero_mas_cercano(frecuencias, FRECUENCIA_ANUAL)
    assert magnitudes[0] < magnitudes[dominante]


def test_detecta_los_dos_ciclos_de_un_regimen_bimodal(procesador, serie_bimodal):
    """
    El caso que importa para Tilaran: anual y semianual separados.

    El semianual es la firma del veranillo (Alfaro, 2014). Si el espectro no lo
    separara del anual, no se podria distinguir un julio seco normal de una
    sequia.
    """
    frecuencias, magnitudes = procesador.espectro(serie_bimodal, 1.0)

    i_anual = casillero_mas_cercano(frecuencias, FRECUENCIA_ANUAL)
    i_semianual = casillero_mas_cercano(frecuencias, FRECUENCIA_SEMIANUAL)

    assert i_anual != i_semianual
    assert magnitudes[i_anual] > magnitudes[i_semianual]

    # Los dos deben destacar sobre el fondo.
    fondo = sorted(magnitudes[1:])[len(magnitudes) // 2]
    assert magnitudes[i_semianual] > 5 * fondo


def test_la_amplitud_recuperada_se_parece_a_la_real(serie_anual):
    """
    El factor 2/n devuelve la amplitud en las unidades de la serie.

    Solo contra la implementacion real: el simulado rellena con ceros, lo que
    reparte la amplitud entre casilleros vecinos y baja el maximo.
    """
    frecuencias, magnitudes = AnalizadorEspectral().espectro(serie_anual, 1.0)

    i = casillero_mas_cercano(frecuencias, FRECUENCIA_ANUAL)

    assert magnitudes[i] == pytest.approx(10.0, rel=0.15)


# --------------------------------------------------------------------------- #
# Interpretacion fisica                                                         #
# --------------------------------------------------------------------------- #


def test_picos_principales_no_devuelve_el_mismo_pico_repetido(serie_bimodal):
    """
    Un pico real ocupa varios casilleros contiguos. Sin separacion minima, los
    cinco picos mas altos serian los cinco vecinos del mismo maximo.
    """
    frecuencias, magnitudes = AnalizadorEspectral().espectro(serie_bimodal, 1.0)

    picos = picos_principales(frecuencias, magnitudes, cuantos=2, separacion_minima=3)
    periodos = [p for p, _ in picos]

    assert len(periodos) == 2
    assert abs(periodos[0] - periodos[1]) > 30


def test_picos_principales_rechaza_separacion_invalida(serie_anual):
    frecuencias, magnitudes = AnalizadorEspectral().espectro(serie_anual, 1.0)

    with pytest.raises(ValueError, match="separacion"):
        picos_principales(frecuencias, magnitudes, separacion_minima=0)


def test_la_razon_semianual_refleja_la_amplitud_puesta(serie_bimodal):
    """El semianual se genero con la mitad de amplitud que el anual."""
    frecuencias, magnitudes = AnalizadorEspectral().espectro(serie_bimodal, 1.0)

    assert razon_semianual_anual(frecuencias, magnitudes) == pytest.approx(0.5, rel=0.25)


def test_la_razon_es_none_si_no_hay_ciclo_anual():
    """
    None y no cero: cero significaria "no hay semianual", que es otra cosa.
    """
    frecuencias = [0.0, FRECUENCIA_ANUAL, FRECUENCIA_SEMIANUAL]
    magnitudes = [0.0, 0.0, 3.0]

    assert razon_semianual_anual(frecuencias, magnitudes) is None
