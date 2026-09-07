"""
Verificador de minimo privilegio. Dueno: Cesar. Historia H1.8, issue #40.

Cubre CA-1 a CA-8. El nucleo es CA-5: una lista de operaciones que tienen que
FALLAR. Una lista de permisos concedidos no demuestra minimo privilegio; lo
demuestra que la API reciba 'permission denied for schema crudo' cuando lo
intenta. Este guion falla si alguna operacion prohibida tiene exito.

CA-9 (reejecutable) y CA-10 (maquina limpia) se verifican por fuera, corriendo
las herramientas dos veces y desde un volumen vacio.

USO

    python -m basedatos.seguridad.verificar_h18
"""

from __future__ import annotations

import ast
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import psycopg
from dotenv import load_dotenv

from basedatos.conexion import ErrorConexion, cadena_conexion, conectar

ROLES = ["geoguardian_etl", "geoguardian_api", "geoguardian_lector"]
ESQUEMAS = ["geo", "crudo", "analitico", "control"]
RAIZ_BASEDATOS = Path(__file__).resolve().parents[1]


@dataclass
class Resultado:
    criterio: str
    titulo: str
    cumple: bool
    detalle: list[str] = field(default_factory=list)


def _conexion_de(usuario: str, contrasena: str) -> str:
    """Cadena de conexion suplantando a un usuario de aplicacion."""
    base = cadena_conexion()
    base = re.sub(r"user=\S+", f"user={usuario}", base)
    base = re.sub(r"password=\S+", f"password={contrasena}", base)
    return base


def _credenciales() -> dict[str, tuple[str, str]]:
    load_dotenv()
    return {
        "etl": (os.getenv("DB_USER_ETL", ""), os.getenv("DB_PASS_ETL", "")),
        "api": (os.getenv("DB_USER_API", ""), os.getenv("DB_PASS_API", "")),
    }


# --------------------------------------------------------------------------- #
# CA-1 y CA-2 · existencia, atributos y pertenencia                            #
# --------------------------------------------------------------------------- #


def ca1_roles(cursor: psycopg.Cursor, cred: dict) -> Resultado:
    nombres = ROLES + [cred["etl"][0], cred["api"][0]]
    cursor.execute(
        """
        SELECT rolname, rolcanlogin, rolinherit, rolsuper, rolcreatedb, rolcreaterole
          FROM pg_roles WHERE rolname = ANY(%s) ORDER BY rolname
        """,
        (nombres,),
    )
    filas = cursor.fetchall()
    vistos = {f[0]: f for f in filas}

    detalle = []
    ok = True

    for r in ROLES:
        f = vistos.get(r)
        if f is None:
            detalle.append(f"  {r:<22} FALTA")
            ok = False
            continue
        if f[1]:
            detalle.append(f"  {r:<22} puede iniciar sesion y no deberia")
            ok = False
        elif f[3] or f[4] or f[5]:
            detalle.append(f"  {r:<22} tiene atributos de administracion")
            ok = False
        else:
            detalle.append(f"  {r:<22} grupo, sin sesion, sin privilegios de administracion")

    for u, _ in cred.values():
        f = vistos.get(u)
        if f is None:
            detalle.append(f"  {u:<22} FALTA")
            ok = False
        elif not f[1] or not f[2]:
            detalle.append(f"  {u:<22} deberia poder iniciar sesion y heredar")
            ok = False
        elif f[3] or f[4] or f[5]:
            detalle.append(f"  {u:<22} tiene atributos de administracion")
            ok = False
        else:
            detalle.append(f"  {u:<22} usuario, inicia sesion, hereda, sin administracion")

    return Resultado("CA-1", "Roles y usuarios con los atributos correctos", ok, detalle)


