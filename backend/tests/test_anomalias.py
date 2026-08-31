"""
Pruebas de las anomalias climaticas. Historia H2.4.

Las pruebas de forma corren contra las dos implementaciones, la real y el
simulado, porque las dos deben cumplir el mismo contrato. `normales_por_mes` y
`anomalia_con_fechas` no son del contrato y se prueban solo contra la real.

Cubre el caso `test_anomalia_mes_faltante_en_normal_devuelve_none` planificado
en `docs/investigacion/plan-pruebas.md`, seccion 3.3.
"""

from __future__ import annotations

from datetime import date

import pytest

from backend.senales.anomalias import (
    MINIMO_ANIOS_NORMAL,
    CalculadorAnomalias,
    anomalia_con_fechas,
    normales_por_mes,
)
from contratos.simulados.senales import ProcesadorSenalesSimulado

# Normal por mes de juguete: doce valores distintos y faciles de seguir.
NORMAL = {m: float(m * 10) for m in range(1, 13)}


@pytest.fixture(
    params=[CalculadorAnomalias(), ProcesadorSenalesSimulado()],
    ids=["real", "simulado"],
)
def procesador(request):
    return request.param


def _meses(n: int, desde: date = date(1991, 1, 1)) -> list[date]:
    """n fechas mensuales consecutivas a partir de `desde`."""
    fechas = []
    anio, mes = desde.year, desde.month
    for _ in range(n):
        fechas.append(date(anio, mes, 1))
        mes += 1
        if mes > 12:
            mes = 1
            anio += 1
    return fechas


# --------------------------------------------------------------------------- #
# El contrato                                                                   #
# --------------------------------------------------------------------------- #


def test_la_anomalia_es_el_valor_menos_la_normal_de_su_mes(procesador):
    """Enero contra 10, febrero contra 20, marzo contra 30."""
    serie: list[float | None] = [15.0, 25.0, 35.0]

    assert procesador.anomalia(serie, NORMAL) == [5.0, 5.0, 5.0]


def test_anomalia_mes_faltante_en_normal_devuelve_none(procesador):
    """
    Caso planificado en el plan de pruebas.

    Si falta el mes, esa posicion sale None. **No se sustituye por el promedio
    de los meses que si estan**: eso mezclaria la normal de un mes con la de
    otro, que es el error que este indice existe para no cometer.
    """
    normal_incompleta = {1: 10.0, 3: 30.0}
    serie: list[float | None] = [15.0, 25.0, 35.0]

    salida = procesador.anomalia(serie, normal_incompleta)

    assert salida[0] == 5.0
    assert salida[1] is None  # febrero no esta en la normal
    assert salida[2] == 5.0


def test_un_hueco_de_la_serie_sale_hueco(procesador):
    serie: list[float | None] = [15.0, None, 35.0]

    assert procesador.anomalia(serie, NORMAL)[1] is None


def test_la_anomalia_no_cambia_el_largo(procesador):
    serie: list[float | None] = [10.0] * 25

    assert len(procesador.anomalia(serie, NORMAL)) == 25


def test_la_serie_da_la_vuelta_al_anio(procesador):
    """La posicion 12 vuelve a enero: es el mes 13 del calendario."""
    serie: list[float | None] = [0.0] * 13

    salida = procesador.anomalia(serie, NORMAL)

    assert salida[0] == salida[12]  # los dos contra la normal de enero
    assert salida[0] == -10.0


def test_una_anomalia_negativa_es_un_resultado(procesador):
    """Llover menos de lo normal no es un error ni un faltante."""
    serie: list[float | None] = [2.0]

    assert procesador.anomalia(serie, NORMAL) == [-8.0]


# --------------------------------------------------------------------------- #
# Validaciones propias de la implementacion real                                #
# --------------------------------------------------------------------------- #


