"""
Contrato de persistencia. Dueno: Cesar.

Aisla el dominio de PostgreSQL. Permite probar la logica de negocio sin base de
datos y cambiar el motor sin tocar los modulos que consumen datos. Patron
Repository.
"""

from __future__ import annotations

from datetime import date
from typing import Optional, Protocol, runtime_checkable

from .enums import TipoEvento
from .esquemas import (
    Distrito,
    EventoHistorico,
    FocoCalor,
    IndiceDerivado,
    MedicionDiaria,
    MetricasModelo,
    ReporteCalidad,
    Riesgo,
)


@runtime_checkable
class Repositorio(Protocol):
    """Acceso a datos. Toda escritura ocurre dentro de una transaccion."""

    # -- Territorio --------------------------------------------------------- #

    def listar_distritos(self) -> list[Distrito]:
        """Todos los distritos del canton con su geometria en GeoJSON."""
        ...

    def obtener_distrito(self, codigo: str) -> Optional[Distrito]:
        """None si el codigo no existe. No lanza excepcion: la ausencia es un caso valido."""
        ...

    # -- Mediciones --------------------------------------------------------- #

    def guardar_mediciones(self, mediciones: list[MedicionDiaria]) -> int:
        """
        Inserta o actualiza y devuelve el numero de filas afectadas.

        Idempotente por la clave natural (distrito, fecha). Si el procedimiento
        falla a mitad, revierte todo: no deja cargas parciales.
        """
        ...

    def obtener_mediciones(
        self,
        codigo_distrito: str,
        desde: date,
        hasta: date,
    ) -> list[MedicionDiaria]:
        """
        Devuelve una fila por dia del rango, incluidos los dias sin dato, con
        sus campos en None. El consumidor necesita ver los huecos.
        """
        ...

    # -- Focos de calor ----------------------------------------------------- #

    def guardar_focos(self, focos: list[FocoCalor]) -> int:
        """Asigna cada foco a su distrito por interseccion espacial al guardar."""
        ...

    def contar_focos(
        self,
        codigo_distrito: str,
        desde: date,
        hasta: date,
    ) -> int:
        """Conteo de focos en la ventana. Base del etiquetado de riesgo de incendio."""
        ...

    # -- Derivados y riesgo ------------------------------------------------- #

    def guardar_indices(self, indices: list[IndiceDerivado]) -> int:
        ...

    def obtener_indices(
        self,
        codigo_distrito: str,
        desde: date,
        hasta: date,
    ) -> list[IndiceDerivado]:
        ...

    def guardar_riesgos(self, riesgos: list[Riesgo]) -> int:
        ...

    def obtener_riesgo(
        self,
        codigo_distrito: str,
        fecha: date,
        tipo_evento: TipoEvento,
    ) -> Optional[Riesgo]:
        """None si no hay estimacion para esa combinacion. No se inventa una."""
        ...

    def obtener_riesgos_por_fecha(self, fecha: date, tipo_evento: TipoEvento) -> list[Riesgo]:
        """Riesgo de todos los distritos en una fecha. Alimenta la coropleta del visor."""
        ...

    # -- Eventos, calidad y modelos ----------------------------------------- #

    def listar_eventos(
        self,
        tipo_evento: Optional[TipoEvento] = None,
    ) -> list[EventoHistorico]:
        ...

    def guardar_reporte_calidad(self, reporte: ReporteCalidad) -> None:
        ...

    def listar_reportes_calidad(self) -> list[ReporteCalidad]:
        ...

    def guardar_metricas(self, metricas: MetricasModelo) -> None:
        ...

    def listar_metricas(self) -> list[MetricasModelo]:
        """Alimenta la tabla comparativa de los tres algoritmos contra la linea base."""
        ...
