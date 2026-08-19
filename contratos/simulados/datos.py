"""Repositorio y extractores simulados. Datos deterministas, reproducibles y falsos."""

from __future__ import annotations

import logging
import random
from datetime import date, timedelta

from .. import VERSION_CONTRATOS
from ..enums import Algoritmo, MetodoImputacion, ModoOperacion, NivelRiesgo, TipoEvento
from ..esquemas import (
    Distrito,
    EventoHistorico,
    FocoCalor,
    IndiceDerivado,
    MedicionDiaria,
    MetricasModelo,
    ReporteCalidad,
    Riesgo,
    Salud,
)

log = logging.getLogger(__name__)

SEMILLA = 20260803

# Los ocho distritos de Tilaran con geometrias de marcador de posicion.
#
# Los codigos son los oficiales del SNIT: 5 = Guanacaste, 08 = Tilaran, y los dos
# ultimos digitos el distrito. NO son 505xx: ese es el canton de Carrillo. El
# error estuvo en los contratos hasta la version 1.2.0. Ver incidencia I-04.
#
# Las geometrias reales se cargan de la capa IGN_5_CO:limitedistrital_5k del SNIT
# en la historia H1.3. Ver D-13.
_DISTRITOS = [
    ("50801", "Tilaran", 60.0),
    ("50802", "Quebrada Grande", 88.4),
    ("50803", "Tronadora", 30.2),
    ("50804", "Santa Rosa", 33.6),
    ("50805", "Libano", 76.9),
    ("50806", "Tierras Morenas", 76.4),
    ("50807", "Arenal", 156.5),
    ("50808", "Cabeceras", 116.3),
]


def _cuadro(i: int) -> dict:
    """Poligono ficticio, solo para que el visor tenga algo que dibujar."""
    lon, lat = -84.97 + (i % 3) * 0.09, 10.47 - (i // 3) * 0.07
    d = 0.04
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [lon, lat],
                [lon + d, lat],
                [lon + d, lat - d],
                [lon, lat - d],
                [lon, lat],
            ]
        ],
    }


