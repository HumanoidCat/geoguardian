"""Criterios de aceptacion de H11.1: la imagen construida arranca y responde.

===========================================================================
POR QUE NO ALCANZA CON QUE EL BUILD TERMINE
===========================================================================

Un `docker build` que termina en cero dice que **el Dockerfile se ejecuto**, no
que la imagen sirva. Los dos modos de fallo que este verificador busca son
justamente los que el build no ve:

  * **Falta un archivo que el `.dockerignore` excluyo.** El build copia lo que
    hay, no falla por lo que no esta, y la imagen revienta al arrancar.
  * **La imagen arranca y no responde.** Un `CMD` mal escrito, un puerto que no
    es el que se expone, una variable que solo existe en la maquina de quien lo
    escribio.

Es el mismo criterio que el resto del proyecto: **verificado ejecutando, no
leyendo**, que ademas es una linea explicita del Definition of Done de esta
historia.

===========================================================================
QUE COMPRUEBA, POR IMAGEN
===========================================================================

**api**

    arranca sin salirse                el contenedor sigue vivo pasados unos segundos
    responde en /salud                 codigo 200
    no corre como root                 el Dockerfile crea un usuario y hay que usarlo

**visor**

    arranca sin salirse
    sirve el index.html                codigo 200 en /
    el bundle esta adentro             hay al menos un .js en el directorio servido
    /api/ degrada con 502              SIN API al lado, y el contenedor sigue vivo
    hay rewrite si hay variable        el par de SC-07 que no se rompe por separado

Los dos ultimos son de **SC-07**. Este verificador corre el visor sin la API al
lado -eso es lo que hace `docker run` a secas- y asi encontro que la imagen ni
siquiera arrancaba: nginx resuelve los upstream **al arrancar**, y con
`proxy_pass http://api:8000/` literal se negaba a levantar. Dentro de
`docker compose` el nombre existe siempre y por eso nunca se noto.

===========================================================================
LO QUE **NO** COMPRUEBA, Y ES DELIBERADO
===========================================================================

**No comprueba que la API hable con la base.** Eso necesita PostgreSQL con
PostGIS levantado y es el trabajo `pruebas` del CI, que ya lo hace. Duplicarlo
aca haria este verificador lento y fragil por una razon que no le corresponde:
lo que se esta comprobando es la **imagen**, no la integracion.

Por eso `/salud` tiene que responder **sin** base. Si algun dia deja de hacerlo,
este verificador se pone rojo y esta bien que lo haga: un endpoint de salud que
exige la base no sirve para saber si el contenedor esta vivo.

Uso:
    python docs/herramientas/verificar_h111.py --imagen api
    python docs/herramientas/verificar_h111.py --imagen visor
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

#: Puerto interno de cada imagen y por donde responde que esta viva.
IMAGENES = {
    "api": {"puerto": 8000, "ruta": "/salud"},
    "visor": {"puerto": 80, "ruta": "/"},
}

#: Cuanto se espera a que arranque antes de darla por muerta. Generoso a
#: proposito: un runner compartido puede ser lento, y un verificador que falla
#: por impaciencia ensena a la gente a reintentar el CI sin leerlo.
ESPERA_MAXIMA = 40
INTERVALO = 2


def _correr(orden: list[str], **extra) -> subprocess.CompletedProcess:
    """Ejecuta y devuelve el resultado. **Sin binario tambien devuelve, no lanza.**

    `subprocess.run` levanta `FileNotFoundError` cuando el ejecutable no existe,
    en vez de devolver un codigo distinto de cero. Sin atrapar eso, la
    comprobacion de «¿hay Docker?» de `main` moria con una traza antes de poder
    imprimir su mensaje, y quien lo corriera sin Docker veia un error de Python
    en lugar de la explicacion.

    Se detecto corriendo el verificador en una maquina sin Docker, que es
    exactamente el caso que ese mensaje existe para cubrir.
    """
    try:
        return subprocess.run(orden, capture_output=True, text=True, check=False, **extra)
    except FileNotFoundError as error:
        return subprocess.CompletedProcess(orden, returncode=127, stdout="", stderr=str(error))


def _etiqueta_local(nombre: str) -> str:
    """La imagen que dejo `docker build`, con el nombre que usa docker compose."""
    return f"geoguardian-{nombre}"


def _esperar_respuesta(url: str) -> tuple[bool, str]:
    """Golpea la URL hasta que responda 200 o se acabe la paciencia."""
    ultimo = "sin intentos"
    limite = time.time() + ESPERA_MAXIMA
    while time.time() < limite:
        try:
            with urllib.request.urlopen(url, timeout=3) as respuesta:  # noqa: S310
                if respuesta.status == 200:
                    return True, f"200 en {url}"
                ultimo = f"codigo {respuesta.status}"
        except urllib.error.HTTPError as error:
            ultimo = f"codigo {error.code}"
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            ultimo = f"sin conexion: {error}"
        time.sleep(INTERVALO)
    return False, ultimo


def verificar(nombre: str) -> int:
    if nombre not in IMAGENES:
        print(f"\nImagen desconocida: {nombre}. Las que hay: {', '.join(IMAGENES)}\n")
        return 1

    config = IMAGENES[nombre]
    imagen = _etiqueta_local(nombre)
    contenedor = f"h111-{nombre}-{uuid.uuid4().hex[:8]}"

    print(f"\nCriterios de aceptacion de H11.1 sobre la imagen `{imagen}`\n")

    fallos: list[str] = []

    def comprobar(descripcion: str, condicion: bool, detalle: str = "") -> None:
        print(
            f"  {'OK   ' if condicion else 'FALLA'} {descripcion}"
            + (f"  ({detalle})" if detalle else "")
        )
        if not condicion:
            fallos.append(descripcion)

    existe = _correr(["docker", "image", "inspect", imagen])
    comprobar("la imagen existe en el demonio local", existe.returncode == 0)
    if existe.returncode != 0:
        print(f"\n  No esta `{imagen}`. Se construye con:\n")
        print("      docker compose build\n")
        return 1

    # El puerto se deja elegir al sistema para no chocar con nada que ya corra
    # en el runner ni en la maquina de quien lo ejecute a mano.
    arranque = _correr(["docker", "run", "-d", "--name", contenedor, "-P", imagen])
    comprobar("el contenedor arranca", arranque.returncode == 0, arranque.stderr.strip()[:80])
    if arranque.returncode != 0:
        return 1

    try:
        # Que `docker run` devuelva cero solo dice que el contenedor se creo. Un
        # proceso que muere en el primer segundo tambien pasa por ahi.
        time.sleep(3)
        estado = _correr(["docker", "inspect", "-f", "{{.State.Running}}", contenedor])
        vivo = estado.stdout.strip() == "true"
        if not vivo:
            registro = _correr(["docker", "logs", "--tail", "20", contenedor])
            comprobar("sigue vivo pasados tres segundos", False, "murio al arrancar")
            print("\n  Ultimas lineas del contenedor:\n")
            for linea in (registro.stdout + registro.stderr).splitlines()[-20:]:
                print(f"    {linea}")
            return 1
        comprobar("sigue vivo pasados tres segundos", True)

        puertos = _correr(["docker", "port", contenedor, str(config["puerto"])])
        publicado = puertos.stdout.strip().splitlines()
        comprobar(
            f"publica el puerto {config['puerto']}",
            bool(publicado),
            puertos.stderr.strip()[:60],
        )
        if not publicado:
            return 1

        # `docker port` puede devolver IPv6 y IPv4; se toma el ultimo campo de
        # la primera linea, que es siempre `direccion:puerto`.
        local = publicado[0].rsplit(":", 1)[-1]
        respondio, detalle = _esperar_respuesta(f"http://127.0.0.1:{local}{config['ruta']}")
        comprobar(f"responde 200 en {config['ruta']}", respondio, detalle)

        if nombre == "api":
            # El Dockerfile crea el usuario `geoguardian`; correr como root
            # anularia esa medida sin que nada mas lo note.
            quien = _correr(["docker", "exec", contenedor, "id", "-u"])
            comprobar(
                "no corre como root",
                quien.stdout.strip() not in ("0", ""),
                f"uid {quien.stdout.strip() or 'desconocido'}",
            )
        else:
            # El build del visor produce el bundle; si el .dockerignore se lleva
            # `dist/`, nginx sirve un index vacio y el 200 de arriba pasa igual.
            listado = _correr(
                ["docker", "exec", contenedor, "sh", "-c", "ls /usr/share/nginx/html/assets/*.js"]
            )
            comprobar(
                "el bundle esta dentro de la imagen",
                listado.returncode == 0 and ".js" in listado.stdout,
                "no hay .js en assets/" if listado.returncode else "",
            )

            # -------------------------------------------------------------- #
            # Los dos criterios de SC-07                                      #
            # -------------------------------------------------------------- #
            # Este verificador corre el visor SIN la API al lado, y asi fue
            # como encontro que la imagen ni siquiera arrancaba: nginx resuelve
            # los upstream al arrancar, y con `proxy_pass http://api:8000/`
            # literal se negaba a levantar con "host not found in upstream".
            #
            # "sigue vivo pasados tres segundos" ya atrapa esa regresion. Estos
            # dos criterios existen para dejar dicho **que comportamiento se
            # espera**, no solo que no se muera.
            codigo = _correr(
                [
                    "docker",
                    "exec",
                    contenedor,
                    "sh",
                    "-c",
                    "wget -q -O /dev/null -S http://localhost/api/salud 2>&1 | "
                    "awk '/HTTP\\// { print $2; exit }'",
                ]
            )
            # 502 es el resultado CORRECTO sin API: nginx difirio la resolucion,
            # intento conectar y no pudo. El visor sigue sirviendo sus estaticos
            # y degrada a su respaldo declarandolo en pantalla, que es D-23.
            #
            # Un 404 aqui seria el otro defecto, el peor: `proxy_pass` con
            # variable pero sin el `rewrite`, que hace que la API reciba
            # `/api/salud` en vez de `/salud`. El contenedor arranca y todas las
            # rutas fallan sin que nada se vea al iniciar.
            visto = codigo.stdout.strip()
            comprobar(
                "sin API, /api/ degrada con 502 en vez de matar al contenedor",
                visto == "502",
                f"devolvio {visto or 'nada'}",
            )

            # El par variable-mas-rewrite no se puede romper por separado, y con
            # el contenedor solo no hay forma de distinguirlo por HTTP: sin API,
            # con rewrite y sin el, los dos dan 502. Se comprueba sobre la
            # configuracion que nginx genero al arrancar, que es el unico lugar
            # donde la diferencia es visible sin levantar una API de mentira.
            config_nginx = _correr(
                ["docker", "exec", contenedor, "cat", "/etc/nginx/conf.d/default.conf"]
            ).stdout
            usa_variable = "proxy_pass $" in config_nginx
            comprobar(
                "si proxy_pass usa variable, existe el rewrite que quita /api/",
                (not usa_variable) or ("rewrite ^/api/" in config_nginx),
                "hay variable sin rewrite: la API recibiria /api/... y todo daria 404",
            )
    finally:
        _correr(["docker", "rm", "-f", contenedor])

    print()
    if fallos:
        print(f"  {len(fallos)} criterio(s) sin cumplir:\n")
        for f in fallos:
            print(f"    {f}")
        print()
        return 1

    print("  Los criterios de H11.1 se cumplen sobre la imagen construida.\n")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--imagen", required=True, choices=sorted(IMAGENES))
    argumentos = p.parse_args()

    if _correr(["docker", "version", "--format", "{{.Server.Version}}"]).returncode != 0:
        print("\n  No hay un demonio de Docker disponible. Este verificador lo necesita:")
        print("  comprueba la imagen **ejecutandola**, que es el punto.\n")
        return 1

    return verificar(argumentos.imagen)


if __name__ == "__main__":
    sys.exit(main())
