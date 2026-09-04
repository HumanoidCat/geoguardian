"""
Pruebas del repositorio contra PostgreSQL, SIN base de datos. Historia H6.2.

QUE PRUEBA ESTO Y QUE NO

`RepositorioPostgres` recibe su conexion por el constructor, asi que se le puede
pasar un doble y ejercitar el modulo entero sin que exista un PostgreSQL en
ninguna parte. Eso es lo que pide el titulo de la historia.

**El doble NO ejecuta el SQL: lo registra.** Una prueba de aca puede afirmar que
se emitio cierta sentencia con ciertos parametros, y puede afirmar que el mapeo
de filas a esquemas del contrato es correcto. **No puede afirmar que el SQL sea
PostgreSQL valido ni que haga lo que dice.** Eso lo cubren los verificadores de
H1.1 y H1.3 contra la base real.

Correr sin base compra velocidad y aislamiento, y paga con no ejecutar el SQL.
Un doble que pretenda lo contrario es peor que no tenerlo, porque da verde sin
haber probado nada.

POR QUE LA BITACORA ES UNA LISTA DE EVENTOS Y NO UN CONTADOR

Contar transacciones diria «se abrio una», que tambien es cierto si la escritura
ocurrio fuera de ella. La bitacora guarda el orden, asi que se comprueba lo que
importa: que el `executemany` cae ENTRE el abre y el cierra. Es el defecto de
H1.1, donde el codigo decia «una transaccion por distrito» y corria una sola para
todo; se descubrio por un `descargado_en` unico en las ocho cargas.

DONDE VIVE ESTE ARCHIVO

En `backend/api/` y no en `backend/tests/`, que es de Luna. El CI corre
`python -m pytest backend/tests`, asi que esta prueba no la ejecuta solo: la
invoca `verificar_h62.py`. La limitacion esta declarada en la evidencia de H6.2
junto con la excepcion que haria falta para moverla.

USO

    python -m pytest backend/api/test_repositorio_postgres.py -v
"""

from __future__ import annotations

import inspect
from datetime import date

import pytest

from backend.api import repositorio_postgres as modulo
from backend.api.repositorio_postgres import (
    PENDIENTES,
    SQL_MEDICIONES,
    RepositorioPostgres,
    TablaPendiente,
)
from contratos.enums import MetodoImputacion
from contratos.esquemas import FocoCalor, MedicionDiaria
from contratos.repositorio import Repositorio

# --------------------------------------------------------------------------- #
# El doble                                                                     #
# --------------------------------------------------------------------------- #


class CursorFalso:
    """Imita la superficie de psycopg que el repositorio usa, y nada mas."""

    def __init__(self, conexion: ConexionFalsa) -> None:
        self._conexion = conexion
        self._filas: list[tuple] = []

    def __enter__(self) -> CursorFalso:
        self._conexion.bitacora.append(("abre_cursor",))
        return self

    def __exit__(self, *_excepcion) -> bool:
        self._conexion.bitacora.append(("cierra_cursor",))
        return False

    def execute(self, sql: str, parametros=None) -> None:
        self._conexion.bitacora.append(("execute", sql, parametros))
        self._filas = self._conexion.siguiente_resultado()

    def executemany(self, sql: str, secuencia) -> None:
        self._conexion.bitacora.append(("executemany", sql, list(secuencia)))

    def fetchall(self) -> list[tuple]:
        return self._filas

    def fetchone(self):
        return self._filas[0] if self._filas else None


class TransaccionFalsa:
    def __init__(self, conexion: ConexionFalsa) -> None:
        self._conexion = conexion

    def __enter__(self) -> TransaccionFalsa:
        self._conexion.bitacora.append(("abre_transaccion",))
        return self

    def __exit__(self, *_excepcion) -> bool:
        self._conexion.bitacora.append(("cierra_transaccion",))
        return False


