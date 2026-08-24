"""
Pruebas del reporte de calidad de datos. Historia H1.5, rubrica OE1.

Implementa los cuatro casos que `docs/investigacion/plan-pruebas.md` planifico
para `backend/calidad` en su seccion 3.6, mas los del cruce con el catalogo.

No hay implementacion simulada contra la que contrastar: este modulo no
implementa ningun metodo de contrato, produce `ReporteCalidad`.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from backend.calidad.reporte_calidad import (
    NO_REPORTAN_AUSENCIA,
    Serie,
    _percentil,
    completitud,
    cruzar_con_catalogo,
    extremos_estadisticos,
    fuera_de_rango_fisico,
    variacion_espacial,
)
from contratos.enums import MetodoImputacion

INICIO = date(2020, 1, 1)


def _fechas(n: int, desde: date = INICIO) -> list[date]:
    return [desde + timedelta(days=i) for i in range(n)]


def _serie(distrito: str, variable: str, valores: list[float | None]) -> Serie:
    return Serie(distrito, variable, _fechas(len(valores)), valores)


# --------------------------------------------------------------------------- #
# Completitud                                                                   #
# --------------------------------------------------------------------------- #


def test_pct_faltantes_se_calcula_no_se_declara():
    """
    Caso planificado en el plan de pruebas, prioridad 1.

    El porcentaje sale de contar sobre una serie conocida, no de lo que diga la
    fuente sobre si misma. Cuatro de veinte valores ausentes son 20 %.
    """
    valores: list[float | None] = [10.0] * 20
    for i in (3, 7, 11, 15):
        valores[i] = None

    reportes = completitud([_serie("50801", "precipitacion_mm", valores)])

    assert len(reportes) == 1
    assert reportes[0].pct_faltantes == pytest.approx(20.0)
    assert reportes[0].total_esperado == 20
    assert reportes[0].total_presente == 16


def test_un_reporte_por_variable_y_su_fuente():
    """
    La completitud es por fuente, no del proyecto.

    CHIRPS aporta precipitacion y POWER el resto: son productos distintos y no
    se pueden resumir en un solo numero.
    """
    series = [
        _serie("50801", "precipitacion_mm", [1.0] * 10),
        _serie("50801", "temp_max_c", [25.0] * 10),
    ]

    reportes = {r.variable: r.fuente for r in completitud(series)}

    assert reportes["precipitacion_mm"] == "chirps"
    assert reportes["temp_max_c"] == "power"


def test_el_total_esperado_son_dias_de_calendario_no_filas():
    """
    Si la carga omitio dias enteros, contar filas daria 100 % de completitud
    sobre una serie con huecos: el hueco estaria en las filas que no existen.
    """
    fechas = [INICIO, INICIO + timedelta(days=1), INICIO + timedelta(days=9)]
    serie = Serie("50801", "precipitacion_mm", fechas, [1.0, 2.0, 3.0])

    reporte = completitud([serie])[0]

    assert reporte.total_esperado == 10  # del 1 al 10 de enero
    assert reporte.total_presente == 3
    assert reporte.pct_faltantes == pytest.approx(70.0)


def test_una_fila_duplicada_no_esconde_un_dia_faltante():
    """
    El defecto que encontro Alejandro revisando el PR #144.

    La carga metio el 3 de enero dos veces y por eso nunca cargo el 9: diez
    filas para nueve dias distintos. Contando filas, `presente` daba 10 sobre
    9 esperados, el porcentaje salia negativo, y `max(pct, 0.0)` lo recortaba a
    cero. El reporte decia **0 % de faltantes con un dia realmente ausente**,
    que es exactamente la frase enganosa que este modulo existe para no
    producir.

    Ahora `total_presente` cuenta dias distintos, y el duplicado se reporta en
    lugar de recortarse.
    """
    fechas = [
        date(2020, 1, 1),
        date(2020, 1, 2),
        date(2020, 1, 3),
        date(2020, 1, 3),  # repetido
        date(2020, 1, 4),
        date(2020, 1, 5),
        date(2020, 1, 6),
        date(2020, 1, 7),
        date(2020, 1, 8),
        date(2020, 1, 10),  # el 9 nunca se cargo
    ]
    serie = Serie("50801", "precipitacion_mm", fechas, [5.0] * 10)

    reporte = completitud([serie])[0]

    assert reporte.total_esperado == 10  # del 1 al 10 de enero
    assert reporte.total_presente == 9  # dias distintos, no filas
    assert reporte.pct_faltantes == pytest.approx(10.0)
    assert "duplicadas" in reporte.observaciones


def test_sin_duplicados_no_se_menciona_el_aviso():
    """El aviso aparece solo cuando corresponde, para que signifique algo."""
    reporte = completitud([_serie("50801", "precipitacion_mm", [5.0] * 30)])[0]

    assert "duplicadas" not in reporte.observaciones


def test_cero_faltantes_se_reporta_con_su_interpretacion():
    """
    El hallazgo central de la historia.

    Un 0 % en un producto de malla no significa 100 % observado: significa que
    el producto no puede reportar ausencia. La observacion tiene que decirlo,
    porque el numero solo se lee como calidad excelente.
    """
    reporte = completitud([_serie("50801", "precipitacion_mm", [5.0] * 30)])[0]

    assert reporte.pct_faltantes == 0.0
    assert "NO significa 100 % observado" in reporte.observaciones


def test_faltantes_en_una_fuente_de_malla_se_marca_como_sospechoso():
    """
    Al reves: si una fuente que no puede reportar ausencia trae huecos, es mas
    probable un fallo de descarga que un hueco real.
    """
    valores: list[float | None] = [5.0] * 30
    valores[10] = None

    reporte = completitud([_serie("50801", "precipitacion_mm", valores)])[0]

    assert "Revisar la carga" in reporte.observaciones


def test_el_metodo_de_imputacion_queda_registrado():
    """
    Caso planificado en el plan de pruebas.

    H1.5 no imputa nada: reporta. Que el campo diga SIN_IMPUTAR es la
    afirmacion de que estos numeros salen del dato y no de un relleno.
    """
    reporte = completitud([_serie("50801", "precipitacion_mm", [1.0] * 10)])[0]

    assert reporte.metodo_imputacion == MetodoImputacion.SIN_IMPUTAR


def test_series_de_largo_distinto_es_error():
    with pytest.raises(ValueError, match="que dia falta"):
        Serie("50801", "precipitacion_mm", _fechas(5), [1.0, 2.0])


# --------------------------------------------------------------------------- #
# Atipicos: las dos categorias no se mezclan                                    #
# --------------------------------------------------------------------------- #


def test_detecta_valores_fuera_de_rango_fisico():
    """
    Caso planificado en el plan de pruebas.

    Una humedad de 120 % no es un evento extremo: es un defecto del dato.
    """
    valores: list[float | None] = [80.0] * 20
    valores[5] = 120.0

    fuera = fuera_de_rango_fisico([_serie("50801", "humedad_relativa_pct", valores)])

    assert len(fuera) == 1
    assert fuera[0][3] == 120.0


def test_la_precipitacion_negativa_es_error_de_dato():
    """Es lo que produce filtrar_ruido sobre lluvia. Ver D-17."""
    valores: list[float | None] = [5.0] * 20
    valores[3] = -2.0

    assert len(fuera_de_rango_fisico([_serie("50801", "precipitacion_mm", valores)])) == 1


def test_un_dia_de_lluvia_extrema_no_es_un_valor_imposible():
    """
    **La distincion que sostiene toda esta seccion.**

    Un dia de 300 mm en Tilaran es el temporal del 5 de octubre de 2017, que
    esta en el catalogo de H4.3. Si el reporte lo marcara como defecto,
    invitaria a limpiarlo, y limpiarlo borraria justamente los dias que el
    modelo tiene que aprender a predecir.
    """
    valores: list[float | None] = [5.0] * 200
    valores[100] = 300.0
    serie = _serie("50801", "precipitacion_mm", valores)

    assert fuera_de_rango_fisico([serie]) == []

    extremos = extremos_estadisticos([serie])
    assert any(v == 300.0 for *_, v in extremos)


def test_los_extremos_se_calculan_contra_la_distribucion_del_propio_distrito():
    """
    Un acumulado normal en Arenal puede ser extremo en Libano.

    Con umbral compartido, el distrito lluvioso aportaria todos los extremos y
    el seco ninguno, que es un artefacto del metodo y no del clima.
    """
    lluvioso = _serie("50807", "precipitacion_mm", [40.0] * 99 + [200.0])
    seco = _serie("50805", "precipitacion_mm", [2.0] * 99 + [20.0])

    extremos = extremos_estadisticos([lluvioso, seco])
    distritos = {d for d, *_ in extremos}

    assert distritos == {"50807", "50805"}


def test_una_serie_corta_no_produce_extremos():
    """Con menos de 20 valores, un percentil de cola no significa nada."""
    assert extremos_estadisticos([_serie("50801", "precipitacion_mm", [1.0] * 10)]) == []


# --------------------------------------------------------------------------- #
# Cruce con el catalogo de H4.3                                                 #
# --------------------------------------------------------------------------- #


def test_un_extremo_que_coincide_con_un_evento_catalogado_se_reconoce():
    """
    Usar el catalogo de H4.3 como validacion cruzada.

    Un extremo que cae en la fecha de un evento documentado no es un dato
    sospechoso: es la confirmacion de que la serie capta lo que ocurrio.
    """
    extremos = [("50803", "precipitacion_mm", date(2017, 10, 5), 250.0)]
    eventos = [("50803", date(2017, 10, 5), None)]

    coincidentes, total = cruzar_con_catalogo(extremos, eventos)

    assert (coincidentes, total) == (1, 1)


def test_la_holgura_admite_el_desfase_entre_lluvia_y_dano():
    """
    El evento se reporta cuando se registra el dano, que puede ser uno o dos
    dias despues de la lluvia que lo causo.
    """
    extremos = [("50803", "precipitacion_mm", date(2017, 10, 3), 250.0)]
    eventos = [("50803", date(2017, 10, 5), None)]

    assert cruzar_con_catalogo(extremos, eventos, holgura_dias=3)[0] == 1
    assert cruzar_con_catalogo(extremos, eventos, holgura_dias=0)[0] == 0


def test_el_cruce_respeta_el_distrito():
    """Un evento en Tronadora no explica un extremo en Libano."""
    extremos = [("50805", "precipitacion_mm", date(2017, 10, 5), 250.0)]
    eventos = [("50803", date(2017, 10, 5), None)]

    assert cruzar_con_catalogo(extremos, eventos)[0] == 0


def test_holgura_negativa_es_error():
    with pytest.raises(ValueError, match="holgura"):
        cruzar_con_catalogo([], [], holgura_dias=-1)


# --------------------------------------------------------------------------- #
# Sesgo espacial: la incidencia I-05                                            #
# --------------------------------------------------------------------------- #


def test_variables_no_son_identicas_entre_distritos():
    """
    Caso planificado en el plan de pruebas tras la medicion de H1.1.

    Una variable que da el mismo valor en los ocho distritos no aporta ninguna
    capacidad de distinguirlos, por mas filas que tenga. Un 0 % aqui es el
    sintoma de I-05.
    """
    identica = [
        _serie("50801", "temp_max_c", [25.0] * 50),
        _serie("50802", "temp_max_c", [25.0] * 50),
    ]
    distinta = [
        _serie("50801", "precipitacion_mm", [1.0] * 50),
        _serie("50802", "precipitacion_mm", [9.0] * 50),
    ]

    variacion = variacion_espacial(identica + distinta)

    assert variacion["temp_max_c"] == 0.0
    assert variacion["precipitacion_mm"] == 100.0


def test_la_variacion_espacial_necesita_al_menos_dos_distritos():
    """Con un solo distrito la pregunta no tiene sentido."""
    assert variacion_espacial([_serie("50801", "temp_max_c", [25.0] * 10)]) == {}


def test_el_percentil_rechaza_la_muestra_vacia():
    """
    La proteccion vive en la funcion, no solo en el llamador.

    Hoy `extremos_estadisticos` filtra las series cortas, asi que el caso no se
    da. Desde otro punto de llamada esto reventaba con un IndexError que no
    explicaba nada.
    """
    with pytest.raises(ValueError, match="vacia"):
        _percentil([], 95)


def test_las_fuentes_de_malla_estan_declaradas():
    """
    El motivo por el que no pueden reportar ausencia queda escrito en el codigo,
    no solo en la evidencia.
    """
    assert "chirps" in NO_REPORTAN_AUSENCIA
    assert "power" in NO_REPORTAN_AUSENCIA
    assert "I-05" in NO_REPORTAN_AUSENCIA["power"]
