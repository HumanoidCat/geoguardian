"""
Pruebas del SPI. Historia H2.3.

Las pruebas de forma corren contra las dos implementaciones, la real y el
simulado, porque las dos deben cumplir el mismo contrato. Las pruebas de valor
corren solo contra la real: el simulado calcula una puntuacion z y no un SPI, y
el propio simulado lo advierte en su docstring.

Cubre el caso `test_spi_primeras_posiciones_none` planificado en
`docs/investigacion/plan-pruebas.md`, seccion 3.3.
"""

from __future__ import annotations

import random

import pytest

from backend.senales.spi import CalculadorSPI, acumular, ajustar_gamma
from contratos.simulados.senales import ProcesadorSenalesSimulado

SEMILLA = 20260818


@pytest.fixture(params=[CalculadorSPI(), ProcesadorSenalesSimulado()], ids=["real", "simulado"])
def procesador(request):
    """Las dos implementaciones del contrato, para las pruebas de forma."""
    return request.param


@pytest.fixture
def serie_larga() -> list[float | None]:
    """35 anios de precipitacion mensual sintetica con sesgo positivo."""
    rnd = random.Random(SEMILLA)
    return [round(rnd.gammavariate(2.0, 50.0), 1) for _ in range(420)]


# --------------------------------------------------------------------------- #
# Forma del resultado: obligatorio en las dos implementaciones                  #
# --------------------------------------------------------------------------- #


def test_spi_primeras_posiciones_none(procesador, serie_larga):
    """
    Las primeras `ventana_meses` posiciones son None por definicion del indice.

    Prioridad 1 del plan de pruebas: no se rellenan con ceros, porque un cero es
    un valor de sequia neutra que nadie calculo.
    """
    salida = procesador.spi(serie_larga, 3)

    assert salida[:3] == [None, None, None]
    assert salida[3] is not None


def test_spi_no_cambia_el_largo(procesador, serie_larga):
    assert len(procesador.spi(serie_larga, 3)) == len(serie_larga)


def test_spi_una_ventana_con_hueco_sale_none(procesador):
    """
    Un hueco contamina las `ventana` posiciones que lo contienen.

    Sumar solo los meses presentes daria un acumulado sistematicamente menor, y
    el SPI lo leeria como sequia donde lo que hay es falta de dato.
    """
    serie: list[float | None] = [50.0] * 30
    serie[15] = None

    salida = procesador.spi(serie, 3)

    assert salida[15] is None
    assert salida[16] is None
    assert salida[17] is None


def test_spi_rechaza_ventana_menor_que_uno(procesador, serie_larga):
    with pytest.raises(ValueError):
        procesador.spi(serie_larga, 0)


def test_spi_serie_demasiado_corta_devuelve_none(procesador):
    """Sin muestra suficiente no se ajusta nada, y se devuelve None, no 0.0."""
    salida = procesador.spi([10.0, 20.0, 30.0], 3)

    assert all(v is None for v in salida)


# --------------------------------------------------------------------------- #
# Valor del indice: solo la implementacion real                                 #
# --------------------------------------------------------------------------- #


def test_spi_rechaza_precipitacion_negativa():
    """
    Una serie con lluvia negativa se rechaza con el motivo, no se recorta.

    Es el caso que produce `filtrar_ruido` si alguien lo aplica a precipitacion
    en contra de la decision D-17: los coeficientes de Savitzky-Golay son
    negativos en los extremos. El mensaje de error lo dice para que quien lo
    encuentre no tenga que deducirlo.
    """
    serie: list[float | None] = [10.0, -2.5, 30.0, 40.0, 50.0, 60.0]

    with pytest.raises(ValueError, match="D-17"):
        CalculadorSPI().spi(serie, 3)


def test_spi_ronda_cero_en_una_serie_sin_anomalias(serie_larga):
    """
    Sobre una serie estacionaria el SPI medio debe rondar cero.

    Es la propiedad que define un indice estandarizado: mide desviaciones
    respecto de lo normal, asi que sin anomalias no hay senal.
    """
    salida = CalculadorSPI().spi(serie_larga, 3)
    valores = [v for v in salida if v is not None]

    assert abs(sum(valores) / len(valores)) < 0.15


