"""Pruebas del extractor de la serie larga del canton. Historia H1.16.

No tocan la red: se le pasan respuestas armadas a mano, con la forma exacta que
la API devolvio el 2026-09-14. Lo que se prueba es lo que se puede probar sin
internet -el parseo y las tres guardas- y sobre todo **que las guardas saben
fallar**, que es la regla del proyecto para cualquier control.
"""

from __future__ import annotations

import json
from datetime import date

import pytest

from backend.etl.fuentes import open_meteo
from backend.etl.fuentes.open_meteo import (
    MODELO_PROHIBIDO,
    ErrorOpenMeteo,
    ExtractorOpenMeteoCanton,
)

PUNTO = (10.47, -84.97)


def extractor(**kw) -> ExtractorOpenMeteoCanton:
    return ExtractorOpenMeteoCanton(punto_lat=PUNTO[0], punto_lon=PUNTO[1], **kw)


def respuesta(fechas, lluvias, lat=10.5, lon=-85.0):
    return {
        "latitude": lat,
        "longitude": lon,
        "daily": {"time": fechas, "precipitation_sum": lluvias},
    }


def test_lee_la_serie_y_conserva_la_celda_que_devolvio_la_fuente():
    filas = extractor().leer(respuesta(["1950-01-01", "1950-01-02"], [0.9, 0.3]))

    assert [f.fecha for f in filas] == [date(1950, 1, 1), date(1950, 1, 2)]
    assert [f.precipitacion_mm for f in filas] == [0.9, 0.3]
    # La celda es la DEVUELTA, no la pedida: es lo que hace auditable el dato.
    assert (filas[0].celda_lat, filas[0].celda_lon) == (10.5, -85.0)
    assert (filas[0].punto_lat, filas[0].punto_lon) == PUNTO


def test_un_hueco_vuelve_como_ausencia_y_no_como_cero():
    """D-07. Contar episodios de sequia sobre ceros inventados no es medir."""
    filas = extractor().leer(respuesta(["2020-01-01", "2020-01-02"], [None, 1.5]))

    assert filas[0].precipitacion_mm is None
    assert filas[1].precipitacion_mm == 1.5


def test_una_serie_entera_en_null_falla_en_vez_de_guardarse():
    """El sabotaje: es exactamente lo que devuelve `era5_land` con la lluvia.

    Sin esta guarda se guardarian 27.394 ausencias y se llamarian serie.
    """
    with pytest.raises(ErrorOpenMeteo) as caso:
        extractor(modelo="era5_land").leer(
            respuesta(["1950-01-01", "1950-01-02", "1950-01-03"], [None, None, None])
        )

    assert "era5_land" in str(caso.value)


def test_el_modelo_no_puede_quedar_en_manos_de_la_api():
    """Sin declararlo, la API elige sola y devuelve otra celda (medido el 09-14)."""
    with pytest.raises(ValueError):
        extractor(modelo=MODELO_PROHIBIDO)
    with pytest.raises(ValueError):
        extractor(modelo="")


def test_una_serie_despareja_no_se_empareja_a_la_fuerza():
    with pytest.raises(ErrorOpenMeteo) as caso:
        extractor().leer(respuesta(["2020-01-01", "2020-01-02"], [1.0]))

    assert "despareja" in str(caso.value)


def test_sin_precipitacion_en_la_respuesta_se_dice_cual_falta():
    with pytest.raises(ErrorOpenMeteo) as caso:
        extractor().leer({"latitude": 10.5, "longitude": -85.0, "daily": {"time": ["2020-01-01"]}})

    assert "precipitation_sum" in str(caso.value)


def test_sin_celda_declarada_no_se_guarda_nada():
    with pytest.raises(ErrorOpenMeteo):
        extractor().leer({"daily": {"time": ["2020-01-01"], "precipitation_sum": [1.0]}})


def test_no_se_piden_anios_anteriores_al_archivo():
    with pytest.raises(ValueError):
        extractor().consultar(date(1949, 12, 31), date(1950, 1, 1))


def test_la_url_declara_el_modelo_y_el_rango():
    u = extractor().url(date(1950, 1, 1), date(2024, 12, 31))

    assert "models=era5" in u
    assert "start_date=1950-01-01" in u and "end_date=2024-12-31" in u
    assert "daily=precipitation_sum" in u
    assert MODELO_PROHIBIDO not in u


class RespuestaFalsa:
    """Lo minimo que `urlopen` devuelve: un contexto con `.read()`."""

    def __init__(self, cuerpo: dict) -> None:
        self._cuerpo = json.dumps(cuerpo).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self) -> bytes:
        return self._cuerpo


def test_cuenta_sus_peticiones_para_poder_declararlas(monkeypatch):
    """CA-7: el rango entero, del 1950 a hoy, sale en UNA sola peticion.

    Esta prueba se escribio primero comprobando que `consultar` fallara sin red
    y que el contador subiera igual. Estaba mal por dos razones y el CI la
    delato: en una maquina CON internet no fallaba -y la prueba daba rojo-, y
    cuando "pasaba" era porque acababa de hacer una peticion de verdad, en una
    suite cuyo encabezado promete que no toca la red.

    Lo que se mide es el contador, asi que la red se reemplaza y no se usa.
    """
    llamadas = []

    def urlopen_falso(url, timeout=None):
        llamadas.append(url)
        return RespuestaFalsa(respuesta(["1950-01-01", "1950-01-02"], [0.9, 0.3]))

    monkeypatch.setattr(open_meteo.urllib.request, "urlopen", urlopen_falso)

    e = extractor()
    assert e.peticiones == 0
    filas = e.consultar(date(1950, 1, 1), date(2026, 9, 9))

    assert e.peticiones == 1
    assert len(llamadas) == 1, "el rango completo tiene que salir en una sola peticion"
    assert len(filas) == 2


def test_una_peticion_que_falla_igual_gasta_la_cuota(monkeypatch):
    """El contador cuenta intentos, no exitos: la cuota se gasta igual."""

    def urlopen_que_revienta(url, timeout=None):
        raise OSError("la red se cayo")

    monkeypatch.setattr(open_meteo.urllib.request, "urlopen", urlopen_que_revienta)

    e = extractor()
    with pytest.raises(ErrorOpenMeteo):
        e.consultar(date(1950, 1, 1), date(1950, 1, 2))

    assert e.peticiones == 1
