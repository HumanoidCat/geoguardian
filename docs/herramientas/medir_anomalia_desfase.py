"""
Mide cuanto cuesta la suposicion de que la serie arranca en enero.

Por que existe: `ProcesadorSenales.anomalia` no recibe fechas, asi que la
implementacion no tiene forma de saber a que mes corresponde cada posicion y
supone que la serie es mensual y empieza en enero.

Esta herramienta cuantifica el error en vez de argumentarlo, para que la
solicitud **SC-06** se apoye en numeros. Es el mismo procedimiento que sostuvo
SC-02 y la decision D-19.

COMO SE MIDE

Se toma una serie mensual con el regimen del Pacifico Norte y se la desfasa un
numero de meses, como pasaria si la carga empezara en cualquier mes que no sea
enero. Despues se comparan:

- `anomalia`, la del contrato, que supone enero.
- `anomalia_con_fechas`, que usa el mes real.

La diferencia entre ambas es el error que introduce la suposicion.

La serie es sintetica y reproduce el regimen del canton. No son datos de
Tilaran: lo que se mide es una propiedad del metodo, no el clima.

Uso:  python docs/herramientas/medir_anomalia_desfase.py
"""

from __future__ import annotations

import logging
import random
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.senales.anomalias import (  # noqa: E402
    CalculadorAnomalias,
    anomalia_con_fechas,
    normales_por_mes,
)

SEMILLA = 20260820
ANIOS = 30

# Precipitacion media mensual en mm, regimen del Pacifico Norte. Enero a
# diciembre. Estacion seca de diciembre a abril, maximo en setiembre-octubre.
MEDIA_MENSUAL = [8, 5, 6, 30, 190, 230, 160, 190, 300, 320, 110, 25]


def generar(anio_inicio: int, mes_inicio: int) -> tuple[list[float | None], list[date]]:
    """Serie mensual sintetica que arranca en el mes indicado."""
    rnd = random.Random(SEMILLA)
    serie: list[float | None] = []
    fechas: list[date] = []

    anio, mes = anio_inicio, mes_inicio
    for _ in range(ANIOS * 12):
        media = MEDIA_MENSUAL[mes - 1]
        serie.append(round(rnd.gammavariate(4.0, media / 4.0), 1))
        fechas.append(date(anio, mes, 1))
        mes += 1
        if mes > 12:
            mes = 1
            anio += 1

    return serie, fechas


def main() -> int:
    # `anomalia` avisa de la suposicion de enero en cada llamada, que es lo
    # correcto para quien la usa. Aqui se llama doce veces a proposito y el
    # aviso taparia la tabla, asi que se silencia **solo en esta herramienta**.
    # Es la advertencia la que se mide, no la que se ignora.
    logging.getLogger("backend.senales.anomalias").setLevel(logging.ERROR)

    calculador = CalculadorAnomalias()

    # La normal se calcula siempre bien, porque `normales_por_mes` si recibe
    # fechas. El problema no es la normal: es contra cual se compara cada valor.
    serie_base, fechas_base = generar(1991, 1)
    normales = normales_por_mes(serie_base, fechas_base)

    print(f"\nSerie sintetica: {ANIOS} anios mensuales, regimen del Pacifico Norte")
    print("Normal climatologica por mes, en mm:")
    print("  " + "  ".join(f"{m:>2}:{normales[m]:>6.1f}" for m in sorted(normales)))
    print()

    print("Error que introduce suponer que la serie arranca en enero")
    print(f"  {'desfase':>8} {'err. medio':>12} {'err. maximo':>13} {'peor mes':>10}")

    for desfase in range(12):
        mes_inicio = (desfase % 12) + 1
        serie, fechas = generar(1991, mes_inicio)

        del_contrato = calculador.anomalia(serie, normales)
        correcta = anomalia_con_fechas(serie, fechas, normales)

        errores = [
            abs(a - b)
            for a, b in zip(del_contrato, correcta, strict=True)
            if a is not None and b is not None
        ]
        if not errores:
            continue

        medio = sum(errores) / len(errores)
        maximo = max(errores)
        peor = fechas[errores.index(maximo)].month

        marca = "  <- sin desfase" if desfase == 0 else ""
        print(f"  {desfase:>8} {medio:>12.1f} {maximo:>13.1f} {peor:>10}{marca}")

    # ------------------------------------------- cuanto vale la anomalia real
    serie, fechas = generar(1991, 1)
    correcta = anomalia_con_fechas(serie, fechas, normales)
    magnitud = [abs(v) for v in correcta if v is not None]
    tipica = sum(magnitud) / len(magnitud)

    print(f"\nMagnitud tipica de una anomalia real: {tipica:.1f} mm")
    print(
        "\nLectura: si el error medio de un desfase supera la magnitud tipica de\n"
        "la anomalia, la suposicion no degrada el resultado: lo reemplaza por\n"
        "otra cosa. El numero que sale ya no mide desviacion respecto de lo\n"
        "normal, mide la diferencia entre dos meses del calendario.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
