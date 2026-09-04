"""
NASA FIRMS por la API de area: el anio en curso. Historia H1.14 (Alejandro, D-38).

POR QUE UN SEGUNDO CLIENTE DE FIRMS

`firms.py` (H1.2) baja los archivos anuales por pais, que no piden clave y
**terminan en 2024** (comprobado: 2025 devuelve 404). Para lo que paso desde
entonces solo existe la API por area, que necesita `FIRMS_MAP_KEY` y acepta
**cinco dias por peticion** (documentacion de la API, leida el 2026-09-03).
Este modulo es ese camino. No reemplaza al otro: el historico sigue viniendo
del archivo, que es una sola descarga por anio en vez de setenta peticiones.

DOS PRODUCTOS POR SENSOR, Y ESO ES LO QUE H1.14 EXISTE PARA DECLARAR

La API sirve cada sensor en dos versiones:

    MODIS_NRT / VIIRS_SNPP_NRT   near real time: llega en ~3 h (D-26)
    MODIS_SP  / VIIRS_SNPP_SP    standard processing: la version definitiva,
                                 que llega semanas o meses despues

No son el mismo dato: el reprocesamiento cambia geolocalizacion y confianza.
Es la misma pareja preliminar/final de CHIRPS, y se trata igual: el NRT entra
declarado como `modis-nrt` / `viirs-snpp-nrt` en `crudo.foco_calor.producto`,
y cuando el SP cubre esos dias, lo reemplaza. Hasta donde llega cada uno lo
dice el servicio mismo (`data_availability`), no una constante.

La clave se lee del entorno y **nunca se imprime ni viaja en un mensaje de
error**: las URL de esta API la llevan adentro, asi que los errores muestran
la fuente y el codigo HTTP, no la URL.
"""

from __future__ import annotations

import csv
import io
import os
import time
from dataclasses import replace
from datetime import date, timedelta

import httpx

from contratos.esquemas import FocoCalor

from .firms import ErrorFirms, ExtractorFirms, FocoBruto

BASE = "https://firms.modaps.eosdis.nasa.gov/api"
DIAS_POR_PETICION = 5
TIEMPO_LIMITE = 60.0
INTENTOS_MAXIMOS = 4

# Producto base del proyecto -> fuente de la API por version. El codigo con el
# que entra a la base es el producto base para el final y `<base>-nrt` para el
# preliminar; los dos estan en crudo.producto_foco desde la migracion 013.
FUENTES: dict[str, dict[str, str]] = {
    "modis": {"final": "MODIS_SP", "preliminar": "MODIS_NRT"},
    "viirs-snpp": {"final": "VIIRS_SNPP_SP", "preliminar": "VIIRS_SNPP_NRT"},
}
SUFIJO_PRELIMINAR = "-nrt"


def codigo_producto(base: str, preliminar: bool) -> str:
    return f"{base}{SUFIJO_PRELIMINAR}" if preliminar else base


def trocear(desde: date, hasta: date, dias: int = DIAS_POR_PETICION) -> list[tuple[date, date]]:
    """Tramos contiguos y sin solapamiento, como `chirps.trocear`, de `dias` como mucho."""
    if hasta < desde:
        raise ErrorFirms("El rango termina antes de empezar")
    tramos: list[tuple[date, date]] = []
    inicio = desde
    while inicio <= hasta:
        fin = min(inicio + timedelta(days=dias - 1), hasta)
        tramos.append((inicio, fin))
        inicio = fin + timedelta(days=1)
    return tramos


