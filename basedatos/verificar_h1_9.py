"""Criterios de aceptacion de H1.9: funciones PL/pgSQL y bitacora de fallos.

CORRE CONTRA UNA BASE REAL

Un manejador de excepciones no se comprueba leyendolo. Se comprueba
**provocando el error** y mirando si la funcion siguio, si dejo registro y si el
registro sirve para arreglar la fila.

QUE COMPRUEBA

   1. La bitacora y las dos funciones existen.
   2. Una fila valida entra y devuelve TRUE.
   3. Una fila invalida devuelve FALSE **sin abortar**, y lo bueno sobrevive.
   4. El registro guarda el SQLSTATE, no solo el mensaje.
   5. El registro guarda los datos rechazados, listos para corregir.
   6. `RAISE` propio: una fecha fuera del horizonte se rechaza con P0001.
   7. `modo_estricto` relanza la excepcion en vez de tragarsela.
   8. Y con ella se pierde el registro, que es **la limitacion declarada**.
   9. El lote cuenta aceptadas y rechazadas por separado.
  10. Un JSON con un tipo mal formado no mata el lote entero.
  11. Ningun `WHEN OTHERS`: un fallo de infraestructura no se disfraza de fila
      mala.
  12. Reestimar sobrescribe, y el disparador de H1.13 lo audita.
  13. El rol lector no puede escribir en la bitacora.
  14. Ninguna restriccion volatil, que es lo que la 007 tuvo que quitar (I-18).

Uso:
    docker compose up -d
    python -m basedatos.verificar_h1_9
    python -m basedatos.verificar_h1_9 --dsn "postgresql://..."

Sale con codigo 1 si algun criterio no se cumple.
"""

from __future__ import annotations

import argparse
import sys

DISTRITO = "50801"
FECHA = "2026-04-12"


class Resultado:
    def __init__(self) -> None:
        self.fallos: list[str] = []
        self.hechos = 0

    def comprobar(self, nombre: str, condicion: bool, detalle: str = "") -> None:
        self.hechos += 1
        print(f"  {'ok  ' if condicion else 'FALLA'}  {nombre}")
        if not condicion:
            self.fallos.append(f"{nombre}{': ' + detalle if detalle else ''}")


