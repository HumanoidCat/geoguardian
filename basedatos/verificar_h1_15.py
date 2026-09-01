"""
Verificador de los criterios de aceptacion de H1.15. Dueno: Cesar. Issue #199.

QUE COMPRUEBA

Que `analitico.riesgo` y `analitico.contribucion_riesgo`, creadas por la
migracion 006, hacen cumplir lo que su DDL declara.

NO LEE EL ARCHIVO .sql. Todo se le pregunta a la base. El archivo dice lo que se
escribio; la base dice lo que quedo aplicado, y entre las dos cosas hay una
migracion que pudo no correr. Comprobar el texto del DDL seria comprobar que
alguien lo tecleo bien.

Los siete criterios estan en
`docs/evidencias/bases-de-datos/H1.15-criterios-aceptacion.md`, escritos antes
que este archivo.

COMO NO ENSUCIA LA BASE

Todo lo que escribe ocurre dentro de UNA transaccion que se revierte al final
levantando `Revertir`. Las inserciones que deben fallar van cada una en su
propio `conexion.transaction()` anidado, que en psycopg3 es un SAVEPOINT: cada
fallo revierte su caso sin abortar la transaccion externa.

Ese anidamiento es el mismo mecanismo que en H1.1 fue una trampa -se creia abrir
una transaccion por distrito y se abria un punto de retorno dentro de una sola-.
Aqui se usa a proposito, y CA-7 comprueba que la base volvio a su estado.

La conexion se abre con `autocommit=True` para que el `transaction()` externo sea
una transaccion de verdad y no un punto de retorno dentro de otra.

USO

    python -m basedatos.verificar_h1_15
    python -m basedatos.verificar_h1_15 --base geoguardian_prueba

La segunda forma es la que importa para el CI: esta historia, a diferencia de
H1.7, NO necesita datos cargados. Le basta con que las migraciones esten
aplicadas, asi que corre contra una base vacia.

CODIGOS DE SALIDA

    0  los siete criterios cumplen
    1  algun criterio no cumple
    2  no se pudo llegar a la base, o falta la migracion 006
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[1]
if str(RAIZ_REPOSITORIO) not in sys.path:
    sys.path.insert(0, str(RAIZ_REPOSITORIO))

import psycopg  # noqa: E402

from basedatos.conexion import ErrorConexion, conectar  # noqa: E402

# Geografia sintetica. No se usa ninguno de los ocho distritos reales para que
# el verificador corra igual contra una base vacia, y para no depender de codigos
# que ya cambiaron una vez (I-04).
#
# Los codigos respetan las tres reglas que el DDL de geo hace cumplir:
#   provincia entre 1 y 7 · canton entre 101 y 799 y canton // 100 = provincia
#   distrito de cinco digitos y substr(codigo, 1, 3) = canton
PROVINCIA = 7
CANTON = 799
DISTRITO = "79999"

FECHA = date(2026, 1, 1)

POLIGONO = "MULTIPOLYGON(((0 0, 0 1, 1 1, 1 0, 0 0)))"

COLUMNAS_ESPERADAS = {
    "codigo_distrito": ("text", "NO"),
    "fecha": ("date", "NO"),
    "tipo_evento": ("text", "NO"),
    "nivel": ("text", "YES"),
    "probabilidad": ("real", "YES"),
    "algoritmo": ("text", "YES"),
    "version_modelo": ("text", "YES"),
    "estimado_en": ("timestamp with time zone", "NO"),
}

PK_ESPERADA = "PRIMARY KEY (codigo_distrito, fecha, tipo_evento)"

SQL_INSERTAR = """
    INSERT INTO analitico.riesgo
        (codigo_distrito, fecha, tipo_evento, nivel, probabilidad, algoritmo)
    VALUES (%(distrito)s, %(fecha)s, %(evento)s, %(nivel)s, %(probabilidad)s, %(algoritmo)s)
