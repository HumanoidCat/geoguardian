"""Pruebas del recuento de sequias sobre la serie larga. Historia H3.11.

No tocan la red ni la base: la serie es sintetica y se arma aca.

La prueba que sostiene todo el PR es la primera. El CA-1 pide que los dos
numeros -el de D-34 y el de esta historia- signifiquen lo mismo, y la unica
forma de mostrarlo es **etiquetar la misma serie con las dos rutas y comparar
etiqueta por etiqueta**. Si algun dia cambia la definicion de sequia en H3.0 y
este guion no la sigue, esa prueba se pone roja.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

from backend.modelado.etiquetado import etiquetar_distrito
from backend.modelado.recontar_sequia_larga import (
    CANTON,
    etiquetar_canton,
    meses_sin_spi,
)


def serie_sintetica(
    desde: date = date(1980, 1, 1),
    hasta: date = date(2019, 12, 31),
    huecos: tuple[date, ...] = (),
) -> dict[date, float | None]:
    """Cuarenta anos de lluvia diaria con estacionalidad y variacion entre anios.

    La variacion importa: una serie constante deja a la gamma sin dispersion y
    el SPI sale igual para todos los meses, con lo que la prueba no probaria
    nada. El coseno da la estacion seca y el termino del anio mueve la escala.
    """
    serie: dict[date, float | None] = {}
    dia = desde
    while dia <= hasta:
        if dia in huecos:
            serie[dia] = None
        else:
            estacion = 1.0 + math.cos((dia.month - 9) / 12 * 2 * math.pi)
            anual = 1.0 + 0.6 * math.sin(dia.year * 1.7)
            serie[dia] = round(max(0.0, 4.0 * estacion * anual + (dia.day % 5)), 2)
        dia += timedelta(days=1)
    return serie


def test_la_etiqueta_es_la_misma_que_la_de_h30():
    """CA-1. La definicion de sequia se importa, no se copia: hay que probarlo.

    `etiquetar_distrito` es el codigo que produjo el 13 de D-34. Con la misma
    serie, la misma base y la misma ventana, `etiquetar_canton` tiene que dar
    **exactamente** las mismas etiquetas de sequia, dia por dia.
    """
    serie = serie_sintetica()
    fechas = sorted(serie)
    ventana = (fechas[0], fechas[-1] - timedelta(days=7))

    de_h30 = etiquetar_distrito(CANTON, serie, focos=[], desde=ventana[0], hasta=ventana[1])
    del_canton = etiquetar_canton(serie, base=(fechas[0], fechas[-1]), ventana=ventana)

    assert len(de_h30) == len(del_canton)
    diferencias = [
        (a.fecha, a.sequia, b.sequia)
        for a, b in zip(de_h30, del_canton, strict=True)
        if a.sequia is not b.sequia
    ]
    assert not diferencias, f"{len(diferencias)} etiquetas distintas, p.ej. {diferencias[:3]}"


def test_la_base_del_spi_cambia_el_resultado():
    """La razon de ser de CA-6: la vara no es neutral.

    Misma ventana etiquetada, dos bases distintas. Si el resultado fuera
    identico, separar los dos parametros no tendria sentido y CA-6 sobraria.
    """
    serie = serie_sintetica()
    ventana = (date(2000, 1, 1), date(2009, 12, 31))

    corta = etiquetar_canton(serie, base=ventana, ventana=ventana)
    larga = etiquetar_canton(serie, base=(date(1980, 1, 1), date(2019, 12, 31)), ventana=ventana)

    assert [e.sequia for e in corta] != [e.sequia for e in larga]


def test_la_ventana_no_arrastra_dias_de_fuera():
    serie = serie_sintetica()
    ventana = (date(2000, 3, 1), date(2000, 3, 31))

    etiquetas = etiquetar_canton(
        serie, base=(date(1980, 1, 1), date(2019, 12, 31)), ventana=ventana
    )

    assert len(etiquetas) == 31
    assert etiquetas[0].fecha == ventana[0] and etiquetas[-1].fecha == ventana[1]
    assert all(e.codigo_distrito == CANTON for e in etiquetas)


def test_el_recuento_no_inventa_lluvia_ni_incendio():
    """La serie del canton solo puede hablar de sequia.

    `lluvia_intensa` necesita percentiles del distrito y `incendio` necesita
    focos por distrito: ninguno de los dos existe a nivel canton. Salen None,
    que es «no se sabe», y no BAJO, que seria una afirmacion.
    """
    serie = serie_sintetica(date(2000, 1, 1), date(2009, 12, 31))
    etiquetas = etiquetar_canton(
        serie,
        base=(date(2000, 1, 1), date(2009, 12, 31)),
        ventana=(date(2005, 1, 1), date(2005, 1, 10)),
    )

    assert all(e.lluvia_intensa is None and e.incendio is None for e in etiquetas)


def test_meses_sin_spi_separa_el_arranque_del_hueco():
    """CA-9. Son dos motivos distintos y no se pueden contar juntos."""
    hueco = date(2005, 7, 14)
    serie = serie_sintetica(huecos=(hueco,))
    base = (date(1980, 1, 1), date(2019, 12, 31))

    faltantes = meses_sin_spi(serie, base)

    arranque = [m for m in faltantes if "arranque" in m]
    sin_dato = [m for m in faltantes if "sin dato" in m]
    assert len(arranque) == 5, "el SPI-6 no existe hasta el sexto mes: cinco meses"
    assert sin_dato == ["2005-07 (algun dia sin dato, D-07)"]


def test_un_dia_sin_dato_no_se_cuenta_como_cero():
    """D-07. Si el hueco entrara como cero, ese mes bajaria y seria una sequia."""
    hueco = date(2005, 7, 14)
    serie = serie_sintetica(huecos=(hueco,))

    assert serie[hueco] is None
    assert "2005-07 (algun dia sin dato, D-07)" in meses_sin_spi(
        serie, (date(1980, 1, 1), date(2019, 12, 31))
    )