class ConexionFalsa:
    """
    Conexion de mentira con memoria.

    `resultados` es una cola: cada `execute` consume el siguiente elemento. La
    prueba declara que le contesta la base y el repositorio hace el resto. No se
    intenta adivinar por el SQL, porque emparejar por texto seria una segunda
    implementacion que tambien puede estar mal.
    """

    def __init__(self, resultados=None) -> None:
        self.bitacora: list[tuple] = []
        self._resultados = list(resultados or [])
        self.cerrada = False

    def cursor(self) -> CursorFalso:
        return CursorFalso(self)

    def transaction(self) -> TransaccionFalsa:
        return TransaccionFalsa(self)

    def close(self) -> None:
        self.cerrada = True

    def siguiente_resultado(self) -> list[tuple]:
        return self._resultados.pop(0) if self._resultados else []

    # -- ayudas para las pruebas ------------------------------------------- #

    def eventos(self) -> list[str]:
        return [e[0] for e in self.bitacora]

    def sentencias(self) -> list[tuple]:
        return [e for e in self.bitacora if e[0] in ("execute", "executemany")]


# --------------------------------------------------------------------------- #
# Datos de ejemplo                                                             #
# --------------------------------------------------------------------------- #

GEOJSON = '{"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]]}'

FILA_DISTRITO = ("50801", "Tilaran", 638.4, None, GEOJSON)


def medicion(dia: int) -> MedicionDiaria:
    return MedicionDiaria(
        codigo_distrito="50801",
        fecha=date(2024, 6, dia),
        temp_max_c=30.0,
        precipitacion_mm=0.0,
        metodo_imputacion=MetodoImputacion.SIN_IMPUTAR,
    )


def foco(dia: int, satelite: str) -> FocoCalor:
    return FocoCalor(
        fecha=date(2024, 3, dia),
        latitud=10.47,
        longitud=-84.97,
        confianza=85,
        brillo_k=320.5,
        satelite=satelite,
    )


# --------------------------------------------------------------------------- #
# CA-1 - cumple el protocolo completo                                          #
# --------------------------------------------------------------------------- #


def metodos_del_protocolo() -> list[str]:
    return sorted(
        nombre
        for nombre, _ in inspect.getmembers(Repositorio, inspect.isfunction)
        if not nombre.startswith("_")
    )


def test_implementa_los_dieciseis_metodos_del_protocolo():
    faltan = [m for m in metodos_del_protocolo() if not hasattr(RepositorioPostgres, m)]
    assert not faltan, f"metodos del protocolo sin implementar: {faltan}"
    assert len(metodos_del_protocolo()) == 16


def test_las_firmas_coinciden_con_las_del_protocolo():
    """
    Se comparan los NOMBRES de los parametros, no las anotaciones.

    Con `from __future__ import annotations` las anotaciones son cadenas, y dos
    formas de escribir el mismo tipo darian distinto sin que nada este mal. Los
    nombres si importan: un endpoint que llame por palabra clave se rompe si
    cambian.
    """
    discrepan = {}
    for nombre in metodos_del_protocolo():
        del_protocolo = list(inspect.signature(getattr(Repositorio, nombre)).parameters)
        de_la_clase = list(inspect.signature(getattr(RepositorioPostgres, nombre)).parameters)
        if del_protocolo != de_la_clase:
            discrepan[nombre] = (del_protocolo, de_la_clase)
    assert not discrepan, f"firmas que no coinciden: {discrepan}"


# --------------------------------------------------------------------------- #
# CA-2 - no se abre ninguna conexion real                                      #
# --------------------------------------------------------------------------- #


def test_construir_con_un_doble_no_llama_a_conectar(monkeypatch):
    """
    La prueba de que esto corre sin base no es que pase: es que `conectar`
    explote si alguien lo llama y aun asi pase.
    """

    def prohibido(*_a, **_k):
        raise AssertionError("se intento abrir una conexion real")

    monkeypatch.setattr(modulo, "conectar", prohibido)
    repositorio = RepositorioPostgres(conexion=ConexionFalsa())
    repositorio.listar_distritos()


# --------------------------------------------------------------------------- #
# CA-3 - los pendientes fallan nombrando lo que falta                          #
# --------------------------------------------------------------------------- #

LLAMADAS_PENDIENTES = {
    "guardar_indices": lambda r: r.guardar_indices([]),
    "obtener_indices": lambda r: r.obtener_indices("50801", date(2024, 1, 1), date(2024, 1, 2)),
    "listar_eventos": lambda r: r.listar_eventos(),
    "guardar_reporte_calidad": lambda r: r.guardar_reporte_calidad(None),
    "listar_reportes_calidad": lambda r: r.listar_reportes_calidad(),
    "guardar_metricas": lambda r: r.guardar_metricas(None),
    "listar_metricas": lambda r: r.listar_metricas(),
}


