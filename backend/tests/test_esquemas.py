"""
Pruebas de validacion de `contratos/esquemas.py`. Historia H10.2.

Cubre la seccion 3.5 de `docs/investigacion/plan-pruebas.md`, los cuatro casos.

QUE PROTEGEN ESTAS CUATRO
-------------------------

No hay Protocol aqui: la validacion la hace Pydantic con sus restricciones de
campo. Estas pruebas comprueban que **las restricciones existen y muerden**.

Una restriccion declarada y no probada es una suposicion. Si alguien quitara el
`ge=0` de `precipitacion_mm` al refactorizar, ninguna prueba del proyecto
fallaria y el error aparecerian meses despues como un percentil negativo en un
reporte.
"""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from contratos.enums import TipoEvento
from contratos.esquemas import FocoCalor, MedicionDiaria, PuntoSerie, Riesgo, SerieTemporal

# --------------------------------------------------------------------------- #
# 3.5 Rangos que no se pueden violar                                            #
# --------------------------------------------------------------------------- #


def test_medicion_precipitacion_negativa_rechazada():
    """
    `precipitacion_mm` no admite negativos: la restriccion es `ge=0`.

    No es un capricho de tipo. La lluvia negativa es el sintoma que aparece si
    alguien filtra la precipitacion con un Savitzky-Golay, que es justo lo que
    **D-17** prohibe: el filtro produce valores por debajo de cero y esos
    rompen el ajuste gamma del SPI, definido sobre valores no negativos.
    """
    with pytest.raises(ValidationError):
        MedicionDiaria(
            codigo_distrito="50801",
            fecha=date(2024, 1, 1),
            precipitacion_mm=-0.1,
        )


def test_medicion_precipitacion_cero_es_valida():
    """
    Un cero **no** es lo mismo que un negativo ni que un hueco. En Tilaran hay
    meses enteros de 0,0 mm en estacion seca, y son dato, no ausencia.
    """
    medicion = MedicionDiaria(
        codigo_distrito="50801",
        fecha=date(2024, 2, 1),
        precipitacion_mm=0.0,
    )

    assert medicion.precipitacion_mm == 0.0


def test_riesgo_probabilidad_fuera_de_rango_rechazada():
    """`probabilidad` se restringe a [0, 1] por los dos lados."""
    for valor in (-0.01, 1.01):
        with pytest.raises(ValidationError):
            Riesgo(
                codigo_distrito="50801",
                fecha=date(2024, 1, 1),
                tipo_evento=TipoEvento.SEQUIA,
                probabilidad=valor,
            )


def test_riesgo_sin_probabilidad_es_valido():
    """
    `probabilidad` es None mientras no exista un modelo que la calcule.

    **None no es cero.** Un riesgo sin estimacion y un riesgo estimado en 0,0
    dicen cosas opuestas: el primero es "no sabemos", el segundo es "sabemos que
    es bajisimo".
    """
    riesgo = Riesgo(
        codigo_distrito="50801",
        fecha=date(2024, 1, 1),
        tipo_evento=TipoEvento.SEQUIA,
    )

    assert riesgo.probabilidad is None
    assert riesgo.nivel is None


def test_foco_calor_confianza_fuera_de_rango_rechazada():
    """`confianza` se restringe a [0, 100]: es un porcentaje."""
    for valor in (-1, 101):
        with pytest.raises(ValidationError):
            FocoCalor(
                fecha=date(2024, 3, 1),
                latitud=10.47,
                longitud=-84.97,
                confianza=valor,
            )


def test_foco_calor_coordenadas_fuera_del_planeta_rechazadas():
    """
    No esta en el plan y cuesta una linea. Latitud y longitud tienen `ge`/`le`
    declarados y nadie los probaba.
    """
    with pytest.raises(ValidationError):
        FocoCalor(fecha=date(2024, 3, 1), latitud=91.0, longitud=-84.97)

    with pytest.raises(ValidationError):
        FocoCalor(fecha=date(2024, 3, 1), latitud=10.47, longitud=181.0)


# --------------------------------------------------------------------------- #
# 3.5 Los huecos se conservan                                                   #
# --------------------------------------------------------------------------- #


def test_serie_temporal_conserva_huecos_como_none():
    """
    Prioridad 1. `SerieTemporal.puntos` **no omite las fechas con valor en
    None.**

    Es la misma invariante que atraviesa todo el proyecto y que cada capa tiene
    que respetar por separado: el extractor no omite el dia, el repositorio
    devuelve la fila, el esquema conserva el punto. Si cualquiera de las tres la
    rompe, el hueco desaparece y la serie parece completa.
    """
    serie = SerieTemporal(
        codigo_distrito="50801",
        variable="precipitacion_mm",
        unidad="mm",
        puntos=[
            PuntoSerie(fecha=date(2024, 1, 1), valor=12.4),
            PuntoSerie(fecha=date(2024, 1, 2), valor=None),
            PuntoSerie(fecha=date(2024, 1, 3), valor=0.0),
        ],
    )

    assert len(serie.puntos) == 3
    assert serie.puntos[1].valor is None
    assert [p.fecha.day for p in serie.puntos] == [1, 2, 3]


def test_un_punto_sin_valor_es_valido():
    """El valor por defecto de `PuntoSerie.valor` es None y se acepta."""
    assert PuntoSerie(fecha=date(2024, 1, 1)).valor is None


def test_el_cero_y_el_hueco_no_se_confunden_en_la_serie():
    """
    Congela la distincion, que es la que mas se pierde al refactorizar: en la
    misma serie, un punto en 0,0 y uno en None tienen que seguir siendo
    distinguibles despues de construir el modelo.
    """
    serie = SerieTemporal(
        codigo_distrito="50801",
        variable="precipitacion_mm",
        unidad="mm",
        puntos=[
            PuntoSerie(fecha=date(2024, 1, 1), valor=0.0),
            PuntoSerie(fecha=date(2024, 1, 2), valor=None),
        ],
    )

    con_dato = [p for p in serie.puntos if p.valor is not None]
    sin_dato = [p for p in serie.puntos if p.valor is None]

    assert len(con_dato) == 1
    assert len(sin_dato) == 1
    assert con_dato[0].valor == 0.0
