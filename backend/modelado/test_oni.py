"""Pruebas del lector del ONI. Historia H3.10.

No tocan la red **nunca**: leen el archivo versionado, que es justamente lo que
el CA-2 pide y lo que el CA-7 necesita.

La prueba central es `test_el_archivo_versionado_no_tiene_huecos`: si el indice
tuviera un mes faltante dentro del rango, las filas de **los ocho distritos** de
ese dia se caerian de la matriz sin que ninguna cifra bajara de golpe.
"""

from __future__ import annotations

from datetime import date

import pytest

from backend.modelado.oni import (
    COLUMNAS_ONI,
    MES_DE_LA_ESTACION,
    REZAGOS_MESES,
    ErrorOni,
    agregar_enso,
    atraso_meses,
    columnas_de,
    leer_oni,
    ultima_fecha_cubierta,
    ultimo_mes_con_dato,
)


def test_el_archivo_versionado_se_lee_entero():
    oni = leer_oni()
    claves = sorted(oni)

    assert len(oni) == 919, "920 lineas = 1 encabezado + 919 filas"
    assert claves[0] == (1950, 1), "la primera es DJF 1950, centrada en enero"
    assert claves[-1] == (2026, 7), "la ultima es JJA 2026, centrada en julio"


def test_el_archivo_versionado_no_tiene_huecos():
    """Un mes faltante se llevaria las filas de los ocho distritos de ese dia."""
    oni = leer_oni()
    claves = sorted(oni)

    faltan = []
    anio, mes = claves[0]
    while (anio, mes) <= claves[-1]:
        if (anio, mes) not in oni:
            faltan.append((anio, mes))
        anio, mes = (anio + 1, 1) if mes == 12 else (anio, mes + 1)

    assert faltan == []


def test_la_estacion_se_asigna_a_su_mes_central():
    """DJF es diciembre-enero-febrero y va a ENERO, no a diciembre."""
    assert MES_DE_LA_ESTACION["DJF"] == 1
    assert MES_DE_LA_ESTACION["NDJ"] == 12
    assert len(MES_DE_LA_ESTACION) == 12
    assert sorted(MES_DE_LA_ESTACION.values()) == list(range(1, 13))


def test_el_pico_del_nino_2015_cae_donde_la_historia_dice():
    """Control contra un hecho conocido, no contra el propio codigo.

    El Nino 2015-2016 fue el mas fuerte registrado y su maximo esta en el
    trimestre NDJ de 2015. Si el mapeo de estaciones estuviera corrido, este
    valor aparecería en otro mes.
    """
    oni = leer_oni()

    assert oni[(2015, 12)] == 2.59
    assert max(oni.values()) == 2.59
    assert max(oni, key=oni.get) == (2015, 12)


def test_los_rezagos_son_multiplos_de_tres():
    """El indice ya es una media de tres meses: un rezago de 1 no es ventana nueva.

    Con rezagos de 1 o 2 las ventanas comparten dos de sus tres meses y entran al
    modelo columnas casi colineales, que es el defecto que H3.9 corrigio al
    descartar `temp_min_c` y `temp_media_c`.
    """
    assert all(r % 3 == 0 for r in REZAGOS_MESES)
    assert len(set(REZAGOS_MESES)) == len(REZAGOS_MESES)
    assert len(COLUMNAS_ONI) == len(REZAGOS_MESES)


def test_los_rezagos_miran_al_pasado_y_cruzan_el_anio():
    oni = leer_oni()

    columnas = columnas_de(date(1991, 1, 15), oni)

    assert columnas["enso_oni"] == oni[(1991, 1)]
    assert columnas["enso_oni_r3"] == oni[(1990, 10)], "tres meses atras cruza el anio"
    assert columnas["enso_oni_r6"] == oni[(1990, 7)]


