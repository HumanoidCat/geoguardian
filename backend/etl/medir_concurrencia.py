"""
Medicion de H8.2: el mismo trabajo del ETL, en secuencial y en paralelo.

CA-9 y CA-10 de la historia. Lo que se mide **es el ETL**, no una imitacion:
llama a los mismos extractores que usa `ingestar.py`, con las mismas fuentes,
sobre una ventana acotada. Por eso el numero significa algo.

QUE MIDE, Y POR QUE ESAS TRES COSAS

  1. **FIRMS por area** (`--firms`): la descarga de una ventana en tramos de
     cinco dias. Es el lote mas grande del ETL -244 peticiones en la corrida
     completa de H1.14- y el que mas se beneficia.
  2. **CHIRPS por distrito** (`--chirps`): ocho consultas que el servicio
     **encola**, y que se cobran esperando. Necesita la base para leer las
     geometrias; no escribe nada.
  3. **Trabajo de CPU** (siempre): leer y convertir filas de CSV, que es lo
     unico del ETL que no espera por la red. Se mide para poder decir donde el
     paralelismo **no** ayuda, en vez de informar solo lo que salio bien.

NO ESCRIBE EN LA BASE. Una medicion que ademas escribe no se puede repetir sin
cambiar el estado, y entonces la segunda corrida ya no mide lo mismo.

EL TOPE NO SE SUPERA POR CURIOSIDAD. La escalera llega hasta 8 porque ocho es
el numero de distritos; medir con mas seria pedirle a dos servicios publicos y
gratuitos mas de lo que el ETL les va a pedir nunca.

USO

    python -m backend.etl.medir_concurrencia                  # FIRMS y CPU
    python -m backend.etl.medir_concurrencia --chirps         # agrega CHIRPS (lento)
    python -m backend.etl.medir_concurrencia --repeticiones 5
    python -m backend.etl.medir_concurrencia --registro ../gestion/medicion-h82.txt
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import statistics
import sys
import time
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from dotenv import load_dotenv  # noqa: E402

from backend.etl import bitacora  # noqa: E402
from backend.etl.cargar_focos import CODIGO_CANTON, caja_del_canton  # noqa: E402
from backend.etl.concurrencia import TRABAJADORES, mapear  # noqa: E402
from backend.etl.fuentes.firms import ExtractorFirms  # noqa: E402
from backend.etl.fuentes.firms_area import ExtractorFirmsArea  # noqa: E402
from backend.etl.fuentes.hibrido import ExtractorHibrido, territorios_desde_base  # noqa: E402

ESCALERA = (1, 2, 4, 8)
DIAS_FIRMS = 60
DIAS_CHIRPS = 10
REPETICIONES = 3
# Cuantas veces se relee el mismo CSV en cada tarea de CPU. Es lo que hace que
# el trabajo dure lo suficiente para medirse.
VUELTAS_CPU = 1000
TAREAS_CPU = 8


def resumen(tiempos: list[float]) -> str:
    if len(tiempos) == 1:
        return f"{tiempos[0]:6.2f} s"
    return (
        f"{statistics.median(tiempos):6.2f} s "
        f"(min {min(tiempos):.2f}, max {max(tiempos):.2f}, {len(tiempos)} corridas)"
    )


def escalar(
    nombre: str,
    trabajo: Callable[[int], object],
    escalera: tuple[int, ...],
    repeticiones: int,
    registrar,
) -> dict[int, list[float]]:
    """
    Corre el mismo trabajo con cada numero de trabajadores, varias veces.

    Comprueba en cada corrida que el resultado sea **identico** al de la
    primera. Si cambia, la comparacion de tiempos no vale nada y se dice.
    """
    registrar(f"\n{nombre}")
    tiempos: dict[int, list[float]] = {}
    por_tarea: dict[int, list[float]] = {}
    referencia = None
    for trabajadores in escalera:
        tiempos[trabajadores] = []
        por_tarea[trabajadores] = []
        for _ in range(repeticiones):
            arranque = time.perf_counter()
            salida = trabajo(trabajadores)
            resultado, medicion = salida if isinstance(salida, tuple) else (salida, None)
            tiempos[trabajadores].append(time.perf_counter() - arranque)
            if medicion is not None:
                por_tarea[trabajadores] += list(medicion.por_tarea)
            if referencia is None:
                referencia = resultado
            elif resultado != referencia:
                registrar(
                    f"  AVISO: con {trabajadores} trabajadores el resultado NO es el mismo. "
                    "La medicion no vale; se para aca."
                )
                raise SystemExit(1)
        base = statistics.median(tiempos[escalera[0]])
        mediana = statistics.median(tiempos[trabajadores])
        aceleracion = base / mediana if mediana else 0.0
        registrar(
            f"  {trabajadores} trabajador{'es' if trabajadores != 1 else ' ':<2} "
            f"{resumen(tiempos[trabajadores])}   x{aceleracion:.2f} contra secuencial"
        )
        # Cuanto tardo CADA tarea, no solo el reloj de la tanda. Es lo que
        # distingue «el trabajo se repartio» de «el servicio lo encola»: si al
        # subir los trabajadores cada tarea empieza a tardar proporcionalmente
        # mas, nadie esta avanzando en paralelo del otro lado.
        if por_tarea[trabajadores]:
            duraciones = por_tarea[trabajadores]
            registrar(
                f"       cada tarea: mediana {statistics.median(duraciones):6.2f} s "
                f"(min {min(duraciones):.2f}, max {max(duraciones):.2f}, "
                f"{len(duraciones)} tareas)"
            )
    return tiempos


# --------------------------------------------------------------------------- #
# 1. FIRMS por area                                                            #
# --------------------------------------------------------------------------- #


def medir_firms(caja, escalera, repeticiones, registrar) -> None:
    hasta = date.today() - timedelta(days=1)
    desde = hasta - timedelta(days=DIAS_FIRMS)
    tramos = (DIAS_FIRMS + 5) // 5

    def trabajo(trabajadores: int):
        extractor = ExtractorFirmsArea(caja, productos=("modis",))
        try:
            focos = extractor.descargar(
                desde, hasta, "modis", preliminar=True, trabajadores=trabajadores
            )
        finally:
            extractor.cerrar()
        # Se compara la lista completa, no su largo: el orden es parte de lo
        # que la concurrencia no puede cambiar.
        filas = [(f.fecha, f.hora_utc, f.latitud, f.longitud) for f in focos]
        return filas, extractor.mediciones[-1] if extractor.mediciones else None

    registrar(f"Ventana {desde} a {hasta}: {tramos} tramos de cinco dias, producto modis-nrt")
    escalar("FIRMS por area (espera por la red)", trabajo, escalera, repeticiones, registrar)


# --------------------------------------------------------------------------- #
# 2. CHIRPS por distrito                                                       #
# --------------------------------------------------------------------------- #


def medir_chirps(escalera, repeticiones, registrar) -> None:
    from basedatos.conexion import conectar

    hasta = date.today() - timedelta(days=40)
    desde = hasta - timedelta(days=DIAS_CHIRPS)

    with conectar(autocommit=True) as conexion:
        territorios = territorios_desde_base(conexion, CODIGO_CANTON)

    def trabajo(trabajadores: int):
        extractor = ExtractorHibrido(territorios, registrar=lambda *_: None)
        try:
            por_distrito, medicion = mapear(
                lambda t: extractor.extraer(t.codigo, desde, hasta),
                territorios,
                trabajadores=trabajadores,
            )
        finally:
            extractor.cerrar()
        filas = [
            (m.codigo_distrito, m.fecha, m.precipitacion_mm)
            for lista in por_distrito
            for m in lista
        ]
        return filas, medicion

    registrar(
        f"\nVentana {desde} a {hasta}: {len(territorios)} distritos, "
        "una consulta encolada por distrito"
    )
    escalar(
        "CHIRPS por distrito (espera por el servidor)", trabajo, escalera, repeticiones, registrar
    )


# --------------------------------------------------------------------------- #
# 3. Trabajo de CPU: donde el paralelismo NO ayuda                             #
# --------------------------------------------------------------------------- #

CSV_MUESTRA = (
    "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,"
    "instrument,confidence,version,bright_t31,frp,daynight\n"
) + "".join(
    f"10.4{i % 10},-84.9{i % 10},32{i % 10}.1,1.0,1.0,2026-05-0{i % 9 + 1},1830,"
    f"Terra,MODIS,8{i % 10},6.1NRT,300.0,5.0,D\n"
    for i in range(40)
)


# La caja del canton, la misma que acotan los CHECK de `crudo.foco_calor`. Se
# escribe aca para que la medicion de CPU no necesite base de datos: lo unico
# que hace con ella es descartar puntos de fuera, y no cambia el tiempo.
CAJA_CPU = (-85.2, 10.2, -84.6, 10.8)


def medir_cpu(repeticiones, registrar) -> None:
    lector = ExtractorFirms(CAJA_CPU, productos=("modis",))

    def leer(_indice: int) -> int:
        filas = 0
        for _ in range(VUELTAS_CPU):
            for fila in csv.DictReader(io.StringIO(CSV_MUESTRA)):
                if lector._leer("modis", fila) is not None:
                    filas += 1
        return filas

    def trabajo(trabajadores: int):
        resultados, medicion = mapear(leer, range(TAREAS_CPU), trabajadores=trabajadores)
        return resultados, medicion

    registrar(
        f"\n{TAREAS_CPU} tareas de {VUELTAS_CPU} lecturas de un CSV de 40 filas. "
        "No hay red: es trabajo de CPU puro."
    )
    escalar(
        "Lectura de CSV (trabajo de CPU, donde el GIL manda)",
        trabajo,
        (1, TRABAJADORES),
        repeticiones,
        registrar,
    )
    lector.cerrar()


def main(argumentos: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        description="Mide el ETL en secuencial y en paralelo (H8.2)"
    )
    analizador.add_argument("--repeticiones", type=int, default=REPETICIONES)
    analizador.add_argument(
        "--escalera",
        default=",".join(str(n) for n in ESCALERA),
        help="Numeros de trabajadores a comparar, separados por coma",
    )
    analizador.add_argument("--chirps", action="store_true", help="Agrega CHIRPS. Tarda minutos")
    analizador.add_argument("--sin-firms", action="store_true", help="Omite FIRMS")
    analizador.add_argument("--registro", help="Archivo donde guardar la salida completa")
    opciones = analizador.parse_args(argumentos)
    escalera = tuple(int(n) for n in opciones.escalera.split(","))

    load_dotenv(RAIZ / ".env")
    with bitacora.abrir(opciones.registro) as registrar:
        registrar(f"Medicion de H8.2 · {date.today()} · tope declarado: {TRABAJADORES}")
        registrar(f"Escalera: {escalera} · repeticiones: {opciones.repeticiones}")
        registrar("Esta medicion NO escribe en la base.")

        if not opciones.sin_firms:
            if not os.environ.get("FIRMS_MAP_KEY", "").strip():
                registrar("\nFIRMS: falta FIRMS_MAP_KEY en el entorno; no se mide")
            else:
                from basedatos.conexion import conectar

                with conectar(autocommit=True) as conexion:
                    caja = caja_del_canton(conexion)
                medir_firms(caja, escalera, opciones.repeticiones, registrar)

        medir_cpu(opciones.repeticiones, registrar)

        if opciones.chirps:
            medir_chirps(escalera, opciones.repeticiones, registrar)

        registrar("\nListo. Los tiempos de arriba son los que van a la evidencia de H8.2.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
