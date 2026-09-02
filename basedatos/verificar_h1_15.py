"""Comprueba los criterios de aceptacion de H1.15, la tabla `analitico.riesgo`.

CORRE CONTRA UNA BASE REAL, Y CONTRA UNA TABLA VACIA

No hace falta que exista el modelo de E3 ni una sola estimacion cargada: todo lo
que se comprueba aca son **restricciones del esquema**, y una restriccion se
ejercita intentando violarla. Cada prueba inserta una fila que deberia ser
rechazada y falla si la base la acepta.

Es lo contrario de `backend/api/test_repositorio_postgres.py`, que usa un doble y
por eso puede afirmar que se emitio cierto SQL pero **no** que ese SQL sea valido
ni que haga lo que dice. Aca el SQL se ejecuta.

POR QUE NO SE LLAMA `verificar_h115.py`

Ese nombre ya existe y es de **H11.5**, el visor publicado. `H1.15` y `H11.5`
colapsan al mismo nombre si se quitan los puntos, y no es una coincidencia
inofensiva: son dos historias de epicas distintas cuyos archivos, ramas y
evidencias se pueden confundir. Aca se separa con guion bajo.

QUE COMPRUEBA

  1. La tabla existe en `analitico`, con su clave primaria natural.
  2. Una estimacion completa entra.
  3. **La ausencia se puede representar**: nivel, probabilidad y algoritmo nulos.
  4. La clave primaria rechaza la terna duplicada.
  5. Los tres CHECK de dominio -evento, nivel, algoritmo- rechazan lo que no esta
     en el enum del contrato.
  6. La probabilidad fuera de [0, 1] se rechaza, incluido el error de escala.
  7. **Una probabilidad sin algoritmo ni version se rechaza.** Es la unica regla
     que **no** viene del contrato ni de un ADR: se agrego al escribir esta
     migracion, porque una probabilidad sin modelo detras no se puede reproducir
     ni retirar. Se dice aca para que nadie la busque en la bitacora.
  8. La explicacion sin nivel se rechaza.
  9. La clave foranea contra `geo.distrito` rechaza un distrito inexistente.
 10. El COMMENT de `probabilidad` dice que es P(nivel = alto), por D-21.

Uso:
    docker compose up -d
    python -m basedatos.verificar_h1_15

    # o contra un PostgreSQL cualquiera:
    python -m basedatos.verificar_h1_15 --dsn "postgresql://..."

Sale con codigo 1 si algun criterio no se cumple.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DDL = RAIZ / "basedatos" / "ddl" / "006_analitico_riesgo.sql"

DISTRITO = "50801"
FECHA = "2026-03-15"


class Resultado:
    def __init__(self) -> None:
        self.fallos: list[str] = []
        self.hechos = 0

    def comprobar(self, nombre: str, condicion: bool, detalle: str = "") -> None:
        self.hechos += 1
        marca = "ok  " if condicion else "FALLA"
        print(f"  {marca}  {nombre}")
        if not condicion:
            self.fallos.append(f"{nombre}{': ' + detalle if detalle else ''}")


def _rechaza(conexion, sentencia: str, parametros: tuple) -> tuple[bool, str]:
    """True si la base RECHAZO la sentencia. Deja la transaccion utilizable."""
    with conexion.cursor() as cursor:
        try:
            cursor.execute("SAVEPOINT sp")
            cursor.execute(sentencia, parametros)
        except Exception as error:  # noqa: BLE001 - cualquier violacion sirve
            cursor.execute("ROLLBACK TO SAVEPOINT sp")
            return True, type(error).__name__
        cursor.execute("ROLLBACK TO SAVEPOINT sp")
        return False, "la base la acepto"


INSERTA = """
    INSERT INTO analitico.riesgo
        (codigo_distrito, fecha, tipo_evento, nivel, probabilidad,
         algoritmo, version_modelo, explicacion)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
