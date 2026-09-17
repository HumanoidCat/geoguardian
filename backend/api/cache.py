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

LO QUE ESTA CACHE NO PUEDE AHORRAR

CA-1 dejo un dato raro: `/distritos/{codigo}` tarda 39 ms, pero `/mediciones`
-que por dentro llama al mismo `obtener_distrito` **mas** su propia consulta-
tarda 16. CA-10 lo confirmo con numeros: `listar_distritos` en el repositorio
cuesta 32.68 ms y el endpoint completo costaba 89.54. **Los otros 56 ms son la
serializacion de la respuesta que hace FastAPI**, y ninguna cache que viva por
debajo de FastAPI la ahorra.

SOBRE LA COPIA DE SALIDA, Y LO QUE LA MEDICION OBLIGO A CAMBIAR

Lo guardado se devuelve copiado, porque si se devolviera el mismo objeto un
consumidor que ordene la lista o la vacie corromperia la cache para todas las
peticiones siguientes, y el defecto aparecerria lejos de su causa. Es CA-6.

**La primera version copiaba en profundidad, y estaba mal.** Medido el
2026-09-15, siete repeticiones, `listar_distritos`:

    sin cache                    32.68 ms
    con cache, copia profunda    75.96 ms
    con cache, sin copia          0.00 ms

Copiar en profundidad ocho geometrias GeoJSON cuesta **76 ms**; traerlas de
PostgreSQL cuesta **33**. La cache era 43 ms mas lenta que no tenerla. La
decision se tomo al reves de como se habia escrito, y la cambio la medicion.

Hoy se copia **solo la lista**: `list(valor)` cuesta microsegundos y protege
contra lo que un consumidor le puede hacer al contenedor -vaciarlo, ordenarlo,
agregarle elementos-. Los modelos van compartidos, y los esquemas de
`contratos/` estan congelados, asi que nadie puede reasignarles un campo.

**LIMITE DECLARADO.** Congelar impide reasignar un atributo, no modificar por
dentro lo que ese atributo apunta. `Distrito.geometria` es un diccionario y
admite claves nuevas. Quien haga `distrito.geometria["type"] = "x"` corrompe lo
guardado. Se acepta a sabiendas: evitarlo cuesta 76 ms por peticion, que es mas
que la consulta que esta cache existe para ahorrar. Hay una prueba que deja el
vector escrito y avisa si alguien cambia la estrategia de copia.

POR QUE EL SIMULADO NO SE ENVUELVE

`dependencias.modo_de` y `dependencias.base_conectada` preguntan
`isinstance(repositorio, RepositorioSimulado)`. Un envoltorio alrededor del
simulado **no es** un `RepositorioSimulado`, asi que /salud pasaria a responder
`modo: real` sirviendo datos inventados. Seria I-41 una tercera vez. La cache se
arma solo sobre el repositorio contra PostgreSQL, y `dependencias.py` es quien lo
garantiza.
"""

from __future__ import annotations

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

# Tope de entradas.
#
# ACOTA EL NUMERO DE ENTRADAS, NO LA MEMORIA, Y ESA DISTINCION IMPORTA. Las
# entradas de este sistema difieren en cuatro ordenes de magnitud: la lista de
# geometrias pesa megabytes y un riesgo pesa bytes. Contar entradas no acota
# memoria; lo que acota la memoria es que **el espacio de claves de lo pesado es
# chico**: una entrada para `listar_distritos` y ocho para `obtener_distrito`,
# porque el canton tiene ocho distritos y no va a tener mas.
#
# El tope existe por `obtener_riesgo`, cuya clave es (distrito, fecha, evento) y
# si crece sin limite. Esas entradas son diminutas. CA-8 mide el techo por
# familia de clave, que es la unica forma de que el numero signifique algo.
TOPE_ENTRADAS = 256

VARIABLE_ENCENDIDA = "GEOGUARDIAN_CACHE"
VARIABLE_TTL = "GEOGUARDIAN_CACHE_TTL"
VARIABLE_TOPE = "GEOGUARDIAN_CACHE_TOPE"

#: Marca de "no estaba". No se usa None porque **None es un valor legitimo**:
#: `obtener_riesgo` devuelve None cuando no hay estimacion, y esa ausencia es
#: justo lo que mas conviene cachear (CA-7). Sin este centinela, cachear una
#: ausencia y no tenerla serian indistinguibles.
AUSENTE = object()


def copia_de_lista(valor: Any) -> Any:
    """
    Copia el contenedor y comparte lo de adentro.

    Es la estrategia de copia por omision, elegida con la medicion de CA-10 a la
    vista. Ver la cabecera del modulo: copiar en profundidad costaba mas que la
    consulta que la cache ahorra.

    Lo que protege: vaciar, ordenar o ampliar la lista devuelta no toca la que
    quedo guardada. Lo que no protege, y esta declarado: modificar por dentro un
    campo mutable de un modelo, como el diccionario de `geometria`.
    """
    if isinstance(valor, list):
        return list(valor)
    return valor


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
                f"entradas {len(self._entradas)}/{self._tope} - "
                f"aciertos {self.aciertos} - fallos {self.fallos} "
                f"({tasa:.1f} % de acierto) - vencidas {self.vencidas} - "
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
        copiar: Callable[[Any], Any] | None = copia_de_lista,
    ) -> None:
        self.envuelto = repositorio
        self.cache = cache if cache is not None else CacheConVencimiento()
        #: `None` desactiva la copia. **Solo para medir y para el sabotaje de
        #: CA-6**: sin copia, quien reciba la respuesta puede corromper lo
        #: guardado. `copy.deepcopy` tambien se puede pasar, y CA-10 lo mide.
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
