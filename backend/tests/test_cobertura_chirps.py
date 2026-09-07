"""
Incidencia I-43: lo que se le pide a ClimateSERV se compara con lo que devuelve.

El 2026-09-04 la ingesta pidio 215 dias, recibio 3 y quedo `exitosa` con 1968
filas sin precipitacion. Estas pruebas fijan la regla que faltaba: la unica
respuesta corta aceptable es la truncada al final por la latencia de D-40.
Tambien cubren el rodeo (`--desde`) y la correccion de I-45 (la fuente se
declara solo cuando hay valor).
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from backend.etl import ingestar
from backend.etl.fuentes.chirps import LATENCIA_MAXIMA_DIAS, ErrorChirps, comprobar_cobertura
from contratos.esquemas import MedicionDiaria

DESDE = date(2025, 12, 29)
HASTA = date(2026, 7, 31)


def serie(desde: date, hasta: date, valor: float | None = 1.0) -> dict[date, float | None]:
    dias = (hasta - desde).days + 1
    return {desde + timedelta(days=i): valor for i in range(dias)}


def test_la_respuesta_completa_pasa_y_lo_dice():
    assert comprobar_cobertura(DESDE, HASTA, serie(DESDE, HASTA)) == "215 de 215 dias"


def test_el_caso_medido_por_luna_detiene_la_corrida():
    # 215 pedidos, 3 devueltos (2025-12-29..31), errMsg None. Antes: exitosa.
    devueltos = serie(DESDE, date(2025, 12, 31))
    with pytest.raises(ErrorChirps) as error:
        comprobar_cobertura(DESDE, HASTA, devueltos)
    mensaje = str(error.value)
    assert "3 de 215" in mensaje
    assert "I-43" in mensaje
    assert "No se escribe nada" in mensaje


def test_la_latencia_documentada_no_es_un_error():
    # La ingesta del 2026-09-04 pidio hasta el 09-03 y el final llegaba al 07-31:
    # 34 dias, dentro de lo que D-40 midio (21 a 51).
    fin_publicado = date(2026, 7, 31)
    frase = comprobar_cobertura(DESDE, date(2026, 9, 3), serie(DESDE, fin_publicado))
    assert "215 de 249 dias" in frase
    assert "2026-07-31" in frase
    assert "34 dias de latencia" in frase


def test_el_tope_de_latencia_es_el_borde():
    hasta = date(2026, 9, 3)
    justo = hasta - timedelta(days=LATENCIA_MAXIMA_DIAS)
    comprobar_cobertura(DESDE, hasta, serie(DESDE, justo))
    with pytest.raises(ErrorChirps):
        comprobar_cobertura(DESDE, hasta, serie(DESDE, justo - timedelta(days=1)))


def test_una_respuesta_vacia_no_es_una_fuente_sin_dato():
    with pytest.raises(ErrorChirps, match="0 de 215"):
        comprobar_cobertura(DESDE, HASTA, {})


def test_una_serie_con_huecos_no_es_latencia():
    devueltos = serie(DESDE, HASTA)
    del devueltos[date(2026, 3, 10)]
    with pytest.raises(ErrorChirps, match="con huecos"):
        comprobar_cobertura(DESDE, HASTA, devueltos)


def test_una_serie_que_no_empieza_donde_se_pidio_tampoco():
    devueltos = serie(DESDE + timedelta(days=1), HASTA)
    with pytest.raises(ErrorChirps, match="con huecos"):
        comprobar_cobertura(DESDE, HASTA, devueltos)


def test_fechas_fuera_de_la_ventana_se_rechazan():
    devueltos = serie(DESDE, HASTA)
    devueltos[HASTA + timedelta(days=1)] = 2.0
    with pytest.raises(ErrorChirps, match="fuera de la ventana"):
        comprobar_cobertura(DESDE, HASTA, devueltos)


def test_los_dias_marcados_sin_dato_cuentan_como_devueltos():
    # `None` es un dia que la fuente SI devolvio, marcado sin dato (D-07). No es
    # un hueco de la respuesta.
    devueltos = serie(DESDE, HASTA)
    devueltos[date(2026, 3, 10)] = None
    assert comprobar_cobertura(DESDE, HASTA, devueltos) == "215 de 215 dias"


# --------------------------------------------------------------------------- #
# El rodeo: --desde                                                            #
# --------------------------------------------------------------------------- #


def test_desde_se_acepta_como_fecha_iso():
    opciones = ingestar.analizador().parse_args(["--desde", "2025-12-01"])
    assert opciones.desde == date(2025, 12, 1)


def test_desde_es_opcional():
    assert ingestar.analizador().parse_args([]).desde is None


def test_desde_rechaza_una_fecha_mal_escrita():
    with pytest.raises(SystemExit):
        ingestar.analizador().parse_args(["--desde", "01/12/2025"])


# --------------------------------------------------------------------------- #
# I-45: la fuente declara el origen de un valor, no de una ausencia            #
# --------------------------------------------------------------------------- #


class _Cursor:
    rowcount = -1

    def __init__(self, registro: list) -> None:
        self._registro = registro

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, parametros=None):
        self._registro.append((sql, parametros))

    def executemany(self, sql, parametros):
        self._registro.append((sql, list(parametros)))


class _Transaccion:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class _Conexion:
    def __init__(self) -> None:
        self.registro: list = []

    def cursor(self):
        return _Cursor(self.registro)

    def transaction(self):
        return _Transaccion()


def test_un_dia_sin_precipitacion_no_declara_fuente():
    conexion = _Conexion()
    corrida = ingestar.Corrida(
        proceso="ingesta.lluvia_intensa", producto="chirps", estado="x", id=1
    )
    mediciones = [
        MedicionDiaria(codigo_distrito="50801", fecha=date(2026, 1, 1), precipitacion_mm=3.5),
        MedicionDiaria(codigo_distrito="50801", fecha=date(2026, 1, 2), precipitacion_mm=None),
    ]
    ingestar.escribir_mediciones(conexion, corrida, mediciones, "chirps")
    lotes = [p for sql, p in conexion.registro if isinstance(p, list)]
    assert len(lotes) == 1
    con_valor, sin_valor = lotes[0]
    assert con_valor["fuente_precipitacion"] == "chirps"
    assert sin_valor["fuente_precipitacion"] is None


def test_la_bitacora_guarda_cuantas_filas_trajo_la_fuente():
    assert "filas_leidas" in ingestar.SQL_CERRAR_CORRIDA
