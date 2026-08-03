"""
Contrato de estimacion de riesgo. Dueno: Alejandro.

Es el nucleo cientifico: aqui vive la respuesta a la pregunta de investigacion.
La linea base implementa la misma interfaz que los modelos entrenados, para que
la comparacion sea justa por construccion y no por convencion.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable

from .enums import Algoritmo, NivelRiesgo, TipoEvento
from .esquemas import ContribucionVariable, MetricasModelo


@runtime_checkable
class Estimador(Protocol):
    """
    Estimador de riesgo. Lo implementan tanto la linea base climatologica como
    los tres algoritmos supervisados.

    Que la linea base cumpla el mismo contrato es deliberado: se evalua con el
    mismo codigo y sobre las mismas particiones, sin margen para comparaciones
    sesgadas.
    """

    algoritmo: Algoritmo
    tipo_evento: TipoEvento
    version: str

    def entrenado(self) -> bool:
        """False mientras no se haya ajustado. Consultarlo antes de predecir."""
        ...

    def entrenar(
        self,
        caracteristicas: list[dict[str, float | None]],
        etiquetas: list[NivelRiesgo],
    ) -> None:
        """
        Ajusta el estimador.

        La linea base ignora `caracteristicas` y usa solo la distribucion
        historica por distrito y mes calendario: esa es justamente su definicion.
        """
        ...

    def predecir(
        self,
        caracteristicas: list[dict[str, float | None]],
    ) -> list[tuple[NivelRiesgo, float]]:
        """
        Devuelve (nivel, probabilidad) por observacion.

        Lanza RuntimeError si no esta entrenado. Nunca devuelve una prediccion
        por defecto: un estimador sin entrenar no tiene nada que decir.
        """
        ...

    def explicar(
        self,
        caracteristicas: dict[str, float | None],
    ) -> list[ContribucionVariable] | None:
        """
        Aporte de cada variable a una prediccion concreta, via SHAP.

        Devuelve None cuando el estimador no soporta explicabilidad, como la
        linea base. None significa no disponible, no ausencia de contribucion.
        """
        ...


@runtime_checkable
class Evaluador(Protocol):
    """Validacion temporal y contraste de hipotesis."""

    def validar_ventana_expansiva(
        self,
        estimador: Estimador,
        caracteristicas: list[dict[str, float | None]],
        etiquetas: list[NivelRiesgo],
        fechas: list[date],
        n_cortes: int,
    ) -> MetricasModelo:
        """
        Valida por ventana expansiva: entrena con el pasado, prueba con el futuro.

        Prohibida la particion aleatoria. Con series temporales filtra
        informacion del futuro y produce metricas infladas que no se sostienen
        en operacion.
        """
        ...

    def comparar_con_linea_base(
        self,
        metricas_modelo: MetricasModelo,
        metricas_linea_base: MetricasModelo,
    ) -> tuple[bool, float]:
        """
        Contrasta H1. Devuelve (supera, valor_p).

        Un resultado negativo no es un fallo del proyecto: significa que los
        datos abiertos globales no bastan a escala cantonal, que es un hallazgo
        valido y reportable.
        """
        ...
