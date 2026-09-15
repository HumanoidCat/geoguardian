"""
Cache en memoria delante del repositorio. Dueno: Cesar. Historia H8.3, issue #65.

QUE ES

Un `Repositorio` que envuelve a otro `Repositorio`. Guarda en memoria lo que el
de adentro devolvio, con vencimiento por tiempo y tope de entradas, y responde
desde ahi mientras la entrada siga viva.

Ningun endpoint cambia. `rutas.py` depende del protocolo, y el envoltorio cumple
el protocolo: quien lo arma es `dependencias.py`, que ya era el unico archivo que
sabia cual implementacion esta activa. Eso es CA-2.

QUE SE CACHEA Y QUE NO, MEDIDO EN CA-1

Medicion del 2026-09-14, siete repeticiones, contra PostgreSQL real:

    endpoint                       consultas   mediana
    /distritos                             1   89.54 ms   <- entra
    /distritos/{codigo}                    1   39.39 ms   <- entra
    /distritos/{codigo}/mediciones         2   16.41 ms   <- NO
    /distritos/{codigo}/riesgo             2   11.13 ms   <- entra
    /riesgos                               1    2.71 ms   <- entra
    /salud                                 2    3.04 ms   <- NO

`obtener_mediciones` queda fuera porque su clave incluye un rango de fechas
libre: el espacio de claves no tiene techo y cada entrada es una serie entera.
Cachear eso es guardar mucho para acertar poco.

`esta_viva` y `ultima_ingesta` quedan fuera porque son el estado de AHORA. Una
respuesta guardada afirmaria una conexion viva que puede estar caida, que es
**I-41 otra vez por otro camino**: el campo diria lo que era cierto hace un rato.
Eso es CA-3.

LO QUE ESTA CACHE NO PUEDE AHORRAR, Y CONVIENE SABERLO ANTES DE MEDIR

CA-1 dejo un dato raro: `/distritos/{codigo}` tarda 39 ms, pero `/mediciones`
-que por dentro llama al mismo `obtener_distrito` **mas** su propia consulta-
tarda 16. La diferencia es que el primero **serializa la geometria en la
respuesta** y el segundo construye el `Distrito` para validar y lo descarta.

Esta cache vive por debajo de FastAPI: ahorra la consulta y la construccion del
modelo, **no** la serializacion de la respuesta. El techo de la ganancia en
`/distritos` es menor que sus 89 ms, y CA-10 tiene que decir cuanto.

SOBRE LA COPIA DE SALIDA

Lo guardado se devuelve copiado. Si se devolviera el mismo objeto, un consumidor
que ordene la lista o le agregue algo corromperia la cache para todas las
peticiones siguientes, y el defecto aparecerria lejos de su causa. Es CA-6.

La copia **cuesta**, y sobre ocho geometrias GeoJSON puede costar tanto como la
consulta que ahorra. Por eso `copiar` es un parametro: `medir_cache.py` corre la
comparacion con y sin copia, y la decision se toma con el numero. Si la copia se
come la ganancia, se declara; no se quita en silencio.

POR QUE EL SIMULADO NO SE ENVUELVE

`dependencias.modo_de` y `dependencias.base_conectada` preguntan
`isinstance(repositorio, RepositorioSimulado)`. Un envoltorio alrededor del
simulado **no es** un `RepositorioSimulado`, asi que /salud pasaria a responder
`modo: real` sirviendo datos inventados. Seria I-41 una tercera vez. La cache se
arma solo sobre el repositorio contra PostgreSQL, y `dependencias.py` es quien lo
garantiza.
"""

from __future__ import annotations

import copy
import os
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from contratos.enums import TipoEvento
from contratos.esquemas import Distrito, MedicionDiaria, Riesgo

# Vencimiento por omision, en segundos.
#
# Sale de la cadencia de ingesta, no del ojo. Por D-26 la fuente mas rapida es el
# incendio, que se ingesta **una vez al dia**; la sequia es semanal como mucho y
# el CHIRPS final llega con 21 a 51 dias de atraso (D-40). Cinco minutos estan
# dos ordenes de magnitud por debajo del dato que cambia mas seguido: el atraso
# que introduce esta cache es despreciable frente al atraso que el dato ya trae.
#
# Hacia el otro lado, una sesion del visor dura minutos, asi que cinco alcanzan
# para que la segunda pantalla que alguien abre pegue en cache.
#
# LO QUE ESTO SIGNIFICA, Y SE DECLARA: una respuesta puede venir con hasta
# TTL_SEGUNDOS de atraso respecto de la base. Es CA-11.
TTL_SEGUNDOS = 300.0

