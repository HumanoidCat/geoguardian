"""
Verificador de H8.2: ETL concurrente con medicion secuencial contra paralelo.

Criterios en docs/evidencias/sistemas-operativos/H8.2-criterios-aceptacion.md.
CA-1 a CA-8 corren **sin red y sin base**, y no contra un juguete que imite al
ETL: contra el ETL de verdad -`ingestar.correr`, `ExtractorFirmsArea`,
`ExtractorHibrido`- con un cliente HTTP falso que duerme y cuenta, y la
conexion falsa de H6.2 ampliada para anotar **desde que hilo** sale cada
sentencia. Los dobles de H1.14 se reutilizan en vez de copiarse.

CA-9 y CA-10 son la medicion contra las fuentes reales y viven en
`medir_concurrencia.py`; su salida va en la evidencia.

    python -m backend.etl.verificar_h82
"""

from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.etl import concurrencia, ingestar  # noqa: E402
from backend.etl.concurrencia import TRABAJADORES, mapear  # noqa: E402
from backend.etl.fuentes import firms_area  # noqa: E402
from backend.etl.fuentes.firms_area import ExtractorFirmsArea  # noqa: E402
from backend.etl.fuentes.hibrido import ExtractorHibrido, Territorio, celda_power  # noqa: E402
from backend.etl.fuentes.power import RespuestaPower  # noqa: E402
from backend.etl.verificar_h1_14 import ConexionIngesta, CursorConteo  # noqa: E402
from backend.modelado.verificar_h33 import Resultado  # noqa: E402
from contratos.esquemas import MedicionDiaria  # noqa: E402

HOY = date(2026, 9, 3)
AYER = HOY - timedelta(days=1)
CAJA = (-85.2, 10.2, -84.6, 10.8)
ESPERA = 0.05

# Ocho territorios que caen en la MISMA celda de POWER, como los de Tilaran.
TERRITORIOS = [
    Territorio(
        codigo=f"5080{i}",
        nombre=f"distrito {i}",
        geometria={},
        longitud=-84.95 + i * 0.01,
        latitud=10.45 + i * 0.01,
    )
    for i in range(1, 9)
]

CSV_MODIS = (
    "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,"
    "instrument,confidence,version,bright_t31,frp,daynight\n"
    "10.47,-84.97,320.1,1.0,1.0,{fecha},1830,Terra,MODIS,85,6.1NRT,300.0,5.0,D\n"
)


# --------------------------------------------------------------------------- #
# Dobles                                                                       #
# --------------------------------------------------------------------------- #


class CursorConHilo(CursorConteo):
    """Como el de H1.14, pero anota desde que hilo sale cada sentencia (CA-2)."""

    def execute(self, sql: str, parametros=None) -> None:
        self._conexion.hilos.append(threading.current_thread().name)
        super().execute(sql, parametros)

    def executemany(self, sql: str, secuencia) -> None:
        self._conexion.hilos.append(threading.current_thread().name)
        super().executemany(sql, secuencia)


class ConexionConHilos(ConexionIngesta):
    def __init__(self, resultados=None) -> None:
        super().__init__(resultados)
        self.hilos: list[str] = []
        self.momento_transaccion: float | None = None

    def cursor(self) -> CursorConHilo:
        return CursorConHilo(self)

    def transaction(self):
        if self.momento_transaccion is None:
            self.momento_transaccion = time.perf_counter()
        return super().transaction()


@dataclass
class Respuesta:
    status_code: int
    text: str


