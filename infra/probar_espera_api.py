"""
Prueba la espera a la API de Kubernetes del paso «Crear el cluster». I-42.

QUE PRUEBA, Y CONTRA QUE

No prueba una copia del guion: **lee el bloque `run:` del paso «Crear el
cluster» de `.github/acciones/preparar-cluster/action.yml` y lo ejecuta**. Una
copia se desincroniza en silencio, que es el mismo motivo por el que esa accion
existe como accion compuesta en vez de repetida tres veces en `cd.yml` (I-21).

Lo unico que se neutraliza es la linea de `k3d cluster create`: levantar un
cluster de verdad en cada corrida del CI costaria dos minutos y no probaria nada
de lo que esta prueba mira. Queda dicho aca para que nadie lea «se ejecuta el
paso» como «se ejecuta entero».

`kubectl` se reemplaza por un doble que contesta que no un numero fijo de veces
y despues contesta que si. Es la carrera de I-42 reproducida sin cluster.

LOS TRES CASOS, Y POR QUE EL TERCERO ES EL QUE IMPORTA

    1. la API contesta al primer intento      -> sale bien, sin esperar
    2. la API contesta al cuarto intento      -> sale bien, y DICE cuanto espero
    3. la API no contesta nunca               -> sale MAL, y dice cuanto espero

El tercero es el que justifica la prueba. Un bucle de espera mal escrito -uno
que se rinda en silencio, o que salga con codigo 0 al agotar el limite- pasa los
dos primeros casos sin problema. Fue justo esa clase de defecto la que dejo pasar
CD #11: `k3d` decia que si y nadie preguntaba de nuevo.

El caso 2 exige ademas que el mensaje traiga el numero de segundos. Un fallo que
no dice cuanto espero no distingue «tarda mas de lo previsto» de «no arranca», y
las dos cosas piden acciones distintas.

COMO SE CORRE

    python -m infra.probar_espera_api

No necesita cluster, ni red, ni Docker.
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ACCION = RAIZ / ".github" / "acciones" / "preparar-cluster" / "action.yml"
PASO = "Crear el cluster"

# El doble de kubectl. Cuenta sus llamadas en un archivo y falla mientras el
# contador no llegue a UMBRAL. Con UMBRAL enorme, no contesta nunca.
DOBLE = """#!/usr/bin/env bash
cuenta=$(cat "$CONTADOR" 2>/dev/null || echo 0)
cuenta=$((cuenta + 1))
echo "$cuenta" > "$CONTADOR"
if [ "$cuenta" -ge "$UMBRAL" ]; then
  echo "Kubernetes control plane is running at https://0.0.0.0:6443"
  exit 0
fi
echo "E0000 memcache.go:381] \\"Couldn't get current server API group list\\"" >&2
echo "Error from server (ServiceUnavailable): the server is currently unable to handle the request" >&2
exit 1
"""


def bloque_del_paso() -> str:
    """
    Saca el `run:` del paso «Crear el cluster», tal como esta en el archivo.

    Se busca por el nombre del paso y no por numero de linea: renumerar el
    archivo no puede romper esta prueba en silencio.
    """
    texto = ACCION.read_text(encoding="utf-8")
    inicio = texto.find(f"- name: {PASO}")
    if inicio < 0:
        raise SystemExit(f"No encuentro el paso «{PASO}» en {ACCION}")

    resto = texto[inicio:]
    marca = "run: |\n"
    desde = resto.find(marca)
    if desde < 0:
        raise SystemExit(f"El paso «{PASO}» no tiene un bloque `run: |`")
    cuerpo = resto[desde + len(marca) :]

    lineas: list[str] = []
    for linea in cuerpo.splitlines():
        if linea.strip() and not linea.startswith("        "):
            break  # se acabo el bloque indentado
        lineas.append(linea[8:] if linea.startswith("        ") else linea)
    return "\n".join(lineas)


def neutralizar_k3d(bloque: str) -> str:
    """Quita la creacion real del cluster, y falla si ya no estaba."""
    if not re.search(r"^k3d cluster create ", bloque, re.MULTILINE):
        raise SystemExit(
            "El paso ya no crea el cluster con `k3d cluster create`. "
            "Esta prueba asumia que si: revisala antes de tocar nada mas."
        )
    return re.sub(
        r"^k3d cluster create .*$",
        ": # `k3d cluster create` neutralizado por la prueba",
        bloque,
        flags=re.MULTILINE,
    )


def correr(bloque: str, umbral: int, limite: int) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as carpeta:
        binarios = Path(carpeta) / "bin"
        binarios.mkdir()
        doble = binarios / "kubectl"
        doble.write_text(DOBLE, encoding="utf-8")
        doble.chmod(0o755)

        entorno = dict(os.environ)
        entorno.update(
            {
                "PATH": f"{binarios}{os.pathsep}{os.environ.get('PATH', '')}",
                "CONTADOR": str(Path(carpeta) / "cuenta"),
                "UMBRAL": str(umbral),
                "ESPERA_MAXIMA_API": str(limite),
            }
        )
        return subprocess.run(
            ["bash", "-c", bloque], capture_output=True, text=True, env=entorno, timeout=180
        )


def caso(
    nombre: str,
    bloque: str,
    umbral: int,
    limite: int,
    codigo_esperado: int,
    dice: str | None = None,
) -> bool:
    proceso = correr(bloque, umbral, limite)
    salida = proceso.stdout + proceso.stderr

    fallas = []
    if proceso.returncode != codigo_esperado:
        fallas.append(f"salio con {proceso.returncode}, se esperaba {codigo_esperado}")
    if dice and dice not in salida:
        fallas.append(f"la salida NO dice {dice!r}")

    print(f"  {'ok  ' if not fallas else 'MAL '} {nombre}")
    for falla in fallas:
        print(f"       -> {falla}")
    return not fallas


def main() -> int:
    if not ACCION.exists():
        print(f"No encuentro {ACCION}. Corre esto desde la raiz del repositorio.")
        return 2

    bloque = neutralizar_k3d(bloque_del_paso())

    print("Espera a la API de Kubernetes · I-42")
    print(f"Bloque leido de {ACCION.relative_to(RAIZ)}, paso «{PASO}»\n")

    resultados = [
        caso(
            "contesta al primer intento: sale bien",
            bloque,
            umbral=1,
            limite=30,
            codigo_esperado=0,
            dice="tras 0s de espera",
        ),
        caso(
            "contesta al cuarto intento: sale bien Y dice cuanto espero",
            bloque,
            umbral=4,
            limite=30,
            codigo_esperado=0,
            dice="tras 9s de espera",
        ),
        # El que importa. Sin este, un bucle que se rinde en silencio pasa.
        caso(
            "no contesta nunca: sale MAL y dice cuanto espero",
            bloque,
            umbral=10_000,
            limite=6,
            codigo_esperado=1,
            dice="no contesto en 6s",
        ),
    ]

    print(f"\n{sum(resultados)} de {len(resultados)} comprobaciones")
    return 0 if all(resultados) else 1


if __name__ == "__main__":
    raise SystemExit(main())
