"""
Verificador de H11.6: publicar la API y la base con un solo origen.

Criterios en `docs/evidencias/sistemas-operativos/H11.6-criterios-aceptacion.md`.

QUE SE COMPRUEBA AQUI Y QUE NO

Este guion **no necesita el despliegue levantado, ni red, ni base**. Comprueba lo
que se puede comprobar sin nada de eso: que las piezas que sostienen el despliegue
sigan diciendo lo que la historia supone que dicen.

Los criterios que **si** necesitan el sitio publicado -CA-1, el dominio unico;
CA-5, `/salud` respondiendo `real`; CA-9, el costo- se comprueban contra el
despliegue y van en la evidencia con su salida. Fingir aqui que se comprobaron
seria justo lo contrario de lo que hace un verificador.

    python -m infra.verificar_h116
"""

from __future__ import annotations

import fnmatch
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from infra import cargar_datos, preparar_base  # noqa: E402

ARRANQUE = RAIZ / "infra" / "docker" / "init-db" / "01-extensiones.sql"
PLANTILLA_NGINX = RAIZ / "frontend" / "nginx.conf.template"
NORMALIZADOR = RAIZ / "frontend" / "docker-entrypoint.d" / "05-destino-api.envsh"
CLIENTE = RAIZ / "frontend" / "src" / "datos" / "cliente.js"
APLICACION = RAIZ / "backend" / "api" / "aplicacion.py"
DEPENDENCIAS = RAIZ / "backend" / "api" / "dependencias.py"
DDL = RAIZ / "basedatos" / "ddl"
CONEXION = RAIZ / "basedatos" / "conexion.py"
RUNBOOK = RAIZ / "docs" / "19-runbook-railway.md"

fallos: list[str] = []
hechos = 0


def exigir(condicion: bool, descripcion: str, detalle: str = "") -> None:
    global hechos
    hechos += 1
    print(
        f"  {'ok   ' if condicion else 'FALLA'} {descripcion}{('  ' + detalle) if detalle else ''}"
    )
    if not condicion:
        fallos.append(descripcion)


def leer(archivo: Path) -> str:
    return archivo.read_text(encoding="utf-8") if archivo.exists() else ""


# --------------------------------------------------------------------------- #


def ca2_un_solo_origen() -> None:
    print("\nCA-2 · Un solo origen: el navegador nunca habla con otro dominio")

    cliente = leer(CLIENTE)
    exigir(
        "VITE_API_URL ?? '/api'" in cliente,
        "el visor usa una ruta relativa por omision, no un origen absoluto (D-23)",
    )
    exigir(
        not re.search(r"const RUTA_API\s*=\s*['\"]https?://", cliente),
        "y no hay ningun origen absoluto escrito en cliente.js",
    )

    plantilla = leer(PLANTILLA_NGINX)
    exigir("location /api/" in plantilla, "el visor reenvia /api/ desde su propio nginx")
    exigir(
        "set $destino_api ${DESTINO_API};" in plantilla,
        "el destino es una VARIABLE: nginx difiere el DNS y levanta sin la API",
    )
    exigir(
        "proxy_pass $destino_api;" in plantilla,
        "y proxy_pass usa esa variable, no un nombre escrito literal",
    )
    exigir(
        "rewrite ^/api/(.*)$ /$1 break;" in plantilla,
        "el rewrite quita el prefijo: con variable, nginx ya no lo quita solo",
    )

    # El normalizador de la barra final. Es un control, y por eso se comprueba
    # que exista Y que tenga el sufijo correcto: en un `.sh` el entrypoint lo
    # ejecuta en un subproceso y el cambio no sobrevive. Lo dice su cabecera.
    normalizador = leer(NORMALIZADOR)
    exigir(
        NORMALIZADOR.suffix == ".envsh",
        "el normalizador de DESTINO_API es .envsh, no .sh: si no, el cambio no sobrevive",
        NORMALIZADOR.name,
    )
    exigir(
        'DESTINO_API="${DESTINO_API%/}"' in normalizador,
        "y recorta la barra final, que si no produce // en cada peticion",
    )

    # La comprobacion invertida: que NO haya CORS.
    #
    # No es una preferencia de estilo. Si alguien agrega CORS, el visor deja de
    # necesitar el mismo origen y la decision de D-23 se vuelve letra muerta sin
    # que nada falle. Que aparezca aqui obliga a que sea una decision escrita.
    aplicacion = leer(APLICACION)
    exigir(
        "CORSMiddleware" not in aplicacion and "allow_origins" not in aplicacion,
        "la API NO tiene CORS: el despliegue va detras de un solo origen (D-23)",
    )


