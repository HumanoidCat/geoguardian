"""
Fuente climatica hibrida: CHIRPS para lluvia, POWER para el resto. H1.1, issue #35.

POR QUE HAY QUE COMBINAR DOS FUENTES

Decision D-15. Ninguna de las dos sirve sola:

  - POWER trae las seis variables que se necesitan, pero su celda mide
    68 x 55 km y el canton entero cabe en una. Los ocho distritos darian el
    mismo numero, y con eso no se puede estimar riesgo por distrito.
  - CHIRPS si distingue distritos, a 0,05 grados, pero solo tiene precipitacion.

La precipitacion es justamente la variable de la que dependen los dos umbrales
del charter, sequia por SPI-6 y lluvia intensa por acumulado de 72 h. Asi que la
que tiene que distinguir distritos viene de CHIRPS, y el resto de POWER.

QUE SIGNIFICA ESO EN LOS DATOS

**Las variables de POWER son identicas en los ocho distritos.** No es un fallo de
la carga: es la resolucion de la fuente. Queda declarado aqui, en el DDL y en la
evidencia, para que nadie lo descubra dentro de tres semanas y lo tome por un bug.

LO QUE ESTE MODULO NO HACE

**No completa un hueco de una fuente con la otra.** El 1 de enero de 2024 en
Tronadora, POWER da 0,0 mm y CHIRPS da 18,72 mm en el mismo lugar. Son productos
distintos y no son intercambiables: si CHIRPS no tiene un dia, ese dia va nulo.
Rellenarlo con POWER produciria una serie que parece completa y no lo es.

**No imputa.** Los huecos se conservan tal cual. Imputar es H1.4, y necesita los
huecos intactos para poder medir cuantos habia.

IDEMPOTENCIA

El contrato la exige. Aqui se cumple porque no hay estado: dos llamadas con los
mismos argumentos hacen las mismas peticiones y arman la misma lista. La
no-duplicacion aguas abajo la garantiza la clave primaria
`(codigo_distrito, fecha)` con `ON CONFLICT DO UPDATE`, en `cargar_mediciones.py`.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from contratos.esquemas import MedicionDiaria

from .chirps import ExtractorChirps
from .power import PARAMETROS, ExtractorPower

log = logging.getLogger(__name__)

# Paso de la malla de MERRA-2, que es el modelo detras de POWER.
PASO_LATITUD = 0.5
PASO_LONGITUD = 0.625


@dataclass(frozen=True)
class Territorio:
    """Lo que hace falta de un distrito para consultar las dos fuentes."""

    codigo: str
    nombre: str
    # Contorno completo, sin simplificar: va en el cuerpo de un POST y ahi no hay
    # limite de tamano. Ver la cabecera de chirps.py.
    geometria: dict
    # Punto interior representativo. Se usa ST_PointOnSurface y no el centroide,
    # porque el centroide de un poligono concavo puede caer fuera del poligono.
    longitud: float
    latitud: float


def celda_power(longitud: float, latitud: float) -> tuple[float, float]:
    """
    Devuelve el centro de la celda de MERRA-2 que contiene al punto.

    **MERRA-2 ancla los centros de celda en multiplos del paso, no los bordes.**
    Por eso se redondea y no se trunca. Con `floor` el calculo da celdas
    distintas para puntos que la fuente sirve identicos, y el numero resultante
    parece razonable, que es lo que lo hace peligroso: fue el error que hubo que
    corregir al contar cuantas celdas cubrian el canton.

    Sirve para no pedir ocho veces la misma serie: si dos distritos caen en la
    misma celda, POWER va a devolver exactamente lo mismo.
    """
    return (
        round(longitud / PASO_LONGITUD) * PASO_LONGITUD,
        round(latitud / PASO_LATITUD) * PASO_LATITUD,
    )


def territorios_desde_base(conexion, codigo_canton: int = 508) -> list[Territorio]:
    """
    Lee los distritos ya cargados por H1.3.

    La geometria sale en EPSG:4326, que es lo que esperan las dos APIs, y en
    orden longitud-latitud, que es el orden de GeoJSON.
    """
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT codigo,
                   nombre,
                   ST_AsGeoJSON(geometria)               AS contorno,
                   ST_X(ST_PointOnSurface(geometria))    AS longitud,
                   ST_Y(ST_PointOnSurface(geometria))    AS latitud
            FROM geo.distrito
            WHERE codigo_canton = %s
            ORDER BY codigo
            """,
            (codigo_canton,),
        )
        filas = cursor.fetchall()

    if not filas:
        raise RuntimeError(
            f"No hay distritos del canton {codigo_canton} en geo.distrito. "
            "H1.1 depende de H1.3: corre primero backend/etl/cargar_distritos.py"
        )

    return [
        Territorio(
            codigo=codigo,
            nombre=nombre,
            geometria=json.loads(contorno),
            longitud=float(longitud),
            latitud=float(latitud),
        )
        for codigo, nombre, contorno, longitud, latitud in filas
    ]