@dataclass
class ClienteFalso:
    """
    Imita lo que `ExtractorFirmsArea` usa de `httpx.Client`: `get` y `close`.

    Duerme para que la concurrencia se note, cuenta cuantas peticiones hay en
    vuelo a la vez -que es como se comprueba el tope- y anota el hilo y el
    momento de cada una.
    """

    espera: float = ESPERA
    invertir: bool = False
    falla_en: int | None = None
    peticiones: list[str] = field(default_factory=list)
    hilos: set[str] = field(default_factory=set)
    momentos: list[float] = field(default_factory=list)
    en_vuelo: int = 0
    maximo_en_vuelo: int = 0
    _candado: threading.Lock = field(default_factory=threading.Lock)

    def get(self, url: str, **_argumentos) -> Respuesta:
        with self._candado:
            self.en_vuelo += 1
            self.maximo_en_vuelo = max(self.maximo_en_vuelo, self.en_vuelo)
            indice = len(self.peticiones)
            self.peticiones.append(url)
            self.hilos.add(threading.current_thread().name)
        try:
            if "data_availability" in url:
                return Respuesta(
                    200,
                    "data_id,min_date,max_date\n"
                    "MODIS_SP,2000-11-01,2026-04-30\n"
                    "MODIS_NRT,2026-05-01,2026-09-03\n"
                    "VIIRS_SNPP_SP,2012-01-20,2026-04-27\n"
                    "VIIRS_SNPP_NRT,2026-04-28,2026-09-03\n",
                )
            if self.falla_en is not None and indice == self.falla_en:
                return Respuesta(503, "el servicio provoco un fallo")
            # Con `invertir`, las primeras peticiones son las mas lentas: si el
            # pool devolviera en orden de terminacion, el resultado saldria al
            # reves.
            espera = self.espera * (6 - min(indice, 5)) if self.invertir else self.espera
            time.sleep(espera)
            fecha = url.rstrip("/").split("/")[-1]
            with self._candado:
                self.momentos.append(time.perf_counter())
            return Respuesta(200, CSV_MODIS.format(fecha=fecha))
        finally:
            with self._candado:
                self.en_vuelo -= 1

    def close(self) -> None:
        pass


@dataclass
class PowerFalso:
    """Cuenta descargas. Es lo que hace visible el defecto de la cache (CA-7)."""

    espera: float = 0.1
    consultas: int = 0
    _candado: threading.Lock = field(default_factory=threading.Lock)

    def consultar(self, longitud: float, latitud: float, desde: date, hasta: date):
        with self._candado:
            self.consultas += 1
        time.sleep(self.espera)
        dias = {desde + timedelta(days=i): 25.0 for i in range((hasta - desde).days + 1)}
        return RespuestaPower(
            url="falsa",
            valor_relleno=-999.0,
            elevacion=381.0,
            version_api="falsa",
            series=dict.fromkeys(
                ("T2M_MAX", "T2M_MIN", "T2M", "RH2M", "WS2M", "ALLSKY_SFC_SW_DWN"), dias
            ),
        )

    def disponible(self) -> bool:
        return True

    def cerrar(self) -> None:
        pass


@dataclass
class ChirpsFalso:
    espera: float = 0.05
    consultas: int = 0
    _candado: threading.Lock = field(default_factory=threading.Lock)

    def consultar(self, geometria, desde: date, hasta: date) -> dict[date, float | None]:
        with self._candado:
            self.consultas += 1
        time.sleep(self.espera)
        return {desde + timedelta(days=i): 1.0 for i in range((hasta - desde).days + 1)}

    def disponible(self) -> bool:
        return True

    def cerrar(self) -> None:
        pass


@dataclass
class FuenteClimaConHilos:
    """Cumple ExtractorClima y anota desde que hilo se le pidio cada distrito."""

    nombre: str = "clima con hilos H8.2"
    hilos: set[str] = field(default_factory=set)
    _candado: threading.Lock = field(default_factory=threading.Lock)

    def disponible(self) -> bool:
        return True

    def extraer(self, codigo_distrito: str, desde: date, hasta: date):
        with self._candado:
            self.hilos.add(threading.current_thread().name)
        time.sleep(ESPERA)
        return [
            MedicionDiaria(
                codigo_distrito=codigo_distrito,
                fecha=desde + timedelta(days=i),
                precipitacion_mm=1.0,
            )
            for i in range((hasta - desde).days + 1)
        ]

    def cerrar(self) -> None:
        pass