def ca2_pertenencia(cursor: psycopg.Cursor, cred: dict) -> Resultado:
    cursor.execute(
        """
        SELECT usuario.rolname, grupo.rolname
          FROM pg_auth_members m
          JOIN pg_roles usuario ON usuario.oid = m.member
          JOIN pg_roles grupo   ON grupo.oid   = m.roleid
         WHERE grupo.rolname = ANY(%s)
         ORDER BY 1
        """,
        (ROLES,),
    )
    reales = {(a, b) for a, b in cursor.fetchall()}
    esperadas = {
        (cred["etl"][0], "geoguardian_etl"),
        (cred["api"][0], "geoguardian_api"),
    }
    sobran = reales - esperadas
    faltan = esperadas - reales

    detalle = [f"  {a} pertenece a {b}" for a, b in sorted(reales)]
    if faltan:
        detalle += [f"  FALTA: {a} en {b}" for a, b in sorted(faltan)]
    if sobran:
        detalle += [f"  SOBRA: {a} en {b}" for a, b in sorted(sobran)]

    return Resultado("CA-2", "Pertenencia exacta a los roles", not faltan and not sobran, detalle)


# --------------------------------------------------------------------------- #
# CA-3 y CA-4 · lo que si debe funcionar                                       #
# --------------------------------------------------------------------------- #

PERMITIDAS = [
    ("etl", "leer geo.distrito", "SELECT count(*) FROM geo.distrito"),
    ("etl", "leer control.migracion", "SELECT count(*) FROM control.migracion"),
    # El cuarto elemento dice si la sentencia ESCRIBE. Antes esto se expresaba
    # poniendo `None` en la consulta, y el probador tenia dentro, escrito a mano,
    # el unico INSERT que sabia hacer. **Un centinela que solo puede significar
    # una cosa deja de servir en cuanto hay dos**, que es lo que pasa con la 014.
    (
        "etl",
        "escribir en control.migracion",
        "INSERT INTO control.migracion (numero, archivo, suma_sha256) "
        "VALUES (999, 'prueba_h18.sql', repeat('a', 64))",
        True,
    ),
    ("api", "leer geo.distrito", "SELECT count(*) FROM geo.distrito"),
    # LO QUE LA MIGRACION 014 CONCEDIO, Y POR QUE SE PRUEBA (D-44).
    #
    # H12.1 le dio a `geoguardian_api` INSERT y UPDATE sobre
    # `control.bitacora_etl`, porque el titulo de la historia dice «pipeline **y
    # aplicacion**» y la aplicacion registra con `proceso = 'api'`.
    #
    # Se prueban los DOS verbos y no uno: la corrida se abre con INSERT y se
    # cierra con UPDATE, asi que conceder solo el primero dejaria corridas
    # eternamente `en_curso` sin que nada fallara al abrirlas.
    (
        "api",
        "abrir una corrida en control.bitacora_etl",
        "INSERT INTO control.bitacora_etl (proceso, estado) VALUES ('api', 'en_curso')",
        True,
    ),
    (
        "api",
        "cerrar una corrida en control.bitacora_etl",
        "UPDATE control.bitacora_etl SET estado = 'exitosa', terminada_en = now() "
        "WHERE estado = 'en_curso'",
        True,
    ),
    # LLAMAR A UNA FUNCION, NO SOLO LEER UNA TABLA.
    #
    # Hasta la 015, de lo PERMITIDO esta lista solo probaba `SELECT` sobre
    # tablas. Ningun caso llamaba a una funcion, y PostGIS vive en el esquema
    # `public`, que la 003 cierra. Resultado: los roles leian las tablas
    # perfectamente y **ninguna funcion espacial se resolvia**.
    #
    #     function st_asgeojson(public.geometry) does not exist
    #
    # `/api/distritos` hace ese `ST_AsGeoJSON`, asi que devolvia 500 con la
    # tabla legible, la conexion sana y `/salud` diciendo `real`. Se descubrio
    # publicando, el 2026-09-05, no aca. Es la incidencia I-40.
    #
    # Un permiso concedido y no probado no esta concedido: sin estos dos casos,
    # la migracion 015 no tendria quien la sostenga.
    ("api", "llamar a postgis_version()", "SELECT postgis_version()"),
    (
        "api",
        "ST_AsGeoJSON sobre geo.distrito",
        "SELECT ST_AsGeoJSON(geometria) FROM geo.distrito LIMIT 1",
    ),
    ("etl", "llamar a postgis_version()", "SELECT postgis_version()"),
    # LO QUE /salud NECESITA LEER, PROBADO ANTES DE DESPLEGARLO.
    #
    # Desde I-41, `/salud` responde `ultima_ingesta` con un `max(terminada_en)`
    # sobre `control.bitacora_etl`. El `GRANT SELECT` esta en la migracion 013 y
    # esta dentro de un `DO $$` con guarda por rol: si la guarda no se cumplio en
    # alguna base, el permiso no esta y **nadie se entera hasta que /salud
    # devuelve 500 en produccion**, con el visor cayendo en silencio al respaldo
    # de datos simulados.
    #
    # Es I-40 otra vez, un paso antes: un permiso que el codigo da por dado. Aqui
    # se prueba en las dos bases, con el rol de la aplicacion, antes de desplegar.
    (
        "api",
        "leer control.bitacora_etl, que es lo que /salud consulta",
        "SELECT max(terminada_en) FROM control.bitacora_etl WHERE estado = 'exitosa'",
    ),
]