def test_un_mes_que_falta_revienta_en_vez_de_devolver_cero():
    """Cero seria «ENSO neutral», que es una afirmacion, no «no se sabe».

    Y None tampoco: el estimador no imputa, asi que una columna nula se lleva la
    fila entera en silencio.
    """
    oni = {(2020, 1): 0.5}

    with pytest.raises(ErrorOni) as caso:
        columnas_de(date(2020, 1, 15), oni)

    assert "2019-10" in str(caso.value), "dice cual mes falta, no solo que falta"


def test_agregar_enso_pone_las_columnas_declaradas_y_no_toca_las_otras():
    oni = leer_oni()
    matriz = {
        ("50801", date(2015, 12, 31)): {"pp_acum_7": 12.0},
        ("50807", date(2015, 12, 31)): {"pp_acum_7": 3.0},
    }

    agregar_enso(matriz, oni)

    for fila in matriz.values():
        assert set(COLUMNAS_ONI) <= set(fila)
        assert fila["enso_oni"] == 2.59
        assert fila["pp_acum_7"] in (12.0, 3.0), "no toca lo que ya estaba"


def test_el_mismo_valor_va_a_los_ocho_distritos_del_mismo_dia():
    """No es trampa -el indice describe el oceano, no el distrito- pero se dice.

    La consecuencia es que esa columna se repite unas 240 veces por mes y **eso
    no son 240 observaciones independientes**.
    """
    oni = leer_oni()
    dia = date(2015, 12, 31)
    matriz = {(f"5080{i}", dia): {} for i in range(1, 9)}

    agregar_enso(matriz, oni)

    valores = {fila["enso_oni"] for fila in matriz.values()}
    assert valores == {2.59}


def test_una_linea_con_otra_forma_revienta(tmp_path):
    malo = tmp_path / "oni.ascii.txt"
    malo.write_text(" SEAS  YR   TOTAL   ANOM\n  DJF 1950  25.01\n", encoding="utf-8")

    with pytest.raises(ErrorOni) as caso:
        leer_oni(malo)

    assert "Linea 2" in str(caso.value)


def test_una_estacion_repetida_revienta(tmp_path):
    malo = tmp_path / "oni.ascii.txt"
    malo.write_text(
        " SEAS  YR   TOTAL   ANOM\n  DJF 1950  25.01  -1.32\n  DJF 1950  25.01  -1.32\n",
        encoding="utf-8",
    )

    with pytest.raises(ErrorOni) as caso:
        leer_oni(malo)

    assert "dos veces" in str(caso.value)


def test_si_no_esta_el_archivo_lo_dice_y_no_sale_a_la_red(tmp_path):
    with pytest.raises(ErrorOni) as caso:
        leer_oni(tmp_path / "no-existe.txt")

    assert "nunca de la red" in str(caso.value)


def test_el_atraso_de_publicacion_se_mide_contra_el_archivo():
    """CA-7. El ONI no esta disponible para el mes en curso, hoy ni nunca.

    El valor de un mes es la media de un trimestre centrado en el, asi que el
    trimestre termina mes y medio despues del centro y recien entonces se
    publica. Esto no se supone: se cuenta contra el archivo que hay.
    """
    oni = leer_oni()

    assert ultimo_mes_con_dato(oni) == (2026, 7), "el archivo llega a JJA 2026"
    # Descargado el 2026-09-14: el mes mas reciente con valor es julio.
    assert atraso_meses(oni, date(2026, 9, 14)) == 2
    # Y el atraso crece solo con el calendario si nadie vuelve a bajar el archivo.
    assert atraso_meses(oni, date(2026, 12, 1)) == 5


def test_la_ultima_fecha_cubierta_es_el_fin_de_ese_mes():
    oni = leer_oni()

    assert ultima_fecha_cubierta(oni) == date(2026, 7, 31)


def test_la_ultima_fecha_cubierta_cruza_el_fin_de_anio():
    assert ultima_fecha_cubierta({(2020, 12): 0.1}) == date(2020, 12, 31)
    assert ultima_fecha_cubierta({(2020, 2): 0.1}) == date(2020, 2, 29), "bisiesto"