def ca3_el_esquema_sale_de_las_migraciones() -> None:
    print("\nCA-3 · El esquema se aplica, no se improvisa")

    fuente = leer(RAIZ / "infra" / "preparar_base.py")
    exigir(
        "ARRANQUE.read_text" in fuente,
        "preparar_base LEE el archivo de arranque; no tiene una copia de sus sentencias",
    )
    exigir(
        'cursor.execute("CREATE' not in fuente and "cursor.execute('CREATE" not in fuente,
        "y no ejecuta ningun CREATE escrito aca: todo sale del archivo",
    )

    arranque = leer(ARRANQUE)
    exigir(bool(arranque), "el archivo de arranque existe", str(ARRANQUE.relative_to(RAIZ)))
    exigir(
        "$$" not in arranque,
        "el arranque no tiene bloques $$: el separador de sentencias no los entiende",
    )
    for esquema in preparar_base.ESQUEMAS:
        exigir(
            f"CREATE SCHEMA IF NOT EXISTS {esquema}" in arranque,
            f"el arranque crea el esquema {esquema}",
        )
    for extension in preparar_base.EXTENSIONES_OBLIGATORIAS:
        exigir(
            f"CREATE EXTENSION IF NOT EXISTS {extension}" in arranque,
            f"el arranque crea la extension obligatoria {extension}",
        )

    # El separador, probado sobre el archivo real y sobre un caso torcido.
    sentencias = preparar_base.sentencias_del_archivo(arranque)
    exigir(
        all(not s.startswith("--") for s in sentencias),
        "el separador no deja comentarios pegados a las sentencias",
    )
    torcido = "COMMENT ON SCHEMA geo IS 'con ; adentro'; CREATE SCHEMA x;"
    exigir(
        len(preparar_base.sentencias_del_archivo(torcido)) == 2,
        "un ; dentro de un texto entrecomillado no parte la sentencia",
        str(preparar_base.sentencias_del_archivo(torcido)),
    )

    # La exigencia del nombre de la base sale del DDL, no de una constante.
    exigencias = preparar_base.bases_que_exigen_las_migraciones()
    exigir(
        exigencias == {"geoguardian": exigencias.get("geoguardian", "")}
        and "geoguardian" in exigencias,
        "las migraciones exigen exactamente una base, y es 'geoguardian'",
        str(exigencias),
    )
    exigir(
        any("003" in donde for donde in exigencias.values()),
        "y la exigencia sale de la migracion 003, leida del DDL",
        str(exigencias),
    )


def ca4_la_carga_no_miente() -> None:
    print("\nCA-4 · La carga se cuenta, y no pisa el registro del destino")

    exigir(
        "control.migracion" in cargar_datos.NO_SE_COPIAN,
        "control.migracion NO se copia: es el registro de lo que se aplico en el destino",
    )
    fuente = leer(RAIZ / "infra" / "cargar_datos.py")
    exigir(
        "registro_antes != registro_del_destino(destino)" in fuente,
        "y al terminar se comprueba que ese registro quedo intacto",
    )
    exigir(
        "if diferencias:" in fuente and "return 1" in fuente,
        "si una tabla no coincide, la carga sale con error en vez de decir que si",
    )
    # La sentencia, no la palabra: el docstring de `vaciar` tambien dice
    # "RESTART IDENTITY", asi que buscar el texto suelto daba verde con el
    # codigo saboteado. Lo detecto el sabotaje numero 10.
    exigir(
        "TRUNCATE {tabla} RESTART IDENTITY CASCADE" in fuente,
        "vaciar reinicia las identidades: si no, la secuencia del destino se adelanta",
    )
    exigir(
        "def igualar_secuencias" in fuente,
        "las secuencias se igualan; si no, la primera insercion del ETL choca",
    )

    # El orden de carga, probado sobre un grafo armado a mano.
    grafo = {"a": set(), "b": {"a"}, "c": {"b"}, "d": {"a"}}
    orden = cargar_datos.orden_de_carga(grafo)
    exigir(
        orden.index("a") < orden.index("b") < orden.index("c")
        and orden.index("a") < orden.index("d"),
        "el orden de carga pone a los padres antes que a los hijos",
        str(orden),
    )
    exigir(
        cargar_datos.orden_de_carga(grafo) == orden,
        "y es estable: dos llamadas dan el mismo orden",
    )
    ciclo = {"a": {"b"}, "b": {"a"}}
    try:
        cargar_datos.orden_de_carga(ciclo)
    except cargar_datos.ErrorCarga:
        exigir(True, "un ciclo de llaves foraneas se detiene en vez de inventar un orden")
    else:
        exigir(False, "un ciclo de llaves foraneas se detiene en vez de inventar un orden")

    exigir(
        "def comprobar_triggers_de_historial" in fuente and "INSERT" in fuente,
        "se comprueba que ningun trigger de historial dispare con INSERT",
    )


