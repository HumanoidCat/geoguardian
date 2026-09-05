"""
Fuente de juguete. Existe solo para H6.3 (CA-4): comprobar que agregar una
fuente climatica no toca los cargadores.

No sale a la red, no se usa en produccion y su `nombre` lo dice para que
nadie la confunda con una fuente real si algun dia queda registrada por
error en un ambiente que no es de pruebas.
"""

from __future__ import annotations

from datetime import date, timedelta

from contratos.esquemas import MedicionDiaria


class ExtractorPrueba:
    """Cumple `ExtractorClima` devolviendo valores fijos, sin red ni base de datos."""

    nombre = "PRUEBA H6.3 (no usar en produccion)"

    def disponible(self) -> bool:
        return True

    def extraer(
        self,
        codigo_distrito: str,
        desde: date,
        hasta: date,
    ) -> list[MedicionDiaria]:
        dias = (hasta - desde).days + 1
        return [
            MedicionDiaria(
                codigo_distrito=codigo_distrito,
                fecha=desde + timedelta(days=i),
                temp_max_c=25.0,
                temp_min_c=18.0,
                temp_media_c=21.5,
                humedad_relativa_pct=80.0,
                viento_ms=2.0,
                radiacion_mj_m2=15.0,
                precipitacion_mm=0.0,
            )
            for i in range(dias)
        ]
