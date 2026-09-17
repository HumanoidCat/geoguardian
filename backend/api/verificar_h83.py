"""
Verificador de H8.3, la parte que necesita PostgreSQL. Dueno: Cesar. Issue #65.

USO

    python -m backend.api.verificar_h83           CA-8, CA-9, CA-10 y CA-12
    python -m backend.api.verificar_h83 --ca3     CA-3, que pide detener la base

POR QUE ESTE ARCHIVO NO COMPRUEBA LOS DOCE CRITERIOS

CA-1 a CA-7 y CA-12 los comprueba `pytest backend/api/test_cache.py`, sin base y
sin red. Repetirlos aca dejaria **dos controles para la misma propiedad**: en
cuanto uno cambie, el otro queda viejo y sigue diciendo CUMPLE. Un control de mas
no es mas evidencia. El ajuste esta escrito y fechado en el archivo de criterios.

Lo que queda aca es lo que pytest no puede hacer porque necesita la base real.
"""

from __future__ import annotations

import argparse
import copy
import statistics
import subprocess
import sys
import time
import tracemalloc
from datetime import date, timedelta

from backend.api.cache import CacheConVencimiento, RepositorioConCache, copia_de_lista
from backend.api.medir_cache import ConexionContadora
from backend.api.repositorio_postgres import RepositorioPostgres
from basedatos.conexion import conectar
from contratos.enums import TipoEvento

REPETICIONES = 7

#: Cuantos dias hacia atras se piden por distrito al medir la familia `riesgo`.
#: Con ocho distritos son 240 entradas, que entran en el tope de 256 sin desalojar:
#: si desalojara, la medicion contaria menos de lo que dice contar.
DIAS_DE_RIESGO = 30


class Resultado:
    """Mismo formato que los demas verificadores del proyecto."""

    def __init__(self) -> None:
        self.filas: list[tuple[str, bool, str]] = []

    def marcar(self, criterio: str, cumple: bool, detalle: str = "") -> None:
        self.filas.append((criterio, cumple, detalle))

    def imprimir(self) -> bool:
        for criterio, cumple, detalle in self.filas:
            print(f"{criterio}: {'CUMPLE' if cumple else 'FALLA'}")
            if detalle:
                for linea in detalle.split("\n"):
                    print(f"    {linea}")
        return all(cumple for _, cumple, _ in self.filas)


def _repetir(llamada) -> list[float]:
    """Una llamada de calentamiento que se descarta, y REPETICIONES que cuentan."""
    llamada()
    tiempos = []
    for _ in range(REPETICIONES):
        arranque = time.perf_counter()
        llamada()
        tiempos.append((time.perf_counter() - arranque) * 1000)
    return tiempos


def _resumen(tiempos: list[float]) -> str:
    return (
        f"mediana {statistics.median(tiempos):.2f} ms, "
        f"rango {min(tiempos):.2f}-{max(tiempos):.2f}"
    )


def _mb(bytes_: int) -> float:
    return bytes_ / (1024 * 1024)


# -- CA-8: cuanto ocupa la cache, por familia de clave ---------------------- #