def _probar_permitidas(cred: dict) -> Resultado:
    detalle = []
    ok = True
    for entrada in PERMITIDAS:
        quien, que, consulta = entrada[0], entrada[1], entrada[2]
        escribe = len(entrada) > 3 and entrada[3]
        usuario, contrasena = cred[quien]
        try:
            with (
                psycopg.connect(_conexion_de(usuario, contrasena)) as cn,
                cn.cursor() as cur,
            ):
                cur.execute(consulta)
                if escribe:
                    # Escritura real, revertida al salir: no deja rastro.
                    #
                    # Tiene que ser real y no un `EXPLAIN`: PostgreSQL comprueba
                    # el permiso al ejecutar, asi que una escritura simulada
                    # daria verde con el GRANT ausente.
                    cn.rollback()
                else:
                    cur.fetchone()
            detalle.append(f"  [ok ] {quien:<4} {que}")
        except psycopg.Error as error:
            ok = False
            detalle.append(f"  [MAL] {quien:<4} {que}: {str(error).splitlines()[0]}")
    return Resultado("CA-3/4", "Lo permitido funciona", ok, detalle)


# --------------------------------------------------------------------------- #
# CA-5 · lo que tiene que fallar. El nucleo de BD-2.                           #
# --------------------------------------------------------------------------- #

PROHIBIDAS = [
    ("api", "SELECT en crudo", "SELECT 1 FROM crudo.medicion_diaria LIMIT 1", "crudo"),
    (
        "api",
        "INSERT en geo.distrito",
        "INSERT INTO geo.distrito (codigo) VALUES ('99999')",
        "denied",
    ),
    ("api", "UPDATE en control.migracion", "UPDATE control.migracion SET archivo = 'x'", "denied"),
    (
        "etl",
        "INSERT en geo.distrito",
        "INSERT INTO geo.distrito (codigo) VALUES ('99999')",
        "denied",
    ),
    ("etl", "DROP TABLE en control", "DROP TABLE control.migracion", "owner"),
    ("etl", "DELETE en control.migracion", "DELETE FROM control.migracion", "denied"),
    # LO QUE LA 014 **NO** CONCEDIO, Y ES LA MITAD QUE SOSTIENE A LA OTRA (D-44).
    #
    # Sin estos casos, la seccion de arriba prueba que la API gano un permiso, y
    # nada mas. **No distingue «se abrio una tabla» de «se abrio la base».**
    #
    # No es una preocupacion teorica: el 2026-09-05 la API recibio DOS
    # ampliaciones el mismo dia, cada una correcta por separado -el USAGE sobre
    # `public` de la 015, por I-40, y el INSERT/UPDATE sobre la bitacora de la
    # 014-. Ninguna de las dos revisiones podia responder cuanto se habia abierto
    # en total, porque esa pregunta no se le hace a un permiso: se le hace al
    # conjunto.
    (
        "api",
        "DELETE en control.bitacora_etl",
        "DELETE FROM control.bitacora_etl",
        "denied",
    ),
    (
        "api",
        "INSERT en analitico.riesgo",
        "INSERT INTO analitico.riesgo (codigo_distrito, fecha, tipo_evento) "
        "VALUES ('50801', DATE '2024-01-01', 'sequia')",
        "denied",
    ),
    # El mismo control, al otro rol. La 013 le dio al ETL SELECT, INSERT y UPDATE
    # sobre la bitacora, y **nunca DELETE**: la propiedad ya existe y hasta hoy
    # nadie la comprobaba. Un diagnostico que puede borrar corridas puede borrar
    # la evidencia de lo que diagnostica.
    (
        "etl",
        "DELETE en control.bitacora_etl",
        "DELETE FROM control.bitacora_etl",
        "denied",
    ),
]