# Tope de entradas. `obtener_riesgo` tiene clave (distrito, fecha, evento), que
# crece sin techo si nadie lo acota: ocho distritos por tres eventos por cuantas
# fechas pidan. 256 cubre con holgura lo que el visor pide en una sesion -los
# ocho distritos, la lista, y los riesgos de unos pocos dias- y pone un techo al
# consumo, que es lo que CA-8 mide.
TOPE_ENTRADAS = 256

VARIABLE_ENCENDIDA = "GEOGUARDIAN_CACHE"
VARIABLE_TTL = "GEOGUARDIAN_CACHE_TTL"
VARIABLE_TOPE = "GEOGUARDIAN_CACHE_TOPE"

#: Marca de "no estaba". No se usa None porque **None es un valor legitimo**:
#: `obtener_riesgo` devuelve None cuando no hay estimacion, y esa ausencia es
#: justo lo que mas conviene cachear (CA-7). Sin este centinela, cachear una
#: ausencia y no tenerla serian indistinguibles.
AUSENTE = object()


class CacheConVencimiento:
    """
    Diccionario con vencimiento por tiempo, tope de entradas y desalojo LRU.

    El reloj se inyecta. Probar un vencimiento con `sleep` hace la prueba lenta y
    fragil; con un reloj falso se puede parar un segundo antes y un segundo
    despues del limite y ejercitar las dos ramas. Es CA-4.
    """

    def __init__(
        self,
        ttl: float = TTL_SEGUNDOS,
        tope: int = TOPE_ENTRADAS,
        reloj: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl <= 0:
            raise ValueError("El ttl tiene que ser positivo")
        if tope <= 0:
            raise ValueError("El tope tiene que ser positivo")

        self._ttl = ttl
        self._tope = tope
        self._reloj = reloj
        self._entradas: OrderedDict[Any, tuple[Any, float]] = OrderedDict()
        self._candado = threading.RLock()

        self.aciertos = 0
        self.fallos = 0
        self.vencidas = 0
        self.desalojadas = 0

    def __len__(self) -> int:
        with self._candado:
            return len(self._entradas)

    @property
    def claves(self) -> list:
        """Las claves vivas, de la menos usada recientemente a la mas."""
        with self._candado:
            return list(self._entradas.keys())

    def obtener(self, clave) -> Any:
        """Lo guardado, o `AUSENTE`. Una entrada vencida se descarta al leerla."""
        with self._candado:
            entrada = self._entradas.get(clave)
            if entrada is None:
                self.fallos += 1
                return AUSENTE

            valor, vence_en = entrada
            if self._reloj() >= vence_en:
                del self._entradas[clave]
                self.vencidas += 1
                self.fallos += 1
                return AUSENTE

            # Usar una entrada la vuelve la mas reciente: eso es lo que hace que
            # el desalojo sea LRU y no arbitrario.
            self._entradas.move_to_end(clave)
            self.aciertos += 1
            return valor

    def guardar(self, clave, valor) -> None:
        with self._candado:
            self._entradas[clave] = (valor, self._reloj() + self._ttl)
            self._entradas.move_to_end(clave)
            while len(self._entradas) > self._tope:
                self._entradas.popitem(last=False)
                self.desalojadas += 1

    def limpiar(self) -> None:
        with self._candado:
            self._entradas.clear()

    def resumen(self) -> str:
        with self._candado:
            total = self.aciertos + self.fallos
            tasa = (self.aciertos / total * 100) if total else 0.0
            return (
                f"entradas {len(self._entradas)}/{self._tope} · "
                f"aciertos {self.aciertos} · fallos {self.fallos} "
                f"({tasa:.1f} % de acierto) · vencidas {self.vencidas} · "
                f"desalojadas {self.desalojadas}"
            )


class RepositorioConCache:
    """
    Cumple el protocolo `Repositorio` y guarda en memoria lo que el de adentro devuelve.

    Cuatro metodos se cachean; el resto pasa tal cual. Los dos que alimentan
    /salud estan escritos explicitamente aunque solo deleguen, para que se vea en
    el codigo que no cachearlos es una decision y no un olvido.
    """

    def __init__(
        self,
        repositorio,
        cache: CacheConVencimiento | None = None,
        copiar: Callable[[Any], Any] | None = copy.deepcopy,
    ) -> None:
        self.envuelto = repositorio
        self.cache = cache if cache is not None else CacheConVencimiento()
        #: `None` desactiva la copia. **Solo para medir** (CA-6 vs CA-10): sin
        #: copia, quien reciba la respuesta puede corromper lo guardado.
        self._copiar = copiar

    def _con_cache(self, clave, producir):
        guardado = self.cache.obtener(clave)
        if guardado is not AUSENTE:
            return self._salida(guardado)

        valor = producir()
        self.cache.guardar(clave, valor)
        return self._salida(valor)

    def _salida(self, valor):
        if self._copiar is None or valor is None:
            return valor
        return self._copiar(valor)

    # -- Cacheados ---------------------------------------------------------- #

    def listar_distritos(self) -> list[Distrito]:
        return self._con_cache(("listar_distritos",), self.envuelto.listar_distritos)

    def obtener_distrito(self, codigo: str) -> Distrito | None:
        return self._con_cache(
            ("obtener_distrito", codigo),
            lambda: self.envuelto.obtener_distrito(codigo),
        )

    def obtener_riesgo(
        self, codigo_distrito: str, fecha: date, tipo_evento: TipoEvento
    ) -> Riesgo | None:
        # La ausencia se cachea igual que la presencia. Si no, un distrito sin
        # estimacion consulta la base en cada peticion, que es el caso mas
        # frecuente en incendio despues del 2024-12-24 (I-37, I-48). El 404 lo
        # sigue construyendo el endpoint: cachear un None no lo convierte en una
        # respuesta vacia, que seria romper D-07.
        return self._con_cache(
            ("obtener_riesgo", codigo_distrito, fecha, tipo_evento.value),
            lambda: self.envuelto.obtener_riesgo(codigo_distrito, fecha, tipo_evento),
        )

    def obtener_riesgos_por_fecha(self, fecha: date, tipo_evento: TipoEvento) -> list[Riesgo]:
        return self._con_cache(
            ("obtener_riesgos_por_fecha", fecha, tipo_evento.value),
            lambda: self.envuelto.obtener_riesgos_por_fecha(fecha, tipo_evento),
        )

    # -- No cacheados, a proposito ------------------------------------------ #

    def esta_viva(self) -> bool:
        """CA-3: el estado de ahora no se guarda. Ver la cabecera."""
        return self.envuelto.esta_viva()

    def ultima_ingesta(self) -> datetime | None:
        """CA-3: idem. Un valor guardado diria la hora de una ingesta vieja."""
        return self.envuelto.ultima_ingesta()

    def obtener_mediciones(
        self, codigo_distrito: str, desde: date, hasta: date
    ) -> list[MedicionDiaria]:
        """Clave sin techo y entradas grandes. Ver la cabecera."""
        return self.envuelto.obtener_mediciones(codigo_distrito, desde, hasta)

    # -- Todo lo demas pasa sin tocar --------------------------------------- #

    def __getattr__(self, nombre):
        # Solo se llama cuando el atributo no esta definido arriba. Las
        # escrituras del protocolo -guardar_mediciones, guardar_riesgos- llegan
        # aca y van derecho a la base: cachear una escritura no significa nada.
        return getattr(self.envuelto, nombre)


def cache_encendida() -> bool:
    """
    Encendida salvo que se diga lo contrario.

    Apagarla es como se mide la linea base (CA-12), y tambien la salida si algun
    dia la cache resultara ser el problema en vez de la solucion.
    """
    return os.getenv(VARIABLE_ENCENDIDA, "1").strip().lower() not in {"0", "false", "no"}


def crear_cache() -> CacheConVencimiento:
    """Arma la cache con los valores del entorno, o los declarados arriba."""

    def _numero(variable: str, por_omision: float) -> float:
        bruto = os.getenv(variable, "").strip()
        if not bruto:
            return por_omision
        try:
            return float(bruto)
        except ValueError as error:
            # No se cae de vuelta al valor por omision en silencio: una variable
            # mal escrita dejaria la cache con un vencimiento que nadie pidio y
            # nadie veria.
            raise ValueError(f"{variable}={bruto!r} no es un numero") from error

    return CacheConVencimiento(
        ttl=_numero(VARIABLE_TTL, TTL_SEGUNDOS),
        tope=int(_numero(VARIABLE_TOPE, TOPE_ENTRADAS)),
    )