"""
Pruebas de `backend/modelado/explicacion.py`. Historia H4.2.

QUE PROTEGEN, Y POR QUE NINGUNA LLAMA A SHAP
--------------------------------------------

Lo que puede salir mal en esta historia **no es el calculo de SHAP**: eso lo hace
una biblioteca probada por otros. Lo que puede salir mal es todo lo que la rodea:

  * elegir los ejemplos de una forma que dependa del orden en que llegan,
  * quedarse con los aciertos y perder los errores,
  * ordenar las contribuciones de modo que las negativas desaparezcan,
  * dar por buena una descomposicion que no cierra.

Los cuatro son defectos que producen figuras **igual de bonitas** que las
correctas, y ninguno se nota mirando el grafico. Por eso las pruebas miran la
seleccion y la aditividad, y no los numeros de SHAP.

La aditividad con SHAP de verdad la comprueba el verificador, que si lo importa.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

from backend.modelado.comparar import Observacion
from backend.modelado.explicacion import (
    Atribucion,
    Caso,
    celdas_vacias,
    elegir_casos,
    encabezado,
    pliegues_de,
)
from backend.modelado.particion import Pliegue
from contratos.enums import NivelRiesgo, TipoEvento

ALTO = NivelRiesgo.ALTO
BAJO = NivelRiesgo.BAJO
MEDIO = NivelRiesgo.MEDIO


def _p(valor: float) -> dict[NivelRiesgo, float]:
    return {ALTO: valor, BAJO: 1.0 - valor}


def _obs(dia: int, codigo: str = "50801") -> Observacion:
    return Observacion(codigo, date(2024, 1, 1) + timedelta(days=dia), {"x": float(dia)})


def _escenario():
    """Filas con las cuatro celdas pobladas y un extremo claro en cada una.

    Se escribe a mano y no se genera: una prueba de seleccion tiene que poder
    decir cual es la respuesta correcta sin recalcularla con el mismo codigo que
    esta probando.
    """
    filas = [
        # celda            dia  verdad  prediccion  P(alto)
        ("acierto_alto", 0, ALTO, ALTO, 0.70),
        ("acierto_alto", 1, ALTO, ALTO, 0.95),  # <- el elegido: mayor P
        ("falso_positivo", 2, BAJO, ALTO, 0.60),
        ("falso_positivo", 3, MEDIO, ALTO, 0.99),  # <- el elegido: mayor P
        ("falso_negativo", 4, ALTO, BAJO, 0.40),
        ("falso_negativo", 5, ALTO, BAJO, 0.02),  # <- el elegido: MENOR P
        ("acierto_bajo", 6, BAJO, BAJO, 0.05),
        ("acierto_bajo", 7, BAJO, BAJO, 0.49),  # <- el elegido: mayor P
    ]
    observaciones = [_obs(d) for _, d, _, _, _ in filas]
    verdades = [v for _, _, v, _, _ in filas]
    predicciones = [p for _, _, _, p, _ in filas]
    probabilidades = [_p(q) for _, _, _, _, q in filas]
    return observaciones, verdades, predicciones, probabilidades


# --------------------------------------------------------------------------- #
# La regla de seleccion                                                         #
# --------------------------------------------------------------------------- #


def test_elige_una_por_celda_y_las_cuatro_celdas():
    casos = elegir_casos(*_escenario())
    assert [c.celda for c in casos] == [
        "acierto_alto",
        "falso_positivo",
        "falso_negativo",
        "acierto_bajo",
    ]


def test_dentro_de_cada_celda_toma_el_extremo_declarado():
    """
    El extremo no es el mismo en las cuatro, y esa asimetria es deliberada.

    En el falso NEGATIVO se toma la probabilidad **mas baja**: es el evento que
    el modelo mas lejos estuvo de ver, y por eso el que mas informa. Tomar el de
    mayor probabilidad ahi mostraria el que casi acierta, que es el caso menos
    interesante de esa celda.
    """
    casos = {c.celda: c for c in elegir_casos(*_escenario())}

    assert casos["acierto_alto"].probabilidad_alto == 0.95
    assert casos["falso_positivo"].probabilidad_alto == 0.99
    assert casos["falso_negativo"].probabilidad_alto == 0.02
    assert casos["acierto_bajo"].probabilidad_alto == 0.49


def test_la_seleccion_no_depende_del_orden_de_entrada():
    """
    CA-1. **Es la prueba que sostiene toda la historia.**

    Si la eleccion dependiera del orden en que llegan las filas, la regla
    escrita en los criterios seria decorativa: el resultado real lo decidiria
    como quedo ordenada la consulta, que nadie declaro y nadie revisa.
    """
    esperados = [(c.celda, c.fecha) for c in elegir_casos(*_escenario())]

    obs, verdades, predicciones, probabilidades = _escenario()
    indices = list(range(len(obs)))
    generador = random.Random("orden")
    for _ in range(5):
        generador.shuffle(indices)
        revueltos = elegir_casos(
            [obs[i] for i in indices],
            [verdades[i] for i in indices],
            [predicciones[i] for i in indices],
            [probabilidades[i] for i in indices],
        )
        assert [(c.celda, c.fecha) for c in revueltos] == esperados


def test_los_empates_se_rompen_por_fecha_y_luego_por_distrito():
    """Sin desempate, dos filas con la misma probabilidad harian la eleccion
    dependiente del orden, que es justo lo que la prueba anterior prohibe."""
    obs = [
        Observacion("50802", date(2024, 5, 2), {}),
        Observacion("50801", date(2024, 5, 1), {}),  # <- misma P, fecha menor
        Observacion("50801", date(2024, 5, 2), {}),
    ]
    casos = elegir_casos(obs, [ALTO] * 3, [ALTO] * 3, [_p(0.8)] * 3)

    assert len(casos) == 1
    assert casos[0].fecha == date(2024, 5, 1)
    assert casos[0].codigo_distrito == "50801"


def test_una_fila_sin_prediccion_no_se_explica():
    """
    No hay salida que descomponer, asi que no se inventa una.

    Es la misma regla que atraviesa el proyecto desde D-07: una ausencia se
    conserva como ausencia. Meterla en una celda con probabilidad cero la haria
    competir por ser el falso negativo «mas lejano», y ganaria siempre.
    """
    obs = [_obs(0), _obs(1)]
    casos = elegir_casos(obs, [ALTO, ALTO], [None, ALTO], [None, _p(0.9)])

    assert len(casos) == 1
    assert casos[0].fecha == _obs(1).fecha


def test_medio_contra_medio_no_se_fuerza_dentro_de_ninguna_celda():
    """Las celdas se definen respecto de `alto`. Una combinacion que no cae en
    ninguna se descarta, en vez de meterla donde entre."""
    casos = elegir_casos([_obs(0)], [MEDIO], [MEDIO], [_p(0.3)])
    assert casos == []


def test_las_celdas_vacias_se_reportan_en_vez_de_rellenarse():
    """
    CA-3. Un modelo que no produjo ningun falso positivo es informacion.

    Callarlo dejaria la impresion de que se eligieron cuatro casos cuando fueron
    tres, y el lector no tendria como notarlo.
    """
    casos = elegir_casos([_obs(0)], [ALTO], [ALTO], [_p(0.9)])
    assert [c.celda for c in casos] == ["acierto_alto"]
    assert celdas_vacias(casos) == ["falso_positivo", "falso_negativo", "acierto_bajo"]


# --------------------------------------------------------------------------- #
# La aditividad y el orden de las contribuciones                                #
# --------------------------------------------------------------------------- #


def _atribucion(contribuciones: dict[str, float], base: float = 0.2, salida: float | None = None):
    caso = Caso("acierto_alto", "d", "50801", date(2024, 1, 1), ALTO, ALTO, 0.9, {})
    if salida is None:
        salida = base + sum(contribuciones.values())
    return Atribucion(caso, ALTO.value, base, salida, contribuciones)


def test_una_descomposicion_que_cierra_es_aditiva():
    a = _atribucion({"pp_7": 0.30, "tmax_3": -0.10})
    assert abs(a.residuo) < 1e-12
    assert a.aditiva


def test_una_descomposicion_que_no_cierra_se_marca():
    """
    CA-4, y es el criterio que decide si la historia mide algo.

    SHAP puede devolver numeros con la forma correcta y el contenido equivocado.
    La suma es lo unico que distingue una descomposicion de una ilustracion.
    """
    a = _atribucion({"pp_7": 0.30}, base=0.2, salida=0.9)
    assert not a.aditiva
    assert abs(a.residuo) > 0.3


def test_las_contribuciones_se_ordenan_por_magnitud_y_no_por_valor():
    """
    Una contribucion NEGATIVA grande dice tanto como una positiva grande.

    Ordenar por valor la mandaria al fondo, que es exactamente como H4.1 casi
    pierde su unico hallazgo distinguible.
    """
    a = _atribucion({"chica": 0.01, "negativa_grande": -0.80, "positiva": 0.30})
    assert [n for n, _ in a.ordenadas()] == ["negativa_grande", "positiva", "chica"]
    assert a.ordenadas(1) == [("negativa_grande", -0.80)]


# --------------------------------------------------------------------------- #
# El encabezado y los pliegues                                                  #
# --------------------------------------------------------------------------- #


def test_el_encabezado_lleva_la_advertencia_pegada():
    """
    CA-7. Una figura de SHAP circula sola: se copia a una presentacion o a un
    mensaje. Si la advertencia vive en el texto que la rodea, se pierde en el
    primer copiado.
    """
    texto = encabezado(TipoEvento.LLUVIA_INTENSA, "xgboost", "empate tecnico", "climatologica")

    assert "NO POR QUE ACIERTA" in texto
    assert "H4.1" in texto
    assert "empate tecnico" in texto
    assert "climatologica" in texto


def test_los_pliegues_separan_entrenamiento_de_prueba():
    """CA-2: lo que se explica sale del bloque de PRUEBA."""
    inicio = date(2020, 1, 1)
    filas = [
        ("50801", inicio + timedelta(days=i), {"lluvia_intensa": ALTO if i % 2 else BAJO})
        for i in range(20)
    ]
    caracteristicas = {(c, f): {"x": 1.0} for c, f, _ in filas}
    pliegue = Pliegue(
        indice=0,
        entrenamiento=(inicio, inicio + timedelta(days=9)),
        prueba=(inicio + timedelta(days=10), inicio + timedelta(days=19)),
        embargo=None,
    )

    pedazos = list(pliegues_de(TipoEvento.LLUVIA_INTENSA, filas, caracteristicas, [pliegue]))
    assert len(pedazos) == 1
    _, _, obs_pru, _ = pedazos[0]

    assert obs_pru
    assert all(pliegue.prueba[0] <= o.fecha <= pliegue.prueba[1] for o in obs_pru)
    assert not any(o.fecha <= pliegue.entrenamiento[1] for o in obs_pru)
