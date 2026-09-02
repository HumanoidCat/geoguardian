"""Pruebas de la Regresion Logistica de H3.3.

Las dos que importan mas no comprueban que acierte, sino que **no haga trampa**:

  * `test_normaliza_dentro_del_pliegue_y_no_fuera` es CA-6 de H3.2. Un
    estandarizador ajustado sobre la serie entera filtra el futuro y **mejora**
    las metricas, asi que el sintoma del defecto es un buen resultado.
  * `test_no_imputa_devuelve_None` es D-07. Imputar produce predicciones
    evaluables a partir de filas que no lo son, y mueve la tabla de H3.6 sin
    que nadie lo note.

Las demas comprueban que el estimador cumpla el contrato del arnes y que falle
ruidosamente cuando no puede cumplirlo.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from backend.modelado.comparar import Observacion
from backend.modelado.regresion_logistica import RegresionLogistica
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
# LAS DOS QUE IMPORTAN                                                         #
# --------------------------------------------------------------------------- #
def test_normaliza_dentro_del_pliegue_y_no_fuera():
    """CA-6 de H3.2: la media y la desviacion salen SOLO del entrenamiento.

    Se ajusta con un pliegue, y despues se predice sobre datos de una escala
    completamente distinta. Si el estandarizador se hubiera ajustado con todo,
    esos datos ya habrian entrado en la media y la prediccion cambiaria.

    Aca se comprueba lo estructural: **el estimador no puede ver el pliegue de
    prueba al normalizar, porque nunca lo recibe en `ajustar()`.**
    """
    obs, etq = separables()
    modelo = RegresionLogistica().ajustar(obs, etq)
    media_entrenamiento = modelo._escalador.mean_.copy()

    # Predecir sobre datos lejanisimos no puede mover la normalizacion.
    modelo.predecir(observaciones([1e6, 2e6, 3e6]))
    assert (
        modelo._escalador.mean_ == media_entrenamiento
    ).all(), "predecir cambio la normalizacion: el estandarizador esta viendo el pliegue de prueba"


def test_no_imputa_devuelve_None():
    """D-07: una fila sin todas sus caracteristicas no se predice, no se rellena."""
    obs, etq = separables()
    modelo = RegresionLogistica().ajustar(obs, etq)

    incompletas = [
        Observacion("50801", date(2021, 1, 1), {"x": 5.0}),  # falta y
        Observacion("50801", date(2021, 1, 2), {"x": 5.0, "y": 10.0}),
    ]
    salida = modelo.predecir(incompletas)
    assert salida[0] is None, "imputo una caracteristica ausente en vez de no predecir"
    assert salida[1] is not None
    assert modelo.filas_sin_prediccion == 1


# --------------------------------------------------------------------------- #
# El contrato del arnes de H3.6                                                #
# --------------------------------------------------------------------------- #
def test_cumple_el_contrato_de_estimador():
    obs, etq = separables()
    modelo = RegresionLogistica()
    assert modelo.nombre == "regresion_logistica"
    assert modelo.ajustar(obs, etq) is modelo, "ajustar tiene que devolver self"
    salida = modelo.predecir(obs)
    assert len(salida) == len(obs), "la salida mide distinto que la entrada"
    assert all(x is None or isinstance(x, NivelRiesgo) for x in salida)


def test_aprende_algo_separable():
    """Si no aprende esto, el defecto es del estimador y no de los datos."""
    obs, etq = separables()
    modelo = RegresionLogistica().ajustar(obs, etq)
    aciertos = sum(p == e for p, e in zip(modelo.predecir(obs), etq, strict=True))
    assert aciertos / len(etq) > 0.9


def test_es_reproducible():
    obs, etq = separables()
    a = RegresionLogistica().ajustar(obs, etq).predecir(obs)
    b = RegresionLogistica().ajustar(obs, etq).predecir(obs)
    assert a == b


def test_el_orden_de_las_caracteristicas_no_cambia_el_modelo():
    """Se indexa por nombre, no por posicion.

    Confiar en el orden produce un modelo que entrena sobre `acum3` creyendo que
    es `media30`: no levanta excepcion y da metricas plausibles.
    """
    obs, etq = separables()
    invertidas = [
        Observacion(o.codigo_distrito, o.fecha, dict(reversed(list(o.caracteristicas.items()))))
        for o in obs
    ]
    a = RegresionLogistica().ajustar(obs, etq).predecir(obs)
    b = RegresionLogistica().ajustar(invertidas, etq).predecir(invertidas)
    assert a == b


def test_maneja_tres_clases():
    n = 90
    obs = observaciones([float(i) for i in range(n)])
    etq = [
        NivelRiesgo.BAJO if i < 30 else NivelRiesgo.MEDIO if i < 60 else NivelRiesgo.ALTO
        for i in range(n)
    ]
    salida = RegresionLogistica().ajustar(obs, etq).predecir(obs)
    assert {x for x in salida if x} <= {NivelRiesgo.BAJO, NivelRiesgo.MEDIO, NivelRiesgo.ALTO}


def test_dos_clases_como_el_incendio():
    """SC-05 dejo el incendio binario: solo ALTO y BAJO."""
    obs, etq = separables()
    modelo = RegresionLogistica().ajustar(obs, etq)
    assert {x for x in modelo.predecir(obs) if x} <= {NivelRiesgo.BAJO, NivelRiesgo.ALTO}

    # LA CLASE POSITIVA ES `bajo`, Y NO ES UN ERROR.
    #
    # `sklearn` ordena `classes_` alfabeticamente -'alto' < 'bajo'- y con dos
    # clases devuelve la fila de `classes_[1]`. Asi que en un evento binario un
    # coeficiente positivo empuja hacia **menos** riesgo.
    #
    # Esta prueba existe para fijar eso por escrito: la primera version asumia
    # 'alto' y fallo. Quien lea el signo al reves entiende el modelo al reves, y
    # el diccionario se devuelve rotulado con el nombre real justamente para que
    # no se pueda leer sin mirar de que clase es.
    assert set(modelo.coeficientes) == {"bajo"}


# --------------------------------------------------------------------------- #
# Lo que falla ruidosamente en vez de dar un numero                            #
# --------------------------------------------------------------------------- #
def test_predecir_sin_ajustar_falla():
    with pytest.raises(ValueError, match="ajustar"):
        RegresionLogistica().predecir(observaciones([1.0]))


def test_sin_caracteristicas_falla_con_explicacion():
    """El caso real hasta H2.5: `caracteristicas` venia vacio."""
    obs = [Observacion("50801", date(2020, 1, 1) + timedelta(days=i), {}) for i in range(10)]
    etq = [NivelRiesgo.BAJO] * 5 + [NivelRiesgo.ALTO] * 5
    with pytest.raises(ValueError, match="no traen caracteristicas"):
        RegresionLogistica().ajustar(obs, etq)


def test_una_sola_clase_falla_en_vez_de_fingir():
    obs, _ = separables()
    with pytest.raises(ValueError, match="una sola clase"):
        RegresionLogistica().ajustar(obs, [NivelRiesgo.BAJO] * len(obs))


def test_largos_distintos_fallan():
    obs, etq = separables()
    with pytest.raises(ValueError, match="no se pueden alinear"):
        RegresionLogistica().ajustar(obs, etq[:-1])


def test_todas_las_filas_incompletas_falla():
    obs = [
        Observacion("50801", date(2020, 1, 1) + timedelta(days=i), {"x": 1.0, "y": None})
        for i in range(10)
    ]
    etq = [NivelRiesgo.BAJO] * 5 + [NivelRiesgo.ALTO] * 5
    with pytest.raises(ValueError, match="No se imputa"):
        RegresionLogistica().ajustar(obs, etq)


# --------------------------------------------------------------------------- #
# El desbalance, declarado                                                     #
# --------------------------------------------------------------------------- #
def test_balancear_cambia_el_resultado_con_clases_desbalanceadas():
    """Con 5 % de positivos, balancear sube la exhaustividad de la minoritaria.

    La prueba no afirma que balancear sea mejor: afirma que **cambia el
    resultado**, que es lo que obliga a declararlo en vez de dejarlo por omision.
    """
    n = 200
    obs = observaciones([float(i) for i in range(n)])
    etq = [NivelRiesgo.BAJO] * 190 + [NivelRiesgo.ALTO] * 10

    con = RegresionLogistica(balancear=True).ajustar(obs, etq).predecir(obs)
    sin = RegresionLogistica(balancear=False).ajustar(obs, etq).predecir(obs)
    assert con != sin, "class_weight no tuvo efecto: revisar que se este pasando"
    assert sum(x == NivelRiesgo.ALTO for x in con) >= sum(x == NivelRiesgo.ALTO for x in sin)


def test_los_coeficientes_se_pueden_leer_por_nombre():
    obs, etq = separables()
    coef = RegresionLogistica().ajustar(obs, etq).coeficientes
    assert set(next(iter(coef.values()))) == {"x", "y"}