def test_rechaza_claves_que_no_son_meses():
    with pytest.raises(ValueError, match="1 a 12"):
        CalculadorAnomalias().anomalia([1.0], {0: 5.0, 13: 5.0})


def test_avisa_por_registro_de_la_suposicion_de_enero(caplog):
    """
    El contrato no recibe fechas y la suposicion no se puede verificar desde
    dentro de la funcion. El aviso va por registro y no solo en el docstring,
    para que lo vea quien lo ejecuta.
    """
    with caplog.at_level("WARNING"):
        CalculadorAnomalias().anomalia([1.0], NORMAL)

    assert "arranca en enero" in caplog.text
    assert "SC-06" in caplog.text


# --------------------------------------------------------------------------- #
# El calculo de la normal, que si recibe fechas                                 #
# --------------------------------------------------------------------------- #


def test_la_normal_promedia_cada_mes_por_separado():
    """Dos eneros de 10 y 20 dan una normal de 15 para enero."""
    fechas = [date(1991, 1, 1), date(1992, 1, 1), date(1991, 7, 1)]
    serie: list[float | None] = [10.0, 20.0, 100.0]

    normales = normales_por_mes(serie, fechas)

    assert normales[1] == pytest.approx(15.0)
    assert normales[7] == pytest.approx(100.0)


def test_la_normal_solo_usa_el_periodo_pedido():
    """Un valor de 1990 no entra en la normal 1991-2020."""
    fechas = [date(1990, 1, 1), date(1991, 1, 1)]
    serie: list[float | None] = [1000.0, 10.0]

    assert normales_por_mes(serie, fechas)[1] == pytest.approx(10.0)


def test_un_mes_sin_datos_no_aparece_en_la_normal():
    """
    No se rellena con el promedio anual ni con el de los meses vecinos: la
    normal de un mes es la de ese mes, y una inventada produciria anomalias que
    parecen validas.
    """
    fechas = [date(1991, 1, 1)]
    serie: list[float | None] = [10.0]

    normales = normales_por_mes(serie, fechas)

    assert set(normales) == {1}


def test_la_normal_ignora_los_huecos():
    fechas = [date(1991, 1, 1), date(1992, 1, 1)]
    serie: list[float | None] = [10.0, None]

    assert normales_por_mes(serie, fechas)[1] == pytest.approx(10.0)


def test_la_normal_rechaza_largos_distintos():
    with pytest.raises(ValueError, match="SC-06"):
        normales_por_mes([1.0, 2.0], _meses(3))


def test_la_normal_rechaza_un_periodo_invertido():
    with pytest.raises(ValueError, match="invertido"):
        normales_por_mes([1.0], _meses(1), desde=date(2020, 1, 1), hasta=date(1991, 1, 1))


def test_avisa_si_la_normal_tiene_menos_de_treinta_anios(caplog):
    """La OMM recomienda al menos 30 anios. WMO-No. 1203, referencia [6]."""
    with caplog.at_level("WARNING"):
        normales_por_mes(
            [10.0], [date(1991, 1, 1)], desde=date(1991, 1, 1), hasta=date(2000, 12, 31)
        )

    assert "30" in caplog.text


def _eneros(cuantos: int, desde_anio: int = 1991) -> tuple[list[float | None], list[date]]:
    """`cuantos` eneros consecutivos con dato, uno por anio."""
    fechas = [date(desde_anio + i, 1, 1) for i in range(cuantos)]
    return [10.0] * cuantos, fechas


def test_avisa_aunque_la_ventana_pedida_sea_larga(caplog):
    """
    **El defecto que encontro Alejandro, congelado como prueba.**

    Tres anios de dato pidiendo la ventana 1991-2020 por defecto. La version
    anterior contaba `(hasta.year - desde.year) + 1`, que da 30, y no avisaba
    nunca: una "normal climatologica" de tres anios pasaba en silencio.

    Si esta prueba empieza a fallar, alguien volvio a contar la ventana en vez
    de los anios que hay.
    """
    serie, fechas = _eneros(3)

    with caplog.at_level("WARNING"):
        normales_por_mes(serie, fechas)

    assert "enero" in caplog.text
    assert "(3)" in caplog.text


