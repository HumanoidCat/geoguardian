"""
Pruebas de la regla de imputacion, contra huecos inyectados. Historia H1.4.

POR QUE HUECOS INYECTADOS Y NO OBSERVADOS

Porque no hay huecos observados. D-22 lo comprobo: cero nulos en las siete
variables, los ocho distritos y 12 784 dias. La limitacion queda declarada en la
propia decision: la regla se prueba contra huecos fabricados y no contra huecos
reales, y eso es lo que se puede hacer hoy.

DONDE VIVE ESTE ARCHIVO

En `backend/etl/` y no en `backend/tests/`, que es de Luna. El CI corre
`python -m pytest backend/tests`, asi que esta prueba no la ejecuta solo: la invoca
`verificar_h14.py`. Es la misma limitacion declarada en H6.2 y la misma peticion
pendiente.

USO

    python -m pytest backend/etl/test_imputacion.py -v
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from backend.etl.imputacion import (
    DIAS_CONSECUTIVOS_QUE_INUTILIZAN,
    FALTANTES_QUE_INUTILIZAN_EL_MES,
    ClaseDeSerie,
    Punto,
    SerieDeEventosNoSeImputa,
    imputar,
)
from contratos.enums import MetodoImputacion

INICIO = date(2024, 6, 1)


def serie_completa(dias: int = 30, primero: date = INICIO) -> list[Punto]:
    """Una serie sin huecos, con valores que crecen de uno en uno.

    Los valores crecen linealmente a proposito: asi el resultado correcto de una
    interpolacion lineal se sabe de antemano y la prueba puede exigir el valor y no
    solo que "haya algo".
    """
    return [Punto(fecha=primero + timedelta(days=i), valor=float(i)) for i in range(dias)]


def con_hueco(serie: list[Punto], desde: int, largo: int) -> list[Punto]:
    salida = list(serie)
    for i in range(desde, desde + largo):
        salida[i] = Punto(fecha=serie[i].fecha, valor=None)
    return salida


# --------------------------------------------------------------------------- #
# CA-1 - un hueco corto se imputa por interpolacion lineal                     #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("largo", [1, 2, 3, 4])
def test_un_hueco_de_hasta_cuatro_dias_se_imputa(largo):
    original = serie_completa()
    salida = imputar(con_hueco(original, desde=10, largo=largo), ClaseDeSerie.MALLA)

    for i in range(10, 10 + largo):
        assert salida[i].valor == pytest.approx(original[i].valor), (
            "los valores crecen de uno en uno, asi que la interpolacion tiene que"
            " devolver exactamente el valor original"
        )
        assert salida[i].imputado is True
        assert salida[i].metodo is MetodoImputacion.INTERPOLACION_LINEAL


def test_lo_que_no_es_hueco_no_se_toca():
    original = serie_completa()
    salida = imputar(con_hueco(original, desde=10, largo=2), ClaseDeSerie.MALLA)

    intactos = [p for i, p in enumerate(salida) if i not in (10, 11)]
    assert all(p.imputado is False for p in intactos)
    assert all(p.metodo is MetodoImputacion.SIN_IMPUTAR for p in intactos)


# --------------------------------------------------------------------------- #
# CA-2 - un hueco largo no se imputa                                           #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("largo", [5, 6, 10])
def test_un_hueco_de_cinco_dias_o_mas_no_se_imputa(largo):
    """WMO-No. 1203, 4.4.1(a): cinco dias seguidos inutilizan el mes."""
    salida = imputar(con_hueco(serie_completa(), desde=10, largo=largo), ClaseDeSerie.MALLA)

    for i in range(10, 10 + largo):
        assert salida[i].valor is None, "queda nulo, no relleno con un valor plausible"
        assert salida[i].imputado is False
        assert salida[i].metodo is MetodoImputacion.SIN_IMPUTAR


def test_el_corte_esta_donde_lo_pone_la_omm():
    """Cuatro se imputa y cinco no. La prueba lee la constante, no el numero."""
    assert DIAS_CONSECUTIVOS_QUE_INUTILIZAN == 5

    justo_debajo = imputar(con_hueco(serie_completa(), 10, 4), ClaseDeSerie.MALLA)
    justo_encima = imputar(con_hueco(serie_completa(), 10, 5), ClaseDeSerie.MALLA)

    assert justo_debajo[10].imputado is True
    assert justo_encima[10].imputado is False


# --------------------------------------------------------------------------- #
# CA-3 - once faltantes inutilizan el mes aunque los huecos sean cortos        #
# --------------------------------------------------------------------------- #


def test_once_huecos_de_un_dia_en_el_mismo_mes_no_se_imputan():
    """
    El otro umbral de la OMM, y **se puede violar sin violar el primero**.

    Once huecos de un solo dia pasan el corte de consecutivos y fallan el del total:
    cada uno es interpolable y el mes deja de serlo. Un verificador que solo mirara
    la longitud del hueco daria por bueno un mes que la fuente considera
    inutilizable.
    """
    assert FALTANTES_QUE_INUTILIZAN_EL_MES == 11

    serie = serie_completa()
    for i in range(1, 22, 2):  # once dias alternos, todos de junio
        serie = con_hueco(serie, desde=i, largo=1)

    salida = imputar(serie, ClaseDeSerie.MALLA)
    assert sum(1 for p in salida if p.imputado) == 0
    assert sum(1 for p in salida if p.valor is None) == 11


def test_diez_huecos_de_un_dia_si_se_imputan():
    """Diez esta por debajo del corte. Delimita el criterio por el otro lado."""
    serie = serie_completa()
    for i in range(1, 20, 2):  # diez dias alternos
        serie = con_hueco(serie, desde=i, largo=1)

    salida = imputar(serie, ClaseDeSerie.MALLA)
    assert sum(1 for p in salida if p.imputado) == 10


# --------------------------------------------------------------------------- #
# CA-4 - toda imputacion queda marcada                                         #
# --------------------------------------------------------------------------- #


def test_ninguna_fila_sale_con_valor_imputado_y_sin_imputar():
    """
    D-07: "toda imputacion deliberada debe quedar marcada con su MetodoImputacion".

    Una imputacion no declarada se vuelve invisible aguas abajo: quien lea la serie
    dentro de tres meses no puede distinguir un valor medido de uno calculado.
    """
    serie = con_hueco(con_hueco(serie_completa(), 5, 2), 20, 3)
    salida = imputar(serie, ClaseDeSerie.MALLA)

    mentirosas = [p for p in salida if p.imputado and p.metodo is MetodoImputacion.SIN_IMPUTAR]
    assert not mentirosas

    huerfanas = [
        p for p in salida if not p.imputado and p.metodo is not MetodoImputacion.SIN_IMPUTAR
    ]
    assert not huerfanas


# --------------------------------------------------------------------------- #
# CA-5 - una serie de eventos no se imputa nunca                               #
# --------------------------------------------------------------------------- #


def test_una_serie_de_eventos_no_se_imputa():
    with pytest.raises(SerieDeEventosNoSeImputa) as capturado:
        imputar(con_hueco(serie_completa(), 10, 1), ClaseDeSerie.EVENTOS)

    mensaje = str(capturado.value)
    assert "ES UN CERO" in mensaje, "el mensaje tiene que decir por que, no solo que no"
    assert "D-07" in mensaje


def test_la_negativa_no_depende_del_largo_del_hueco():
    """Ni siquiera un hueco de un dia en una serie de eventos se toca."""
    for largo in (1, 4, 30):
        with pytest.raises(SerieDeEventosNoSeImputa):
            imputar(con_hueco(serie_completa(), 0, largo), ClaseDeSerie.EVENTOS)


# --------------------------------------------------------------------------- #
# CA-6 - un cero no es un hueco                                               #
# --------------------------------------------------------------------------- #


def test_una_serie_llena_de_ceros_sale_identica():
    """
    D-07: "cero milimetros de lluvia es una medicion; la ausencia de dato no lo es".

    Es el defecto clasico: tratar el cero como faltante convierte una medicion en un
    valor inventado, y sesga hacia el escenario seco justo en el evento que mas
    interesa.
    """
    serie = [Punto(fecha=INICIO + timedelta(days=i), valor=0.0) for i in range(30)]
    salida = imputar(serie, ClaseDeSerie.MALLA)

    assert salida == serie
    assert all(p.valor == 0.0 for p in salida)
    assert not any(p.imputado for p in salida)


# --------------------------------------------------------------------------- #
# CA-7 - no se inventa fuera de los extremos                                   #
# --------------------------------------------------------------------------- #


def test_un_hueco_al_principio_no_se_imputa():
    """Sin vecino de un lado no hay entre que interpolar."""
    salida = imputar(con_hueco(serie_completa(), desde=0, largo=2), ClaseDeSerie.MALLA)
    assert salida[0].valor is None
    assert salida[1].valor is None


def test_un_hueco_al_final_no_se_imputa():
    serie = serie_completa()
    salida = imputar(con_hueco(serie, desde=len(serie) - 2, largo=2), ClaseDeSerie.MALLA)
    assert salida[-1].valor is None
    assert salida[-2].valor is None


def test_extender_el_ultimo_valor_conocido_seria_inventar():
    """
    Deja escrito por que el caso de arriba NO se resuelve con un relleno hacia
    adelante: repetir el ultimo valor produce una serie que parece medida y no lo
    esta, que es exactamente lo que D-07 descarta con el relleno por cero.
    """
    serie = serie_completa()
    salida = imputar(con_hueco(serie, desde=len(serie) - 1, largo=1), ClaseDeSerie.MALLA)
    assert salida[-1].valor is None
    assert salida[-1].valor != salida[-2].valor


# --------------------------------------------------------------------------- #
# La entrada no se modifica                                                    #
# --------------------------------------------------------------------------- #


def test_la_serie_de_entrada_no_se_modifica():
    entrada = con_hueco(serie_completa(), 10, 2)
    copia = list(entrada)
    imputar(entrada, ClaseDeSerie.MALLA)
    assert entrada == copia