"""


class Revertir(Exception):
    """Se levanta al final para revertir la transaccion externa."""


class FaltaLaMigracion(Exception):
    """analitico.riesgo no existe."""


def titulo(texto: str) -> None:
    print(f"\n{texto}")
    print("-" * len(texto))


def insertar(conexion: psycopg.Connection, **campos) -> None:
    """Inserta una fila de riesgo. Los campos ausentes van nulos."""
    parametros = {
        "distrito": DISTRITO,
        "fecha": FECHA,
        "evento": "sequia",
        "nivel": None,
        "probabilidad": None,
        "algoritmo": None,
    }
    parametros.update(campos)
    conexion.execute(SQL_INSERTAR, parametros)


def debe_rechazar(
    conexion: psycopg.Connection,
    descripcion: str,
    restriccion_esperada: str,
    **campos,
) -> bool:
    """
    Intenta una insercion que tiene que fallar, dentro de su propio punto de
    retorno, y comprueba que fallo POR LA RESTRICCION ESPERADA.

    Que la insercion falle no basta: podria estar fallando por otra cosa y el
    criterio quedaria verde sin haber probado la regla que dice probar.
    """
    try:
        with conexion.transaction():
            insertar(conexion, **campos)
    except psycopg.errors.IntegrityError as error:
        nombre = error.diag.constraint_name or "(sin nombre)"
        if nombre == restriccion_esperada:
            print(f"  OK      {descripcion}: rechazada por {nombre}")
            return True
        print(
            f"  FALLA   {descripcion}: la rechazo {nombre}, " f"se esperaba {restriccion_esperada}"
        )
        return False

    print(f"  FALLA   {descripcion}: la base la ACEPTO, y no debia")
    return False


def preparar_geografia(conexion: psycopg.Connection) -> None:
    """Crea la provincia, el canton y el distrito sinteticos."""
    conexion.execute(
        "INSERT INTO geo.provincia (codigo, nombre) VALUES (%s, %s) "
        "ON CONFLICT (codigo) DO NOTHING",
        (PROVINCIA, "Provincia de prueba H1.15"),
    )
    conexion.execute(
        "INSERT INTO geo.canton (codigo, codigo_provincia, nombre) "
        "VALUES (%s, %s, %s) ON CONFLICT (codigo) DO NOTHING",
        (CANTON, PROVINCIA, "Canton de prueba H1.15"),
    )
    conexion.execute(
        "INSERT INTO geo.distrito "
        "  (codigo, codigo_canton, nombre, area_km2, geometria) "
        "VALUES (%s, %s, %s, %s, ST_GeomFromText(%s, 4326)) "
        "ON CONFLICT (codigo) DO NOTHING",
        (DISTRITO, CANTON, "Distrito de prueba H1.15", 1.0, POLIGONO),
    )


# --------------------------------------------------------------------------- #
# Criterios
# --------------------------------------------------------------------------- #


def ca1_estructura(conexion: psycopg.Connection) -> bool:
    titulo("CA-1 · La tabla existe con sus ocho columnas y su indice")

    filas = conexion.execute(
        """
        SELECT column_name, data_type, is_nullable
          FROM information_schema.columns
         WHERE table_schema = 'analitico' AND table_name = 'riesgo'
        """
    ).fetchall()

    if not filas:
        raise FaltaLaMigracion(
            "analitico.riesgo no existe. Corre primero:\n"
            "  python -m basedatos.aplicar_migraciones"
        )

    encontradas = {nombre: (tipo, nulable) for nombre, tipo, nulable in filas}
    ok = True

    for nombre, esperado in COLUMNAS_ESPERADAS.items():
        real = encontradas.get(nombre)
        if real is None:
            print(f"  FALLA   falta la columna {nombre}")
            ok = False
        elif real != esperado:
            print(f"  FALLA   {nombre}: es {real}, se esperaba {esperado}")
            ok = False
        else:
            nulo = "admite nulos" if esperado[1] == "YES" else "obligatoria"
            print(f"  OK      {nombre:16} {esperado[0]:26} {nulo}")

    sobrantes = set(encontradas) - set(COLUMNAS_ESPERADAS)
    if sobrantes:
        print(f"  FALLA   columnas no declaradas en los criterios: {sorted(sobrantes)}")
        ok = False

    indices = {
        nombre
        for (nombre,) in conexion.execute(
            "SELECT indexname FROM pg_indexes "
            " WHERE schemaname = 'analitico' AND tablename = 'riesgo'"
        ).fetchall()
    }

    # El indice (codigo_distrito, fecha) que pedia el ticket NO se creo: ya
    # existe como prefijo de la clave primaria. El que hace falta es este, que
    # sirve a obtener_riesgos_por_fecha, la consulta de las coropletas.
    if "riesgo_fecha_evento_idx" in indices:
        print("  OK      indice riesgo_fecha_evento_idx presente")
    else:
        print(f"  FALLA   falta riesgo_fecha_evento_idx. Hay: {sorted(indices)}")
        ok = False

    return ok


def ca2_claves(conexion: psycopg.Connection) -> bool:
    titulo("CA-2 · Clave primaria y clave foranea a geo.distrito")

    definiciones = dict(
        conexion.execute(
            """
            SELECT conname, pg_get_constraintdef(oid)
              FROM pg_constraint
             WHERE conrelid = 'analitico.riesgo'::regclass
            """
        ).fetchall()
    )

    ok = True

    pk = definiciones.get("riesgo_pk", "")
    if pk == PK_ESPERADA:
        print(f"  OK      {pk}")
    else:
        print(f"  FALLA   la clave primaria es '{pk}', se esperaba '{PK_ESPERADA}'")
        ok = False

    fk = definiciones.get("riesgo_distrito_fk", "")
    if "REFERENCES geo.distrito(codigo)" in fk.replace(" (", "("):
        print(f"  OK      {fk}")
    else:
        print(f"  FALLA   la clave foranea a geo.distrito es '{fk}'")
        ok = False

    # La definicion declara la referencia; esto comprueba que la hace cumplir.
    ok &= debe_rechazar(
        conexion,
        "distrito inexistente",
        "riesgo_distrito_fk",
        distrito="00000",
    )

    return ok


def ca3_ausencia_es_nula(conexion: psycopg.Connection) -> bool:
    titulo("CA-3 · La ausencia de estimacion se distingue del riesgo bajo (D-07)")

    insertar(conexion, evento="sequia", nivel=None)
    insertar(conexion, evento="lluvia_intensa", nivel="bajo", probabilidad=0.12)

    sin_estimacion, en_bajo = conexion.execute(
        """
        SELECT count(*) FILTER (WHERE nivel IS NULL),
               count(*) FILTER (WHERE nivel = 'bajo')
          FROM analitico.riesgo
         WHERE codigo_distrito = %s
        """,
        (DISTRITO,),
    ).fetchone()

    ok = True

    if sin_estimacion == 1:
        print("  OK      una fila sin estimacion se guardo con nivel NULO")
    else:
        print(f"  FALLA   filas con nivel nulo: {sin_estimacion}, se esperaba 1")
        ok = False

    if en_bajo == 1:
        print("  OK      una fila en 'bajo' se guardo, y es OTRA fila")
    else:
        print(f"  FALLA   filas en 'bajo': {en_bajo}, se esperaba 1")
        ok = False

    # El punto entero de D-07: las dos existen a la vez y una consulta las separa.
    if sin_estimacion == 1 and en_bajo == 1:
        print("  OK      'sin estimacion' y 'riesgo bajo' son estados distintos")
    else:
        ok = False

    return ok


def ca4_restricciones(conexion: psycopg.Connection) -> bool:
    titulo("CA-4 · Los seis CHECK rechazan lo que declaran rechazar")

    casos = [
        ("evento fuera del dominio", "riesgo_evento_ck", {"evento": "terremoto"}),
        ("nivel fuera del dominio", "riesgo_nivel_ck", {"nivel": "altisimo"}),
        (
            "probabilidad fuera de [0, 1]",
            "riesgo_probabilidad_ck",
            {"nivel": "alto", "probabilidad": 1.5},
        ),
        (
            "incendio en nivel medio (SC-05)",
            "riesgo_incendio_binario_ck",
            {"evento": "incendio", "nivel": "medio"},
        ),
        (
            "probabilidad sin nivel (D-21)",
            "riesgo_probabilidad_exige_nivel_ck",
            {"nivel": None, "probabilidad": 0.8},
        ),
        # No la exige el ticket y se comprueba igual: esta en el DDL.
        (
            "algoritmo fuera del dominio",
            "riesgo_algoritmo_ck",
            {"nivel": "alto", "algoritmo": "red_neuronal"},
        ),
    ]

    # CADA CASO LLEVA SU PROPIA FECHA, Y ESA ES LA PARTE QUE IMPORTA
    #
    # Con la fecha por omision, cuatro de los seis chocarian ademas contra la
    # clave primaria, porque CA-3 ya dejo filas en (79999, 2026-01-01, sequia).
    # Pasarian igual -PostgreSQL evalua los CHECK de tabla antes de insertar en
    # el indice unico- pero estarian pasando por el orden interno de evaluacion
    # del motor y no porque la restriccion sea la que rechaza.
    #
    # Un criterio que depende de eso da verde sin comprobar lo que dice
    # comprobar, y deja de darlo el dia que alguien reordene el DDL.
    ok = True
    for numero, (descripcion, restriccion, campos) in enumerate(casos, start=1):
        campos.setdefault("fecha", date(2026, 2, numero))
        ok &= debe_rechazar(conexion, descripcion, restriccion, **campos)

    return ok


def ca5_comentario(conexion: psycopg.Connection) -> bool:
    titulo("CA-5 · El COMMENT de probabilidad declara D-21 en la base")

    (comentario,) = conexion.execute(
        """
        SELECT col_description(a.attrelid, a.attnum)
          FROM pg_attribute a
         WHERE a.attrelid = 'analitico.riesgo'::regclass
           AND a.attname = 'probabilidad'
        """
    ).fetchone()

    if not comentario:
        print("  FALLA   la columna probabilidad no tiene COMMENT en la base")
        return False

    print(f"  Comentario: {comentario}")

    ok = True
    for exigido in ("P(nivel = alto)", "D-21"):
        if exigido in comentario:
            print(f"  OK      el comentario contiene '{exigido}'")
        else:
            print(f"  FALLA   el comentario NO contiene '{exigido}'")
            ok = False

    return ok


def ca6_cascada(conexion: psycopg.Connection) -> bool:
    titulo("CA-6 · Borrar una estimacion borra sus contribuciones")

    insertar(conexion, evento="incendio", nivel="alto", probabilidad=0.9)
    conexion.execute(
        """
        INSERT INTO analitico.contribucion_riesgo
            (codigo_distrito, fecha, tipo_evento, variable, aporte)
        VALUES (%s, %s, 'incendio', 'precipitacion_acumulada_30d', -0.42),
               (%s, %s, 'incendio', 'dias_sin_lluvia', 0.31)
        """,
        (DISTRITO, FECHA, DISTRITO, FECHA),
    )

    (antes,) = conexion.execute(
        "SELECT count(*) FROM analitico.contribucion_riesgo WHERE codigo_distrito = %s",
        (DISTRITO,),
    ).fetchone()

    conexion.execute(
        "DELETE FROM analitico.riesgo "
        " WHERE codigo_distrito = %s AND fecha = %s AND tipo_evento = 'incendio'",
        (DISTRITO, FECHA),
    )

    (despues,) = conexion.execute(
        "SELECT count(*) FROM analitico.contribucion_riesgo WHERE codigo_distrito = %s",
        (DISTRITO,),
    ).fetchone()

    if antes == 2 and despues == 0:
        print(f"  OK      {antes} contribuciones antes del borrado, {despues} despues")
        return True

    print(f"  FALLA   antes: {antes} (se esperaban 2), despues: {despues} (0)")
    return False


def contar_riesgos(conexion: psycopg.Connection) -> int:
    (total,) = conexion.execute("SELECT count(*) FROM analitico.riesgo").fetchone()
    return total


# --------------------------------------------------------------------------- #


def verificar(conexion: psycopg.Connection) -> bool:
    antes = contar_riesgos(conexion)
    print(f"Filas en analitico.riesgo antes de empezar: {antes}")

    resultados: dict[str, bool] = {}

    resultados["CA-1"] = ca1_estructura(conexion)

    try:
        with conexion.transaction():
            preparar_geografia(conexion)
            resultados["CA-2"] = ca2_claves(conexion)
            resultados["CA-3"] = ca3_ausencia_es_nula(conexion)
            resultados["CA-4"] = ca4_restricciones(conexion)
            resultados["CA-6"] = ca6_cascada(conexion)
            raise Revertir
    except Revertir:
        pass

    resultados["CA-5"] = ca5_comentario(conexion)

    titulo("CA-7 · La base quedo como estaba")
    despues = contar_riesgos(conexion)
    if despues == antes:
        print(f"  OK      {antes} filas antes, {despues} despues. Nada quedo escrito")
        resultados["CA-7"] = True
    else:
        print(
            f"  FALLA   {antes} filas antes, {despues} despues. "
            "LA BASE QUEDO TOCADA, revisar antes de seguir"
        )
        resultados["CA-7"] = False

    titulo("Resumen")
    for criterio in sorted(resultados):
        estado = "CUMPLE" if resultados[criterio] else "NO CUMPLE"
        print(f"  {criterio}  {estado}")

    return all(resultados.values())


def main() -> int:
    analizador = argparse.ArgumentParser(
        description="Comprueba los criterios de aceptacion de H1.15 (issue #199)."
    )
    analizador.add_argument(
        "--base",
        help=(
            "Nombre de la base contra la que correr. Por omision, la de .env. "
            "Con una base vacia recien migrada tambien tiene que dar verde: "
            "esta historia no necesita datos cargados."
        ),
    )
    argumentos = analizador.parse_args()

    if argumentos.base:
        os.environ["POSTGRES_DB"] = argumentos.base

    print("Verificacion de H1.15 · analitico.riesgo y sus restricciones")
    print(f"Base: {os.getenv('POSTGRES_DB') or 'geoguardian'}")

    try:
        # autocommit para que el transaction() externo sea una transaccion de
        # verdad y no un punto de retorno dentro de otra. Trampa de psycopg3.
        with conectar(autocommit=True) as conexion:
            todo_bien = verificar(conexion)
    except FaltaLaMigracion as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        return 2
    except ErrorConexion as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        return 2

    print()
    if todo_bien:
        print("Los siete criterios de H1.15 se cumplen.")
        return 0

    print("Hay criterios sin cumplir.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