def test_la_tabla_de_pendientes_cubre_exactamente_los_metodos_que_fallan():
    """Sin numero escrito a mano: decia `== 10` y H3.6 implemento tres (D-39).

    Lo que se exige es que cada metodo declarado pendiente tenga su llamada de
    prueba y que ninguna llamada apunte a un metodo que ya existe. El numero
    sale de `PENDIENTES`, que es la fuente.
    """
    assert set(LLAMADAS_PENDIENTES) == set(PENDIENTES)
    assert PENDIENTES, "si no queda ningun pendiente, esta prueba y sus vecinas se retiran"


@pytest.mark.parametrize("metodo", sorted(LLAMADAS_PENDIENTES))
def test_un_pendiente_falla_en_vez_de_devolver_vacio(metodo):
    """
    Devolver `[]` diria «no hay ninguno», que es legitimo y falso: lo cierto es
    que la tabla no existe. La distincion es la de D-22 entre un cero y un hueco.
    """
    repositorio = RepositorioPostgres(conexion=ConexionFalsa())
    tabla, historia = PENDIENTES[metodo]

    with pytest.raises(TablaPendiente) as capturado:
        LLAMADAS_PENDIENTES[metodo](repositorio)

    mensaje = str(capturado.value)
    assert tabla in mensaje, f"el mensaje no nombra la tabla `{tabla}`"
    assert historia in mensaje, f"el mensaje no nombra la historia {historia}"


def test_los_pendientes_los_atrapa_un_except_generico():
    """Hereda de NotImplementedError para que no haga falta conocer el modulo."""
    repositorio = RepositorioPostgres(conexion=ConexionFalsa())
    with pytest.raises(NotImplementedError):
        repositorio.listar_metricas()


# --------------------------------------------------------------------------- #
# CA-4 - cada escritura ocurre dentro de su propia transaccion                 #
# --------------------------------------------------------------------------- #


def test_guardar_mediciones_escribe_dentro_de_la_transaccion():
    conexion = ConexionFalsa()
    repositorio = RepositorioPostgres(conexion=conexion)

    guardadas = repositorio.guardar_mediciones([medicion(1), medicion(2)])

    assert guardadas == 2
    assert conexion.eventos() == [
        "abre_transaccion",
        "abre_cursor",
        "executemany",
        "cierra_cursor",
        "cierra_transaccion",
    ]


def test_guardar_focos_escribe_dentro_de_la_transaccion():
    conexion = ConexionFalsa()
    repositorio = RepositorioPostgres(conexion=conexion)

    guardados = repositorio.guardar_focos([foco(1, "Terra"), foco(2, "N")])

    assert guardados == 2
    assert conexion.eventos() == [
        "abre_transaccion",
        "abre_cursor",
        "executemany",
        "cierra_cursor",
        "cierra_transaccion",
    ]


def test_dos_guardados_abren_dos_transacciones():
    """El defecto de H1.1 fue exactamente esto: una sola transaccion para todo."""
    conexion = ConexionFalsa()
    repositorio = RepositorioPostgres(conexion=conexion)

    repositorio.guardar_mediciones([medicion(1)])
    repositorio.guardar_mediciones([medicion(2)])

    assert conexion.eventos().count("abre_transaccion") == 2


def test_guardar_una_lista_vacia_no_abre_ninguna_transaccion():
    conexion = ConexionFalsa()
    repositorio = RepositorioPostgres(conexion=conexion)

    assert repositorio.guardar_mediciones([]) == 0
    assert repositorio.guardar_focos([]) == 0
    assert conexion.bitacora == []


def test_las_lecturas_no_abren_transaccion():
    """
    Con `autocommit=True` una lectura no necesita envoltorio, y ponerselo seria
    la trampa de psycopg3: la transaccion siguiente se volveria un punto de
    retorno dentro de ella.
    """
    conexion = ConexionFalsa(resultados=[[FILA_DISTRITO]])
    repositorio = RepositorioPostgres(conexion=conexion)

    repositorio.listar_distritos()

    assert "abre_transaccion" not in conexion.eventos()


