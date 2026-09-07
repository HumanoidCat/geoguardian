"""
Copia los datos de una base a otra, tabla por tabla. Historia H11.6.
Dueno: Alejandro. Vive en `infra/` porque es despliegue, no DDL.

QUE HACE Y QUE NO

Copia **solo los datos**. El esquema tiene que existir ya en el destino, puesto
por `infra/preparar_base.py` y `basedatos/aplicar_migraciones.py`: ese es el
camino por el que `control.migracion` queda poblada y coincidiendo con el
repositorio. Este guion no crea tablas, no crea roles y no aplica migraciones.

    origen    la base local, la de `.env`, con los datos reales
    destino   la base nueva, la de `--destino`, con el esquema ya aplicado

POR QUE NO ES UN `pg_dump | psql`

Podria serlo, y para un volcado completo lo seria. Lo que un volcado no hace es
lo que esta historia necesita:

  * **`control.migracion` no se copia.** Es el registro de que migraciones se
    aplicaron **en el destino**. Pisarlo con el del origen deja una base que
    afirma un estado que nadie le aplico, y el aplicador compara sumas SHA-256
    contra ese registro. Un volcado completo lo pisa sin preguntar.
  * **Las secuencias se dejan donde estan las del origen.** Sin eso la primera
    insercion del ETL choca contra una clave que ya existe, y el fallo aparece
    lejos de aqui.
  * **Se comprueba que copiar no fabrique historial de auditoria.** Ver abajo.
  * **Se cuenta antes y despues, y las cuentas se comparan.** El criterio CA-4
    de H11.6 pide exactamente eso, y un volcado que "no dio error" no es una
    comprobacion.

EL TRIGGER DE AUDITORIA: LO QUE SUPUSE, Y LO QUE MEDI

`analitico.riesgo` tiene `riesgo_auditoria_tg`, que escribe en
`analitico.riesgo_auditoria`. La primera version de este guion lo **apagaba
durante la copia**, razonando que si no, copiar 104 estimaciones fabricaria 104
filas de historial fechadas hoy, encima del historial verdadero.

**Ese razonamiento era falso, y lo dijo el sabotaje.** El apagado se quito a
proposito y el caso paso en verde: no habia nada que romper. El trigger es

    AFTER DELETE OR UPDATE ON analitico.riesgo

y una copia solo inserta. **No se dispara nunca durante una carga.** Apagarlo era
una precaucion contra algo que no pasa, con el costo de exigir ser dueno de la
tabla y el riesgo de dejarlo apagado si algo falla a mitad.

Lo que quedo en su lugar es la premisa **comprobada** en vez del arreglo: antes
de copiar, `comprobar_triggers_de_historial` lee la definicion real de cada
trigger y **se detiene si alguno dispara con INSERT**. El dia que alguien agregue
`OR INSERT` -que es un cambio razonable y que nadie pensaria en relacionar con
esto- la carga se planta y explica por que, en vez de fabricar un historial
silenciosamente.

LO QUE `--reemplazar` DESTRUYE, DICHO ANTES DE QUE PASE

`TRUNCATE` **no dispara triggers de fila**. Vaciar `analitico.riesgo` para
recargar borra estimaciones auditadas **sin dejar rastro en la auditoria**. En un
destino recien creado da igual porque no hay nada; en una recarga sobre datos
reales, no. El guion lo advierte con las filas que va a borrar y solo lo hace si
se lo pide explicitamente.

USO

    python -m infra.cargar_datos --destino .env.railway --comprobar
    python -m infra.cargar_datos --destino .env.railway
    python -m infra.cargar_datos --destino .env.railway --reemplazar
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import psycopg  # noqa: E402
from dotenv import dotenv_values  # noqa: E402

from basedatos.conexion import cadena_conexion  # noqa: E402

ESQUEMAS = ("geo", "crudo", "analitico", "control")

#: NO se copia: es el registro de lo que se aplico **en el destino**.
#: Pisarlo deja una base que afirma un estado que nadie le aplico.
NO_SE_COPIAN = ("control.migracion",)

#: Triggers que escriben historial. NO se apagan: se comprueba que sigan sin
#: dispararse con INSERT, que es lo unico que hace una copia. Ver la cabecera.
TRIGGERS_DE_HISTORIAL = (("analitico.riesgo", "riesgo_auditoria_tg"),)


class ErrorCarga(Exception):
    """La carga no se puede hacer con garantias. Se detiene sin escribir."""


# --------------------------------------------------------------------------- #
# Conexiones                                                                   #
# --------------------------------------------------------------------------- #


def cadena_desde(archivo: Path) -> str:
    """
    Arma la cadena de conexion de otro `.env`, **con la misma funcion de siempre**.

    `cadena_conexion()` lee de `os.environ`. Se le presta el entorno un momento
    en vez de copiar su logica aca: dos definiciones de como se arma una cadena
    de conexion es como se termina apuntando a la base equivocada.
    """
    valores = dotenv_values(archivo)
    if not valores:
        raise ErrorCarga(f"{archivo} no existe o esta vacio")
    previo = {clave: os.environ.get(clave) for clave in valores}
    try:
        for clave, valor in valores.items():
            if valor is not None:
                os.environ[clave] = valor
        return cadena_conexion()
    finally:
        for clave, valor in previo.items():
            if valor is None:
                os.environ.pop(clave, None)
            else:
                os.environ[clave] = valor


def describir(conexion) -> str:
    with conexion.cursor() as cursor:
        cursor.execute("SELECT current_database(), inet_server_addr(), inet_server_port()")
        base, direccion, puerto = cursor.fetchone()
    return f"{base} en {direccion or 'local'}:{puerto}"


# --------------------------------------------------------------------------- #
# Que tablas, y en que orden                                                   #
# --------------------------------------------------------------------------- #


def tablas_de(conexion) -> list[str]:
    """Las tablas de los cuatro esquemas, sin particiones: la copia va al padre."""
    with conexion.cursor() as cursor:
        cursor.execute(
            "SELECT n.nspname || '.' || c.relname "
            "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = ANY(%s) AND c.relkind IN ('r', 'p') "
            "AND NOT c.relispartition ORDER BY 1",
            (list(ESQUEMAS),),
        )
        return [fila[0] for fila in cursor.fetchall()]


def dependencias(conexion, tablas: list[str]) -> dict[str, set[str]]:
    """
    De que otras tablas depende cada una, por llave foranea.

    Se lee del catalogo y no se escribe a mano: el orden de carga tiene que
    seguir al esquema, no a lo que alguien recuerde del esquema. Las llaves de
    las particiones se resuelven a su tabla padre.
    """
    with conexion.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COALESCE(ph.oid, h.oid)::regclass::text,
                COALESCE(pp.oid, p.oid)::regclass::text
            FROM pg_constraint con
            JOIN pg_class h ON h.oid = con.conrelid
            JOIN pg_class p ON p.oid = con.confrelid
            LEFT JOIN pg_inherits ih ON ih.inhrelid = h.oid
            LEFT JOIN pg_class ph ON ph.oid = ih.inhparent
            LEFT JOIN pg_inherits ip ON ip.inhrelid = p.oid
            LEFT JOIN pg_class pp ON pp.oid = ip.inhparent
            WHERE con.contype = 'f'
            """
        )
        crudas = cursor.fetchall()

    conocidas = set(tablas)
    mapa: dict[str, set[str]] = {t: set() for t in tablas}
    for hijo, padre in crudas:
        if hijo in conocidas and padre in conocidas and hijo != padre:
            mapa[hijo].add(padre)
    return mapa


