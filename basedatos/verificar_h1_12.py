"""Criterios de aceptacion de H1.12, los indices espaciales y compuestos.

QUE COMPRUEBA, Y POR QUE NO BASTA CON QUE EXISTAN

Un indice que existe y el planificador nunca elige es coste puro: ocupa espacio,
cuesta en cada escritura y no devuelve nada. Por eso **cada criterio mira el
plan**, no el catalogo.

  1. Los tres indices existen, y con el metodo correcto (btree, btree, GIST).
  2. El de riesgo lo ELIGE el planificador, y ademas sin tocar la tabla.
  3. El de focos lo elige, y el orden de sus columnas es el que sirve.
  4. Sin el de riesgo el plan seria un recorrido secuencial.
  5. El GIST lo elige la consulta de ST_Contains.
  6. `medicion_fecha_ix` NO existe: se midio y se descarto.
  7. Ningun indice duplica a la clave primaria de su tabla.
  8. Las escrituras siguen funcionando con los indices puestos.

El 6 es el que mas cuesta defender y el que mas dice: comprueba que **no** se
agrego algo. Una historia de indices que solo comprueba lo que agrego no puede
distinguirse de una que agrego todo lo que se le ocurrio.

Uso:
    docker compose up -d
    python -m basedatos.verificar_h1_12

Sale con codigo 1 si algun criterio no se cumple.
"""

from __future__ import annotations

import argparse
import sys


class Resultado:
    def __init__(self) -> None:
        self.fallos: list[str] = []
        self.hechos = 0

    def comprobar(self, nombre: str, condicion: bool, detalle: str = "") -> None:
        self.hechos += 1
        print(f"  {'ok  ' if condicion else 'FALLA'}  {nombre}")
        if not condicion:
            self.fallos.append(f"{nombre}{': ' + detalle if detalle else ''}")


def plan_de(cur, sql: str, parametros: tuple = ()) -> str:
    cur.execute("EXPLAIN " + sql, parametros)
    return "\n".join(f[0] for f in cur.fetchall())


