"""
Mide cuanto se desvia el SPI de ajuste unico respecto del SPI por mes calendario.

Por que existe: se escribio para sostener la solicitud de cambio SC-02, cuando
la firma del contrato no recibia fechas y el ajuste solo podia ser unico para
toda la serie.

**SC-02 fue aprobada.** El contrato v1.3.0 incorpora el parametro `meses` por
la decision D-19, y `backend/senales/spi.py` ya hace el ajuste por mes
calendario. La herramienta se conserva porque sigue cumpliendo dos funciones:

1. **Cuantifica lo que se gana**, comparando las dos formas de llamar al mismo
   codigo. Sirve de regresion: si alguien rompiera el ajuste por mes, las dos
   salidas volverian a parecerse.
2. **Es la evidencia de la decision.** D-19 se tomo con estos numeros y conviene
   que sigan siendo reproducibles.

Las dos salidas provienen de la misma implementacion, la de
`backend/senales/spi.py`. Esta herramienta ya no tiene su propia copia de la
logica: lo que mide es el codigo que se entrega.

La serie es sintetica y reproduce el regimen del Pacifico Norte de Costa Rica:
estacion seca marcada de diciembre a abril y maximos en setiembre y octubre. No
son datos reales del canton, y no pretenden serlo: lo que se mide es una
propiedad del metodo, no del clima de Tilaran.

Uso:  python docs/herramientas/medir_spi_por_mes.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.senales.spi import CalculadorSPI  # noqa: E402

SEMILLA = 20260818
ANIOS = 35
VENTANA = 3  # SPI-3, que es el que usa el umbral de sequia del proyecto

# Precipitacion media mensual en mm, regimen del Pacifico Norte. Enero a
# diciembre. Estacion seca de diciembre a abril, maximo en setiembre-octubre.
MEDIA_MENSUAL = [8, 5, 6, 30, 190, 230, 160, 190, 300, 320, 110, 25]
UMBRAL_SEQUIA_MODERADA = -1.0  # contratos/enums.py


def generar_serie(anios: int = ANIOS) -> tuple[list[float | None], list[int]]:
    """Serie mensual sintetica y la lista de meses calendario de cada posicion."""
    rnd = random.Random(SEMILLA)
    serie: list[float | None] = []
    meses: list[int] = []

    for _ in range(anios):
        for mes in range(12):
            media = MEDIA_MENSUAL[mes]
            # Gamma con forma 2: sesgo positivo, como la precipitacion real.
            valor = rnd.gammavariate(2.0, media / 2.0) if media > 0 else 0.0
            serie.append(round(valor, 1))
            meses.append(mes + 1)

    return serie, meses


def _promedio(valores: list[float]) -> float:
    return sum(valores) / len(valores) if valores else float("nan")


def main() -> int:
    serie, meses = generar_serie()

    # Las dos salidas provienen de la MISMA implementacion, la de
    # backend/senales/spi.py. Desde D-19 el ajuste por mes vive alli y esta
    # herramienta ya no necesita su propia copia: lo que se mide es el codigo
    # que se entrega, no una reimplementacion parecida.
    calculador = CalculadorSPI()
    unico = calculador.spi(serie, VENTANA)
    por_mes = calculador.spi(serie, VENTANA, meses)

    comunes = [i for i in range(len(serie)) if unico[i] is not None and por_mes[i] is not None]

    print(f"\nSerie sintetica: {ANIOS} anios, {len(serie)} meses, SPI-{VENTANA}")
    print(f"Posiciones con SPI calculado en ambos metodos: {len(comunes)}\n")

    # ------------------------------------------------------- por estacion
    secos = {12, 1, 2, 3, 4}
    i_secos = [i for i in comunes if meses[i] in secos]
    i_lluviosos = [i for i in comunes if meses[i] not in secos]

    print("SPI medio por estacion (deberia rondar 0 en las dos: es un indice de anomalia)")
    print(f"{'':22} {'ajuste unico':>14} {'ajuste por mes':>16}")
    print(
        f"  {'estacion seca':20} "
        f"{_promedio([unico[i] for i in i_secos]):>14.2f} "  # type: ignore[arg-type]
        f"{_promedio([por_mes[i] for i in i_secos]):>16.2f}"  # type: ignore[arg-type]
    )
    print(
        f"  {'estacion lluviosa':20} "
        f"{_promedio([unico[i] for i in i_lluviosos]):>14.2f} "  # type: ignore[arg-type]
        f"{_promedio([por_mes[i] for i in i_lluviosos]):>16.2f}"  # type: ignore[arg-type]
    )

    # ------------------------------------------- declaraciones de sequia
    sequia_unico = [i for i in comunes if unico[i] <= UMBRAL_SEQUIA_MODERADA]  # type: ignore[operator]
    sequia_por_mes = [i for i in comunes if por_mes[i] <= UMBRAL_SEQUIA_MODERADA]  # type: ignore[operator]
    coinciden = set(sequia_unico) & set(sequia_por_mes)

    print(f"\nMeses declarados en sequia (SPI <= {UMBRAL_SEQUIA_MODERADA})")
    print(f"  ajuste unico   : {len(sequia_unico):>4}")
    print(f"  ajuste por mes : {len(sequia_por_mes):>4}")
    print(f"  coinciden      : {len(coinciden):>4}")

    if sequia_unico:
        en_seca = sum(1 for i in sequia_unico if meses[i] in secos)
        print(
            f"\n  De los {len(sequia_unico)} meses que el ajuste unico declara en sequia, "
            f"{en_seca} caen en estacion seca ({100 * en_seca / len(sequia_unico):.1f} %)."
        )
    if sequia_por_mes:
        en_seca = sum(1 for i in sequia_por_mes if meses[i] in secos)
        print(
            f"  De los {len(sequia_por_mes)} del ajuste por mes, "
            f"{en_seca} caen en estacion seca ({100 * en_seca / len(sequia_por_mes):.1f} %)."
        )

    # ------------------------------------------------------- correlacion
    if len(comunes) > 1:
        x = [unico[i] for i in comunes]
        y = [por_mes[i] for i in comunes]
        mx, my = _promedio(x), _promedio(y)  # type: ignore[arg-type]
        num = sum((a - mx) * (b - my) for a, b in zip(x, y, strict=True))  # type: ignore[operator]
        dx = sum((a - mx) ** 2 for a in x) ** 0.5  # type: ignore[operator]
        dy = sum((b - my) ** 2 for b in y) ** 0.5  # type: ignore[operator]
        if dx and dy:
            print(f"\nCorrelacion entre ambos metodos: {num / (dx * dy):.3f}")

    print(
        "\nLectura: si el SPI de ajuste unico separa la estacion seca de la "
        "lluviosa,\nno esta midiendo anomalia sino estacionalidad.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