def _probar_prohibidas(cred: dict) -> Resultado:
    detalle = []
    ok = True
    for quien, que, consulta, esperado in PROHIBIDAS:
        usuario, contrasena = cred[quien]
        try:
            with psycopg.connect(_conexion_de(usuario, contrasena)) as cn:
                with cn.cursor() as cur:
                    cur.execute(consulta)
                cn.rollback()
            # Llegar aqui es el fallo que esta historia existe para evitar.
            ok = False
            detalle.append(f"  [MAL] {quien:<4} {que:<28} NO FUE RECHAZADA")
        except psycopg.Error as error:
            msg = str(error).splitlines()[0]
            if esperado in msg.lower() or "denied" in msg.lower() or "owner" in msg.lower():
                detalle.append(f"  [ok ] {quien:<4} {que:<28} {msg[:52]}")
            else:
                ok = False
                detalle.append(f"  [MAL] {quien:<4} {que:<28} error inesperado: {msg[:44]}")
    return Resultado("CA-5", "Toda operacion prohibida es rechazada", ok, detalle)


# --------------------------------------------------------------------------- #
# CA-6, CA-7 y CA-8                                                            #
# --------------------------------------------------------------------------- #


def ca6_public(cursor: psycopg.Cursor) -> Resultado:
    cursor.execute("SELECT has_schema_privilege('public', 'public', 'CREATE')")
    crea = cursor.fetchone()[0]
    cursor.execute("SELECT has_database_privilege('public', current_database(), 'CONNECT')")
    conecta = cursor.fetchone()[0]
    detalle = [
        f"  PUBLIC puede crear en el esquema public: {crea} (esperado False)",
        f"  PUBLIC puede conectarse a la base:       {conecta} (esperado False)",
    ]
    return Resultado(
        "CA-6", "Permisos implicitos de PUBLIC retirados", not crea and not conecta, detalle
    )


def ca7_por_omision(conexion: psycopg.Connection, cred: dict) -> Resultado:
    """Una tabla nueva nace con los permisos correctos."""
    detalle = []
    try:
        conexion.execute("CREATE TABLE crudo.prueba_h18 (id integer)")
        with conexion.cursor() as cur:
            cur.execute(
                "SELECT has_table_privilege(%s, 'crudo.prueba_h18', 'SELECT')",
                (cred["etl"][0],),
            )
            etl_lee = cur.fetchone()[0]
            cur.execute(
                "SELECT has_table_privilege(%s, 'crudo.prueba_h18', 'SELECT')",
                (cred["api"][0],),
            )
            api_lee = cur.fetchone()[0]
        detalle.append(f"  el ETL puede leerla:  {etl_lee} (esperado True)")
        detalle.append(f"  la API puede leerla:  {api_lee} (esperado False)")
        cumple = etl_lee and not api_lee
    finally:
        conexion.execute("DROP TABLE IF EXISTS crudo.prueba_h18")
        detalle.append("  tabla de prueba eliminada")
    return Resultado("CA-7", "Una tabla nueva nace con los permisos correctos", cumple, detalle)


def _lineas_de_prosa(texto: str, sufijo: str) -> set[int]:
    """
    Numeros de linea que son comentario o docstring, no codigo ejecutable.

    Hace falta porque tanto la migracion 003 como este paquete explican por
    escrito por que no debe haber un CREATE ROLE con la contrasena en el SQL. Esa
    frase es documentacion, no una fuga, y contarla como hallazgo convertiria el
    criterio en ruido que se termina ignorando.
    """
    prosa = {
        n for n, linea in enumerate(texto.splitlines(), 1) if linea.strip().startswith(("--", "#"))
    }

    if sufijo == ".py":
        try:
            arbol = ast.parse(texto)
        except SyntaxError:
            return prosa
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Module | ast.ClassDef | ast.FunctionDef):
                continue
            cuerpo = getattr(nodo, "body", [])
            if not cuerpo or not isinstance(cuerpo[0], ast.Expr):
                continue
            valor = cuerpo[0].value
            if isinstance(valor, ast.Constant) and isinstance(valor.value, str):
                prosa.update(range(valor.lineno, (valor.end_lineno or valor.lineno) + 1))

    return prosa


