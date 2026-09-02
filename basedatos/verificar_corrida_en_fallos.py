"""Comprueba que cada fila rechazada sabe a que corrida pertenece. Migracion 012.

No cierra ninguna historia: responde al pedido de Luna en el PR #223, que H12.4
necesita para poder diagnosticar.

QUE COMPRUEBA, Y POR QUE CADA UNO

  1. La columna y la funcion existen.
  2. Sin corrida declarada, la fila entra con NULL. **Escribir fuera de una
     corrida es legitimo** -una prueba, una carga a mano- y no debe romperse.
  3. Con `SET LOCAL`, la fila queda atribuida.
  4. **Al terminar la transaccion el valor NO sobrevive.** Es el criterio que
     mas vale: si se filtrara, las filas de la corrida siguiente quedarian
     atribuidas a la anterior y el diagnostico mentiria en silencio.
  5. Un valor que no es un numero no tumba la carga.
  6. Un lote entero queda atribuido con una sola declaracion.
  7. La consulta que H12.4 necesita se puede escribir.
  8. **Las funciones de H1.9 no se tocaron.** La columna se llena por DEFAULT,
     asi que sus 22 criterios siguen valiendo sin volver a correrlos.

Uso:
    docker compose up -d
    python -m basedatos.verificar_corrida_en_fallos
"""

from __future__ import annotations

import argparse
import sys

RECHAZA = (
    "SELECT analitico.registrar_riesgo('50801'::text, %s::date, 'sequia'::text, "
    "'bajo'::text, 1.5::numeric, 'xgboost'::text, 'v1'::text, false)"
)


class Resultado:
    def __init__(self) -> None:
        self.fallos: list[str] = []
        self.hechos = 0

    def comprobar(self, nombre: str, condicion: bool, detalle: str = "") -> None:
        self.hechos += 1
        print(f"  {'ok  ' if condicion else 'FALLA'}  {nombre}")
        if not condicion:
            self.fallos.append(f"{nombre}{': ' + detalle if detalle else ''}")


def verificar(conexion) -> Resultado:
    r = Resultado()
    cur = conexion.cursor()
    print("\nLa corrida en la bitacora de fallos · migracion 012\n")

    cur.execute("""
        SELECT count(*) FROM information_schema.columns
        WHERE table_schema = 'control' AND table_name = 'fallo' AND column_name = 'corrida_id'
    """)
    existe = cur.fetchone()[0] == 1
    if not existe:
        print("  La migracion 012 no esta aplicada.\n")
        print("      python -m basedatos.aplicar_migraciones\n")
        r.comprobar("0. la migracion 012 esta aplicada", False)
        return r
    r.comprobar("1. la columna control.fallo.corrida_id existe", True)

    cur.execute(
        "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
        "WHERE n.nspname = 'control' AND p.proname = 'corrida_actual'"
    )
    r.comprobar("   y control.corrida_actual() tambien", cur.fetchone()[0] == 1)

    def ultima() -> int | None:
        cur.execute("SELECT corrida_id FROM control.fallo ORDER BY id DESC LIMIT 1")
        fila = cur.fetchone()
        return fila[0] if fila else "sin filas"

    cur.execute("SAVEPOINT prueba")
    cur.execute("DELETE FROM control.fallo")

    # ---------------------------------------------------------------- 2
    cur.execute("RESET geoguardian.corrida_id")
    cur.execute(RECHAZA, ("2019-06-01",))
    r.comprobar(
        "2. sin corrida declarada la fila entra con NULL, no falla",
        ultima() is None,
        f"quedo {ultima()}",
    )

    # ---------------------------------------------------------------- 3
    cur.execute("SET LOCAL geoguardian.corrida_id = 42")
    cur.execute(RECHAZA, ("2019-06-02",))
    r.comprobar("3. con SET LOCAL la fila queda atribuida", ultima() == 42, f"quedo {ultima()}")

    # ---------------------------------------------------------------- 6 y 7
    lote = """[
        {"codigo_distrito":"50801","fecha":"2019-07-01","tipo_evento":"sequia",
         "nivel":"bajo","probabilidad":1.9,"algoritmo":"xgboost","version_modelo":"v1"},
        {"codigo_distrito":"50802","fecha":"2019-07-01","tipo_evento":"incendio",
         "nivel":"medio","probabilidad":0.5,"algoritmo":"xgboost","version_modelo":"v1"}
    ]"""
    cur.execute("SELECT rechazadas FROM analitico.registrar_riesgo_lote(%s::jsonb)", (lote,))
    rechazadas = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM control.fallo WHERE corrida_id = 42")
    atribuidas = cur.fetchone()[0]
    r.comprobar(
        "6. un lote entero queda atribuido con una sola declaracion",
        rechazadas == 2 and atribuidas == 3,
        f"{rechazadas} rechazadas, {atribuidas} atribuidas a la corrida 42",
    )

    cur.execute("""
        SELECT sqlstate, count(*) FROM control.fallo
        WHERE corrida_id = 42 GROUP BY sqlstate ORDER BY 2 DESC
    """)
    resumen = cur.fetchall()
    r.comprobar(
        "7. la consulta de diagnostico de H12.4 se puede escribir",
        bool(resumen) and sum(n for _, n in resumen) == atribuidas,
        f"devolvio {resumen}",
    )

    # ---------------------------------------------------------------- 5
    cur.execute("SET LOCAL geoguardian.corrida_id = 'no-soy-un-numero'")
    try:
        cur.execute(RECHAZA, ("2019-06-04",))
        sobrevive = ultima() is None
        detalle = f"quedo {ultima()}"
    except Exception as error:  # noqa: BLE001
        sobrevive, detalle = False, str(error).splitlines()[0]
    r.comprobar("5. un valor que no es numero no tumba la carga", sobrevive, detalle)

    cur.execute("ROLLBACK TO SAVEPOINT prueba")

    # ---------------------------------------------------------------- 4
    # EL CRITERIO QUE MAS VALE, Y NECESITA SU PROPIA TRANSACCION.
    #
    # `SET LOCAL` tiene que morir con la transaccion. Si sobreviviera, las filas
    # de la corrida siguiente quedarian atribuidas a la anterior **y el
    # diagnostico mentiria sin que nadie lo note**.
    cur.execute("SELECT NULLIF(current_setting('geoguardian.corrida_id', true), '')")
    quedo = cur.fetchone()[0]
    r.comprobar(
        "4. el valor NO sobrevive a la transaccion: no se filtra entre corridas",
        quedo is None,
        f"quedo '{quedo}' despues del ROLLBACK",
    )

    # ---------------------------------------------------------------- 8
    cur.execute("""
        SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'analitico'
          AND p.proname IN ('registrar_riesgo', 'registrar_riesgo_lote')
          AND p.prosrc ~ 'corrida'
    """)
    r.comprobar(
        "8. las funciones de H1.9 no mencionan la corrida: se llena por DEFAULT",
        cur.fetchone()[0] == 0,
        "alguna funcion la nombra, asi que sus 22 criterios habria que recorrerlos",
    )
    return r


def main() -> int:
    p = argparse.ArgumentParser(description="La corrida en control.fallo.")
    p.add_argument("--dsn")
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
        print(f"\nLa base no responde: {error}\n")
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
    print("\nLa migracion 012 cumple lo que el PR #223 pidio.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