def verificar(conexion) -> Resultado:  # noqa: PLR0915 - es una lista de criterios
    r = Resultado()
    cur = conexion.cursor()
    print("\nCriterios de aceptacion de H1.12\n")

    # ---------------------------------------------------------------- 0
    # ¿ESTA APLICADA LA MIGRACION? Se pregunta antes de nada.
    #
    # Sin esto, una base sin la 011 produce «los tres indices existen: FALLA» y
    # «encontrados []», que suena a que la migracion esta rota cuando lo que pasa
    # es que no se corrio. Un verificador tiene que distinguir «esto no cumple»
    # de «esto no se hizo todavia».
    cur.execute("""
        SELECT count(*) FROM pg_class WHERE relkind = 'i'
          AND relname IN ('riesgo_fecha_evento_ix', 'foco_distrito_fecha_ix',
                          'distrito_geometria_gix')
    """)
    if cur.fetchone()[0] == 0:
        print("  La migracion 011 no esta aplicada en esta base.\n")
        print("  Ninguno de los tres indices existe todavia. No es un defecto: es")
        print("  un paso que falta.\n")
        print("      python -m basedatos.aplicar_migraciones\n")
        r.comprobar("0. la migracion 011 esta aplicada", False, "falta aplicarla")
        return r

    # ---------------------------------------------------------------- 1
    cur.execute("""
        SELECT c.relname, am.amname
        FROM pg_class c
        JOIN pg_am am ON am.oid = c.relam
        WHERE c.relkind = 'i'
          AND c.relname IN ('riesgo_fecha_evento_ix', 'foco_distrito_fecha_ix',
                            'distrito_geometria_gix')
        ORDER BY c.relname
    """)
    metodos = dict(cur.fetchall())
    r.comprobar(
        "1. los tres indices existen",
        len(metodos) == 3,
        f"encontrados {sorted(metodos)}",
    )
    r.comprobar(
        "   y el espacial usa GIST, no btree",
        metodos.get("distrito_geometria_gix") == "gist",
        f"usa {metodos.get('distrito_geometria_gix')}",
    )

    # ---------------------------------------------------------------- 2
    sql_riesgo = (
        "SELECT codigo_distrito, nivel FROM analitico.riesgo "
        "WHERE fecha = %s AND tipo_evento = %s"
    )
    # SI LA TABLA ESTA VACIA, EL VERIFICADOR SE FABRICA EL DATO.
    #
    # `analitico.riesgo` se llena cuando H3.6 decida que modelo escribe, y hasta
    # entonces esta vacia en casi todas las maquinas. Sobre una tabla vacia el
    # planificador recorre siempre —no hay nada que indexar— asi que el criterio
    # daria FALLA por una razon que no tiene que ver con el indice.
    #
    # Se insertan filas suficientes para que la eleccion sea significativa, se
    # mide, y **se revierte**. Es lo mismo que hace verificar_h1_9: un criterio
    # que solo se puede comprobar cuando alguien mas ya cargo datos no es un
    # criterio, es una espera.
    cur.execute("SELECT count(*) FROM analitico.riesgo")
    fabricado = cur.fetchone()[0] < 5000
    if fabricado:
        print("  (analitico.riesgo tiene pocas filas: se fabrican para medir y se revierten)")
        cur.execute("SAVEPOINT datos_fabricados")
        cur.execute("""
            INSERT INTO analitico.riesgo
                (codigo_distrito, fecha, tipo_evento, nivel, algoritmo, version_modelo)
            SELECT d.codigo, dia::date, e.tipo,
                   CASE WHEN random() < 0.2 THEN 'alto' ELSE 'bajo' END,
                   -- `algoritmo` tiene su propio CHECK con la lista cerrada de
                   -- D-09: no vale poner 'verificador'. Se usa uno legitimo y la
                   -- version dice de donde salio, que es lo que permite
                   -- distinguirlo si alguna vez sobreviviera al ROLLBACK.
                   'linea_base_climatologica', 'verificador-h1.12'
            FROM geo.distrito d
            CROSS JOIN generate_series(DATE '2020-01-01', DATE '2022-12-31', '1 day') AS dia
            CROSS JOIN (VALUES ('sequia'), ('lluvia_intensa'), ('incendio')) AS e(tipo)
            WHERE d.codigo_canton = 508
            ON CONFLICT DO NOTHING
        """)
        cur.execute("ANALYZE analitico.riesgo")

    cur.execute("SELECT fecha, tipo_evento FROM analitico.riesgo LIMIT 1")
    fila = cur.fetchone()
    if fila is None:
        r.comprobar(
            "2. el indice de riesgo se usa",
            False,
            "no hay filas ni se pudieron fabricar: ¿existen los distritos de geo.distrito?",
        )
        return r
    plan = plan_de(cur, sql_riesgo, fila)
    r.comprobar(
        "2. el planificador elige riesgo_fecha_evento_ix",
        "riesgo_fecha_evento_ix" in plan,
        f"plan: {plan.splitlines()[0] if plan else ''}",
    )
    r.comprobar(
        "   y resuelve la consulta sin tocar la tabla (Index Only Scan)",
        "Index Only Scan" in plan,
        "el INCLUDE no esta sirviendo para lo que se puso",
    )

    # ---------------------------------------------------------------- 3
    cur.execute(
        "SELECT codigo_distrito FROM crudo.foco_calor WHERE codigo_distrito IS NOT NULL LIMIT 1"
    )
    fila = cur.fetchone()
    if fila is None:
        r.comprobar(
            "3. el indice de focos se usa",
            False,
            "crudo.foco_calor esta vacia. Se carga con: python -m backend.etl.cargar_focos",
        )
    else:
        plan = plan_de(
            cur,
            "SELECT count(*) FROM crudo.foco_calor "
            "WHERE codigo_distrito = %s AND fecha BETWEEN %s AND %s",
            (fila[0], "2000-01-01", "2024-12-31"),
        )
        r.comprobar(
            "3. el planificador elige foco_distrito_fecha_ix",
            "foco_distrito_fecha_ix" in plan,
            f"plan: {plan.splitlines()[0] if plan else ''}",
        )
        cur.execute("""
            SELECT pg_get_indexdef(c.oid) FROM pg_class c
            WHERE c.relname = 'foco_distrito_fecha_ix'
        """)
        definicion = cur.fetchone()
        r.comprobar(
            "   con codigo_distrito primero: igualdad antes que rango",
            definicion is not None and "(codigo_distrito, fecha)" in definicion[0],
            f"definicion: {definicion[0] if definicion else 'no existe'}",
        )

    # ---------------------------------------------------------------- 4
    # SIN EL INDICE, ¿QUE HARIA? Se quita dentro de un savepoint y se mira.
    #
    # Es la mitad «antes» de los «planes antes y despues» que pide la historia, y
    # no se puede obtener leyendo: hay que quitarlo y preguntar.
    cur.execute("SAVEPOINT sin_indice")
    try:
        cur.execute("DROP INDEX analitico.riesgo_fecha_evento_ix")
        cur.execute("SELECT fecha, tipo_evento FROM analitico.riesgo LIMIT 1")
        antes = plan_de(cur, sql_riesgo, cur.fetchone())
        secuencial = "Seq Scan" in antes
        detalle = antes.splitlines()[0] if antes else ""
    except Exception as error:  # noqa: BLE001
        secuencial, detalle = False, str(error).splitlines()[0]
    cur.execute("ROLLBACK TO SAVEPOINT sin_indice")
    r.comprobar(
        "4. sin ese indice el plan es un recorrido secuencial",
        secuencial,
        f"plan sin indice: {detalle}",
    )

    # ---------------------------------------------------------------- 5
    cur.execute("SELECT count(*) FROM pg_extension WHERE extname = 'postgis'")
    if cur.fetchone()[0] == 0:
        r.comprobar(
            "5. el GIST se usa en ST_Contains", False, "PostGIS no esta instalado en esta base"
        )
    else:
        plan = plan_de(
            cur,
            "SELECT d.codigo FROM geo.distrito d "
            "WHERE ST_Contains(d.geometria, ST_SetSRID(ST_MakePoint(%s, %s), 4326))",
            (-84.97, 10.47),
        )
        # Con ocho filas el planificador puede preferir el recorrido igual, y eso
        # seria una respuesta legitima: se reporta lo que hace, no lo que
        # conviene. El detalle lleva el plan para poder discutirlo.
        r.comprobar(
            "5. el planificador elige distrito_geometria_gix en ST_Contains",
            "distrito_geometria_gix" in plan,
            f"plan: {plan.splitlines()[0] if plan else ''}. Con 8 filas puede preferir "
            "el recorrido; si es asi, el indice sobra y hay que quitarlo de la 011",
        )

    # ---------------------------------------------------------------- 6
    cur.execute(
        "SELECT count(*) FROM pg_class WHERE relkind = 'i' AND relname = 'medicion_fecha_ix'"
    )
    r.comprobar(
        "6. medicion_fecha_ix NO existe: se midio y se descarto",
        cur.fetchone()[0] == 0,
        "esta creado, y la medicion dijo que el planificador no lo elige",
    )

    # ---------------------------------------------------------------- 7
    # Un indice cuyas columnas guia sean las mismas y en el mismo orden que las
    # de la clave primaria seria una copia: PostgreSQL no lo impide.
    cur.execute("""
        SELECT i.relname, t.relname
        FROM pg_index x
        JOIN pg_class i ON i.oid = x.indexrelid
        JOIN pg_class t ON t.oid = x.indrelid
        WHERE i.relname IN ('riesgo_fecha_evento_ix', 'foco_distrito_fecha_ix')
          AND EXISTS (
              SELECT 1 FROM pg_index p
              WHERE p.indrelid = x.indrelid AND p.indisprimary
                AND p.indkey::text = x.indkey::text
          )
    """)
    duplicados = cur.fetchall()
    r.comprobar(
        "7. ningun indice nuevo duplica la clave primaria de su tabla",
        not duplicados,
        f"duplican: {duplicados}",
    )

    # ---------------------------------------------------------------- 8
    cur.execute("SAVEPOINT escritura")
    try:
        cur.execute("SELECT codigo_distrito, fecha, tipo_evento FROM analitico.riesgo LIMIT 1")
        clave = cur.fetchone()
        cur.execute(
            "UPDATE analitico.riesgo SET nivel = 'alto' "
            "WHERE codigo_distrito = %s AND fecha = %s AND tipo_evento = %s",
            clave,
        )
        escribe = cur.rowcount == 1
        detalle = ""
    except Exception as error:  # noqa: BLE001
        escribe, detalle = False, str(error).splitlines()[0]
    cur.execute("ROLLBACK TO SAVEPOINT escritura")
    r.comprobar("8. las escrituras siguen funcionando con los indices puestos", escribe, detalle)

    return r


def main() -> int:
    p = argparse.ArgumentParser(description="Criterios de aceptacion de H1.12.")
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
    print("\nH1.12 cumple sus criterios de aceptacion.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