def test_spi_es_monotono_respecto_de_la_lluvia(serie_larga):
    """Mas lluvia acumulada nunca puede dar un SPI menor."""
    salida = CalculadorSPI().spi(serie_larga, 3)
    acumulados = acumular(serie_larga, 3)

    pares = [
        (a, s) for a, s in zip(acumulados, salida, strict=True) if a is not None and s is not None
    ]
    pares.sort()

    # strict=False a proposito: se comparan pares consecutivos, asi que las dos
    # secuencias tienen largos distintos por construccion.
    for (_, spi_menor), (_, spi_mayor) in zip(pares, pares[1:], strict=False):
        assert spi_mayor >= spi_menor - 1e-9


def test_spi_detecta_un_periodo_seco(serie_larga):
    """Un tramo con la decima parte de lluvia debe salir claramente negativo."""
    serie = list(serie_larga)
    for i in range(200, 212):
        serie[i] = serie[i] / 10.0  # type: ignore[operator]

    salida = CalculadorSPI().spi(serie, 3)
    en_el_tramo = [salida[i] for i in range(205, 212) if salida[i] is not None]

    assert sum(en_el_tramo) / len(en_el_tramo) < -1.0  # type: ignore[operator]


def test_spi_admite_meses_de_cero(serie_larga):
    """
    Una serie con meses de 0,0 mm no rompe el ajuste.

    La gamma no esta definida en cero. La correccion de la OMM separa la masa de
    ceros en una probabilidad q y ajusta la gamma solo sobre los positivos. Sin
    eso, este caso lanzaria, y Tilaran tiene meses de 0 mm en estacion seca.
    """
    serie = list(serie_larga)
    for i in range(0, len(serie), 12):
        serie[i] = 0.0

    salida = CalculadorSPI().spi(serie, 1)

    assert any(v is not None for v in salida)


# --------------------------------------------------------------------------- #
# Utilidades                                                                    #
# --------------------------------------------------------------------------- #


def test_acumular_es_una_suma_movil():
    serie: list[float | None] = [1.0, 2.0, 3.0, 4.0, 5.0]

    assert acumular(serie, 2) == [None, None, 5.0, 7.0, 9.0]


def test_acumular_marca_none_la_ventana_con_hueco():
    serie: list[float | None] = [1.0, 2.0, None, 4.0, 5.0]

    salida = acumular(serie, 2)

    assert salida[2] is None
    assert salida[3] is None
    assert salida[4] == 9.0


def test_ajustar_gamma_cuenta_la_proporcion_de_ceros():
    muestra = [0.0, 0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0]

    forma, escala, prob_cero = ajustar_gamma(muestra)

    assert prob_cero == pytest.approx(0.2)
    assert forma is not None and forma > 0
    assert escala is not None and escala > 0


def test_ajustar_gamma_sin_positivos_suficientes_no_ajusta():
    forma, escala, prob_cero = ajustar_gamma([0.0, 0.0, 0.0, 5.0])

    assert forma is None
    assert escala is None
    assert prob_cero == pytest.approx(0.75)


def test_ajustar_gamma_serie_constante_no_ajusta():
    """
    Sin dispersion no hay anomalia que medir, y el ajuste ademas diverge.

    La forma de la gamma tiende a infinito cuando todos los valores son iguales
    y scipy lanza al no poder resolver. Se detecta antes y se devuelve None, no
    0.0: un cero seria un valor de sequia neutra que nadie calculo.

    Lo encontro esta misma prueba sobre una serie de 30 meses de 50 mm cada uno.
    """
    forma, escala, _ = ajustar_gamma([150.0] * 20)

    assert forma is None
    assert escala is None


def test_spi_de_una_serie_constante_es_todo_none():
    """Comprobacion de extremo a extremo del caso anterior."""
    salida = CalculadorSPI().spi([50.0] * 30, 3)

    assert all(v is None for v in salida)