def orden_de_carga(mapa: dict[str, set[str]]) -> list[str]:
    """
    Padres antes que hijos. Alfabetico dentro de cada nivel, para que no cambie.

    Si quedara un ciclo, se detiene: cargar en un orden inventado deja fallos de
    llave foranea a mitad de camino, con la mitad de los datos adentro.
    """
    pendientes = {t: set(padres) for t, padres in mapa.items()}
    orden: list[str] = []
    while pendientes:
        listas = sorted(t for t, padres in pendientes.items() if not padres)
        if not listas:
            raise ErrorCarga(f"hay un ciclo de llaves foraneas entre {sorted(pendientes)}")
        orden.extend(listas)
        for tabla in listas:
            del pendientes[tabla]
        for padres in pendientes.values():
            padres.difference_update(listas)
    return orden


# --------------------------------------------------------------------------- #
# Comprobaciones previas                                                       #
# --------------------------------------------------------------------------- #


def columnas_de(conexion, tabla: str) -> list[tuple[str, str]]:
    esquema, nombre = tabla.split(".", 1)
    with conexion.cursor() as cursor:
        cursor.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
            (esquema, nombre),
        )
        return [(c, t) for c, t in cursor.fetchall()]


def registro_del_destino(conexion) -> list[tuple]:
    """Foto del registro de migraciones: numero, archivo y suma. Se compara despues."""
    with conexion.cursor() as cursor:
        cursor.execute(
            "SELECT numero, archivo, suma_sha256 FROM control.migracion ORDER BY numero, archivo"
        )
        return cursor.fetchall()


