"""
Analisis espectral de la precipitacion de Tilaran. Historia H2.2.

Corre sobre el volcado real de H1.1 y produce la interpretacion fisica que pide
la historia. Los criterios de aceptacion se escribieron **antes** de ver los
datos y estan en
`docs/evidencias/senales-y-sistemas/H2.2-criterios-aceptacion.md`.

QUE HACE

1. Calcula el espectro de la precipitacion diaria de cada uno de los ocho
   distritos, por separado.
2. Compara la amplitud del ciclo semianual contra la del anual.
3. Construye un **modelo nulo** y mide contra el.

POR QUE HACE FALTA EL MODELO NULO

Un pico semianual no demuestra por si solo que exista el veranillo. Cualquier
senal periodica que no sea una sinusoide genera armonicos en 1/2, 1/3 y 1/4 de
su periodo, **aunque no haya ningun fenomeno fisico en esas frecuencias**. Y el
ciclo anual de la lluvia no es una sinusoide: es una estacion seca casi plana y
una lluviosa con forma de meseta.

El modelo nulo es una serie con un solo ciclo anual, con esa forma de meseta y
**sin ninguna pausa de mitad de estacion**. Su razon semianual/anual es la que
produce la forma por si sola. El veranillo se declara detectado solo si los
datos reales la superan claramente.

Aqui la serie sintetica si es la herramienta correcta: su papel no es sustituir
al dato, es aportar el valor de referencia contra el que se compara.

SOBRE QUE COLUMNA

Solo `precipitacion_mm`, que viene de CHIRPS. Las variables de POWER son
identicas en los ocho distritos porque la celda de MERRA-2 cubre el canton
entero (D-15, incidencia I-05): un espectro sobre ellas seria el de una sola
serie repetida ocho veces.

USO

    python docs/herramientas/analizar_espectro_lluvia.py --csv mediciones.csv

El CSV es el volcado de `crudo.medicion_diaria`. No se versiona: `.gitignore`
excluye los datos.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.senales.espectro import (  # noqa: E402
    DIAS_POR_ANO,
    FRECUENCIA_ANUAL,
    FRECUENCIA_SEMIANUAL,
    AnalizadorEspectral,
    casillero_mas_cercano,
    picos_principales,
    razon_semianual_anual,
)

DISTRITOS = {
    "50801": "Tilaran",
    "50802": "Quebrada Grande",
    "50803": "Tronadora",
    "50804": "Santa Rosa",
    "50805": "Libano",
    "50806": "Tierras Morenas",
    "50807": "Arenal",
    "50808": "Cabeceras",
}

# Dia del anio en que arranca y termina la estacion lluviosa en la vertiente del
# Pacifico. Se usan solo para dar forma al modelo nulo, no para analizar nada.
INICIO_LLUVIOSA = 121  # 1 de mayo
FIN_LLUVIOSA = 334  # 30 de noviembre


def leer_csv(ruta: Path) -> dict[str, list[tuple[date, float | None]]]:
    """Precipitacion diaria por distrito, ordenada por fecha."""
    por_distrito: dict[str, list[tuple[date, float | None]]] = defaultdict(list)

    with ruta.open(encoding="utf-8", newline="") as f:
        for fila in csv.DictReader(f):
            crudo = fila["precipitacion_mm"].strip()
            valor = None if crudo == "" else float(crudo)
            por_distrito[fila["codigo_distrito"].strip()].append(
                (date.fromisoformat(fila["fecha"].strip()), valor)
            )

    for serie in por_distrito.values():
        serie.sort()

    return dict(por_distrito)


def modelo_nulo(dias: int) -> list[float | None]:
    """
    Un solo ciclo anual, no sinusoidal, **sin pausa de mitad de estacion**.

    Estacion seca plana en cero y lluviosa con forma de meseta, con bordes
    suavizados para que la transicion no sea un escalon perfecto. La amplitud es
    arbitraria: lo que se mide es una razon entre componentes, no un valor
    absoluto.
    """
    serie: list[float | None] = []

    for d in range(dias):
        dia_del_anio = d % int(DIAS_POR_ANO)

        if INICIO_LLUVIOSA <= dia_del_anio <= FIN_LLUVIOSA:
            # Meseta con bordes suaves: medio seno sobre el ancho de la estacion.
            fraccion = (dia_del_anio - INICIO_LLUVIOSA) / (FIN_LLUVIOSA - INICIO_LLUVIOSA)
            valor = 10.0 * math.sin(math.pi * fraccion) ** 0.35
        else:
            valor = 0.0

        serie.append(valor)

    return serie


def _fmt(valor: float | None, ancho: int = 8, decimales: int = 2) -> str:
    return " " * ancho if valor is None else f"{valor:>{ancho}.{decimales}f}"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, required=True, help="volcado de crudo.medicion_diaria")
    args = p.parse_args()

    if not args.csv.exists():
        print(f"ERROR: no existe {args.csv}")
        return 1

    series = leer_csv(args.csv)
    analizador = AnalizadorEspectral()

    print(f"\nVolcado: {args.csv}")
    print(f"Distritos encontrados: {len(series)}")
    total = sum(len(s) for s in series.values())
    print(f"Filas: {total}\n")

    if not series:
        print("ERROR: el volcado no tiene filas")
        return 1

    # ------------------------------------------------- modelo nulo, primero
    dias = max(len(s) for s in series.values())
    f_nulo, m_nulo = analizador.espectro(modelo_nulo(dias), 1.0)
    razon_nula = razon_semianual_anual(f_nulo, m_nulo)

    print("MODELO NULO: un solo ciclo anual, sin pausa de mitad de estacion")
    print(f"  razon semianual/anual que produce la forma por si sola: {razon_nula:.3f}")
    print(
        "  Cualquier distrito que no supere claramente este valor NO aporta\n"
        "  evidencia de veranillo: su pico semianual es el armonico de la forma.\n"
    )

    # ------------------------------------------------------- por distrito
    print("PRECIPITACION DIARIA POR DISTRITO (CHIRPS)")
    print(
        f"  {'codigo':<7} {'distrito':<17} {'dias':>6} {'anual':>9} "
        f"{'semianual':>10} {'razon':>7} {'veranillo':>10}"
    )

    razones: dict[str, float] = {}
    fallos: list[str] = []

    for codigo in sorted(series):
        valores = [v for _, v in series[codigo]]
        nombre = DISTRITOS.get(codigo, "?")

        faltantes = sum(1 for v in valores if v is None)
        if faltantes:
            fallos.append(f"{codigo}: {faltantes} faltantes, no se puede transformar")
            continue

        frecuencias, magnitudes = analizador.espectro(valores, 1.0)

        i_anual = casillero_mas_cercano(frecuencias, FRECUENCIA_ANUAL)
        i_semi = casillero_mas_cercano(frecuencias, FRECUENCIA_SEMIANUAL)
        dominante = max(range(1, len(magnitudes)), key=lambda i: magnitudes[i])

        razon = razon_semianual_anual(frecuencias, magnitudes)
        razones[codigo] = razon  # type: ignore[assignment]

        if dominante != i_anual:
            periodo = 1 / frecuencias[dominante] if frecuencias[dominante] else float("inf")
            fallos.append(
                f"{codigo}: el pico dominante no es el anual, esta en {periodo:.1f} dias. "
                "Ver la tabla de criterios: puede ser tendencia, solapamiento o "
                "artefacto del producto"
            )

        marca = "si" if razon and razon_nula and razon > 1.5 * razon_nula else "no"
        print(
            f"  {codigo:<7} {nombre:<17} {len(valores):>6} "
            f"{_fmt(magnitudes[i_anual], 9)} {_fmt(magnitudes[i_semi], 10)} "
            f"{_fmt(razon, 7, 3)} {marca:>10}"
        )

    # --------------------------------------------------------- homogeneidad
    if razones:
        menor, mayor = min(razones.values()), max(razones.values())
        print(f"\nRango de la razon entre distritos: {menor:.3f} a {mayor:.3f}")
        if menor > 0:
            print(f"  El mayor es {mayor / menor:.2f} veces el menor.")

    # ------------------------------------------------- picos por distrito
    print("\nPICOS PRINCIPALES POR DISTRITO, en dias de periodo")
    for codigo in sorted(series):
        valores = [v for _, v in series[codigo]]
        if any(v is None for v in valores):
            continue
        frecuencias, magnitudes = analizador.espectro(valores, 1.0)
        picos = picos_principales(frecuencias, magnitudes, cuantos=4, separacion_minima=5)
        detalle = "  ".join(f"{periodo:>7.1f}d ({mag:.2f})" for periodo, mag in picos)
        print(f"  {codigo} {DISTRITOS.get(codigo, '?'):<17} {detalle}")

    # ------------------------------------------------------------- avisos
    if fallos:
        print(f"\nAVISOS ({len(fallos)}):")
        for f in fallos:
            print(f"  - {f}")
        print(
            "\n  Antes de interpretar cualquiera de estos como clima, revisar la\n"
            "  tabla 'Que resultado haria dudar del metodo' de los criterios."
        )
    else:
        print("\nSin avisos: el ciclo anual domina en todos los distritos.")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
