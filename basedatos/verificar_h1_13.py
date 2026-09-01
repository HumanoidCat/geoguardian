"""Criterios de aceptacion de H1.13, la auditoria de `analitico.riesgo`.

CORRE CONTRA UNA BASE REAL

Un disparador no se comprueba leyendolo. Se comprueba **cambiando una fila y
mirando si aparecio el registro**, que es lo unico que distingue un disparador
que funciona de uno que existe.

QUE COMPRUEBA

  1. La tabla y el disparador existen.
  2. Un INSERT **no** deja registro: una fila nueva no cambio nada.
  3. Un UPDATE deja **el valor ANTERIOR**, no el nuevo.
  4. Un DELETE deja registro, y el registro **sobrevive al borrado**.
  5. Dos cambios seguidos dejan dos registros, en orden.
  6. Un UPDATE que toca varias filas deja **un registro por fila**.
  7. Un UPDATE que la base RECHAZA no deja rastro: se auditan hechos, no
     intentos.
  8. Queda constancia de quien y cuando.
  9. `registrado_en` no depende de un CHECK volatil, que es lo que la 007 tuvo
     que quitar de la 006.

Uso:
    docker compose up -d
    python -m basedatos.verificar_h1_13
    python -m basedatos.verificar_h1_13 --dsn "postgresql://..."

Sale con codigo 1 si algun criterio no se cumple.
"""

from __future__ import annotations

import argparse
import sys

DISTRITO = "50801"
FECHA = "2026-04-10"


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
    INSERT INTO analitico.riesgo
        (codigo_distrito, fecha, tipo_evento, nivel, probabilidad,
         algoritmo, version_modelo)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