def contar(conexion, tabla: str) -> int:
    with conexion.cursor() as cursor:
        cursor.execute(f"SELECT count(*) FROM {tabla}")  # noqa: S608 - viene del catalogo
        return cursor.fetchone()[0]


def comprobar_esquemas_iguales(origen, destino, tablas: list[str]) -> None:
    """
    Mismas columnas, mismo tipo, mismo orden. Si no, no se copia nada.

    La copia va en formato binario, que es rapido y exacto **y no comprueba
    nada**: si una columna cambio de tipo o de posicion, el destino queda con
    datos corridos y sin ningun error. Esta comprobacion es lo unico que separa
    eso de una carga correcta, y por eso corre antes de escribir la primera fila.
    """
    problemas: list[str] = []
    for tabla in tablas:
        aca, alla = columnas_de(origen, tabla), columnas_de(destino, tabla)
        if aca != alla:
            solo_origen = [c for c in aca if c not in alla]
            solo_destino = [c for c in alla if c not in aca]
            detalle = []
            if solo_origen:
                detalle.append(f"solo en el origen: {solo_origen}")
            if solo_destino:
                detalle.append(f"solo en el destino: {solo_destino}")
            if not detalle:
                detalle.append("mismas columnas en distinto orden")
            problemas.append(f"  {tabla}: {'; '.join(detalle)}")
    if problemas:
        raise ErrorCarga(
            "el esquema del destino no coincide con el del origen:\n"
            + "\n".join(problemas)
            + "\n\nAplica las migraciones en el destino antes de cargar."
        )


# --------------------------------------------------------------------------- #
# El trigger de auditoria                                                      #
# --------------------------------------------------------------------------- #


def definicion_de_trigger(conexion, tabla: str, trigger: str) -> str | None:
    with conexion.cursor() as cursor:
        cursor.execute(
            "SELECT pg_get_triggerdef(oid) FROM pg_trigger "
            "WHERE tgrelid = %s::regclass AND tgname = %s AND NOT tgisinternal",
            (tabla, trigger),
        )
        fila = cursor.fetchone()
    return None if fila is None else fila[0]


def comprobar_triggers_de_historial(destino, registrar) -> None:
    """
    Comprueba la premisa de la que depende que copiar no invente historial.

    Una copia **solo inserta**. Mientras los triggers de historial disparen con
    DELETE o UPDATE y no con INSERT, cargar no escribe una sola fila de
    auditoria, y el historial del destino es exactamente el del origen.

    Si alguien agrega `OR INSERT` -un cambio razonable, que nadie relacionaria
    con esto-, cada fila copiada fabricaria una entrada fechada el dia de la
    carga. Aca se detiene, en vez de descubrirlo mirando una auditoria que dice
    que todas las estimaciones nacieron el mismo martes.
    """
    for tabla, trigger in TRIGGERS_DE_HISTORIAL:
        definicion = definicion_de_trigger(destino, tabla, trigger)
        if definicion is None:
            registrar(f"  aviso  {tabla}.{trigger} no existe en el destino")
            continue
        cabecera = definicion.upper().split(" ON ")[0]
        if "INSERT" in cabecera:
            raise ErrorCarga(
                f"{tabla}.{trigger} dispara con INSERT:\n    {definicion}\n\n"
                "Copiar filas escribiria historial de auditoria falso, fechado hoy. "
                "Hay que apagarlo durante la carga y volver a encenderlo, o cargar "
                "de otra manera. Este guion no lo hace solo a proposito: apagar la "
                "auditoria de una base es una decision, no un detalle."
            )
        registrar(f"  ok     {tabla}.{trigger} no dispara con INSERT: copiar no lo activa")


