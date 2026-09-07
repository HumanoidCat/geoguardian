"""
Prueba del reintento de `basedatos.conexion.conectar()` contra un PostgreSQL real.

POR QUE VIVE EN infra/ Y NO EN basedatos/

`conexion.py` es de Cesar. H11.6 tiene una excepcion de propiedad escrita en
`docs/07-propiedad-archivos.md` para tocar **solo `conectar()`**. Dejar esta
prueba en `basedatos/` -o en `backend/tests/`, que es de Luna- haria falta una
segunda excepcion para una historia que solo necesita una. Es el mismo criterio
con el que el verificador de H1.6 quedo junto al extractor.

QUE COMPRUEBA, Y QUE ES LO QUE IMPORTA

`conectar()` reintenta hasta noventa segundos mientras la base termina de
arrancar. Desde H11.6 **no** reintenta ante los fallos en los que el servidor ya
contesto -la base no existe, el rol no existe, la contrasena es incorrecta-,
porque esperar no los arregla.

Lo que importa de esta prueba **no** es que esos fallos salgan rapido: eso se
consigue rompiendo el reintento entero. Lo que importa es que el caso transitorio
-el puerto cerrado- **siga esperando**, porque es lo que la Definition of Done de
H1.3 exige y es lo unico que esta correccion puede romper sin que nadie lo note.
Por eso ese caso exige un tiempo MINIMO, no solo un maximo.

Cada caso comprueba tres cosas: la clase de la excepcion, cuanto tardo, y que
dice el mensaje. Un cambio que acierte el tiempo y mande a mirar al lugar
equivocado no esta bien: esa fue justamente la queja que abrio esto.

COMO SE CORRE

Necesita un PostgreSQL al que se pueda conectar. Por omision usa lo que haya en
`.env` -es decir, el de `docker compose up -d db`-:

    docker compose up -d db
    python -m infra.probar_reintento_conexion

Para apuntarlo a otro, se ponen las variables de siempre en la sesion:

    $env:POSTGRES_HOST_LOCAL = "..."   # PowerShell
    $env:POSTGRES_PORT       = "..."
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from dotenv import load_dotenv  # noqa: E402

from basedatos.conexion import ErrorConexion, conectar  # noqa: E402

load_dotenv()

# El destino sale del entorno, no de constantes: la prueba tiene que poder
# correrse contra la base local de docker compose y contra cualquier otra.
BASE = {
    "POSTGRES_HOST_LOCAL": os.getenv("POSTGRES_HOST_LOCAL", "localhost"),
    "POSTGRES_PORT": os.getenv("POSTGRES_PORT") or "5432",
    "POSTGRES_DB": os.getenv("POSTGRES_DB") or "geoguardian",
    "POSTGRES_USER": os.getenv("POSTGRES_USER") or "geoguardian",
    "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD") or "",
}

# Un puerto sin nadie escuchando, para el caso transitorio.
PUERTO_CERRADO = "5999"

# Espera corta a proposito: la prueba mide la FORMA del comportamiento, no los
# noventa segundos de produccion. Si se sube, la prueba tarda mas y no dice mas.
ESPERA = 20.0
ESPERA_CORTA = 8.0


def correr(
    nombre: str,
    cambios: dict[str, str],
    espera: float,
    minimo: float,
    tope: float,
    dice: str | None = None,
    no_dice: str | None = None,
    clase_esperada: str = "ErrorConexion",
) -> bool:
    entorno = dict(BASE)
    entorno.update(cambios)
    os.environ.update(entorno)

    inicio = time.monotonic()
    mensaje = ""
    try:
        conexion = conectar(espera_maxima=espera)
    except ErrorConexion as error:
        clase, mensaje = "ErrorConexion", str(error)
    except Exception as error:  # noqa: BLE001
        clase, mensaje = type(error).__name__, str(error)
    else:
        clase = "conecto"
        conexion.close()
    transcurrido = time.monotonic() - inicio

    fallas = []
    if clase != clase_esperada:
        fallas.append(f"salio como {clase}, se esperaba {clase_esperada}")
    if not (minimo <= transcurrido <= tope):
        fallas.append(f"tardo {transcurrido:.1f}s, se esperaba entre {minimo:.0f} y {tope:.0f}")
    if dice and dice not in mensaje:
        fallas.append(f"el mensaje NO dice {dice!r}")
    if no_dice and no_dice in mensaje:
        fallas.append(f"el mensaje dice {no_dice!r} y no deberia")

    print(f"  {'ok  ' if not fallas else 'MAL '} {nombre:30} {transcurrido:5.1f}s  {clase}")
    for falla in fallas:
        print(f"       -> {falla}")
    return not fallas


def main() -> int:
    print("Reintento de conexion · H11.6 sobre H1.3")
    print(f"Base de referencia: {BASE['POSTGRES_HOST_LOCAL']}:{BASE['POSTGRES_PORT']}\n")

    resultados = []

    print("PERMANENTES · el servidor contesto. Tienen que fallar YA, no en 20 segundos")
    resultados.append(
        correr(
            "base inexistente",
            {"POSTGRES_DB": "no_existe_nunca"},
            ESPERA,
            0,
            3,
            dice="Revisa el nombre de la base",
            no_dice="docker compose",
        )
    )
    resultados.append(
        correr(
            "rol inexistente",
            {"POSTGRES_USER": "fantasma_que_no_existe"},
            ESPERA,
            0,
            3,
            dice="esperar no lo arregla",
        )
    )

    print("\nTRANSITORIO · el servidor no contesto. TIENE que esperar todo")
    print("  (este es el caso que importa: si deja de esperar, se rompe H1.3)")
    resultados.append(
        correr(
            "puerto cerrado",
            {"POSTGRES_PORT": PUERTO_CERRADO},
            ESPERA,
            ESPERA - 1,
            ESPERA + 6,
            dice="docker compose ps",
        )
    )

    print("\nLA PISTA depende de donde este la base")
    resultados.append(
        correr(
            "host remoto que no resuelve",
            {"POSTGRES_HOST_LOCAL": "no.existe.invalido"},
            ESPERA_CORTA,
            ESPERA_CORTA - 1,
            ESPERA_CORTA + 6,
            dice="no es local",
            no_dice="docker compose",
        )
    )

    print("\nY conecta cuando tiene que conectar")
    resultados.append(correr("la base de verdad", {}, ESPERA, 0, 5, clase_esperada="conecto"))

    print(f"\n{sum(resultados)} de {len(resultados)} comprobaciones")
    return 0 if all(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
