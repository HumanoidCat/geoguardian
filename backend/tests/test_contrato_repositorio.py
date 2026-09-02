"""
Pruebas del contrato `Repositorio` contra su simulado. Historia H10.2.

Cubre la seccion 3.1 de `docs/investigacion/plan-pruebas.md`.

QUE VERIFICAN Y QUE NO
----------------------

Estas pruebas verifican que **`RepositorioSimulado` cumple el contrato**, no que
la implementacion de PostgreSQL funcione. Sirven para detectar dos cosas: que un
simulado se desvie del contrato, y que el contrato cambie sin que el simulado se
entere. Es exactamente para lo que el proyecto tiene simulados.

**No sustituyen a `backend/api/test_repositorio_postgres.py`**, que prueba la
implementacion real y tiene otro dueno.

CUATRO CASOS DEL PLAN QUE NO SE PUEDEN ESCRIBIR AQUI
---------------------------------------------------

El plan asume que los once casos de la seccion 3.1 se prueban contra el
simulado. Al escribirlos aparecio que **cuatro no**, porque el simulado no
implementa la invariante que esos casos protegen:

1. `test_guardar_mediciones_es_idempotente`. El simulado no guarda nada:
   `guardar_mediciones` devuelve `len(mediciones)` y descarta la lista. No hay
   estado sobre el que la segunda escritura pueda ser idempotente.
2. `test_guardar_mediciones_revierte_en_fallo_parcial`. Sin almacenamiento no
   hay carga parcial que revertir, y el simulado no tiene modo de fallo.
3. `test_guardar_focos_asigna_distrito_por_interseccion`. El simulado no hace
   analisis espacial; devuelve el conteo y ya.
4. `test_obtener_riesgo_sin_estimacion_devuelve_none`. El simulado **siempre**
   devuelve un `Riesgo`: no tiene forma de representar la ausencia de
   estimacion, que es justo lo que el caso quiere proteger.

**Los cuatro son de prioridad 1 o 2 y hoy no los cubre nadie.** Se reviso
`test_repositorio_postgres.py`: prueba el comportamiento transaccional
—que la escritura ocurra dentro de una transaccion, que dos guardados abran dos—
pero no la idempotencia, ni la reversion parcial, ni la asignacion espacial. Y
su propia prueba `test_la_tabla_de_pendientes_cubre_exactamente_diez_metodos`
declara que diez de los dieciseis metodos siguen sin implementar.

Queda anotado en la evidencia de H10.2. Cerrarlo requiere o fortalecer el
simulado, que es `contratos/` y no es mi carpeta, o esperar a que la
implementacion real cubra esos metodos.
"""

from __future__ import annotations

from datetime import date, timedelta

from contratos.enums import TipoEvento
from contratos.repositorio import Repositorio
from contratos.simulados.datos import RepositorioSimulado

# Los ocho distritos de Tilaran, canton 08 de Guanacaste. La lista esta aqui
# escrita a mano y no importada del simulado a proposito: si se importara, la
# prueba compararia el simulado consigo mismo y no detectaria nada.
CODIGOS_OFICIALES = {
    "50801",
    "50802",
    "50803",
    "50804",
    "50805",
    "50806",
    "50807",
    "50808",
}


def _repo() -> RepositorioSimulado:
    return RepositorioSimulado()


# --------------------------------------------------------------------------- #
# Conformidad con el protocolo                                                  #
# --------------------------------------------------------------------------- #


def test_el_simulado_cumple_el_protocolo():
    """
    `Repositorio` es `runtime_checkable`, asi que la conformidad se puede
    comprobar y no solo suponer. Es la prueba mas barata del archivo y la que
    detecta que alguien agregue un metodo al contrato sin tocar el simulado.
    """
    assert isinstance(_repo(), Repositorio)


# --------------------------------------------------------------------------- #
# 3.1 Territorio                                                                #
# --------------------------------------------------------------------------- #


def test_listar_distritos_devuelve_ocho():
    """El vocabulario territorial esta cerrado a los ocho distritos."""
    assert len(_repo().listar_distritos()) == 8


def test_codigos_distrito_son_los_oficiales_de_tilaran():
    """
    Prioridad 1, y viene de la incidencia **I-04**.

    Los ocho codigos son 50801 a 50808, sin repetidos. Un codigo con forma
    valida pero de otro canton —50501 a 50508 es Carrillo— es un dato falso que
    **ninguna validacion de tipo detecta**: tiene cinco digitos, es numerico y
    entra en cualquier esquema. Esto se descubrio con datos reales de
    DesInventar, no en una prueba.
    """
    codigos = [d.codigo for d in _repo().listar_distritos()]

    assert len(codigos) == len(set(codigos)), "hay codigos repetidos"
    assert set(codigos) == CODIGOS_OFICIALES