"""


def verificar(conexion) -> Resultado:  # noqa: PLR0915 - es una lista de criterios
    r = Resultado()
    cur = conexion.cursor()
    print("\nCriterios de aceptacion de H1.13\n")

    # 1
    cur.execute("""
        SELECT count(*) FROM information_schema.tables
        WHERE table_schema = 'analitico' AND table_name = 'riesgo_auditoria'
    """)
    r.comprobar("1. la tabla analitico.riesgo_auditoria existe", cur.fetchone()[0] == 1)
    cur.execute("""
        SELECT count(*) FROM pg_trigger
        WHERE tgname = 'riesgo_auditoria_tg' AND NOT tgisinternal
    """)
    r.comprobar("   el disparador esta instalado sobre analitico.riesgo", cur.fetchone()[0] == 1)

    def auditoria() -> list[tuple]:
        cur.execute("""
            SELECT operacion, nivel_anterior, probabilidad_anterior, codigo_distrito
            FROM analitico.riesgo_auditoria ORDER BY id
        """)
        return cur.fetchall()

    cur.execute("DELETE FROM analitico.riesgo_auditoria")
    cur.execute("DELETE FROM analitico.riesgo")
    cur.execute("DELETE FROM analitico.riesgo_auditoria")

    # 2. El INSERT no audita.
    cur.execute(INSERTA, (DISTRITO, FECHA, "sequia", "bajo", 0.10, "xgboost", "v1"))
    r.comprobar(
        "2. un INSERT no deja registro: la fila no cambio nada, aparecio",
        len(auditoria()) == 0,
        f"dejo {len(auditoria())} registro(s)",
    )

    # 3. El UPDATE guarda el ANTERIOR.
    cur.execute(
        "UPDATE analitico.riesgo SET nivel = 'alto', probabilidad = 0.91 "
        "WHERE codigo_distrito = %s AND fecha = %s AND tipo_evento = 'sequia'",
        (DISTRITO, FECHA),
    )
    filas = auditoria()
    r.comprobar(
        "3. un UPDATE deja el valor ANTERIOR, no el nuevo",
        len(filas) == 1 and filas[0][0] == "UPDATE" and filas[0][1] == "bajo",
        f"guardo {filas[0][1] if filas else 'nada'}, se esperaba 'bajo'",
    )
    r.comprobar(
        "   y guarda tambien la probabilidad anterior",
        bool(filas) and filas[0][2] is not None and abs(float(filas[0][2]) - 0.10) < 1e-6,
    )

    # 5. Dos cambios, dos registros, en orden.
    cur.execute(
        "UPDATE analitico.riesgo SET nivel = 'medio' "
        "WHERE codigo_distrito = %s AND fecha = %s AND tipo_evento = 'sequia'",
        (DISTRITO, FECHA),
    )
    filas = auditoria()
    r.comprobar(
        "5. dos cambios dejan dos registros, en orden",
        len(filas) == 2 and [f[1] for f in filas] == ["bajo", "alto"],
        f"quedo {[f[1] for f in filas]}",
    )

    # 7. Un cambio RECHAZADO no deja rastro. Se auditan hechos, no intentos.
    antes = len(auditoria())
    cur.execute("SAVEPOINT sp")
    try:
        # `medio` para incendio lo prohibe la 007; aca se intenta sobre sequia
        # con una probabilidad imposible, que viola riesgo_probabilidad_ck.
        cur.execute(
            "UPDATE analitico.riesgo SET probabilidad = 85 "
            "WHERE codigo_distrito = %s AND fecha = %s",
            (DISTRITO, FECHA),
        )
        rechazado = False
    except Exception:  # noqa: BLE001
        rechazado = True
    cur.execute("ROLLBACK TO SAVEPOINT sp")
    r.comprobar(
        "7. un UPDATE que la base rechaza no deja rastro",
        rechazado and len(auditoria()) == antes,
        "se auditaron intentos, no hechos" if not rechazado else "",
    )

    # 6. Un UPDATE de varias filas deja un registro por fila.
    cur.execute("DELETE FROM analitico.riesgo_auditoria")
    for evento in ("lluvia_intensa", "incendio"):
        cur.execute(INSERTA, (DISTRITO, FECHA, evento, "bajo", None, None, None))
    cur.execute(
        "UPDATE analitico.riesgo SET nivel = 'alto' WHERE codigo_distrito = %s AND fecha = %s",
        (DISTRITO, FECHA),
    )
    filas = auditoria()
    r.comprobar(
        "6. un UPDATE de tres filas deja tres registros, uno por fila",
        len(filas) == 3,
        f"dejo {len(filas)}",
    )

    # 4. El DELETE audita, y el registro sobrevive.
    cur.execute("DELETE FROM analitico.riesgo_auditoria")
    cur.execute(
        "DELETE FROM analitico.riesgo WHERE codigo_distrito = %s AND fecha = %s AND "
        "tipo_evento = 'incendio'",
        (DISTRITO, FECHA),
    )
    filas = auditoria()
    r.comprobar(
        "4. un DELETE deja registro con el ultimo valor conocido",
        len(filas) == 1 and filas[0][0] == "DELETE" and filas[0][1] == "alto",
        f"quedo {filas}",
    )
    cur.execute(
        "SELECT count(*) FROM analitico.riesgo WHERE codigo_distrito = %s AND fecha = %s "
        "AND tipo_evento = 'incendio'",
        (DISTRITO, FECHA),
    )
    r.comprobar(
        "   la fila original ya no existe y su historia si",
        cur.fetchone()[0] == 0 and len(auditoria()) == 1,
    )

    # 8. Quien y cuando.
    cur.execute("""
        SELECT registrado_por IS NOT NULL, registrado_en IS NOT NULL
        FROM analitico.riesgo_auditoria ORDER BY id DESC LIMIT 1
    """)
    quien, cuando = cur.fetchone()
    r.comprobar("8. queda constancia de quien y cuando", bool(quien) and bool(cuando))

    # 9. Ningun CHECK volatil, que es lo que la 007 tuvo que quitar de la 006.
    cur.execute("""
        SELECT count(*) FROM pg_constraint
        WHERE conrelid = 'analitico.riesgo_auditoria'::regclass AND contype = 'c'
          AND lower(pg_get_constraintdef(oid)) ~ 'current_date|now\\(|current_timestamp'
    """)
    r.comprobar(
        "9. ninguna restriccion depende de la fecha de hoy",
        cur.fetchone()[0] == 0,
        "un CHECK volatil rompe la restauracion, como en I-18",
    )
    return r


def main() -> int:
    p = argparse.ArgumentParser(description="Criterios de aceptacion de H1.13.")
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
    print("\nH1.13 cumple sus criterios de aceptacion.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