class CandadoDeMentira:
    """Un candado que no cierra nada. Sirve para medir el defecto que el de verdad evita."""

    def __enter__(self):
        return self

    def __exit__(self, *_excepcion) -> bool:
        return False


def extractor_firms(cliente: ClienteFalso) -> ExtractorFirmsArea:
    return ExtractorFirmsArea(CAJA, clave="clave-de-prueba", cliente=cliente, productos=("modis",))


def cola_incendio(dias_atras: int = 60) -> ConexionConHilos:
    """
    La cola de respuestas de una corrida de incendio.

    Con una corrida anterior que llego hasta `dias_atras`, la ventana es corta y
    el verificador no tarda un minuto en cada comprobacion. Son doce tramos de
    cinco dias: suficiente para que cuatro trabajadores se noten.
    """
    ultima = (datetime.combine(HOY, datetime.min.time(), UTC), HOY - timedelta(dias_atras))
    return ConexionConHilos(resultados=[[ultima], [(7,)], [(None, None)]])


def correr_incendio(conexion, extractor, trabajadores: int) -> ingestar.Corrida:
    """Una corrida real de incendio contra los dobles."""
    return ingestar.correr(
        conexion, "incendio", HOY, lambda *_: None, extractor=extractor, trabajadores=trabajadores
    )


def escritas(conexion) -> list[dict]:
    return [
        fila for evento in conexion.sentencias() if evento[0] == "executemany" for fila in evento[2]
    ]


# --------------------------------------------------------------------------- #
# Criterios                                                                    #
# --------------------------------------------------------------------------- #