# --------------------------------------------------------------------------- #
# La copia                                                                     #
# --------------------------------------------------------------------------- #


def copiar(origen, destino, tabla: str) -> int:
    """Copia una tabla entera en binario, en trozos, sin traerla a memoria."""
    columnas = ", ".join(f'"{c}"' for c, _ in columnas_de(origen, tabla))
    leer = f"COPY (SELECT {columnas} FROM {tabla}) TO STDOUT (FORMAT BINARY)"  # noqa: S608
    escribir = f"COPY {tabla} ({columnas}) FROM STDIN (FORMAT BINARY)"

    with origen.cursor().copy(leer) as fuente, destino.cursor().copy(escribir) as sumidero:
        for bloque in fuente:
            sumidero.write(bloque)
    return contar(destino, tabla)


def igualar_secuencias(origen, destino, registrar) -> None:
    """
    Deja cada secuencia del destino donde esta la del origen.

    Sin esto la primera fila que inserte el ETL choca contra una clave que ya
    existe, y el fallo aparece lejos de aca, en la primera corrida real.
    """
    with origen.cursor() as cursor:
        cursor.execute(
            "SELECT n.nspname || '.' || c.relname FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE c.relkind = 'S' AND n.nspname = ANY(%s) ORDER BY 1",
            (list(ESQUEMAS),),
        )
        secuencias = [fila[0] for fila in cursor.fetchall()]

    for secuencia in secuencias:
        with origen.cursor() as cursor:
            cursor.execute(f"SELECT last_value, is_called FROM {secuencia}")  # noqa: S608
            ultimo, usada = cursor.fetchone()
        with destino.cursor() as cursor:
            cursor.execute("SELECT setval(%s, %s, %s)", (secuencia, ultimo, usada))
        registrar(f"  {secuencia:38} -> {ultimo}")


def vaciar(destino, orden: list[str], registrar) -> None:
    """
    Vacia en orden inverso al de carga: hijos antes que padres.

    `RESTART IDENTITY` porque si no, las columnas de identidad siguen contando
    desde donde iban y la secuencia del destino queda por delante de la del
    origen. `igualar_secuencias` la corrige despues, pero una secuencia que
    depende de dos pasos en vez de uno es una secuencia que algun dia va a
    quedar mal.

    **Y esto borra sin auditoria.** `TRUNCATE` no dispara triggers de fila, asi
    que vaciar `analitico.riesgo` se lleva estimaciones auditadas sin dejar
    rastro en `analitico.riesgo_auditoria`. En un destino recien creado no hay
    nada que perder; sobre datos reales, si.
    """
    for tabla in reversed(orden):
        with destino.cursor() as cursor:
            cursor.execute(f"TRUNCATE {tabla} RESTART IDENTITY CASCADE")  # noqa: S608
        registrar(f"  vaciada {tabla}")


# --------------------------------------------------------------------------- #
# Programa                                                                     #
# --------------------------------------------------------------------------- #


