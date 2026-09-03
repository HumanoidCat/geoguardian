"""
Toma un respaldo logico de la base. Dueno: Cesar. Historia H1.10, issue #42.

POR QUE INVOCA pg_dump DENTRO DEL CONTENEDOR

    docker compose exec -T db pg_dump ...

y no un `pg_dump` instalado en la maquina. La razon es de version, no de
comodidad: **pg_dump se niega a volcar un servidor mas nuevo que el**, y la
version del cliente local depende de lo que cada quien tenga instalado. Usando el
binario del propio contenedor, cliente y servidor son la misma version por
construccion, y esta historia no agrega una dependencia nueva a la maquina de
nadie. Es la misma razon por la que el proyecto corre PostgreSQL en Docker.

FORMATO `custom`

`-Fc`. Se comprime solo, permite restaurar selectivamente, y sobre todo permite
**comprobar el contenido sin restaurar**, con `pg_restore --list`. El formato
plano solo gana en que se lee con un editor, y para eso esta `--list`.

LO QUE ESTE RESPALDO NO CONTIENE, Y ES A PROPOSITO

**Los roles.** `pg_dump` de una base no los incluye: los roles son del cluster,
no de la base. El volcado trae los GRANT de `003_seguridad_roles.sql` apuntando a
`geoguardian_api` y `geoguardian_etl`, y en un cluster nuevo esos roles no
existen.

`pg_dumpall --roles-only` si los exportaria, **con sus contrasenas cifradas
dentro**, y eso convierte al respaldo en un secreto. `003` ya esta en el
repositorio y es reproducible, asi que restaurar exige correrlo antes y no hay
nada que ganar exportando contrasenas. Ver los criterios de aceptacion, CA-8.

USO

    python -m basedatos.respaldar
    python -m basedatos.respaldar --etiqueta antes-de-h3.4
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[1]
DIRECTORIO_RESPALDOS = RAIZ / "basedatos" / "respaldos"
SERVICIO = "db"


class ErrorRespaldo(Exception):
    """No se pudo tomar el respaldo."""


def configuracion() -> dict[str, str]:
    """Los mismos valores por omision que declara docker-compose.yml."""
    load_dotenv()
    contrasena = os.getenv("POSTGRES_PASSWORD")
    if not contrasena:
        raise ErrorRespaldo(
            "Falta POSTGRES_PASSWORD en .env. Es la unica variable de conexion "
            "sin valor por defecto, igual que en conexion.py."
        )
    return {
        "base": os.getenv("POSTGRES_DB") or "geoguardian",
        "usuario": os.getenv("POSTGRES_USER") or "geoguardian",
        "contrasena": contrasena,
    }


def en_contenedor(
    orden: list[str], contrasena: str, entrada: bytes | None = None
) -> subprocess.CompletedProcess:
    """
    Corre una orden dentro del contenedor de la base y devuelve su salida cruda.

    `-T` desactiva la asignacion de terminal: sin eso, la salida binaria del
    volcado se corrompe. La contrasena va por `-e` y no en la linea de comandos
    de pg_dump, para que no aparezca en la lista de procesos del contenedor.
    """
    completa = [
        "docker",
        "compose",
        "exec",
        "-T",
        "-e",
        f"PGPASSWORD={contrasena}",
        SERVICIO,
        *orden,
    ]
    return subprocess.run(
        completa,
        cwd=RAIZ,
        input=entrada,
        capture_output=True,
        check=False,
    )


# Marcas con las que el CLI de Docker avisa que no pudo hablar con el demonio.
# No son errores del comando que se le pidio correr: el comando ni siquiera
# arranco. Distinguirlos importa porque el mensaje manda a buscar en un lado o
# en el otro, y equivocarse cuesta el rato entero.
MARCAS_DOCKER_CAIDO = (
    "docker api",
    "cannot connect to the docker daemon",
    "the docker daemon is not running",
    "is the docker daemon running",
    "no such file or directory",
    "el sistema no puede encontrar el archivo especificado",
)


def docker_responde() -> tuple[bool, str]:
    """Comprueba que el demonio de Docker este arriba antes de culpar a otro."""
    try:
        resultado = subprocess.run(
            ["docker", "compose", "ps", "--quiet"],
            cwd=RAIZ,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return False, "No se encontro el ejecutable `docker` en el PATH."

    if resultado.returncode == 0:
        return True, ""

    error = resultado.stderr.decode("utf-8", "replace").strip()
    if any(m in error.lower() for m in MARCAS_DOCKER_CAIDO):
        return False, (
            "El demonio de Docker no responde. **No es un fallo de la base ni de "
            "pg_dump: no llegaron a ejecutarse.**\n"
            "Abri Docker Desktop, espera a que diga que esta corriendo, y repeti.\n\n"
            f"Lo que dijo docker: {error}"
        )
    return False, f"`docker compose ps` fallo:\n{error}"


def nombre_del_archivo(etiqueta: str | None) -> str:
    momento = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    sufijo = f"-{etiqueta}" if etiqueta else ""
    return f"geoguardian-{momento}{sufijo}.dump"


def respaldar(etiqueta: str | None = None) -> Path:
    arriba, motivo = docker_responde()
    if not arriba:
        raise ErrorRespaldo(motivo)

    cfg = configuracion()
    DIRECTORIO_RESPALDOS.mkdir(parents=True, exist_ok=True)
    destino = DIRECTORIO_RESPALDOS / nombre_del_archivo(etiqueta)

    print(f"Base:    {cfg['base']}")
    print(f"Destino: {destino.relative_to(RAIZ)}")
    print("Volcando con pg_dump -Fc dentro del contenedor...")

    resultado = en_contenedor(
        ["pg_dump", "-Fc", "--no-owner", "-U", cfg["usuario"], "-d", cfg["base"]],
        cfg["contrasena"],
    )

    if resultado.returncode != 0:
        raise ErrorRespaldo(
            "pg_dump fallo dentro del contenedor.\n"
            f"{resultado.stderr.decode('utf-8', 'replace').strip()}\n"
            "Comproba que el servicio este arriba: docker compose ps"
        )

    if not resultado.stdout:
        raise ErrorRespaldo(
            "pg_dump termino en cero y no devolvio ni un byte. "
            "Un respaldo vacio que se da por bueno es peor que uno que falla."
        )

    destino.write_bytes(resultado.stdout)

    suma = hashlib.sha256(resultado.stdout).hexdigest()
    print(f"\nListo. {len(resultado.stdout):,} bytes")
    print(f"SHA-256: {suma}")
    print("\nPara restaurarlo:")
    print(f"    python -m basedatos.restaurar {destino.relative_to(RAIZ)}")
    return destino


def main() -> int:
    analizador = argparse.ArgumentParser(
        description="Toma un respaldo logico de la base en basedatos/respaldos/."
    )
    analizador.add_argument(
        "--etiqueta",
        help="Texto que se agrega al nombre del archivo, para reconocerlo despues.",
    )
    argumentos = analizador.parse_args()

    try:
        respaldar(argumentos.etiqueta)
    except ErrorRespaldo as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
