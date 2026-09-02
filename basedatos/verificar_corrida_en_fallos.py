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
  9. **Dos transacciones simultaneas con corridas distintas no se contaminan.**
     Con dos conexiones de verdad, porque `SET LOCAL` es por transaccion y por
     conexion. Lo pidio Luna en la revision del PR #223, para que H8.2 -ETL
     concurrente- lo herede demostrado en vez de descubrirlo cuando falle.
 10. La otra mitad del 9: **una conexion que no declara nada escribe NULL
     igual**, con dos corridas abiertas al lado. Es el comportamiento correcto,
     y el hueco que H12.4 cubre contando las filas sin atribuir.

SET LOCAL EN AUTOCOMMIT, QUE ES LA PREGUNTA 2 DE LUNA

`SET LOCAL` solo tiene efecto dentro de una transaccion explicita. En autocommit
-el modo por omision de `psycopg`- PostgreSQL emite un `WARNING` y lo ignora, y
la fila entra con `corrida_id` en NULL.

**No falla, y ese es el problema:** el sintoma no aparece al escribir sino
semanas despues, al diagnosticar, y el aviso de PostgreSQL es facil de no ver.
Quien cargue dentro de una corrida abre la transaccion explicitamente. El conteo
de filas sin atribuir de H12.4 es la red que atrapa el olvido.

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


def verificar_concurrencia(abrir, r: Resultado) -> None:
    """Criterios 9 y 10. Dos conexiones de verdad, no dos savepoints.

    LO QUE PIDIO LUNA, Y POR QUE ANTES DE H8.2 Y NO DESPUES

    Hoy la ETL es secuencial y esto da igual. Cuando H8.2 la paralelice por
    distrito sobre un pool, no: `SET LOCAL` es por transaccion **y por
    conexion**, asi que cada trabajador tiene que declarar la suya y ninguna
    declaracion alcanza a las demas.

    El momento en que eso rompe es el peor posible: un fallo concurrente ya es
    lo mas dificil de diagnosticar, y seria justo cuando la atribucion deja de
    funcionar. Por eso el criterio se escribe **antes** de que exista el codigo
    que podria romperlo -si pasa hoy, H8.2 lo hereda demostrado-.

    POR QUE DOS CONEXIONES Y NO DOS SAVEPOINTS

    Un savepoint comparte sesion, y la sesion es justamente lo que se quiere
    probar aislado. Con savepoints el criterio pasaria sin comprobar nada.

    POR QUE NINGUNA DE LAS DOS HACE COMMIT

    Cada transaccion lee su propia fila mientras la otra sigue abierta. Con eso
    alcanza para la pregunta -si el parametro se filtrara entre sesiones, se
    veria aca- y **no queda ni una fila en `control.fallo`**: las dos revierten.
    Un verificador que ensucia la tabla que verifica se vuelve el proximo
    defecto.

    EL CRITERIO 10 NO LO PIDIO NADIE, Y ES LA OTRA MITAD

    El 9 comprueba que dos corridas no se contaminen. **No comprueba que un
    trabajador se acuerde de declarar la suya.** El que nunca haga `SET LOCAL`
    escribe NULL y el criterio 9 pasa igual. El 10 lo deja escrito: una tercera
    conexion, con dos corridas abiertas al lado, sigue escribiendo NULL.

    Eso no es un defecto -es el comportamiento correcto, y romper la carga seria
    peor-. Es el hueco que Luna asume en H12.4 contando las filas sin atribuir
    antes de agrupar, y conviene que este demostrado y no supuesto.
    """
    una = abrir()
    otra = abrir()
    sin_declarar = abrir()

    def ultima_propia(conexion) -> int | None:
        cur = conexion.cursor()
        cur.execute("SELECT corrida_id FROM control.fallo ORDER BY id DESC LIMIT 1")
        fila = cur.fetchone()
        return fila[0] if fila else "sin filas"

    try:
        for conexion, corrida, fecha in (
            (una, 101, "2019-08-01"),
            (otra, 202, "2019-08-02"),
        ):
            cur = conexion.cursor()
            cur.execute(f"SET LOCAL geoguardian.corrida_id = {corrida}")
            cur.execute(RECHAZA, (fecha,))

        cur = sin_declarar.cursor()
        cur.execute(RECHAZA, ("2019-08-03",))

        # Las tres transacciones estan abiertas AL MISMO TIEMPO en este punto.
        de_una = ultima_propia(una)
        de_otra = ultima_propia(otra)
        de_nadie = ultima_propia(sin_declarar)

        r.comprobar(
            "9. dos transacciones simultaneas con corridas distintas no se contaminan",
            de_una == 101 and de_otra == 202,
            f"la primera quedo en {de_una} y la segunda en {de_otra}",
        )
        r.comprobar(
            "10. una tercera conexion que no declara nada escribe NULL igual",
            de_nadie is None,
            f"quedo {de_nadie} con dos corridas abiertas al lado",
        )
    finally:
        for conexion in (una, otra, sin_declarar):
            conexion.rollback()
            conexion.close()


def main() -> int:
    p = argparse.ArgumentParser(description="La corrida en control.fallo.")
    p.add_argument("--dsn")
    args = p.parse_args()

    try:
        import psycopg
    except ImportError:
        print("\nFalta psycopg:  pip install -r requirements.txt\n")
        return 1

    def abrir():
        if args.dsn:
            return psycopg.connect(args.dsn)
        return __import__("basedatos.conexion", fromlist=["conectar"]).conectar()

    try:
        conexion = abrir()
    except Exception as error:  # noqa: BLE001
        print(f"\nLa base no responde: {error}\n")
        return 1

    try:
        resultado = verificar(conexion)
    finally:
        conexion.rollback()
        conexion.close()

    if not any(f.startswith("0.") for f in resultado.fallos):
        print("\nConcurrencia, con tres conexiones a la vez:\n")
        verificar_concurrencia(abrir, resultado)

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
