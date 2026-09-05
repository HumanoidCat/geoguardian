"""
Verificador de los criterios de aceptacion de H1.10. Dueno: Cesar. Issue #42.

QUE HACE

Respalda de verdad, restaura de verdad en `geoguardian_restaurada`, y despues
comprueba ocho criterios. No simula ninguno de los dos pasos.

EL CRITERIO CENTRAL ES CA-2, Y SE APOYA EN H1.7

`generar_manifiesto.py` describe el contenido con sumas SHA-256 por tabla y **sin
marca de tiempo**, de modo que dos corridas sobre los mismos datos dan bytes
identicos. Eso se decidio en D-29 por otra razon y resulta ser justo lo que hace
falta aca: se genera el manifiesto de la base original y el de la restaurada con
los mismos argumentos, y **se comparan byte a byte**.

Que `pg_restore` termine en cero no demuestra nada: puede omitir objetos y salir
bien. Que los dos manifiestos coincidan si demuestra que el contenido es el
mismo, y cuando no coinciden, el diff dice **que tabla** difiere.

CA-3 Y CA-4 SON DOS COSAS DISTINTAS

CA-3 comprueba que el disparador de auditoria **existe** en el destino. CA-4
comprueba que **dispara**. Un disparador restaurado pero deshabilitado aparece en
`pg_trigger` igual que uno activo. Es la misma distincion de H6.2: contar que la
transaccion se abrio no demuestra que la escritura ocurrio dentro de ella.

LA BASE DE TRABAJO NO SE TOCA, Y NUNCA SE USA --forzar

Todo lo que escribe ocurre en `geoguardian_restaurada`, que se recrea al empezar.
CA-5 lo comprueba contando filas en la de trabajo antes y despues. **En ninguna
parte se usa `docker compose down -v`**, por I-05.

USO

    python -m basedatos.verificar_h1_10

CODIGOS DE SALIDA

    0  los ocho criterios cumplen
    1  algun criterio no cumple
    2  no se pudo respaldar o restaurar, o falta Docker
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from basedatos.respaldar import (  # noqa: E402
    DIRECTORIO_RESPALDOS,
    ErrorRespaldo,
    configuracion,
    en_contenedor,
    respaldar,
)
from basedatos.restaurar import DESTINO_POR_OMISION, ErrorRestauracion, restaurar, sql  # noqa: E402

RUTA_EVIDENCIA = RAIZ / "docs" / "evidencias" / "bases-de-datos" / "H1.10-respaldo-restauracion.md"

ESQUEMAS = ("geo", "crudo", "analitico", "control")

# Se arma explicitamente y no con repr() de la tupla: con un solo esquema, repr
# daria ('geo',) y esa coma final no es SQL valido. Hoy funcionaria por
# casualidad, que es la peor razon por la que algo funciona.
ESQUEMAS_SQL = "(" + ", ".join(f"'{e}'" for e in ESQUEMAS) + ")"

# Un distrito real cualquiera, para CA-4. Se toma de la base restaurada, no se
# escribe a mano: si los codigos del SNIT cambian -y ya cambiaron una vez, I-04-
# el verificador sigue funcionando.
SQL_UN_DISTRITO = "SELECT codigo FROM geo.distrito ORDER BY codigo LIMIT 1"


def titulo(texto: str) -> None:
    print(f"\n{texto}")
    print("-" * len(texto))


def manifiesto(base: str) -> bytes:
    """
    Genera el manifiesto de `base` y lo devuelve, sin tocar ningun archivo.

    `--salida -` escribe a la salida estandar. La version y la fecha se pasan
    iguales en las dos llamadas a proposito: asi cualquier diferencia entre los
    dos manifiestos viene del contenido y no de los argumentos.
    """
    entorno = dict(os.environ, POSTGRES_DB=base)
    resultado = subprocess.run(
        [
            sys.executable,
            "-m",
            "basedatos.generar_manifiesto",
            "--version",
            "comparacion",
            "--fecha",
            "2026-01-01",
            "--salida",
            "-",
        ],
        cwd=RAIZ,
        env=entorno,
        capture_output=True,
        check=False,
    )
    if resultado.returncode != 0:
        raise ErrorRestauracion(
            f"No se pudo generar el manifiesto de `{base}`:\n"
            f"{resultado.stderr.decode('utf-8', 'replace').strip()}"
        )
    return resultado.stdout


def contar_filas(base: str, cfg: dict[str, str]) -> dict[str, int]:
    consulta = " UNION ALL ".join(
        f"SELECT '{t}', count(*) FROM {t}"
        for t in ("geo.distrito", "crudo.medicion_diaria", "crudo.foco_calor", "analitico.riesgo")
    )
    filas = {}
    for linea in sql(consulta, base, cfg).splitlines():
        tabla, cuenta = linea.split("|")
        filas[tabla] = int(cuenta)
    return filas


# --------------------------------------------------------------------------- #
# Criterios
# --------------------------------------------------------------------------- #


def ca1_el_volcado_es_legible(archivo: Path, cfg: dict[str, str]) -> bool:
    titulo("CA-1 · El volcado existe, es legible y trae los cuatro esquemas")

    resultado = en_contenedor(
        ["pg_restore", "--list"], cfg["contrasena"], entrada=archivo.read_bytes()
    )
    if resultado.returncode != 0:
        print(
            f"  FALLA   pg_restore --list no pudo leer el archivo:\n{resultado.stderr.decode('utf-8','replace')}"
        )
        return False

    listado = resultado.stdout.decode("utf-8", "replace")
    ok = True
    for esquema in ESQUEMAS:
        cuantas = sum(1 for ln in listado.splitlines() if f" {esquema} " in ln)
        if cuantas:
            print(f"  OK      {esquema:10} {cuantas:4} entradas en el volcado")
        else:
            print(f"  FALLA   {esquema}: ninguna entrada")
            ok = False

    print(f"  Tamano del archivo: {archivo.stat().st_size:,} bytes")
    return ok


def tablas_y_filas(base: str, cfg: dict[str, str]) -> dict[str, int]:
    """Cuenta las filas de TODAS las tablas de los cuatro esquemas."""
    nombres = sql(
        "SELECT table_schema || '.' || table_name FROM information_schema.tables "
        f"WHERE table_schema IN {ESQUEMAS_SQL} AND table_type = 'BASE TABLE' ORDER BY 1",
        base,
        cfg,
    ).splitlines()
    if not nombres:
        return {}
    consulta = " UNION ALL ".join(f"SELECT '{n}', count(*) FROM {n}" for n in nombres)
    filas = {}
    for linea in sql(consulta, base, cfg).splitlines():
        tabla, cuenta = linea.rsplit("|", 1)
        filas[tabla] = int(cuenta)
    return filas


def ca2_el_contenido_es_identico(cfg: dict[str, str]) -> bool:
    titulo("CA-2 · El contenido restaurado coincide con el original")

    original = manifiesto(cfg["base"])
    restaurado = manifiesto(DESTINO_POR_OMISION)

    if original != restaurado:
        print(f"  FALLA   los manifiestos difieren: {len(original)} bytes contra {len(restaurado)}")
    else:
        print(f"  OK      manifiestos identicos, {len(original):,} bytes cada uno")
        print("          sumas SHA-256 iguales en geo.distrito, crudo.medicion_diaria y")
        print("          crudo.foco_calor, que son las TRES tablas que el manifiesto cubre")

        # SEGUNDA PARTE, Y EXISTE POR UNA SOBREDECLARACION PROPIA
        #
        # El manifiesto de H1.7 describe tres tablas. La restauracion trae once.
        # Apoyar «el contenido restaurado es identico» solo en el manifiesto
        # dejaba fuera analitico y control -incluida `control.migracion`, que
        # declara que version de esquema es esa base-: se habrian restaurado
        # vacias y el criterio seguiria en verde.
        #
        # Un conteo no es tan fuerte como una suma SHA-256: detecta la ausencia y
        # el faltante, no un valor cambiado. Pero cubre las ocho tablas que el
        # manifiesto no mira, y decirlo asi es mas honesto que el titulo anterior.
        a = tablas_y_filas(cfg["base"], cfg)
        b = tablas_y_filas(DESTINO_POR_OMISION, cfg)
        if a == b:
            print(f"  OK      las {len(a)} tablas de los cuatro esquemas, mismo conteo de filas")
            for tabla in sorted(a):
                print(f"            {tabla:34} {a[tabla]:>7,}")
            return True
        print("  FALLA   el conteo de filas no coincide en todas las tablas:")
        for tabla in sorted(set(a) | set(b)):
            if a.get(tabla) != b.get(tabla):
                print(
                    f"            {tabla}: origen {a.get(tabla, 'ausente')}, destino {b.get(tabla, 'ausente')}"
                )
        return False

    print(f"  FALLA   los manifiestos difieren: {len(original)} bytes contra {len(restaurado)}")
    a = original.decode("utf-8", "replace").splitlines()
    b = restaurado.decode("utf-8", "replace").splitlines()
    mostradas = 0
    for i, (x, y) in enumerate(zip(a, b, strict=False)):
        if x != y and mostradas < 8:
            print(f"          linea {i + 1}:")
            print(f"            original:   {x.strip()[:100]}")
            print(f"            restaurado: {y.strip()[:100]}")
            mostradas += 1
    if len(a) != len(b):
        print(f"          y tienen distinto numero de lineas: {len(a)} contra {len(b)}")
    return False


def ca3_vuelven_los_objetos(cfg: dict[str, str]) -> bool:
    titulo("CA-3 · Vuelven funciones, disparadores y restricciones, no solo filas")

    # Se comparan los NOMBRES, no la cantidad. «3 funciones en las dos bases»
    # seria verde aunque fueran tres funciones distintas: dos conjuntos distintos
    # del mismo tamano es la forma mas facil de dar por bueno algo que no se
    # comprobo.
    consultas = {
        "funciones": "SELECT n.nspname || '.' || p.proname FROM pg_proc p "
        "JOIN pg_namespace n ON n.oid = p.pronamespace "
        f"WHERE n.nspname IN {ESQUEMAS_SQL} ORDER BY 1",
        "disparadores": "SELECT tgname FROM pg_trigger WHERE NOT tgisinternal ORDER BY 1",
        "restricciones": "SELECT c.conname FROM pg_constraint c "
        "JOIN pg_namespace n ON n.oid = c.connamespace "
        f"WHERE n.nspname IN {ESQUEMAS_SQL} ORDER BY 1",
    }

    ok = True
    for nombre, consulta in consultas.items():
        lista_origen = sql(consulta, cfg["base"], cfg).splitlines()
        lista_destino = sql(consulta, DESTINO_POR_OMISION, cfg).splitlines()
        origen, destino = len(lista_origen), len(lista_destino)

        if lista_origen == lista_destino and origen > 0:
            print(f"  OK      {nombre:14} {origen} en las dos bases, y son los mismos")
            if nombre != "restricciones":
                for x in lista_origen:
                    print(f"            {x}")
        elif origen == destino and origen > 0:
            faltan = sorted(set(lista_origen) - set(lista_destino))
            sobran = sorted(set(lista_destino) - set(lista_origen))
            print(f"  FALLA   {nombre}: {origen} en las dos, pero NO son los mismos")
            print(f"          falta en el destino: {faltan}")
            print(f"          sobra en el destino: {sobran}")
            ok = False
        elif origen == destino == 0:
            print(f"  FALLA   {nombre}: cero en las dos bases")
            print("          Eso no dice que la restauracion este mal: dice que la BASE DE")
            print("          TRABAJO no tiene esos objetos. Probablemente le faltan")
            print("          migraciones. Corre `python -m basedatos.aplicar_migraciones`")
            print("          y repeti. Un respaldo fiel de una base atrasada sigue siendo")
            print("          fiel, y no demuestra lo que este criterio quiere demostrar.")
            ok = False
        else:
            print(f"  FALLA   {nombre}: {origen} en el origen, {destino} en el destino")
            ok = False
    return ok


def ca4_el_disparador_dispara(cfg: dict[str, str]) -> bool:
    titulo("CA-4 · El disparador de auditoria funciona en la base restaurada")

    distrito = sql(SQL_UN_DISTRITO, DESTINO_POR_OMISION, cfg)
    if not distrito:
        print("  FALLA   la base restaurada no tiene ningun distrito")
        return False

    # Se escribe en la base restaurada, que es desechable. Nunca en la de trabajo.
    sql(
        "INSERT INTO analitico.riesgo (codigo_distrito, fecha, tipo_evento, nivel) "
        f"VALUES ('{distrito}', DATE '2026-01-01', 'sequia', 'bajo') "
        "ON CONFLICT DO NOTHING",
        DESTINO_POR_OMISION,
        cfg,
    )
    antes = int(sql("SELECT count(*) FROM analitico.riesgo_auditoria", DESTINO_POR_OMISION, cfg))

    sql(
        "UPDATE analitico.riesgo SET nivel = 'alto' "
        f"WHERE codigo_distrito = '{distrito}' AND fecha = DATE '2026-01-01' AND tipo_evento = 'sequia'",
        DESTINO_POR_OMISION,
        cfg,
    )
    despues = int(sql("SELECT count(*) FROM analitico.riesgo_auditoria", DESTINO_POR_OMISION, cfg))

    if despues == antes + 1:
        registro = sql(
            "SELECT operacion, nivel_anterior FROM analitico.riesgo_auditoria "
            "ORDER BY id DESC LIMIT 1",
            DESTINO_POR_OMISION,
            cfg,
        )
        print(f"  OK      un UPDATE dejo un registro: {registro}")
        print("          el disparador no solo existe: dispara")
        return True

    print(
        f"  FALLA   registros de auditoria: {antes} antes, {despues} despues. Se esperaba uno mas"
    )
    print("          el disparador esta restaurado pero no esta actuando")
    return False


def ca5_la_base_de_trabajo_no_se_toco(antes: dict[str, int], cfg: dict[str, str]) -> bool:
    titulo("CA-5 · La base de trabajo quedo como estaba")

    despues = contar_filas(cfg["base"], cfg)
    if antes == despues:
        for tabla, cuenta in antes.items():
            print(f"  OK      {tabla:24} {cuenta:>7,} filas, sin cambio")
        return True

    for tabla in antes:
        if antes[tabla] != despues[tabla]:
            print(f"  FALLA   {tabla}: {antes[tabla]} antes, {despues[tabla]} despues")
    print("          LA BASE DE TRABAJO QUEDO TOCADA. Revisar antes de seguir")
    return False


def ca6_el_volcado_no_entra_al_repositorio(archivo: Path) -> bool:
    titulo("CA-6 · El volcado no puede entrar al repositorio")

    resultado = subprocess.run(
        ["git", "check-ignore", "-v", str(archivo.relative_to(RAIZ))],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        check=False,
    )
    if resultado.returncode == 0:
        print(f"  OK      {archivo.relative_to(RAIZ)}")
        print(f"          ignorado por: {resultado.stdout.strip()}")

        # HALLAZGO, Y NO UN FALLO DE ESTE CRITERIO
        #
        # El criterio pide que EL VOLCADO no entre al repositorio, y no entra.
        # Pero no entra por una regla de EXTENSION -*.dump-, que es el antipatron
        # que este mismo .gitignore condena cuatro lineas mas arriba al arreglar
        # infra/docker/respaldos/: «SE IGNORA LA CARPETA, NO LAS EXTENSIONES, Y
        # ESO ES LO QUE FALLABA».
        #
        # basedatos/respaldos/ no figura en .gitignore. Se comprueba con un nombre
        # que no termina en .dump, para que el hueco se vea en vez de suponerse.
        senuelo = DIRECTORIO_RESPALDOS.relative_to(RAIZ) / "no-existe-solo-para-comprobar.sql"
        prueba = subprocess.run(
            ["git", "check-ignore", str(senuelo)],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            check=False,
        )
        if prueba.returncode != 0:
            print()
            print("  AVISO   la carpeta no esta ignorada: solo lo esta la extension.")
            print(f"          `{senuelo}` entraria al repositorio.")
            print("          Es el antipatron que .gitignore condena al arreglar")
            print("          infra/docker/respaldos/. Se pide en el PR:")
            print("              basedatos/respaldos/*")
            print("              !basedatos/respaldos/.gitkeep")
        return True

    print(f"  FALLA   {archivo.relative_to(RAIZ)} NO esta ignorado")
    print("          un git add . se lo lleva al historial, y sacarlo despues")
    print("          obliga a reescribir el historial")
    return False


def ca7_el_procedimiento_esta_escrito() -> bool:
    titulo("CA-7 · El procedimiento esta escrito y se puede seguir")

    if not RUTA_EVIDENCIA.exists():
        print(f"  FALLA   no existe {RUTA_EVIDENCIA.relative_to(RAIZ)}")
        return False

    texto = RUTA_EVIDENCIA.read_text(encoding="utf-8")
    exigidos = [
        ("el comando de respaldo", "basedatos.respaldar"),
        ("el comando de restauracion", "basedatos.restaurar"),
        ("el paso de roles", "003_seguridad_roles"),
        ("que el volcado trae los esquemas", "SCHEMA"),
        ("la cadencia declarada", "cada"),
    ]
    ok = True
    print(f"  {RUTA_EVIDENCIA.relative_to(RAIZ)}: {len(texto.splitlines())} lineas")
    for descripcion, aguja in exigidos:
        if aguja in texto:
            print(f"  OK      nombra {descripcion}")
        else:
            print(f"  FALLA   no nombra {descripcion} ({aguja})")
            ok = False
    return ok


def ca8_los_roles_no_viajan(archivo: Path, cfg: dict[str, str]) -> bool:
    titulo("CA-8 · Los roles no viajan en el volcado, y eso esta declarado")

    resultado = en_contenedor(
        ["pg_restore", "--list"], cfg["contrasena"], entrada=archivo.read_bytes()
    )
    listado = resultado.stdout.decode("utf-8", "replace")

    ok = True
    if "CREATE ROLE" in listado.upper():
        print("  FALLA   el volcado contiene definiciones de rol")
        print("          eso significa contrasenas cifradas dentro del archivo")
        ok = False
    else:
        print("  OK      el volcado no contiene ninguna definicion de rol")

    if RUTA_EVIDENCIA.exists() and "003_seguridad_roles" in RUTA_EVIDENCIA.read_text(
        encoding="utf-8"
    ):
        print("  OK      el procedimiento declara 003_seguridad_roles.sql como paso previo")
    else:
        print("  FALLA   el procedimiento no declara como se recuperan los roles")
        ok = False

    return ok


# --------------------------------------------------------------------------- #


def main() -> int:
    print("Verificacion de H1.10 · respaldo y restauracion probada")
    print("=" * 70)

    try:
        cfg = configuracion()
        print(f"Base de trabajo: {cfg['base']}   ·   destino de prueba: {DESTINO_POR_OMISION}\n")

        filas_antes = contar_filas(cfg["base"], cfg)

        print("Paso 1 de 2 · respaldo")
        archivo = respaldar(etiqueta="verificacion")

        print("\nPaso 2 de 2 · restauracion")
        restaurar(archivo, DESTINO_POR_OMISION)
    except (ErrorRespaldo, ErrorRestauracion) as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        return 2

    # Cada criterio corre aislado. Si uno levanta una excepcion -una tabla que no
    # existe, la base caida a mitad-, **se registra como NO CUMPLE y los demas
    # siguen corriendo**.
    #
    # La primera version no hacia esto y CA-4 reventaba con un traceback que se
    # comia el veredicto de CA-5 a CA-8, que ya se podian evaluar. Es el mismo
    # defecto que reporte en `verificar_diagramas.py` el 2026-09-02: un control
    # que se cae se ve distinto de uno que falla, y quien lo mira no sabe si el
    # criterio no se cumple o si su maquina esta mal.
    criterios = [
        ("CA-1", lambda: ca1_el_volcado_es_legible(archivo, cfg)),
        ("CA-2", lambda: ca2_el_contenido_es_identico(cfg)),
        ("CA-3", lambda: ca3_vuelven_los_objetos(cfg)),
        ("CA-4", lambda: ca4_el_disparador_dispara(cfg)),
        ("CA-5", lambda: ca5_la_base_de_trabajo_no_se_toco(filas_antes, cfg)),
        ("CA-6", lambda: ca6_el_volcado_no_entra_al_repositorio(archivo)),
        ("CA-7", ca7_el_procedimiento_esta_escrito),
        ("CA-8", lambda: ca8_los_roles_no_viajan(archivo, cfg)),
    ]

    resultados: dict[str, bool] = {}
    for nombre, comprobacion in criterios:
        try:
            resultados[nombre] = comprobacion()
        except (ErrorRespaldo, ErrorRestauracion) as error:
            print(f"  FALLA   {nombre} no se pudo evaluar:")
            for linea in str(error).splitlines():
                print(f"          {linea}")
            resultados[nombre] = False

    titulo("Resumen")
    for criterio in sorted(resultados):
        print(f"  {criterio}  {'CUMPLE' if resultados[criterio] else 'NO CUMPLE'}")

    print()
    if all(resultados.values()):
        print("Los ocho criterios de H1.10 se cumplen.")
        print(f"La base `{DESTINO_POR_OMISION}` queda creada para poder inspeccionarla.")
        return 0

    print("Hay criterios sin cumplir.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
