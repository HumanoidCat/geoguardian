"""Dice en que estado esta la base y que comando falta para completarla.

POR QUE EXISTE

El 25 de agosto la base de una maquina del equipo estaba vacia y **nos enteramos
tres veces, siempre a mitad de otra tarea**:

    ERROR:  relation "geo.distrito" does not exist
    ERROR:  relation "crudo.medicion" does not exist
    Ya aplicadas: 0

Ninguna de las tres fue un error de la base: fue que nadie tenia forma barata de
preguntarle en que estado estaba. `docker compose ps` dice que el contenedor
esta sano, y un contenedor sano con cero tablas se ve igual que uno completo.

La causa de fondo es que **levantar la base son cuatro pasos y solo el primero lo
hace compose**:

    docker compose up -d                       el motor
    python -m basedatos.aplicar_migraciones    las tablas
    python -m backend.etl.cargar_distritos     los 8 distritos
    python -m backend.etl.cargar_mediciones    las series, ~14 min
    python -m backend.etl.cargar_focos         los focos

Saltarse cualquiera deja un sistema que arranca y falla despues.

QUE HACE

Consulta y **no escribe nada**. Por cada hueco imprime el comando exacto que lo
llena, en el orden en que hay que correrlos.

QUE NO HACE

No corre en el CI, y es a proposito: alli la base nace vacia en cada ejecucion y
se llena con lo que cada prueba necesita. Una base vacia en el CI no es un
defecto, es el diseno.

SI LA BASE ESTA APAGADA, TARDA 90 SEGUNDOS EN DECIRLO

`basedatos/conexion.py` reintenta hasta 90 s antes de rendirse, porque su caso de
uso es un cargador que arranca junto con el contenedor y tiene que esperar a que
PostgreSQL termine de levantar.

Para una consulta de estado eso es lento, pero **se prefiere esperar a duplicar
la logica de conexion**: dos formas de conectarse serian dos comportamientos que
se separan con el tiempo, y es el defecto que este proyecto sigue encontrando.

Si esta corriendo, la respuesta es inmediata.

Uso:
    python docs/herramientas/verificar_base.py

Sale con codigo 1 si falta algo, para poder encadenarlo.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

# Que tiene que existir, en el orden en que se llena. El conteo esperado es
# **orientativo**: sirve para distinguir "vacia" de "cargada", no para validar el
# dato. Lo segundo lo hacen los verificadores de cada historia.
CONTENIDO = [
    ("geo.distrito", 8, "python -m backend.etl.cargar_distritos", "H1.3"),
    ("crudo.medicion_diaria", 100_000, "python -m backend.etl.cargar_mediciones", "H1.1"),
    ("crudo.foco_calor", 400, "python -m backend.etl.cargar_focos", "H1.2"),
]


def main() -> int:
    try:
        from basedatos.conexion import conectar
    except ImportError as error:
        print(f"\nNo se pudo importar el conector: {error}")
        print("\n    pip install -r requirements.txt\n")
        return 1

    print("\nEstado de la base\n")

    try:
        conexion = conectar()
    except Exception as error:  # ErrorConexion o lo que levante el driver
        print(f"  La base no responde: {error}")
        print("\n  Se levanta con:\n")
        print("      docker compose up -d")
        print("      docker compose ps        # esperar a que diga healthy\n")
        return 1

    faltan: list[str] = []

    with conexion, conexion.cursor() as cursor:
        # ------------------------------------------------------------------ #
        # Migraciones
        # ------------------------------------------------------------------ #
        en_disco = sorted(p.name for p in (RAIZ / "basedatos" / "ddl").glob("[0-9]*.sql"))

        try:
            cursor.execute("SELECT archivo FROM control.migracion")
            aplicadas = {fila[0] for fila in cursor.fetchall()}
        except Exception:
            # Si no existe control.migracion no hay ninguna aplicada, y el
            # aplicador la crea. No es un caso raro: es una base recien nacida.
            conexion.rollback()
            aplicadas = set()

        pendientes = [a for a in en_disco if a not in aplicadas]
        print(f"  migraciones     {len(aplicadas)} de {len(en_disco)} aplicadas")
        for archivo in pendientes:
            print(f"                  falta {archivo}")

        if pendientes:
            faltan.append("python -m basedatos.aplicar_migraciones")

        # ------------------------------------------------------------------ #
        # Contenido
        # ------------------------------------------------------------------ #
        print()
        for tabla, esperado, comando, historia in CONTENIDO:
            try:
                cursor.execute(f"SELECT count(*) FROM {tabla}")  # noqa: S608
                filas = cursor.fetchone()[0]
            except Exception:
                conexion.rollback()
                print(f"  {tabla:24} la tabla no existe          ({historia})")
                if comando not in faltan:
                    faltan.append(comando)
                continue

            if filas == 0:
                print(f"  {tabla:24} vacia                       ({historia})")
                faltan.append(comando)
            elif filas < esperado * 0.9:
                print(f"  {tabla:24} {filas:>8} filas, se esperaban ~{esperado}  ({historia})")
                faltan.append(comando)
            else:
                print(f"  {tabla:24} {filas:>8} filas")

    if not faltan:
        print("\nLa base esta completa.\n")
        return 0

    print("\nFalta correr, en este orden:\n")
    for comando in faltan:
        print(f"    {comando}")
    print("\n  cargar_mediciones tarda unos 14 minutos: son 8 distritos contra")
    print("  CHIRPS, y no hay forma de acelerarlo. Ver H1.10, la estrategia de")
    print("  respaldo, que convertiria esos 14 minutos en una restauracion.\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
