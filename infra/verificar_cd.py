"""Comprueba la entrega continua. Historias H11.2, H11.3 y H11.4.

QUE COMPRUEBA, Y POR QUE ESTAN SEPARADOS EN DOS MODOS

Los manifiestos se pueden comprobar **sin cluster**, y eso importa: el flujo de
CD solo corre sobre `main`, asi que sin el modo estatico un manifiesto roto
llegaria a `main` para descubrirse alli. El modo estatico corre en cada PR.

    --manifiestos            sin cluster. Estructura e invariantes de infra/k8s.
    --entorno X --sha Y      contra un cluster vivo, despues de desplegar.
    --entorno X --tras-reversion   que la reversion dejo el sistema en pie.
    --comprobar-aprobacion X que el entorno de GitHub exige una persona.

EL MODO QUE MAS VALE ES EL ULTIMO, Y NO MIRA NINGUN POD

H11.3 y H11.4 piden aprobacion manual y explicita. Eso **no vive en este
repositorio**: son `environment:` de GitHub con revisores, configurados en
Settings. Un flujo puede decir `environment: produccion` y salir verde aunque
ese entorno no exista o no tenga revisores — y entonces la historia esta
incumplida con el CI en verde.

Es la forma de I-25: un control que corre y no protege. La unica manera de
vigilar una condicion que vive fuera del repositorio es preguntarle a la API.

Uso:
    python infra/verificar_cd.py --manifiestos
    python infra/verificar_cd.py --entorno desarrollo --sha <sha>
    python infra/verificar_cd.py --comprobar-aprobacion produccion
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
K8S = RAIZ / "infra" / "k8s"
BASE = "ghcr.io/humanoidcat/geoguardian"
ENTORNOS = ("desarrollo", "pruebas", "produccion")

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


class SinKubectl(Exception):
    """No hay `kubectl` en el PATH, o no responde."""


def kubectl(*argumentos: str) -> str:
    """Corre kubectl y devuelve su salida.

    NO DEJA QUE UNA EXCEPCION SE ESCAPE COMO TRAZA DE PYTHON.

    La primera version llamaba con `check=True` y nada mas. Al correrlo en una
    maquina sin `kubectl` en el PATH, el guion moria con veinte lineas de
    `CalledProcessError` que no mencionan `kubectl` hasta el final.

    **Un verificador que revienta es peor que uno que falla**: el que falla dice
    que criterio no se cumple; el que revienta obliga a leer una traza para
    averiguar si el defecto es del sistema o de la herramienta. Lo encontro
    Alejandro corriendo esto en Windows el 2026-09-02, y es de la familia de
    I-24: el control funcionaba solo donde ya estaba todo instalado.
    """
    try:
        terminado = subprocess.run(
            ["kubectl", *argumentos], capture_output=True, text=True, check=True
        )
    except FileNotFoundError:
        raise SinKubectl(
            "no hay `kubectl` en el PATH.\n"
            "      Instalarlo:  winget install -e --id Kubernetes.kubectl\n"
            "      Y abrir una consola nueva para que el PATH se actualice."
        ) from None
    except subprocess.CalledProcessError as error:
        detalle = (error.stderr or error.stdout or "").strip().splitlines()
        raise SinKubectl(
            f"`kubectl {' '.join(argumentos[:3])}` fallo: "
            f"{detalle[0] if detalle else 'sin mensaje'}"
        ) from None
    return terminado.stdout


def leer(ruta: Path) -> dict:
    return yaml.safe_load(ruta.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# Modo estatico. Corre en cada PR, sin cluster.                                 #
# --------------------------------------------------------------------------- #


def comprobar_manifiestos() -> None:
    print("\nLos manifiestos de infra/k8s, sin cluster\n")

    base = leer(K8S / "base" / "kustomization.yaml")
    recursos = set(base.get("resources", []))

    for nombre in ("api-deployment.yaml", "api-service.yaml", "visor-deployment.yaml"):
        exigir(nombre in recursos, f"la base incluye {nombre}")

    # La base declara `latest` a proposito, para poder aplicarse a mano. Lo que
    # no puede pasar es que el guion de despliegue no sepa reemplazarlo.
    declaradas = {i["name"] for i in base.get("images", [])}
    exigir(
        declaradas == {f"{BASE}/api", f"{BASE}/visor"},
        "el bloque images declara las dos imagenes de H11.1",
        f"declara {sorted(declaradas)}",
    )

    guion = (K8S / "desplegar.py").read_text(encoding="utf-8")
    exigir("newTag" in guion, "el guion de despliegue sabe reemplazar la etiqueta")
    exigir(
        '"rollout", "status"' in guion,
        "el guion espera a que converja: sin esto, `apply` siempre dice exito",
    )
    # El guion estuvo escrito en bash y no corria en ninguna maquina del equipo:
    # winget instala kubectl como alias de WindowsApps y Git Bash no lo ejecuta.
    # Era el quinto caso de I-24. Que nadie lo devuelva a bash sin darse cuenta.
    exigir(
        not (K8S / "desplegar.sh").exists(),
        "el guion de despliegue no volvio a bash",
        "en Windows, Git Bash no puede ejecutar el kubectl que instala winget",
    )

    api = leer(K8S / "base" / "api-deployment.yaml")
    visor = leer(K8S / "base" / "visor-deployment.yaml")

    for nombre, manifiesto in (("api", api), ("visor", visor)):
        contenedor = manifiesto["spec"]["template"]["spec"]["containers"][0]
        exigir(
            "readinessProbe" in contenedor and "livenessProbe" in contenedor,
            f"{nombre} declara las dos sondas",
            "sin readiness, rollout status da por bueno un pod que no responde",
        )
        exigir(
            contenedor["image"].startswith(f"{BASE}/{nombre}:"),
            f"{nombre} usa la imagen que publica H11.1",
            contenedor["image"],
        )

    # LA INVARIANTE DE SC-07, VIGILADA POR UNA MAQUINA.
    #
    # Una barra final en DESTINO_API produce `//distritos` en cada peticion, sin
    # fallar al arrancar y sin aparecer en ningun registro. El guion
    # 05-destino-api.envsh la recorta, pero eso no es motivo para escribirla:
    # el guion es la red, no el permiso.
    entorno = {
        v["name"]: v.get("value") for v in visor["spec"]["template"]["spec"]["containers"][0]["env"]
    }
    destino = entorno.get("DESTINO_API", "")
    exigir(
        destino.endswith(":8000") and not destino.endswith("/"),
        "DESTINO_API no termina en barra",
        destino,
    )

    servicio_api = leer(K8S / "base" / "api-service.yaml")
    nombre_servicio = servicio_api["metadata"]["name"]
    exigir(
        f"//{nombre_servicio}:" in destino,
        "DESTINO_API apunta al Service que existe, por su nombre real",
        f"el Service se llama '{nombre_servicio}' y DESTINO_API dice '{destino}'",
    )

    puerto_api = servicio_api["spec"]["ports"][0]["port"]
    exigir(
        destino.endswith(f":{puerto_api}"),
        "el puerto de DESTINO_API es el del Service",
        f"Service en {puerto_api}, DESTINO_API en {destino.rsplit(':', 1)[-1]}",
    )

    for nombre in ENTORNOS:
        overlay = leer(K8S / "local" / nombre / "kustomization.yaml")
        exigir(
            overlay.get("namespace") == f"geoguardian-{nombre}"
            and "../../base" in overlay.get("resources", []),
            f"el entorno {nombre} tiene su namespace y hereda la base",
        )


# --------------------------------------------------------------------------- #
# Modo con cluster.                                                             #
# --------------------------------------------------------------------------- #


def imagenes_corriendo(namespace: str) -> dict[str, str]:
    salida = kubectl(
        "-n",
        namespace,
        "get",
        "deployments",
        "-o",
        "jsonpath={range .items[*]}{.metadata.name}={.spec.template.spec.containers[0].image}{'\\n'}{end}",
    )
    return dict(linea.split("=", 1) for linea in salida.strip().splitlines() if "=" in linea)


def comprobar_entorno(entorno: str, sha: str | None, tras_reversion: bool) -> None:
    namespace = f"geoguardian-{entorno}"
    print(f"\nEl entorno {namespace}, contra el cluster\n")

    listos = json.loads(kubectl("-n", namespace, "get", "pods", "-o", "json"))["items"]
    exigir(bool(listos), "hay pods en el namespace", f"{len(listos)} pods")

    for pod in listos:
        nombre = pod["metadata"]["name"]
        condiciones = {c["type"]: c["status"] for c in pod["status"].get("conditions", [])}
        exigir(condiciones.get("Ready") == "True", f"{nombre} esta Ready")

    imagenes = imagenes_corriendo(namespace)
    exigir(set(imagenes) == {"api", "visor"}, "estan los dos Deployment", f"{sorted(imagenes)}")

    if sha:
        # NINGUN DESPLIEGUE AUTOMATICO PUEDE QUEDAR EN `latest`.
        #
        # Con `latest`, dos corridas del mismo manifiesto dan resultados
        # distintos y nada registra cual esta corriendo. Es la diferencia entre
        # un despliegue reproducible y uno que hay que ir a mirar.
        for nombre, imagen in imagenes.items():
            exigir(
                imagen.endswith(f":sha-{sha}"),
                f"{nombre} corre el SHA exacto, no `latest`",
                imagen,
            )

    if tras_reversion:
        for nombre, imagen in imagenes.items():
            exigir(
                not imagen.endswith(":sha-0000000000000000000000000000000000000000"),
                f"{nombre} volvio a la revision anterior",
                imagen,
            )

    # QUE LOS PODS ESTEN READY NO DICE QUE EL SISTEMA RESPONDA.
    #
    # Es la leccion de I-10 aplicada aca: las sondas comprueban lo que se les
    # pidio comprobar. Esto pregunta de verdad, desde dentro del cluster.
    #
    # El fallo se convierte en un criterio en rojo y no en una excepcion: que la
    # API no responda es justamente uno de los resultados que este verificador
    # existe para reportar.
    try:
        salud = kubectl(
            "-n",
            namespace,
            "run",
            "prueba-salud",
            "--rm",
            "-i",
            "--restart=Never",
            "--image=curlimages/curl:8.10.1",
            "--quiet",
            "--",
            "curl",
            "-sf",
            "-o",
            "/dev/null",
            "-w",
            "%{http_code}",
            "http://api:8000/salud",
        ).strip()
    except SinKubectl as error:
        salud = f"no se pudo preguntar: {error}"
    exigir(salud.endswith("200"), "la API responde 200 en /salud desde el cluster", salud)


# --------------------------------------------------------------------------- #
# Modo aprobacion. No mira ningun pod.                                          #
# --------------------------------------------------------------------------- #


def comprobar_aprobacion(entorno: str) -> None:
    print(f"\nEl entorno de GitHub '{entorno}' exige una persona\n")

    repositorio = "HumanoidCat/geoguardian"
    try:
        crudo = subprocess.run(
            ["gh", "api", f"repos/{repositorio}/environments/{entorno}"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except FileNotFoundError:
        exigir(False, "hace falta `gh` para consultar el entorno")
        return
    except subprocess.CalledProcessError as error:
        exigir(
            False,
            f"el entorno '{entorno}' existe en Settings",
            (error.stderr or "").strip().splitlines()[0] if error.stderr else "",
        )
        return

    datos = json.loads(crudo)
    reglas = datos.get("protection_rules", [])
    revisores = [r for r in reglas if r.get("type") == "required_reviewers"]

    exigir(bool(revisores), f"el entorno '{entorno}' tiene revisores requeridos")
    if revisores:
        cuantos = len(revisores[0].get("reviewers", []))
        exigir(cuantos >= 1, "hay al menos un revisor configurado", f"{cuantos} revisores")


def main() -> int:
    p = argparse.ArgumentParser(description="Comprobaciones de la entrega continua.")
    p.add_argument("--manifiestos", action="store_true")
    p.add_argument("--entorno", choices=ENTORNOS)
    p.add_argument("--sha")
    p.add_argument("--tras-reversion", action="store_true")
    p.add_argument("--comprobar-aprobacion", choices=ENTORNOS)
    args = p.parse_args()

    if args.manifiestos:
        comprobar_manifiestos()
    if args.entorno:
        # Un problema de herramienta se distingue de un criterio incumplido.
        # Confundirlos hace perder tiempo buscando el defecto donde no esta.
        try:
            comprobar_entorno(args.entorno, args.sha, args.tras_reversion)
        except SinKubectl as error:
            print(f"\n  No se pudo hablar con el cluster: {error}\n")
            return 2
    if args.comprobar_aprobacion:
        comprobar_aprobacion(args.comprobar_aprobacion)

    if not (args.manifiestos or args.entorno or args.comprobar_aprobacion):
        p.error("hay que pedir al menos un modo")

    print(f"\n{hechos - len(fallos)} de {hechos} comprobaciones")
    if fallos:
        print("\nNO se cumplen:")
        for f in fallos:
            print(f"  - {f}")
        print()
        return 1
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
