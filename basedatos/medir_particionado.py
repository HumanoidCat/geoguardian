"""Mide que le hace el particionado a las consultas reales. Historia H1.11.

===========================================================================
POR QUE ESTE GUION EXISTE
===========================================================================

La historia dice «particionar **y medir efecto en consultas**». La segunda mitad
es la que vale: particionar es media hora de DDL, y decidir si sirve requiere
numeros.

**El resultado puede ser que no sirva, y eso tambien es un resultado.** Con
~100 000 filas y un indice de clave primaria, es perfectamente posible que la
tabla plana gane. Si sale asi, se reporta asi: una historia que solo puede
terminar en «funciono» no esta midiendo nada.

===========================================================================
COMO SE COMPARA, Y POR QUE ASI
===========================================================================

No se puede comparar «antes y despues» en el tiempo: la migracion 010 ya corrio y
volver atras no es reproducible. Lo que se hace es construir **las dos formas de
la misma tabla, con las mismas filas**, en un esquema aparte:

    banco.plana           copia sin particionar
    banco.particionada    copia particionada por anio

y correr sobre las dos exactamente las mismas consultas. Las dos tienen su clave
primaria y sus indices equivalentes, porque comparar una tabla indexada contra
una sin indexar mediria el indice, no la particion.

CADA CONSULTA SE CORRE VARIAS VECES Y SE REPORTA LA MEDIANA

La primera corrida paga la lectura de disco a memoria y no representa nada. Se
descarta una corrida de calentamiento por consulta y por tabla, y de las
siguientes se toma **la mediana y no el promedio**: una pausa del recolector de
basura o del sistema operativo mueve el promedio y no mueve la mediana.

LAS CONSULTAS SON LAS DEL SISTEMA, NO LAS QUE FAVORECEN

Se eligieron leyendo el codigo, no imaginando:

    ventana_visor        7 dias, los 8 distritos. Es lo que pide el visor
    ventana_modelo      30 dias de un distrito. Es la ventana mas larga de H2.5
    pliegue             ~7 anios. Es el entrenamiento del pliegue 1 de H3.2
    serie_completa      un distrito entero, 34 anios. Lo que lee H3.3
    agregado_anual      promedios por anio. Lo unico que toca todo el historico

`serie_completa` esta a proposito: es la consulta que el particionado **deberia
empeorar**, porque obliga a tocar 34 particiones en vez de una tabla. Un banco de
pruebas que solo incluye lo que le conviene a la respuesta que uno quiere no es
una medicion.

Uso:
    docker compose up -d
    python -m basedatos.medir_particionado
    python -m basedatos.medir_particionado --repeticiones 9
"""

from __future__ import annotations

import argparse
import re
import statistics
import sys
import time
from pathlib import Path

#: Por debajo de esto, dos consultas no se distinguen **en terminos absolutos**,
#: por mucho que el porcentaje asuste.
#:
#: Existe porque la medicion lo pidio: `ventana_modelo` salio +105 %, que suena a
#: catastrofe, y en absoluto son 0,15 ms contra 0,31 ms. Un porcentaje sobre una
#: consulta que ya tardaba menos que el parpadeo de un planificador **no informa
#: nada**, y reportarlo sin este aviso seria elegir el numero mas dramatico.
DIFERENCIA_MINIMA_MS = 1.0

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

COLUMNAS = """codigo_distrito, fecha, temp_max_c, temp_min_c, temp_media_c,
    humedad_relativa_pct, viento_ms, radiacion_mj_m2, precipitacion_mm,
    fuente_precipitacion, fuente_resto, imputado, metodo_imputacion, descargado_en"""

#: Cada consulta lleva `{t}` donde va la tabla, para que las dos formas reciban
#: **exactamente el mismo texto**. Escribir dos versiones a mano es como se cuela
#: una diferencia que despues se atribuye a la particion.
CONSULTAS: dict[str, tuple[str, str]] = {
    "ventana_visor": (
        "7 dias, los 8 distritos (lo que pide el visor)",
        "SELECT codigo_distrito, fecha, precipitacion_mm FROM {t} "
        "WHERE fecha >= DATE '2024-12-01' AND fecha < DATE '2024-12-08'",
    ),
    "ventana_modelo": (
        "30 dias de un distrito (la ventana mas larga de H2.5)",
        "SELECT fecha, precipitacion_mm, temp_max_c FROM {t} "
        "WHERE codigo_distrito = '50801' "
        "AND fecha >= DATE '2024-11-01' AND fecha < DATE '2024-12-01'",
    ),
    "pliegue": (
        "~7 anios, todos los distritos (entrenamiento del pliegue 1 de H3.2)",
        "SELECT codigo_distrito, fecha, precipitacion_mm FROM {t} "
        "WHERE fecha >= DATE '1991-01-01' AND fecha < DATE '1998-01-01'",
    ),
    "serie_completa": (
        "un distrito entero, 34 anios (lo que lee H3.3; aqui la particion estorba)",
        "SELECT fecha, precipitacion_mm FROM {t} WHERE codigo_distrito = '50801' ORDER BY fecha",
    ),
    "agregado_anual": (
        "promedio por anio sobre todo el historico",
        "SELECT extract(year FROM fecha) AS anio, avg(precipitacion_mm) FROM {t} "
        "GROUP BY 1 ORDER BY 1",
    ),
}


