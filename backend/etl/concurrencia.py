"""
Pool acotado para la parte del ETL que espera por la red. Historia H8.2.
Dueno: Alejandro, por D-38 (la historia era de Cesar).

QUE PROBLEMA RESUELVE, MEDIDO ANTES DE ESCRIBIRSE

El ETL hace dos cosas muy distintas: **espera a la red** y **escribe en
PostgreSQL**. En las corridas reales de H1.14, registradas en
`control.bitacora_etl`, casi todo el reloj se va esperando: 244 peticiones de
cinco dias a FIRMS, y ocho consultas a ClimateSERV que **se encolan del lado
del servidor** y hay que reintentar cada tres segundos. La escritura de esas
mismas corridas son dos `executemany` que tardan menos de un segundo.

Por eso lo concurrente es la **descarga**, y la escritura sigue donde estaba:
en el hilo principal, en una transaccion por lote. Esa transaccion es lo que
sostiene la idempotencia de H1.1 y H1.14; repartirla entre hilos seria cambiar
una garantia por segundos.

POR QUE HILOS Y NO `asyncio`

Un trabajo que espera por la red no necesita corrutinas para dejar de esperar:
necesita que otra peticion avance mientras esta espera, y eso lo hace un hilo
bloqueado en `recv` igual de bien. Pasar el proyecto a `asyncio` obligaria a
reescribir los tres extractores, sus pruebas y los dos cargadores para ganar lo
mismo. El GIL no estorba aca **porque el tiempo no es de CPU**: un hilo que
espera por la red lo suelta. Donde si estorba es en el trabajo de CPU, y eso se
mide aparte en `medir_concurrencia.py` en vez de esconderse (CA-10).

`httpx.Client` se comparte entre hilos a proposito: su mantenedor declara que
es seguro y que **una sola instancia rinde mejor** que una por hilo, porque
comparte el pool de conexiones (discusion encode/httpx#1633; la documentacion
publicada no lo dice, asi que queda citada la fuente que si lo dice). Su pool
por omision admite 100 conexiones, muy por encima del tope de aqui.

LO QUE ESTE MODULO GARANTIZA

  * **El orden del resultado es el de entrada**, nunca el de terminacion.
  * **Un fallo se propaga**, y se propaga siempre el mismo: el de la tarea de
    menor indice. Un error que cambia de una corrida a otra no se puede
    reproducir.
  * **Con un trabajador no hay hilos**: el tiempo base no paga un costo que el
    paralelo tampoco paga. Sin esto la comparacion mentiria a favor del pool.
  * **Se mide sola**: cada llamada devuelve cuanto tardo, cuanto tardo cada
    tarea y en cuantos hilos corrio. La medicion de H8.2 no es un guion aparte
    que imita al ETL: es el ETL informando.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import FIRST_EXCEPTION, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from typing import TypeVar

E = TypeVar("E")
R = TypeVar("R")

# Tope de peticiones en vuelo. Es un dato declarado, no un numero de la suerte
# (CA-8):
#
#   * **CHIRPS/ClimateSERV no publica un limite de concurrencia.** Ante una
#     fuente publica y gratuita que no dice cuanto aguanta, el equipo no lo
#     averigua a la fuerza. Ocho distritos con cuatro en vuelo son dos rondas.
#   * **FIRMS si lo publica**: 5 000 transacciones cada diez minutos. Las 244
#     peticiones de una corrida completa de incendio no lo rozan ni con el tope
#     mas alto, asi que el limite de aqui no sale de FIRMS.
#   * El numero se eligio **midiendo**, no suponiendo: `medir_concurrencia.py`
#     corre la escalera 1, 2, 4, 8 sobre el trabajo real y la evidencia de la
#     historia trae los tiempos. Subirlo requiere volver a medir.
TRABAJADORES = 4


@dataclass(frozen=True)
class Medicion:
    """Lo que costo una tanda. Es lo que compara `medir_concurrencia.py`."""

    etiqueta: str
    trabajadores: int
    tareas: int
    segundos: float
    por_tarea: tuple[float, ...] = ()
    hilos: frozenset[str] = field(default_factory=frozenset)

    @property
    def suma_de_tareas(self) -> float:
        """Cuanto habria tardado en serie, sumando lo que tardo cada tarea."""
        return sum(self.por_tarea)

    @property
    def aceleracion(self) -> float:
        """Cuanto se gano contra la suma de las tareas. 1.0 es no haber ganado nada."""
        return self.suma_de_tareas / self.segundos if self.segundos > 0 else 0.0

    def __str__(self) -> str:
        return (
            f"{self.etiqueta}: {self.tareas} tareas con {self.trabajadores} "
            f"trabajador{'es' if self.trabajadores != 1 else ''} en "
            f"{self.segundos:.2f} s (suma de tareas {self.suma_de_tareas:.2f} s, "
            f"x{self.aceleracion:.2f}, {len(self.hilos)} hilos)"
        )


def _cronometrar(funcion: Callable[[E], R], elemento: E) -> tuple[R, float, str]:
    inicio = time.perf_counter()
    valor = funcion(elemento)
    return valor, time.perf_counter() - inicio, threading.current_thread().name


def mapear(
    funcion: Callable[[E], R],
    elementos: Iterable[E],
    trabajadores: int = 1,
    etiqueta: str = "",
) -> tuple[list[R], Medicion]:
    """
    Aplica `funcion` a cada elemento y devuelve los resultados **en el orden de entrada**.

    Con `trabajadores <= 1` corre en el hilo que llama, sin crear pool: es el
    tiempo base de la comparacion y tiene que estar limpio de costos que el
    paralelo no tenga.

    Si una tarea lanza una excepcion, se cancelan las que no empezaron y se
    relanza **la de menor indice**, no la primera en fallar por reloj: dos
    corridas del mismo trabajo roto tienen que dar el mismo error.
    """
    items: Sequence[E] = list(elementos)
    arranque = time.perf_counter()

    if trabajadores <= 1 or len(items) <= 1:
        resultados: list[R] = []
        duraciones: list[float] = []
        for elemento in items:
            valor, duracion, _ = _cronometrar(funcion, elemento)
            resultados.append(valor)
            duraciones.append(duracion)
        return resultados, Medicion(
            etiqueta=etiqueta,
            trabajadores=1,
            tareas=len(items),
            segundos=time.perf_counter() - arranque,
            por_tarea=tuple(duraciones),
            hilos=frozenset({threading.current_thread().name}),
        )

    en_vuelo = min(trabajadores, len(items))
    with ThreadPoolExecutor(max_workers=en_vuelo, thread_name_prefix="etl") as pool:
        futuros: list[Future] = [pool.submit(_cronometrar, funcion, e) for e in items]
        wait(futuros, return_when=FIRST_EXCEPTION)

        # Lo que todavia no empezo no empieza. `cancel()` devuelve False para lo
        # que ya esta corriendo: a eso se lo espera, no se lo mata a mitad.
        if any(f.done() and f.exception() is not None for f in futuros):
            for futuro in futuros:
                futuro.cancel()

        # Esta busqueda y el `futuro.result()` de mas abajo hacen lo mismo, y la
        # redundancia es a proposito: la descubrio un sabotaje que paso en verde
        # -tragarse el error aca no cambiaba nada, porque `result()` lo vuelve a
        # lanzar-. Se conservan las dos porque no son identicas en un caso: si
        # una tarea anterior quedo cancelada, `result()` levantaria
        # `CancelledError` y taparia el error de verdad. Esta pasada lo impide.
        fallo: BaseException | None = None
        for futuro in futuros:
            if futuro.cancelled():
                continue
            error = futuro.exception()
            if error is not None:
                fallo = error
                break
        if fallo is not None:
            raise fallo

        salida: list[R] = []
        duraciones = []
        hilos: set[str] = set()
        for futuro in futuros:
            valor, duracion, hilo = futuro.result()
            salida.append(valor)
            duraciones.append(duracion)
            hilos.add(hilo)

    return salida, Medicion(
        etiqueta=etiqueta,
        trabajadores=en_vuelo,
        tareas=len(items),
        segundos=time.perf_counter() - arranque,
        por_tarea=tuple(duraciones),
        hilos=frozenset(hilos),
    )


def serializar(registrar: Callable[..., None]) -> Callable[..., None]:
    """
    Envuelve la bitacora para que dos hilos no escriban la misma linea encimados.

    `bitacora.abrir` hace `print` y luego `write` + `flush`. Son tres
    operaciones, y nada garantiza que otro hilo no se meta entre ellas: sin
    esto, la evidencia de una corrida concurrente sale con lineas partidas por
    la mitad. Es el mismo defecto que I-06 en otra forma -la salida que nadie
    mira hasta que hace falta-, y cuesta un candado.
    """
    candado = threading.Lock()

    def registrar_serializado(*partes: object) -> None:
        with candado:
            registrar(*partes)

    return registrar_serializado