def ca8_consumo(resultado: Resultado, crudo) -> None:
    """
    El techo se mide por FAMILIA DE CLAVE, no llenando el tope.

    La primera version de esta comprobacion guardaba la respuesta mas grande bajo
    256 claves sinteticas y declaraba 1622 MB. **Ese numero era ficticio**: ese
    estado no puede ocurrir. El espacio de claves de las geometrias esta acotado
    por el canton -una entrada para `listar_distritos` y una por distrito, y
    distritos hay ocho- y lo que si tiene muchas claves, `obtener_riesgo`, tiene
    entradas diminutas.

    Contar entradas no acota memoria cuando los tamanios difieren en cuatro
    ordenes de magnitud. Lo que acota la memoria es el espacio de claves de lo
    pesado, y por eso el techo se arma sumando familias reales.

    Se mide con `tracemalloc`, que cuenta lo que Python reservo de verdad;
    `sys.getsizeof` sobre una estructura anidada solo mide el envoltorio.
    """
    repositorio = RepositorioConCache(crudo, CacheConVencimiento(ttl=3600.0, tope=256))
    distritos = crudo.listar_distritos()
    evento = next(iter(TipoEvento))
    hoy = date.today()

    tracemalloc.start()
    base = tracemalloc.get_traced_memory()[0]

    repositorio.listar_distritos()
    for distrito in distritos:
        repositorio.obtener_distrito(distrito.codigo)
    geometrias = tracemalloc.get_traced_memory()[0] - base
    entradas_geometria = len(repositorio.cache)

    marca = tracemalloc.get_traced_memory()[0]
    for distrito in distritos:
        for dias in range(DIAS_DE_RIESGO):
            repositorio.obtener_riesgo(distrito.codigo, hoy - timedelta(days=dias), evento)
    riesgos = tracemalloc.get_traced_memory()[0] - marca
    entradas_totales = len(repositorio.cache)
    tracemalloc.stop()

    entradas_riesgo = entradas_totales - entradas_geometria
    total = geometrias + riesgos

    # Que no haya desalojado importa: si hubiera desalojado, lo medido seria
    # menos que lo declarado y el numero mentiria por lo bajo.
    sin_desalojar = repositorio.cache.desalojadas == 0

    resultado.marcar(
        "CA-8 el techo de la cache esta medido por familia de clave",
        total > 0 and sin_desalojar,
        f"geometrias: {entradas_geometria} entradas (1 lista + {len(distritos)} distritos) "
        f"= {_mb(geometrias):.2f} MB\n"
        f"riesgos:    {entradas_riesgo} entradas ({len(distritos)} distritos x "
        f"{DIAS_DE_RIESGO} dias) = {_mb(riesgos):.2f} MB\n"
        f"TECHO POR PROCESO: {_mb(total):.2f} MB con {entradas_totales} entradas vivas\n"
        f"desalojadas durante la medicion: {repositorio.cache.desalojadas} "
        f"(si fuera >0 el numero contaria de menos)\n"
        f"el espacio de claves de las geometrias esta acotado por el canton: "
        f"no puede crecer",
    )


# -- CA-9: el techo es por proceso ------------------------------------------ #


GUION_OTRO_PROCESO = (
    "import sys; sys.path.insert(0, '.');"
    "from backend.api.cache import CacheConVencimiento;"
    "print(len(CacheConVencimiento()))"
)


def ca9_por_proceso(resultado: Resultado, repositorio_con_cache) -> None:
    """
    Un proceso nuevo arranca con la cache vacia. Eso ES el techo por proceso.

    Se demuestra lanzando otro interprete y preguntandole cuantas entradas tiene
    su cache recien construida. Si la cache fuera compartida entre procesos, ahi
    apareceria lo que este proceso ya guardo.

    LIMITE DECLARADO. Esto demuestra que el estado no cruza de proceso a proceso,
    que es la propiedad de la que depende el techo. **No se levanto `uvicorn` con
    dos trabajadores**: no hace falta para establecer la propiedad, y montarlo
    agregaria un despliegue a una comprobacion que se resuelve con dos procesos.
    Lo que se afirma es que con N trabajadores hay N caches y el techo de CA-8 se
    multiplica por N; no se afirma haber medido un uvicorn de dos.
    """
    repositorio_con_cache.listar_distritos()
    aqui = len(repositorio_con_cache.cache)

    salida = subprocess.run(
        [sys.executable, "-c", GUION_OTRO_PROCESO],
        capture_output=True,
        text=True,
        timeout=60,
    )
    alla = salida.stdout.strip()

    resultado.marcar(
        "CA-9 la cache vive en el proceso: otro proceso arranca vacio",
        aqui > 0 and alla == "0",
        f"en este proceso: {aqui} entrada(s) - en un proceso nuevo: {alla}\n"
        f"con N trabajadores de uvicorn hay N caches y el techo de CA-8 se multiplica por N\n"
        f"no se midio un uvicorn de dos trabajadores: se establece la propiedad, "
        f"no el despliegue",
    )