def ca5_el_modo_no_puede_mentir() -> None:
    print("\nCA-5 · El modo lo decide quien respondio, no una variable")

    fuente = leer(DEPENDENCIAS)
    exigir(
        "isinstance(repositorio, RepositorioSimulado)" in fuente,
        "modo_de pregunta por la implementacion, no por GEOGUARDIAN_REPOSITORIO",
    )
    exigir(
        "VARIABLE_REPOSITORIO" in fuente and 'os.getenv(VARIABLE_REPOSITORIO, "")' in fuente,
        "la variable elige QUE repositorio se construye, y ahi termina su papel",
    )

    from backend.api.dependencias import modo_de
    from contratos.enums import ModoOperacion
    from contratos.simulados.datos import RepositorioSimulado

    exigir(
        modo_de(RepositorioSimulado()) is ModoOperacion.SIMULADO,
        "con el simulado responde 'simulado', se configure lo que se configure",
    )


def ca8_no_hay_secretos() -> None:
    print("\nCA-8 · Ningun secreto entra al repositorio")

    # QUE BUSCA ESTE CONTROL, Y QUE NO
    #
    # La primera version buscaba cualquier `CLAVE = valor` con pinta de
    # contrasena, y marco cinco lineas que **no eran secretos**: las
    # interpolaciones `${POSTGRES_PASSWORD:?...}` de docker-compose y los
    # marcadores de posicion de `docs/ARRANQUE.md`. Un control que grita por
    # cosas correctas es un control que se aprende a ignorar, y entonces no
    # protege de nada.
    #
    # Lo que si se puede juzgar por el texto, sin adivinar, es una **cadena de
    # conexion con credencial adentro**: `postgres://usuario:clave@host`. Esa
    # forma no tiene uso legitimo en el repositorio, y es exactamente como se
    # filtra la de un proveedor de nube: alguien copia la URL que le dio el
    # panel y la pega en un manifiesto o en una nota.
    #
    # Las contrasenas literales en SQL ya las vigila **CA-8 de H1.8**
    # (`basedatos/seguridad/verificar_h18.py`), con el patron `PASSWORD '...'`.
    # No se repite aqui: dos controles del mismo hecho se desincronizan.
    CARPETAS = ("backend", "contratos", "basedatos", "infra", "docs", "frontend/src", ".github")
    EXTENSIONES = {".py", ".yml", ".yaml", ".sql", ".md", ".sh", ".envsh", ".js", ".jsx"}
    PODADAS = {".git", "node_modules", ".venv", "__pycache__", "dist"}

    with_credencial = re.compile(
        r"postgres(?:ql)?://[^\s/:@$]+:[^\s/@$]+@",
        re.IGNORECASE,
    )

    def archivos() -> list[Path]:
        salida: list[Path] = []
        for nombre in CARPETAS:
            carpeta = RAIZ / nombre
            if not carpeta.is_dir():
                continue
            for actual, subcarpetas, nombres in os.walk(carpeta):
                subcarpetas[:] = [s for s in subcarpetas if s not in PODADAS]
                salida.extend(Path(actual) / n for n in nombres if Path(n).suffix in EXTENSIONES)
        salida.extend(a for a in RAIZ.glob("*") if a.is_file() and a.suffix in EXTENSIONES)
        return sorted(salida)

    # Este archivo se excluye porque **contiene el patron como ejemplo** en el
    # comentario de arriba, y si no se marcaria a si mismo en cada corrida. El
    # costo esta declarado: una credencial pegada dentro de este verificador no
    # se detectaria. Se acepta porque este archivo no recibe configuracion de
    # nadie, y porque un control que siempre falla se apaga y deja de proteger.
    propio = Path(__file__).resolve()

    revisados = 0
    encontrados: list[str] = []
    for archivo in archivos():
        if archivo.resolve() == propio:
            continue
        revisados += 1
        for numero, linea in enumerate(leer(archivo).splitlines(), 1):
            if with_credencial.search(linea):
                encontrados.append(f"{archivo.relative_to(RAIZ)}:{numero}")

    exigir(
        not encontrados,
        f"ninguna cadena de conexion con credencial en {revisados} archivos",
        " / ".join(encontrados[:5]),
    )

    # QUE PRUEBA ESTE CONTROL, Y POR QUE NO ALCANZA CON BUSCAR EL TEXTO
    #
    # La primera version preguntaba `".env" in ignorados` y respondia que si
    # mientras un `.env.railway` con contrasenas reales quedaba SIN ignorar:
    # `.env` a secas es un nombre exacto, no un prefijo. Es la incidencia I-35.
    # Un control que no puede decir que no no es un control, asi que este aplica
    # los patrones a nombres concretos e incluye el caso que tiene que quedar
    # FUERA: si alguien "simplifica" el .gitignore a `.env*`, esa comprobacion
    # falla y se entera antes de borrar el ejemplo del repositorio.
    ignorados = leer(RAIZ / ".gitignore")
    patrones = [
        linea.strip()
        for linea in ignorados.splitlines()
        if linea.strip() and not linea.lstrip().startswith("#")
    ]

    def ignorado(nombre: str) -> bool:
        decision = False
        for patron in patrones:  # el ultimo patron que coincide manda, como en git
            if fnmatch.fnmatch(nombre, patron.lstrip("!")):
                decision = not patron.startswith("!")
        return decision

    for nombre in (".env", ".env.railway", ".env.destino"):
        exigir(ignorado(nombre), f".gitignore ignora {nombre}")
    exigir(
        not ignorado(".env.example"),
        "y NO ignora .env.example, que se versiona a proposito y no lleva ningun valor",
    )
    exigir(
        not (RAIZ / ".env.railway").exists(),
        ".env.railway no esta en el arbol del repositorio",
    )


