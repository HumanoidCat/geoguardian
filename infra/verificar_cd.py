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

    # SE EJECUTA LA FUNCION, NO SE BUSCA UN TEXTO.
    #
    # La version anterior comprobaba que la cadena "newTag" apareciera en el
    # guion. Eso pasaba en verde mientras `fijar_etiqueta` fallaba en el runner
    # con `Missing kustomization file`: buscar un texto no dice si el codigo
    # corre.
    #
    # Es la leccion de I-10 aplicada a un verificador estatico. Ahora se copia el
    # arbol a un temporal, se llama a la funcion de verdad, y se comprueba el
    # resultado.
    import importlib.util
    import shutil
    import tempfile

    especificacion = importlib.util.spec_from_file_location("desplegar", K8S / "desplegar.py")
    desplegar = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(desplegar)

    with tempfile.TemporaryDirectory() as carpeta:
        arbol = Path(carpeta) / "k8s"
        shutil.copytree(K8S, arbol)
        try:
            desplegar.fijar_etiqueta(arbol, "desarrollo", "sha-" + "a" * 40)
            resultado = (arbol / "base" / "kustomization.yaml").read_text(encoding="utf-8")
            fijo = f"newTag: sha-{'a' * 40}" in resultado and "newTag: latest" not in resultado
            detalle = ""
        # `SystemExit` va explicito: hereda de BaseException, no de Exception, y
        # `fijar_etiqueta` la usa para plantarse. Sin nombrarla, el verificador
        # moria a mitad y se saltaba los trece criterios restantes en vez de
        # reportar uno en rojo.
        except (Exception, SystemExit) as error:  # noqa: BLE001
            fijo, detalle = False, f"{type(error).__name__}: {str(error).splitlines()[0]}"

    exigir(fijo, "fijar_etiqueta() corre y deja la etiqueta puesta", detalle)

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


def separar_pods(items: list[dict]) -> tuple[list[dict], list[dict]]:
    """Los pods que cuentan y los que se estan apagando. I-28.

    `kubectl rollout status` vuelve cuando la revision nueva esta disponible, no
    cuando la anterior termino de morir. Durante ese hueco -hasta 30 s por
    omision- el pod viejo sigue en la lista con `deletionTimestamp` puesto y
    `Ready=False`, y exigirle Ready es exigirle a un despliegue correcto que
    parezca roto. En produccion el hueco existe SIEMPRE, porque el flujo
    despliega dos veces a proposito para tener a que revertir.

    Un pod que se apaga no cuenta. Uno vivo y no Ready si, y sigue haciendo
    fallar el criterio: es lo que `--manifiestos` comprueba sin cluster.
    """
    apagandose = [p for p in items if p.get("metadata", {}).get("deletionTimestamp")]
    vivos = [p for p in items if not p.get("metadata", {}).get("deletionTimestamp")]
    return vivos, apagandose


def esta_ready(pod: dict) -> bool:
    condiciones = {c["type"]: c["status"] for c in pod.get("status", {}).get("conditions", [])}
    return condiciones.get("Ready") == "True"


def comprobar_separacion_de_pods() -> None:
    """El control sabe decir que no: se le dan los tres casos y se mira que hace.

    Corre en `--manifiestos`, o sea en cada PR y sin cluster, porque la primera
    version de este control paso dos corridas del CD en verde y fallo en la
    tercera por el reloj, y un control que depende del reloj no se puede probar
    esperando a que falle.
    """
    print("\nLa separacion de pods de I-28, sin cluster\n")
    ready = {"status": {"conditions": [{"type": "Ready", "status": "True"}]}}
    no_ready = {"status": {"conditions": [{"type": "Ready", "status": "False"}]}}
    vivo_ready = {"metadata": {"name": "visor-nuevo"}, **ready}
    vivo_roto = {"metadata": {"name": "visor-roto"}, **no_ready}
    viejo = {
        "metadata": {"name": "visor-viejo", "deletionTimestamp": "2026-09-03T20:12:40Z"},
        **no_ready,
    }

    vivos, apagandose = separar_pods([vivo_ready, viejo])
    exigir(
        [p["metadata"]["name"] for p in apagandose] == ["visor-viejo"],
        "un pod con deletionTimestamp se aparta y no cuenta",
    )
    exigir(
        [p["metadata"]["name"] for p in vivos] == ["visor-nuevo"] and esta_ready(vivos[0]),
        "el pod nuevo cuenta y esta Ready",
    )
    vivos, _ = separar_pods([vivo_ready, vivo_roto])
    exigir(
        any(not esta_ready(p) for p in vivos),
        "un pod vivo y no Ready sigue contando, y haria fallar el criterio",
    )
    vivos, apagandose = separar_pods([viejo])
    exigir(
        not vivos and len(apagandose) == 1,
        "si solo queda el pod que se apaga, no hay pods que cuenten",
    )


def comprobar_entorno(entorno: str, sha: str | None, tras_reversion: bool) -> None:
    namespace = f"geoguardian-{entorno}"
    print(f"\nEl entorno {namespace}, contra el cluster\n")

    items = json.loads(kubectl("-n", namespace, "get", "pods", "-o", "json"))["items"]
    vivos, apagandose = separar_pods(items)
    for pod in apagandose:
        print(f"  --    {pod['metadata']['name']} se esta apagando: revision anterior, no cuenta")
    detalle = f"{len(vivos)} pods" + (f", {len(apagandose)} apagandose" if apagandose else "")
    exigir(bool(vivos), "hay pods en el namespace", detalle)

    for pod in vivos:
        exigir(esta_ready(pod), f"{pod['metadata']['name']} esta Ready")

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
        comprobar_separacion_de_pods()
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
