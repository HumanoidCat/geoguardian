"""Vocabulario compartido del dominio. Nadie define estos valores por su cuenta."""

from enum import Enum


class TipoEvento(str, Enum):
    """Eventos que el sistema estima. Cerrado: no se agregan sin cambiar el contrato."""

    LLUVIA_INTENSA = "lluvia_intensa"
    SEQUIA = "sequia"
    INCENDIO = "incendio"


class NivelRiesgo(str, Enum):
    """
    Niveles de la variable objetivo.

    Umbrales definidos en el charter, seccion 2.3.1. Ninguno lo fija el equipo
    de forma arbitraria: se apoyan en indices reconocidos o en la distribucion
    historica del propio distrito.

      Lluvia intensa -> precipitacion acumulada en 72 h por distrito:
                        bajo si <= P95; medio si P95 < acum <= P99; alto si > P99.
                        Percentiles sobre la normal climatologica 1991-2020 del
                        distrito. Corresponde a los indices R95p y R99p del
                        ETCCDI, adoptados por la OMM.

      Sequia         -> SPI-3: bajo si SPI > -1.0; medio si -1.5 < SPI <= -1.0;
                        alto si SPI <= -1.5. McKee et al. (1993), adoptado por la OMM.

      Incendio       -> focos FIRMS en ventana de 7 dias por distrito: bajo si 0;
                        medio si 1 <= n <= P90; alto si n > P90.
                        ATENCION: pendiente de verificar que el canton tenga
                        suficientes focos historicos para entrenar. Ver riesgo R16.
    """

    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"


class Algoritmo(str, Enum):
    """Los tres algoritmos comparados, mas la linea base de contraste."""

    LINEA_BASE = "linea_base_climatologica"
    REGRESION_LOGISTICA = "regresion_logistica"
    RANDOM_FOREST = "random_forest"
    XGBOOST = "xgboost"


class ModoOperacion(str, Enum):
    """
    Indica si la API sirve datos reales o simulados.

    El frontend muestra un aviso visible cuando el modo es SIMULADO. Ver la regla
    de no inventar datos en el metodo de trabajo.
    """

    REAL = "real"
    SIMULADO = "simulado"


class MetodoImputacion(str, Enum):
    """Estrategias permitidas para faltantes. Toda imputacion queda registrada."""

    SIN_IMPUTAR = "sin_imputar"
    INTERPOLACION_LINEAL = "interpolacion_lineal"
    MEDIA_MOVIL = "media_movil"
    CLIMATOLOGIA_MENSUAL = "climatologia_mensual"