def ca8_sin_contrasenas() -> Resultado:
    """Ninguna contrasena literal en los archivos versionados de basedatos/."""
    patron = re.compile(r"password\s+'[^']", re.IGNORECASE)
    hallazgos = []
    revisados = 0

    for ruta in sorted(RAIZ_BASEDATOS.rglob("*")):
        if ruta.suffix not in (".sql", ".py") or "__pycache__" in ruta.parts:
            continue
        revisados += 1
        texto = ruta.read_text(encoding="utf-8")
        prosa = _lineas_de_prosa(texto, ruta.suffix)
        for n, linea in enumerate(texto.splitlines(), 1):
            if n not in prosa and patron.search(linea):
                hallazgos.append(f"  {ruta.relative_to(RAIZ_BASEDATOS)}:{n}  {linea.strip()[:60]}")

    detalle = hallazgos or [
        f"  cero contrasenas literales en {revisados} archivos versionados de basedatos/"
    ]
    return Resultado("CA-8", "Ninguna contrasena en el repositorio", not hallazgos, detalle)


# --------------------------------------------------------------------------- #


def _faltantes(cursor: psycopg.Cursor, cred: dict) -> list[str]:
    """Roles de grupo y usuarios que se esperaban y no estan en la base."""
    esperados = ROLES + [cred["etl"][0], cred["api"][0]]
    cursor.execute("SELECT rolname FROM pg_roles WHERE rolname = ANY(%s)", (esperados,))
    presentes = {f[0] for f in cursor.fetchall()}
    return [n for n in esperados if n not in presentes]


def main() -> int:
    cred = _credenciales()
    if not all(u and p for u, p in cred.values()):
        print(
            "ERROR: faltan DB_USER_ETL, DB_PASS_ETL, DB_USER_API o DB_PASS_API en .env",
            file=sys.stderr,
        )
        return 1

    print("Verificacion de minimo privilegio de H1.8 (issue #40)")
    print("=" * 74)

    resultados: list[Resultado] = []
    try:
        with conectar(autocommit=True) as conexion, conexion.cursor() as cursor:
            # Comprobar antes que nada que existe lo que se va a verificar. Sin
            # esto, la ausencia de un rol se manifiesta como un rastro de error a
            # mitad de camino, que no le dice a nadie que hacer.
            faltan = _faltantes(cursor, cred)
            if faltan:
                print(
                    "\nERROR: no existen todavia estos roles o usuarios:\n"
                    + "\n".join(f"  {n}" for n in faltan)
                    + "\n\nSegun cual falte:\n"
                    "  roles geoguardian_*   python -m basedatos.aplicar_migraciones\n"
                    "  usuarios de .env      python -m basedatos.seguridad.crear_usuarios",
                    file=sys.stderr,
                )
                return 1

            resultados.append(ca1_roles(cursor, cred))
            resultados.append(ca2_pertenencia(cursor, cred))
            resultados.append(_probar_permitidas(cred))
            resultados.append(_probar_prohibidas(cred))
            resultados.append(ca6_public(cursor))
            resultados.append(ca7_por_omision(conexion, cred))
    except ErrorConexion as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    resultados.append(ca8_sin_contrasenas())

    for r in resultados:
        print(f"\n{r.criterio} · {r.titulo} ... {'CUMPLE' if r.cumple else 'NO CUMPLE'}")
        for linea in r.detalle:
            print(linea)

    fallidos = [r for r in resultados if not r.cumple]
    print("\n" + "=" * 74)
    if fallidos:
        print("NO CUMPLEN: " + ", ".join(r.criterio for r in fallidos))
        return 1
    print("Los criterios verificados aqui se cumplen.")
    print("Faltan CA-9 y CA-10, que se verifican corriendo dos veces y en maquina limpia.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