def test_el_aviso_nombra_solo_los_meses_cortos(caplog):
    """
    Un mes al que le faltan anios no puede esconderse detras de los completos.

    Enero con 30 anios y julio con 5. El promedio global daria 17,5 y no diria
    cual de los dos es el debil; el aviso tiene que nombrar a julio y callar
    sobre enero.
    """
    serie: list[float | None] = []
    fechas: list[date] = []

    for i in range(MINIMO_ANIOS_NORMAL):
        serie.append(10.0)
        fechas.append(date(1991 + i, 1, 1))
    for i in range(5):
        serie.append(20.0)
        fechas.append(date(1991 + i, 7, 1))

    with caplog.at_level("WARNING"):
        normales = normales_por_mes(serie, fechas)

    assert "julio" in caplog.text
    assert "(5)" in caplog.text
    assert "enero" not in caplog.text

    # El aviso no cambia el resultado: los dos meses siguen saliendo.
    assert normales[1] == pytest.approx(10.0)
    assert normales[7] == pytest.approx(20.0)


def test_no_avisa_con_treinta_anios_completos(caplog):
    serie, fechas = _eneros(MINIMO_ANIOS_NORMAL)

    with caplog.at_level("WARNING"):
        normales_por_mes(serie, fechas)

    assert "WMO-No. 1203" not in caplog.text


def test_los_anios_repetidos_no_inflan_la_cuenta(caplog):
    """
    Doce meses de un mismo anio no son doce anios de ese mes.

    Se cuentan anios distintos, no filas. Contar filas daria 12 para enero con
    un solo enero por anio repetido y volveria a esconder el problema.
    """
    serie: list[float | None] = [10.0] * 12
    fechas = [date(1991, 1, 1)] * 12

    with caplog.at_level("WARNING"):
        normales_por_mes(serie, fechas)

    assert "enero (1)" in caplog.text


# --------------------------------------------------------------------------- #
# El costo de la suposicion, congelado                                          #
# --------------------------------------------------------------------------- #


def test_sin_desfase_las_dos_versiones_coinciden():
    """Cuando la serie si arranca en enero, la suposicion es correcta."""
    fechas = _meses(24, date(1991, 1, 1))
    serie: list[float | None] = [float(i) for i in range(24)]

    del_contrato = CalculadorAnomalias().anomalia(serie, NORMAL)
    correcta = anomalia_con_fechas(serie, fechas, NORMAL)

    assert del_contrato == correcta


def test_con_desfase_la_version_del_contrato_se_equivoca_de_mes():
    """
    **El defecto que sostiene SC-06, congelado como prueba.**

    Una serie que arranca en julio se compara, posicion por posicion, contra
    las normales de enero, febrero, marzo... El error no es un sesgo pequeno:
    es la diferencia entre dos meses del calendario.

    Si algun dia esta prueba empieza a fallar porque las dos coinciden,
    significa que `anomalia` dejo de suponer enero y hay que revisar por que.
    """
    fechas = _meses(12, date(1991, 7, 1))  # arranca en julio
    serie: list[float | None] = [100.0] * 12

    del_contrato = CalculadorAnomalias().anomalia(serie, NORMAL)
    correcta = anomalia_con_fechas(serie, fechas, NORMAL)

    assert del_contrato != correcta

    # La primera posicion es julio, normal 70. El contrato usa la de enero, 10.
    assert correcta[0] == pytest.approx(30.0)
    assert del_contrato[0] == pytest.approx(90.0)


def test_anomalia_con_fechas_rechaza_largos_distintos():
    with pytest.raises(ValueError):
        anomalia_con_fechas([1.0, 2.0], _meses(3), NORMAL)
