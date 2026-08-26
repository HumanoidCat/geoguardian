"""
NASA FIRMS: focos de calor. Historia H1.2, issue #36.

DE DONDE SE BAJAN, Y POR QUE NO DE LA API

FIRMS publica dos caminos. El obvio es la API por area, que necesita una clave
gratuita y acepta **maximo cinco dias por peticion**: cubrir 2001-2024 serian unas
1.800 peticiones contra un tope de 5.000 transacciones cada diez minutos.

El que se usa aqui son los archivos anuales por pais, que no necesitan clave:

    https://firms.modaps.eosdis.nasa.gov/data/country/modis/2020/modis_2020_Costa_Rica.csv

Un archivo por producto y por anio. **Treinta y siete descargas en vez de mil
ochocientas peticiones**, y sin credencial que gestionar.

Dos limites medidos, no supuestos:

  - El archivo llega hasta **2024**. Para el anio en curso si hace falta la clave.
  - El servicio devuelve 502 de vez en cuando. Pasó en dos de los treinta y siete
    mientras se media R16, y se resolvio reintentando. Por eso este modulo nace
    con reintentos y no se los agrega despues, que es lo que le falto a H1.3.

DOS PRODUCTOS Y UN SALTO DE 2,1 VECES

MODIS desde 2000 con pixel de 1 km, VIIRS S-NPP desde 2012 con pixel de 375 m.
VIIRS ve fuegos mas pequenos, asi que el conteo salta al entrar:

    2001-2011, solo MODIS:     69 focos / 11 anios =  6,3 por anio
    2012-2024, MODIS + VIIRS: 173 focos / 13 anios = 13,3 por anio

Es del sensor, no del clima. Entra igual por D-25, porque sacarlo cuesta la mitad
de las ventanas positivas y con veinte no se valida ningun modelo. Cada foco
declara su producto para que aguas abajo se pueda separar.

LA CONFIANZA SE CONVIERTE HACIA LO GRUESO

MODIS la da como entero de 0 a 100 y VIIRS como categoria. Se colapsa MODIS a tres
clases y no al reves: expandir tres categorias a un numero seria inventar precision
que la fuente no da. Los cortes salen del manual del producto, no del equipo.

QUE DEVUELVE ESTE MODULO, Y POR QUE SON DOS COSAS

`extraer` cumple el contrato `ExtractorFocosCalor` y devuelve `FocoCalor`, que es
la forma acordada del proyecto. Pero ese esquema no tiene donde guardar el
producto, la banda de origen, la potencia radiativa ni la confianza categorica: su
campo `confianza` es un entero de 0 a 100, y VIIRS no tiene entero.

Por eso `descargar` devuelve `FocoBruto`, con todo lo que la fuente da, y es lo que
usa el cargador. Es la misma forma de H1.1: `ExtractorPower` devuelve un
`RespuestaPower` completo y solo el hibrido produce el tipo del contrato.

**Consecuencia declarada:** la vista del contrato pierde la confianza de VIIRS, que
queda nula porque no es un entero. En la base se guarda completa. Si el contrato
pasa a admitir la categoria, cambia solo `a_foco_calor`.
"""

from __future__ import annotations

import csv
import io
import time
from dataclasses import dataclass
from datetime import date

import httpx

from contratos.esquemas import FocoCalor

BASE = "https://firms.modaps.eosdis.nasa.gov/data/country"
PAIS = "Costa_Rica"

# Productos y el primer anio que publica cada uno. MODIS arranca en 2000 y VIIRS
# S-NPP el 20 de enero de 2012, segun la tabla de atributos de cada producto.
PRODUCTOS = {
    "modis": 2000,
    "viirs-snpp": 2012,
}

# Ultimo anio del archivo historico por pais, comprobado: 2025 devuelve 404.
ULTIMO_ANIO_ARCHIVO = 2024

# Cortes de confianza de MODIS a categoria.
#
#   Tabla 10 de: Giglio, Schroeder, Hall y Justice, MODIS Collection 6 Active Fire
#   Product User's Guide, Revision C. University of Maryland, diciembre de 2020.
#
#     0 %  <= C <  30 %   low
#     30 % <= C <  80 %   nominal
#     80 % <= C <= 100 %  high
#
# No son criterio del equipo: estan publicados y se citan.
CORTE_BAJA = 30
CORTE_ALTA = 80

# Las tres letras de VIIRS, de su tabla de atributos.
CATEGORIA_VIIRS = {"l": "baja", "n": "nominal", "h": "alta"}

