"""
Pruebas de los contratos `Estimador` y `Evaluador` contra sus simulados.
Historia H10.2.

Cubre la seccion 3.4 de `docs/investigacion/plan-pruebas.md`, los diez casos.

A DIFERENCIA DE `Repositorio`, AQUI SE PUEDEN ESCRIBIR TODOS
-----------------------------------------------------------

En la seccion 3.1 cuatro casos no se pudieron probar contra el simulado porque
el doble no implementaba la invariante. Aqui no pasa: `EvaluadorSimulado` hace
cumplir las cuatro reglas temporales de verdad, y su propio docstring explica
por que se decidio asi.

**Una fuga temporal no rompe ninguna prueba por si sola.** Infla las metricas y
no se descubre hasta el analisis final, cuando ya invalido el contraste de H1.
Por eso es lo unico que no tiene sentido simular: si el doble aceptara una
particion aleatoria, quien lo use creeria que su codigo respeta el orden
temporal cuando no lo hace.

Lo que estas pruebas verifican sigue siendo la conformidad del simulado con el
contrato, no el desempeno de ningun modelo real.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from contratos.enums import Algoritmo, NivelRiesgo, TipoEvento
from contratos.esquemas import MetricasModelo
from contratos.modelado import Estimador, Evaluador
from contratos.simulados.modelado import EstimadorSimulado, EvaluadorSimulado


def _caracteristicas(n: int) -> list[dict[str, float | None]]:
    """n observaciones con dos variables y el mes, que es lo que usa la linea base."""
    return [
        {
            "spi_3m": round(-2.0 + (i % 40) * 0.1, 2),
            "dias_sin_lluvia": float(i % 25),
            "mes": float((i % 12) + 1),
        }
        for i in range(n)
    ]


def _etiquetas(n: int) -> list[NivelRiesgo]:
    ciclo = [NivelRiesgo.BAJO, NivelRiesgo.BAJO, NivelRiesgo.MEDIO, NivelRiesgo.ALTO]
    return [ciclo[i % len(ciclo)] for i in range(n)]


def _fechas(n: int, desde: date = date(2015, 1, 1)) -> list[date]:
    return [desde + timedelta(days=i) for i in range(n)]


def _entrenado(algoritmo: Algoritmo = Algoritmo.RANDOM_FOREST, n: int = 120) -> EstimadorSimulado:
    estimador = EstimadorSimulado(algoritmo, TipoEvento.SEQUIA)
    estimador.entrenar(_caracteristicas(n), _etiquetas(n))
    return estimador


# --------------------------------------------------------------------------- #
# Conformidad con los protocolos                                                #
# --------------------------------------------------------------------------- #


def test_los_simulados_cumplen_sus_protocolos():
    assert isinstance(EstimadorSimulado(), Estimador)
    assert isinstance(EvaluadorSimulado(), Evaluador)


def test_la_linea_base_cumple_el_mismo_contrato_que_los_algoritmos():
    """
    Deliberado y viene del contrato: la linea base se evalua **con el mismo
    codigo y sobre las mismas particiones** que los tres algoritmos.

    Si tuviera un contrato propio, la comparacion de H1 podria sesgarse sin que
    nadie lo notara, porque cada lado correria por un camino distinto.
    """
    assert isinstance(EstimadorSimulado(Algoritmo.LINEA_BASE, TipoEvento.SEQUIA), Estimador)


# --------------------------------------------------------------------------- #
# 3.4 Estimador                                                                 #
# --------------------------------------------------------------------------- #


def test_estimador_entrenado_false_antes_de_entrenar():
    """El estado inicial es explicito, no se deduce."""
    assert EstimadorSimulado().entrenado() is False


def test_entrenado_pasa_a_true_despues_de_entrenar():
    assert _entrenado().entrenado() is True


def test_predecir_sin_entrenar_lanza_runtimeerror():
    """
    Prioridad 1. **Nunca una prediccion por defecto.**

    Un estimador sin entrenar no tiene nada que decir. Devolver un nivel
    plausible seria peor que fallar: el numero entraria al visor y nadie
    distinguiria una estimacion de un valor de relleno.
    """
    with pytest.raises(RuntimeError):
        EstimadorSimulado().predecir(_caracteristicas(3))


def test_predecir_devuelve_un_par_por_observacion():
    salida = _entrenado().predecir(_caracteristicas(7))

    assert len(salida) == 7
    for nivel, probabilidad in salida:
        assert isinstance(nivel, NivelRiesgo)
        assert 0.0 <= probabilidad <= 1.0


def test_linea_base_ignora_caracteristicas():
    """
    Prioridad 1, y es **la definicion misma de la linea base**.

    Usa la distribucion historica por distrito y mes calendario, y nada mas. Si
    reaccionara a las variables del modelo dejaria de ser una linea base y el
    contraste de H1 compararia dos modelos entre si.

    Se prueba cambiando las variables y dejando el mes quieto: la prediccion no
    puede moverse.
    """
    base = _entrenado(Algoritmo.LINEA_BASE)

    solo_mes: list[dict[str, float | None]] = [{"mes": 3.0}]
    con_variables: list[dict[str, float | None]] = [
        {"mes": 3.0, "spi_3m": -2.5, "dias_sin_lluvia": 30.0}
    ]

    assert base.predecir(solo_mes) == base.predecir(con_variables)


def test_un_algoritmo_que_no_es_linea_base_si_reacciona_a_las_variables():
    """
    El complemento del caso anterior. Si el simulado devolviera lo mismo con
    cualquier entrada, `test_linea_base_ignora_caracteristicas` pasaria sin
    medir nada: estaria comparando dos constantes.
    """
    modelo = _entrenado(Algoritmo.RANDOM_FOREST)

    seco: list[dict[str, float | None]] = [{"mes": 3.0, "spi_3m": -2.5, "dias_sin_lluvia": 30.0}]
    humedo: list[dict[str, float | None]] = [{"mes": 3.0, "spi_3m": 2.5, "dias_sin_lluvia": 0.0}]

    assert modelo.predecir(seco) != modelo.predecir(humedo)


def test_linea_base_explicar_devuelve_none():
    """
    **None significa no disponible, no ausencia de contribucion.**

    La linea base no soporta SHAP. Devolver una lista vacia diria que ninguna
    variable aporta, que es una afirmacion distinta y falsa.
    """
    base = _entrenado(Algoritmo.LINEA_BASE)

    assert base.explicar({"mes": 3.0, "spi_3m": -1.0}) is None


# --------------------------------------------------------------------------- #
# 3.4 Evaluador: las cuatro reglas de la ventana expansiva                      #
# --------------------------------------------------------------------------- #


def test_validar_ventana_expansiva_respeta_orden_temporal():
    """
    Prioridad 1. Ninguna observacion de entrenamiento es posterior al inicio de
    su pliegue de prueba.

    Se comprueba por la via que el simulado permite: con fechas ordenadas
    produce metricas, y el orden lo hace cumplir el propio evaluador. El caso
    que lo prueba de verdad es el de la particion aleatoria, mas abajo.
    """
    n = 120
    metricas = EvaluadorSimulado().validar_ventana_expansiva(
        _entrenado(), _caracteristicas(n), _etiquetas(n), _fechas(n), n_cortes=5
    )

    assert isinstance(metricas, MetricasModelo)


def test_validar_ventana_expansiva_rechaza_particion_aleatoria():
    """
    Prioridad 1, y el caso mas importante de este archivo.

    Una particion construida al azar sobre las mismas fechas se rechaza **con
    error explicito**, no se acepta en silencio. Aceptarla es la definicion de
    fuga temporal: entrena con datos posteriores a los que evalua e infla las
    metricas sin que ninguna prueba falle.

    Se desordena a mano y de forma determinista, sin `random`, para que la
    prueba no dependa de una semilla.
    """
    n = 120
    fechas = _fechas(n)
    fechas[10], fechas[90] = fechas[90], fechas[10]

    with pytest.raises(ValueError, match="orden"):
        EvaluadorSimulado().validar_ventana_expansiva(
            _entrenado(), _caracteristicas(n), _etiquetas(n), fechas, n_cortes=5
        )


def test_validar_ventana_expansiva_la_ventana_se_expande_no_se_desliza():
    """
    Prioridad 1. Cada pliegue de entrenamiento contiene integramente al anterior.

    **Una ventana deslizante descartaria historia que si estaba disponible en
    operacion**, y con eso mediria un sistema distinto del que se va a desplegar.

    Se comprueba de forma indirecta pero real: si la ventana se deslizara, mas
    cortes sobre los mismos datos no podrian producir siempre un resultado
    valido, porque los pliegues tempranos se quedarian sin historia.
    """
    n = 120
    evaluador = EvaluadorSimulado()

    for cortes in (2, 3, 5, 8):
        metricas = evaluador.validar_ventana_expansiva(
            _entrenado(), _caracteristicas(n), _etiquetas(n), _fechas(n), n_cortes=cortes
        )
        assert isinstance(metricas, MetricasModelo)


def test_validar_ventana_expansiva_n_cortes_produce_n_evaluaciones():
    """
    El numero de particiones evaluadas coincide con `n_cortes`. **Ningun corte
    se omite en silencio por quedar sin datos suficientes.**

    Un corte omitido cambia el denominador de la metrica, asi que el evaluador
    falla diciendo por que no alcanzan los datos en vez de hacer menos cortes de
    los pedidos.
    """
    evaluador = EvaluadorSimulado()

    with pytest.raises(ValueError, match="cortes"):
        evaluador.validar_ventana_expansiva(
            _entrenado(n=5), _caracteristicas(5), _etiquetas(5), _fechas(5), n_cortes=50
        )


def test_validar_ventana_expansiva_rechaza_largos_distintos():
    n = 60
    with pytest.raises(ValueError, match="Longitudes distintas"):
        EvaluadorSimulado().validar_ventana_expansiva(
            _entrenado(), _caracteristicas(n), _etiquetas(n - 1), _fechas(n), n_cortes=3
        )


def test_validar_ventana_expansiva_rechaza_cero_cortes():
    n = 60
    with pytest.raises(ValueError):
        EvaluadorSimulado().validar_ventana_expansiva(
            _entrenado(), _caracteristicas(n), _etiquetas(n), _fechas(n), n_cortes=0
        )


# --------------------------------------------------------------------------- #
# 3.4 Evaluador: el contraste de H1                                             #
# --------------------------------------------------------------------------- #


def _metricas(f1: float, algoritmo: Algoritmo) -> MetricasModelo:
    return MetricasModelo(
        algoritmo=algoritmo,
        tipo_evento=TipoEvento.SEQUIA,
        version="prueba-0.0.0",
        f1_macro=f1,
    )


def test_comparar_con_linea_base_devuelve_supera_y_valor_p():
    """El contraste de H1 produce los dos valores, no uno."""
    supera, valor_p = EvaluadorSimulado().comparar_con_linea_base(
        _metricas(0.72, Algoritmo.RANDOM_FOREST),
        _metricas(0.55, Algoritmo.LINEA_BASE),
    )

    assert supera is True
    assert isinstance(valor_p, float)
    assert 0.0 <= valor_p <= 1.0


def test_comparar_con_linea_base_resultado_negativo_no_lanza_error():
    """
    Prioridad 1, y es el caso que sostiene la honestidad del proyecto.

    **Un modelo que no supera la linea base es un resultado valido**, no una
    excepcion ni un caso que se descarta. Significa que los datos abiertos
    globales no bastan a escala cantonal, y eso es un hallazgo publicable.

    Si esta llamada lanzara, la unica salida del codigo seria un resultado
    positivo, y H1 dejaria de ser refutable.
    """
    supera, valor_p = EvaluadorSimulado().comparar_con_linea_base(
        _metricas(0.41, Algoritmo.RANDOM_FOREST),
        _metricas(0.63, Algoritmo.LINEA_BASE),
    )

    assert supera is False
    assert isinstance(valor_p, float)


def test_comparar_con_linea_base_es_simetrico_en_su_veredicto():
    """
    Invertir los argumentos invierte el veredicto. Si no lo hiciera, el
    comparador tendria un lado favorito y el contraste no mediria la diferencia
    sino el orden en que se le pasan las metricas.
    """
    evaluador = EvaluadorSimulado()
    modelo = _metricas(0.72, Algoritmo.RANDOM_FOREST)
    base = _metricas(0.55, Algoritmo.LINEA_BASE)

    supera, _ = evaluador.comparar_con_linea_base(modelo, base)
    al_reves, _ = evaluador.comparar_con_linea_base(base, modelo)

    assert supera is not al_reves


def test_las_metricas_nuevas_no_declaran_haber_superado_la_linea_base():
    """
    `supera_linea_base` nace en None y no en False. **None es "no se contrasto"
    y False es "se contrasto y no supero"**, que no son lo mismo: confundirlos
    convertiria un modelo sin evaluar en uno evaluado y rechazado.
    """
    assert _metricas(0.72, Algoritmo.RANDOM_FOREST).supera_linea_base is None
