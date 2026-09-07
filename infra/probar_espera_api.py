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

POR QUE `kubectl` SE REEMPLAZA CON UNA FUNCION DE BASH Y NO CON UN ARCHIVO

La primera version escribia un `kubectl` falso en una carpeta y la ponia al
frente del PATH. **En Windows no funciona**, y fallo en la maquina del PM:
`Path.chmod` no concede el bit de ejecucion en NTFS, asi que bash encontraba el
archivo y no podia ejecutarlo -codigo 126-, y el bucle se quedaba dando vueltas
hasta el limite del subproceso.

Una funcion de bash declarada antes del bloque hace lo mismo sin depender del
bit de ejecucion, del PATH ni de que las variables de entorno crucen a bash.
Todo lo que la prueba necesita viaja dentro del propio guion.

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

No necesita cluster, ni red, ni Docker. Necesita `bash`: en Windows, el de Git.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ACCION = RAIZ / ".github" / "acciones" / "preparar-cluster" / "action.yml"
PASO = "Crear el cluster"

# Tope duro del subproceso. Es mayor que cualquier limite que usen los casos, y
# esta para que un bucle que no sepa rendirse falle rapido y con un mensaje
# claro, en vez de colgar la corrida.
TOPE_SEGUNDOS = 60


def preambulo(umbral: int, limite: int) -> str:
    """
    Declara el doble de `kubectl` y el limite, dentro del mismo guion.

    `umbral` es en que llamada empieza a contestar que si. Con un numero enorme,
    no contesta nunca.

    EL CONTADOR VIVE EN UNA VARIABLE, NO EN UN ARCHIVO. La version anterior lo
    guardaba en un archivo temporal, y eso metia la ruta de Windows dentro de un
    guion que puede ejecutarse en WSL -donde `C:/Users/...` no existe-. Como la
    funcion se invoca en el mismo shell que el bucle, una variable basta.
    """
    return f"""
export ESPERA_MAXIMA_API={limite}
UMBRAL={umbral}
CUENTA=0

kubectl() {{
  CUENTA=$((CUENTA + 1))
  if [ "$CUENTA" -ge "$UMBRAL" ]; then
    echo "Kubernetes control plane is running at https://0.0.0.0:6443"
    return 0
  fi
  echo "E0000 memcache.go:381] no server API group list" >&2
  echo "Error from server (ServiceUnavailable): the server is unable to handle the request" >&2
  return 1
}}
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


def guion_de(bloque: str, umbral: int, limite: int) -> str:
    return preambulo(umbral, limite) + "\n" + bloque


def correr(bloque: str, umbral: int, limite: int) -> tuple[int, str]:
    """
    Ejecuta el guion por la entrada estandar, EN BYTES Y NO EN TEXTO.

    Las dos decisiones estan medidas contra la maquina del PM, donde el `bash`
    del PATH es el de WSL:

      * **Por la entrada estandar y no como argumento.** Con `bash -c` este
        guion -decenas de lineas, con acentos y comillas angulares- no terminaba
        nunca, mientras `bash -c 'echo HOLA'` contestaba en 0,1 s.
      * **En bytes y no en texto.** Con `text=True`, Python codifica con la
        codificacion local -cp1252 en Windows, no UTF-8- y ademas traduce cada
        salto de linea a CRLF. bash recibia un guion en CRLF y salia con
        codigo 2: error de sintaxis. Codificando a UTF-8 a mano no hay
        traduccion de ninguna clase.

    Es la cuarta vuelta de la misma leccion: lo que se le pasa a otro proceso
    cruza una frontera, y cada frontera tiene sus reglas. La forma de no
    tropezar con ellas es no dejar que nadie traduzca por uno.
    """
    try:
        proceso = subprocess.run(
            ["bash", "-s"],
            input=guion_de(bloque, umbral, limite).encode("utf-8"),
            capture_output=True,
            timeout=TOPE_SEGUNDOS,
        )
    except subprocess.TimeoutExpired:
        # No es un fallo de la prueba: es el bucle que no supo rendirse.
        return 124, f"El bloque no termino en {TOPE_SEGUNDOS}s."
    salida = (proceso.stdout + proceso.stderr).decode("utf-8", errors="replace")
    return proceso.returncode, salida


def caso(
    nombre: str,
    bloque: str,
    umbral: int,
    limite: int,
    codigo_esperado: int,
    dice: str | None = None,
) -> bool:
    codigo, salida = correr(bloque, umbral, limite)

    fallas = []
    if codigo != codigo_esperado:
        fallas.append(f"salio con {codigo}, se esperaba {codigo_esperado}")
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
    if shutil.which("bash") is None:
        print("No encuentro `bash`. En Windows lo trae Git. Sin el, esta prueba no puede correr,")
        print("y no da por buenos los criterios que no pudo ejecutar.")
        return 2

    bloque = neutralizar_k3d(bloque_del_paso())

    # Para diagnosticar cuando la prueba falla por el entorno y no por el guion:
    # deja el texto exacto que se ejecuta, para poder correrlo a mano.
    if "--guardar" in sys.argv:
        destino = RAIZ / "guion-generado.sh"
        destino.write_text(guion_de(bloque, 1, 30), encoding="utf-8", newline="\n")
        print(f"Escrito {destino}. Corrrelo con:  bash {destino.name}")
        return 0

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
