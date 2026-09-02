"""
Calcula el puntaje SUS de uno o varios cuestionarios. Historia H9.2a.

USO

    python docs/herramientas/calcular_sus.py 4 2 5 1 4 2 5 2 4 1

    python docs/herramientas/calcular_sus.py --archivo respuestas.txt

El archivo lleva un cuestionario por linea, diez numeros separados por espacios.
Las lineas en blanco y las que empiezan con `#` se ignoran, para poder anotar de
quien es cada una sin romper nada.

POR QUE SE CALCULA EJECUTANDO

El SUS puntea distinto los items pares y los impares. Hacerlo a mano para cinco
participantes son cincuenta restas alternadas, y un error ahi no lo detecta
nadie: el resultado sigue estando entre 0 y 100 y sigue pareciendo un puntaje.

La regla vive en `backend/calidad/sus.py` y esta congelada por
`backend/tests/test_sus.py`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from backend.calidad.sus import interpretar, promediar, puntuar  # noqa: E402


def _leer_archivo(ruta: Path) -> list[list[int]]:
    cuestionarios = []
    for numero, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), start=1):
        limpia = linea.split("#")[0].strip()
        if not limpia:
            continue
        try:
            cuestionarios.append([int(v) for v in limpia.split()])
        except ValueError:
            raise ValueError(f"Linea {numero}: no son numeros separados por espacios") from None
    return cuestionarios


def main(argumentos: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description="Puntaje SUS de H9.2a")
    analizador.add_argument("respuestas", nargs="*", type=int, help="diez numeros de 1 a 5")
    analizador.add_argument("--archivo", type=Path, help="un cuestionario por linea")
    opciones = analizador.parse_args(argumentos)

    if opciones.archivo and opciones.respuestas:
        print("ERROR: o se pasan las respuestas o se pasa --archivo, no las dos.")
        return 1

    try:
        if opciones.archivo:
            cuestionarios = _leer_archivo(opciones.archivo)
        elif opciones.respuestas:
            cuestionarios = [opciones.respuestas]
        else:
            analizador.print_help()
            return 1

        if not cuestionarios:
            print("ERROR: no hay ningun cuestionario que puntuar.")
            return 1

        puntajes = [puntuar(c) for c in cuestionarios]
    except ValueError as error:
        print(f"ERROR: {error}")
        return 1

    print()
    for numero, (respuestas, puntaje) in enumerate(zip(cuestionarios, puntajes, strict=True), 1):
        print(f"  Cuestionario {numero}: {' '.join(str(r) for r in respuestas)}")
        print(f"    aportes : {' '.join(f'{a:.0f}' for a in puntaje.aporte_por_item)}")
        print(f"    {interpretar(puntaje.valor)}")
        print()

    if len(puntajes) > 1:
        promedio, aviso = promediar(puntajes)
        print(f"  PROMEDIO: {promedio:.1f} / 100")
        print(f"  {aviso}")
        print()
        print("  Individuales: " + ", ".join(f"{p.valor:.1f}" for p in puntajes))
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