def ca6_el_reintento_no_espera_lo_que_no_va_a_cambiar() -> None:
    """
    H11.6 encontro que `conectar()` esperaba noventa segundos por
    `database "geoguardian" does not exist`, un error que el servidor ya habia
    contestado, y despues mandaba a mirar `docker compose ps` con la base en otro
    continente. La correccion vive en `basedatos/conexion.py` bajo la excepcion
    de propiedad escrita en `docs/07-propiedad-archivos.md`.

    La prueba de punta a punta -tiempos reales contra un PostgreSQL- esta en
    `infra/probar_reintento_conexion.py` y necesita base. Aca va lo que no la
    necesita: que la clasificacion acierte sobre los MENSAJES REALES, copiados de
    las corridas contra PostgreSQL 16 con psycopg 3.3.5.
    """
    print("\nCA-6 · El reintento distingue lo que va a cambiar de lo que no")

    import psycopg

    from basedatos.conexion import HOSTS_LOCALES, PERMANENTES, _base_local, _es_permanente

    # Mensajes textuales de psycopg, medidos. No inventados: cada uno salio de
    # provocar la situacion contra un servidor real.
    MEDIDOS = [
        ('FATAL:  database "no_existe" does not exist', True),
        ('FATAL:  role "fantasma" does not exist', True),
        ('FATAL:  password authentication failed for user "postgres"', True),
        ("fe_sendauth: no password supplied", True),
        ("Connection refused", False),
        (
            "failed to resolve host 'no.existe.invalido': [Errno -2] Name or service not known",
            False,
        ),
        # El que decide la forma de la regla: llega con FATAL, y aun asi se
        # reintenta, porque es exactamente lo que el reintento existe para cubrir.
        ("FATAL:  the database system is starting up", False),
        ("server closed the connection unexpectedly", False),
    ]
    errados = [
        m
        for m, permanente in MEDIDOS
        if _es_permanente(psycopg.OperationalError(f"connection failed: {m}")) is not permanente
    ]
    exigir(
        not errados,
        f"clasifica bien los {len(MEDIDOS)} mensajes medidos de psycopg",
        " / ".join(e[:40] for e in errados),
    )
    exigir(
        _es_permanente(psycopg.OperationalError("FATAL:  the database system is starting up"))
        is False,
        "y 'the database system is starting up' se REINTENTA, aunque traiga FATAL",
    )
    exigir(
        len(PERMANENTES) >= 3 and all(isinstance(m, str) for m in PERMANENTES),
        "la lista es de permanentes: lo que no esta en ella sigue reintentando",
        str(PERMANENTES),
    )

    # La pista depende de donde este la base, no de una constante.
    guardado = os.environ.get("POSTGRES_HOST_LOCAL")
    try:
        os.environ["POSTGRES_HOST_LOCAL"] = "localhost"
        local = _base_local()
        os.environ["POSTGRES_HOST_LOCAL"] = "postgis.railway.internal"
        remoto = _base_local()
    finally:
        if guardado is None:
            os.environ.pop("POSTGRES_HOST_LOCAL", None)
        else:
            os.environ["POSTGRES_HOST_LOCAL"] = guardado
    exigir(local and not remoto, "y la pista de 'docker compose' solo sale con la base local")
    exigir("db" in HOSTS_LOCALES, "el nombre del servicio de compose cuenta como local")