def construir_banco(cur, anios: range) -> None:
    """Deja `banco.plana` y `banco.particionada` con las mismas filas."""
    cur.execute("DROP SCHEMA IF EXISTS banco CASCADE")
    cur.execute("CREATE SCHEMA banco")

    cur.execute(f"CREATE TABLE banco.plana AS SELECT {COLUMNAS} FROM crudo.medicion_diaria")
    cur.execute("ALTER TABLE banco.plana ADD PRIMARY KEY (codigo_distrito, fecha)")

    cur.execute("""
        CREATE TABLE banco.particionada (
            LIKE banco.plana INCLUDING DEFAULTS
        ) PARTITION BY RANGE (fecha)
    """)
    # La clave primaria va DESPUES del PARTITION BY: en una tabla particionada
    # tiene que incluir la clave de particion, y `LIKE ... INCLUDING INDEXES`
    # copiaria la de la plana sin esa comprobacion.
    cur.execute("ALTER TABLE banco.particionada ADD PRIMARY KEY (codigo_distrito, fecha)")
    for anio in anios:
        cur.execute(
            f"CREATE TABLE banco.particionada_{anio} PARTITION OF banco.particionada "
            f"FOR VALUES FROM ('{anio}-01-01') TO ('{anio + 1}-01-01')"
        )
    cur.execute("CREATE TABLE banco.particionada_resto PARTITION OF banco.particionada DEFAULT")
    cur.execute("INSERT INTO banco.particionada SELECT * FROM banco.plana")

    # ANALYZE en las dos. Sin estadisticas frescas el planificador de una de las
    # dos decidiria a ciegas y la comparacion mediria eso.
    cur.execute("ANALYZE banco.plana")
    cur.execute("ANALYZE banco.particionada")


def cronometrar(cur, sql: str, repeticiones: int) -> float:
    """Mediana en milisegundos, descartando una corrida de calentamiento."""
    cur.execute(sql)
    cur.fetchall()
    tiempos = []
    for _ in range(repeticiones):
        arranque = time.perf_counter()
        cur.execute(sql)
        cur.fetchall()
        tiempos.append((time.perf_counter() - arranque) * 1000)
    return statistics.median(tiempos)


def nombres_de_particion(cur) -> set[str]:
    """Las particiones que existen de verdad, preguntadas al catalogo."""
    cur.execute("""
        SELECT c.relname FROM pg_inherits i
        JOIN pg_class c ON c.oid = i.inhrelid
        WHERE i.inhparent = 'banco.particionada'::regclass
    """)
    return {fila[0] for fila in cur.fetchall()}


def particiones_leidas(cur, sql: str, existentes: set[str]) -> int:
    """Cuantas de las particiones REALES aparecen en el plan. La poda, medida.

    DOS VECES ESTUVO MAL, Y LAS DOS LO DELATO EL PROPIO NUMERO.

    Contando lineas daba 69 sobre 35 particiones: un `Merge Append` nombra cada
    una en varios nodos. Contando nombres unicos con una expresion regular daba
    104, porque `Index Scan using particionada_1991_pkey on particionada_1991`
    aporta dos cadenas distintas y una es el indice, no la particion.

    **Un contador que puede superar a su propio maximo es un contador roto.** Se
    arregla preguntandole al catalogo cuales existen y buscando esas, en vez de
    adivinar por la forma del nombre.
    """
    cur.execute("EXPLAIN (FORMAT TEXT) " + sql)
    plan = "\n".join(fila[0] for fila in cur.fetchall())
    encontradas = set(re.findall(r"\b\w+\b", plan)) & existentes
    return len(encontradas)


