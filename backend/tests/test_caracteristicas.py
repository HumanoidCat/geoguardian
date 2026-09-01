"""Pruebas de rezagos, acumulados y medias moviles. Historia H2.5.

La prueba que importa es `test_no_mira_al_futuro`. Las demas comprueban que los
numeros salgan bien; esa comprueba que salgan bien **por la razon correcta**, y
es la unica cuyo fallo no se veria nunca en las metricas: una fuga hacia adelante
produce resultados MEJORES, que es justo lo que uno querria ver.

Los valores esperados se calculan a mano en el propio caso, no copiando una
corrida del codigo. Una prueba que compara el codigo contra su propia salida no
comprueba nada.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from backend.senales.caracteristicas import (
    Punto,
    acumulado,
    caracteristicas_por_distrito,
    matriz_de_caracteristicas,
    media_movil,
    rezago,
)


def serie(valores: list[float | None], desde: date = date(2020, 1, 1)) -> list[Punto]:
    return [Punto(desde + timedelta(days=i), v) for i, v in enumerate(valores)]


# --------------------------------------------------------------------------- #
# LA PRUEBA QUE IMPORTA                                                        #
# --------------------------------------------------------------------------- #
def test_no_mira_al_futuro():
    """Cambiar el futuro no puede mover el pasado. Por construccion, no por lectura.

    Se calculan las caracteristicas de una serie, se **reescribe la segunda
    mitad** con valores absurdos, y se exige que la primera mitad salga
    identica. Si alguna ventana mirara hacia adelante, algun numero se moveria.

    El etiquetado de H3.0 define el riesgo del dia `t` sobre los siete dias
    POSTERIORES a `t`. Una entrada que mire hacia adelante le estaria mostrando
    al modelo parte de la respuesta.
    """
    base = [float(i) for i in range(40)]
    antes = matriz_de_caracteristicas(serie(base), prefijo="p")

    alterada = base[:20] + [9999.0] * 20
    despues = matriz_de_caracteristicas(serie(alterada), prefijo="p")

    assert antes[:20] == despues[:20], "una caracteristica del pasado cambio al mover el futuro"


def test_la_ventana_incluye_el_dia_actual_y_eso_no_es_fuga():
    """`acum3` en el dia t suma t-2, t-1 y t. La etiqueta empieza en t+1."""
    r = acumulado(serie([1.0, 2.0, 3.0, 4.0]), 3)
    assert r[2].valor == 6.0  # 1+2+3
    assert r[3].valor == 9.0  # 2+3+4


# --------------------------------------------------------------------------- #
# Los nulos no son ceros                                                       #
# --------------------------------------------------------------------------- #
def test_una_ventana_con_hueco_da_None_y_no_suma_de_menos():
    r = acumulado(serie([1.0, None, 3.0]), 3)
    assert r[2].valor is None, "sumo ignorando el hueco: 4 mm es indistinguible de 4 mm completos"
    assert r[2].observados == 2


def test_la_media_divide_entre_los_observados_no_entre_la_ventana():
    """60 mm en 2 dias observados de 3 son 30, no 20.

    Dividir entre 3 equivale a contar el hueco como cero, que es lo que inventa
    sequias donde solo hubo un sensor apagado.
    """
    r = media_movil(serie([30.0, None, 30.0]), 3, minimo_observado=2)
    assert r[2].valor == pytest.approx(30.0)


def test_con_minimo_observado_se_calcula_y_se_declara_cuantos_dias_vio():
    r = acumulado(serie([1.0, None, 3.0]), 3, minimo_observado=2)
    assert r[2].valor == 4.0
    assert r[2].observados == 2
    assert r[2].esperados == 3
    assert not r[2].completa


def test_el_cero_es_un_dato_y_no_un_hueco():
    """Un dia sin lluvia suma cero y cuenta como observado. D-07."""
    r = acumulado(serie([0.0, 0.0, 0.0]), 3)
    assert r[2].valor == 0.0
    assert r[2].observados == 3
    assert r[2].completa


# --------------------------------------------------------------------------- #
# Los bordes                                                                   #
# --------------------------------------------------------------------------- #
def test_las_primeras_filas_no_se_recortan():
    """La salida mide lo mismo que la entrada, con None al principio."""
    v = rezago(serie([1.0, 2.0, 3.0]), 2)
    assert len(v) == 3
    assert v[:2] == [None, None]
    assert v[2] == 1.0


def test_ventana_mas_larga_que_la_serie_da_None():
    r = acumulado(serie([1.0, 2.0]), 30)
    assert all(x.valor is None for x in r)


def test_serie_vacia_no_revienta():
    assert matriz_de_caracteristicas([], prefijo="p") == []


# --------------------------------------------------------------------------- #
# Lo que se rechaza en vez de calcular mal                                     #
# --------------------------------------------------------------------------- #
def test_un_hueco_de_calendario_se_rechaza():
    """Falta la fila del dia 2. Las ventanas cuentan posiciones, no fechas.

    Sin esta comprobacion, un `acum3` abarcaria 5 dias de calendario sin avisar.
    Una fila ausente no es lo mismo que un valor nulo.
    """
    huecos = [Punto(date(2020, 1, 1), 1.0), Punto(date(2020, 1, 3), 2.0)]
    with pytest.raises(ValueError, match="hueco de calendario"):
        acumulado(huecos, 2)


def test_una_serie_desordenada_se_rechaza():
    desordenada = [Punto(date(2020, 1, 2), 1.0), Punto(date(2020, 1, 1), 2.0)]
    with pytest.raises(ValueError, match="ordenada"):
        acumulado(desordenada, 2)


def test_fecha_repetida_se_rechaza():
    repetida = [Punto(date(2020, 1, 1), 1.0), Punto(date(2020, 1, 1), 2.0)]
    with pytest.raises(ValueError, match="ordenada o repite"):
        acumulado(repetida, 2)


def test_ventana_o_rezago_invalidos_se_rechazan():
    with pytest.raises(ValueError):
        rezago(serie([1.0]), 0)
    with pytest.raises(ValueError):
        acumulado(serie([1.0]), 0)


# --------------------------------------------------------------------------- #
# El agrupamiento por distrito                                                 #
# --------------------------------------------------------------------------- #
def test_la_media_movil_no_cruza_de_un_distrito_a_otro():
    """El defecto clasico: una ventana que arrastra el final de Tilaran al
    principio de Quebrada Grande. No levanta excepcion y da un numero plausible.
    """
    salida = caracteristicas_por_distrito(
        {"50801": serie([100.0, 100.0]), "50802": serie([0.0, 0.0])},
        prefijo="lluvia",
    )
    # Si cruzara, el primer dia de 50802 veria los 100 del distrito anterior.
    assert salida["50802"][0]["lluvia_acum3"] is None
    assert salida["50802"][1]["lluvia_media3"] is None


def test_los_nombres_de_columna_son_estables():
    """H3.6 compara estimadores entre corridas; si los nombres bailan, no puede."""
    fila = matriz_de_caracteristicas(serie([1.0] * 40), prefijo="lluvia")[-1]
    for esperado in (
        "lluvia_rez1",
        "lluvia_rez7",
        "lluvia_acum3",
        "lluvia_acum30",
        "lluvia_media7",
        "lluvia_acum3_observados",
    ):
        assert esperado in fila


def test_es_reproducible():
    """Dos corridas sobre la misma entrada dan exactamente lo mismo."""
    s = serie([float(i % 7) for i in range(50)])
    assert matriz_de_caracteristicas(s, prefijo="p") == matriz_de_caracteristicas(s, prefijo="p")
