"""
Comprueba que la imagen de trabajos programados lleva todo lo que la cadena usa.

POR QUE EXISTE
==============

`infra/docker/trabajos.Dockerfile` copia archivos sueltos y filtra
`requirements.txt` a siete paquetes. Las dos listas se escribieron leyendo el
codigo, y **leyendo se me escaparon dos**: `scipy`, que entra por una linea
dentro de `backend/senales/spi.py`, tres saltos por debajo del punto de entrada,
y `pydantic`, que entra por `contratos/esquemas.py`.

Una imagen a la que le falta un paquete **no falla al construirse**. Falla en la
primera corrida programada, que por definicion es de madrugada y sin nadie
mirando, y lo unico que queda es una fila que nunca se escribio.

Este guion recorre el grafo de imports de verdad, desde los tres puntos de
entrada, y compara lo que encuentra contra lo que el Dockerfile promete. No lee
opiniones: lee `ast`.

QUE COMPRUEBA
=============

  1. Cada modulo propio que la cadena alcanza cae dentro de lo que el Dockerfile
     copia. Si alguien agrega un import a un modulo nuevo, esto lo dice.
  2. Cada paquete de terceros que la cadena importa esta en el filtro del
     Dockerfile. Si alguien importa una biblioteca nueva, esto lo dice.
  3. El numero del `test` del Dockerfile coincide con el largo de su propio
     filtro, y ese filtro encuentra esa cantidad de lineas en requirements.txt.
  4. Se prueba a si mismo antes de mirar nada, con casos que tienen que fallar.

No usa ninguna biblioteca externa: solo la biblioteca estandar.

Uso, desde la raiz del repositorio:

    python infra/verificar_trabajos.py

Sale con codigo 1 si algo no cuadra.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DOCKERFILE = RAIZ / "infra" / "docker" / "trabajos.Dockerfile"

# Los tres comandos que corre el CMD de la imagen, en el mismo orden.
ENTRADAS = (
    "backend.modelado.generar_etiquetas",
    "backend.modelado.generar_caracteristicas",
    "backend.modelado.estimar_riesgo",
)

PROPIOS = ("backend", "basedatos", "contratos")

fallos: list[str] = []


def exigir(condicion: bool, descripcion: str, detalle: str = "") -> None:
    marca = "OK   " if condicion else "FALLA"
    print(f"  {marca} {descripcion}{('  ' + detalle) if detalle else ''}")
    if not condicion:
        fallos.append(descripcion)


# --------------------------------------------------------------------------- #
# Lo que el Dockerfile promete                                                  #
# --------------------------------------------------------------------------- #


def copiado_por_el_dockerfile(texto: str) -> list[str]:
    """Los prefijos de modulo que las lineas COPY dejan dentro de la imagen."""
    prefijos: list[str] = []
    for linea in texto.splitlines():
        if not linea.startswith("COPY ") or "--from=" in linea:
            continue
        partes = linea.split()[1:-1]  # sin COPY y sin el destino
        for origen in partes:
            if origen == "requirements.txt":
                continue
            limpio = origen.rstrip("/").removesuffix(".py")
            prefijos.append(limpio.replace("/", "."))
    return prefijos


def filtro_del_dockerfile(texto: str) -> tuple[set[str], int | None]:
    """Los paquetes del `grep -E` y el numero que exige el `test`."""
    grep = re.search(r"grep -E '\^\(([^)]+)\)'", texto)
    prueba = re.search(r'test "\$\(wc -l < [^)]+\)" -eq (\d+)', texto)
    paquetes = set(grep.group(1).split("|")) if grep else set()
    return paquetes, int(prueba.group(1)) if prueba else None


# --------------------------------------------------------------------------- #
# El grafo de imports                                                           #
# --------------------------------------------------------------------------- #


def ruta_de(modulo: str) -> Path | None:
    directo = RAIZ / (modulo.replace(".", "/") + ".py")
    if directo.exists():
        return directo
    paquete = RAIZ / modulo.replace(".", "/") / "__init__.py"
    return paquete if paquete.exists() else None


def recorrer(entradas: tuple[str, ...]) -> tuple[set[str], set[str]]:
    """Devuelve (modulos propios alcanzados, paquetes de terceros importados)."""
    vistos: set[str] = set()
    terceros: set[str] = set()

    def visitar(modulo: str) -> None:
        if modulo in vistos:
            return
        vistos.add(modulo)
        ruta = ruta_de(modulo)
        if ruta is None:
            return
        arbol = ast.parse(ruta.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom) and nodo.module:
                base = nodo.module.split(".")[0]
                if base in PROPIOS:
                    if ruta_de(nodo.module):
                        visitar(nodo.module)
                    else:
                        # `from paquete import modulo`
                        for alias in nodo.names:
                            visitar(f"{nodo.module}.{alias.name}")
                elif nodo.level == 0 and base not in sys.stdlib_module_names:
                    terceros.add(base)
            elif isinstance(nodo, ast.Import):
                for alias in nodo.names:
                    base = alias.name.split(".")[0]
                    if base in PROPIOS:
                        visitar(alias.name)
                    elif base not in sys.stdlib_module_names:
                        terceros.add(base)

    for entrada in entradas:
        visitar(entrada)
    return vistos, terceros


# El nombre que se importa no siempre es el nombre que se instala.
NOMBRE_EN_REQUIREMENTS = {
    "sklearn": "scikit-learn",
    "dotenv": "python-dotenv",
}


def autoprueba() -> None:
    """Casos que TIENEN que fallar, antes de mirar el repositorio de verdad."""
    print("El propio verificador sabe fallar:")
    copias = copiado_por_el_dockerfile(
        "COPY contratos/ ./contratos/\nCOPY backend/api/repositorio_postgres.py ./backend/api/\n"
    )
    exigir(copias == ["contratos", "backend.api.repositorio_postgres"], "lee las lineas COPY")
    paquetes, numero = filtro_del_dockerfile(
        "    grep -E '^(numpy|scipy)' /tmp/r.txt > /tmp/t.txt; \\\n"
        '    test "$(wc -l < /tmp/t.txt)" -eq 2; \\\n'
    )
    exigir(paquetes == {"numpy", "scipy"} and numero == 2, "lee el filtro y su numero")
    exigir(ruta_de("backend.modelado.estimar_riesgo") is not None, "encuentra un modulo que existe")
    exigir(ruta_de("backend.modelado.no_existe") is None, "no inventa un modulo que no existe")
    print()


def main() -> None:
    autoprueba()

    if not DOCKERFILE.exists():
        raise SystemExit(f"ERROR: no existe {DOCKERFILE}")
    texto = DOCKERFILE.read_text(encoding="utf-8")
    prefijos = copiado_por_el_dockerfile(texto)
    paquetes, numero = filtro_del_dockerfile(texto)

    modulos, terceros = recorrer(ENTRADAS)
    print(f"La cadena alcanza {len(modulos)} modulos propios y {len(terceros)} paquetes externos.")

    print("\nTodo modulo propio que la cadena usa entra en la imagen:")
    fuera = sorted(m for m in modulos if not any(m == p or m.startswith(p + ".") for p in prefijos))
    exigir(not fuera, "ningun modulo queda fuera de las lineas COPY", ", ".join(fuera))

    print("\nTodo paquete externo que la cadena importa entra en el filtro:")
    for importado in sorted(terceros):
        instalable = NOMBRE_EN_REQUIREMENTS.get(importado, importado)
        exigir(instalable in paquetes, f"{importado} esta en el filtro", f"como «{instalable}»")

    print("\nEl filtro y su comprobacion dicen lo mismo:")
    exigir(
        numero == len(paquetes),
        "el `test` cuenta lo mismo que el filtro",
        f"{numero} contra {len(paquetes)}",
    )
    requisitos = (RAIZ / "requirements.txt").read_text(encoding="utf-8").splitlines()
    encontradas = [linea for linea in requisitos if any(linea.startswith(p) for p in paquetes)]
    exigir(
        len(encontradas) == numero,
        "requirements.txt trae exactamente esas lineas",
        f"{len(encontradas)} encontradas",
    )

    if fallos:
        print(f"\n{len(fallos)} verificaciones fallaron:")
        for fallo in fallos:
            print(f"  - {fallo}")
        sys.exit(1)

    print("\nTodas las verificaciones pasaron.")


if __name__ == "__main__":
    main()
