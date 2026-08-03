"""
Contrato de procesamiento de senales. Dueno: Alejandro.

Cubre la integracion de Senales y Sistemas: filtrado, remuestreo, analisis en el
dominio de la frecuencia y convolucion de ventana movil para el SPI.

Trabaja sobre listas de valores opcionales porque las series reales tienen
huecos. Cada metodo declara explicitamente como trata los None.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProcesadorSenales(Protocol):
    """Operaciones sobre series temporales climaticas."""

    def filtrar_ruido(
        self,
        serie: list[float | None],
        ventana: int,
    ) -> list[float | None]:
        """
        Suaviza la serie preservando los huecos.

        Una posicion que entra como None sale como None. El filtro no rellena:
        rellenar aqui esconderia la falta de dato al resto del sistema.
        """
        ...

    def espectro(
        self,
        serie: list[float | None],
        frecuencia_muestreo: float,
    ) -> tuple[list[float], list[float]]:
        """
        Analisis en el dominio de la frecuencia.

        Devuelve (frecuencias, magnitudes). Sirve para identificar el ciclo anual
        y semianual de la precipitacion.

        Requiere una serie sin huecos: si recibe None, lanza ValueError indicando
        cuantos faltan. Interpolar en silencio antes de una FFT introduce
        componentes espectrales falsas.
        """
        ...

    def spi(
        self,
        precipitacion: list[float | None],
        ventana_meses: int,
    ) -> list[float | None]:
        """
        Indice de Precipitacion Estandarizado por convolucion de ventana movil.

        Referencia: McKee, Doesken y Kleist (1993), adoptado por la OMM.

        Las primeras `ventana_meses` posiciones salen None porque no hay historia
        suficiente para calcularlas. No se rellenan con ceros.
        """
        ...

    def anomalia(
        self,
        serie: list[float | None],
        normal_por_mes: dict[int, float],
    ) -> list[float | None]:
        """
        Desviacion respecto a la normal climatologica 1991-2020.

        `normal_por_mes` va indexado por numero de mes (1 a 12). Si falta el mes,
        el resultado de esa posicion es None.
        """
        ...

    def remuestrear(
        self,
        serie: list[float | None],
        factor: int,
        agregacion: str,
    ) -> list[float | None]:
        """
        Cambia la frecuencia de muestreo. `agregacion` en {"suma", "media", "max", "min"}.

        Una ventana con mas de la mitad de valores faltantes produce None, no un
        promedio de los pocos datos presentes que aparentaria ser confiable.
        """
        ...
