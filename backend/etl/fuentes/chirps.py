"""
CHIRPS via ClimateSERV: precipitacion. Historia H1.1, issue #35.

POR QUE ESTA FUENTE Y NO POWER

Decision D-15. Los dos eventos que definen los umbrales del charter, sequia por
SPI-6 y lluvia intensa por acumulado de 72 h, se calculan sobre precipitacion.
POWER no sirve para eso: su celda cubre el canton entero y daria el mismo valor en
los ocho distritos. CHIRPS trabaja a 0,05 grados, unos 5,5 km, y cada distrito cae
en su propia celda.

Comprobado del 1 al 7 de setiembre de 2024: los valores difieren todos los dias
entre distritos, con 20,3 % entre el acumulado mayor y el menor, y el orden cambia
de un dia a otro. Un sesgo constante del metodo daria siempre el mismo orden.

TRES COSAS QUE SE COMPROBARON CONTRA EL SERVICIO

**1. El maximo por peticion son 20 anios.** Responde literalmente
`"Max date range is: 20 years"`. La ventana 1991-2025 son 35, asi que se trocea.

**2. El poligono no cabe en la URL.** Los distritos vienen del SNIT a escala
1:5000; Tilaran tiene 24.515 vertices. Simplificado a la unica tolerancia que
conserva sus celdas, sigue pesando 8 KB y nginx responde
`414 Request-URI Too Large`.

**3. Pero el servicio acepta POST.** Con el poligono en el cuerpo no hay limite de
tamano, asi que se envia el contorno completo sin simplificar. La consulta
`basedatos/consultas/poligonos_simplificados.sql` queda en el repositorio como
evidencia de por que se descarto simplificar.

EL PROTOCOLO ES EN DOS PASOS

Se envia la peticion y devuelve un identificador; despues se consulta el resultado
con ese identificador. El calculo se encola, asi que hay que esperar y reintentar.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import date

import httpx

BASE = "https://climateserv.servirglobal.net/chirps"
ENVIAR = f"{BASE}/submitDataRequest/"
RECOGER = f"{BASE}/getDataFromRequest/"

# Catalogo de ClimateSERV, comprobado en la pagina de la API el 2026-09-03:
# 0 es "UCSB CHIRPS Rainfall", el producto final con estaciones; 90 es
# "UCSB CHIRP Rainfall", el mismo algoritmo SIN la correccion por estaciones.
# El catalogo NO ofrece el "CHIRPS preliminar" del que habla D-26 (ese lo
# publica CHC en GeoTIFF). Y medido ese mismo dia, el 90 llega DESPUES que el
# 0 (junio contra julio), asi que no sirve como preliminar: la ingesta carga
# el 0 (D-40). El 90 queda disponible, declarado, por si algun dia adelanta.
TIPO_DATO = "0"
TIPO_DATO_CHIRP = "90"
PRODUCTOS = {TIPO_DATO: "chirps", TIPO_DATO_CHIRP: "chirp"}
# Operacion 5: promedio sobre el poligono. Es lo que representa a un distrito que
# abarca varias celdas.
OPERACION_PROMEDIO = "5"

# Tope del servicio, comprobado. Se deja en 19 para no rozar el limite cuando el
# rango incluye anios bisiestos.
ANIOS_POR_TRAMO = 19

TIEMPO_LIMITE = 180.0
ESPERA_ENTRE_INTENTOS = 3.0
INTENTOS_MAXIMOS = 40


class ErrorChirps(Exception):
    """Falla al consultar CHIRPS. Detiene la descarga en vez de seguir a medias."""


@dataclass(frozen=True)
class TramoChirps:
    """Un tramo de la serie, con su rastro."""

    desde: date
    hasta: date
    identificador: str
    valores: dict[date, float | None]
    nulos: int


def trocear(desde: date, hasta: date) -> list[tuple[date, date]]:
    """
    Parte el rango en tramos que el servicio acepta.

    Devuelve tramos contiguos y sin solapamiento: el dia siguiente al fin de uno
    es el inicio del siguiente. Si se solaparan, la carga escribiria dos veces las
    mismas fechas.
    """
    if hasta < desde:
        raise ErrorChirps("El rango termina antes de empezar")

    tramos: list[tuple[date, date]] = []
    inicio = desde
    while inicio <= hasta:
        try:
            limite = date(inicio.year + ANIOS_POR_TRAMO, inicio.month, inicio.day)
        except ValueError:
            # 29 de febrero en un anio destino no bisiesto.
            limite = date(inicio.year + ANIOS_POR_TRAMO, inicio.month, 28)
        fin = min(limite, hasta)
        tramos.append((inicio, fin))
        inicio = date.fromordinal(fin.toordinal() + 1)
    return tramos


class ExtractorChirps:
    """
    Consulta CHIRPS sobre un poligono. No cumple `ExtractorClima` por si solo: lo
    hace el extractor hibrido, que combina esta fuente con POWER.
    """

    nombre = "CHIRPS 2.0 via ClimateSERV"

    def __init__(self, cliente: httpx.Client | None = None, tipo_dato: str = TIPO_DATO) -> None:
        if tipo_dato not in PRODUCTOS:
            raise ErrorChirps(
                f"Tipo de dato {tipo_dato!r} no esta en el catalogo conocido: "
                f"{sorted(PRODUCTOS)}"
            )
        # H1.14: que producto pide este cliente. Se declara al construirlo para
        # que cada fila escrita pueda decir de cual vino.
        self.tipo_dato = tipo_dato
        self.producto = PRODUCTOS[tipo_dato]
        self._propio = cliente is None
        self._cliente = cliente or httpx.Client(timeout=TIEMPO_LIMITE, follow_redirects=True)

    def cerrar(self) -> None:
        if self._propio:
            self._cliente.close()

    def disponible(self) -> bool:
        """
        Comprueba conectividad pidiendo un solo dia sobre un cuadro minimo.

        Devuelve falso en vez de lanzar excepcion: el contrato dice que se llama
        antes de una ingesta larga para fallar temprano.
        """
        cuadro = {
            "type": "Polygon",
            "coordinates": [
                [
                    [-84.95, 10.48],
                    [-84.94, 10.48],
                    [-84.94, 10.49],
                    [-84.95, 10.49],
                    [-84.95, 10.48],
                ]
            ],
        }
        try:
            identificador = self._enviar(cuadro, date(2024, 1, 1), date(2024, 1, 1))
            return bool(identificador)
        except (httpx.HTTPError, ErrorChirps):
            return False

    def _enviar(self, geometria: dict, desde: date, hasta: date) -> str:
        """
        Encola una peticion y devuelve su identificador.

        Va por POST y no por GET: con el poligono completo la URL supera el limite
        de nginx y responde 414. En el cuerpo no hay limite de tamano.
        """
        respuesta = self._cliente.post(
            ENVIAR,
            data={
                "datatype": self.tipo_dato,
                "begintime": desde.strftime("%m/%d/%Y"),
                "endtime": hasta.strftime("%m/%d/%Y"),
                "intervaltype": "0",
                "operationtype": OPERACION_PROMEDIO,
                "dateType_Category": "default",
                "isZip_CurrentDataType": "false",
                "geometry": json.dumps(geometria),
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        respuesta.raise_for_status()

        try:
            cuerpo = respuesta.json()
        except ValueError as error:
            raise ErrorChirps(
                f"ClimateSERV no devolvio JSON al encolar:\n{respuesta.text[:300]}"
            ) from error

        if not isinstance(cuerpo, list) or not cuerpo:
            raise ErrorChirps(f"ClimateSERV no devolvio identificador: {cuerpo}")

        # Cuando algo no le gusta, devuelve el identificador y un aviso al lado.
        # El caso conocido es el tope de anios, y hay que tratarlo como fallo.
        if len(cuerpo) > 1:
            raise ErrorChirps(f"ClimateSERV rechazo la peticion: {cuerpo[1:]}")

        return str(cuerpo[0])

    def _recoger(self, identificador: str) -> list[dict]:
        """Consulta el resultado, esperando mientras el calculo esta encolado."""
        for intento in range(INTENTOS_MAXIMOS):
            respuesta = self._cliente.get(RECOGER, params={"id": identificador})
            respuesta.raise_for_status()

            try:
                cuerpo = respuesta.json()
            except ValueError:
                cuerpo = {}

            datos = cuerpo.get("data") if isinstance(cuerpo, dict) else None
            if datos:
                return datos

            if intento < INTENTOS_MAXIMOS - 1:
                time.sleep(ESPERA_ENTRE_INTENTOS)

        raise ErrorChirps(
            f"ClimateSERV no entrego el resultado {identificador} tras "
            f"{INTENTOS_MAXIMOS * ESPERA_ENTRE_INTENTOS:.0f} segundos"
        )

    def consultar_tramo(self, geometria: dict, desde: date, hasta: date) -> TramoChirps:
        """Descarga un tramo, que ya debe caber en el tope del servicio."""
        identificador = self._enviar(geometria, desde, hasta)
        datos = self._recoger(identificador)

        valores: dict[date, float | None] = {}
        nulos = 0

        for fila in datos:
            try:
                dia = date(int(fila["year"]), int(fila["month"]), int(fila["day"]))
            except (KeyError, TypeError, ValueError) as error:
                raise ErrorChirps(f"Fila sin fecha utilizable: {fila}") from error

            crudo = fila.get("value", {})
            valor = crudo.get("avg") if isinstance(crudo, dict) else fila.get("raw_value")

            # ClimateSERV reporta la fraccion sin dato en el campo NaN. Un valor
            # negativo tambien es ausencia: la lluvia no puede serlo.
            sin_dato = valor is None or (isinstance(valor, int | float) and valor < 0)
            if sin_dato:
                nulos += 1
                valores[dia] = None
            else:
                valores[dia] = float(valor)

        return TramoChirps(
            desde=desde, hasta=hasta, identificador=identificador, valores=valores, nulos=nulos
        )

    def consultar(self, geometria: dict, desde: date, hasta: date) -> dict[date, float | None]:
        """
        Descarga el rango completo, troceandolo segun el tope del servicio.

        Los tramos son contiguos y no se solapan, asi que unirlos no puede
        producir una fecha con dos valores distintos.
        """
        completo: dict[date, float | None] = {}
        for inicio, fin in trocear(desde, hasta):
            tramo = self.consultar_tramo(geometria, inicio, fin)
            repetidas = set(tramo.valores) & set(completo)
            if repetidas:
                raise ErrorChirps(
                    f"Los tramos se solapan en {len(repetidas)} fechas. "
                    "El troceado esta mal y la union no seria fiable."
                )
            completo.update(tramo.valores)
        return completo
