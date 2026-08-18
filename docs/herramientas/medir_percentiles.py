"""
Mide la diferencia entre el percentil del ETCCDI y el percentil sobre acumulado
de 72 h.

Por que existe: `contratos/enums.py` define el umbral de lluvia intensa sobre el
acumulado de 72 h y dice que "corresponde a los indices R95p y R99p del ETCCDI".
Pero el ETCCDI define esos indices sobre la precipitacion **diaria** de los dias
humedos. Son dos cantidades distintas.

Esta herramienta cuantifica cuanto difieren, para que la decision de como
nombrarlas en el documento IEEE se tome con numeros.

La serie es sintetica y reproduce el regimen del Pacifico Norte: estacion seca
de diciembre a abril, lluviosa de mayo a noviembre. No son datos de Tilaran, y
lo que se mide es una relacion entre dos definiciones, no el clima del canton.

Uso:  python docs/herramientas/medir_percentiles.py
"""

from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.senales.percentiles import (  # noqa: E402
    UMBRAL_DIA_HUMEDO_MM,
    percentil_acumulado,
    percentil_dias_humedos,
)

SEMILLA = 20260818
INICIO = date(1991, 1, 1)
FIN = date(2020, 12, 31)
MESES_SECOS = (12, 1, 2, 3, 4)


def generar_serie() -> tuple[list[float | None], list[date]]:
    """Precipitacion diaria sintetica del periodo base 1991-2020."""
    rnd = random.Random(SEMILLA)
    fechas: list[date] = []
    serie: list[float | None] = []

    actual = INICIO
    while actual <= FIN:
        if actual.month in MESES_SECOS:
            valor = 0.0 if rnd.random() < 0.92 else round(rnd.gammavariate(1.5, 2.0), 1)
        else:
            valor = 0.0 if rnd.random() < 0.35 else round(rnd.gammavariate(1.8, 9.0), 1)
        serie.append(valor)
        fechas.append(actual)
        actual += timedelta(days=1)

    return serie, fechas


def main() -> int:
    serie, fechas = generar_serie()

    presentes = [v for v in serie if v is not None]
    humedos = [v for v in presentes if v >= UMBRAL_DIA_HUMEDO_MM]

    print(f"\nSerie sintetica: {INICIO} a {FIN}, {len(serie)} dias")
    print(
        f"Dias humedos (>= {UMBRAL_DIA_HUMEDO_MM} mm): {len(humedos)} "
        f"({100 * len(humedos) / len(presentes):.1f} %)"
    )
    print(f"Dias secos: {len(presentes) - len(humedos)}\n")

    # ------------------------------------------- las dos definiciones
    p95_diario = percentil_dias_humedos(serie, fechas, 95)
    p99_diario = percentil_dias_humedos(serie, fechas, 99)
    p95_acum = percentil_acumulado(serie, fechas, 95, ventana_dias=3)
    p99_acum = percentil_acumulado(serie, fechas, 99, ventana_dias=3)

    print("Umbrales, en mm")
    print(f"{'':34} {'P95':>10} {'P99':>10}")
    print(f"  {'ETCCDI, diario de dias humedos':32} {p95_diario:>10.2f} {p99_diario:>10.2f}")
    print(f"  {'acumulado de 72 h':32} {p95_acum:>10.2f} {p99_acum:>10.2f}")
    print(
        f"  {'razon acumulado / diario':32} "
        f"{p95_acum / p95_diario:>10.2f} {p99_acum / p99_diario:>10.2f}"
    )

    # ------------------------------- que pasa si se confunden ambos
    acumulados: list[float] = []
    for i in range(2, len(serie)):
        trozo = serie[i - 2 : i + 1]
        if any(v is None for v in trozo):
            continue
        acumulados.append(sum(v for v in trozo if v is not None))

    con_umbral_correcto = sum(1 for a in acumulados if a > p99_acum)
    con_umbral_diario = sum(1 for a in acumulados if a > p99_diario)

    print(f"\nDias clasificados como riesgo alto sobre {len(acumulados)} ventanas de 72 h")
    print(
        f"  usando el umbral de acumulado (correcto) : {con_umbral_correcto:>6}"
        f"  ({100 * con_umbral_correcto / len(acumulados):.2f} %)"
    )
    print(
        f"  usando el umbral diario del ETCCDI       : {con_umbral_diario:>6}"
        f"  ({100 * con_umbral_diario / len(acumulados):.2f} %)"
    )

    if con_umbral_correcto:
        veces = con_umbral_diario / con_umbral_correcto
        print(
            f"\n  Confundir las definiciones multiplicaria por {veces:.1f} "
            f"los dias declarados en riesgo alto."
        )

    # ------------------------------------- efecto de incluir los secos
    todos_los_dias = [v for v in presentes]
    todos_ordenados = sorted(todos_los_dias)
    pos = int(0.95 * (len(todos_ordenados) - 1))
    p95_con_secos = todos_ordenados[pos]

    print("\nEfecto de NO excluir los dias secos del percentil diario")
    print(f"  P95 solo con dias humedos (ETCCDI) : {p95_diario:>8.2f} mm")
    print(f"  P95 con todos los dias             : {p95_con_secos:>8.2f} mm")
    if p95_diario:
        caida = 100 * (1 - p95_con_secos / p95_diario)
        print(f"  El umbral caeria un {caida:.1f} %.")

    print(
        "\nLectura: el percentil sobre acumulado de 72 h y el indice R95p del\n"
        "ETCCDI no son la misma cantidad. Los dos son legitimos, pero el\n"
        "documento no deberia llamar R95p al primero sin aclararlo.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