def ca10_el_procedimiento_esta_escrito() -> None:
    print("\nCA-10 · El procedimiento esta versionado y nombra lo que el codigo lee")

    exigir(
        RUNBOOK.exists(),
        "el runbook vive en docs/, versionado, y no en gestion/, que no lo esta",
        str(RUNBOOK.relative_to(RAIZ)),
    )
    runbook = leer(RUNBOOK)

    # Las variables NO se listan a mano aca. Se sacan del codigo que de verdad
    # las lee, asi que el dia que alguien agregue una y no la documente, este
    # control lo dice. Una lista escrita a mano envejeceria en silencio, que es
    # el defecto que CA-10 existe para evitar.
    from backend.api.dependencias import VARIABLE_REPOSITORIO

    variables = set(re.findall(r"os\.getenv\(\s*['\"]([A-Z0-9_]+)['\"]", leer(CONEXION)))
    variables.add(VARIABLE_REPOSITORIO)
    variables.add("DESTINO_API")  # la unica del visor; sale de nginx.conf.template
    faltan = sorted(v for v in variables if v not in runbook)
    exigir(
        not faltan,
        f"el runbook nombra las {len(variables)} variables de entorno que el codigo lee",
        " / ".join(faltan),
    )
    exigir(
        "DESTINO_API" in leer(PLANTILLA_NGINX),
        "y DESTINO_API es de verdad la que lee el nginx del visor",
    )

    # La secuencia que costo un directorio de datos inicializado al reves (I-36).
    exigir(
        "Wipe volume" in runbook and runbook.index("Source Image") < runbook.index("Wipe volume"),
        "el runbook pone el cambio de imagen ANTES del purgado del volumen (I-36)",
    )
    exigir(
        "3.7.0dev" in runbook and "16-3.5" in runbook,
        "y deja escrito por que la imagen va fijada y no en una etiqueta -master",
    )

    # Un runbook con un valor real adentro seria un secreto versionado. El
    # barrido de CA-8 ya recorre docs/, asi que aca solo se comprueba que siga
    # hablando por nombres: los marcadores estan y no hay ningun host de Railway.
    exigir(
        "<host del TCP proxy>" in runbook
        and not re.search(r"\.rlwy\.net|\.up\.railway\.app/", runbook),
        "el runbook nombra los valores, no los escribe",
    )


def main() -> int:
    print("Verificacion de H11.6 · sin red, sin base y sin el despliegue levantado")
    ca2_un_solo_origen()
    ca3_el_esquema_sale_de_las_migraciones()
    ca4_la_carga_no_miente()
    ca5_el_modo_no_puede_mentir()
    ca6_el_reintento_no_espera_lo_que_no_va_a_cambiar()
    ca8_no_hay_secretos()
    ca10_el_procedimiento_esta_escrito()

    print(f"\n{hechos - len(fallos)} de {hechos} comprobaciones")
    if fallos:
        print("\nNO se cumplen:")
        for fallo in fallos:
            print(f"  - {fallo}")
        print()
        return 1
    print("\nLo que no necesita el despliegue levantado se cumple.")
    print(
        "CA-1, CA-5 contra el sitio, CA-6 contra la base y CA-9 van con su salida en la evidencia.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