class RepositorioSimulado:
    """Cumple el protocolo Repositorio. No toca ninguna base de datos."""

    def __init__(self) -> None:
        log.warning("RepositorioSimulado en uso: los datos NO son reales")
        self._rnd = random.Random(SEMILLA)

    # -- Territorio --------------------------------------------------------- #

    def listar_distritos(self) -> list[Distrito]:
        return [
            Distrito(codigo=c, nombre=n, area_km2=a, poblacion=None, geometria=_cuadro(i))
            for i, (c, n, a) in enumerate(_DISTRITOS)
        ]

    def obtener_distrito(self, codigo: str) -> Distrito | None:
        return next((d for d in self.listar_distritos() if d.codigo == codigo), None)

    # -- Mediciones --------------------------------------------------------- #

    def guardar_mediciones(self, mediciones: list[MedicionDiaria]) -> int:
        return len(mediciones)

    def obtener_mediciones(
        self, codigo_distrito: str, desde: date, hasta: date
    ) -> list[MedicionDiaria]:
        """Incluye huecos a proposito: una de cada veinte fechas viene sin dato."""
        salida, actual, i = [], desde, 0
        while actual <= hasta:
            hueco = i % 20 == 7
            salida.append(
                MedicionDiaria(
                    codigo_distrito=codigo_distrito,
                    fecha=actual,
                    temp_max_c=None if hueco else round(self._rnd.uniform(27, 34), 1),
                    temp_min_c=None if hueco else round(self._rnd.uniform(17, 22), 1),
                    temp_media_c=None if hueco else round(self._rnd.uniform(22, 27), 1),
                    precipitacion_mm=None if hueco else round(max(0.0, self._rnd.gauss(4, 9)), 1),
                    humedad_relativa_pct=None if hueco else round(self._rnd.uniform(60, 95), 1),
                    viento_ms=None if hueco else round(self._rnd.uniform(1, 11), 1),
                    radiacion_mj_m2=None if hueco else round(self._rnd.uniform(12, 24), 1),
                    imputado=False,
                    metodo_imputacion=MetodoImputacion.SIN_IMPUTAR,
                )
            )
            actual += timedelta(days=1)
            i += 1
        return salida

    # -- Focos de calor ----------------------------------------------------- #

    def guardar_focos(self, focos: list[FocoCalor]) -> int:
        return len(focos)

    def contar_focos(self, codigo_distrito: str, desde: date, hasta: date) -> int:
        return self._rnd.randint(0, 6)

    # -- Derivados y riesgo ------------------------------------------------- #

    def guardar_indices(self, indices: list[IndiceDerivado]) -> int:
        return len(indices)

    def obtener_indices(
        self, codigo_distrito: str, desde: date, hasta: date
    ) -> list[IndiceDerivado]:
        salida, actual = [], desde
        while actual <= hasta:
            salida.append(
                IndiceDerivado(
                    codigo_distrito=codigo_distrito,
                    fecha=actual,
                    spi_1m=round(self._rnd.gauss(0, 1), 2),
                    spi_3m=round(self._rnd.gauss(0, 1), 2),
                    anomalia_temp_c=round(self._rnd.gauss(0, 1.5), 2),
                    dias_sin_lluvia=self._rnd.randint(0, 20),
                )
            )
            actual += timedelta(days=7)
        return salida

    def guardar_riesgos(self, riesgos: list[Riesgo]) -> int:
        return len(riesgos)

    def obtener_riesgo(
        self, codigo_distrito: str, fecha: date, tipo_evento: TipoEvento
    ) -> Riesgo | None:
        nivel = self._rnd.choice(list(NivelRiesgo))
        return Riesgo(
            codigo_distrito=codigo_distrito,
            fecha=fecha,
            tipo_evento=tipo_evento,
            nivel=nivel,
            probabilidad=round(self._rnd.uniform(0.3, 0.95), 2),
            algoritmo=Algoritmo.XGBOOST,
            version_modelo="simulado-0.0.0",
            explicacion=None,
        )

    def obtener_riesgos_por_fecha(self, fecha: date, tipo_evento: TipoEvento) -> list[Riesgo]:
        return [
            self.obtener_riesgo(d.codigo, fecha, tipo_evento)  # type: ignore[misc]
            for d in self.listar_distritos()
        ]

    # -- Eventos, calidad y modelos ----------------------------------------- #

    def listar_eventos(self, tipo_evento: TipoEvento | None = None) -> list[EventoHistorico]:
        base = [
            EventoHistorico(
                codigo_distrito="50801",
                tipo_evento=TipoEvento.LLUVIA_INTENSA,
                fecha_inicio=date(2021, 7, 20),
                fecha_fin=date(2021, 7, 23),
                severidad=NivelRiesgo.ALTO,
                fuente="SIMULADO: reemplazar con catalogo real de la historia H4.3",
                descripcion=None,
            ),
            EventoHistorico(
                codigo_distrito="50806",
                tipo_evento=TipoEvento.SEQUIA,
                fecha_inicio=date(2019, 2, 1),
                fecha_fin=date(2019, 5, 15),
                severidad=NivelRiesgo.ALTO,
                fuente="SIMULADO: reemplazar con catalogo real de la historia H4.3",
                descripcion=None,
            ),
            EventoHistorico(
                codigo_distrito="50807",
                tipo_evento=TipoEvento.INCENDIO,
                fecha_inicio=date(2020, 3, 10),
                fecha_fin=date(2020, 3, 14),
                severidad=NivelRiesgo.MEDIO,
                fuente="SIMULADO: reemplazar con catalogo real de la historia H4.3",
                descripcion=None,
            ),
        ]
        return [e for e in base if tipo_evento is None or e.tipo_evento == tipo_evento]

    def guardar_reporte_calidad(self, reporte: ReporteCalidad) -> None:
        return None

    def listar_reportes_calidad(self) -> list[ReporteCalidad]:
        return []

    def guardar_metricas(self, metricas: MetricasModelo) -> None:
        return None

    def listar_metricas(self) -> list[MetricasModelo]:
        """
        Vacio a proposito. Todavia no se entreno ningun modelo, asi que no hay
        metricas que reportar. Devolver numeros aqui seria inventar resultados.
        """
        return []


class ExtractorClimaSimulado:
    """Cumple el protocolo ExtractorClima. No hace peticiones de red."""

    nombre = "SIMULADO-clima"

    def __init__(self) -> None:
        log.warning("ExtractorClimaSimulado en uso: los datos NO son reales")
        self._repo = RepositorioSimulado()

    def disponible(self) -> bool:
        return True

    def extraer(self, codigo_distrito: str, desde: date, hasta: date) -> list[MedicionDiaria]:
        return self._repo.obtener_mediciones(codigo_distrito, desde, hasta)


class ExtractorFocosSimulado:
    """Cumple el protocolo ExtractorFocosCalor."""

    nombre = "SIMULADO-focos"

    def __init__(self) -> None:
        log.warning("ExtractorFocosSimulado en uso: los datos NO son reales")
        self._rnd = random.Random(SEMILLA)

    def disponible(self) -> bool:
        return True

    def extraer(self, desde: date, hasta: date) -> list[FocoCalor]:
        return [
            FocoCalor(
                fecha=desde + timedelta(days=self._rnd.randint(0, max(0, (hasta - desde).days))),
                latitud=round(self._rnd.uniform(10.40, 10.55), 4),
                longitud=round(self._rnd.uniform(-85.05, -84.85), 4),
                confianza=self._rnd.randint(30, 100),
                brillo_k=round(self._rnd.uniform(300, 360), 1),
                satelite="SIMULADO",
                codigo_distrito=None,
            )
            for _ in range(12)
        ]


def salud_simulada() -> Salud:
    """Estado que la API expone mientras corre con simulados."""
    return Salud(
        version_api="0.1.0",
        version_contratos=VERSION_CONTRATOS,
        modo=ModoOperacion.SIMULADO,
        base_datos_conectada=False,
        ultima_ingesta=None,
    )