# De que banda sale `brillo_k` en cada producto. Se emparejan por region
# espectral: MODIS canal 21/22 esta en 3,9 a 4 um y VIIRS I-4 en 3,55 a 3,93 um.
BANDA_ORIGEN = {"modis": "modis_21_22", "viirs-snpp": "viirs_i4"}

TIEMPO_LIMITE = 120.0
INTENTOS_MAXIMOS = 5


class ErrorFirms(Exception):
    """Falla al bajar de FIRMS. Detiene la descarga en vez de seguir a medias."""


@dataclass(frozen=True)
class FocoBruto:
    """
    Una deteccion con todo lo que la fuente da.

    Existe porque `FocoCalor` del contrato no tiene donde poner el producto, la
    banda, la potencia radiativa ni una confianza que no sea entera. Ver la
    cabecera del modulo.
    """

    producto: str
    satelite: str
    fecha: date
    hora_utc: int
    latitud: float
    longitud: float
    confianza: str
    confianza_bruta: int | None
    brillo_k: float | None
    brillo_largo_k: float | None
    banda_origen: str
    frp_mw: float | None
    tipo: int | None
    dia_noche: str | None

    def a_foco_calor(self, codigo_distrito: str | None = None) -> FocoCalor:
        """
        Traduce a la forma del contrato, que es mas pobre.

        `confianza` queda nula en VIIRS porque el contrato la declara entera de 0
        a 100 y VIIRS no da un entero. Poner 50 donde la fuente dice 'nominal'
        seria inventar precision. En la base se guarda la categoria, que si
        conserva la informacion.
        """
        return FocoCalor(
            fecha=self.fecha,
            latitud=self.latitud,
            longitud=self.longitud,
            confianza=self.confianza_bruta,
            brillo_k=self.brillo_k,
            satelite=self.satelite,
            codigo_distrito=codigo_distrito,
        )


def categoria_confianza(producto: str, crudo: str) -> tuple[str, int | None]:
    """
    Devuelve la categoria y, si existe, el entero original.

    MODIS se colapsa con los cortes publicados; VIIRS ya viene en categoria y solo
    se traduce el nombre. Nunca al reves: de tres clases no se puede volver a un
    numero.
    """
    if producto == "modis":
        entero = int(float(crudo))
        if entero < CORTE_BAJA:
            return "baja", entero
        if entero < CORTE_ALTA:
            return "nominal", entero
        return "alta", entero

    letra = crudo.strip().lower()
    if letra not in CATEGORIA_VIIRS:
        raise ErrorFirms(
            f"VIIRS devolvio una confianza que no es 'l', 'n' ni 'h': {crudo!r}. "
            "Su tabla de atributos declara solo esas tres."
        )
    return CATEGORIA_VIIRS[letra], None


def _numero(valor: str | None) -> float | None:
    if valor is None or valor.strip() == "":
        return None
    return float(valor)