class ExtractorFirmsArea:
    """
    Cumple `ExtractorFocosCalor` (`extraer` trae el NRT de los dos sensores).

    Lo que usa la ingesta es `descargar`, que devuelve `FocoBruto` con producto
    y version declarados, y `disponibilidad`, que dice hasta que dia sirve cada
    version segun el propio servicio.
    """

    nombre = "NASA FIRMS, API por area: MODIS y VIIRS S-NPP, NRT y SP"

    def __init__(
        self,
        caja: tuple[float, float, float, float],
        clave: str | None = None,
        cliente: httpx.Client | None = None,
        productos: tuple[str, ...] = ("modis", "viirs-snpp"),
    ) -> None:
        self.caja = caja
        self.productos = productos
        self._clave = (clave if clave is not None else os.environ.get("FIRMS_MAP_KEY", "")).strip()
        if not self._clave:
            raise ErrorFirms(
                "Falta FIRMS_MAP_KEY. La API por area de FIRMS no sirve sin clave; "
                "el archivo por pais no cubre el anio en curso."
            )
        self._propio = cliente is None
        self._cliente = cliente or httpx.Client(timeout=TIEMPO_LIMITE, follow_redirects=True)
        # Reusa la traduccion de filas de H1.2: misma caja, mismos cortes.
        self._lector = ExtractorFirms(caja, cliente=self._cliente, productos=productos)
        self._disponibilidad: dict[tuple[str, str], tuple[date, date]] | None = None

    def cerrar(self) -> None:
        if self._propio:
            self._cliente.close()

    # -- disponibilidad ------------------------------------------------------ #

    def _pedir(self, ruta: str, que: str) -> str:
        """GET con reintentos. Los mensajes no llevan la URL: lleva la clave."""
        ultimo = ""
        for intento in range(INTENTOS_MAXIMOS):
            try:
                respuesta = self._cliente.get(f"{BASE}/{ruta}")
            except httpx.HTTPError as error:
                ultimo = type(error).__name__
            else:
                if respuesta.status_code == 200 and not respuesta.text.lstrip().startswith("<"):
                    return respuesta.text
                ultimo = f"HTTP {respuesta.status_code}: {respuesta.text[:80]!r}"
            if intento < INTENTOS_MAXIMOS - 1:
                time.sleep(2 * (intento + 1))
        raise ErrorFirms(
            f"FIRMS no respondio a {que} tras {INTENTOS_MAXIMOS} intentos. Ultimo: {ultimo}"
        )

    def disponibilidad(self) -> dict[tuple[str, str], tuple[date, date]]:
        """
        Hasta que dia sirve cada version, segun `data_availability` del servicio.

        Devuelve {(producto_base, "final"|"preliminar"): (primer_dia, ultimo_dia)}.
        Se consulta una vez por instancia: la ingesta la usa para decidir que
        dias pide en SP y cuales en NRT, y para saber que NRT ya puede reemplazar.
        """
        if self._disponibilidad is not None:
            return self._disponibilidad

        texto = self._pedir(f"data_availability/csv/{self._clave}/ALL", "data_availability")
        por_fuente: dict[str, tuple[date, date]] = {}
        for fila in csv.DictReader(io.StringIO(texto)):
            try:
                por_fuente[fila["data_id"]] = (
                    date.fromisoformat(fila["min_date"]),
                    date.fromisoformat(fila["max_date"]),
                )
            except (KeyError, ValueError) as error:
                raise ErrorFirms(f"data_availability con una fila inesperada: {fila}") from error

        salida: dict[tuple[str, str], tuple[date, date]] = {}
        for base in self.productos:
            for version, fuente in FUENTES[base].items():
                if fuente in por_fuente:
                    salida[(base, version)] = por_fuente[fuente]
        if not salida:
            raise ErrorFirms(
                f"data_availability no lista ninguna de {sorted(FUENTES)}; "
                f"trajo {sorted(por_fuente)}"
            )
        self._disponibilidad = salida
        return salida

    def disponible(self) -> bool:
        try:
            return bool(self.disponibilidad())
        except ErrorFirms:
            return False

    # -- descarga ------------------------------------------------------------ #

    def descargar(
        self, desde: date, hasta: date, base: str, preliminar: bool, registrar=None
    ) -> list[FocoBruto]:
        """
        Baja un producto base en una version, en tramos de cinco dias.

        Los focos salen con `producto` ya declarado (`modis` o `modis-nrt`), que
        es lo que la base guarda y lo que permite reemplazar despues.
        """
        if base not in FUENTES:
            raise ErrorFirms(f"Producto {base!r} desconocido; conocidos: {sorted(FUENTES)}")
        fuente = FUENTES[base]["preliminar" if preliminar else "final"]
        codigo = codigo_producto(base, preliminar)
        oeste, sur, este, norte = self.caja
        area = f"{oeste},{sur},{este},{norte}"

        salida: list[FocoBruto] = []
        for inicio, fin in trocear(desde, hasta):
            dias = (fin - inicio).days + 1
            texto = self._pedir(
                f"area/csv/{self._clave}/{fuente}/{area}/{dias}/{inicio.isoformat()}",
                f"{fuente} {inicio}..{fin}",
            )
            antes = len(salida)
            for fila in csv.DictReader(io.StringIO(texto)):
                foco = self._lector._leer(base, fila)
                if foco is None or not (inicio <= foco.fecha <= fin):
                    continue
                salida.append(replace(foco, producto=codigo))
            if registrar:
                registrar(f"  {codigo} {inicio}..{fin}: {len(salida) - antes} en la caja")
        return salida

    def extraer(self, desde: date, hasta: date) -> list[FocoCalor]:
        """Cumple el contrato: el NRT de todos los productos, en la forma acordada."""
        focos: list[FocoCalor] = []
        for base in self.productos:
            focos += [f.a_foco_calor() for f in self.descargar(desde, hasta, base, preliminar=True)]
        return focos
