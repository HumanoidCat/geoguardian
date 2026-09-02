"""
Pruebas del calculo del puntaje SUS. Historia H9.2a.

Congelan la regla del instrumento original de Brooke, ficha `[7]`: los items
impares aportan `respuesta - 1`, los pares `5 - respuesta`, y el total se
multiplica por 2,5.

**La prueba que mas importa es `test_los_extremos_dan_cero_y_cien`**, porque
verifica la alternancia. Si alguien "simplificara" la formula sumando todo
igual, el resto de las pruebas podria seguir pasando y esa fallaria.
"""

from __future__ import annotations

import pytest

from backend.calidad.sus import (
    UMBRAL_BUENA,
    UMBRAL_EXCELENTE,
    interpretar,
    promediar,
    puntuar,
)

# El peor cuestionario posible: en desacuerdo con lo bueno, de acuerdo con lo
# malo. Impares en 1 y pares en 5.
PEOR = [1, 5, 1, 5, 1, 5, 1, 5, 1, 5]

# El mejor: impares en 5 y pares en 1.
MEJOR = [5, 1, 5, 1, 5, 1, 5, 1, 5, 1]

# Todo en el punto medio.
NEUTRO = [3] * 10


# --------------------------------------------------------------------------- #
# La regla del instrumento                                                      #
# --------------------------------------------------------------------------- #


def test_los_extremos_dan_cero_y_cien():
    """
    **Congela la alternancia par/impar, que es lo unico dificil de esta cuenta.**

    Si alguien sumara todos los items igual, `PEOR` y `MEJOR` darian ambos 50 y
    esta prueba fallaria. Las otras podrian no notarlo.
    """
    assert puntuar(PEOR).valor == 0.0
    assert puntuar(MEJOR).valor == 100.0


def test_el_punto_medio_da_cincuenta():
    assert puntuar(NEUTRO).valor == 50.0


def test_un_caso_calculado_a_mano():
    """
    Respuestas 4 2 5 1 4 2 5 2 4 1.

    Impares (1,3,5,7,9) valen 4,5,4,5,4 -> aportan 3,4,3,4,3 = 17
    Pares  (2,4,6,8,10) valen 2,1,2,2,1 -> aportan 3,4,3,3,4 = 17
    Total 34, por 2,5 = 85,0

    La cuenta esta escrita aparte a proposito: si la funcion cambia, esta
    prueba no la sigue.
    """
    puntaje = puntuar([4, 2, 5, 1, 4, 2, 5, 2, 4, 1])

    assert puntaje.valor == pytest.approx(85.0)
    assert sum(puntaje.aporte_por_item) == pytest.approx(34.0)


def test_se_reporta_el_aporte_de_cada_item():
    """La cuenta tiene que poder auditarse, no solo su resultado."""
    puntaje = puntuar(MEJOR)

    assert len(puntaje.aporte_por_item) == 10
    assert all(a == 4.0 for a in puntaje.aporte_por_item)


def test_el_puntaje_no_se_puede_modificar():
    """
    `Puntaje` es inmutable. Un puntaje calculado no se ajusta a mano: si hay que
    corregirlo, se corrige la respuesta y se vuelve a calcular.
    """
    puntaje = puntuar(NEUTRO)

    with pytest.raises(AttributeError):
        puntaje.valor = 99.0  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# Lo que se rechaza, y por que                                                  #
# --------------------------------------------------------------------------- #


def test_un_cuestionario_incompleto_es_error_y_no_un_puntaje_parcial():
    """
    **Rellenar el hueco con el punto medio seria inventar una respuesta que el
    participante no dio.**

    Con nueve respuestas no hay un 90 % de un puntaje: no hay puntaje.
    """
    with pytest.raises(ValueError, match="10 items"):
        puntuar([3] * 9)


def test_mas_de_diez_respuestas_tambien_es_error():
    with pytest.raises(ValueError, match="10 items"):
        puntuar([3] * 11)


def test_una_respuesta_fuera_de_la_escala_es_error():
    for valor in (0, 6, -1):
        respuestas = [3] * 10
        respuestas[4] = valor
        with pytest.raises(ValueError, match="item 5"):
            puntuar(respuestas)


def test_el_error_nombra_todos_los_items_invalidos_no_solo_el_primero():
    """
    Quien transcribe una hoja de papel quiere corregir todo de una vez, no
    descubrir un error por corrida.
    """
    respuestas = [3] * 10
    respuestas[1] = 0
    respuestas[7] = 9

    with pytest.raises(ValueError) as error:
        puntuar(respuestas)

    assert "item 2" in str(error.value)
    assert "item 8" in str(error.value)


# --------------------------------------------------------------------------- #
# Interpretacion                                                                #
# --------------------------------------------------------------------------- #


def test_las_bandas_caen_donde_dicen():
    assert "excelente" in interpretar(UMBRAL_EXCELENTE)
    assert "buena" in interpretar(UMBRAL_BUENA)
    assert "por debajo" in interpretar(UMBRAL_BUENA - 0.1)


def test_la_interpretacion_nunca_devuelve_un_adjetivo_solo():
    """
    **Un "excelente" suelto se cita como veredicto.** La frase completa obliga a
    arrastrar de donde sale, incluida la deuda de verificacion sobre las bandas.
    """
    texto = interpretar(90.0)

    assert "NO es un porcentaje" in texto
    assert "[36]" in texto
    assert "[13]" in texto


def test_interpretar_rechaza_un_puntaje_imposible():
    for valor in (-0.1, 100.1):
        with pytest.raises(ValueError):
            interpretar(valor)


# --------------------------------------------------------------------------- #
# Promedio                                                                      #
# --------------------------------------------------------------------------- #


def test_el_promedio_de_pocos_participantes_viene_con_su_advertencia():
    """
    H9.2 contempla de 3 a 5 participantes, asi que esta advertencia se activa
    siempre. Es deliberado: el promedio no puede salir sin ella.
    """
    puntajes = [puntuar(MEJOR), puntuar(NEUTRO), puntuar(PEOR)]

    promedio, aviso = promediar(puntajes)

    assert promedio == pytest.approx(50.0)
    assert "sin poder estadistico" in aviso
    assert "individuales" in aviso


def test_promediar_sin_puntajes_es_error():
    """Un promedio de cero cuestionarios no es 0.0: no existe."""
    with pytest.raises(ValueError, match="no existe"):
        promediar([])


def test_el_promedio_no_esconde_la_dispersion():
    """
    Tres participantes en 0, 50 y 100 promedian 50, igual que tres en 50. El
    promedio solo no distingue esos dos casos, y por eso la advertencia exige
    reportar los individuales.
    """
    dispersos = [puntuar(PEOR), puntuar(NEUTRO), puntuar(MEJOR)]
    parejos = [puntuar(NEUTRO)] * 3

    assert promediar(dispersos)[0] == promediar(parejos)[0]
    assert [p.valor for p in dispersos] != [p.valor for p in parejos]