# -- CA-10: la ganancia, y lo que cada estrategia de copia cuesta ----------- #


def ca10_ganancia(resultado: Resultado, conexion_contadora) -> None:
    """
    El mismo trabajo por cuatro caminos, siete repeticiones cada uno.

    1. sin cache                 -> va a la base cada vez
    2. con cache, copia de lista -> lo que este sistema hace hoy
    3. con cache, copia profunda -> la primera decision, que la medicion descarto
    4. con cache, sin copia      -> el piso teorico; NO es una configuracion
                                    proponible, porque permite corromper lo
                                    guardado

    Los cuatro se informan aunque solo el segundo sea el de produccion: el camino
    hasta la decision es parte de lo que esta historia demuestra, y sin el numero
    del tercero la eleccion del segundo seria una opinion.
    """
    crudo = RepositorioPostgres(conexion=conexion_contadora)

    def _armar(copiar):
        return RepositorioConCache(crudo, CacheConVencimiento(ttl=3600.0, tope=256), copiar=copiar)

    sin = _repetir(crudo.listar_distritos)
    lista = _repetir(_armar(copia_de_lista).listar_distritos)
    profunda = _repetir(_armar(copy.deepcopy).listar_distritos)
    ninguna = _repetir(_armar(None).listar_distritos)

    mediana_sin = statistics.median(sin)
    mediana_lista = statistics.median(lista)
    mediana_profunda = statistics.median(profunda)

    ahorro = mediana_sin - mediana_lista
    porcentaje = (ahorro / mediana_sin * 100) if mediana_sin else 0.0

    resultado.marcar(
        "CA-10 la ganancia esta medida repetida y declarada con su limite",
        mediana_lista < mediana_sin,
        f"listar_distritos, {REPETICIONES} repeticiones cada uno\n"
        f"  sin cache:                 {_resumen(sin)}\n"
        f"  con cache, copia de lista: {_resumen(lista)}   <- produccion\n"
        f"  con cache, copia profunda: {_resumen(profunda)}   <- descartada\n"
        f"  con cache, sin copia:      {_resumen(ninguna)}   <- piso, no proponible\n"
        f"ahorro: {ahorro:.2f} ms ({porcentaje:.1f} %)\n"
        f"la copia profunda costaba {mediana_profunda - statistics.median(ninguna):.2f} ms, "
        f"mas que los {mediana_sin:.2f} ms de la consulta que ahorra: por eso se descarto\n"
        f"LIMITE: esto mide la capa del repositorio. La serializacion de la\n"
        f"respuesta que hace FastAPI no la ahorra ninguna cache que viva aca\n"
        f"abajo: en CA-1 /distritos costaba 89.54 ms de punta a punta y el\n"
        f"repositorio explica solo {mediana_sin:.2f} de esos milisegundos",
    )


# -- CA-12: apagada, el sistema se comporta como antes ---------------------- #


def ca12_interruptor(resultado: Resultado, conexion_contadora) -> None:
    """Con la cache apagada, el conteo de consultas vuelve a ser el de la linea base."""
    crudo = RepositorioPostgres(conexion=conexion_contadora)
    con_cache = RepositorioConCache(crudo, CacheConVencimiento(ttl=3600.0, tope=256))

    conexion_contadora.consultas = 0
    for _ in range(3):
        crudo.listar_distritos()
    apagada = conexion_contadora.consultas

    conexion_contadora.consultas = 0
    for _ in range(3):
        con_cache.listar_distritos()
    encendida = conexion_contadora.consultas

    resultado.marcar(
        "CA-12 apagada consulta igual que antes de H8.3; encendida, una sola vez",
        apagada == 3 and encendida == 1,
        f"tres llamadas iguales - sin cache: {apagada} consultas - con cache: {encendida}",
    )


# -- CA-3: el estado de ahora no se guarda ---------------------------------- #