def test_obtener_distrito_codigo_inexistente_devuelve_none():
    """
    La ausencia es un caso valido y no una excepcion. Se prueba con un codigo de
    Carrillo, que es el error realista, y no con una cadena absurda.
    """
    assert _repo().obtener_distrito("50501") is None


def test_obtener_distrito_devuelve_el_que_se_pidio():
    for codigo in sorted(CODIGOS_OFICIALES):
        distrito = _repo().obtener_distrito(codigo)
        assert distrito is not None
        assert distrito.codigo == codigo


# --------------------------------------------------------------------------- #
# 3.1 Mediciones                                                                #
# --------------------------------------------------------------------------- #


def test_obtener_mediciones_incluye_dias_sin_dato():
    """
    Prioridad 1. Una fila por dia del rango, con campos en None en los huecos.

    **El consumidor necesita ver los huecos.** Si el repositorio omitiera las
    fechas sin dato, quien calcula una ventana movil contaria dias que no
    existen: la serie parece completa y el hueco esta en las filas que no vinieron.
    Es el mismo defecto que H1.5 congelo en
    `test_el_total_esperado_son_dias_de_calendario_no_filas`.
    """
    desde, hasta = date(2024, 1, 1), date(2024, 3, 31)
    esperados = (hasta - desde).days + 1

    filas = _repo().obtener_mediciones("50801", desde, hasta)

    assert len(filas) == esperados
    assert [f.fecha for f in filas] == [desde + timedelta(days=i) for i in range(esperados)]

    # El simulado siembra huecos, uno de cada veinte. Sobre 91 dias tiene que
    # haber al menos uno, y su fecha tiene que estar presente igual.
    huecos = [f for f in filas if f.precipitacion_mm is None]
    assert huecos, "el simulado deberia traer huecos en un rango de 91 dias"


def test_un_hueco_deja_todas_las_variables_en_none():
    """Un dia sin dato no trae media variable: no existe la fila a medias."""
    filas = _repo().obtener_mediciones("50801", date(2024, 1, 1), date(2024, 6, 30))
    huecos = [f for f in filas if f.precipitacion_mm is None]

    assert huecos
    for fila in huecos:
        assert fila.temp_max_c is None
        assert fila.temp_min_c is None
        assert fila.humedad_relativa_pct is None
        assert fila.viento_ms is None
        assert fila.radiacion_mj_m2 is None


def test_la_serie_no_cambia_si_se_pide_en_tandas():
    """
    **Congela SC-04.** Una version anterior sorteaba cada dia desde su posicion
    en el rango pedido, asi que el mismo dia tenia valores distintos segun donde
    cayera en la consulta. Le pegaba a cualquier calculo sobre ventanas moviles.

    Pedir del 1 al 5 y del 3 al 7 tiene que dar lo mismo para el 3, 4 y 5.
    """
    repo = _repo()
    primera = repo.obtener_mediciones("50803", date(2024, 5, 1), date(2024, 5, 5))
    segunda = repo.obtener_mediciones("50803", date(2024, 5, 3), date(2024, 5, 7))

    solape_primera = {f.fecha: f.precipitacion_mm for f in primera if f.fecha >= date(2024, 5, 3)}
    solape_segunda = {f.fecha: f.precipitacion_mm for f in segunda if f.fecha <= date(2024, 5, 5)}

    assert solape_primera == solape_segunda


def test_cada_distrito_tiene_su_propia_serie():
    """
    Dos distritos no pueden devolver la misma serie. Si la devolvieran, el
    simulado estaria reproduciendo la limitacion de NASA POWER que H1.5 midio en
    los datos reales, y las pruebas que dependan de variacion espacial pasarian
    sin medir nada.
    """
    desde, hasta = date(2024, 1, 1), date(2024, 2, 29)
    una = [f.precipitacion_mm for f in _repo().obtener_mediciones("50801", desde, hasta)]
    otra = [f.precipitacion_mm for f in _repo().obtener_mediciones("50807", desde, hasta)]

    assert una != otra


def test_guardar_mediciones_devuelve_el_numero_de_filas():
    """
    Lo unico que el simulado puede demostrar de `guardar_mediciones`.

    **No prueba idempotencia**, que es lo que pedia el plan: el simulado no
    guarda nada, asi que no hay estado sobre el que una segunda escritura pueda
    ser idempotente. Ver la nota del modulo.
    """
    filas = _repo().obtener_mediciones("50802", date(2024, 1, 1), date(2024, 1, 10))

    assert _repo().guardar_mediciones(filas) == len(filas)
    assert _repo().guardar_mediciones([]) == 0


# --------------------------------------------------------------------------- #
# 3.1 Focos de calor                                                            #
# --------------------------------------------------------------------------- #


