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
from typing import Any, Optional

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

    codigo: str = Field(description="Codigo oficial del distrito", examples=["50501"])
    nombre: str
    area_km2: float = Field(gt=0)
    poblacion: Optional[int] = Field(default=None, ge=0, description="None si no hay dato censal")
    geometria: dict[str, Any] = Field(description="Poligono GeoJSON en EPSG:4326, listo para Leaflet")


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
    temp_max_c: Optional[float] = None
    temp_min_c: Optional[float] = None
    temp_media_c: Optional[float] = None
    precipitacion_mm: Optional[float] = Field(default=None, ge=0)
    humedad_relativa_pct: Optional[float] = Field(default=None, ge=0, le=100)
    viento_ms: Optional[float] = Field(default=None, ge=0)
    radiacion_mj_m2: Optional[float] = Field(default=None, ge=0)
    imputado: bool = Field(default=False, description="True si algun valor fue imputado")
    metodo_imputacion: MetodoImputacion = MetodoImputacion.SIN_IMPUTAR


class IndiceDerivado(_Base):
    """Indices calculados a partir de las mediciones. None mientras no se calculen."""

    codigo_distrito: str
    fecha: date
    spi_1m: Optional[float] = None
    spi_3m: Optional[float] = None
    anomalia_temp_c: Optional[float] = None
    dias_sin_lluvia: Optional[int] = Field(default=None, ge=0)


class FocoCalor(_Base):
    """Deteccion de foco de calor. Etiqueta de la variable objetivo de incendio."""

    fecha: date
    latitud: float = Field(ge=-90, le=90)
    longitud: float = Field(ge=-180, le=180)
    confianza: Optional[int] = Field(default=None, ge=0, le=100)
    brillo_k: Optional[float] = None
    satelite: Optional[str] = None
    codigo_distrito: Optional[str] = Field(default=None, description="None si cae fuera de todo distrito")


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
    """

    codigo_distrito: str
    fecha: date
    tipo_evento: TipoEvento
    nivel: Optional[NivelRiesgo] = None
    probabilidad: Optional[float] = Field(default=None, ge=0, le=1)
    algoritmo: Optional[Algoritmo] = None
    version_modelo: Optional[str] = None
    explicacion: Optional[list[ContribucionVariable]] = None


class EventoHistorico(_Base):
    """Evento registrado. Sirve para contrastar el modelo contra la realidad."""

    codigo_distrito: str
    tipo_evento: TipoEvento
    fecha_inicio: date
    fecha_fin: Optional[date] = Field(default=None, description="None si el evento sigue abierto")
    severidad: Optional[NivelRiesgo] = None
    fuente: str
    descripcion: Optional[str] = None


# --------------------------------------------------------------------------- #
# Series y calidad                                                              #
# --------------------------------------------------------------------------- #

class PuntoSerie(_Base):
    """Un punto de una serie temporal. `valor` es None donde falta el dato."""

    fecha: date
    valor: Optional[float] = None


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
    observaciones: Optional[str] = None


class MetricasModelo(_Base):
    """
    Desempeno de un modelo bajo validacion temporal por ventana expansiva.

    Los campos son opcionales porque un modelo puede estar registrado sin
    haberse evaluado todavia. Nunca se reporta una metrica no calculada.
    """

    algoritmo: Algoritmo
    tipo_evento: TipoEvento
    version: str
    entrenado_en: Optional[datetime] = None
    f1_macro: Optional[float] = Field(default=None, ge=0, le=1)
    precision_macro: Optional[float] = Field(default=None, ge=0, le=1)
    exhaustividad_macro: Optional[float] = Field(default=None, ge=0, le=1)
    matriz_confusion: Optional[list[list[int]]] = None
    supera_linea_base: Optional[bool] = Field(
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
    ultima_ingesta: Optional[datetime] = Field(default=None, description="None si nunca se ejecuto")
