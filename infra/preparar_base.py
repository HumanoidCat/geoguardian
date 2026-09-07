"""
Prepara una base de datos recien creada para recibir las migraciones. Historia H11.6.
Dueno: Alejandro. Vive en `infra/` porque el arranque es infraestructura, no DDL.

EL PROBLEMA QUE ESTE GUION EXISTE PARA RESOLVER, ENCONTRADO ANTES DE QUE DOLIERA

`infra/docker/init-db/01-extensiones.sql` crea las extensiones y los cuatro
esquemas. Corre **una sola vez y solo desde docker-compose**, cuando el volumen
esta vacio, porque lo monta en `/docker-entrypoint-initdb.d`.

Eso alcanzo mientras la unica base del proyecto fue la de compose. El dia que
hay una base en otra parte -un proveedor de nube, la maquina de alguien que no
usa compose, un cluster- ese guion **no corre**, y entonces:

    Aplicando 001 001_control_migracion.sql ... FALLO
    schema "control" does not exist

Comprobado el 2026-09-04 contra un PostgreSQL 16 vacio: la migracion 001 cae en
la primera sentencia. No es una hipotesis, es la salida.

QUE HACE, Y QUE NO

Aplica el **mismo** `01-extensiones.sql` que compose, leido del disco y no
copiado aca: dos definiciones del arranque son dos bases distintas esperando a
que alguien las note. Despues informa contra que servidor quedo, para que las
diferencias con la base local se vean en vez de suponerse.

**No aplica migraciones y no crea usuarios.** Eso es `aplicar_migraciones.py` y
`crear_usuarios.py`, que son de Cesar y no se tocan. Este guion es el escalon
que faltaba antes del primero.

LA ZONA HORARIA, Y POR QUE NO VA LITERAL

`01-extensiones.sql` termina con `ALTER DATABASE geoguardian SET timezone`. El
nombre esta escrito porque en compose la base siempre se llama asi. En un
proveedor de nube la base puede llamarse de otra manera -la plantilla de Railway
crea `railway`-, y la sentencia fallaria con «database "geoguardian" does not
exist» **despues** de haber creado las extensiones, dejando el arranque a medias.

Por eso esa linea se reescribe aqui contra la base **a la que estamos
conectados**, y no se toca el archivo: el archivo tiene que seguir sirviendo tal
cual para compose y para el evaluador que lo lea.

`pg_stat_statements` ES OPCIONAL, A PROPOSITO

Necesita estar en `shared_preload_libraries` del servidor. En compose lo esta;
en una base gestionada puede no estarlo y no siempre se puede cambiar. Es una
extension de **observacion**: sin ella el sistema funciona igual y solo se pierde
la medicion de H1.11. Abortar el arranque entero por eso seria cambiar un
despliegue por una metrica. Se intenta, y si no se puede se dice con todas las
letras.

Las otras dos no son opcionales: sin PostGIS no hay geometrias y no hay
proyecto.

USO

    python -m infra.preparar_base                # con las variables de .env
    python -m infra.preparar_base --comprobar    # informa y no cambia nada
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import psycopg  # noqa: E402

from basedatos.conexion import ErrorConexion, conectar  # noqa: E402

ARRANQUE = RAIZ / "infra" / "docker" / "init-db" / "01-extensiones.sql"

#: Sin estas dos no hay proyecto. Si fallan, el guion falla.
EXTENSIONES_OBLIGATORIAS = ("postgis", "postgis_raster")

#: Observacion. Si falla, se dice y se sigue. Ver la cabecera.
EXTENSIONES_OPCIONALES = ("pg_stat_statements",)

#: Los cuatro de BD-2. El orden es el del archivo de arranque.
ESQUEMAS = ("geo", "crudo", "analitico", "control")

ZONA = "America/Costa_Rica"


#: Donde viven las migraciones, para leer que nombre de base exigen.
DDL = RAIZ / "basedatos" / "ddl"


class ErrorArranque(Exception):
    """El arranque no se pudo completar y no tiene sentido seguir."""


def bases_que_exigen_las_migraciones() -> dict[str, str]:
    """
    Que nombre de base exigen las migraciones, leido de ellas y no escrito aca.

    POR QUE ESTA COMPROBACION EXISTE

    `003_seguridad_roles.sql` tiene el nombre de la base **escrito literal**:

        REVOKE ALL   ON DATABASE geoguardian FROM PUBLIC;
        GRANT CONNECT ON DATABASE geoguardian TO ...;

    Es correcto -un `GRANT ON DATABASE` necesita nombrarla- y no se puede
    arreglar editando la migracion: una migracion aplicada **no se edita nunca**,
    y el aplicador compara su SHA-256 justamente para detectarlo.

    La consecuencia es una regla que hasta hoy no estaba escrita en ningun lado:
    **la base tiene que llamarse `geoguardian`**. Contra una base con otro
    nombre, el arranque pasa, las migraciones 001 y 002 pasan, y recien la 003
    falla. Comprobado el 2026-09-04 contra una base llamada `railway`, que es
    como se llama la que crea la plantilla de Railway:

        Aplicando 003 003_seguridad_roles.sql ... FALLO

    Este guion lo dice **antes**, y lo dice leyendo las migraciones: si algun dia
    dejan de exigirlo, la comprobacion desaparece sola en vez de quedar mintiendo.
    """
    exigencias: dict[str, str] = {}
    if not DDL.is_dir():
        return exigencias
    patron = re.compile(r"\bON\s+DATABASE\s+([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)
    for archivo in sorted(DDL.glob("*.sql")):
        for numero, linea in enumerate(archivo.read_text(encoding="utf-8").splitlines(), 1):
            if linea.strip().startswith("--"):
                continue
            for nombre in patron.findall(linea):
                exigencias.setdefault(nombre, f"{archivo.name}:{numero}")
    return exigencias


def sentencias_del_archivo(texto: str) -> list[str]:
    """
    Parte el archivo de arranque en sentencias, respetando comillas y comentarios.

    LA PRIMERA VERSION PARTIA POR `;` A SECAS, Y ESTABA MAL

    Quitaba solo las lineas que **empiezan** con `--`, asi que un comentario al
    final de una linea con codigo se pegaba a la sentencia siguiente. Se vio en
    la salida del 2026-09-04:

        ok  -- referencia territorial, casi estatica CREATE SCHEMA ... crudo

    Ejecutaba bien de casualidad -PostgreSQL entiende el `--` y descarta el resto
    de esa linea-, pero la fragilidad es real: **un `;` dentro de un comentario o
    de un texto entrecomillado partia una sentencia por la mitad**, y el archivo
    de arranque tiene textos entrecomillados en cada `COMMENT ON SCHEMA`.

    Esto recorre el texto respetando las comillas simples -con `''` como escape,
    que es como PostgreSQL las duplica-, descarta los comentarios `--` hasta el
    fin de linea, y corta solo en los `;` que quedan fuera de todo eso.

    Sigue sin entender `$$ ... $$`, y el arranque no los tiene. `verificar_h116`
    comprueba que no aparezcan: el dia que alguien agregue una funcion al
    arranque, el control cae en vez de partirla al medio en silencio.
    """
    sentencias: list[str] = []
    actual: list[str] = []
    dentro_de_texto = False
    i = 0

    while i < len(texto):
        caracter = texto[i]

        if dentro_de_texto:
            actual.append(caracter)
            if caracter == "'":
                # '' es una comilla escapada, no el cierre del texto.
                if i + 1 < len(texto) and texto[i + 1] == "'":
                    actual.append(texto[i + 1])
                    i += 2
                    continue
                dentro_de_texto = False
            i += 1
            continue

        if caracter == "'":
            dentro_de_texto = True
            actual.append(caracter)
            i += 1
            continue

        if texto.startswith("--", i):
            salto = texto.find("\n", i)
            i = len(texto) if salto == -1 else salto
            continue

        if caracter == ";":
            if actual and "".join(actual).strip():
                sentencias.append("".join(actual).strip())
            actual = []
            i += 1
            continue

        actual.append(caracter)
        i += 1

    if actual and "".join(actual).strip():
        sentencias.append("".join(actual).strip())
    return sentencias


def es_alter_database(sentencia: str) -> bool:
    return sentencia.upper().startswith("ALTER DATABASE")


def aplicar(conexion, sentencias: list[str], registrar) -> list[str]:
    """
    Ejecuta el arranque. Devuelve los avisos de lo opcional que no se pudo.

    Cada sentencia va en su **propia** transaccion. Con una sola, el fallo de
    `pg_stat_statements` revertiria tambien las extensiones que si se crearon, y
    entonces «opcional» no significaria nada.
    """
    avisos: list[str] = []
    base = conexion.info.dbname

    for sentencia in sentencias:
        # La linea de la zona horaria se reescribe contra la base conectada.
        # Ver la cabecera: el nombre literal del archivo es correcto para
        # compose y equivocado en cualquier otro lado.
        if es_alter_database(sentencia):
            sentencia = f'ALTER DATABASE "{base}" SET timezone TO {ZONA!r}'

        resumen = re.sub(r"\s+", " ", sentencia)[:70]
        opcional = next((e for e in EXTENSIONES_OPCIONALES if e in sentencia), None)
        try:
            with conexion.transaction(), conexion.cursor() as cursor:
                cursor.execute(sentencia)
        except psycopg.Error as error:
            if opcional is None:
                raise ErrorArranque(f"{resumen} -> {error}") from error
            avisos.append(f"{opcional}: {str(error).strip().splitlines()[0]}")
            registrar(f"  aviso  {resumen} ... NO SE PUDO, y se sigue")
            continue
        registrar(f"  ok     {resumen}")

    return avisos


def informe(conexion) -> dict[str, str]:
    """
    Contra que servidor quedo esto. Se informa para que las diferencias se vean.

    La base local del equipo es PostgreSQL 16 y una gestionada puede ser 17 u
    otra. La diferencia no rompe estas migraciones -se comprobo-, pero **si
    invalida restaurar un volcado binario de una en la otra**, y quien lea la
    evidencia tiene que poder saber sobre que corrio sin preguntar.
    """
    datos: dict[str, str] = {}
    with conexion.cursor() as cursor:
        cursor.execute("SELECT current_database(), version()")
        base, version = cursor.fetchone()
        datos["base"] = base
        datos["servidor"] = version.split(" on ")[0]

        cursor.execute("SELECT extname, extversion FROM pg_extension ORDER BY extname")
        datos["extensiones"] = ", ".join(f"{n} {v}" for n, v in cursor.fetchall())

        cursor.execute(
            "SELECT nspname FROM pg_namespace WHERE nspname = ANY(%s) ORDER BY nspname",
            (list(ESQUEMAS),),
        )
        datos["esquemas"] = ", ".join(fila[0] for fila in cursor.fetchall())

        # El cotejo es propiedad de la base, no un parametro del servidor:
        # `current_setting('lc_collate')` no existe desde PostgreSQL 16. Sale de
        # `pg_database`, que es donde vive de verdad. Importa porque el
        # `POSTGRES_INITDB_ARGS` de compose fija `es-CR` por I-02, y una base
        # gestionada casi seguro no lo hace: el orden de los textos difiere.
        cursor.execute(
            "SELECT datcollate, pg_encoding_to_char(encoding), datctype "
            "FROM pg_database WHERE datname = current_database()"
        )
        cotejo, codificacion, tipo = cursor.fetchone()
        datos["cotejo"] = f"{cotejo} / {tipo} · {codificacion}"

        cursor.execute("SELECT to_regclass('control.migracion') IS NOT NULL")
        datos["migraciones_ya"] = "si" if cursor.fetchone()[0] else "no"
    return datos


def faltantes(conexion) -> tuple[list[str], list[str]]:
    """Que esquemas y que extensiones obligatorias faltan. Vacio es estar listo."""
    with conexion.cursor() as cursor:
        cursor.execute("SELECT nspname FROM pg_namespace")
        hay_esquemas = {fila[0] for fila in cursor.fetchall()}
        cursor.execute("SELECT extname FROM pg_extension")
        hay_extensiones = {fila[0] for fila in cursor.fetchall()}
    return (
        [e for e in ESQUEMAS if e not in hay_esquemas],
        [e for e in EXTENSIONES_OBLIGATORIAS if e not in hay_extensiones],
    )


def main(argumentos: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        description="Prepara una base recien creada para recibir las migraciones"
    )
    analizador.add_argument(
        "--comprobar",
        action="store_true",
        help="Informa el estado y no cambia nada",
    )
    opciones = analizador.parse_args(argumentos)

    if not ARRANQUE.exists():
        print(f"\nNo esta el archivo de arranque: {ARRANQUE}\n")
        return 1

    try:
        conexion = conectar(autocommit=True)
    except ErrorConexion as error:
        print(f"\n{error}\n")
        return 1

    with conexion:
        estado = informe(conexion)
        print("\nBase conectada")
        print(f"  base:         {estado['base']}")
        print(f"  servidor:     {estado['servidor']}")
        print(f"  cotejo:       {estado['cotejo']}")
        print(f"  extensiones:  {estado['extensiones'] or '(ninguna)'}")
        print(f"  esquemas:     {estado['esquemas'] or '(ninguno)'}")
        print(f"  migraciones aplicadas antes: {estado['migraciones_ya']}")

        # Antes que nada: el nombre. Preparar una base que las migraciones van a
        # rechazar tres pasos despues es peor que no prepararla.
        exigencias = bases_que_exigen_las_migraciones()
        if exigencias and estado["base"] not in exigencias:
            esperado = ", ".join(sorted(exigencias))
            donde = " / ".join(f"{n} en {d}" for n, d in sorted(exigencias.items()))
            print(f"\nLa base se llama {estado['base']!r} y las migraciones exigen {esperado!r}.")
            print(f"  lo exige: {donde}")
            print("\nUna migracion aplicada no se edita nunca, asi que esto NO se arregla")
            print("cambiando el SQL: hay que crear la base con ese nombre y conectarse ahi.")
            print(f"\n    CREATE DATABASE {esperado};\n")
            print("Sin esto el arranque pasaria, tambien las migraciones 001 y 002,")
            print("y recien fallaria la 003.\n")
            return 1

        sin_esquema, sin_extension = faltantes(conexion)

        if opciones.comprobar:
            listo = not sin_esquema and not sin_extension
            print(f"\n{'Lista para migrar.' if listo else 'Le falta arranque:'}")
            for nombre in sin_esquema:
                print(f"  falta el esquema {nombre}")
            for nombre in sin_extension:
                print(f"  falta la extension {nombre}")
            print()
            return 0 if listo else 1

        if not sin_esquema and not sin_extension:
            print("\nYa estaba preparada. No se toca nada.")
            print("Sigue:  python -m basedatos.aplicar_migraciones\n")
            return 0

        print(f"\nAplicando {ARRANQUE.relative_to(RAIZ)}")
        sentencias = sentencias_del_archivo(ARRANQUE.read_text(encoding="utf-8"))
        try:
            avisos = aplicar(conexion, sentencias, print)
        except ErrorArranque as error:
            print(f"\nFALLO el arranque, y sin esto las migraciones no pueden correr:\n  {error}\n")
            return 1

        sin_esquema, sin_extension = faltantes(conexion)
        if sin_esquema or sin_extension:
            print("\nEl arranque corrio y aun asi falta algo. No sigas:")
            for nombre in sin_esquema + sin_extension:
                print(f"  falta {nombre}")
            print()
            return 1

        final = informe(conexion)
        print("\nPreparada.")
        print(f"  extensiones:  {final['extensiones']}")
        print(f"  esquemas:     {final['esquemas']}")
        if avisos:
            print("\nLo opcional que NO quedo, dicho y no escondido:")
            for aviso in avisos:
                print(f"  {aviso}")
            print("  El sistema funciona igual; se pierde la medicion de H1.11.")
        print("\nSigue:")
        print("  python -m basedatos.aplicar_migraciones")
        print("  python -m basedatos.seguridad.crear_usuarios")
        print("  python -m basedatos.seguridad.verificar_h18\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