def test_contar_focos_ventana_sin_focos_devuelve_cero():
    """
    Prioridad 2. Una ventana vacia no lanza error ni devuelve None.

    Se construye con `desde` posterior a `hasta`, que es el unico caso en que el
    simulado no cuenta ningun dia. **Un cero es una respuesta**, no la ausencia
    de una: FIRMS informa que no hubo detecciones, que es distinto de no tener
    dato. Es la distincion de D-22.
    """
    conteo = _repo().contar_focos("50804", date(2024, 3, 10), date(2024, 3, 1))

    assert conteo == 0
    assert isinstance(conteo, int)
    assert conteo is not None


def test_contar_focos_es_aditivo_entre_ventanas_contiguas():
    """
    Contar dos ventanas contiguas da lo mismo que contar la ventana completa,
    que es como se comporta una consulta real sobre filas.

    Importa para H3.0: el etiquetado de incendio usa ventanas de siete dias, y
    con un sorteo por rango dos ventanas solapadas se contradirian.
    """
    repo = _repo()
    completa = repo.contar_focos("50805", date(2024, 4, 1), date(2024, 4, 14))
    primera = repo.contar_focos("50805", date(2024, 4, 1), date(2024, 4, 7))
    segunda = repo.contar_focos("50805", date(2024, 4, 8), date(2024, 4, 14))

    assert completa == primera + segunda


# --------------------------------------------------------------------------- #
# 3.1 Riesgo                                                                    #
# --------------------------------------------------------------------------- #


def test_obtener_riesgos_por_fecha_todos_los_distritos():
    """Alimenta la coropleta del visor: un riesgo por distrito, sin faltar ninguno."""
    riesgos = _repo().obtener_riesgos_por_fecha(date(2024, 9, 15), TipoEvento.LLUVIA_INTENSA)

    assert len(riesgos) == 8
    assert {r.codigo_distrito for r in riesgos} == CODIGOS_OFICIALES


def test_el_mismo_riesgo_pedido_dos_veces_es_el_mismo():
    """
    **Congela I-08 y SC-03.** El simulado sorteaba contra un generador con
    estado, asi que tres peticiones identicas a `GET /riesgos` daban tres
    respuestas distintas. Se midio el 20 de agosto.

    La razon por la que esto importa no es HTTP —un GET puede devolver algo
    distinto cada vez y seguir siendo idempotente— sino **sustituibilidad**: el
    repositorio real lee filas guardadas y es determinista. Un doble que no
    cumple la propiedad por la que se lo pone en lugar del original no sirve.
    """
    repo = _repo()
    argumentos = ("50806", date(2024, 10, 5), TipoEvento.SEQUIA)

    primero = repo.obtener_riesgo(*argumentos)
    segundo = repo.obtener_riesgo(*argumentos)

    assert primero is not None and segundo is not None
    assert primero.probabilidad == segundo.probabilidad
    assert primero.nivel == segundo.nivel


def test_el_riesgo_cambia_con_el_tipo_de_evento():
    """Sequia e incendio del mismo dia y distrito no pueden ser el mismo numero."""
    repo = _repo()
    sequia = repo.obtener_riesgo("50801", date(2024, 3, 1), TipoEvento.SEQUIA)
    incendio = repo.obtener_riesgo("50801", date(2024, 3, 1), TipoEvento.INCENDIO)

    assert sequia is not None and incendio is not None
    assert sequia.probabilidad != incendio.probabilidad


# --------------------------------------------------------------------------- #
# 3.1 Eventos, calidad y modelos                                                #
# --------------------------------------------------------------------------- #


def test_listar_metricas_sin_modelos_entrenados_devuelve_vacio():
    """
    Prioridad 1. No hay metricas inventadas antes de entrenar.

    Devolver numeros aqui seria inventar resultados de un modelo que nadie
    entreno, y esos numeros terminarian en una tabla comparativa.
    """
    assert _repo().listar_metricas() == []


def test_listar_reportes_calidad_sin_reportes_devuelve_vacio():
    assert _repo().listar_reportes_calidad() == []


def test_listar_eventos_filtra_por_tipo():
    repo = _repo()
    todos = repo.listar_eventos()
    sequias = repo.listar_eventos(TipoEvento.SEQUIA)

    assert len(todos) >= len(sequias)
    assert all(e.tipo_evento == TipoEvento.SEQUIA for e in sequias)


def test_los_eventos_del_simulado_se_declaran_como_simulados():
    """
    Cada evento del simulado dice en su fuente que hay que reemplazarlo por el
    catalogo real de H4.3. Si alguien los usara creyendo que son reales, el
    contraste de H4.4 se haria contra tres eventos inventados.
    """
    for evento in _repo().listar_eventos():
        assert "SIMULADO" in evento.fuente