def main(argumentos: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description="Copia los datos de una base a otra")
    analizador.add_argument(
        "--destino", type=Path, required=True, help="Archivo .env de la base destino"
    )
    analizador.add_argument(
        "--comprobar", action="store_true", help="Compara las dos bases y no escribe nada"
    )
    analizador.add_argument(
        "--reemplazar", action="store_true", help="Vacia las tablas del destino antes de cargar"
    )
    opciones = analizador.parse_args(argumentos)

    try:
        cadena_destino = cadena_desde(opciones.destino)
    except ErrorCarga as error:
        print(f"\n{error}\n")
        return 1

    with psycopg.connect(cadena_conexion()) as origen, psycopg.connect(cadena_destino) as destino:
        origen.autocommit = True
        print(f"\norigen   {describir(origen)}")
        print(f"destino  {describir(destino)}")

        if origen.info.get_parameters() == destino.info.get_parameters() and describir(
            origen
        ) == describir(destino):
            print("\nEl origen y el destino son la misma base. No hay nada que copiar.\n")
            return 1

        tablas = [t for t in tablas_de(origen) if t not in NO_SE_COPIAN]
        faltan = set(tablas) - set(tablas_de(destino))
        if faltan:
            print(f"\nAl destino le faltan tablas: {sorted(faltan)}")
            print("Aplica el esquema primero:")
            print("  python -m infra.preparar_base")
            print("  python -m basedatos.aplicar_migraciones\n")
            return 1

        try:
            comprobar_esquemas_iguales(origen, destino, tablas)
        except ErrorCarga as error:
            print(f"\n{error}\n")
            return 1

        orden = orden_de_carga(dependencias(origen, tablas))
        antes = {t: (contar(origen, t), contar(destino, t)) for t in orden}
        registro_antes = registro_del_destino(destino)

        print(f"\n{'tabla':30} {'origen':>10} {'destino':>10}")
        for tabla in orden:
            print(f"{tabla:30} {antes[tabla][0]:>10} {antes[tabla][1]:>10}")
        print(f"\nNo se copia: {', '.join(NO_SE_COPIAN)} (es el registro del destino)")

        if opciones.comprobar:
            print("\nSolo se comprobo. Nada se escribio.\n")
            return 0

        con_datos = [t for t in orden if antes[t][1] > 0]
        if con_datos and not opciones.reemplazar:
            print(f"\nEl destino ya tiene datos en: {', '.join(con_datos)}")
            print("\nUna base recien migrada ya trae las filas de referencia que siembran las")
            print("migraciones -fuentes y productos-, asi que esto es lo normal la primera vez.")
            print("Con --reemplazar se vacian primero. Sin eso, no se toca nada.\n")
            return 1

        auditadas = [t for t, _ in TRIGGERS_DE_HISTORIAL if t in con_datos and antes[t][1] > 0]
        if auditadas:
            print("\nAVISO: --reemplazar vacia estas tablas auditadas SIN dejar rastro")
            print("en la auditoria, porque TRUNCATE no dispara triggers de fila:")
            for tabla in auditadas:
                print(f"  {tabla}: se pierden {antes[tabla][1]} filas")

        try:
            with destino.transaction():
                print("\nTriggers de historial")
                comprobar_triggers_de_historial(destino, print)
                if con_datos:
                    print("\nVaciando el destino")
                    vaciar(destino, orden, print)
                print("\nCopiando")
                for tabla in orden:
                    filas = copiar(origen, destino, tabla)
                    esperadas = antes[tabla][0]
                    marca = "ok " if filas == esperadas else "MAL"
                    print(f"  {marca} {tabla:30} {filas:>10} de {esperadas}")
                print("\nSecuencias")
                igualar_secuencias(origen, destino, print)
        except ErrorCarga as error:
            print(f"\nFALLO: {error}\n")
            return 1
        except psycopg.Error as error:
            print(f"\nFALLO y no se escribio nada: {error}\n")
            return 1

        # El registro de migraciones del destino tiene que ser el suyo, intacto.
        #
        # `NO_SE_COPIAN` es lo unico que lo protege, y quitarlo de esa lista no
        # produce ningun error: la copia funciona, las cuentas cuadran, y el
        # destino queda afirmando que le aplicaron migraciones con sumas SHA-256
        # que son las del origen. Se comprobo sabotenandolo, y paso en verde.
        # Por eso se compara contra la foto tomada antes de escribir.
        if registro_antes != registro_del_destino(destino):
            print("\nEl registro de migraciones del destino CAMBIO durante la carga.")
            print(f"Esto no deberia poder pasar: {', '.join(NO_SE_COPIAN)} no se copia.")
            print("La base quedo afirmando un estado que nadie le aplico. No la uses.\n")
            return 1

        print(f"\n{'tabla':30} {'origen':>10} {'destino':>10}")
        diferencias = []
        for tabla in orden:
            aca, alla = contar(origen, tabla), contar(destino, tabla)
            print(f"{tabla:30} {aca:>10} {alla:>10}{'' if aca == alla else '   <- NO COINCIDE'}")
            if aca != alla:
                diferencias.append(tabla)

        if diferencias:
            print(f"\nNO coinciden: {', '.join(diferencias)}. La carga no esta completa.\n")
            return 1
        print("\nTodas las cuentas coinciden.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