def _dias(desde: date, hasta: date):
    dia = desde
    while dia <= hasta:
        yield dia
        dia = dia + timedelta(days=1)


class ExtractorHibrido:
    """
    Cumple el protocolo `ExtractorClima`.

    Recibe los territorios ya resueltos en vez de consultar la base por su
    cuenta: asi se puede probar sin PostgreSQL y sin red, pasandole territorios
    de prueba y fuentes falsas.
    """

    nombre = "CHIRPS + NASA POWER (hibrida, D-15)"

    def __init__(
        self,
        territorios: list[Territorio],
        power: ExtractorPower | None = None,
        chirps: ExtractorChirps | None = None,
        registrar: Callable[[str], None] | None = None,
    ) -> None:
        self._territorios = {t.codigo: t for t in territorios}
        self._power = power or ExtractorPower()
        self._chirps = chirps or ExtractorChirps()
        self._registrar = registrar or log.info
        # Una celda de POWER cubre varios distritos y devuelve lo mismo para
        # todos. Se guarda por celda y rango para no repetir la peticion.
        self._cache_power: dict[tuple, dict[str, dict[date, float | None]]] = {}

    def cerrar(self) -> None:
        self._power.cerrar()
        self._chirps.cerrar()

    def disponible(self) -> bool:
        """
        Las dos fuentes tienen que responder.

        Con una sola no alcanza: sin CHIRPS no hay lluvia, que es la variable de
        los umbrales; sin POWER faltan las otras cinco. Media descarga produce
        una tabla que parece cargada y no lo esta.
        """
        power = self._power.disponible()
        chirps = self._chirps.disponible()
        if not power:
            self._registrar("NASA POWER no responde")
        if not chirps:
            self._registrar("ClimateSERV/CHIRPS no responde")
        return power and chirps

    def _series_power(self, territorio: Territorio, desde: date, hasta: date):
        longitud, latitud = celda_power(territorio.longitud, territorio.latitud)
        clave = (longitud, latitud, desde, hasta)

        if clave in self._cache_power:
            self._registrar(
                f"{territorio.nombre}: POWER reutiliza la celda "
                f"({longitud}, {latitud}), ya descargada"
            )
            return self._cache_power[clave]

        respuesta = self._power.consultar(territorio.longitud, territorio.latitud, desde, hasta)
        self._registrar(
            f"{territorio.nombre}: POWER {respuesta.dias} dias, "
            f"elevacion {respuesta.elevacion} m, api {respuesta.version_api}"
        )
        self._cache_power[clave] = respuesta.series
        return respuesta.series

    def extraer(
        self,
        codigo_distrito: str,
        desde: date,
        hasta: date,
    ) -> list[MedicionDiaria]:
        """
        Devuelve una medicion por dia del rango, huecos incluidos.

        Los dias sin dato salen con sus campos en None y **no se omiten**: el
        contrato lo pide asi porque omitirlos haria indistinguible un hueco de un
        dia que no existe.
        """
        territorio = self._territorios.get(codigo_distrito)
        if territorio is None:
            conocidos = ", ".join(sorted(self._territorios)) or "ninguno"
            raise KeyError(
                f"El distrito {codigo_distrito} no esta entre los cargados ({conocidos})"
            )

        series = self._series_power(territorio, desde, hasta)
        lluvia = self._chirps.consultar(territorio.geometria, desde, hasta)
        self._registrar(
            f"{territorio.nombre}: CHIRPS {len(lluvia)} dias, "
            f"{sum(1 for v in lluvia.values() if v is None)} sin dato"
        )

        mediciones: list[MedicionDiaria] = []
        for dia in _dias(desde, hasta):
            valores = {
                campo: series.get(parametro, {}).get(dia) for parametro, campo in PARAMETROS.items()
            }
            # `lluvia.get(dia)` da None tanto si CHIRPS marco el dia sin dato como
            # si no devolvio la fila. Las dos cosas son ausencia de dato y se
            # representan igual: nulo. Nunca cero.
            mediciones.append(
                MedicionDiaria(
                    codigo_distrito=codigo_distrito,
                    fecha=dia,
                    precipitacion_mm=lluvia.get(dia),
                    **valores,
                )
            )

        return mediciones
