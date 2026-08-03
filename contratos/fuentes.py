"""
Contrato de extractores. Dueno: Cesar.

Toda fuente externa se adapta a esta interfaz. Agregar una fuente nueva no debe
requerir tocar el orquestador: se registra y listo. Patron Strategy.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable

from .esquemas import FocoCalor, MedicionDiaria


@runtime_checkable
class ExtractorClima(Protocol):
    """Fuente de series climaticas diarias. Implementaciones: NASA POWER, IMN."""

    nombre: str

    def disponible(self) -> bool:
        """
        Verifica conectividad y credenciales sin descargar datos.

        Se llama antes de iniciar una ingesta larga, para fallar temprano.
        """
        ...

    def extraer(
        self,
        codigo_distrito: str,
        desde: date,
        hasta: date,
    ) -> list[MedicionDiaria]:
        """
        Descarga las mediciones del rango.

        Debe ser idempotente: llamarla dos veces con los mismos argumentos
        produce el mismo resultado y no duplica nada aguas abajo.

        Los dias sin dato se devuelven con sus campos en None, no se omiten.
        Omitirlos haria indistinguible un hueco de un dia que no existe.
        """
        ...


@runtime_checkable
class ExtractorFocosCalor(Protocol):
    """Fuente de focos de calor. Implementacion: NASA FIRMS."""

    nombre: str

    def disponible(self) -> bool: ...

    def extraer(self, desde: date, hasta: date) -> list[FocoCalor]:
        """
        Descarga los focos del rango dentro del area de estudio.

        El filtrado por distrito ocurre despues, en la capa de repositorio, que
        es la que conoce las geometrias. El extractor no hace analisis espacial.
        """
        ...
