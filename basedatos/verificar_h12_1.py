"""
Verificador de H12.1 · La bitacora de corridas, extendida para el diagnostico.

Dueno de la historia: Luna, traspasada desde Cesar el 2026-09-03 por **D-37**.
La excepcion de propiedad sobre `basedatos/` esta declarada en
`docs/07-propiedad-archivos.md`, seccion «Excepcion: H12.1, para Luna».

Comprueba los criterios de
`docs/evidencias/arquitectura-software/H12.1-criterios-aceptacion.md`.

QUE HACE ANTES DE COMPROBAR NADA
--------------------------------

Empieza por un informe de ESTADO DE LOS DATOS que no comprueba nada y no falla
nunca. Esta primero a proposito.

Las tres restricciones que la migracion 014 agrega van con `NOT VALID`: se
aplican a lo que entre desde ahora, y **las filas que ya existian no se
revisaron**. Esa decision solo vale si alguien mira despues. Este informe es ese
alguien.

Si el informe encuentra filas que violan una restriccion, **eso es un hallazgo
sobre los datos y va a la evidencia antes de corregirse**. No se arregla en
silencio y no se convierte en un fallo del verificador: un dato malo heredado no
es un defecto de esta historia, es informacion que esta historia hizo visible.

Y si el informe dice que la tabla esta vacia, **tambien hay que escribirlo**. Una
restriccion que no encontro violaciones sobre cero filas no demostro nada. Es la
diferencia entre «se comprobo y esta limpio» y «no habia nada que comprobar», y
confundirlas seria darse por verificado gratis.

QUE NO COMPRUEBA
----------------

El **criterio 10** -que el ETL de H1.14 siga corriendo despues de la extension-
no se puede comprobar desde aca: necesita red y descarga datos reales. Va como
comando aparte en la evidencia:

    python -m backend.etl.ingestar --evento lluvia_intensa

Es el criterio que mas importa de los doce, porque los otros once se pueden
cumplir con una migracion perfecta que rompa el trabajo de otro.

USO
---

    docker compose up -d
    python -m basedatos.aplicar_migraciones
    python -m basedatos.verificar_h12_1

Todo lo que escribe lo escribe dentro de un SAVEPOINT y lo deshace al terminar.
La conexion se cierra con ROLLBACK: el verificador no deja filas.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RUTA_MIGRACION = Path(__file__).resolve().parent / "ddl" / "014_bitacora_etl_diagnostico.sql"

# La migracion abre y cierra su propia transaccion. Para reejecutarla dentro de
# un SAVEPOINT hay que quitar esas dos lineas: un COMMIT aca dentro cerraria la
# transaccion del verificador y las filas de prueba quedarian escritas.
#
# Solo se quitan las lineas que son EXACTAMENTE `BEGIN;` o `COMMIT;` al margen
# izquierdo. Los `BEGIN` de los bloques `DO $$` van indentados y sin punto y
# coma, asi que no los toca.
PATRON_TRANSACCION = re.compile(r"^(BEGIN|COMMIT);\s*$", re.MULTILINE)

COLUMNAS_NUEVAS = {
    "sqlstate": "text",
    "filas_leidas": "bigint",
    "version_codigo": "text",
    "reportado_por": "text",
}

RESTRICCIONES_NO_VALIDADAS = (
    "bitacora_etl_fin_coherente_ck",
    "bitacora_etl_orden_temporal_ck",
    "fallo_corrida_fk",
)


class Resultado:
    def __init__(self) -> None:
        self.fallos: list[str] = []
        self.hechos = 0
        self.hallazgos: list[str] = []

    def comprobar(self, nombre: str, condicion: bool, detalle: str = "") -> None:
        self.hechos += 1
        print(f"  {'ok   ' if condicion else 'FALLA'}  {nombre}")
        if not condicion:
            self.fallos.append(f"{nombre}{': ' + detalle if detalle else ''}")
        elif detalle:
            print(f"           {detalle}")

    def anotar(self, texto: str) -> None:
        self.hallazgos.append(texto)


# --------------------------------------------------------------------------- #
# Estado de los datos: no comprueba, informa                                    #
# --------------------------------------------------------------------------- #


def informar_estado(conexion, r: Resultado) -> None:
    cur = conexion.cursor()
    print("\nESTADO DE LOS DATOS ANTES DE COMPROBAR NADA\n")

    cur.execute("SELECT count(*) FROM control.bitacora_etl")
    corridas = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM control.fallo")
    fallos = cur.fetchone()[0]
    print(f"  control.bitacora_etl  {corridas} filas")
    print(f"  control.fallo         {fallos} filas")

    if corridas == 0:
        r.anotar(
            "control.bitacora_etl estaba VACIA al aplicar la 014. Las tres "
            "restricciones NOT VALID no encontraron violaciones porque no habia "
            "filas que violarlas. No se comprobo contra datos heredados."
        )

    cur.execute("""
        SELECT count(*) FROM control.bitacora_etl
        WHERE NOT ((estado =  'en_curso' AND terminada_en IS NULL)
                OR (estado <> 'en_curso' AND terminada_en IS NOT NULL))
    """)
    incoherentes = cur.fetchone()[0]

    cur.execute("""
        SELECT count(*) FROM control.bitacora_etl
        WHERE terminada_en IS NOT NULL AND terminada_en < iniciada_en
    """)
    invertidas = cur.fetchone()[0]

    cur.execute("""
        SELECT count(*) FROM control.fallo f
        WHERE f.corrida_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM control.bitacora_etl b WHERE b.id = f.corrida_id)
    """)
    huerfanas = cur.fetchone()[0]

    print(f"\n  filas que violan la coherencia estado/terminada_en   {incoherentes}")
    print(f"  filas con terminada_en anterior a iniciada_en        {invertidas}")
    print(f"  filas de control.fallo con corrida_id inexistente    {huerfanas}")

    if incoherentes:
        r.anotar(
            f"{incoherentes} corridas quedaron con estado y terminada_en "
            "incoherentes ANTES de esta migracion. Van a la evidencia antes de "
            "corregirse: son la razon por la que la restriccion entro NOT VALID."
        )
    if invertidas:
        r.anotar(f"{invertidas} corridas tienen una duracion negativa.")
    if huerfanas:
        r.anotar(
            f"{huerfanas} filas de control.fallo apuntan a corridas que no "
            "existen. La clave foranea entro NOT VALID justamente por esto."
        )

    cur.execute(
        "SELECT conname, convalidated FROM pg_constraint WHERE conname = ANY(%s) ORDER BY conname",
        (list(RESTRICCIONES_NO_VALIDADAS),),
    )
    print("\n  Restricciones que siguen sin validar contra las filas viejas:")
    for nombre, validada in cur.fetchall():
        print(f"    {nombre:35s} {'validada' if validada else 'NOT VALID'}")
    print(
        "\n  NOT VALID no significa apagada: muerde en todo lo que entre desde\n"
        "  ahora. Significa que las filas anteriores no se revisaron, y por eso\n"
        "  estan los tres conteos de arriba."
    )


# --------------------------------------------------------------------------- #
# Los criterios                                                                 #
# --------------------------------------------------------------------------- #


def verificar(conexion, r: Resultado) -> None:
    import psycopg

    cur = conexion.cursor()
    print("\nCRITERIOS DE ACEPTACION DE H12.1\n")

    # ------------------------------------------------------------------ 0
    cur.execute("SELECT count(*) FROM control.migracion WHERE numero = 14")
    if cur.fetchone()[0] != 1:
        r.comprobar("0. la migracion 014 esta aplicada", False, "corre aplicar_migraciones")
        return

    # ------------------------------------------------------------------ 1
    #
    # Son CUATRO columnas, no cinco. Los criterios escritos el 3 de septiembre
    # dicen «las cinco columnas nuevas» porque contaban el estado `parcial` como
    # una mas, y `parcial` no es una columna: es un valor admitido por el CHECK
    # de una columna que ya existia. La tabla de faltantes de ese mismo documento
    # lista cuatro. Se corrige el criterio, no el codigo.
    cur.execute("""
        SELECT column_name, data_type, is_nullable
          FROM information_schema.columns
         WHERE table_schema = 'control' AND table_name = 'bitacora_etl'
    """)
    presentes = {c: (t, n) for c, t, n in cur.fetchall()}

    for columna, tipo in COLUMNAS_NUEVAS.items():
        encontrada = presentes.get(columna)
        r.comprobar(
            f"1. control.bitacora_etl.{columna} existe como {tipo}",
            encontrada is not None and encontrada[0] == tipo,
            f"esta como {encontrada}" if encontrada else "no existe",
        )
        if encontrada:
            r.comprobar(
                "   y admite NULL, porque las corridas viejas no tienen ese dato",
                encontrada[1] == "YES",
            )

    cur.execute("SAVEPOINT prueba")

    def corrida(proceso: str = "prueba.h12_1") -> int:
        """Abre una corrida en curso y devuelve su id. Sin terminada_en, que es
        lo unico coherente con el estado 'en_curso' desde la 014."""
        cur.execute(
            "INSERT INTO control.bitacora_etl (proceso, estado) "
            "VALUES (%s, 'en_curso') RETURNING id",
            (proceso,),
        )
        return cur.fetchone()[0]

    # ------------------------------------------------------------------ 2
    cur.execute("SAVEPOINT c2")
    try:
        cur.execute(
            "INSERT INTO control.bitacora_etl (proceso, estado, terminada_en) "
            "VALUES ('prueba.h12_1', 'parcial', now())"
        )
        acepta_parcial = True
    except psycopg.errors.CheckViolation:
        acepta_parcial = False
    cur.execute("ROLLBACK TO SAVEPOINT c2")
    r.comprobar("2. el estado 'parcial' se acepta", acepta_parcial)

    cur.execute("SAVEPOINT c2b")
    try:
        cur.execute(
            "INSERT INTO control.bitacora_etl (proceso, estado, terminada_en) "
            "VALUES ('prueba.h12_1', 'casi', now())"
        )
        rechaza_invento = False
    except psycopg.errors.CheckViolation:
        rechaza_invento = True
    cur.execute("ROLLBACK TO SAVEPOINT c2b")
    r.comprobar("   y un estado inventado se rechaza", rechaza_invento)

    # ------------------------------------------------------------------ 3
    #
    # La idempotencia NO se puede comprobar con el aplicador: guarda la suma
    # SHA-256 de cada archivo y **nunca reaplica uno ya aplicado**, asi que
    # correrlo dos veces no prueba nada del archivo, solo del aplicador.
    #
    # Aca se ejecuta el contenido del archivo dos veces seguidas, a mano, dentro
    # del savepoint. Asi fue como aparecio que a `bitacora_etl_leidas_ck` le
    # faltaba su `DROP CONSTRAINT IF EXISTS`.
    sql = PATRON_TRANSACCION.sub("", RUTA_MIGRACION.read_text(encoding="utf-8"))
    cur.execute("SAVEPOINT c3")
    try:
        cur.execute(sql)
        cur.execute(sql)
        idempotente, detalle = True, "el contenido del archivo se ejecuto dos veces sin error"
    except psycopg.Error as error:
        idempotente, detalle = False, str(error).strip().splitlines()[0]
        cur.execute("ROLLBACK TO SAVEPOINT c3")
    r.comprobar("3. la migracion es idempotente", idempotente, detalle)

    # ------------------------------------------------------------------ 4
    abierta = corrida()
    cur.execute("SAVEPOINT c4")
    try:
        cur.execute("UPDATE control.bitacora_etl SET estado = 'exitosa' WHERE id = %s", (abierta,))
        cierre_sin_fecha = True
    except psycopg.errors.CheckViolation:
        cierre_sin_fecha = False
    cur.execute("ROLLBACK TO SAVEPOINT c4")
    r.comprobar(
        "4. una corrida no puede cerrarse sin terminada_en",
        not cierre_sin_fecha,
        "quedo 'exitosa' con terminada_en en NULL" if cierre_sin_fecha else "",
    )

    cur.execute("SAVEPOINT c4b")
    try:
        cur.execute(
            "UPDATE control.bitacora_etl SET terminada_en = now() WHERE id = %s", (abierta,)
        )
        en_curso_con_fecha = True
    except psycopg.errors.CheckViolation:
        en_curso_con_fecha = False
    cur.execute("ROLLBACK TO SAVEPOINT c4b")
    r.comprobar("   ni quedar 'en_curso' con fecha de fin", not en_curso_con_fecha)

    cur.execute(
        "UPDATE control.bitacora_etl SET estado = 'exitosa', terminada_en = now() WHERE id = %s",
        (abierta,),
    )
    r.comprobar("   y el cierre correcto sigue funcionando", cur.rowcount == 1)

    # ------------------------------------------------------------------ 5 y 6
    cur.execute("SELECT coalesce(max(id), 0) + 1000 FROM control.bitacora_etl")
    inexistente = cur.fetchone()[0]

    cur.execute("SAVEPOINT c5")
    try:
        cur.execute(
            "INSERT INTO control.fallo (origen, sqlstate, mensaje, corrida_id) "
            "VALUES ('prueba.h12_1', '23514', 'prueba', %s)",
            (inexistente,),
        )
        acepto_huerfana = True
    except psycopg.errors.ForeignKeyViolation:
        acepto_huerfana = False
    cur.execute("ROLLBACK TO SAVEPOINT c5")
    r.comprobar("5. la clave foranea rechaza una corrida inexistente", not acepto_huerfana)

    cur.execute(
        "INSERT INTO control.fallo (origen, sqlstate, mensaje, corrida_id) "
        "VALUES ('prueba.h12_1', '23514', 'fuera de corrida', NULL) RETURNING corrida_id"
    )
    r.comprobar(
        "6. escribir fuera de una corrida sigue siendo legitimo",
        cur.fetchone()[0] is None,
        "NULL significa «fuera de una corrida», no «se olvidaron de anotarlo»",
    )

    # ------------------------------------------------------------------ 7
    enlazada = corrida()
    cur.execute(
        "INSERT INTO control.fallo (origen, sqlstate, mensaje, corrida_id) "
        "VALUES ('prueba.h12_1', '23514', 'atribuida', %s)",
        (enlazada,),
    )
    cur.execute("SAVEPOINT c7")
    try:
        cur.execute("DELETE FROM control.bitacora_etl WHERE id = %s", (enlazada,))
        borro = True
    except psycopg.errors.ForeignKeyViolation:
        borro = False
    cur.execute("ROLLBACK TO SAVEPOINT c7")
    r.comprobar(
        "7. borrar una corrida con filas rechazadas es rechazado",
        not borro,
        "ON DELETE RESTRICT: las filas no quedan hablando de algo que ya no existe",
    )

    # ------------------------------------------------------------------ 8
    cur.execute(
        "SELECT count(*) FROM pg_indexes "
        "WHERE schemaname = 'control' AND indexname = 'bitacora_etl_en_curso_ix'"
    )
    r.comprobar("8. el indice parcial sobre 'en_curso' existe", cur.fetchone()[0] == 1)

    consulta_muertas = (
        "SELECT id, proceso, iniciada_en FROM control.bitacora_etl "
        "WHERE estado = 'en_curso' AND iniciada_en < now() - interval '6 hours'"
    )
    cur.execute(f"EXPLAIN {consulta_muertas}")
    plan_libre = "\n".join(f[0] for f in cur.fetchall())

    cur.execute("SET LOCAL enable_seqscan = off")
    cur.execute(f"EXPLAIN {consulta_muertas}")
    plan_forzado = "\n".join(f[0] for f in cur.fetchall())
    cur.execute("SET LOCAL enable_seqscan = on")

    r.comprobar(
        "   y el planificador PUEDE usarlo para las corridas muertas",
        "bitacora_etl_en_curso_ix" in plan_forzado,
        "medido con enable_seqscan = off",
    )
    # EL AVISO VA EN LOS DOS CASOS, Y ESA SIMETRIA ES EL PUNTO.
    #
    # La primera version solo avisaba si el planificador NO elegia el indice.
    # Eso convertia el caso contrario en una victoria silenciosa: si lo elegia,
    # nadie decia nada y quedaba pareciendo una mejora medida.
    #
    # **Con esta cantidad de filas ninguno de los dos resultados significa nada.**
    # Un plan sobre una tabla practicamente vacia no dice si el indice sirve;
    # dice que el planificador tenia poco que comparar. Callarse en el caso
    # favorable seria contar solo la mitad que conviene.
    cur.execute("SELECT count(*) FROM control.bitacora_etl")
    volumen = cur.fetchone()[0]
    elegido = "bitacora_etl_en_curso_ix" in plan_libre

    if volumen < 1000:
        r.anotar(
            f"El plan del criterio 8 se midio sobre {volumen} filas, y el "
            f"planificador {'SI' if elegido else 'NO'} eligio el indice parcial "
            "por su cuenta. Con este volumen el resultado no es evidencia en "
            "ninguna de las dos direcciones: lo unico demostrado es que el "
            "indice EXISTE y que el planificador PUEDE usarlo. **No presentar "
            "esto como una mejora de rendimiento medida.** Se vuelve a medir "
            "cuando la tabla tenga corridas reales acumuladas."
        )
    elif not elegido:
        r.anotar(
            f"Con {volumen} filas el planificador sigue prefiriendo recorrer la "
            "tabla. Ya no es falta de volumen: hay que revisar si el indice "
            "parcial se justifica o si la consulta de H12.4 no lo aprovecha."
        )

    # ------------------------------------------------------------------ 9
    api = corrida(proceso="api")
    cur.execute(
        "UPDATE control.bitacora_etl SET estado = 'exitosa', terminada_en = now(), "
        "filas_leidas = 120, filas = 118, version_codigo = 'prueba', "
        "reportado_por = current_user WHERE id = %s",
        (api,),
    )
    cur.execute(
        "SELECT proceso, estado, filas_leidas, filas FROM control.bitacora_etl WHERE id = %s",
        (api,),
    )
    fila = cur.fetchone()
    r.comprobar(
        "9. la aplicacion puede registrar con proceso = 'api'",
        fila == ("api", "exitosa", 120, 118),
        f"quedo {fila}",
    )

    # ------------------------------------------------------------------ 11 y 12
    cur.execute(
        "SELECT count(*) FROM control.fallo WHERE corrida_id = %s",
        (enlazada,),
    )
    r.comprobar(
        "11. las filas rechazadas se cuentan por corrida_id",
        cur.fetchone()[0] == 1,
    )

    cur.execute("SELECT count(*) FROM control.fallo WHERE corrida_id IS NULL")
    sin_atribuir = cur.fetchone()[0]
    r.comprobar(
        "12. las filas SIN corrida atribuida se cuentan aparte",
        sin_atribuir >= 1,
        f"{sin_atribuir} sin atribuir. H12.4 tiene que contarlas ANTES de agrupar: "
        "si no, agrupa sobre un subconjunto que nadie delimito",
    )

    cur.execute("ROLLBACK TO SAVEPOINT prueba")


def main() -> int:
    p = argparse.ArgumentParser(description="Criterios de aceptacion de H12.1.")
    p.add_argument("--dsn")
    args = p.parse_args()

    try:
        import psycopg  # noqa: F401
    except ImportError:
        # EL PRIMER SOSPECHOSO ES EL ENTORNO, NO EL PAQUETE.
        #
        # La version anterior de este mensaje decia «Falta psycopg: pip install
        # -r requirements.txt» y nada mas. El 2026-09-04 eso llevo a instalar el
        # requirements entero en el Python GLOBAL de la maquina, que degrado
        # numpy, pandas, scipy, scikit-learn, pytest y ruff a las versiones de
        # este proyecto y dejo otro proyecto sin poder arrancar.
        #
        # El paquete no faltaba: faltaba el entorno. Un mensaje de error que
        # nombra la cura equivocada es peor que uno que no dice nada, porque el
        # que lo lee le hace caso.
        print(
            f"\nEste Python no tiene psycopg:\n  {sys.executable}\n\n"
            "Antes de instalar nada, comproba que el entorno virtual este activo.\n"
            "La ruta de arriba tiene que terminar en '.venv\\Scripts\\python.exe':\n\n"
            "    .\\.venv\\Scripts\\Activate.ps1\n\n"
            "Solo si YA estas dentro del venv y aun asi falta:\n\n"
            "    pip install -r requirements.txt\n\n"
            "Correr ese pip fuera del venv instala el proyecto entero en el\n"
            "Python del sistema y degrada lo que otros proyectos usen.\n"
        )
        return 1

    try:
        if args.dsn:
            import psycopg

            conexion = psycopg.connect(args.dsn)
        else:
            from basedatos.conexion import conectar

            conexion = conectar()
    except Exception as error:  # noqa: BLE001
        print(f"\nLa base no responde: {error}\n")
        return 1

    r = Resultado()
    try:
        informar_estado(conexion, r)
        verificar(conexion, r)
    finally:
        conexion.rollback()
        conexion.close()

    print(f"\n{r.hechos - len(r.fallos)} de {r.hechos} comprobaciones")

    if r.hallazgos:
        print("\nHALLAZGOS. Van a la evidencia ANTES de corregirse:\n")
        for h in r.hallazgos:
            print(f"  - {h}\n")

    if r.fallos:
        print("NO se cumplen:")
        for f in r.fallos:
            print(f"  - {f}")
        print()
        return 1

    print(
        "\nLos once criterios comprobables se cumplen. Falta el 10, que no se\n"
        "puede comprobar desde aca y es el que mas importa:\n\n"
        "    python -m backend.etl.ingestar --evento lluvia_intensa\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