def ca3_base_caida() -> int:
    """
    El unico criterio que pide intervencion: hay que detener PostgreSQL a mano.

    Se llena la cache con la base viva, se espera a que la detengas, y se mira
    que /distritos siga respondiendo desde memoria mientras /salud **deja de
    afirmar que la base esta conectada**. Si /salud siguiera diciendo que si,
    seria I-41 otra vez: un campo que dice lo que era cierto hace un rato.
    """
    from fastapi.testclient import TestClient

    from backend.api.aplicacion import crear_aplicacion
    from backend.api.dependencias import obtener_repositorio

    repositorio = RepositorioConCache(
        RepositorioPostgres(conexion=conectar(autocommit=True)),
        CacheConVencimiento(ttl=3600.0, tope=256),
    )
    aplicacion = crear_aplicacion()
    aplicacion.dependency_overrides[obtener_repositorio] = lambda: repositorio
    cliente = TestClient(aplicacion)

    salud_viva = cliente.get("/salud").json()
    distritos_vivos = cliente.get("/distritos")
    print(
        f"Con la base viva - /salud base_datos_conectada: " f"{salud_viva['base_datos_conectada']}"
    )
    print(
        f"Con la base viva - /distritos: {distritos_vivos.status_code}, "
        f"{len(distritos_vivos.json())} distritos, ya en cache"
    )
    print()
    input("Deteni PostgreSQL en otra ventana (docker compose stop db) y presiona Enter... ")
    print()

    resultado = Resultado()

    respuesta = cliente.get("/distritos")
    resultado.marcar(
        "CA-3a con la base caida, /distritos sigue respondiendo desde la cache",
        respuesta.status_code == 200 and len(respuesta.json()) == len(distritos_vivos.json()),
        f"estado {respuesta.status_code}",
    )

    # /salud puede responder 200 diciendo que no hay base, o fallar ruidosamente.
    # Las dos son honestas. Lo unico inaceptable es un 200 afirmando que si.
    try:
        salud = cliente.get("/salud")
        miente = salud.status_code == 200 and salud.json().get("base_datos_conectada") is True
        detalle = f"estado {salud.status_code}, cuerpo {salud.json()}"
    except Exception as error:  # noqa: BLE001
        miente = False
        detalle = f"/salud fallo ruidosamente: {type(error).__name__}: {error}"

    resultado.marcar(
        "CA-3b con la base caida, /salud no afirma que la base esta conectada",
        not miente,
        detalle + "\nfallar ruidosamente tambien es honesto; mentir en 200 no",
    )

    todo = resultado.imprimir()
    print()
    print("CA-3 cumple." if todo else "CA-3 falla.")
    return 0 if todo else 1


def principal() -> int:
    analizador = argparse.ArgumentParser(description="Verificador de H8.3 contra PostgreSQL")
    analizador.add_argument(
        "--ca3",
        action="store_true",
        help="Corre solo CA-3, que pide detener la base a mano",
    )
    argumentos = analizador.parse_args()

    if argumentos.ca3:
        return ca3_base_caida()

    contadora = ConexionContadora(conectar(autocommit=True))
    crudo = RepositorioPostgres(conexion=contadora)
    con_cache = RepositorioConCache(crudo, CacheConVencimiento(ttl=3600.0, tope=256))

    resultado = Resultado()
    ca8_consumo(resultado, crudo)
    ca9_por_proceso(resultado, con_cache)
    ca10_ganancia(resultado, contadora)
    ca12_interruptor(resultado, contadora)

    todo_cumple = resultado.imprimir()
    print()
    print("Los cuatro criterios de base cumplen." if todo_cumple else "Hay criterios que fallan.")
    print("CA-3 se corre aparte: python -m backend.api.verificar_h83 --ca3")
    print("CA-1 a CA-7 y CA-12 sin base: pytest backend/api/test_cache.py")
    return 0 if todo_cumple else 1


if __name__ == "__main__":
    raise SystemExit(principal())
