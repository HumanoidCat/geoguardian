"""Criterios de aceptacion de H1.11, el particionado de `crudo.medicion_diaria`.

CORRE CONTRA UNA BASE REAL

Un particionado no se comprueba mirando el catalogo. Se comprueba **escribiendo
filas** y viendo en cual particion caen, si la clave sigue rechazando duplicados
y si el ETL de H1.1 sigue pudiendo recargar sin duplicar.

QUE COMPRUEBA

  1. La tabla esta particionada por rango sobre `fecha`.
  2. Hay una particion por anio con dato, y la DEFAULT existe.
  3. La DEFAULT esta VACIA: una fila ahi significa que falta una particion.
  4. Ninguna fila se perdio: el padre y la suma de las partes coinciden.
  5. La clave primaria sigue rechazando duplicados.
  6. **El upsert idempotente de H1.1 sigue funcionando.**
  7. Las claves foraneas siguen vigentes.
  8. Las restricciones CHECK las heredan las particiones.
  9. La poda ocurre: una consulta de 7 dias lee UNA particion.
 10. `asegurar_particion_anual` es idempotente.
 11. **Una fecha futura ya entra**: el CHECK con CURRENT_DATE se fue.
 12. Una fila fuera de todo rango cae en la DEFAULT, no se rechaza.
 13. Cambiar el anio de una fila la mueve de particion.
 14. **NINGUNA tabla del esquema tiene un CHECK volatil**, no solo esta.

El 14 es el que importa mas alla de esta historia. Los verificadores de H1.13 y
H1.9 miraban **una tabla cada uno**, y por eso el defecto de I-18 sobrevivio en
`crudo.medicion_diaria` y `crudo.foco_calor` tres migraciones despues de haberlo
«arreglado». Un control con menos alcance que el defecto da la misma
tranquilidad y ninguna proteccion.

Uso:
    docker compose up -d
    python -m basedatos.verificar_h1_11

Sale con codigo 1 si algun criterio no se cumple.
"""

from __future__ import annotations

import argparse
import sys

DISTRITO = "50801"


class Resultado:
    def __init__(self) -> None:
        self.fallos: list[str] = []
        self.hechos = 0

    def comprobar(self, nombre: str, condicion: bool, detalle: str = "") -> None:
        self.hechos += 1
        print(f"  {'ok  ' if condicion else 'FALLA'}  {nombre}")
        if not condicion:
            self.fallos.append(f"{nombre}{': ' + detalle if detalle else ''}")


INSERTA = """
    INSERT INTO crudo.medicion_diaria
        (codigo_distrito, fecha, precipitacion_mm, fuente_precipitacion, fuente_resto)
    VALUES (%s, %s, %s, 'chirps', 'power')
"""


def migracion_aplicada(cur) -> bool:
    """Si la 010 ya corrio sobre esta base.

    SE PREGUNTA ANTES DE COMPROBAR NADA, Y ESO NO ES DEFENSA EXCESIVA.

    La primera version arrancaba directo con los criterios. Contra una base sin
    la migracion daba dos FALLA y despues **reventaba con un traceback** al
    consultar una particion que no existe.

    Un verificador que se cae en vez de explicar manda a buscar el defecto donde
    no esta: el mensaje decia «relation crudo.medicion_diaria_futuro does not
    exist», que se lee como un error del codigo y era simplemente un paso que
    faltaba. Es la misma leccion del criterio 13, en el arnes en vez de en un
    criterio.
    """
    cur.execute("""
        SELECT count(*) FROM pg_partitioned_table
        WHERE partrelid = 'crudo.medicion_diaria'::regclass
    """)
    return cur.fetchone()[0] == 1


