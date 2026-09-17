"""Pruebas de `correlacion_enso`. Historia H3.10.

**Ninguna toca la red ni la base**, igual que las de `oni.py`: la matriz de
prueba se arma aca adentro.

Los valores esperados de `correlacion` estan calculados **a mano** y escritos en
la prueba, no sacados de la propia funcion. Una prueba que compara una funcion
consigo misma pasa en verde con la funcion rota; es el mismo defecto de forma que
el CA-4 de H6.3 tenia -afirmar mas de lo que se mide- y no tiene sentido
arreglarlo alla y repetirlo aca.
"""

from __future__ import annotations

from datetime import date

from backend.modelado.correlacion_enso import (
    FUERTE,
    MINIMO_PAREJAS,
    alineadas,
    columnas_comparables,
    correlacion,
    por_distrito,
)
from backend.modelado.generar_caracteristicas import COLUMNAS_CONTEXTO
from backend.modelado.oni import COLUMNAS_ONI

#: Repetido hasta pasar `MINIMO_PAREJAS`. Replicar el patron **no cambia** el
#: Pearson -numerador y denominador se multiplican por el mismo factor- asi que
#: el valor esperado sigue siendo el que se calculo a mano sobre los cinco.
VECES = 8

BASE = [1.0, 2.0, 3.0, 4.0, 5.0]


def test_una_recta_creciente_da_uno():
    assert correlacion(BASE * VECES, [2.0, 4.0, 6.0, 8.0, 10.0] * VECES) == 1.0


def test_una_recta_decreciente_da_menos_uno():
    assert correlacion(BASE * VECES, [5.0, 4.0, 3.0, 2.0, 1.0] * VECES) == -1.0


def test_coincide_con_el_calculo_a_mano():
    """x=[1..5], y=[2,1,4,3,5]: sxy = 8, sxx = 10, syy = 10, r = 8/10 = 0.8 exacto."""
    assert abs(correlacion(BASE * VECES, [2.0, 1.0, 4.0, 3.0, 5.0] * VECES) - 0.8) < 1e-12


def test_una_serie_constante_no_da_cero_sino_nada():
    """Devolver 0.0 aca afirmaria «no hay relacion»; lo cierto es «no se puede saber».

    Es la distincion que hace util a este guion: el ONI dentro de un pliegue
    corto puede ser constante, y un 0.0 inventado ahi se leeria como evidencia de
    que el indice no sirve, cuando lo que pasa es que no se pudo medir.
    """
    constante = [7.0] * (5 * VECES)
    assert correlacion(BASE * VECES, constante) is None
    assert correlacion(constante, BASE * VECES) is None


def test_pocas_parejas_no_producen_un_numero():
    assert len(BASE) < MINIMO_PAREJAS
    assert correlacion(BASE, [2.0, 4.0, 6.0, 8.0, 10.0]) is None


def _matriz() -> dict[tuple[str, date], dict[str, float]]:
    """Dos distritos, y una fila a la que le falta la columna de lluvia."""
    return {
        ("50801", date(2020, 1, 1)): {"enso_oni": 0.5, "pp_acum30": 10.0, "cal_seno": 0.1},
        ("50801", date(2020, 1, 2)): {"enso_oni": 0.5, "cal_seno": 0.2},
        ("50802", date(2020, 1, 1)): {"enso_oni": 0.5, "pp_acum30": 20.0, "cal_seno": 0.1},
    }


def test_las_columnas_quedan_alineadas_por_fecha_y_no_por_azar():
    """El hueco entra como None y se descarta de a pares, no columna por columna.

    Si cada columna descartara sus propios huecos, dos listas del mismo largo
    podrian corresponder a fechas distintas y el Pearson seria entre cosas que no
    pasaron el mismo dia. Aca 50801 tiene dos filas y solo una con `pp_acum30`.
    """
    tablas = por_distrito(_matriz())
    assert tablas["50801"]["pp_acum30"] == [10.0, None]
    x, y = alineadas(tablas["50801"], "enso_oni", "pp_acum30")
    assert x == [0.5]
    assert y == [10.0]


def test_cada_distrito_va_por_su_cuenta():
    """El ONI es el mismo para los ocho; la lluvia no. Mezclarlos hunde el Pearson."""
    tablas = por_distrito(_matriz())
    assert sorted(tablas) == ["50801", "50802"]
    assert len(tablas["50802"]["pp_acum30"]) == 1


def test_el_oni_no_se_compara_contra_si_mismo():
    """`enso_oni` contra `enso_oni_r3` daria un numero alto y vacio: misma serie corrida."""
    assert not set(columnas_comparables(_matriz())) & set(COLUMNAS_ONI)


def test_las_columnas_de_contexto_quedan_fuera():
    """Que el ONI se parezca al calendario es el ciclo anual, no una senal climatica."""
    encontradas = columnas_comparables(_matriz())
    assert "pp_acum30" in encontradas
    assert not set(encontradas) & set(COLUMNAS_CONTEXTO)


def test_el_corte_esta_declarado_antes_de_mirar_los_resultados():
    """CA-3 de H3.10 en miniatura: el umbral se fija antes, no despues.

    Si `FUERTE` se elige mirando los numeros que salieron, la conclusion se
    acomoda al resultado. Esta prueba no lo valida, lo **congela**: cambiarlo
    obliga a tocar la prueba y a decir por que en el cuerpo del PR.
    """
    assert FUERTE == 0.30
