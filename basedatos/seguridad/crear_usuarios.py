"""
Creacion de los usuarios de aplicacion. Dueno: Cesar. Historia H1.8, issue #40.

POR QUE ESTA SEPARADO DE LA MIGRACION

La migracion 003 crea los roles de grupo y reparte los permisos, y va al
repositorio: es la parte que el evaluador de BD-2 tiene que poder leer.

Los usuarios que inician sesion no pueden ir ahi, porque llevan contrasena. Un
CREATE ROLE ... PASSWORD 'algo' en un archivo versionado la deja en el historial
de git para siempre, y borrarla despues no la quita de los commits anteriores.

Este guion las lee de .env, que esta en .gitignore.

QUE HACE

  1. Lee los cuatro valores de .env.
  2. Crea cada usuario con LOGIN, o le actualiza la contrasena si ya existe.
  3. Lo mete en su rol de grupo.

Es idempotente: correrlo dos veces no falla ni cambia los permisos resultantes.

LO QUE NO HACE

No concede ningun permiso directamente a los usuarios. Todo permiso viene del rol
heredado. Si algun dia hay que revocarle el acceso a alguien, se quita el usuario
y el esquema de permisos no se toca.

USO

    python -m basedatos.seguridad.crear_usuarios
    python -m basedatos.seguridad.crear_usuarios --verificar   # informa, no crea
"""

from __future__ import annotations

import argparse
import os
import re
import sys

import psycopg
from dotenv import load_dotenv
from psycopg import sql

from basedatos.conexion import ErrorConexion, conectar

# Un usuario por rol de grupo. El rol lector no tiene usuario propio: se concede
# a quien lo necesite para consultar a mano, sin crear una cuenta que nadie usa.
USUARIOS = [
    ("DB_USER_ETL", "DB_PASS_ETL", "geoguardian_etl"),
    ("DB_USER_API", "DB_PASS_API", "geoguardian_api"),
]

PATRON_NOMBRE = re.compile(r"^[a-z][a-z0-9_]{2,62}$")
LARGO_MINIMO = 12


class ErrorUsuarios(Exception):
    """Falla que impide continuar."""


def leer_credenciales() -> list[tuple[str, str, str]]:
    """
    Lee y valida los cuatro valores de .env.

    Valida antes de tocar la base: si falta una contrasena, es mejor enterarse
    sin haber creado a medias el primer usuario.
    """
    load_dotenv()

    problemas: list[str] = []
    salida: list[tuple[str, str, str]] = []

    for clave_usuario, clave_contrasena, rol in USUARIOS:
        nombre = (os.getenv(clave_usuario) or "").strip()
        contrasena = os.getenv(clave_contrasena) or ""

        if not nombre:
            problemas.append(f"  {clave_usuario} esta vacio en .env")
        elif not PATRON_NOMBRE.match(nombre):
            problemas.append(
                f"  {clave_usuario}={nombre!r} no es un nombre valido: minusculas, "
                "digitos y guion bajo, empezando por letra"
            )

        if not contrasena:
            problemas.append(f"  {clave_contrasena} esta vacio en .env")
        elif len(contrasena) < LARGO_MINIMO:
            problemas.append(f"  {clave_contrasena} tiene menos de {LARGO_MINIMO} caracteres")

        if nombre and contrasena:
            salida.append((nombre, contrasena, rol))

    if problemas:
        raise ErrorUsuarios(
            "Faltan credenciales o son invalidas:\n"
            + "\n".join(problemas)
            + "\n\nLos nombres acordados por el equipo estan en .env.example. Las "
            "contrasenas las pone cada quien en su .env y no se comparten."
        )

    return salida


def existe(conexion: psycopg.Connection, nombre: str) -> bool:
    with conexion.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (nombre,))
        return cursor.fetchone() is not None


def rol_existe(conexion: psycopg.Connection, rol: str) -> bool:
    return existe(conexion, rol)


def pertenece(conexion: psycopg.Connection, nombre: str, rol: str) -> bool:
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
              FROM pg_auth_members m
              JOIN pg_roles usuario ON usuario.oid = m.member
              JOIN pg_roles grupo   ON grupo.oid   = m.roleid
             WHERE usuario.rolname = %s AND grupo.rolname = %s
            """,
            (nombre, rol),
        )
        return cursor.fetchone() is not None


def aplicar(solo_verificar: bool = False) -> int:
    credenciales = leer_credenciales()

    with conectar(autocommit=True) as conexion:
        faltan_roles = [rol for _, _, rol in credenciales if not rol_existe(conexion, rol)]
        if faltan_roles:
            raise ErrorUsuarios(
                "No existen los roles de grupo: " + ", ".join(faltan_roles) + "\n"
                "Aplica primero las migraciones: python -m basedatos.aplicar_migraciones"
            )

        for nombre, contrasena, rol in credenciales:
            ya_estaba = existe(conexion, nombre)
            ya_en_rol = pertenece(conexion, nombre, rol) if ya_estaba else False

            if solo_verificar:
                estado = "existe" if ya_estaba else "falta"
                en_rol = "si" if ya_en_rol else "no"
                print(f"  {nombre:<20} {estado:<7} en {rol:<20} miembro: {en_rol}")
                continue

            # La contrasena no admite parametro enlazado en CREATE ROLE: va como
            # literal, citada por psycopg. Nunca se imprime ni se registra.
            if ya_estaba:
                conexion.execute(
                    sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(
                        sql.Identifier(nombre), sql.Literal(contrasena)
                    )
                )
                accion = "actualizado"
            else:
                conexion.execute(
                    sql.SQL("CREATE ROLE {} WITH LOGIN PASSWORD {}").format(
                        sql.Identifier(nombre), sql.Literal(contrasena)
                    )
                )
                accion = "creado"

            # Ningun permiso directo: todo viene del rol heredado.
            conexion.execute(
                sql.SQL("GRANT {} TO {}").format(sql.Identifier(rol), sql.Identifier(nombre))
            )

            print(f"  {nombre:<20} {accion:<12} miembro de {rol}")

        if solo_verificar:
            print("\nModo verificacion: no se creo ni modifico nada.")
        else:
            print(f"\nListos {len(credenciales)} usuarios. Ninguno tiene permisos propios.")

    return 0


def main() -> int:
    analizador = argparse.ArgumentParser(
        description="Crea los usuarios de aplicacion a partir de .env."
    )
    analizador.add_argument(
        "--verificar",
        action="store_true",
        help="Informa el estado de los usuarios sin crear ni modificar.",
    )
    argumentos = analizador.parse_args()

    try:
        return aplicar(solo_verificar=argumentos.verificar)
    except (ErrorUsuarios, ErrorConexion) as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        return 1
    except psycopg.Error as error:
        print(f"\nERROR de PostgreSQL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
