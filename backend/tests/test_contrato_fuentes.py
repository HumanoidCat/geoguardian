"""
Pruebas de los contratos `ExtractorClima` y `ExtractorFocosCalor` contra sus
simulados. Historia H10.2.

Cubre la seccion 3.2 de `docs/investigacion/plan-pruebas.md`, los cinco casos.

Como en los otros archivos de contrato: verifican que el simulado cumple lo
prometido, no que NASA POWER o FIRMS respondan.
"""

from __future__ import annotations

from datetime import date, timedelta

from contratos.fuentes import ExtractorClima, ExtractorFocosCalor
from contratos.simulados.datos import ExtractorClimaSimulado, ExtractorFocosSimulado


def test_los_simulados_cumplen_sus_protocolos():
    assert isinstance(ExtractorClimaSimulado(), ExtractorClima)
    assert isinstance(ExtractorFocosSimulado(), ExtractorFocosCalor)


def test_los_extractores_se_identifican_como_simulados():
    """
    El campo `nombre` viaja a la procedencia de cada fila. Si un simulado se
    identificara como la fuente real, un volcado de prueba quedaria indistinguible
    de uno de produccion.
    """
    assert "SIMULADO" in ExtractorClimaSimulado().nombre
    assert "SIMULADO" in ExtractorFocosSimulado().nombre


# --------------------------------------------------------------------------- #
# 3.2 ExtractorClima                                                            #
# --------------------------------------------------------------------------- #


def test_extractor_clima_disponible_antes_de_extraer():
    """
    Se puede verificar conectividad **sin descargar datos**, para fallar
    temprano en vez de a mitad de una ingesta larga.

    En la carga real de H1.1 esto importa de verdad: son 1180 segundos y ocho
    distritos. Descubrir en el septimo que la fuente no responde cuesta veinte
    minutos.
    """
    assert ExtractorClimaSimulado().disponible() is True


def test_extractor_clima_extraer_es_idempotente():
    """
    Prioridad 1. Dos llamadas con los mismos argumentos producen el mismo
    resultado.

    **Aqui si se puede probar de verdad**, a diferencia de
    `guardar_mediciones` en el repositorio: extraer no tiene efecto sobre
    ningun estado, asi que la igualdad de las dos salidas es la propiedad
    completa y no una aproximacion.
    """
    extractor = ExtractorClimaSimulado()
    argumentos = ("50801", date(2024, 1, 1), date(2024, 2, 15))

    assert extractor.extraer(*argumentos) == extractor.extraer(*argumentos)


def test_extractor_clima_es_idempotente_entre_instancias():
    """
    Dos extractores distintos devuelven lo mismo. Si el determinismo dependiera
    de la instancia, la prueba anterior pasaria y la reproducibilidad entre
    ejecuciones seguiria rota.
    """
    argumentos = ("50803", date(2024, 6, 1), date(2024, 6, 30))

    assert ExtractorClimaSimulado().extraer(*argumentos) == ExtractorClimaSimulado().extraer(
        *argumentos
    )


def test_extractor_clima_no_omite_dias_sin_dato():
    """
    Prioridad 1. Un dia sin dato se devuelve con campos en None; **no se omite
    la fecha.**

    Omitirlos haria indistinguible un hueco de un dia que no existe, y quien
    calcule sobre ventanas moviles contaria dias que nunca vinieron.
    """
    desde, hasta = date(2024, 1, 1), date(2024, 3, 31)
    esperados = (hasta - desde).days + 1

    filas = ExtractorClimaSimulado().extraer("50801", desde, hasta)

    assert len(filas) == esperados
    assert [f.fecha for f in filas] == [desde + timedelta(days=i) for i in range(esperados)]
    assert any(f.precipitacion_mm is None for f in filas), "el simulado deberia traer huecos"


# --------------------------------------------------------------------------- #
# 3.2 ExtractorFocosCalor                                                       #
# --------------------------------------------------------------------------- #


def test_extractor_focos_extrae_dentro_del_rango():
    """Los focos devueltos caen dentro de `desde` y `hasta`, sin excepciones."""
    desde, hasta = date(2024, 3, 1), date(2024, 3, 31)

    focos = ExtractorFocosSimulado().extraer(desde, hasta)

    assert focos
    for foco in focos:
        assert desde <= foco.fecha <= hasta


def test_extractor_focos_no_asigna_distrito():
    """
    Prioridad 2, y es una regla de **diseno**, no de datos.

    El extractor no hace analisis espacial: `codigo_distrito` sale en None. El
    filtrado por distrito ocurre despues, en el repositorio, que es la capa que
    conoce las geometrias.

    Si un extractor empezara a asignar distrito, habria dos lugares del sistema
    decidiendo la misma cosa con criterios que nadie garantiza iguales.
    """
    focos = ExtractorFocosSimulado().extraer(date(2024, 3, 1), date(2024, 3, 31))

    assert focos
    assert all(f.codigo_distrito is None for f in focos)


def test_extractor_focos_es_idempotente():
    """
    No esta en el plan y se agrega por lo que dice el docstring del simulado:
    esta clase **era el quinto sitio que sorteaba contra un generador con
    estado**, y SC-04 no lo cubrio porque la revision miro solo dentro de
    `RepositorioSimulado`. Lo encontro Cesar.

    Importa para H1.2, que implementa el extractor de verdad: si el doble contra
    el que se compara no es reproducible, la comparacion no prueba nada.
    """
    extractor = ExtractorFocosSimulado()
    argumentos = (date(2024, 5, 1), date(2024, 5, 31))

    primera = extractor.extraer(*argumentos)
    segunda = extractor.extraer(*argumentos)

    assert primera == segunda


def test_extractor_focos_disponible_antes_de_extraer():
    assert ExtractorFocosSimulado().disponible() is True
