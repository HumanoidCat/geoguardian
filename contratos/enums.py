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
                        distrito.
                        NO es el indice R95p del ETCCDI. R95p se define sobre
                        precipitacion DIARIA de dias humedos, no sobre acumulado
                        de 72 h, y sobre los mismos 30 anios los dos umbrales
                        difieren en un factor de 1,6. Confundirlos multiplica por
                        8,5 los dias declarados en riesgo alto: medido en H2.7,
                        ver la nota de revision de D-08. El corte sigue el
                        criterio de percentiles extremos del ETCCDI, que es otra
                        cosa que ser uno de sus indices.

      Sequia         -> SPI-6 (D-32): bajo si SPI > -1.0; medio si -1.5 < SPI <= -1.0;
                        alto si SPI <= -1.5. McKee et al. (1993), adoptado por la OMM.

      Incendio       -> focos FIRMS en ventana de 7 dias por distrito:
                        **alto si hay al menos un foco; bajo si no hay ninguno.**
                        MEDIO NO EXISTE PARA ESTE EVENTO.

                        El umbral anterior era por percentiles del conteo —bajo
                        si 0, medio si 1 <= n <= P90, alto si n > P90— y **no
                        producia tres clases sobre estos datos, producia dos**.
                        Cesar midio R16 el 20 de agosto: 242 focos en 24 anios,
                        con entre 97 % y 99,9 % de ventanas vacias, asi que el
                        P90 vale 0,0 en los ocho distritos. La condicion
                        `1 <= n <= 0` esta vacia y cualquier foco unico caia en
                        ALTO. La regla vieja ya se comportaba como binaria: lo
                        que cambia es que ahora lo declara.

                        Al definir ALTO como «al menos un foco», la probabilidad
                        que predice el modelo —P(al menos un foco)— **es**
                        P(nivel = alto), y D-21 se cumple literalmente. Con la
                        formulacion anterior serian dos magnitudes distintas
                        bajo el mismo nombre.

                        Que un evento use dos de los tres valores del enum es
                        propiedad del evento, no defecto del vocabulario.

                        Ver la solicitud SC-05 y la decision D-25. Cierra R16.
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
