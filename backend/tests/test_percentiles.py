"""
Pruebas de los percentiles de precipitacion. Historia H2.7.

No hay implementacion simulada contra la que contrastar: el contrato
`ProcesadorSenales` no tiene metodo de percentiles, asi que este modulo no esta
atado a una firma congelada.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

import pytest

from backend.senales.percentiles import (
    MINIMO_DIAS_HUMEDOS,
    UMBRAL_DIA_HUMEDO_MM,
    _percentil,
    percentil_acumulado,
    percentil_dias_humedos,
    umbrales_por_distrito,
)

SEMILLA = 20260818
INICIO = date(1991, 1, 1)


def _fechas(n: int, inicio: date = INICIO) -> list[date]:
    return [inicio + timedelta(days=i) for i in range(n)]


@pytest.fixture
def serie_diaria() -> tuple[list[float | None], list[date]]:
    """
    Diez anios de precipitacion diaria con estacion seca marcada.

    Diciembre a abril casi sin lluvia, mayo a noviembre lluvioso, que es el
    regimen del Pacifico Norte.
    """
    rnd = random.Random(SEMILLA)
    fechas = _fechas(3653)
    serie: list[float | None] = []

    for f in fechas:
        seco = f.month in (12, 1, 2, 3, 4)
        if seco:
            valor = 0.0 if rnd.random() < 0.9 else round(rnd.gammavariate(1.5, 2.0), 1)
        else:
            valor = 0.0 if rnd.random() < 0.3 else round(rnd.gammavariate(1.8, 8.0), 1)
        serie.append(valor)

    return serie, fechas


# --------------------------------------------------------------------------- #
# Definicion del ETCCDI: solo dias humedos                                      #
# --------------------------------------------------------------------------- #


def test_los_dias_secos_no_entran_al_percentil():
    """
    El umbral de dia humedo es parte de la definicion, no un parametro.

    Si los dias secos entraran, la masa de ceros de la estacion seca desplazaria
    el percentil hacia abajo y el P95 dejaria de representar lluvia muy intensa.
    """
    humedos: list[float | None] = [5.0] * 30
    secos: list[float | None] = [0.0] * 300
    serie = secos + humedos
    fechas = _fechas(len(serie))

    umbral = percentil_dias_humedos(serie, fechas, 95)

    # Con solo los humedos, todos de 5.0, el percentil es 5.0. Si entraran los
    # secos, el P95 de 330 valores mayoritariamente cero seria mucho menor.
    assert umbral == pytest.approx(5.0)


def test_el_umbral_de_dia_humedo_es_un_milimetro():
    """Un dia de 0,9 mm no es humedo; uno de 1,0 si. Zhang et al. (2011)."""
    serie: list[float | None] = [0.9] * 50 + [1.0] * 25
    fechas = _fechas(len(serie))

    umbral = percentil_dias_humedos(serie, fechas, 95)

    assert UMBRAL_DIA_HUMEDO_MM == 1.0
    assert umbral == pytest.approx(1.0)


def test_sin_dias_humedos_suficientes_devuelve_none():
    """
    None y no 0.0: un umbral de cero declararia lluvia intensa cualquier gota.
    """
    serie: list[float | None] = [0.0] * 100 + [5.0] * (MINIMO_DIAS_HUMEDOS - 1)
    fechas = _fechas(len(serie))

    assert percentil_dias_humedos(serie, fechas, 95) is None


def test_p99_es_mayor_o_igual_que_p95(serie_diaria):
    serie, fechas = serie_diaria

    p95 = percentil_dias_humedos(serie, fechas, 95)
    p99 = percentil_dias_humedos(serie, fechas, 99)

    assert p99 >= p95


# --------------------------------------------------------------------------- #
# Periodo base                                                                  #
# --------------------------------------------------------------------------- #


def test_solo_entran_las_fechas_del_periodo_base():
    """Los dias fuera del periodo base no participan del calculo."""
    fechas = _fechas(60, date(1990, 1, 1)) + _fechas(60, date(1991, 1, 1))
    serie: list[float | None] = [100.0] * 60 + [5.0] * 60

    umbral = percentil_dias_humedos(serie, fechas, 95, desde=date(1991, 1, 1))

    # Si los 100.0 de 1990 entraran, el umbral seria mucho mayor que 5.0.
    assert umbral == pytest.approx(5.0)


def test_serie_y_fechas_de_distinto_largo_es_error():
    with pytest.raises(ValueError, match="fechas"):
        percentil_dias_humedos([1.0, 2.0], _fechas(3), 95)


def test_percentil_fuera_de_rango_es_error():
    with pytest.raises(ValueError, match="percentil"):
        percentil_dias_humedos([5.0] * 50, _fechas(50), 100)


def test_rechaza_precipitacion_negativa():
    """Es lo que produce filtrar_ruido sobre lluvia. Ver D-17."""
    serie: list[float | None] = [5.0] * 50 + [-1.0]
    fechas = _fechas(len(serie))

    with pytest.raises(ValueError, match="D-17"):
        percentil_dias_humedos(serie, fechas, 95)


# --------------------------------------------------------------------------- #
# Acumulado de 72 h                                                             #
# --------------------------------------------------------------------------- #


def test_acumulado_suma_la_ventana():
    serie: list[float | None] = [10.0] * 100
    fechas = _fechas(100)

    umbral = percentil_acumulado(serie, fechas, 95, ventana_dias=3)

    assert umbral == pytest.approx(30.0)


def test_acumulado_descarta_las_ventanas_con_hueco():
    """Sumar solo los dias presentes daria un acumulado menor y bajaria el umbral."""
    serie: list[float | None] = [10.0] * 100
    serie[50] = None
    fechas = _fechas(100)

    umbral = percentil_acumulado(serie, fechas, 95, ventana_dias=3)

    # Todas las ventanas validas suman 30. Si alguna con hueco entrara sumando
    # solo dos dias, apareceria un 20 y el percentil bajaria.
    assert umbral == pytest.approx(30.0)


def test_el_acumulado_no_es_el_indice_diario(serie_diaria):
    """
    Las dos cantidades difieren, y por eso no deben llamarse igual.

    El percentil sobre acumulado de 72 h es sistematicamente mayor que el
    percentil diario de dias humedos, porque suma tres dias. Llamarlos a ambos
    R95p en el documento seria inexacto.
    """
    serie, fechas = serie_diaria

    diario = percentil_dias_humedos(serie, fechas, 95)
    acumulado = percentil_acumulado(serie, fechas, 95, ventana_dias=3)

    assert acumulado > diario


# --------------------------------------------------------------------------- #
# Por distrito                                                                  #
# --------------------------------------------------------------------------- #


def test_cada_distrito_tiene_su_propio_umbral():
    """
    Un distrito seco y uno lluvioso no pueden compartir umbral.

    Con umbral compartido, el seco no alcanzaria nunca el nivel alto y el
    lluvioso lo alcanzaria siempre.
    """
    fechas = _fechas(400)
    seco: list[float | None] = [2.0] * 400
    lluvioso: list[float | None] = [40.0] * 400

    umbrales = umbrales_por_distrito({"50801": (seco, fechas), "50807": (lluvioso, fechas)})

    assert umbrales["50801"]["p95_diario"] < umbrales["50807"]["p95_diario"]


def test_un_distrito_sin_datos_suficientes_queda_en_none():
    """No se rellena con el umbral de otro distrito: eso seria inventar."""
    fechas = _fechas(400)
    completo: list[float | None] = [40.0] * 400
    vacio: list[float | None] = [None] * 400

    umbrales = umbrales_por_distrito({"50801": (completo, fechas), "50808": (vacio, fechas)})

    assert umbrales["50808"]["p95_diario"] is None
    assert umbrales["50808"]["p95_acumulado"] is None
    assert umbrales["50801"]["p95_diario"] is not None


# --------------------------------------------------------------------------- #
# El calculo del percentil                                                      #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "muestra, percentil, esperado",
    [
        ([1.0, 2.0, 3.0, 4.0], 50, 2.5),
        ([1.0, 2.0, 3.0, 4.0], 0.001, 1.0),
        ([1.0, 2.0, 3.0, 4.0], 99.999, 4.0),
        ([7.0], 95, 7.0),
    ],
)
def test_percentil_interpolacion_lineal(muestra, percentil, esperado):
    """Metodo 7 de Hyndman y Fan, el mismo que numpy por defecto."""
    assert _percentil(muestra, percentil) == pytest.approx(esperado, abs=1e-3)