def verificar() -> Resultado:
    r = Resultado()

    print("CA-1 · La concurrencia esta donde esta el tiempo: la descarga, no la escritura")
    cliente = ClienteFalso()
    conexion = cola_incendio()
    corrida = correr_incendio(conexion, extractor_firms(cliente), TRABAJADORES)
    r.comprobar("la corrida termino bien", corrida.estado == "exitosa", corrida.mensaje)
    r.comprobar(
        "toda peticion de red ocurrio ANTES de abrir la transaccion",
        bool(cliente.momentos)
        and conexion.momento_transaccion is not None
        and max(cliente.momentos) < conexion.momento_transaccion,
    )
    r.comprobar(
        "descargar y escribir son dos funciones distintas, no una sola",
        callable(ingestar.descargar_focos) and callable(ingestar.escribir_focos),
    )

    print("CA-2 · Ningun hilo escribe en PostgreSQL")
    r.comprobar(
        "todas las sentencias salieron del hilo principal",
        set(conexion.hilos) == {threading.current_thread().name},
        str(set(conexion.hilos)),
    )
    r.comprobar("y la descarga si uso varios hilos", len(cliente.hilos) > 1, str(cliente.hilos))

    print("CA-3 · Secuencial y paralelo producen el mismo resultado")
    cliente_uno = ClienteFalso()
    conexion_uno = cola_incendio()
    correr_incendio(conexion_uno, extractor_firms(cliente_uno), 1)
    cliente_varios = ClienteFalso()
    conexion_varios = cola_incendio()
    correr_incendio(conexion_varios, extractor_firms(cliente_varios), TRABAJADORES)
    r.comprobar(
        "las filas escritas son identicas, en el mismo orden",
        escritas(conexion_uno) == escritas(conexion_varios),
    )
    r.comprobar(
        "y son las mismas peticiones, aunque el orden de respuesta cambie",
        sorted(cliente_uno.peticiones) == sorted(cliente_varios.peticiones),
    )
    r.comprobar(
        "el trabajo comparado no fue trivial",
        len(cliente_uno.peticiones) > 10,
        f"{len(cliente_uno.peticiones)} peticiones",
    )

    print("CA-4 · El orden del resultado es el de entrada, no el de terminacion")
    cliente_invertido = ClienteFalso(invertir=True)
    conexion_invertida = cola_incendio()
    correr_incendio(conexion_invertida, extractor_firms(cliente_invertido), 6)
    fechas = [f["fecha"] for f in escritas(conexion_invertida)]
    r.comprobar(
        "las fechas salen ordenadas aunque las primeras peticiones sean las mas lentas",
        len(fechas) > 5 and fechas == sorted(fechas),
        str(fechas[:3]),
    )

    print("CA-5 · Un fallo se propaga y no deja una lista incompleta")
    # Un solo intento: el reintento de FIRMS espera 2, 4 y 6 segundos, y aqui se
    # comprueba la propagacion del fallo, no la paciencia del cliente.
    intentos = firms_area.INTENTOS_MAXIMOS
    firms_area.INTENTOS_MAXIMOS = 1
    try:
        cliente_roto = ClienteFalso(falla_en=3)
        conexion_rota = cola_incendio()
        corrida_rota = correr_incendio(conexion_rota, extractor_firms(cliente_roto), TRABAJADORES)
    finally:
        firms_area.INTENTOS_MAXIMOS = intentos
    r.comprobar(
        "la corrida queda fallida con el motivo, no exitosa a medias",
        corrida_rota.estado == "fallida" and "FIRMS" in corrida_rota.mensaje,
        corrida_rota.mensaje,
    )
    r.comprobar("y no se escribio ninguna fila", not escritas(conexion_rota))

    corridas: list[int] = []
    candado = threading.Lock()

    def falla_la_primera(numero: int) -> int:
        if numero == 0:
            raise ValueError("provocado")
        time.sleep(ESPERA)
        with candado:
            corridas.append(numero)
        return numero

    try:
        mapear(falla_la_primera, range(20), trabajadores=2)
        propago = False
    except ValueError:
        propago = True
    r.comprobar("la excepcion llega a quien llama", propago)
    r.comprobar(
        "las tareas que no habian empezado no corren", len(corridas) < 19, f"{len(corridas)} de 19"
    )

    print("CA-6 · Secuencial es secuencial de verdad")
    r.comprobar(
        "con un trabajador todo corre en el hilo que llama",
        cliente_uno.hilos == {threading.current_thread().name},
        str(cliente_uno.hilos),
    )
    _, medicion = mapear(time.sleep, [0.01] * 3, trabajadores=1)
    r.comprobar("y la medicion lo declara", medicion.trabajadores == 1 and len(medicion.hilos) == 1)

    print("CA-7 · El estado compartido esta protegido, y el defecto se demuestra")
    desde, hasta = date(2026, 8, 1), date(2026, 8, 3)
    celdas = {celda_power(t.longitud, t.latitud) for t in TERRITORIOS}
    r.comprobar(
        "los ocho territorios caen en una sola celda de POWER", len(celdas) == 1, str(celdas)
    )

    sin_candado = PowerFalso()
    hibrido_roto = ExtractorHibrido(
        TERRITORIOS, power=sin_candado, chirps=ChirpsFalso(), registrar=lambda *_: None
    )
    hibrido_roto._candado_power = CandadoDeMentira()
    mapear(lambda t: hibrido_roto.extraer(t.codigo, desde, hasta), TERRITORIOS, trabajadores=8)
    r.comprobar(
        "sin candado la cache se pierde: POWER recibe mas de una peticion",
        sin_candado.consultas > 1,
        f"{sin_candado.consultas} peticiones",
    )

    con_candado = PowerFalso()
    hibrido = ExtractorHibrido(
        TERRITORIOS, power=con_candado, chirps=ChirpsFalso(), registrar=lambda *_: None
    )
    resultados, _ = mapear(
        lambda t: hibrido.extraer(t.codigo, desde, hasta), TERRITORIOS, trabajadores=8
    )
    r.comprobar(
        "con candado vuelve a ser una sola, como en secuencial",
        con_candado.consultas == 1,
        f"{con_candado.consultas} peticiones",
    )
    r.comprobar(
        "y el resultado sigue siendo uno por distrito y dia",
        [len(m) for m in resultados] == [3] * 8,
    )
    lineas: list[str] = []
    registrar = concurrencia.serializar(lineas.append)
    mapear(lambda i: registrar(f"linea {i}"), range(8), trabajadores=4)
    r.comprobar("la bitacora concurrente no pierde ni parte lineas", len(lineas) == 8)

    print("CA-8 · El tope es un dato declarado y se respeta")
    r.comprobar(
        "el tope por omision del guion es el declarado en concurrencia.py",
        ingestar.trabajadores_de(ingestar.analizador().parse_args([])) == TRABAJADORES,
    )
    r.comprobar(
        "--secuencial es un trabajador",
        ingestar.trabajadores_de(ingestar.analizador().parse_args(["--secuencial"])) == 1,
    )
    r.comprobar(
        "y nunca hay menos de uno",
        ingestar.trabajadores_de(ingestar.analizador().parse_args(["--trabajadores", "0"])) == 1,
    )
    cliente_tope = ClienteFalso()
    correr_incendio(cola_incendio(), extractor_firms(cliente_tope), TRABAJADORES)
    r.comprobar(
        "nunca hubo mas peticiones en vuelo que el tope",
        1 < cliente_tope.maximo_en_vuelo <= TRABAJADORES,
        f"maximo en vuelo {cliente_tope.maximo_en_vuelo}, tope {TRABAJADORES}",
    )
    # El hilo principal tambien pide -la consulta de disponibilidad sale de el,
    # antes de repartir nada-, asi que se descuenta: lo que se comprueba es
    # cuantos hilos abrio el pool, no cuantos hilos hubo.
    del_pool = cliente_tope.hilos - {threading.current_thread().name}
    r.comprobar(
        "el pool tampoco abre mas hilos que el tope",
        0 < len(del_pool) <= TRABAJADORES,
        f"{len(del_pool)} hilos del pool, tope {TRABAJADORES}",
    )

    # Ajuste que trajo la medicion de CA-9: el tope no es uno solo para todo el
    # ETL, porque las dos fuentes no se comportan igual. ClimateSERV encola
    # -cada tarea pasa de 6.18 s a 20.27 s con cuatro en vuelo-, asi que la
    # precipitacion va de a una aunque se pida mas.
    r.comprobar(
        "cada fuente declara lo que admite: precipitacion de a una, focos al tope",
        ingestar.EN_VUELO["lluvia_intensa"] == 1
        and ingestar.EN_VUELO["sequia"] == 1
        and ingestar.EN_VUELO["incendio"] is None,
        str(ingestar.EN_VUELO),
    )
    clima = FuenteClimaConHilos()
    territorios = TERRITORIOS[:4]
    conexion_lluvia = ConexionIngesta(resultados=[[], [(HOY - timedelta(days=5),)], [(9,)]])
    corrida_lluvia = ingestar.correr(
        conexion_lluvia,
        "lluvia_intensa",
        HOY,
        lambda *_: None,
        extractor=clima,
        territorios=territorios,
        trabajadores=8,
    )
    r.comprobar(
        "y pedir ocho no hace que la precipitacion salga en paralelo",
        corrida_lluvia.estado == "exitosa" and clima.hilos == {threading.current_thread().name},
        str(clima.hilos),
    )

    return r


def main() -> int:
    resultado = verificar()
    print(f"\n{resultado.hechos - len(resultado.fallos)} de {resultado.hechos} criterios")
    if resultado.fallos:
        print("\nNO se cumplen:")
        for fallo in resultado.fallos:
            print(f"  - {fallo}")
        print()
        return 1
    print("\nH8.2 cumple CA-1 a CA-8. CA-9 y CA-10 son la medicion real: medir_concurrencia.py.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
