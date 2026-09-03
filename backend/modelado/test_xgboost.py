"""Pruebas del XGBoost de H3.5.

Viven junto al modulo y no en `backend/tests/` porque `testpaths` apunta a
`backend/` desde el 2026-08-27 y esa es la carpeta del estimador.

Las que importan mas no comprueban que acierte, sino que **no haga trampa** y
que sea **comparable con la regresion de H3.3**:

  * `test_no_imputa_devuelve_None` es D-07, y aqui pesa mas que en H3.3 y
    H3.4: XGBoost aceptaria un NaN y aprenderia una rama para el ausente, asi
    que la fila incompleta tiene que cortarse ANTES de que la libreria la vea.
  * `test_invariante_a_escala` es la forma que toma CA-6 de H3.2 en un arbol.
  * `test_mismo_trato_de_nulos_que_los_otros_dos` es lo que hace justa la tabla
    de H3.6: sobre el mismo conjunto, los tres descartan las mismas filas.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from backend.modelado.comparar import Estimador, Observacion
from backend.modelado.random_forest import BosqueAleatorio
from backend.modelado.regresion_logistica import RegresionLogistica
from backend.modelado.xgboost_ import XGBoostEstimador
from contratos.enums import NivelRiesgo


def observaciones(valores: list[float], distrito: str = "50801") -> list[Observacion]:
    inicio = date(2020, 1, 1)
    return [
        Observacion(distrito, inicio + timedelta(days=i), {"x": v, "y": v * 2})
        for i, v in enumerate(valores)
    ]


def separables(n: int = 60) -> tuple[list[Observacion], list[NivelRiesgo]]:
    """Un problema facil: valores altos son ALTO, bajos son BAJO."""
    valores = [float(i) for i in range(n)]
    etiquetas = [NivelRiesgo.BAJO if i < n // 2 else NivelRiesgo.ALTO for i in range(n)]
    return observaciones(valores), etiquetas


# --------------------------------------------------------------------------- #
# LAS QUE IMPORTAN                                                             #
# --------------------------------------------------------------------------- #
def test_no_imputa_devuelve_None():
    """D-07: una fila sin todas sus caracteristicas no se predice, no se rellena."""
    obs, etq = separables()
    modelo = XGBoostEstimador().ajustar(obs, etq)

    incompletas = [
        Observacion("50801", date(2021, 1, 1), {"x": 5.0}),  # falta y
        Observacion("50801", date(2021, 1, 2), {"x": 5.0, "y": 10.0}),
    ]
    salida = modelo.predecir(incompletas)
    assert salida[0] is None, "imputo una caracteristica ausente en vez de no predecir"
    assert salida[1] is not None
    assert modelo.filas_sin_prediccion == 1


def test_invariante_a_escala():
    """CA-6 de H3.2 en su forma para arboles: nada se ajusta fuera del pliegue.

    Si el estimador normalizara con un estadistico global, o guardara algo entre
    llamadas, multiplicar la entrada por diez moveria alguna prediccion.
    """
    obs, etq = separables()
    a = XGBoostEstimador().ajustar(obs, etq).predecir(obs)

    por_diez = [
        Observacion(o.codigo_distrito, o.fecha, {k: v * 10 for k, v in o.caracteristicas.items()})
        for o in obs
    ]
    b = XGBoostEstimador().ajustar(por_diez, etq).predecir(por_diez)
    assert a == b, "la escala cambio las predicciones: hay un ajuste que no es por umbral"


def test_mismo_trato_de_nulos_que_los_otros_dos():
    """La tabla de H3.6 solo es justa si los tres descartan exactamente lo mismo."""
    obs, etq = separables()
    # Cada tercera fila pierde `y`.
    con_huecos = [
        Observacion(
            o.codigo_distrito,
            o.fecha,
            {"x": o.caracteristicas["x"]} if i % 3 == 0 else o.caracteristicas,
        )
        for i, o in enumerate(obs)
    ]
    xgb = XGBoostEstimador().ajustar(con_huecos, etq)
    bosque = BosqueAleatorio().ajustar(con_huecos, etq)
    regresion = RegresionLogistica().ajustar(con_huecos, etq)
    assert xgb.filas_descartadas_al_ajustar == bosque.filas_descartadas_al_ajustar == 20
    assert xgb.filas_descartadas_al_ajustar == regresion.filas_descartadas_al_ajustar

    huecos = [[p is None for p in m.predecir(con_huecos)] for m in (xgb, bosque, regresion)]
    assert huecos[0] == huecos[1] == huecos[2]
    assert (
        xgb.filas_sin_prediccion
        == bosque.filas_sin_prediccion
        == regresion.filas_sin_prediccion
        == 20
    )


# --------------------------------------------------------------------------- #
# El contrato del arnes de H3.6                                                #
# --------------------------------------------------------------------------- #
def test_cumple_el_contrato_de_estimador():
    obs, etq = separables()
    modelo = XGBoostEstimador()
    assert modelo.nombre == "xgboost"
    assert isinstance(modelo, Estimador)
    assert modelo.ajustar(obs, etq) is modelo, "ajustar tiene que devolver self"
    salida = modelo.predecir(obs)
    assert len(salida) == len(obs), "la salida mide distinto que la entrada"
    assert all(x is None or isinstance(x, NivelRiesgo) for x in salida)


def test_aprende_algo_separable():
    obs, etq = separables()
    modelo = XGBoostEstimador().ajustar(obs, etq)
    aciertos = sum(p == e for p, e in zip(modelo.predecir(obs), etq, strict=True))
    assert aciertos / len(etq) > 0.9


def test_es_reproducible():
    obs, etq = separables()
    a = XGBoostEstimador().ajustar(obs, etq).predecir(obs)
    b = XGBoostEstimador().ajustar(obs, etq).predecir(obs)
    assert a == b


def test_el_orden_de_las_caracteristicas_no_cambia_el_modelo():
    obs, etq = separables()
    al_reves = [
        Observacion(o.codigo_distrito, o.fecha, dict(reversed(list(o.caracteristicas.items()))))
        for o in obs
    ]
    a = XGBoostEstimador().ajustar(obs, etq).predecir(obs)
    b = XGBoostEstimador().ajustar(al_reves, etq).predecir(al_reves)
    assert a == b


def test_maneja_tres_clases():
    valores = [float(i) for i in range(90)]
    etq = [NivelRiesgo.BAJO] * 30 + [NivelRiesgo.MEDIO] * 30 + [NivelRiesgo.ALTO] * 30
    modelo = XGBoostEstimador().ajustar(observaciones(valores), etq)
    salida = modelo.predecir(observaciones(valores))
    assert set(salida) == {NivelRiesgo.BAJO, NivelRiesgo.MEDIO, NivelRiesgo.ALTO}
    assert set(modelo.probabilidades(observaciones(valores))[0]) == set(etq)


def test_dos_clases_como_el_incendio():
    """SC-05: incendio es binario, y las probabilidades salen rotuladas por clase."""
    obs, etq = separables()
    modelo = XGBoostEstimador().ajustar(obs, etq)
    distribuciones = modelo.probabilidades(obs)
    assert all(set(d) == {NivelRiesgo.BAJO, NivelRiesgo.ALTO} for d in distribuciones)
    # XGBoost calcula en float32: la suma cierra a 1e-6, no a 1e-9 como el bosque.
    assert all(abs(sum(d.values()) - 1.0) < 1e-6 for d in distribuciones)


def test_probabilidades_y_niveles_coinciden():
    """D-21: el nivel es el de mayor probabilidad, fila a fila, y None donde no se predice."""
    obs, etq = separables()
    modelo = XGBoostEstimador().ajustar(obs, etq)
    con_hueco = [*obs[:10], Observacion("50801", date(2021, 1, 1), {"x": 5.0})]
    niveles = modelo.predecir(con_hueco)
    distribuciones = modelo.probabilidades(con_hueco)
    assert niveles[-1] is None and distribuciones[-1] is None
    for nivel, d in zip(niveles[:-1], distribuciones[:-1], strict=True):
        assert nivel == max(d, key=d.get)


# --------------------------------------------------------------------------- #
# Falla ruidosamente cuando no puede cumplir el contrato                       #
# --------------------------------------------------------------------------- #
def test_predecir_sin_ajustar_falla():
    with pytest.raises(ValueError, match="ajustar"):
        XGBoostEstimador().predecir(observaciones([1.0]))
    with pytest.raises(ValueError, match="ajustar"):
        XGBoostEstimador().probabilidades(observaciones([1.0]))
    with pytest.raises(ValueError, match="ajustar"):
        _ = XGBoostEstimador().importancias


def test_sin_caracteristicas_falla_con_explicacion():
    obs = [Observacion("50801", date(2020, 1, i + 1), {}) for i in range(4)]
    etq = [NivelRiesgo.BAJO, NivelRiesgo.ALTO] * 2
    with pytest.raises(ValueError, match="caracteristicas"):
        XGBoostEstimador().ajustar(obs, etq)


def test_una_sola_clase_falla_en_vez_de_fingir():
    obs, _ = separables()
    with pytest.raises(ValueError, match="una sola clase"):
        XGBoostEstimador().ajustar(obs, [NivelRiesgo.BAJO] * len(obs))


def test_largos_distintos_fallan():
    obs, etq = separables()
    with pytest.raises(ValueError, match="alinear"):
        XGBoostEstimador().ajustar(obs, etq[:-1])


def test_todas_las_filas_incompletas_falla():
    obs = [Observacion("50801", date(2020, 1, i + 1), {"x": 1.0, "y": None}) for i in range(4)]
    etq = [NivelRiesgo.BAJO, NivelRiesgo.ALTO] * 2
    with pytest.raises(ValueError, match="ninguna observacion"):
        XGBoostEstimador().ajustar(obs, etq)


# --------------------------------------------------------------------------- #
# Lo que sale ademas del nivel                                                 #
# --------------------------------------------------------------------------- #
def test_balancear_cambia_el_resultado_con_clases_desbalanceadas():
    """`class_weight` es una decision, no un valor por omision: tiene que notarse.

    Se usan los mismos diez cajones repetidos de H3.4, con una minoria de ALTO
    que nunca llega a la mitad en ninguno. Sin pesos, ningun cajon predice
    ALTO; con pesos, los cajones con mas ALTO tienen que hacerlo. En XGBoost
    el peso va por fila (`sample_weight`), porque `class_weight` no existe y
    `scale_pos_weight` solo sirve para dos clases.
    """
    import random

    azar = random.Random(7)
    valores = [float(azar.randrange(10)) for _ in range(500)]
    etq = [NivelRiesgo.ALTO if azar.random() < 0.04 * v else NivelRiesgo.BAJO for v in valores]
    assert 0 < etq.count(NivelRiesgo.ALTO) < len(etq) // 3
    obs = observaciones(valores)
    cajones = observaciones([float(v) for v in range(10)])
    con = XGBoostEstimador(balancear=True).ajustar(obs, etq).predecir(cajones)
    sin = XGBoostEstimador(balancear=False).ajustar(obs, etq).predecir(cajones)
    assert NivelRiesgo.ALTO not in sin, "sin pesos, una minoria nunca gana el voto de una hoja"
    assert NivelRiesgo.ALTO in con, "con pesos, los cajones con mas ALTO tienen que predecirlo"


def test_las_clases_vuelven_como_nivel_y_no_como_entero():
    """XGBoost trabaja con 0..K-1; hacia afuera solo puede salir NivelRiesgo."""
    valores = [float(i) for i in range(90)]
    etq = [NivelRiesgo.BAJO] * 30 + [NivelRiesgo.MEDIO] * 30 + [NivelRiesgo.ALTO] * 30
    modelo = XGBoostEstimador().ajustar(observaciones(valores), etq)
    salida = modelo.predecir(observaciones(valores))
    assert all(isinstance(s, NivelRiesgo) for s in salida)
    assert salida[0] is NivelRiesgo.BAJO and salida[-1] is NivelRiesgo.ALTO
    # Y las probabilidades van rotuladas por clase, no por posicion.
    d = modelo.probabilidades(observaciones([89.0]))[0]
    assert max(d, key=d.get) is NivelRiesgo.ALTO


def test_las_importancias_se_leen_por_nombre_y_suman_uno():
    obs, etq = separables()
    modelo = XGBoostEstimador().ajustar(obs, etq)
    importancias = modelo.importancias
    assert set(importancias) == {"x", "y"}
    assert abs(sum(importancias.values()) - 1.0) < 1e-9
