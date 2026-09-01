"""La matriz de caracteristicas de H3.3, probada sobre series construidas a mano.

No hay base de datos aca a proposito. Lo que se prueba es **la construccion de la
matriz**, que es donde estan los errores que no se ven: una columna colineal, un
umbral que no se puede cumplir, una caracteristica que mira al futuro.
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

import pytest

from backend.modelado.generar_caracteristicas import (
    SE_ACUMULAN,
    VARIABLES,
    construir,
    escribir,
    leer,
    rendimiento,
    sin_columnas_constantes,
)

INICIO = date(2020, 1, 1)


def serie(dias: int, *, huecos: set[int] | None = None, semilla: float = 1.0):
    """Una serie de un distrito, con valores crecientes y deterministas."""
    huecos = huecos or set()
    filas = []
    for i in range(dias):
        valor = None if i in huecos else semilla * (i + 1)
        filas.append(
            (
                INICIO + timedelta(days=i),
                {p: valor for p in VARIABLES.values()},
            )
        )
    return filas


# --------------------------------------------------------------------------- #
# Colinealidad                                                                  #
# --------------------------------------------------------------------------- #


def test_solo_la_precipitacion_se_acumula():
    """Sumar humedades no da una humedad, y la suma es colineal con la media.

    Es el mismo motivo por el que `temp_min_c` y `temp_media_c` quedaron fuera:
    entradas perfectamente correlacionadas no mejoran la prediccion y arruinan la
    interpretacion de los coeficientes, que es lo que H4.1 necesita.
    """
    matriz = construir({"50801": serie(60)}, None)
    columnas = {c for fila in matriz.values() for c in fila}

    assert any(c.startswith("pp_acum") for c in columnas)
    for prefijo in VARIABLES.values():
        if prefijo not in SE_ACUMULAN:
            assert not any(
                c.startswith(f"{prefijo}_acum") for c in columnas
            ), f"{prefijo} no deberia acumularse"


def test_la_media_y_el_acumulado_de_la_lluvia_no_son_la_misma_columna():
    """Para la lluvia las dos tienen sentido, y se comprueba que no coincidan."""
    matriz = construir({"50801": serie(60)}, None)
    fila = matriz[("50801", INICIO + timedelta(days=40))]
    assert fila["pp_acum7"] is not None
    assert fila["pp_acum7"] != pytest.approx(fila["pp_media7"])
    assert fila["pp_acum7"] == pytest.approx(fila["pp_media7"] * 7)


# --------------------------------------------------------------------------- #
# El umbral como fraccion                                                       #
# --------------------------------------------------------------------------- #


def test_el_minimo_es_una_fraccion_de_cada_ventana():
    """Un conteo absoluto es una trampa: la ventana de 3 nunca llega a 20.

    Con una fraccion, cada ventana recibe su propio umbral. Este es el defecto que
    hizo caer el rendimiento de 17,5 % a 0 % cuando el argumento era un entero.
    """
    entrada = {"50801": serie(120, huecos={10, 50, 90})}

    estricta = rendimiento(construir(entrada, None))
    relajada = rendimiento(construir(entrada, 0.8))

    assert relajada["completas"] > estricta["completas"]
    assert relajada["porcentaje"] > 50


def test_la_ventana_corta_sigue_siendo_estricta_con_fraccion_alta():
    """0,8 sobre 3 dias redondea hacia arriba a 3: la ventana corta no se relaja.

    Importa porque una media de 3 dias calculada sobre 2 no es una media de 3
    dias, y en las ventanas cortas el redondeo hacia abajo cambia el significado.
    """
    matriz = construir({"50801": serie(40, huecos={20})}, 0.8)
    # El dia 20 esta ausente, asi que las ventanas de 3 que lo tocan no se pueden
    # completar: 21, 22 y 23 (indices 20, 21, 22) miran hacia atras e incluyen el hueco.
    fila = matriz[("50801", INICIO + timedelta(days=21))]
    assert fila["pp_media3"] is None


# --------------------------------------------------------------------------- #
# Causalidad                                                                    #
# --------------------------------------------------------------------------- #


def test_ninguna_caracteristica_mira_al_futuro():
    """Reescribir la segunda mitad no puede cambiar ni un valor de la primera.

    Es la prueba central. Todas las caracteristicas son ventanas que **terminan**
    en la fila actual, asi que el pasado no puede depender del futuro. Si alguna
    vez alguien agrega una centrada -o un percentil sobre toda la serie- esta
    prueba lo dice antes de que el modelo aprenda del futuro y parezca buenisimo.
    """
    original = serie(100)
    alterada = list(original[:50]) + serie(100, semilla=999.0)[50:]

    antes = construir({"50801": original}, None)
    despues = construir({"50801": alterada}, None)

    for i in range(50):
        clave = ("50801", INICIO + timedelta(days=i))
        assert antes[clave] == despues[clave], f"la fila {i} cambio al reescribir el futuro"


def test_las_series_no_se_cruzan_entre_distritos():
    """Una media movil que cruza de un distrito a otro da un valor plausible y falso."""
    matriz = construir({"50801": serie(40), "50802": serie(40, semilla=100.0)}, None)
    primero = matriz[("50802", INICIO)]
    assert primero["pp_rez1"] is None, "el primer dia de un distrito no tiene ayer"


# --------------------------------------------------------------------------- #
# Columnas constantes                                                           #
# --------------------------------------------------------------------------- #


def test_se_quitan_las_columnas_constantes():
    """Una columna sin varianza no informa y ensucia la tabla de coeficientes.

    `StandardScaler` no falla con ella -sklearn cambia la desviacion cero por
    uno- asi que no se nota sola.
    """
    matriz = construir({"50801": serie(60)}, None)
    for fila in matriz.values():
        fila["constante"] = 7.0

    limpia, quitadas = sin_columnas_constantes(matriz)

    assert "constante" in quitadas
    assert all("constante" not in fila for fila in limpia.values())


def test_una_columna_que_varia_se_conserva():
    matriz = construir({"50801": serie(60)}, None)
    _, quitadas = sin_columnas_constantes(matriz)
    assert "pp_rez1" not in quitadas


# --------------------------------------------------------------------------- #
# El CSV                                                                        #
# --------------------------------------------------------------------------- #


def test_la_celda_vacia_no_se_lee_como_cero(tmp_path: Path):
    """**D-07 hasta el ultimo paso.** Un acumulado de lluvia vale cero muy seguido.

    Si «no se pudo calcular» se guardara como 0, seria indistinguible de «no
    llovio», y el modelo aprenderia que los dias sin medir son dias secos.
    """
    matriz = construir({"50801": serie(40)}, None)
    destino = tmp_path / "caracteristicas.csv"
    escribir(matriz, destino)

    crudo = list(csv.DictReader(destino.open(encoding="utf-8")))
    assert crudo[0]["pp_rez1"] == "", "el primer dia no tiene ayer y debe quedar vacio"

    leido = leer(destino)
    assert "pp_rez1" not in leido[("50801", INICIO)], "la clave ausente es la senal de hueco"
    assert leido[("50801", INICIO + timedelta(days=1))]["pp_rez1"] == pytest.approx(1.0)


def test_el_csv_va_y_vuelve_sin_perder_valores(tmp_path: Path):
    matriz = construir({"50801": serie(40)}, None)
    destino = tmp_path / "caracteristicas.csv"
    escribir(matriz, destino)
    leido = leer(destino)

    clave = ("50801", INICIO + timedelta(days=35))
    for columna, valor in matriz[clave].items():
        if valor is not None:
            assert leido[clave][columna] == pytest.approx(valor, rel=1e-6)


# --------------------------------------------------------------------------- #
# El rendimiento                                                                #
# --------------------------------------------------------------------------- #


def test_el_rendimiento_cuenta_filas_completas_no_columnas_llenas():
    """El estimador no imputa: una fila a la que le falta UNA columna no se usa.

    Por eso la cifra que importa es cuantas filas tienen todo, y no que
    porcentaje de las celdas esta lleno. Las dos se parecen y la segunda enganya.
    """
    matriz = construir({"50801": serie(60)}, None)
    r = rendimiento(matriz)

    a_mano = sum(1 for f in matriz.values() if all(v is not None for v in f.values()))
    assert r["completas"] == a_mano
    assert r["completas"] < r["filas"], "las primeras 30 filas no pueden tener la ventana de 30"
