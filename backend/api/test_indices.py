"""
Pruebas del SPI-6 al pedirlo, SIN base de datos. Historia H14.5, decision D-53.

Tres cosas se prueban aqui, y una no.

  1. `indices_de` es una funcion pura y se ejercita con una serie sintetica de
     35 anios: una fila por mes, la fecha es el ultimo dia del mes, y la
     ausencia sale None donde tiene que salir -los primeros meses, un mes con un
     dia sin dato, los meses que la fuente no entrego-.
  2. `RepositorioPostgres.obtener_indices` lee la serie UNA vez por distrito por
     ingesta (CA-8). Se cuenta con el doble de conexion de `test_repositorio_postgres`,
     que registra cada `execute`: dos consultas seguidas emiten una sola lectura
     de la serie, y una ingesta nueva vuelve a leer.
  3. `guardar_indices` sigue fallando, y su mensaje nombra a D-53 y no a una
     historia que nadie va a hacer.

Lo que NO se prueba: que el numero sea el SPI correcto. Eso es de
`backend/senales/spi.py` y de sus pruebas, y esta funcion no lo recalcula: lo
llama. Repetir aqui una prueba del SPI seria una segunda opinion sobre un
modulo ajeno.

Vive en `backend/api/` por la misma razon que `test_repositorio_postgres.py`, y
el CI lo corre porque `python -m pytest backend` recorre el paquete entero.

USO

    python -m pytest backend/api/test_indices.py -v
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta

import pytest

from backend.api.indices import DECIMALES, indices_de, ultimo_dia_del_mes
from backend.api.repositorio_postgres import RepositorioPostgres, TablaPendiente
from backend.api.test_repositorio_postgres import ConexionFalsa

CODIGO = "50801"


# --------------------------------------------------------------------------- #
# Serie sintetica                                                              #
# --------------------------------------------------------------------------- #


def serie(desde: date, hasta: date, semilla: int = 7) -> dict[date, float | None]:
    """
    Lluvia diaria inventada con estacion seca, para que la gamma tenga ceros.

    No pretende parecerse a Tilaran: pretende ejercitar las ramas. Es
    determinista por la semilla, asi que dos corridas dan los mismos numeros.
    """
    sorteo = random.Random(semilla)
    salida: dict[date, float | None] = {}
    dia = desde
    while dia <= hasta:
        if dia.month in (1, 2, 3, 4):
            valor = 0.0 if sorteo.random() < 0.6 else sorteo.expovariate(1 / 3)
        else:
            valor = sorteo.expovariate(1 / 8)
        salida[dia] = round(valor, 1)
        dia += timedelta(days=1)
    return salida


@pytest.fixture(scope="module")
def treinta_y_cinco_anios() -> dict[date, float | None]:
    return serie(date(1991, 1, 1), date(2025, 12, 31))


# --------------------------------------------------------------------------- #
# 1 · La funcion pura                                                          #
# --------------------------------------------------------------------------- #


def test_una_fila_por_mes_y_la_fecha_es_el_ultimo_dia(treinta_y_cinco_anios):
    filas = indices_de(CODIGO, treinta_y_cinco_anios)

    assert len(filas) == 35 * 12
    assert filas[0].fecha == date(1991, 1, 31)
    assert filas[1].fecha == date(1991, 2, 28)
    assert filas[-1].fecha == date(2025, 12, 31)
    assert all(f.codigo_distrito == CODIGO for f in filas)
    # 1992 es bisiesto: la fecha sale del calendario, no de una resta.
    assert ultimo_dia_del_mes(1992, 2) == date(1992, 2, 29)


def test_el_arranque_sale_none_y_despues_hay_valor(treinta_y_cinco_anios):
    filas = indices_de(CODIGO, treinta_y_cinco_anios)
    valores = [f.spi_6m for f in filas]

    # Los primeros meses no tienen seis meses de historia por delante.
    assert valores[0] is None
    # Y a partir de ahi la serie completa da un valor en todos los meses.
    con_valor = [v for v in valores if v is not None]
    assert len(con_valor) > 35 * 12 - 12
    assert all(-4 < v < 4 for v in con_valor)
    assert all(v == round(v, DECIMALES) for v in con_valor)


def test_un_dia_sin_dato_anula_el_mes_y_no_lo_rellena(treinta_y_cinco_anios):
    """
    Un total con dias de menos es menor por construccion y entraria como sequia.
    `acumulado_mensual` anula el mes; aqui se comprueba que la anulacion llega
    hasta la fila publicada y que la ventana movil la arrastra.
    """
    con_hueco = dict(treinta_y_cinco_anios)
    con_hueco[date(2010, 6, 15)] = None

    por_fecha = {f.fecha: f.spi_6m for f in indices_de(CODIGO, con_hueco)}
    sin_hueco = {f.fecha: f.spi_6m for f in indices_de(CODIGO, treinta_y_cinco_anios)}

    assert sin_hueco[date(2010, 6, 30)] is not None
    assert por_fecha[date(2010, 6, 30)] is None
    # El mes anterior no lo toca: su ventana termina antes del hueco y la gamma
    # de mayo se ajusta con los mismos mayos.
    assert por_fecha[date(2010, 5, 31)] == sin_hueco[date(2010, 5, 31)]
    # Un ano despues el junio SI se mueve, y esta prueba lo deja escrito en vez
    # de esconderlo: la gamma de junio se ajusta sobre todos los junios, y al
    # perder uno cambian sus parametros. Es lo que D-34 midio con la base del
    # ajuste -«mueve el numero»-, en chiquito. Medido con esta serie: 0,3973
    # contra 0,4125. Lo que se exige es que el corrimiento sea de ese tamano y
    # no un salto.
    assert por_fecha[date(2011, 6, 30)] is not None
    assert por_fecha[date(2011, 6, 30)] != sin_hueco[date(2011, 6, 30)]
    assert abs(por_fecha[date(2011, 6, 30)] - sin_hueco[date(2011, 6, 30)]) < 0.1


def test_los_meses_que_la_fuente_no_entrego_viajan_en_none(treinta_y_cinco_anios):
    """
    Es el caso de hoy: CHIRPS llega con 21 a 51 dias de atraso (D-40). Los meses
    sin dato se devuelven -una fila por mes- con el indice en None. No se omiten:
    la tarjeta tiene que poder decir «el ultimo con valor es julio».
    """
    hasta_julio = dict(treinta_y_cinco_anios)
    dia = date(2026, 1, 1)
    while dia <= date(2026, 9, 17):
        hasta_julio[dia] = 5.0 if dia <= date(2026, 7, 31) else None
        dia += timedelta(days=1)

    filas = indices_de(CODIGO, hasta_julio)
    ultimas = {f.fecha: f.spi_6m for f in filas[-3:]}

    assert list(ultimas) == [date(2026, 7, 31), date(2026, 8, 31), date(2026, 9, 30)]
    assert ultimas[date(2026, 7, 31)] is not None
    assert ultimas[date(2026, 8, 31)] is None
    assert ultimas[date(2026, 9, 30)] is None


def test_sin_serie_no_hay_filas():
    assert indices_de(CODIGO, {}) == []


def test_los_otros_indices_del_contrato_quedan_none(treinta_y_cinco_anios):
    """Nadie los calcula todavia; None es lo que el contrato dice que significa eso."""
    fila = indices_de(CODIGO, treinta_y_cinco_anios)[-1]
    assert fila.spi_1m is None
    assert fila.spi_3m is None
    assert fila.anomalia_temp_c is None
    assert fila.dias_sin_lluvia is None


# --------------------------------------------------------------------------- #
# 2 · El repositorio lee una vez por distrito por ingesta (CA-8)               #
# --------------------------------------------------------------------------- #

INGESTA_1 = datetime(2026, 9, 10, 6, 0)
INGESTA_2 = datetime(2026, 9, 17, 6, 0)


def filas_de_lluvia(hasta: date) -> list[tuple[date, float | None]]:
    """Lo que la base contestaria a SQL_LLUVIA: una fila por dia, hasta `hasta`."""
    datos = serie(date(1991, 1, 1), hasta)
    return [(dia, mm) for dia, mm in datos.items()]


def lecturas_de_serie(conexion: ConexionFalsa) -> int:
    return sum(1 for evento in conexion.sentencias() if "serie_climatica" in evento[1])


def test_dos_consultas_seguidas_leen_la_serie_una_vez():
    lluvia = filas_de_lluvia(date(2026, 7, 31))
    # La cola de resultados: ingesta, serie, ingesta. La segunda consulta pregunta
    # por la ingesta -tiene que hacerlo, es la clave- y NO vuelve a pedir la serie.
    conexion = ConexionFalsa(resultados=[[(INGESTA_1,)], lluvia, [(INGESTA_1,)]])
    repositorio = RepositorioPostgres(conexion=conexion)

    primera = repositorio.obtener_indices(CODIGO, date(2026, 1, 1), date(2026, 12, 31))
    segunda = repositorio.obtener_indices(CODIGO, date(2026, 1, 1), date(2026, 12, 31))

    assert lecturas_de_serie(conexion) == 1
    assert primera == segunda
    assert [f.fecha for f in primera] == [ultimo_dia_del_mes(2026, m) for m in range(1, 8)]
    assert all(f.spi_6m is not None for f in primera)


def test_una_ingesta_nueva_vuelve_a_leer():
    lluvia_vieja = filas_de_lluvia(date(2026, 6, 30))
    lluvia_nueva = filas_de_lluvia(date(2026, 7, 31))
    conexion = ConexionFalsa(
        resultados=[[(INGESTA_1,)], lluvia_vieja, [(INGESTA_2,)], lluvia_nueva]
    )
    repositorio = RepositorioPostgres(conexion=conexion)

    antes = repositorio.obtener_indices(CODIGO, date(2026, 1, 1), date(2026, 12, 31))
    despues = repositorio.obtener_indices(CODIGO, date(2026, 1, 1), date(2026, 12, 31))

    assert lecturas_de_serie(conexion) == 2
    assert antes[-1].fecha == date(2026, 6, 30)
    assert despues[-1].fecha == date(2026, 7, 31)


def test_el_rango_recorta_y_no_recalcula():
    lluvia = filas_de_lluvia(date(2026, 7, 31))
    conexion = ConexionFalsa(resultados=[[(INGESTA_1,)], lluvia, [(INGESTA_1,)]])
    repositorio = RepositorioPostgres(conexion=conexion)

    repositorio.obtener_indices(CODIGO, date(1991, 1, 1), date(2026, 12, 31))
    solo_julio = repositorio.obtener_indices(CODIGO, date(2026, 7, 1), date(2026, 7, 31))

    assert lecturas_de_serie(conexion) == 1
    assert [f.fecha for f in solo_julio] == [date(2026, 7, 31)]


def test_la_lectura_pide_la_serie_entera_desde_1991():
    """Un rango corto no puede dar un indice sin historia: la gamma se ajusta sobre todos los anios."""
    conexion = ConexionFalsa(resultados=[[(INGESTA_1,)], filas_de_lluvia(date(2026, 7, 31))])
    repositorio = RepositorioPostgres(conexion=conexion)

    repositorio.obtener_indices(CODIGO, date(2026, 7, 1), date(2026, 7, 31))

    (lectura,) = [e for e in conexion.sentencias() if "serie_climatica" in e[1]]
    parametros = lectura[2]
    assert parametros["codigo"] == CODIGO
    assert parametros["desde"] == date(1991, 1, 1)
    assert parametros["hasta"] >= date(2026, 7, 31)


# --------------------------------------------------------------------------- #
# 3 · guardar_indices no tiene tabla y lo dice                                 #
# --------------------------------------------------------------------------- #


def test_guardar_indices_nombra_a_d53_y_no_a_una_historia():
    repositorio = RepositorioPostgres(conexion=ConexionFalsa())
    with pytest.raises(TablaPendiente) as capturado:
        repositorio.guardar_indices([])
    mensaje = str(capturado.value)
    assert "D-53" in mensaje
    assert "H2.5" not in mensaje
    assert "no va a existir" in mensaje
