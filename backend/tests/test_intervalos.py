"""Pruebas del intervalo de Wilson.

Se comprueban sobre todo los casos donde el intervalo de Wald -el que uno
escribe de memoria- da una respuesta absurda, porque son los que motivaron
escribir este modulo y son los que de verdad ocurren en el proyecto: la sequia
dio **0 de 7**.

Los valores de referencia se calculan aparte con la formula cerrada de Wilson,
no se copian de una corrida del propio codigo. Una prueba que compara el codigo
contra su propia salida no comprueba nada.
"""

from __future__ import annotations

import math

import pytest

from backend.modelado.intervalos import Z_95, realce_con_intervalo, wilson


def wilson_referencia(exitos: int, total: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson escrito de nuevo, en una linea por termino, para contrastar."""
    p = exitos / total
    denominador = 1 + z**2 / total
    centro = (p + z**2 / (2 * total)) / denominador
    margen = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominador
    return centro - margen, centro + margen


# --------------------------------------------------------------------------- #
# Los casos que rompen a Wald                                                   #
# --------------------------------------------------------------------------- #
def test_cero_exitos_no_da_intervalo_degenerado():
    """0 de 7 es el caso real de la sequia. Wald daria [0, 0]: certeza absoluta."""
    i = wilson(0, 7)
    assert i.punto == 0.0
    assert i.inferior == 0.0
    # El limite superior tiene que ser informativo, no cero.
    assert 0.30 < i.superior < 0.45


def test_todos_exitos_no_da_intervalo_degenerado():
    i = wilson(7, 7)
    assert i.punto == 1.0
    assert i.superior == 1.0
    assert 0.55 < i.inferior < 0.70


def test_coincide_con_la_formula_escrita_aparte():
    for exitos, total in [(0, 7), (2, 7), (3, 7), (22, 34), (5, 100), (500, 1000)]:
        i = wilson(exitos, total)
        inferior, superior = wilson_referencia(exitos, total)
        assert i.inferior == pytest.approx(max(0.0, inferior), abs=1e-12)
        assert i.superior == pytest.approx(min(1.0, superior), abs=1e-12)


# --------------------------------------------------------------------------- #
# Propiedades que tienen que valer siempre                                      #
# --------------------------------------------------------------------------- #
def test_el_punto_siempre_cae_dentro():
    for total in range(1, 60):
        for exitos in range(total + 1):
            i = wilson(exitos, total)
            assert i.inferior <= i.punto <= i.superior


def test_el_intervalo_se_angosta_al_crecer_la_muestra():
    """La misma proporcion con mas datos tiene que dar un intervalo mas corto."""
    anchos = [wilson(n // 2, n).amplitud for n in (10, 40, 160, 640, 2560)]
    assert anchos == sorted(anchos, reverse=True)


def test_amplitud_con_n_pequeno_es_la_del_caso_real():
    """34 eventos de lluvia, 22 detectados: el numero del documento.

    Si esta prueba falla porque el intervalo se angosto, alguien cambio el
    metodo y las conclusiones del documento hay que releerlas.
    """
    i = wilson(22, 34)
    assert i.punto == pytest.approx(0.647, abs=0.001)
    assert i.amplitud > 0.30, "con n=34 el intervalo NO es estrecho, y el documento lo dice"


# --------------------------------------------------------------------------- #
# El solape, que es la regla de lectura                                         #
# --------------------------------------------------------------------------- #
def test_solape_es_simetrico():
    a, b = wilson(2, 7), wilson(3, 7)
    assert a.solapa(b) == b.solapa(a)


def test_muestras_pequenas_se_solapan_aunque_el_punto_difiera():
    """28,6 % contra 42,9 % con n=7 **no** es una diferencia. Es el veredicto real."""
    assert wilson(2, 7).solapa(wilson(3, 7))


def test_muestras_grandes_separan_las_mismas_proporciones():
    """La misma diferencia de puntos, con n=700, si separa."""
    assert not wilson(200, 700).solapa(wilson(300, 700))


# --------------------------------------------------------------------------- #
# Errores que no se deben tragar en silencio                                    #
# --------------------------------------------------------------------------- #
def test_sin_muestra_falla_en_vez_de_inventar():
    with pytest.raises(ValueError):
        wilson(0, 0)


def test_exitos_fuera_de_rango_falla():
    with pytest.raises(ValueError):
        wilson(8, 7)
    with pytest.raises(ValueError):
        wilson(-1, 7)


# --------------------------------------------------------------------------- #
# El realce                                                                     #
# --------------------------------------------------------------------------- #
def test_realce_contiene_el_uno_cuando_no_hay_distincion():
    """Cobertura igual a la tasa base: el etiquetado no distingue, y el rango lo dice."""
    punto, menor, mayor = realce_con_intervalo(wilson(2, 7), wilson(2000, 7000))
    assert punto == pytest.approx(1.0, abs=0.01)
    assert menor < 1.0 < mayor


def test_realce_excluye_el_uno_cuando_la_distincion_es_clara():
    punto, menor, _ = realce_con_intervalo(wilson(300, 400), wilson(500, 10000))
    assert punto > 10
    assert menor > 1.0


def test_realce_sin_tasa_base_falla():
    with pytest.raises(ValueError):
        realce_con_intervalo(wilson(2, 7), wilson(0, 1000))


# --------------------------------------------------------------------------- #
# El veredicto de la comparacion de escalas                                     #
#                                                                               #
# Vive aca y no en un archivo aparte porque lo unico que se prueba es la regla  #
# de lectura de los intervalos, que es de este modulo.                          #
# --------------------------------------------------------------------------- #
from backend.modelado.comparar_escalas_spi import Medicion, veredicto  # noqa: E402


def _medicion(escala: int, detectados: int, contrastables: int, marcados: int, total: int):
    return Medicion(
        escala=escala,
        ventana=7,
        contrastables=contrastables,
        detectados=detectados,
        dias_marcados=marcados,
        dias_totales=total,
        fallos=[],
        episodios=0,
    )


def test_descarta_la_escala_separada_hacia_abajo():
    """**La regresion que importa.**

    Es el caso real medido el 2026-08-30: SPI-3 dio 0 de 7 y las otras dos 7 de
    7. La primera version de `veredicto` buscaba la de mayor cobertura, veia que
    SPI-6 y SPI-12 se solapaban entre si, y devolvia «sin veredicto» -enterrando
    que la escala en uso habia quedado separada por debajo de las dos.
    """
    salida = veredicto(
        [
            _medicion(3, 0, 7, 15_000, 100_000),
            _medicion(6, 7, 7, 15_000, 100_000),
            _medicion(12, 7, 7, 18_000, 100_000),
        ]
    )
    assert "DESCARTADA SPI-3" in salida
    assert "EMPATAN SPI-6, SPI-12" in salida


def test_no_descarta_nada_cuando_todas_se_solapan():
    salida = veredicto(
        [
            _medicion(3, 2, 7, 15_000, 100_000),
            _medicion(6, 3, 7, 15_000, 100_000),
            _medicion(12, 4, 7, 15_000, 100_000),
        ]
    )
    assert "DESCARTADA" not in salida
    assert "EMPATAN" in salida


def test_una_sola_sobreviviente_se_declara_con_su_realce():
    salida = veredicto(
        [
            _medicion(3, 0, 40, 15_000, 100_000),
            _medicion(6, 40, 40, 15_000, 100_000),
        ]
    )
    assert "DESCARTADA SPI-3" in salida
    assert "QUEDA SPI-6" in salida
    assert "excluye el 1,0" in salida


def test_sin_eventos_contrastables_no_inventa_veredicto():
    salida = veredicto([_medicion(3, 0, 0, 15_000, 100_000)])
    assert "SIN VEREDICTO" in salida