def verificar(conexion) -> Resultado:  # noqa: PLR0915 - es una lista de criterios
    r = Resultado()
    cur = conexion.cursor()
    print("\nCriterios de aceptacion de H1.11\n")

    if not migracion_aplicada(cur):
        print("  La migracion 010 no esta aplicada en esta base.\n")
        print("  `crudo.medicion_diaria` existe pero no esta particionada, asi que")
        print("  no hay nada que verificar todavia. No es un defecto: es un paso.\n")
        print("      python -m basedatos.aplicar_migraciones\n")
        r.comprobar("0. la migracion 010 esta aplicada", False, "falta aplicarla")
        return r

    # ---------------------------------------------------------------- 1
    cur.execute("""
        SELECT partstrat, pg_get_partkeydef('crudo.medicion_diaria'::regclass)
        FROM pg_partitioned_table WHERE partrelid = 'crudo.medicion_diaria'::regclass
    """)
    fila = cur.fetchone()
    r.comprobar(
        "1. la tabla esta particionada por RANGE sobre fecha",
        fila is not None and fila[0] == "r" and "fecha" in fila[1],
        f"pg_partitioned_table dice {fila}",
    )

    # ---------------------------------------------------------------- 2 y 3
    cur.execute("""
        SELECT c.relname, pg_get_expr(c.relpartbound, c.oid)
        FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid
        WHERE i.inhparent = 'crudo.medicion_diaria'::regclass
        ORDER BY c.relname
    """)
    particiones = cur.fetchall()
    defecto = [n for n, b in particiones if b == "DEFAULT"]
    r.comprobar(
        "2. hay particiones anuales y una DEFAULT",
        len(particiones) > 1 and len(defecto) == 1,
        f"{len(particiones)} particiones, {len(defecto)} DEFAULT",
    )

    cur.execute("SELECT count(*) FROM crudo.medicion_diaria_futuro")
    en_defecto = cur.fetchone()[0]
    r.comprobar(
        "3. la particion DEFAULT esta vacia",
        en_defecto == 0,
        f"tiene {en_defecto} filas: falta crear la particion de su anio",
    )

    # ---------------------------------------------------------------- 4
    cur.execute("SELECT count(*) FROM crudo.medicion_diaria")
    total = cur.fetchone()[0]
    suma = 0
    for nombre, _ in particiones:
        cur.execute(f"SELECT count(*) FROM crudo.{nombre}")  # noqa: S608 - del catalogo
        suma += cur.fetchone()[0]
    r.comprobar(
        "4. el padre y la suma de las particiones coinciden",
        total == suma and total > 0,
        f"padre {total}, suma {suma}",
    )

    # ---------------------------------------------------------------- 5
    cur.execute(
        "SELECT fecha FROM crudo.medicion_diaria WHERE codigo_distrito = %s LIMIT 1", (DISTRITO,)
    )
    existente = cur.fetchone()
    if existente is None:
        r.comprobar("5. la clave primaria rechaza duplicados", False, "la tabla esta vacia")
        return r
    fecha = existente[0]

    cur.execute("SAVEPOINT sp")
    try:
        cur.execute(INSERTA, (DISTRITO, fecha, 1.0))
        rechazo = False
    except Exception:  # noqa: BLE001
        rechazo = True
    cur.execute("ROLLBACK TO SAVEPOINT sp")
    r.comprobar("5. la clave primaria sigue rechazando duplicados", rechazo)

    # ---------------------------------------------------------------- 6
    # EL CRITERIO QUE MAS VALE.
    #
    # H1.1 recarga con ON CONFLICT DO UPDATE, y en una tabla particionada eso
    # solo funciona si la clave de conflicto contiene la clave de particion.
    # Aqui la contiene, pero eso hay que **demostrarlo**: si fallara, la ingesta
    # dejaria de ser idempotente y nadie lo notaria hasta la siguiente recarga.
    cur.execute("SAVEPOINT sp")
    try:
        cur.execute(
            INSERTA.rstrip()
            + """
            ON CONFLICT (codigo_distrito, fecha) DO UPDATE
                SET precipitacion_mm = EXCLUDED.precipitacion_mm
            """,
            (DISTRITO, fecha, 99.5),
        )
        cur.execute(
            "SELECT precipitacion_mm FROM crudo.medicion_diaria "
            "WHERE codigo_distrito = %s AND fecha = %s",
            (DISTRITO, fecha),
        )
        valor = cur.fetchone()[0]
        upsert = abs(float(valor) - 99.5) < 1e-3
        detalle = f"quedo {valor}"
    except Exception as error:  # noqa: BLE001
        upsert, detalle = False, str(error).splitlines()[0]
    cur.execute("ROLLBACK TO SAVEPOINT sp")
    r.comprobar("6. el upsert idempotente de H1.1 sigue funcionando", upsert, detalle)

    # ---------------------------------------------------------------- 7
    cur.execute("SAVEPOINT sp")
    try:
        cur.execute(INSERTA, ("99999", fecha, 1.0))
        fk = False
    except Exception:  # noqa: BLE001
        fk = True
    cur.execute("ROLLBACK TO SAVEPOINT sp")
    r.comprobar("7. la clave foranea a geo.distrito sigue vigente", fk)

    # ---------------------------------------------------------------- 8
    cur.execute("SAVEPOINT sp")
    try:
        cur.execute(INSERTA, (DISTRITO, "2019-06-15", -5.0))
        chk = False
    except Exception:  # noqa: BLE001
        chk = True
    cur.execute("ROLLBACK TO SAVEPOINT sp")
    r.comprobar("8. las particiones heredan los CHECK (precipitacion negativa rechazada)", chk)

    # ---------------------------------------------------------------- 9
    cur.execute("""
        SELECT c.relname FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid
        WHERE i.inhparent = 'crudo.medicion_diaria'::regclass
    """)
    nombres = {f[0] for f in cur.fetchall()}
    cur.execute("""
        EXPLAIN SELECT codigo_distrito, fecha FROM crudo.medicion_diaria
        WHERE fecha >= DATE '2019-06-01' AND fecha < DATE '2019-06-08'
    """)
    plan = "\n".join(f[0] for f in cur.fetchall())
    import re

    leidas = set(re.findall(r"\b\w+\b", plan)) & nombres
    r.comprobar(
        "9. la poda ocurre: una ventana de 7 dias lee UNA particion",
        len(leidas) == 1,
        f"leyo {len(leidas)}: {sorted(leidas)}",
    )

    # ---------------------------------------------------------------- 10
    cur.execute("SELECT crudo.asegurar_particion_anual(2030)")
    primera = cur.fetchone()[0]
    cur.execute("SELECT crudo.asegurar_particion_anual(2030)")
    segunda = cur.fetchone()[0]
    r.comprobar(
        "10. asegurar_particion_anual es idempotente",
        "creada" in primera and "ya existia" in segunda,
        f"primera: {primera}; segunda: {segunda}",
    )

    # ---------------------------------------------------------------- 11
    # I-18: con `fecha <= CURRENT_DATE` esta insercion fallaba y la particion
    # de 2030 quedaba creada e inservible.
    cur.execute("SAVEPOINT sp")
    try:
        cur.execute(INSERTA, (DISTRITO, "2030-03-10", 1.0))
        futuro, detalle = True, ""
    except Exception as error:  # noqa: BLE001
        futuro, detalle = False, str(error).splitlines()[0]
    cur.execute("ROLLBACK TO SAVEPOINT sp")
    r.comprobar("11. una fecha futura ya entra: el CHECK con CURRENT_DATE se fue", futuro, detalle)

    # ---------------------------------------------------------------- 12
    cur.execute("SAVEPOINT sp")
    try:
        cur.execute(INSERTA, (DISTRITO, "2040-01-01", 1.0))
        cur.execute("SELECT count(*) FROM crudo.medicion_diaria_futuro")
        en_default = cur.fetchone()[0] == 1
        detalle = ""
    except Exception as error:  # noqa: BLE001
        en_default, detalle = False, str(error).splitlines()[0]
    cur.execute("ROLLBACK TO SAVEPOINT sp")
    r.comprobar(
        "12. una fila fuera de todo rango cae en la DEFAULT, no se rechaza",
        en_default,
        detalle,
    )

    # ---------------------------------------------------------------- 13
    # SE USA UNA FILA NUEVA EN UN ANIO SIN DATO, Y NO UNA EXISTENTE.
    #
    # La primera version hacia `fecha + INTERVAL '1 year'` sobre una fila real y
    # fallaba con clave duplicada: el mismo distrito **ya tiene** ese dia del
    # anio siguiente. El particionado estaba bien; la prueba estaba mal. Se deja
    # anotado porque un criterio que falla por su propio montaje es peor que no
    # tenerlo: manda a buscar el defecto donde no esta.
    cur.execute("SAVEPOINT sp")
    try:
        cur.execute("SELECT crudo.asegurar_particion_anual(2029)")
        cur.execute(INSERTA, (DISTRITO, "2030-05-05", 3.0))
        cur.execute(
            "SELECT count(*) FROM crudo.medicion_diaria_2030 WHERE fecha = DATE '2030-05-05'"
        )
        antes_2030 = cur.fetchone()[0]

        cur.execute(
            "UPDATE crudo.medicion_diaria SET fecha = DATE '2029-05-05' "
            "WHERE codigo_distrito = %s AND fecha = DATE '2030-05-05'",
            (DISTRITO,),
        )
        cur.execute(
            "SELECT count(*) FROM crudo.medicion_diaria_2030 WHERE fecha = DATE '2030-05-05'"
        )
        despues_2030 = cur.fetchone()[0]
        cur.execute(
            "SELECT count(*) FROM crudo.medicion_diaria_2029 WHERE fecha = DATE '2029-05-05'"
        )
        en_2029 = cur.fetchone()[0]

        movida = antes_2030 == 1 and despues_2030 == 0 and en_2029 == 1
        detalle = f"2030 antes {antes_2030}, despues {despues_2030}; 2029 {en_2029}"
    except Exception as error:  # noqa: BLE001
        movida, detalle = False, str(error).splitlines()[0]
    cur.execute("ROLLBACK TO SAVEPOINT sp")
    r.comprobar("13. cambiar el anio de una fila la mueve de particion de verdad", movida, detalle)

    # ---------------------------------------------------------------- 14
    cur.execute("""
        SELECT n.nspname || '.' || t.relname || ' · ' || c.conname
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE c.contype = 'c'
          AND n.nspname IN ('geo', 'crudo', 'analitico', 'control')
          AND lower(pg_get_constraintdef(c.oid))
              ~ 'current_date|now\\(|current_timestamp|localtime'
        ORDER BY 1
    """)
    volatiles = [f[0] for f in cur.fetchall()]
    r.comprobar(
        "14. NINGUNA tabla del esquema tiene un CHECK volatil",
        not volatiles,
        f"quedan {len(volatiles)}: {', '.join(volatiles)}",
    )
    return r


def main() -> int:
    p = argparse.ArgumentParser(description="Criterios de aceptacion de H1.11.")
    p.add_argument("--dsn", help="cadena de conexion; sin ella usa basedatos.conexion")
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
        resultado = verificar(conexion)
    finally:
        conexion.rollback()
        conexion.close()

    print(f"\n{resultado.hechos - len(resultado.fallos)} de {resultado.hechos} criterios")
    if resultado.fallos:
        print("\nNO se cumplen:")
        for f in resultado.fallos:
            print(f"  - {f}")
        print()
        return 1
    print("\nH1.11 cumple sus criterios de aceptacion.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
