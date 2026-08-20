"""
NASA POWER: temperatura, humedad, viento y radiacion. Historia H1.1, issue #35.

QUE APORTA Y QUE NO

Por la decision D-15, POWER aporta todo menos la precipitacion. Esa viene de
CHIRPS, porque POWER no distingue entre distritos: su celda mide 68 x 55 km y el
canton entero cabe dentro de una sola.

Consecuencia que hay que tener presente: **las variables de este modulo son
identicas en los ocho distritos**. No es un error de la carga, es la resolucion de
la fuente, y queda declarado como limitacion.

LO QUE SE COMPROBO CONTRA EL SERVICIO

  - Acepta los 35 anios de la ventana en una sola peticion, sin trocear.
  - Marca los faltantes con -999.0, declarado en la cabecera como `fill_value`.
  - Declara la unidad de cada parametro en la seccion `parameters`.
  - Devuelve la elevacion junto a las coordenadas: sirve para detectar que dos
    puntos distintos cayeron en la misma celda de malla.

DOS COSAS QUE NO SE SUPONEN

El valor de relleno se lee de la cabecera de cada respuesta, no se fija en el
codigo: si la fuente lo cambia, el extractor sigue siendo correcto.

Las unidades se comparan contra lo que espera el contrato y la descarga falla si
no coinciden. El caso peligroso es la radiacion: el contrato la pide en MJ/m2 y
POWER la sirve en MJ/m2/dia o en kWh/m2/dia segun la comunidad de datos que se
pida. Un factor 3,6 pasado por alto no rompe nada visible y contamina el modelo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import httpx

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

# Comunidad de datos. AG entrega la radiacion en MJ/m2/dia, que es lo que pide el
# contrato. Cambiarla altera las unidades: por eso la comprobacion de UNIDADES.
COMUNIDAD = "AG"

# Parametro de POWER -> campo del contrato MedicionDiaria.
PARAMETROS = {
    "T2M_MAX": "temp_max_c",
    "T2M_MIN": "temp_min_c",
    "T2M": "temp_media_c",
    "RH2M": "humedad_relativa_pct",
    "WS2M": "viento_ms",
    "ALLSKY_SFC_SW_DWN": "radiacion_mj_m2",
}

# Unidad que el contrato espera para cada parametro. Si la respuesta declara otra,
# la descarga se detiene en vez de convertir a ciegas.
UNIDADES = {
    "T2M_MAX": "C",
    "T2M_MIN": "C",
    "T2M": "C",
    "RH2M": "%",
    "WS2M": "m/s",
    "ALLSKY_SFC_SW_DWN": "MJ/m^2/day",
}

TIEMPO_LIMITE = 180.0


class ErrorPower(Exception):
    """Falla al consultar POWER. Detiene la descarga en vez de seguir a medias."""


@dataclass(frozen=True)
class RespuestaPower:
    """Lo que devolvio una consulta, con su rastro."""

    url: str
    valor_relleno: float
    elevacion: float | None
    version_api: str
    series: dict[str, dict[date, float | None]]

    @property
    def dias(self) -> int:
        return len(next(iter(self.series.values()), {}))


def _a_fecha(clave: str) -> date:
    return date(int(clave[0:4]), int(clave[4:6]), int(clave[6:8]))


def _comprobar_unidades(contenido: dict) -> None:
    """Compara lo que declara la respuesta contra lo que espera el contrato."""
    declaradas = contenido.get("parameters", {})
    problemas = []

    for parametro, esperada in UNIDADES.items():
        real = (declaradas.get(parametro) or {}).get("units")
        if real is None:
            problemas.append(f"  {parametro}: la respuesta no declara unidad")
        elif real != esperada:
            problemas.append(
                f"  {parametro}: la fuente da {real!r} y el contrato espera {esperada!r}"
            )

    if problemas:
        raise ErrorPower(
            "Las unidades de POWER no son las esperadas:\n"
            + "\n".join(problemas)
            + "\n\nNo se convierte a ciegas: revisar la comunidad de datos "
            f"(ahora {COMUNIDAD!r}) antes de seguir."
        )


class ExtractorPower:
    """
    Consulta POWER en un punto. No cumple `ExtractorClima` por si solo: lo hace el
    extractor hibrido, que combina esta fuente con CHIRPS.
    """

    nombre = "NASA POWER"

    def __init__(self, cliente: httpx.Client | None = None) -> None:
        self._propio = cliente is None
        self._cliente = cliente or httpx.Client(timeout=TIEMPO_LIMITE, follow_redirects=True)

    def cerrar(self) -> None:
        if self._propio:
            self._cliente.close()

    def disponible(self) -> bool:
        """
        Comprueba conectividad sin descargar una serie larga.

        Pide un solo dia de un solo parametro. Devuelve falso en vez de lanzar
        excepcion, porque el contrato dice que se llama antes de una ingesta larga
        para fallar temprano, no para interrumpir.
        """
        try:
            ayer = date.today() - timedelta(days=30)
            respuesta = self._cliente.get(
                URL,
                params={
                    "parameters": "T2M",
                    "community": COMUNIDAD,
                    "longitude": -84.95,
                    "latitude": 10.48,
                    "start": ayer.strftime("%Y%m%d"),
                    "end": ayer.strftime("%Y%m%d"),
                    "format": "JSON",
                },
                timeout=20.0,
            )
            return respuesta.status_code == 200
        except httpx.HTTPError:
            return False

    def consultar(
        self, longitud: float, latitud: float, desde: date, hasta: date
    ) -> RespuestaPower:
        """
        Descarga el rango completo para un punto.

        POWER acepta los 35 anios de la ventana sin trocear, comprobado contra el
        servicio, asi que aqui no hay particion por tramos.
        """
        respuesta = self._cliente.get(
            URL,
            params={
                "parameters": ",".join(PARAMETROS),
                "community": COMUNIDAD,
                "longitude": longitud,
                "latitude": latitud,
                "start": desde.strftime("%Y%m%d"),
                "end": hasta.strftime("%Y%m%d"),
                "format": "JSON",
            },
        )
        respuesta.raise_for_status()

        try:
            contenido = respuesta.json()
        except ValueError as error:
            raise ErrorPower(
                "POWER no devolvio JSON. Primeros 300 caracteres:\n" f"{respuesta.text[:300]}"
            ) from error

        if "properties" not in contenido:
            mensajes = contenido.get("messages") or contenido
            raise ErrorPower(f"POWER respondio sin datos: {mensajes}")

        _comprobar_unidades(contenido)

        cabecera = contenido.get("header", {})
        relleno = float(cabecera.get("fill_value", -999.0))
        coordenadas = contenido.get("geometry", {}).get("coordinates", [])
        elevacion = coordenadas[2] if len(coordenadas) > 2 else None

        series: dict[str, dict[date, float | None]] = {}
        crudas = contenido["properties"]["parameter"]

        for parametro in PARAMETROS:
            if parametro not in crudas:
                raise ErrorPower(f"POWER no devolvio el parametro {parametro}")
            # El valor de relleno se traduce a None. Nunca a cero: cero es una
            # medicion y ausencia de dato no lo es.
            series[parametro] = {
                _a_fecha(clave): (None if valor == relleno else float(valor))
                for clave, valor in crudas[parametro].items()
            }

        return RespuestaPower(
            url=str(respuesta.url),
            valor_relleno=relleno,
            elevacion=elevacion,
            version_api=cabecera.get("api", {}).get("version", "desconocida"),
            series=series,
        )