def test_el_satelite_decide_producto_y_banda():
    """Terra y Aqua son MODIS; los que empiezan con N son VIIRS. Ver H1.2."""
    conexion = ConexionFalsa()
    repositorio = RepositorioPostgres(conexion=conexion)

    repositorio.guardar_focos([foco(1, "Terra"), foco(2, "N")])

    (_, _, parametros) = conexion.sentencias()[0]
    assert parametros[0]["producto"] == "modis"
    assert parametros[0]["banda_origen"] == "modis_21_22"
    assert parametros[1]["producto"] == "viirs-snpp"
    assert parametros[1]["banda_origen"] == "viirs_i4"
    assert parametros[1]["confianza_bruta"] is None, "VIIRS no tiene confianza numerica comparable"


# --------------------------------------------------------------------------- #
# CA-6 - los dias sin dato vuelven como nulos                                  #
# --------------------------------------------------------------------------- #


def test_los_dias_sin_medicion_vuelven_con_nulos_y_no_ausentes():
    """
    Omitir el dia haria indistinguible un hueco de un dia que no existe. El
    contrato exige que el consumidor pueda ver los huecos.
    """
    filas = [
        (date(2024, 6, 1), 30.0, 20.0, 25.0, 0.0, 80.0, 2.0, 18.0, False, None),
        (date(2024, 6, 2), None, None, None, None, None, None, None, False, None),
        (date(2024, 6, 3), 31.0, 21.0, 26.0, 12.5, 82.0, 2.5, 19.0, False, None),
    ]
    conexion = ConexionFalsa(resultados=[filas])
    repositorio = RepositorioPostgres(conexion=conexion)

    salida = repositorio.obtener_mediciones("50801", date(2024, 6, 1), date(2024, 6, 3))

    assert len(salida) == 3, "el dia sin dato tiene que venir igual"
    assert [m.fecha.day for m in salida] == [1, 2, 3]
    assert salida[1].temp_max_c is None
    assert salida[1].precipitacion_mm is None
    assert salida[0].precipitacion_mm == 0.0, "un cero es una medicion, no un hueco"
    assert salida[1].metodo_imputacion is MetodoImputacion.SIN_IMPUTAR


def test_el_sql_de_mediciones_genera_el_rango_y_une_por_la_izquierda():
    """
    COMPROBACION DE TEXTO, no de comportamiento.

    Sin base de datos no se puede ejecutar el SQL, asi que lo unico honesto que
    se puede afirmar aca es que la sentencia contiene las dos piezas de las que
    depende el criterio. Que hagan lo que dicen lo comprueba el verificador de
    H1.1 contra la base real.
    """
    sql = SQL_MEDICIONES.lower()
    assert "generate_series" in sql
    assert "left join" in sql


# --------------------------------------------------------------------------- #
# Lecturas: mapeo y ausencia                                                   #
# --------------------------------------------------------------------------- #


def test_listar_distritos_mapea_la_geometria_a_diccionario():
    conexion = ConexionFalsa(resultados=[[FILA_DISTRITO]])
    repositorio = RepositorioPostgres(conexion=conexion)

    (distrito,) = repositorio.listar_distritos()

    assert distrito.codigo == "50801"
    assert distrito.geometria["type"] == "Polygon", "ST_AsGeoJSON devuelve texto, no un dict"
    assert distrito.poblacion is None, "sin dato censal es None, no cero"


def test_obtener_distrito_devuelve_none_si_no_hay_fila():
    """La ausencia es un caso valido del contrato, no un error."""
    conexion = ConexionFalsa(resultados=[[]])
    repositorio = RepositorioPostgres(conexion=conexion)

    assert repositorio.obtener_distrito("00000") is None


def test_contar_focos_devuelve_un_entero():
    conexion = ConexionFalsa(resultados=[[(7,)]])
    repositorio = RepositorioPostgres(conexion=conexion)

    assert repositorio.contar_focos("50801", date(2024, 1, 1), date(2024, 12, 31)) == 7


def test_cerrar_cierra_la_conexion():
    conexion = ConexionFalsa()
    RepositorioPostgres(conexion=conexion).cerrar()
    assert conexion.cerrada is True
