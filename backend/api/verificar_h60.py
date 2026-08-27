"""
Verificador de las imagenes de Docker. Dueno: Cesar. Historia H6.0, issue #62.

Cubre CA-1 a CA-5 y dos comprobaciones extra que no estan en el issue pero que
sostienen lo que el issue afirma.

ESTE GUION CONSTRUYE Y LEVANTA DE VERDAD

No lee los Dockerfile para adivinar que harian. Corre `docker build`, arranca los
contenedores y pide `/salud` y la pagina del visor por HTTP. Si Docker no esta
disponible, **falla**: no se salta las comprobaciones ni las da por buenas. Un
verificador que pasa cuando no pudo verificar nada es peor que no tenerlo.

Tarda varios minutos la primera vez, casi todo en `npm ci`.

POR QUE VIVE AQUI Y NO EN infra/docker

Porque `infra/` es de Alejandro y la excepcion que me dieron cubre exactamente
`api.Dockerfile` y su `.dockerignore`, no un tercer archivo. Los verificadores del
proyecto viven junto al codigo que revisan y este acompana a `verificar_h61.py`.

No importa nada del proyecto —solo biblioteca estandar y `docker`— asi que corre
tanto por ruta como por modulo, sin tocar sys.path.

USO

    python backend/api/verificar_h60.py

    python backend/api/verificar_h60.py --sin-construir   # reusa las imagenes

REQUISITOS

Un archivo .env en la raiz con POSTGRES_PASSWORD, porque docker-compose.yml lo
exige. Los puertos 8000 y 5173 libres, o exportar API_PORT y VISOR_PORT.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

IMAGEN_API = "geoguardian-api"
IMAGEN_VISOR = "geoguardian-visor"

# Cuanto se espera a que un servicio responda antes de darlo por caido. La API
# espera a PostgreSQL, y PostgreSQL en un volumen nuevo corre los guiones de
# init-db, que no son instantaneos.
ESPERA_MAXIMA_S = 180
INTERVALO_S = 3


@dataclass
class Resultado:
    criterio: str
    titulo: str
    cumple: bool
    detalle: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Utilidades                                                                    #
# --------------------------------------------------------------------------- #


def correr(orden: list[str], *, mostrar: bool = True, comprobar: bool = False):
    """Corre una orden en la raiz del repositorio y devuelve el proceso."""
    if mostrar:
        print(f"    $ {' '.join(orden)}")
    return subprocess.run(
        orden,
        cwd=RAIZ,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=comprobar,
    )


def hay_docker() -> tuple[bool, str]:
    if shutil.which("docker") is None:
        return False, "no se encontro el ejecutable `docker` en el PATH"
    proceso = correr(["docker", "info", "--format", "{{.ServerVersion}}"], mostrar=False)
    if proceso.returncode != 0:
        return False, "el motor de Docker no responde: " + proceso.stderr.strip()[:200]
    return True, "motor " + proceso.stdout.strip()


def esperar_http(url: str, *, limite_s: int = ESPERA_MAXIMA_S) -> tuple[bool, str]:
    """Pide una URL hasta que responda 200 o se acabe el plazo."""
    limite = time.monotonic() + limite_s
    ultimo = "sin intentos"
    while time.monotonic() < limite:
        try:
            with urllib.request.urlopen(url, timeout=5) as respuesta:
                if respuesta.status == 200:
                    return True, respuesta.read().decode("utf-8", "replace")
                ultimo = f"HTTP {respuesta.status}"
        except urllib.error.HTTPError as error:
            ultimo = f"HTTP {error.code}"
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as error:
            ultimo = type(error).__name__ + ": " + str(error)[:120]
        time.sleep(INTERVALO_S)
    return False, f"no respondio en {limite_s} s. Ultimo intento: {ultimo}"


def dentro(imagen: str, orden: str) -> subprocess.CompletedProcess:
    """Corre una orden de shell dentro de un contenedor nuevo de la imagen."""
    return correr(
        ["docker", "run", "--rm", "--entrypoint", "sh", imagen, "-c", orden],
        mostrar=False,
    )


def puerto(nombre: str, por_omision: str) -> str:
    return os.environ.get(nombre, por_omision)


# --------------------------------------------------------------------------- #
# CA-1 · la imagen de la API es multietapa, arranca y responde /salud           #
# --------------------------------------------------------------------------- #


def ca1_api(url_api: str) -> Resultado:
    detalle: list[str] = []
    cumple = True

    ruta = RAIZ / "infra" / "docker" / "api.Dockerfile"
    etapas = [
        linea.strip()
        for linea in ruta.read_text(encoding="utf-8").splitlines()
        if linea.strip().upper().startswith("FROM ")
    ]
    detalle.append(f"  etapas declaradas: {len(etapas)}")
    for etapa in etapas:
        detalle.append(f"    {etapa}")
    if len(etapas) < 2:
        cumple = False
        detalle.append("  FALLA: el criterio pide multietapa y hay una sola instruccion FROM")

    ok, cuerpo = esperar_http(f"{url_api}/salud")
    if not ok:
        cumple = False
        detalle.append(f"  FALLA: /salud {cuerpo}")
        return Resultado("CA-1", "La imagen de la API arranca y responde /salud", cumple, detalle)

    detalle.append(f"  GET {url_api}/salud respondio 200")
    try:
        salud = json.loads(cuerpo)
    except json.JSONDecodeError:
        cumple = False
        detalle.append(f"  FALLA: /salud no devolvio JSON: {cuerpo[:120]}")
        return Resultado("CA-1", "La imagen de la API arranca y responde /salud", cumple, detalle)

    detalle.append(f"  cuerpo: {json.dumps(salud, ensure_ascii=False)}")
    # /salud declara version de contratos y modo de operacion desde H6.1. Si esos
    # campos llegan, la aplicacion no solo abrio el puerto: cargo sus esquemas.
    for campo in ("version_contratos", "modo"):
        if campo not in salud:
            cumple = False
            detalle.append(f"  FALLA: /salud no trae el campo `{campo}` que declara H6.1")

    return Resultado("CA-1", "La imagen de la API arranca y responde /salud", cumple, detalle)


# --------------------------------------------------------------------------- #
# CA-2 · la imagen del visor sirve el build estatico                            #
# --------------------------------------------------------------------------- #


def ca2_visor(url_visor: str) -> Resultado:
    detalle: list[str] = []
    cumple = True

    ok, cuerpo = esperar_http(f"{url_visor}/")
    if not ok:
        return Resultado(
            "CA-2", "La imagen del visor sirve el build estatico", False, [f"  FALLA: {cuerpo}"]
        )

    detalle.append(f"  GET {url_visor}/ respondio 200 ({len(cuerpo)} bytes)")

    if '<div id="root"' not in cuerpo and "<div id=root" not in cuerpo:
        cumple = False
        detalle.append("  FALLA: no se hallo el div raiz que monta React")

    # La marca de que esto es el build y no el codigo fuente: Vite reescribe la
    # etiqueta script a un archivo con huella en assets/. Si sirviera el fuente,
    # apuntaria a /src/main.jsx y el navegador no podria interpretarlo.
    #
    # Se busca "assets/" sin barra inicial a proposito: H11.5 puso `base: './'` en
    # vite.config.js para que el visor funcione bajo /geoguardian/ en GitHub Pages,
    # asi que las rutas salen relativas (./assets/...) y no absolutas.
    if "assets/" not in cuerpo:
        cumple = False
        detalle.append("  FALLA: el HTML no referencia assets/, asi que no parece un build de Vite")
    else:
        detalle.append("  el HTML referencia assets/, o sea que es el build y no el fuente")

    if "/src/main.jsx" in cuerpo:
        cumple = False
        detalle.append(
            "  FALLA: el HTML todavia apunta a /src/main.jsx, que es el fuente sin construir"
        )

    # Y el archivo referenciado tiene que existir de verdad. Un index.html que
    # apunta a un bundle ausente devuelve 200 y una pagina en blanco.
    referencias = re.findall(r'src="\.?/?(assets/[^"]+\.js)"', cuerpo)
    if not referencias:
        cumple = False
        detalle.append("  FALLA: no se pudo extraer el bundle referenciado por index.html")
    else:
        ok_bundle, _ = esperar_http(f"{url_visor}/{referencias[0]}", limite_s=15)
        detalle.append(f"  el bundle {referencias[0]} {'se sirve' if ok_bundle else 'NO se sirve'}")
        if not ok_bundle:
            cumple = False

    # `try_files ... /index.html` en nginx. Hoy el visor NO tiene enrutador —no hay
    # react-router en package.json— asi que ninguna subruta existe todavia y esto
    # no es un criterio, es un seguro para cuando lo tenga.
    #
    # Se anota, ademas, algo que hay que resolver antes de que ese dia llegue: con
    # `base: './'` un index.html servido en /a/b buscaria sus assets en /a/assets/,
    # que no existe. Enrutador y base relativo no conviven sin decidir uno de los
    # dos. Reportado a Alejandro y a Avril, no arreglado aqui: vite.config.js no es
    # mio mas alla de la excepcion de H6.6.
    ok_ruta, cuerpo_ruta = esperar_http(f"{url_visor}/ruta-que-no-existe", limite_s=15)
    if ok_ruta and "assets/" in cuerpo_ruta:
        detalle.append("  una ruta inexistente devuelve index.html (try_files activo)")
    else:
        detalle.append("  aviso: una ruta inexistente no devuelve index.html; hoy no rompe nada")

    return Resultado("CA-2", "La imagen del visor sirve el build estatico", cumple, detalle)


# --------------------------------------------------------------------------- #
# CA-3 · ninguna imagen contiene credenciales ni el .env                        #
# --------------------------------------------------------------------------- #

PALABRAS_SENSIBLES = ("PASSWORD", "SECRET", "TOKEN", "KEY", "CLAVE", "CONTRASENA")


def entorno_de(imagen: str) -> list[str] | None:
    """Variables de entorno horneadas en la configuracion de una imagen."""
    inspeccion = correr(
        ["docker", "image", "inspect", imagen, "--format", "{{json .Config.Env}}"],
        mostrar=False,
    )
    if inspeccion.returncode != 0:
        return None
    return json.loads(inspeccion.stdout)


def imagen_base_de(dockerfile: Path) -> str | None:
    """
    La imagen base de la ULTIMA etapa del Dockerfile, que es la que hereda la
    imagen final. Se lee del archivo en vez de escribirla aqui para que cambiar la
    version base no deje esta comprobacion mirando la imagen equivocada.
    """
    ultima = None
    for linea in dockerfile.read_text(encoding="utf-8").splitlines():
        partes = linea.strip().split()
        if partes and partes[0].upper() == "FROM":
            ultima = partes[1]
    return ultima


def ca3_sin_secretos() -> Resultado:
    """
    POR QUE SE COMPARA CONTRA LA IMAGEN BASE Y NO SE BUSCAN PALABRAS A SECAS

    La primera version de esta comprobacion buscaba PASSWORD, SECRET, TOKEN o KEY
    en los nombres de las variables de la imagen y marcaba CA-3 como incumplido por
    `GPG_KEY`. Esa variable la pone la imagen oficial `python:3.11-slim`: es la
    huella publica de la llave con la que Python verifica su propio tarball al
    construirse. Es publica por definicion y nosotros no la pusimos.

    Lo que el criterio pide es que NOSOTROS no horneemos credenciales. Asi que se
    inspecciona tambien la imagen base y solo se escrutan las variables que
    aparecen de mas. Es mas correcto que una lista de excepciones: una lista habria
    tapado GPG_KEY por nombre y habria seguido ciega a cualquier variable base
    nueva, ademas de no distinguir jamas quien la puso.
    """
    detalle: list[str] = []
    cumple = True

    dockerfiles = {
        IMAGEN_API: RAIZ / "infra" / "docker" / "api.Dockerfile",
        IMAGEN_VISOR: RAIZ / "frontend" / "Dockerfile",
    }

    for imagen in (IMAGEN_API, IMAGEN_VISOR):
        # Se busca en TODO el sistema de archivos de la imagen, no solo en /app:
        # un .env podria haber entrado en cualquier capa.
        proceso = dentro(imagen, "find / -name '.env' -o -name '*.env' 2>/dev/null | head -20")
        hallazgos = [linea for linea in proceso.stdout.splitlines() if linea.strip()]
        if hallazgos:
            cumple = False
            detalle.append(f"  FALLA: {imagen} contiene archivos de entorno:")
            detalle.extend(f"    {linea}" for linea in hallazgos)
        else:
            detalle.append(f"  {imagen}: ningun archivo .env dentro de la imagen")

        # Y la contrasena tampoco puede estar horneada como variable de entorno de
        # la imagen. En docker-compose.yml llega en tiempo de ejecucion, que es
        # distinto: eso no queda en las capas ni se publica con la imagen.
        entorno = entorno_de(imagen)
        if entorno is None:
            cumple = False
            detalle.append(f"  FALLA: no se pudo inspeccionar {imagen}")
            continue

        base = imagen_base_de(dockerfiles[imagen])
        entorno_base = entorno_de(base) if base else None

        if entorno_base is None and base:
            # Construir la imagen no garantiza que la base quede en `docker images`:
            # con buildx las capas base pueden quedar solo en la cache de
            # construccion. Se trae y se reintenta, que es mas util que pedirle al
            # que corre esto que lo haga a mano.
            detalle.append(f"  la base `{base}` no estaba en el almacen local; se trae")
            correr(["docker", "pull", "--quiet", base], mostrar=False)
            entorno_base = entorno_de(base)

        if entorno_base is None:
            # Sin la base no se puede saber quien puso que. Se dice y se marca como
            # incumplido: preferible un fallo explicado a un criterio dado por bueno
            # sin haberlo comprobado.
            cumple = False
            detalle.append(
                f"  FALLA: no se pudo inspeccionar la imagen base `{base}` ni siquiera tras"
            )
            detalle.append(
                "         intentar traerla, asi que no se puede distinguir lo que agregamos."
            )
            continue

        # Se comparan los pares completos `nombre=valor`, no solo los nombres. Asi
        # una variable que ya existe en la base pero cuyo valor reescribimos
        # nosotros tambien aparece y se escruta. PATH sale por eso: la etapa de
        # ejecucion le antepone /opt/venv/bin.
        agregadas = [v for v in entorno if v not in set(entorno_base)]
        detalle.append(
            f"  {imagen}: base `{base}`, variables agregadas por nosotros: {len(agregadas)}"
        )
        for variable in agregadas:
            detalle.append(f"    {variable}")

        sospechosas = [
            variable
            for variable in agregadas
            if any(palabra in variable.split("=")[0].upper() for palabra in PALABRAS_SENSIBLES)
        ]
        if sospechosas:
            cumple = False
            detalle.append(f"  FALLA: {imagen} hornea variables sensibles: {sospechosas}")
        else:
            detalle.append(f"  {imagen}: ninguna de ellas es sensible")

    # requirements.txt tampoco deberia viajar en la imagen final de la API: es el
    # archivo compartido con las veinticinco dependencias del proyecto entero.
    proceso = dentro(IMAGEN_API, "test -f /app/requirements.txt && echo presente || echo ausente")
    estado = proceso.stdout.strip()
    detalle.append(f"  {IMAGEN_API}: requirements.txt en la imagen final -> {estado}")
    if estado == "presente":
        detalle.append(
            "    aviso: no es una credencial, pero la separacion en dos etapas deberia dejarlo fuera"
        )

    return Resultado(
        "CA-3", "Las imagenes no contienen credenciales ni el archivo .env", cumple, detalle
    )


# --------------------------------------------------------------------------- #
# CA-4 · la API corre como usuario sin privilegios                              #
# --------------------------------------------------------------------------- #


def ca4_sin_privilegios() -> Resultado:
    detalle: list[str] = []
    cumple = True

    # Se pregunta a un contenedor de verdad, no al Dockerfile: lo que vale es el
    # usuario con el que el proceso termina corriendo.
    proceso = dentro(IMAGEN_API, "id -u; id -un")
    lineas = [linea.strip() for linea in proceso.stdout.splitlines() if linea.strip()]
    if len(lineas) < 2:
        return Resultado(
            "CA-4",
            "La imagen de la API no corre como root",
            False,
            [f"  FALLA: {proceso.stderr[:200]}"],
        )

    uid, nombre = lineas[0], lineas[1]
    detalle.append(f"  usuario dentro del contenedor: {nombre} (uid {uid})")
    if uid == "0":
        cumple = False
        detalle.append("  FALLA: el uid 0 es root")

    # Y no debe poder escribir donde no le toca.
    prueba = dentro(
        IMAGEN_API, "touch /etc/prueba-escritura 2>&1 && echo ESCRIBIO || echo BLOQUEADO"
    )
    resultado_escritura = (
        prueba.stdout.strip().splitlines()[-1] if prueba.stdout.strip() else "sin salida"
    )
    detalle.append(f"  escritura en /etc: {resultado_escritura}")
    if resultado_escritura == "ESCRIBIO":
        cumple = False
        detalle.append("  FALLA: el usuario puede escribir en /etc")

    return Resultado("CA-4", "La imagen de la API no corre como root", cumple, detalle)


# --------------------------------------------------------------------------- #
# CA-5 · la evidencia existe y trae salidas                                     #
# --------------------------------------------------------------------------- #


def ca5_evidencia() -> Resultado:
    detalle: list[str] = []
    ruta = RAIZ / "docs" / "evidencias" / "arquitectura-software" / "H6.0-imagenes-docker.md"

    if not ruta.exists():
        return Resultado(
            "CA-5",
            "docker build y docker run documentados con su salida",
            False,
            [f"  FALLA: no existe {ruta.relative_to(RAIZ)}"],
        )

    texto = ruta.read_text(encoding="utf-8")
    detalle.append(f"  {ruta.relative_to(RAIZ)} existe ({len(texto.splitlines())} lineas)")

    cumple = True
    for marca, que in (
        ("docker build", "la orden de construccion"),
        ("docker compose up", "la orden de levantado"),
        ("/salud", "la respuesta de la sonda"),
    ):
        if marca not in texto:
            cumple = False
            detalle.append(f"  FALLA: la evidencia no menciona `{marca}` ({que})")
        else:
            detalle.append(f"  la evidencia incluye `{marca}`")

    return Resultado(
        "CA-5", "docker build y docker run documentados con su salida", cumple, detalle
    )


# --------------------------------------------------------------------------- #
# CA-6 (extra) · el .dockerignore hizo efecto                                   #
# --------------------------------------------------------------------------- #


def ca6_contexto_limpio() -> Resultado:
    """
    No esta en el issue. Se agrega porque los dos .dockerignore son la mitad del
    trabajo de esta historia y sin comprobarlos nadie sabria si funcionan: una
    imagen construida con el contexto sucio arranca igual.
    """
    detalle: list[str] = []
    cumple = True

    comprobaciones = [
        (IMAGEN_API, "/app/.venv", ".venv del anfitrion"),
        (IMAGEN_API, "/app/.git", "historia de git"),
        (IMAGEN_API, "/app/frontend", "carpeta del visor"),
        (IMAGEN_API, "/app/backend/etl", "guiones del ETL"),
        (IMAGEN_VISOR, "/usr/share/nginx/html/node_modules", "node_modules en lo publicado"),
    ]
    for imagen, ruta, que in comprobaciones:
        proceso = dentro(imagen, f"test -e {ruta} && echo presente || echo ausente")
        estado = proceso.stdout.strip()
        detalle.append(f"  {imagen}: {que} -> {estado}")
        if estado != "ausente":
            cumple = False
            detalle.append(f"    FALLA: {ruta} no deberia estar en la imagen")

    return Resultado("CA-6", "El contexto de construccion quedo limpio (extra)", cumple, detalle)


# --------------------------------------------------------------------------- #
# CA-7 (extra) · el visor alcanza la API por /api/                              #
# --------------------------------------------------------------------------- #


def ca7_paso_a_la_api(url_visor: str) -> Resultado:
    """
    Extra. La configuracion de nginx escrita dentro del Dockerfile del visor pasa
    /api/ hacia el servicio `api`. Si esa costura estuviera mal, el visor se
    veria perfecto y no traeria un solo dato, que es exactamente la clase de
    fallo que no se nota leyendo.
    """
    ok, cuerpo = esperar_http(f"{url_visor}/api/salud", limite_s=30)
    if not ok:
        return Resultado(
            "CA-7", "El visor alcanza la API por /api/ (extra)", False, [f"  FALLA: {cuerpo}"]
        )
    try:
        salud = json.loads(cuerpo)
    except json.JSONDecodeError:
        return Resultado(
            "CA-7",
            "El visor alcanza la API por /api/ (extra)",
            False,
            [f"  FALLA: /api/salud no devolvio JSON: {cuerpo[:120]}"],
        )
    return Resultado(
        "CA-7",
        "El visor alcanza la API por /api/ (extra)",
        True,
        [
            f"  GET {url_visor}/api/salud respondio 200",
            f"  cuerpo: {json.dumps(salud, ensure_ascii=False)}",
            "  o sea que nginx paso la peticion al servicio `api` por la red de Docker",
        ],
    )


# --------------------------------------------------------------------------- #


def main() -> int:
    analizador = argparse.ArgumentParser(description="Verifica los criterios de H6.0")
    analizador.add_argument(
        "--sin-construir",
        action="store_true",
        help="reusa las imagenes ya construidas en vez de volver a construirlas",
    )
    analizador.add_argument(
        "--dejar-arriba", action="store_true", help="no baja los contenedores al terminar"
    )
    argumentos = analizador.parse_args()

    print("Verificacion de las imagenes de Docker de H6.0 (issue #62)")
    print("=" * 74)

    disponible, mensaje = hay_docker()
    print(f"Docker: {mensaje}")
    if not disponible:
        print("\nNO SE PUEDE VERIFICAR: " + mensaje)
        print("Este guion no da por buenos los criterios que no pudo ejecutar.")
        return 2

    if not (RAIZ / ".env").exists():
        print("\nNO SE PUEDE VERIFICAR: falta el archivo .env en la raiz.")
        print("docker-compose.yml exige POSTGRES_PASSWORD y aborta sin el.")
        return 2

    url_api = f"http://localhost:{puerto('API_PORT', '8000')}"
    url_visor = f"http://localhost:{puerto('VISOR_PORT', '5173')}"
    print(f"API en {url_api} · visor en {url_visor}")

    resultados: list[Resultado] = []

    try:
        if not argumentos.sin_construir:
            print("\nConstruyendo. La primera vez tarda varios minutos por `npm ci`.")
            construccion = correr(["docker", "compose", "build", "api", "visor"])
            if construccion.returncode != 0:
                print("\nFALLO LA CONSTRUCCION:")
                print(construccion.stdout[-3000:])
                print(construccion.stderr[-3000:])
                return 1
            print("    construccion terminada")

        print("\nLevantando los servicios.")
        levantado = correr(["docker", "compose", "up", "-d", "db", "api", "visor"])
        if levantado.returncode != 0:
            print("\nNO LEVANTARON:")
            print(levantado.stdout[-3000:])
            print(levantado.stderr[-3000:])
            return 1

        resultados.append(ca1_api(url_api))
        resultados.append(ca2_visor(url_visor))
        resultados.append(ca3_sin_secretos())
        resultados.append(ca4_sin_privilegios())
        resultados.append(ca5_evidencia())
        resultados.append(ca6_contexto_limpio())
        resultados.append(ca7_paso_a_la_api(url_visor))

        # Los resultados se imprimen ANTES de bajar los contenedores, aunque el
        # bajado este en el `finally`. Si no, el log de la evidencia muestra
        # "bajando los contenedores" arriba de las comprobaciones y parece que
        # hubieran corrido con todo apagado, que no es lo que paso.
        for r in resultados:
            print(f"\n{r.criterio} · {r.titulo} ... {'CUMPLE' if r.cumple else 'NO CUMPLE'}")
            for linea in r.detalle:
                print(linea)

        fallidos = [r for r in resultados if not r.cumple]
        print("\n" + "=" * 74)
        if fallidos:
            print("NO CUMPLEN: " + ", ".join(r.criterio for r in fallidos))
            salida = 1
        else:
            print("Los cinco criterios del issue y las dos comprobaciones extra se cumplen.")
            print("Falta la Definition of Done en maquina limpia, que verifica otra persona.")
            salida = 0
    finally:
        if not argumentos.dejar_arriba:
            print("\nBajando los contenedores. El volumen de datos NO se borra.")
            # Sin -v a proposito: `docker compose down -v` destruye el volumen de
            # PostgreSQL. Ya paso una vez en este proyecto y costo una recarga
            # entera. Ver incidencia I-05.
            correr(["docker", "compose", "stop", "api", "visor"], mostrar=False)

    return salida


if __name__ == "__main__":
    raise SystemExit(main())
