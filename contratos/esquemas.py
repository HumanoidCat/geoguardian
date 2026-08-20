"""
Esquemas de la API. Es el contrato mas importante del proyecto: lo consume el
frontend y define la forma de todo lo que cruza la frontera del sistema.

Regla que atraviesa todo este archivo: un dato que no se pudo obtener o calcular
se representa como None, nunca como 0 ni como un valor plausible. Cero milimetros
de lluvia es una medicion; ausencia de dato no lo es. Confundirlos arruina el
modelo y nadie lo detecta hasta que es tarde.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .enums import Algoritmo, MetodoImputacion, ModoOperacion, NivelRiesgo, TipoEvento


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True, frozen=True)


# --------------------------------------------------------------------------- #
# Territorio                                                                    #
# --------------------------------------------------------------------------- #


class Distrito(_Base):
    """
    Distrito del canton de Tilaran.

    Se identifica por `codigo`, no por nombre: el nombre puede escribirse de
    varias formas y no sirve como clave.
    """

    codigo: str = Field(description="Codigo oficial del distrito", examples=["50801"])
    nombre: str
    area_km2: float = Field(gt=0)
    poblacion: int | None = Field(default=None, ge=0, description="None si no hay dato censal")
    geometria: dict[str, Any] = Field(
        description="Poligono GeoJSON en EPSG:4326, listo para Leaflet"
    )


# --------------------------------------------------------------------------- #
# Mediciones                                                                    #
# --------------------------------------------------------------------------- #


class MedicionDiaria(_Base):
    """
    Observacion climatica de un dia. Todas las variables son opcionales a
    proposito: las series reales tienen huecos y hay que poder representarlos.
    """

    codigo_distrito: str
    fecha: date
    temp_max_c: float | None = None
    temp_min_c: float | None = None
    temp_media_c: float | None = None
    precipitacion_mm: float | None = Field(default=None, ge=0)
    humedad_relativa_pct: float | None = Field(default=None, ge=0, le=100)
    viento_ms: float | None = Field(default=None, ge=0)
    radiacion_mj_m2: float | None = Field(default=None, ge=0)
    imputado: bool = Field(default=False, description="True si algun valor fue imputado")
    metodo_imputacion: MetodoImputacion = MetodoImputacion.SIN_IMPUTAR


class IndiceDerivado(_Base):
    """Indices calculados a partir de las mediciones. None mientras no se calculen."""

    codigo_distrito: str
    fecha: date
    spi_1m: float | None = None
    spi_3m: float | None = None
    anomalia_temp_c: float | None = None
    dias_sin_lluvia: int | None = Field(default=None, ge=0)


class FocoCalor(_Base):
    """Deteccion de foco de calor. Etiqueta de la variable objetivo de incendio."""

    fecha: date
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    confianza: int | None = Field(default=None, ge=0, le=100)
    brillo_k: float | None = None
    satelite: str | None = None
    codigo_distrito: str | None = Field(
        default=None, description="None si cae fuera de todo distrito"
    )


# --------------------------------------------------------------------------- #
# Riesgo                                                                        #
# --------------------------------------------------------------------------- #


class ContribucionVariable(_Base):
    """Aporte de una variable a una prediccion concreta, segun SHAP."""

    variable: str
    aporte: float = Field(description="Valor SHAP: positivo empuja hacia mayor riesgo")


class Riesgo(_Base):
    """
    Estimacion de riesgo para un distrito, una fecha y un tipo de evento.

    `probabilidad` y `explicacion` son None mientras no exista un modelo
    entrenado. Un riesgo sin modelo detras no se rellena con un valor plausible:
    se devuelve nulo y el frontend lo muestra como no disponible.

    **`probabilidad` es P(nivel = alto)**, la probabilidad que el modelo asigna a
    la clase mas severa del evento, con independencia de cual sea el `nivel`
    devuelto. Decision **D-21**.

    NO es la confianza del modelo en la clase que asigno. Un distrito con `nivel`
    bajo y `probabilidad` 0,05 esta diciendo que el modelo lo ve tranquilo, no que
    este poco seguro.

    El motivo es el orden: con la confianza, un distrito tranquilo con el modelo
    seguro puntuaria mas alto que uno en riesgo con el modelo dudando, y el mapa
    de calor pintaria mas intenso al equivocado. Con P(nivel = alto) el campo es
    monotono en el riesgo, comparable entre distritos y entre eventos, y sirve
    como umbral continuo.
    """

    codigo_distrito: str
    fecha: date
    tipo_evento: TipoEvento
    nivel: NivelRiesgo | None = None
    probabilidad: float | None = Field(default=None, ge=0, le=1)
    algoritmo: Algoritmo | None = None
    version_modelo: str | None = None
    explicacion: list[ContribucionVariable] | None = None


class EventoHistorico(_Base):
    """Evento registrado. Sirve para contrastar el modelo contra la realidad."""

    codigo_distrito: str
    tipo_evento: TipoEvento
    fecha_inicio: date
    fecha_fin: date | None = Field(default=None, description="None si el evento sigue abierto")
    severidad: NivelRiesgo | None = None
    fuente: str
    descripcion: str | None = None


# --------------------------------------------------------------------------- #
# Series y calidad                                                              #
# --------------------------------------------------------------------------- #


class PuntoSerie(_Base):
    """Un punto de una serie temporal. `valor` es None donde falta el dato."""

    fecha: date
    valor: float | None = None


class SerieTemporal(_Base):
    """
    Serie para graficar. `puntos` conserva los huecos como None en lugar de
    omitir la fecha: asi el grafico muestra la discontinuidad en vez de
    inventar una linea recta que sugiere continuidad falsa.
    """

    codigo_distrito: str
    variable: str
    unidad: str
    puntos: list[PuntoSerie]


class ReporteCalidad(_Base):
    """Calidad de una variable en un periodo. Evidencia del objetivo especifico 1."""

    fuente: str
    variable: str
    periodo_inicio: date
    periodo_fin: date
    total_esperado: int = Field(ge=0)
    total_presente: int = Field(ge=0)
    pct_faltantes: float = Field(ge=0, le=100)
    metodo_imputacion: MetodoImputacion
    observaciones: str | None = None


class MetricasModelo(_Base):
    """
    Desempeno de un modelo bajo validacion temporal por ventana expansiva.

    Los campos son opcionales porque un modelo puede estar registrado sin
    haberse evaluado todavia. Nunca se reporta una metrica no calculada.
    """

    algoritmo: Algoritmo
    tipo_evento: TipoEvento
    version: str
    entrenado_en: datetime | None = None
    f1_macro: float | None = Field(default=None, ge=0, le=1)
    precision_macro: float | None = Field(default=None, ge=0, le=1)
    exhaustividad_macro: float | None = Field(default=None, ge=0, le=1)
    matriz_confusion: list[list[int]] | None = None
    supera_linea_base: bool | None = Field(
        default=None,
        description="None mientras no se haya contrastado contra la linea base climatologica",
    )


# --------------------------------------------------------------------------- #
# Estado del sistema                                                            #
# --------------------------------------------------------------------------- #


class Salud(_Base):
    """
    Estado de la API. El frontend consulta este endpoint al arrancar y muestra
    un aviso visible cuando `modo` es SIMULADO, para que nadie confunda datos
    de relleno con estimaciones reales.
    """

    version_api: str
    version_contratos: str
    modo: ModoOperacion
    base_datos_conectada: bool
    ultima_ingesta: datetime | None = Field(default=None, description="None si nunca se ejecuto")
