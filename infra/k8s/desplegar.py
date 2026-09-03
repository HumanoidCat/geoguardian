"""Aplica los manifiestos de un entorno. Historias H11.2, H11.3 y H11.4.

=============================================================================
EL MISMO GUION EN LOS DOS SITIOS, Y ESE ES EL PUNTO
=============================================================================

Lo corre el flujo de CD contra el cluster efimero, y lo corre una persona contra
el cluster k3d local. **No hay dos definiciones del despliegue**: si el CI y la
maquina desplegaran por caminos distintos, el CI en verde no diria nada sobre lo
que pasa en local, que es lo unico que alguien va a ver.

Ver D-36.

=============================================================================
POR QUE PYTHON Y NO BASH, QUE ERA LA PRIMERA VERSION
=============================================================================

Esto estaba escrito en bash. En la primera corrida en una maquina del equipo
-Windows, 2026-09-02- no funciono, y el motivo importa mas que el sintoma:

**winget instala `kubectl` como alias de linea de comandos**, uno de esos
reparse points de `WindowsApps`. PowerShell lo ejecuta. Python lo ejecuta. **Git
Bash no**, ni siquiera lo encuentra con `command -v`.

O sea que el guion en bash era el quinto caso de **I-24**: un control que pasa en
el CI de Linux y no corre en ninguna maquina del equipo. Y se habria escrito el
mismo dia en que esa incidencia se registro.

Se podia arreglar pidiendole a cada uno que bajara el binario real. Pero eso es
resolver el sintoma en cuatro maquinas en vez de la causa en un archivo, y deja
la trampa puesta para el proximo que clone el repositorio.

**Python ya es requisito del proyecto, corre igual en los tres sistemas, y
resuelve los ejecutables como los resuelve el sistema operativo.**

Uso:
    python infra/k8s/desplegar.py <entorno> [etiqueta]

    entorno    desarrollo | pruebas | produccion
    etiqueta   `latest`, o el SHA del commit. Un SHA de 40 caracteres se
               convierte a `sha-<sha>`, que es como los etiqueta H11.1. Por
               omision, `latest`.

Ejemplos:
    python infra/k8s/desplegar.py desarrollo
    python infra/k8s/desplegar.py produccion 3f2a9c1...
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
K8S = RAIZ / "infra" / "k8s"
BASE = "ghcr.io/humanoidcat/geoguardian"
ENTORNOS = ("desarrollo", "pruebas", "produccion")


def correr(*argumentos: str, entrada_muda: bool = False) -> subprocess.CompletedProcess:
    """Corre un comando mostrando su salida, y se planta si falla."""
    if not entrada_muda:
        print(f"  $ {' '.join(argumentos)}")
    return subprocess.run(argumentos, check=True)


def hay_kubectl() -> bool:
    """Comprueba kubectl EJECUTANDOLO, no buscando el archivo.

    `shutil.which` da un falso negativo con el alias de winget en Windows, que es
    justo el caso que rompio la version en bash. La pregunta correcta no es
    «existe un archivo que se llama kubectl» sino «puedo ejecutar kubectl».
    """
    try:
        subprocess.run(
            ["kubectl", "version", "--client"],
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def normalizar_etiqueta(etiqueta: str) -> str:
    """Un SHA pelado se convierte a la etiqueta que publica H11.1.

    Se acepta el SHA sin prefijo porque es lo que uno tiene a mano -sale de
    `git rev-parse HEAD`- y obligar a recordar el prefijo es una fuente de
    despliegues fallidos que no dicen por que.
    """
    return f"sha-{etiqueta}" if re.fullmatch(r"[0-9a-f]{40}", etiqueta) else etiqueta


def fijar_etiqueta(arbol: Path, entorno: str, etiqueta: str) -> None:
    """Reescribe el bloque `images:` de la base, en una COPIA del arbol.

    POR QUE SE COPIA EL ARBOL PRIMERO

    Reescribir el kustomization del arbol de trabajo dejaria el repositorio
    sucio despues de cada despliegue, y tarde o temprano alguien commitea la
    etiqueta de una corrida.

    POR QUE UN SOLO CAMINO, Y NO `kustomize` CUANDO ESTA DISPONIBLE

    La primera version usaba `kustomize edit set image` si el binario existia, y
    una sustitucion de texto si no. **Fallo en la primera corrida del CD** con
    `Missing kustomization file`: al portar el guion de bash a Python se perdio
    el `cd` al directorio del overlay, y `subprocess` hereda el directorio
    actual, que es la raiz del repositorio.

    Lo que convierte el descuido en algo peor: **en las maquinas del equipo no
    hay `kustomize` instalado, asi que el camino que se probaba era el otro.**
    En el runner si esta, y tomo el que nunca se habia ejecutado.

    Dos caminos de los que solo uno se recorre son un defecto esperando. Queda
    **uno solo**: la sustitucion de texto, que es la que se ejecuta en las dos
    partes y esta comprobada abajo.
    """
    kustomization = arbol / "base" / "kustomization.yaml"
    texto = kustomization.read_text(encoding="utf-8")
    nuevo = re.sub(r"newTag: .*", f"newTag: {etiqueta}", texto)
    kustomization.write_text(nuevo, encoding="utf-8")

    # SE COMPRUEBA QUE LA SUSTITUCION OCURRIO.
    #
    # Una sustitucion que no encuentra su patron no falla: no cambia nada. Sin
    # esta comprobacion, un cambio de formato en el kustomization dejaria el
    # despliegue en `latest` **en silencio**, que es la peor clase de defecto
    # que puede tener un despliegue automatico.
    if f"newTag: {etiqueta}" not in nuevo:
        raise SystemExit(
            f"ERROR: no se pudo fijar la etiqueta {etiqueta} en el kustomization.\n"
            f"       Cambio el formato de {kustomization.name}?"
        )


def main() -> int:
    p = argparse.ArgumentParser(description="Despliega un entorno de GeoGuardian.")
    p.add_argument("entorno", choices=ENTORNOS)
    p.add_argument("etiqueta", nargs="?", default="latest")
    args = p.parse_args()

    if not hay_kubectl():
        print(
            "ERROR: no se puede ejecutar 'kubectl'.\n"
            "\n"
            "  winget install -e --id Kubernetes.kubectl\n"
            "\n"
            "Y abri una consola nueva: winget no actualiza el PATH de la que ya\n"
            "esta abierta, que es el motivo por el que 'ya lo instale' y\n"
            "'command not found' conviven tan seguido.\n",
            file=sys.stderr,
        )
        return 3

    etiqueta = normalizar_etiqueta(args.etiqueta)
    namespace = f"geoguardian-{args.entorno}"
    print(f"\nDesplegando a {namespace} con la etiqueta {etiqueta}\n")

    with tempfile.TemporaryDirectory() as carpeta:
        arbol = Path(carpeta) / "k8s"
        shutil.copytree(K8S, arbol)
        fijar_etiqueta(arbol, args.entorno, etiqueta)

        correr("kubectl", "apply", "-k", str(arbol / "local" / args.entorno))

        # `rollout status` CON LIMITE DE TIEMPO ES LO QUE CONVIERTE ESTO EN UNA
        # COMPROBACION.
        #
        # Sin el, `kubectl apply` devuelve exito en cuanto la API acepta el
        # objeto -o sea, siempre- y el despliegue diria que funciono aunque
        # ningun pod arranque.
        print("\nEsperando a que converja...\n")
        for objeto, limite in (
            ("statefulset/postgis", "240s"),
            ("deployment/api", "240s"),
            ("deployment/visor", "180s"),
        ):
            correr("kubectl", "-n", namespace, "rollout", "status", objeto, f"--timeout={limite}")

    print()
    correr("kubectl", "-n", namespace, "get", "pods", "-o", "wide")
    print(
        f"\nListo. Para verlo desde la maquina:\n"
        f"  kubectl -n {namespace} port-forward svc/visor 8080:80\n"
        f"  kubectl -n {namespace} port-forward svc/api   8000:8000\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
