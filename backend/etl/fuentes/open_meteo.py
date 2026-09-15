"""
Open-Meteo como serie larga del canton. Historia H1.16, issue #299. Decision D-47.

QUE TRAE, Y QUE NO

Trae **una serie diaria de precipitacion del canton entero desde 1950**, para un
solo uso: contar episodios de sequia sobre la serie larga (H3.11).

**No trae una serie por distrito, y no puede traerla.** D-47 lo decidio con el
test de resolucion que D-15 dejo como condicion, y el CA-9 de H1.16 lo hace
cumplir en el esquema: `crudo.serie_canton` no tiene columna de distrito.

ERA5-Land NO SIRVE LLUVIA, Y ESO CAMBIO LA FUENTE

D-47 se escribio nombrando **ERA5-Land**: 0,1 grados, archivo desde 1950. Medido
el 2026-09-14 contra la API, ese modelo **no devuelve precipitacion diaria en
ningun punto del mundo**:

    punto                modelo      temperatura   precipitacion
    Tilaran              era5_land        5 / 5         0 / 5
    San Jose             era5_land        5 / 5         0 / 5
    Madrid               era5_land        5 / 5         0 / 5
    Tilaran              era5             5 / 5         5 / 5

Asi que la serie larga sale de **ERA5**, que es una malla mas gruesa -0,25
grados-. Repetido el test de D-15 sobre ERA5 con los ocho centroides:

    50801 Tilaran          -> 10.5, -85.0       50805 Libano          -> 10.5, -85.0
    50802 Quebrada Grande  -> 10.5, -85.0       50806 Tierras Morenas -> 10.5, -85.0
    50803 Tronadora        -> 10.5, -84.75      50807 Arenal          -> 10.5, -84.75
    50804 Santa Rosa       -> 10.5, -85.0       50808 Cabeceras       -> 10.25, -84.75

**Tres celdas para ocho distritos, y cinco comparten una.** La conclusion de D-47
no se debilita: se refuerza. Y para el uso a nivel canton da igual, porque D-34
ya cuenta la sequia a nivel canton.

EL MODELO SE DECLARA SIEMPRE

Sin el parametro `models` la API elige sola y **devuelve otra celda**
(10,509666 / -85,004425 en vez de 10,5 / -85). Una serie cuyo origen puede
cambiar entre dos corridas sin que nadie lo note no es una serie. Es la misma
regla que D-50 fijo para el pronostico: modelo declarado, nunca `best_match`.

POR QUE ESTA CLASE NO SE REGISTRA EN LA FABRICA

`fuentes/fabrica.py` ya explica que `ExtractorChirps` y `ExtractorPower` no estan
registradas porque no cumplen `ExtractorClima`: son clientes de una API, no
estrategias intercambiables. Esta clase esta en el mismo caso y por una razon
mas fuerte: **devuelve una serie del canton, no una serie por distrito**, asi que
no es intercambiable con las otras ni aunque tuviera los metodos.

Registrarla declararia como sustituible algo que no lo es, y el orquestador la
recibiria donde espera otra forma. Por eso **no se toca la fabrica ni el
orquestador**, que es lo que pedia el CA-2, y el hallazgo se declara: el patron
Strategy cubre «otra fuente de la misma forma», no «una fuente de otra forma».

CUANTO CUESTA UNA CORRIDA

**Una peticion.** Medido el 2026-09-14: 1950-01-01 a 2024-12-31 en una sola
llamada devuelve 27.394 dias, 493 KB, en 604 ms. Es el CA-7.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date

#: El archivo de reanalisis. `era5_land` no sirve precipitacion: ver la cabecera.
MODELO = "era5"

#: La API nunca elige: este nombre esta prohibido en el esquema (migracion 020).
MODELO_PROHIBIDO = "best_match"

BASE = "https://archive-api.open-meteo.com/v1/archive"

#: ERA5 empieza en 1950. Pedir antes devuelve error, no una serie mas larga.
PRIMER_ANIO = 1950

TIEMPO_LIMITE = 120

ATRIBUCION = (
    "Open-Meteo (open-meteo.com), reanalisis ERA5 de Copernicus / ECMWF. "
    "Datos bajo Attribution 4.0 International (CC BY 4.0)."
)


class ErrorOpenMeteo(Exception):
    """La fuente no contesto, o contesto algo que no es una serie."""


@dataclass
class DiaDelCanton:
    """Un dia de la serie del canton. Sin distrito, a proposito."""

    fecha: date
    precipitacion_mm: float | None
    modelo: str
    celda_lat: float
    celda_lon: float
    punto_lat: float
    punto_lon: float


@dataclass
class ExtractorOpenMeteoCanton:
    """Cliente del archivo de Open-Meteo para UN punto: el del canton.

    `punto_lat` y `punto_lon` no tienen valor por omision a proposito. El punto
    representativo del canton se calcula desde `geo.distrito` y se le pasa
    hecho: un par de coordenadas escrito a mano en el codigo es un dato sin
    procedencia, y este proyecto ya tuvo esa discusion con las geometrias.
    """

    punto_lat: float
    punto_lon: float
    modelo: str = MODELO
    peticiones: int = field(default=0, init=False)

    nombre: str = "open-meteo-canton"

    def __post_init__(self) -> None:
        if self.modelo == MODELO_PROHIBIDO or not self.modelo:
            raise ValueError(
                f"El modelo tiene que declararse y no puede ser '{MODELO_PROHIBIDO}': "
                "sin declararlo la API elige sola y devuelve otra celda."
            )

    # -- La consulta ------------------------------------------------------- #

    def url(self, desde: date, hasta: date) -> str:
        parametros = {
            "latitude": f"{self.punto_lat:.6f}",
            "longitude": f"{self.punto_lon:.6f}",
            "start_date": desde.isoformat(),
            "end_date": hasta.isoformat(),
            "daily": "precipitation_sum",
            "timezone": "UTC",
            "models": self.modelo,
        }
        return f"{BASE}?{urllib.parse.urlencode(parametros)}"

    def disponible(self) -> bool:
        """No necesita credenciales. Se deja por simetria con las otras fuentes."""
        return True

    def consultar(self, desde: date, hasta: date) -> list[DiaDelCanton]:
        """Una peticion, un rango. Devuelve la serie tal como vino.

        No rellena huecos ni recorta: los dias sin dato vuelven con
        `precipitacion_mm = None` y se guardan asi, que es D-07.
        """
        if desde.year < PRIMER_ANIO:
            raise ValueError(f"El archivo empieza en {PRIMER_ANIO}; se pidio {desde.isoformat()}.")
        if hasta < desde:
            raise ValueError("La fecha final es anterior a la inicial.")

        self.peticiones += 1
        try:
            with urllib.request.urlopen(self.url(desde, hasta), timeout=TIEMPO_LIMITE) as r:
                cuerpo = json.loads(r.read().decode("utf-8"))
        except Exception as causa:  # noqa: BLE001
            raise ErrorOpenMeteo(f"No se pudo consultar Open-Meteo: {causa}") from causa

        return self.leer(cuerpo)

    # -- La lectura, separada de la red para poder probarla ----------------- #

    def leer(self, cuerpo: dict) -> list[DiaDelCanton]:
        """Convierte la respuesta en filas, o explica por que no puede.

        Vive aparte de `consultar` para que las pruebas midan el parseo sin
        tocar la red, que es lo unico que se puede comprobar sin internet.
        """
        diario = cuerpo.get("daily")
        if not isinstance(diario, dict) or "time" not in diario:
            raise ErrorOpenMeteo(f"La respuesta no trae una serie diaria: {str(cuerpo)[:200]}")

        fechas = diario["time"]
        lluvias = diario.get("precipitation_sum")
        if lluvias is None:
            raise ErrorOpenMeteo("La respuesta no trae `precipitation_sum`.")
        if len(fechas) != len(lluvias):
            raise ErrorOpenMeteo(
                f"La serie viene despareja: {len(fechas)} fechas y {len(lluvias)} valores."
            )

        celda_lat = cuerpo.get("latitude")
        celda_lon = cuerpo.get("longitude")
        if celda_lat is None or celda_lon is None:
            raise ErrorOpenMeteo("La respuesta no dice que celda devolvio.")

        # Una serie entera en `null` NO es una serie vacia: es el sintoma de
        # haber pedido un modelo que no sirve esta variable, que es exactamente
        # lo que hace `era5_land` con la precipitacion. Fallar aca es lo que
        # impide guardar 28.011 ausencias y llamarlas dato (medido el 2026-09-14).
        if fechas and all(v is None for v in lluvias):
            raise ErrorOpenMeteo(
                f"El modelo '{self.modelo}' devolvio {len(fechas)} dias y ninguno con "
                "precipitacion. Medido el 2026-09-14: 'era5_land' se comporta asi en "
                "cualquier punto del mundo. Revisar el modelo antes de guardar nada."
            )

        return [
            DiaDelCanton(
                fecha=date.fromisoformat(f),
                precipitacion_mm=None if v is None else float(v),
                modelo=self.modelo,
                celda_lat=float(celda_lat),
                celda_lon=float(celda_lon),
                punto_lat=self.punto_lat,
                punto_lon=self.punto_lon,
            )
            for f, v in zip(fechas, lluvias, strict=True)
        ]
