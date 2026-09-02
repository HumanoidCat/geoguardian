"""Mide cada indice candidato antes de crearlo. Historia H1.12.

===========================================================================
EL PUNTO DE PARTIDA: EL ESQUEMA NO TIENE NI UN INDICE SECUNDARIO
===========================================================================

Antes de esta historia habia **uno solo** en todo el proyecto, `fallo_origen_fecha_ix`,
creado ayer en la 009. Todo lo demas se apoya en los indices que PostgreSQL crea
solos para las claves primarias.

Eso no es un descuido menor: significa que **ninguna consulta que no empiece por
la primera columna de su clave primaria tiene apoyo**, y varias de las que el
sistema hace todo el tiempo son exactamente asi.

===========================================================================
UN INDICE QUE NO SE USA ES PEOR QUE NO TENERLO
===========================================================================

Cuesta espacio, cuesta en cada `INSERT` y `UPDATE`, y hay que mantenerlo. Un
indice que el planificador nunca elige es coste puro.

Por eso este guion mide **cada candidato por separado**, y por eso incluye uno que
espera **descartar**. Una historia de indices que termina agregando todos los que
se le ocurrieron a alguien no midio nada: eligio.

===========================================================================
COMO MIDE, Y POR QUE NO DEJA RASTRO
===========================================================================

Para cada candidato:

    1. corre la consulta SIN el indice y cronometra
    2. `CREATE INDEX` y `ANALYZE`
    3. corre la MISMA consulta y cronometra
    4. mira el plan: **¿el planificador lo eligio?**

Todo dentro de una transaccion que **se revierte al final**. El guion se puede
correr cuantas veces se quiera sin cambiar la base: quien decide que indices
quedan es la migracion 011, no esta herramienta.

Que el paso 4 exista es lo que separa medir de suponer. Un indice puede estar
creado, la consulta ir mas rapido por casualidad -la cache- y el plan seguir
siendo un `Seq Scan`. Si el planificador no lo elige, el indice no hizo nada.

Uso:
    docker compose up -d
    python -m basedatos.medir_indices
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

DIFERENCIA_MINIMA_MS = 0.5


@dataclass(frozen=True)
class Candidato:
    nombre: str
    porque: str
    indice: str
    consulta: str
    parametros: tuple = ()
    #: Lo que se espera ANTES de medir. Escribirlo aqui obliga a comprometerse
    #: con una prediccion, y hace visible cuando la medicion la contradice.
    esperado: str = "mejora"


CANDIDATOS = [
    Candidato(
        nombre="riesgo_fecha_evento_ix",
        porque=(
            "El visor pide 'el riesgo de todos los distritos para esta fecha y este "
            "evento'. La clave primaria es (codigo_distrito, fecha, tipo_evento) y la "
            "consulta NO filtra por la primera columna, asi que el indice de la clave "
            "no sirve: falta la columna guia"
        ),
        indice=(
            "CREATE INDEX riesgo_fecha_evento_ix "
            "ON analitico.riesgo (fecha, tipo_evento) INCLUDE (codigo_distrito, nivel)"
        ),
        consulta=(
            "SELECT codigo_distrito, nivel, probabilidad FROM analitico.riesgo "
            "WHERE fecha = %s AND tipo_evento = %s"
        ),
        parametros=("2024-06-15", "lluvia_intensa"),
    ),
    Candidato(
        nombre="foco_distrito_fecha_ix",
        porque=(
            "`SQL_CONTAR_FOCOS` filtra por (codigo_distrito, fecha BETWEEN ...). La "
            "clave primaria de foco_calor es (producto, satelite, fecha, hora_utc, "
            "latitud, longitud): **codigo_distrito no aparece en ella**, asi que la "
            "consulta recorre la tabla entera"
        ),
        indice=("CREATE INDEX foco_distrito_fecha_ix ON crudo.foco_calor (codigo_distrito, fecha)"),
        consulta=(
            "SELECT count(*) FROM crudo.foco_calor "
            "WHERE codigo_distrito = %s AND fecha BETWEEN %s AND %s"
        ),
        parametros=("50801", "2020-01-01", "2020-12-31"),
    ),
    Candidato(
        nombre="distrito_geometria_gix",
        porque=(
            "El cargador de focos y el repositorio asignan distrito con "
            "`ST_Contains(geometria, punto)`. Sin GIST, PostgreSQL evalua la "
            "geometria exacta de los OCHO distritos por cada punto; con el, la caja "
            "envolvente descarta siete antes de la prueba cara"
        ),
        indice="CREATE INDEX distrito_geometria_gix ON geo.distrito USING GIST (geometria)",
        consulta=(
            "SELECT d.codigo FROM geo.distrito d "
            "WHERE ST_Contains(d.geometria, ST_SetSRID(ST_MakePoint(%s, %s), 4326))"
        ),
        parametros=(-84.97, 10.47),
    ),
    Candidato(
        nombre="medicion_fecha_ix",
        porque=(
            "Candidato que se espera DESCARTAR, y por eso esta aqui. Desde H1.11 la "
            "tabla esta particionada por anio, asi que la poda ya reduce la busqueda "
            "por fecha antes de tocar dato. Un btree sobre `fecha` dentro de cada "
            "particion deberia aportar poco y cobrar en cada insercion del ETL"
        ),
        indice="CREATE INDEX medicion_fecha_ix ON crudo.medicion_diaria (fecha)",
        consulta=(
            "SELECT codigo_distrito, precipitacion_mm FROM crudo.medicion_diaria "
            "WHERE fecha >= %s AND fecha < %s"
        ),
        parametros=("2024-12-01", "2024-12-08"),
        esperado="sin efecto",
    ),
]


def cronometrar(cur, sql: str, parametros: tuple, repeticiones: int) -> float:
    cur.execute(sql, parametros)
    cur.fetchall()
    tiempos = []
    for _ in range(repeticiones):
        arranque = time.perf_counter()
        cur.execute(sql, parametros)
        cur.fetchall()
        tiempos.append((time.perf_counter() - arranque) * 1000)
    return statistics.median(tiempos)


def lo_usa(cur, sql: str, parametros: tuple, nombre: str) -> bool:
    """Si el PLANIFICADOR eligio el indice. No si el indice existe.

    Es la diferencia entre medir y suponer: un indice puede estar creado, la
    consulta ir mas rapido por la cache, y el plan seguir siendo un `Seq Scan`.
    """
    # `EXPLAIN` acepta parametros como cualquier otra sentencia. La primera
    # version armaba el texto con `cur.mogrify`, que en psycopg3 **no vive en el
    # cursor** sino en `ClientCursor`, y fallaba en los cuatro candidatos a la
    # vez. Cuatro errores identicos y simultaneos casi nunca son cuatro
    # problemas: son uno en el arnes.
    cur.execute("EXPLAIN " + sql, parametros)
    plan = "\n".join(f[0] for f in cur.fetchall())
    return nombre in plan


def medir(conexion, repeticiones: int) -> list[dict]:
    cur = conexion.cursor()
    resultados = []

    for c in CANDIDATOS:
        cur.execute("SAVEPOINT antes_del_indice")
        try:
            sin = cronometrar(cur, c.consulta, c.parametros, repeticiones)
            # El plan de ANTES, que es el que dice si hay crecimiento que ganar.
            cur.execute("EXPLAIN " + c.consulta, c.parametros)
            plan_antes = "\n".join(f[0] for f in cur.fetchall())
            recorrido = "Seq Scan" in plan_antes
            cur.execute(c.indice)
            cur.execute(f"ANALYZE {c.indice.split(' ON ')[1].split(' ')[0]}")
            con = cronometrar(cur, c.consulta, c.parametros, repeticiones)
            usado = lo_usa(cur, c.consulta, c.parametros, c.nombre)
            error = ""
            recorrido = recorrido and usado
        except Exception as fallo:  # noqa: BLE001
            sin = con = 0.0
            usado = recorrido = False
            error = str(fallo).splitlines()[0]
            # NO MEDIBLE NO ES LO MISMO QUE ROTO.
            #
            # El candidato GIST necesita PostGIS. En un entorno sin la extension
            # -el sandbox de verificacion, por ejemplo- la consulta falla porque
            # `st_makepoint` no existe, y eso **no dice nada** sobre si el indice
            # sirve. Confundir las dos cosas haria que un entorno incompleto se
            # leyera como un indice descartado.
            if "does not exist" in error and ("st_" in error or "gist" in error.lower()):
                error = f"NO MEDIBLE aqui, falta PostGIS: {error}"
        # Se revierte SIEMPRE. La herramienta no decide que queda en la base.
        cur.execute("ROLLBACK TO SAVEPOINT antes_del_indice")

        resultados.append(
            {
                "candidato": c,
                "sin_ms": sin,
                "con_ms": con,
                "cambio": (con - sin) / sin * 100 if sin else 0.0,
                "usado": usado,
                "reemplaza_recorrido": recorrido,
                "error": error,
            }
        )
    return resultados


def veredicto(r: dict) -> str:
    """Se acepta si el planificador lo usa Y el escaneo que reemplaza crece.

    LA PRIMERA REGLA MIRABA LA VARIABLE EQUIVOCADA, Y LA MEDICION LO DIJO.

    Empezo siendo «se acepta si ahorra mas de 0,5 ms». Con eso,
    `riesgo_fecha_evento_ix` quedaba **descartado por 0,05 ms** aunque el
    planificador lo eligiera y aunque reemplazara un `Seq Scan`.

    Medido a cuatro tamanos de `analitico.riesgo`:

        filas     sin indice   con indice   ahorro   factor
         17 544      0,56 ms      0,07 ms   0,49 ms    8,5x
         52 584      2,56 ms      0,11 ms   2,45 ms   23,0x
        122 664      6,03 ms      0,10 ms   5,92 ms   57,4x
        262 824     10,20 ms      0,11 ms  10,09 ms   90,6x

    **La consulta indexada se queda plana y la otra crece linealmente.**
    `analitico.riesgo` suma 24 filas por dia -8 distritos por 3 eventos- para
    siempre, asi que el numero de hoy es el mas pequeno que va a tener nunca.

    Aceptar o rechazar por los milisegundos de hoy es medir el tamano de la base
    de hoy, no el valor del indice. La regla correcta es **que tipo de escaneo
    reemplaza**: si cambia un recorrido secuencial por uno de indice, la
    diferencia crece sola.

    El umbral absoluto se conserva para el caso contrario: un indice que el
    planificador usa pero que sustituye otro acceso ya indexado, donde no hay
    crecimiento que esperar.
    """
    if r["error"].startswith("NO MEDIBLE"):
        return "SIN MEDIR: falta PostGIS en este entorno"
    if r["error"]:
        return "ERROR"
    if not r["usado"]:
        return "SE DESCARTA: el planificador no lo elige"
    if r["reemplaza_recorrido"]:
        return "SE ACEPTA: reemplaza un Seq Scan, y el ahorro crece con la tabla"
    if r["sin_ms"] - r["con_ms"] < DIFERENCIA_MINIMA_MS:
        return "SE DESCARTA: lo usa pero no cambia nada medible"
    return "SE ACEPTA"


def informar(resultados: list[dict]) -> None:
    print("\nIndices candidatos de H1.12\n")
    print(f"  {'indice':26}{'sin':>9}{'con':>9}{'cambio':>10}  {'lo usa':8} veredicto")
    print("  " + "-" * 76)
    for r in resultados:
        c = r["candidato"]
        print(
            f"  {c.nombre:26}{r['sin_ms']:>9.2f}{r['con_ms']:>9.2f}"
            f"{r['cambio']:>+9.1f} %  {'si' if r['usado'] else 'NO':8} {veredicto(r)}"
        )
    print()

    for r in resultados:
        c = r["candidato"]
        print(f"  {c.nombre}")
        print(f"    esperado antes de medir: {c.esperado}")
        print(f"    {c.porque}")
        if r["error"]:
            print(f"    ERROR: {r['error']}")
        print()

    aceptados = [r for r in resultados if veredicto(r).startswith("SE ACEPTA")]
    print(f"  Se aceptan {len(aceptados)} de {len(resultados)}:")
    for r in aceptados:
        print(f"    {r['candidato'].nombre}")
    print()
    print("  Nada de esto quedo en la base: el banco revierte cada prueba.")
    print("  Los indices aceptados los crea la migracion 011.\n")


def main() -> int:
    p = argparse.ArgumentParser(description="Efecto de cada indice candidato.")
    p.add_argument("--dsn")
    p.add_argument("--repeticiones", type=int, default=7)
    args = p.parse_args()

    try:
        import psycopg
    except ImportError:
        print("\nFalta psycopg:  pip install -r requirements.txt\n")
        return 1

    try:
        conexion = (
            psycopg.connect(args.dsn)
            if args.dsn
            else __import__("basedatos.conexion", fromlist=["conectar"]).conectar()
        )
    except Exception as error:  # noqa: BLE001
        print(f"\nLa base no responde: {error}")
        print("\n  Se levanta con:  docker compose up -d\n")
        return 1

    try:
        resultados = medir(conexion, args.repeticiones)
    finally:
        conexion.rollback()
        conexion.close()

    informar(resultados)
    return 0


if __name__ == "__main__":
    sys.exit(main())