class ExtractorFirms:
    """
    Cumple el protocolo `ExtractorFocosCalor`.

    **No hace analisis espacial.** Filtra por caja envolvente del area de estudio,
    que es una comparacion de numeros, y nada mas. La asignacion de cada foco a su
    distrito ocurre despues, en la capa que conoce las geometrias, como dice el
    contrato.
    """

    nombre = "NASA FIRMS: MODIS C6.1 y VIIRS S-NPP 375 m"

    def __init__(
        self,
        caja: tuple[float, float, float, float],
        cliente: httpx.Client | None = None,
        productos: tuple[str, ...] = ("modis", "viirs-snpp"),
    ) -> None:
        """
        `caja` es (oeste, sur, este, norte) en EPSG:4326.

        No se fija aqui: la calcula quien conoce las geometrias y se la pasa. Para
        Tilaran, medida sobre la capa del SNIT, es
        (-85.0468, 10.32079, -84.76609, 10.65175).
        """
        self.caja = caja
        self.productos = productos
        self._propio = cliente is None
        self._cliente = cliente or httpx.Client(timeout=TIEMPO_LIMITE, follow_redirects=True)

    def cerrar(self) -> None:
        if self._propio:
            self._cliente.close()

    def disponible(self) -> bool:
        """
        Comprueba que el archivo historico responda, sin bajarlo entero.

        Devuelve falso en vez de lanzar excepcion: el contrato dice que se llama
        antes de una ingesta larga para fallar temprano.
        """
        try:
            respuesta = self._cliente.head(self._url("modis", 2020), timeout=30.0)
            return respuesta.status_code == 200
        except httpx.HTTPError:
            return False

    def _url(self, producto: str, anio: int) -> str:
        return f"{BASE}/{producto}/{anio}/{producto}_{anio}_{PAIS}.csv"

    def _bajar(self, producto: str, anio: int, registrar=None) -> str:
        """
        Baja un archivo anual, reintentando ante fallas pasajeras.

        Existe porque pasó: dos de los treinta y siete archivos devolvieron 502
        mientras se media R16, y a la segunda funcionaron. Se comprueba tambien
        que el cuerpo sea el CSV esperado, porque el 502 llega con una pagina de
        error y codigo 200 no siempre significa datos.
        """
        url = self._url(producto, anio)
        for intento in range(INTENTOS_MAXIMOS):
            try:
                respuesta = self._cliente.get(url)
            except httpx.HTTPError as error:
                ultimo = f"{type(error).__name__}: {error}"
            else:
                if respuesta.status_code == 200 and "latitude" in respuesta.text[:200]:
                    if intento and registrar:
                        registrar(f"  {producto} {anio}: bien al intento {intento + 1}")
                    return respuesta.text
                ultimo = f"HTTP {respuesta.status_code}"

            if intento < INTENTOS_MAXIMOS - 1:
                if registrar:
                    registrar(f"  {producto} {anio}: {ultimo}, reintentando")
                time.sleep(2 * (intento + 1))

        raise ErrorFirms(
            f"No se pudo bajar {url} tras {INTENTOS_MAXIMOS} intentos. Ultimo: {ultimo}"
        )

    def _dentro(self, longitud: float, latitud: float) -> bool:
        oeste, sur, este, norte = self.caja
        return oeste <= longitud <= este and sur <= latitud <= norte

    def descargar(self, desde: date, hasta: date, registrar=None) -> list[FocoBruto]:
        """
        Baja los anios que cubren el rango y devuelve todo lo que la fuente da.

        Es el metodo que usa el cargador. `extraer` traduce esto a la forma del
        contrato, que es mas pobre.
        """
        if hasta < desde:
            raise ErrorFirms("El rango termina antes de empezar")

        if hasta.year > ULTIMO_ANIO_ARCHIVO:
            raise ErrorFirms(
                f"El archivo historico por pais llega hasta {ULTIMO_ANIO_ARCHIVO} y se "
                f"pidio hasta {hasta.year}. Para el anio en curso hace falta la MAP_KEY "
                "y la API por area, con su tope de cinco dias por peticion."
            )

        salida: list[FocoBruto] = []
        for producto in self.productos:
            primero = max(desde.year, PRODUCTOS[producto])
            for anio in range(primero, hasta.year + 1):
                texto = self._bajar(producto, anio, registrar)
                antes = len(salida)
                for fila in csv.DictReader(io.StringIO(texto)):
                    foco = self._leer(producto, fila)
                    if foco is None or not (desde <= foco.fecha <= hasta):
                        continue
                    salida.append(foco)
                if registrar:
                    registrar(f"  {producto} {anio}: {len(salida) - antes} en el area")
        return salida

    def _leer(self, producto: str, fila: dict) -> FocoBruto | None:
        """Traduce una fila del CSV. Devuelve None si cae fuera de la caja."""
        longitud, latitud = float(fila["longitude"]), float(fila["latitude"])
        if not self._dentro(longitud, latitud):
            return None

        categoria, bruta = categoria_confianza(producto, fila["confidence"])
        anio, mes, dia = (int(p) for p in fila["acq_date"].split("-"))

        return FocoBruto(
            producto=producto,
            satelite=fila["satellite"],
            fecha=date(anio, mes, dia),
            hora_utc=int(fila["acq_time"]),
            latitud=latitud,
            longitud=longitud,
            confianza=categoria,
            confianza_bruta=bruta,
            # MODIS nombra las bandas 'brightness' y 'bright_t31'; VIIRS,
            # 'bright_ti4' y 'bright_ti5'. Se emparejan por region espectral.
            brillo_k=_numero(fila.get("brightness") or fila.get("bright_ti4")),
            brillo_largo_k=_numero(fila.get("bright_t31") or fila.get("bright_ti5")),
            banda_origen=BANDA_ORIGEN[producto],
            frp_mw=_numero(fila.get("frp")),
            tipo=int(fila["type"]) if fila.get("type", "").strip() != "" else None,
            dia_noche=(fila.get("daynight") or "").strip() or None,
        )

    def extraer(self, desde: date, hasta: date) -> list[FocoCalor]:
        """
        Cumple el contrato. Devuelve la forma acordada, que pierde informacion.

        `codigo_distrito` queda nulo: el contrato dice que el filtrado por distrito
        ocurre despues, en la capa de repositorio, y que el extractor no hace
        analisis espacial.
        """
        return [bruto.a_foco_calor() for bruto in self.descargar(desde, hasta)]
