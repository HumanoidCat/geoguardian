"""
Genera el reporte de calidad de datos. Historia H1.5, rubrica OE1.

Corre sobre el volcado de `crudo.medicion_diaria` y produce las cuatro secciones
del reporte:

1. **Completitud por fuente**, con su interpretacion. La seccion mas corta y la
   mas importante.
2. **Atipicos**, separando valores fisicamente imposibles de extremos
   estadisticos.
3. **Sesgos**, empezando por el espacial.
4. **Trazabilidad de la procedencia**, que con D-15 dejo de ser homogenea.

El cruce de los extremos contra el catalogo de eventos historicos de H4.3 usa
`docs/investigacion/catalogo-eventos.csv`, que si esta en el repositorio.

USO

    python docs/herramientas/generar_reporte_calidad.py --csv mediciones.csv

El volcado no se versiona: `.gitignore` excluye los datos. Conviene guardar su
suma de verificacion junto al reporte para saber sobre que version se corrio.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from backend.calidad.reporte_calidad import (  # noqa: E402
    FUENTE_DE,
    Serie,
    completitud,
    cruzar_con_catalogo,
    extremos_estadisticos,
    fuera_de_rango_fisico,
    variacion_espacial,
)

CATALOGO = RAIZ / "docs" / "investigacion" / "catalogo-eventos.csv"

VARIABLES = [
    "precipitacion_mm",
    "temp_max_c",
    "temp_min_c",
    "temp_media_c",
    "humedad_relativa_pct",
    "viento_ms",
    "radiacion_mj_m2",
]

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


def leer_mediciones(ruta: Path) -> tuple[list[Serie], dict[tuple[str, str], int]]:
    """Series por distrito y variable, mas el conteo de filas por procedencia."""
    fechas: dict[str, list[date]] = defaultdict(list)
    valores: dict[tuple[str, str], list[float | None]] = defaultdict(list)
    procedencia: dict[tuple[str, str], int] = defaultdict(int)

    with ruta.open(encoding="utf-8", newline="") as f:
        for fila in csv.DictReader(f):
            distrito = fila["codigo_distrito"].strip()
            fechas[distrito].append(date.fromisoformat(fila["fecha"].strip()))

            for variable in VARIABLES:
                crudo = fila.get(variable, "").strip()
                valores[(distrito, variable)].append(None if crudo == "" else float(crudo))

            procedencia[
                (
                    fila.get("fuente_precipitacion", "?").strip(),
                    fila.get("fuente_resto", "?").strip(),
                )
            ] += 1

    series = [
        Serie(distrito, variable, fechas[distrito], vs)
        for (distrito, variable), vs in valores.items()
    ]

    return series, dict(procedencia)


def leer_catalogo() -> list[tuple[str, date, date | None]]:
    """Eventos de H4.3 como (distrito, inicio, fin)."""
    if not CATALOGO.exists():
        return []

    eventos: list[tuple[str, date, date | None]] = []
    with CATALOGO.open(encoding="utf-8", newline="") as f:
        for fila in csv.DictReader(f):
            fin = fila["fecha_fin"].strip()
            eventos.append(
                (
                    fila["codigo_distrito"].strip(),
                    date.fromisoformat(fila["fecha_inicio"].strip()),
                    date.fromisoformat(fin) if fin else None,
                )
            )
    return eventos


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, required=True, help="volcado de crudo.medicion_diaria")
    args = p.parse_args()

    if not args.csv.exists():
        print(f"ERROR: no existe {args.csv}")
        return 1

    series, procedencia = leer_mediciones(args.csv)
    if not series:
        print("ERROR: el volcado no tiene filas")
        return 1

    distritos = sorted({s.codigo_distrito for s in series})
    dias = len(series[0].fechas)

    print("\nREPORTE DE CALIDAD DE DATOS · H1.5")
    print(f"Volcado: {args.csv}")
    print(f"{len(distritos)} distritos x {dias} dias\n")

    # ------------------------------------------------ 1. completitud
    print("=" * 72)
    print("1. COMPLETITUD, POR FUENTE")
    print("=" * 72)
    print("\nLa completitud no es un numero del proyecto: es un numero por fuente.\n")

    print(f"  {'variable':<22} {'fuente':<8} {'esperado':>9} {'presente':>9} {'% falta':>8}")
    for r in completitud(series):
        print(
            f"  {r.variable:<22} {r.fuente:<8} {r.total_esperado:>9} "
            f"{r.total_presente:>9} {r.pct_faltantes:>8.2f}"
        )

    sin_faltantes = [r for r in completitud(series) if r.pct_faltantes == 0]
    if sin_faltantes:
        print(f"\n  {len(sin_faltantes)} de {len(VARIABLES)} variables con 0 % de faltantes.")
        print("  " + sin_faltantes[0].observaciones)

    # --------------------------------------------------- 2. atipicos
    print("\n" + "=" * 72)
    print("2. ATIPICOS")
    print("=" * 72)

    imposibles = fuera_de_rango_fisico(series)
    print(f"\n  Fuera de rango fisico (ERROR DE DATO): {len(imposibles)}")
    for distrito, variable, fecha, valor in imposibles[:10]:
        print(f"    {distrito} {variable} {fecha} = {valor}")
    if len(imposibles) > 10:
        print(f"    ... y {len(imposibles) - 10} mas")

    solo_lluvia = [s for s in series if s.variable == "precipitacion_mm"]
    extremos = extremos_estadisticos(solo_lluvia)
    print(f"\n  Extremos estadisticos de precipitacion (CANDIDATOS A EVENTO REAL): {len(extremos)}")

    eventos = leer_catalogo()
    if eventos:
        coincidentes, total = cruzar_con_catalogo(extremos, eventos)
        pct = 100 * coincidentes / total if total else 0.0
        print(f"\n  Cruce contra el catalogo de H4.3 ({len(eventos)} filas de evento):")
        print(
            f"    extremos que coinciden con un evento catalogado: {coincidentes} de {total}"
            f" ({pct:.2f} %)"
        )
        print(
            "\n    Un extremo que coincide con un evento documentado NO es un dato\n"
            "    sospechoso: es la confirmacion de que la serie capta lo que ocurrio."
        )
    else:
        print(f"\n  AVISO: no se encontro el catalogo en {CATALOGO}")

    # ----------------------------------------------------- 3. sesgos
    print("\n" + "=" * 72)
    print("3. SESGOS")
    print("=" * 72)
    print("\n  Variacion espacial: % de dias con al menos dos valores distintos\n")

    variacion = variacion_espacial(series)
    for variable in VARIABLES:
        if variable not in variacion:
            continue
        pct = variacion[variable]
        marca = "  <- no distingue distritos" if pct == 0 else ""
        print(f"    {variable:<22} {FUENTE_DE.get(variable, '?'):<8} {pct:>7.2f} %{marca}")

    sin_variacion = [v for v, pct in variacion.items() if pct == 0]
    if sin_variacion:
        print(
            f"\n    {len(sin_variacion)} variables con 0 % de variacion espacial.\n"
            "    Un dato que no cambia entre ocho puntos separados por kilometros\n"
            "    no fue observado en ninguno de los ocho. Ver la incidencia I-05."
        )

    print(
        "\n  Incertidumbre no reportada: un producto de malla trae error de\n"
        "  estimacion en cada celda y no lo entrega junto al valor. No se puede\n"
        "  medir desde aqui, pero no es cero, y pertenece a limitaciones."
    )

    # ----------------------------------------------- 4. procedencia
    print("\n" + "=" * 72)
    print("4. TRAZABILIDAD DE LA PROCEDENCIA")
    print("=" * 72)
    print("\n  Con D-15 la procedencia dejo de ser homogenea.\n")

    for (fuente_precip, fuente_resto), filas in sorted(procedencia.items()):
        print(f"    precipitacion={fuente_precip}, resto={fuente_resto}: {filas} filas")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