def verificar(conexion) -> Resultado:  # noqa: PLR0915 - es una lista de criterios
    r = Resultado()
    cur = conexion.cursor()
    print("\nCriterios de aceptacion de H1.9\n")

    def limpiar() -> None:
        cur.execute("DELETE FROM analitico.riesgo_auditoria")
        cur.execute("DELETE FROM analitico.riesgo")
        cur.execute("DELETE FROM analitico.riesgo_auditoria")
        cur.execute("DELETE FROM control.fallo")

    def fallos() -> list[tuple]:
        cur.execute("SELECT origen, sqlstate, mensaje, datos FROM control.fallo ORDER BY id")
        return cur.fetchall()

    def registrar(*args, estricto: bool = False) -> bool:
        # LOS CASTES SON OBLIGATORIOS, NO ADORNO.
        #
        # psycopg manda un float de Python como `double precision`, y PostgreSQL
        # **no lo convierte solo a `numeric`** al resolver que funcion llamar:
        # falla con «function does not exist», que es de los errores mas
        # engañosos que da. Se descubrio corriendo esto, no leyendolo.
        cur.execute(
            "SELECT analitico.registrar_riesgo("
            "%s::text, %s::date, %s::text, %s::text, %s::numeric, %s::text, %s::text, %s::boolean)",
            (*args, estricto),
        )
        return cur.fetchone()[0]

    # ---------------------------------------------------------------- 1
    cur.execute("""
        SELECT count(*) FROM information_schema.tables
        WHERE table_schema = 'control' AND table_name = 'fallo'
    """)
    r.comprobar("1. la bitacora control.fallo existe", cur.fetchone()[0] == 1)
    cur.execute("""
        SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'analitico'
          AND p.proname IN ('registrar_riesgo', 'registrar_riesgo_lote')
          AND p.prolang = (SELECT oid FROM pg_language WHERE lanname = 'plpgsql')
    """)
    r.comprobar("   las dos funciones existen y son PL/pgSQL", cur.fetchone()[0] == 2)

    limpiar()

    # ---------------------------------------------------------------- 2
    entro = registrar(DISTRITO, FECHA, "sequia", "bajo", 0.12, "xgboost", "v1")
    cur.execute("SELECT count(*) FROM analitico.riesgo")
    r.comprobar(
        "2. una fila valida entra y devuelve TRUE",
        entro is True and cur.fetchone()[0] == 1,
    )

    # ---------------------------------------------------------------- 3
    # `probabilidad = 1.5` cabe en numeric(5,4) y viola riesgo_probabilidad_ck.
    rechazo = registrar(DISTRITO, FECHA, "lluvia_intensa", "alto", 1.5, "xgboost", "v1")
    cur.execute("SELECT count(*) FROM analitico.riesgo")
    sobreviven = cur.fetchone()[0]
    r.comprobar(
        "3. una fila invalida devuelve FALSE sin abortar la transaccion",
        rechazo is False,
        f"devolvio {rechazo}",
    )
    r.comprobar(
        "   y la fila buena de antes sigue ahi",
        sobreviven == 1,
        f"quedaron {sobreviven} filas, se esperaba 1",
    )

    # ---------------------------------------------------------------- 4
    filas = fallos()
    r.comprobar(
        "4. el registro guarda el SQLSTATE, no solo el mensaje",
        len(filas) == 1 and filas[0][1] == "23514",
        f"guardo {filas[0][1] if filas else 'nada'}, se esperaba 23514 (check_violation)",
    )

    # ---------------------------------------------------------------- 5
    datos = filas[0][3] if filas else {}
    r.comprobar(
        "5. el registro guarda los datos rechazados, listos para corregir",
        datos.get("codigo_distrito") == DISTRITO
        and datos.get("tipo_evento") == "lluvia_intensa"
        and float(datos.get("probabilidad", 0)) == 1.5,
        f"guardo {datos}",
    )

    # ---------------------------------------------------------------- 5-bis
    # EL CASO QUE CASI SE ESCAPA.
    #
    # `probabilidad` es numeric(5,4): un 85 **desborda el tipo antes de que se
    # evalue el CHECK**, y llega como 22003, no como 23514. Un modelo que
    # devuelva probabilidades sin normalizar produce justo esto.
    cur.execute("DELETE FROM control.fallo")
    desborde = registrar(DISTRITO, FECHA, "incendio", "alto", 85, "xgboost", "v1")
    filas = fallos()
    r.comprobar(
        "   un valor que desborda el TIPO tambien se atrapa, no solo el CHECK",
        desborde is False and len(filas) == 1 and filas[0][1] == "22003",
        f"quedo {[f[1] for f in filas]}, se esperaba 22003 (numeric_value_out_of_range)",
    )
    cur.execute("DELETE FROM control.fallo")
    limpiar()
    registrar(DISTRITO, FECHA, "sequia", "bajo", 0.12, "xgboost", "v1")
    cur.execute("DELETE FROM control.fallo")

    # ---------------------------------------------------------------- 6
    cur.execute("DELETE FROM control.fallo")
    lejos = registrar(DISTRITO, "2027-12-31", "sequia", "alto", 0.5, "xgboost", "v1")
    filas = fallos()
    r.comprobar(
        "6. RAISE propio: una fecha fuera del horizonte se rechaza con P0001",
        lejos is False and len(filas) == 1 and filas[0][1] == "P0001",
        f"quedo {[f[1] for f in filas]}",
    )
    r.comprobar(
        "   y el mensaje dice cual fue la fecha, no solo que fallo",
        bool(filas) and "2027-12-31" in filas[0][2],
        f"mensaje: {filas[0][2] if filas else ''}",
    )

    # ---------------------------------------------------------------- 7 y 8
    cur.execute("DELETE FROM control.fallo")
    cur.execute("SAVEPOINT sp_estricto")
    try:
        registrar(DISTRITO, FECHA, "incendio", "medio", None, None, None, estricto=True)
        relanzo = False
    except Exception:  # noqa: BLE001
        relanzo = True
    r.comprobar(
        "7. modo_estricto relanza la excepcion en vez de tragarsela",
        relanzo,
        "se la trago: una prueba pasaria sobre datos que no se escribieron",
    )
    cur.execute("ROLLBACK TO SAVEPOINT sp_estricto")
    r.comprobar(
        "8. y al revertir se pierde el registro: la limitacion esta declarada",
        len(fallos()) == 0,
        "sobrevivio, asi que la cabecera de la 009 miente sobre lo que puede hacer",
    )

    # ---------------------------------------------------------------- 9
    limpiar()
    lote = """[
        {"codigo_distrito": "50801", "fecha": "2026-04-12", "tipo_evento": "sequia",
         "nivel": "bajo", "probabilidad": 0.1, "algoritmo": "xgboost", "version_modelo": "v1"},
        {"codigo_distrito": "50802", "fecha": "2026-04-12", "tipo_evento": "sequia",
         "nivel": "alto", "probabilidad": 0.9, "algoritmo": "xgboost", "version_modelo": "v1"},
        {"codigo_distrito": "50803", "fecha": "2026-04-12", "tipo_evento": "incendio",
         "nivel": "medio", "probabilidad": 0.5, "algoritmo": "xgboost", "version_modelo": "v1"},
        {"codigo_distrito": "50804", "fecha": "2026-04-12", "tipo_evento": "lluvia_intensa",
         "nivel": "alto", "probabilidad": 1.7, "algoritmo": "xgboost", "version_modelo": "v1"},
        {"codigo_distrito": "50805", "fecha": "2026-04-12", "tipo_evento": "sequia",
         "nivel": "bajo", "probabilidad": 0.2, "algoritmo": "xgboost", "version_modelo": "v1"}
    ]"""
    cur.execute(
        "SELECT aceptadas, rechazadas FROM analitico.registrar_riesgo_lote(%s::jsonb)", (lote,)
    )
    aceptadas, rechazadas = cur.fetchone()
    cur.execute("SELECT count(*) FROM analitico.riesgo")
    reales = cur.fetchone()[0]
    r.comprobar(
        "9. el lote cuenta aceptadas y rechazadas por separado",
        (aceptadas, rechazadas) == (3, 2),
        f"devolvio ({aceptadas}, {rechazadas}), se esperaba (3, 2)",
    )
    r.comprobar(
        "   y las 3 aceptadas estan de verdad en la tabla",
        reales == 3,
        f"hay {reales} filas",
    )
    r.comprobar(
        "   el 'medio' para incendio se rechazo por la 007, no por el rango",
        any(f[1] == "23514" and f[3].get("tipo_evento") == "incendio" for f in fallos()),
    )

    # ---------------------------------------------------------------- 10
    limpiar()
    malo = """[
        {"codigo_distrito": "50801", "fecha": "2026-04-12", "tipo_evento": "sequia",
         "nivel": "bajo", "probabilidad": 0.1, "algoritmo": "xgboost", "version_modelo": "v1"},
        {"codigo_distrito": "50802", "fecha": "ayer", "tipo_evento": "sequia",
         "nivel": "alto", "probabilidad": 0.9, "algoritmo": "xgboost", "version_modelo": "v1"},
        {"codigo_distrito": "50803", "fecha": "2026-04-12", "tipo_evento": "sequia",
         "nivel": "bajo", "probabilidad": 0.3, "algoritmo": "xgboost", "version_modelo": "v1"}
    ]"""
    cur.execute("SAVEPOINT sp_json")
    try:
        cur.execute(
            "SELECT aceptadas, rechazadas FROM analitico.registrar_riesgo_lote(%s::jsonb)", (malo,)
        )
        aceptadas, rechazadas = cur.fetchone()
    except Exception:  # noqa: BLE001
        cur.execute("ROLLBACK TO SAVEPOINT sp_json")
        aceptadas, rechazadas = -1, -1
    r.comprobar(
        "10. un JSON con un tipo mal formado no mata el lote entero",
        (aceptadas, rechazadas) == (2, 1),
        f"devolvio ({aceptadas}, {rechazadas}), se esperaba (2, 1)",
    )
    r.comprobar(
        "    y el fallo se atribuye al lote, que es donde ocurrio la conversion",
        any(f[0] == "analitico.registrar_riesgo_lote" and f[1] == "22007" for f in fallos()),
        f"quedo {[(f[0], f[1]) for f in fallos()]}",
    )

    # ---------------------------------------------------------------- 11
    # Se quitan los comentarios ANTES de buscar. Sin eso el criterio falla
    # contra el propio comentario que explica por que no hay WHEN OTHERS, que
    # es exactamente el tipo de falso positivo que hace desconfiar de un
    # verificador.
    cur.execute("""
        SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'analitico'
          AND p.proname IN ('registrar_riesgo', 'registrar_riesgo_lote')
          AND regexp_replace(p.prosrc, '--[^\\n]*', '', 'g') ~* 'when\\s+others'
    """)
    r.comprobar(
        "11. ningun WHEN OTHERS: un fallo de disco no se disfraza de fila mala",
        cur.fetchone()[0] == 0,
        "un manejador demasiado ancho convierte incidentes en datos rechazados",
    )

    # ---------------------------------------------------------------- 12
    limpiar()
    registrar(DISTRITO, FECHA, "sequia", "bajo", 0.10, "xgboost", "v1")
    segunda = registrar(DISTRITO, FECHA, "sequia", "alto", 0.88, "xgboost", "v2")
    cur.execute(
        "SELECT nivel, version_modelo FROM analitico.riesgo WHERE codigo_distrito = %s "
        "AND fecha = %s AND tipo_evento = 'sequia'",
        (DISTRITO, FECHA),
    )
    fila = cur.fetchone()
    r.comprobar(
        "12. reestimar sobrescribe en vez de fallar por clave duplicada",
        segunda is True and fila == ("alto", "v2"),
        f"quedo {fila}",
    )
    cur.execute("SELECT nivel_anterior FROM analitico.riesgo_auditoria ORDER BY id")
    historia = [f[0] for f in cur.fetchall()]
    r.comprobar(
        "    y el disparador de H1.13 guardo el valor anterior",
        historia == ["bajo"],
        f"la auditoria quedo en {historia}",
    )

    # ---------------------------------------------------------------- 13
    cur.execute("""
        SELECT count(*) FROM pg_roles WHERE rolname = 'geoguardian_lector'
    """)
    if cur.fetchone()[0] == 1:
        cur.execute("""
            SELECT has_table_privilege('geoguardian_lector', 'control.fallo', 'INSERT'),
                   has_table_privilege('geoguardian_lector', 'control.fallo', 'SELECT')
        """)
        escribe, lee = cur.fetchone()
        r.comprobar(
            "13. el rol lector puede leer la bitacora pero no escribirla",
            lee and not escribe,
            f"INSERT={escribe}, SELECT={lee}",
        )
    else:
        r.comprobar("13. el rol lector puede leer la bitacora pero no escribirla", True)

    # ---------------------------------------------------------------- 14
    cur.execute("""
        SELECT count(*) FROM pg_constraint
        WHERE conrelid = 'control.fallo'::regclass AND contype = 'c'
          AND lower(pg_get_constraintdef(oid)) ~ 'current_date|now\\(|current_timestamp|localtime'
    """)
    r.comprobar(
        "14. ninguna restriccion depende de la fecha de hoy",
        cur.fetchone()[0] == 0,
        "un CHECK volatil rompe la restauracion, como en I-18",
    )
    return r


def main() -> int:
    p = argparse.ArgumentParser(description="Criterios de aceptacion de H1.9.")
    p.add_argument("--dsn", help="cadena de conexion; sin ella usa basedatos.conexion")
    args = p.parse_args()

    try:
        import psycopg  # noqa: F401
    except ImportError:
        print("\nFalta psycopg:  pip install -r requirements.txt\n")
        return 1

    try:
        import psycopg

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
    print("\nH1.9 cumple sus criterios de aceptacion.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