"""


def verificar(conexion) -> Resultado:
    r = Resultado()
    print("\nCriterios de aceptacion de H1.15\n")

    with conexion.cursor() as cursor:
        cursor.execute("""
            SELECT count(*) FROM information_schema.tables
            WHERE table_schema = 'analitico' AND table_name = 'riesgo'
        """)
        r.comprobar("1. la tabla analitico.riesgo existe", cursor.fetchone()[0] == 1)

        cursor.execute("""
            SELECT count(*) FROM information_schema.key_column_usage
            WHERE constraint_name = 'riesgo_pk'
        """)
        r.comprobar("   la clave primaria es la terna natural", cursor.fetchone()[0] == 3)

    # 2. Una estimacion completa entra.
    with conexion.cursor() as cursor:
        cursor.execute("SAVEPOINT base")
        try:
            cursor.execute(
                INSERTA,
                (
                    DISTRITO,
                    FECHA,
                    "sequia",
                    "alto",
                    0.93,
                    "regresion_logistica",
                    "v1",
                    '[{"variable":"spi_6","aporte":0.4}]',
                ),
            )
            r.comprobar("2. una estimacion completa entra", True)
        except Exception as error:  # noqa: BLE001
            cursor.execute("ROLLBACK TO SAVEPOINT base")
            r.comprobar("2. una estimacion completa entra", False, str(error)[:90])

    # 3. La ausencia se puede representar. Es D-07 y es el criterio central.
    with conexion.cursor() as cursor:
        try:
            cursor.execute(
                INSERTA,
                (DISTRITO, FECHA, "incendio", None, None, None, None, None),
            )
            cursor.execute(
                """
                SELECT nivel IS NULL AND probabilidad IS NULL
                FROM analitico.riesgo
                WHERE codigo_distrito = %s AND fecha = %s AND tipo_evento = 'incendio'
            """,
                (DISTRITO, FECHA),
            )
            r.comprobar(
                "3. la ausencia se guarda como NULL, no como cero (D-07)",
                cursor.fetchone()[0] is True,
            )
        except Exception as error:  # noqa: BLE001
            r.comprobar(
                "3. la ausencia se guarda como NULL, no como cero (D-07)", False, str(error)[:90]
            )

    casos = [
        (
            "4. la terna duplicada se rechaza",
            (DISTRITO, FECHA, "sequia", "bajo", None, None, None, None),
        ),
        (
            "5. un tipo de evento fuera del enum se rechaza",
            (DISTRITO, FECHA, "terremoto", "alto", None, None, None, None),
        ),
        (
            "   un nivel fuera del enum se rechaza",
            (DISTRITO, FECHA, "lluvia_intensa", "altisimo", None, None, None, None),
        ),
        (
            "   un algoritmo fuera del enum se rechaza",
            (DISTRITO, FECHA, "lluvia_intensa", "alto", 0.5, "red_neuronal", "v1", None),
        ),
        (
            "6. una probabilidad de 85 en vez de 0,85 se rechaza",
            (DISTRITO, FECHA, "lluvia_intensa", "alto", 85, "xgboost", "v1", None),
        ),
        (
            "   una probabilidad negativa se rechaza",
            (DISTRITO, FECHA, "lluvia_intensa", "alto", -0.1, "xgboost", "v1", None),
        ),
        (
            "7. una probabilidad sin algoritmo se rechaza",
            (DISTRITO, FECHA, "lluvia_intensa", "alto", 0.9, None, None, None),
        ),
        (
            "   una probabilidad sin version de modelo se rechaza",
            (DISTRITO, FECHA, "lluvia_intensa", "alto", 0.9, "xgboost", None, None),
        ),
        (
            "8. una explicacion sin nivel se rechaza",
            (DISTRITO, FECHA, "lluvia_intensa", None, None, None, None, "[]"),
        ),
        (
            "9. un distrito inexistente se rechaza",
            ("99999", FECHA, "sequia", "alto", None, None, None, None),
        ),
        # --- Los dos de la migracion 007, que encontro Cesar --- #
        (
            "11. el incendio con nivel 'medio' se rechaza (SC-05)",
            (DISTRITO, FECHA, "incendio", "medio", None, None, None, None),
        ),
    ]
    for nombre, parametros in casos:
        rechazo, detalle = _rechaza(conexion, INSERTA, parametros)
        r.comprobar(nombre, rechazo, detalle)

    # 12. Que ninguna restriccion dependa del reloj.
    #
    # LA COMPROBACION QUE FALTABA, Y QUE DEJO PASAR EL DEFECTO
    #
    # La 006 declaraba `CHECK (fecha <= CURRENT_DATE + INTERVAL '31 days')`.
    # PostgreSQL la acepta, asi que los 15 criterios pasaban; pero la reevalua en
    # cada insercion, no solo al escribir la fila. Como `pg_dump` emite literales
    # y restaurar es reinsertar, **un volcado de ayer no restaura hoy**.
    #
    # No se comprueba insertando -eso exigiria mover el reloj-, sino leyendo la
    # definicion de las restricciones. Es el unico lugar donde el defecto es
    # visible sin esperar un dia.
    with conexion.cursor() as cursor:
        cursor.execute("""
            SELECT conname, pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'analitico.riesgo'::regclass AND contype = 'c'
        """)
        VOLATILES = ("current_date", "now(", "current_timestamp", "localtime")
        con_reloj = [
            f"{nombre}: {definicion}"
            for nombre, definicion in cursor.fetchall()
            if any(v in definicion.lower() for v in VOLATILES)
        ]
        r.comprobar(
            "12. ninguna restriccion depende de la fecha de hoy",
            not con_reloj,
            con_reloj[0][:80] if con_reloj else "",
        )

    # 10. El COMMENT, que es lo que lee quien abre la base con un cliente SQL.
    with conexion.cursor() as cursor:
        cursor.execute("""
            SELECT col_description('analitico.riesgo'::regclass,
                   (SELECT ordinal_position FROM information_schema.columns
                    WHERE table_schema='analitico' AND table_name='riesgo'
                      AND column_name='probabilidad'))
        """)
        comentario = cursor.fetchone()[0] or ""
        r.comprobar(
            "10. el COMMENT declara P(nivel = alto), por D-21",
            "P(nivel = alto)" in comentario,
            comentario[:70],
        )

    return r


def main() -> int:
    p = argparse.ArgumentParser(description="Criterios de aceptacion de H1.15.")
    p.add_argument("--dsn", help="cadena de conexion; sin ella usa basedatos.conexion")
    args = p.parse_args()

    try:
        import psycopg
    except ImportError:
        print("\nFalta psycopg:  pip install -r requirements.txt\n")
        return 1

    if args.dsn:
        try:
            conexion = psycopg.connect(args.dsn)
        except Exception as error:  # noqa: BLE001
            print(f"\nLa base no responde: {error}\n")
            return 1
    else:
        from basedatos.conexion import conectar

        try:
            conexion = conectar()
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
    print("\nH1.15 cumple sus criterios de aceptacion.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