def medir(conexion, repeticiones: int) -> list[dict]:
    cur = conexion.cursor()

    cur.execute("SELECT min(fecha), max(fecha), count(*) FROM crudo.medicion_diaria")
    desde, hasta, filas = cur.fetchone()
    print(f"\nBanco de medicion de H1.11\n\n  filas      {filas}")
    print(f"  periodo    {desde} a {hasta}")
    print(f"  repeticiones por consulta  {repeticiones} (mas una de calentamiento)\n")

    construir_banco(cur, range(desde.year, hasta.year + 1))
    existentes = nombres_de_particion(cur)
    print(f"  banco listo: {len(existentes)} particiones\n")

    resultados = []
    for nombre, (descripcion, plantilla) in CONSULTAS.items():
        plana = cronometrar(cur, plantilla.format(t="banco.plana"), repeticiones)
        part = cronometrar(cur, plantilla.format(t="banco.particionada"), repeticiones)
        leidas = particiones_leidas(cur, plantilla.format(t="banco.particionada"), existentes)
        resultados.append(
            {
                "consulta": nombre,
                "descripcion": descripcion,
                "plana_ms": plana,
                "particionada_ms": part,
                "cambio": (part - plana) / plana * 100 if plana else 0.0,
                "particiones_leidas": leidas,
            }
        )

    cur.execute("DROP SCHEMA banco CASCADE")
    return resultados


def informar(resultados: list[dict]) -> None:
    print(f"  {'consulta':18}{'plana':>10}{'particion':>11}{'cambio':>10}   particiones")
    print(f"  {'':18}{'ms':>10}{'ms':>11}{'':>10}   leidas")
    print("  " + "-" * 62)
    for r in resultados:
        signo = "+" if r["cambio"] >= 0 else ""
        print(
            f"  {r['consulta']:18}{r['plana_ms']:>10.2f}{r['particionada_ms']:>11.2f}"
            f"{signo + format(r['cambio'], '.1f') + ' %':>10}   {r['particiones_leidas']:>3}"
        )
    print()
    for r in resultados:
        print(f"  {r['consulta']:18}{r['descripcion']}")
    print()

    def relevante(r: dict) -> bool:
        return abs(r["particionada_ms"] - r["plana_ms"]) >= DIFERENCIA_MINIMA_MS

    mejoran = [r for r in resultados if r["cambio"] < -5 and relevante(r)]
    empeoran = [r for r in resultados if r["cambio"] > 5 and relevante(r)]
    menores = [r for r in resultados if not relevante(r)]
    iguales = [r for r in resultados if -5 <= r["cambio"] <= 5 and relevante(r)]

    def lista(rs):
        return ", ".join(r["consulta"] for r in rs) or "-"

    print("  Lectura del resultado")
    print(f"    mejoran            {len(mejoran)}: {lista(mejoran)}")
    print(f"    empeoran           {len(empeoran)}: {lista(empeoran)}")
    print(f"    sin cambio         {len(iguales)}: {lista(iguales)}")
    print(f"    bajo el ruido      {len(menores)}: {lista(menores)}")
    print()
    print("  Dos umbrales, los dos fijados ANTES de correr la medicion:")
    print("    5 % de cambio relativo, por debajo del cual no se distingue del ruido")
    print(f"    {DIFERENCIA_MINIMA_MS:.0f} ms de diferencia absoluta, por debajo de la cual el")
    print("    porcentaje no informa aunque sea grande")
    print()
    for r in menores:
        print(
            f"    {r['consulta']}: {r['cambio']:+.1f} % suena mucho y son "
            f"{abs(r['particionada_ms'] - r['plana_ms']):.2f} ms. No se reporta como empeora."
        )
    if menores:
        print()


def main() -> int:
    p = argparse.ArgumentParser(description="Efecto del particionado en las consultas.")
    p.add_argument("--dsn", help="cadena de conexion; sin ella usa basedatos.conexion")
    p.add_argument("--repeticiones", type=int, default=7)
    args = p.parse_args()

    try:
        import psycopg
    except ImportError:
        print("\nFalta psycopg:  pip install -r requirements.txt\n")
        return 1

    try:
        conexion = (
            psycopg.connect(args.dsn, autocommit=True)
            if args.dsn
            else __import__("basedatos.conexion", fromlist=["conectar"]).conectar(autocommit=True)
        )
    except Exception as error:  # noqa: BLE001
        print(f"\nLa base no responde: {error}")
        print("\n  Se levanta con:  docker compose up -d\n")
        return 1

    try:
        resultados = medir(conexion, args.repeticiones)
    finally:
        conexion.close()

    informar(resultados)
    return 0


if __name__ == "__main__":
    sys.exit(main())
