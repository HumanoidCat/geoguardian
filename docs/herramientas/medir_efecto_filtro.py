"""
Mide cuanto mueve el filtro de ruido los percentiles de precipitacion.

Es la herramienta que sostiene la decision **D-17**. La pregunta que responde no
es "cual filtro suaviza mejor" sino otra: **si la serie de precipitacion se
filtra antes de calcular los indices, cuanto cambia lo que el proyecto declara
como evento extremo.**

Se escribio porque la alternativa era decidirlo por argumento. Los dos argumentos
suenan razonables —"el ruido instrumental hay que quitarlo" y "un pico de lluvia
no es ruido"— y no se puede elegir entre ellos leyendo. Se puede midiendo.

Uso:

    python docs/herramientas/medir_efecto_filtro.py

Sale con codigo 0 siempre: es una herramienta de medicion, no un verificador. No
corre en el CI.

**Sobre los datos.** Mide sobre una serie sintetica, no sobre Tilaran: H1.1 sigue
abierta y no hay series descargadas. La serie se genera con el modelo estandar de
un generador estocastico de clima —ocurrencia de Bernoulli con probabilidad
mensual, intensidad gamma— parametrizado con el regimen de la vertiente pacifica
de Guanacaste: estacion seca marcada de diciembre a abril y maximo en septiembre
y octubre.

Eso basta para lo que se quiere medir, porque el efecto que se busca depende de
la forma de la distribucion —muchos ceros y una cola larga— y no de los valores
exactos de Tilaran. **Cuando existan las series de CHIRPS hay que volver a
correrlo sobre ellas**, y esta anotado en la seccion de medicion de D-17.
"""

from __future__ import annotations

import datetime
import random
import statistics
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# Regimen de lluvia de la vertiente pacifica de Guanacaste.
# Probabilidad de dia con lluvia y escala de la intensidad, por mes.
PROBABILIDAD_DIA_LLUVIOSO = {
    1: 0.10, 2: 0.06, 3: 0.06, 4: 0.15, 5: 0.45, 6: 0.55,
    7: 0.50, 8: 0.55, 9: 0.65, 10: 0.70, 11: 0.45, 12: 0.20,
}  # fmt: skip

ESCALA_INTENSIDAD_MM = {
    1: 2.0, 2: 1.5, 3: 1.5, 4: 3.0, 5: 7.0, 6: 8.5,
    7: 7.5, 8: 8.5, 9: 11.0, 10: 12.0, 11: 7.0, 12: 3.5,
}  # fmt: skip

# Forma de la gamma. Por debajo de 1 la distribucion tiene moda en cero y cola
# larga, que es como se comporta la lluvia diaria en el tropico.
FORMA_GAMMA = 0.7

# Umbral de dia humedo del ETCCDI. R95p y R99p se calculan sobre los dias que lo
# superan, no sobre todos los dias del anio.
DIA_HUMEDO_MM = 1.0

VENTANA_ACUMULADO_H = 3  # 72 horas, el umbral de lluvia intensa del proyecto
VENTANA_FILTRO = 7  # el valor por defecto de backend/senales/filtros.py
ANIOS = 35  # 1991-2025, la ventana de descarga acordada en D-15


def construir_filtro():
    """
    El filtro real del proyecto si esta disponible; si no, el equivalente.

    Se prefiere `backend.senales.filtros` porque lo que interesa medir es el
    efecto del codigo que se va a usar, no el de una reimplementacion parecida.
    La reserva existe para que la herramienta siga corriendo sobre una copia del
    repositorio donde la historia H2.1 todavia no este integrada.
    """
    try:
        from backend.senales.filtros import FiltroSavitzkyGolay

        return FiltroSavitzkyGolay().filtrar_ruido, "backend/senales/filtros.py (H2.1)"
    except ImportError:
        from scipy.signal import savgol_filter

        def filtrar(serie, ventana=VENTANA_FILTRO):
            return list(savgol_filter([float(v) for v in serie], ventana, 2))

        return filtrar, "scipy.signal.savgol_filter (reserva: H2.1 no esta integrada)"


def serie_diaria(anios: int = ANIOS, semilla: int = 42) -> list[float]:
    """Precipitacion diaria sintetica desde el 1 de enero de 1991."""
    rnd = random.Random(semilla)
    dia = datetime.date(1991, 1, 1)
    fin = datetime.date(1991 + anios, 1, 1)
    serie: list[float] = []

    while dia < fin:
        if rnd.random() < PROBABILIDAD_DIA_LLUVIOSO[dia.month]:
            escala = ESCALA_INTENSIDAD_MM[dia.month] / FORMA_GAMMA
            serie.append(round(rnd.gammavariate(FORMA_GAMMA, escala), 1))
        else:
            serie.append(0.0)
        dia += datetime.timedelta(days=1)

    return serie


def acumulado(serie: list[float], dias: int = VENTANA_ACUMULADO_H) -> list[float]:
    """Suma movil de `dias`, sin rellenar el arranque."""
    return [sum(serie[i - dias + 1 : i + 1]) for i in range(dias - 1, len(serie))]


def percentil(valores: list[float], p: float) -> float | None:
    """Percentil por interpolacion lineal. Devuelve None si no hay valores."""
    ordenados = sorted(valores)
    if not ordenados:
        return None
    k = (len(ordenados) - 1) * p / 100
    bajo = int(k)
    alto = min(bajo + 1, len(ordenados) - 1)
    return ordenados[bajo] + (ordenados[alto] - ordenados[bajo]) * (k - bajo)


def comparar(nombre: str, crudo: list[float], filtrado: list[float], solo_humedos: bool) -> None:
    """
    Contrasta percentiles y clasificacion de eventos entre las dos series.

    `solo_humedos` reproduce la definicion del ETCCDI, que calcula el percentil
    sobre los dias con lluvia y no sobre todo el calendario. Sin ese filtro los
    percentiles salen aplastados por los ceros de la estacion seca y no
    significan lo mismo.
    """
    if solo_humedos:
        indices = [i for i, v in enumerate(crudo) if v >= DIA_HUMEDO_MM]
        muestra_cruda = [crudo[i] for i in indices]
        muestra_filtrada = [filtrado[i] for i in indices]
    else:
        muestra_cruda, muestra_filtrada = crudo, filtrado

    print(f"\n--- {nombre}  (n = {len(muestra_cruda)}) ---")

    for p in (95, 99):
        pc = percentil(muestra_cruda, p)
        pf = percentil(muestra_filtrada, p)
        print(
            f"  P{p}: crudo {pc:8.2f} mm | filtrado {pf:8.2f} mm | "
            f"diferencia {pf - pc:+8.2f} mm ({(pf - pc) / pc * 100:+6.1f} %)"
        )

    umbral_crudo = percentil(muestra_cruda, 99)
    umbral_filtrado = percentil(muestra_filtrada, 99)

    extremos_crudos = {i for i, v in enumerate(muestra_cruda) if v > umbral_crudo}
    extremos_filtrados = {i for i, v in enumerate(muestra_filtrada) if v > umbral_filtrado}
    coinciden = len(extremos_crudos & extremos_filtrados)

    print(
        f"  dias sobre el P99 de su propia serie: crudo {len(extremos_crudos)}, "
        f"filtrado {len(extremos_filtrados)}, los mismos dias "
        f"{coinciden} ({coinciden / max(len(extremos_crudos), 1) * 100:.1f} %)"
    )

    sobreviven = sum(1 for v in muestra_filtrada if v > umbral_crudo)
    print(
        f"  si se conserva el umbral crudo y se aplica a la serie filtrada, "
        f"quedan {sobreviven} de {len(extremos_crudos)} "
        f"({sobreviven / max(len(extremos_crudos), 1) * 100:.1f} %)"
    )


def artefactos(crudo: list[float], filtrado: list[float]) -> None:
    """
    Efectos que no son de magnitud sino de plausibilidad fisica.

    Son los que deciden la cuestion. Un corrimiento de percentil se puede
    documentar y compensar; una serie con lluvia negativa no es una serie de
    lluvia.
    """
    negativos = [v for v in filtrado if v < 0]
    dias_secos = [i for i, v in enumerate(crudo) if v == 0.0]
    secos_que_llueven = [i for i in dias_secos if filtrado[i] >= DIA_HUMEDO_MM]

    print("\n--- Plausibilidad fisica ---")
    print(
        f"  valores negativos: {len(negativos)} de {len(filtrado)} "
        f"({len(negativos) / len(filtrado) * 100:.2f} %), minimo {min(filtrado):.2f} mm"
    )
    print(
        f"  dias de 0.0 mm que salen con {DIA_HUMEDO_MM:.0f} mm o mas: "
        f"{len(secos_que_llueven)} de {len(dias_secos)} "
        f"({len(secos_que_llueven) / len(dias_secos) * 100:.2f} %)"
    )
    print(
        f"  masa total: crudo {sum(crudo):.0f} mm, filtrado {sum(filtrado):.0f} mm "
        f"({(sum(filtrado) - sum(crudo)) / sum(crudo) * 100:+.2f} %)"
    )
    print(
        "\n  El corrimiento de percentil se podria documentar y compensar. Estos dos\n"
        "  no: la lluvia negativa no existe, y un dia seco que pasa a contar como\n"
        "  humedo rompe la definicion sobre la que se calculan R95p y R99p."
    )


def robustez(filtrar) -> None:
    """
    Repite la medida con otras semillas y otras ventanas.

    Sin esto, el resultado podria ser un artefacto de una serie afortunada o de
    haber elegido justo la ventana que mas dana.
    """
    print("\n--- Robustez: otras semillas, otras ventanas ---")
    print(
        f"  {'semilla':>8} {'ventana':>8} {'P99 crudo':>11} {'P99 filtrado':>13} "
        f"{'cambio':>8} {'negativos':>10} {'secos con lluvia':>17}"
    )

    for semilla in (42, 7, 2026):
        for ventana in (3, 5, 7, 11):
            crudo = serie_diaria(semilla=semilla)
            filtrado = filtrar(list(crudo), ventana)

            indices = [i for i, v in enumerate(crudo) if v >= DIA_HUMEDO_MM]
            pc = percentil([crudo[i] for i in indices], 99)
            pf = percentil([filtrado[i] for i in indices], 99)

            negativos = sum(1 for v in filtrado if v < 0) / len(filtrado) * 100
            secos = [i for i, v in enumerate(crudo) if v == 0.0]
            mojados = sum(1 for i in secos if filtrado[i] >= DIA_HUMEDO_MM) / len(secos) * 100

            print(
                f"  {semilla:>8} {ventana:>8} {pc:>11.2f} {pf:>13.2f} "
                f"{(pf - pc) / pc * 100:>7.1f}% {negativos:>9.2f}% {mojados:>16.2f}%"
            )

    print(
        "\n  La ventana de 3 con polinomio de orden 2 no cambia nada, y no es un\n"
        "  error de medicion: con tres puntos una parabola pasa exactamente por los\n"
        "  tres, asi que el filtro devuelve la entrada. La unica ventana que no\n"
        "  dana la precipitacion es aquella en la que el filtro no hace nada."
    )


def main() -> int:
    filtrar, origen = construir_filtro()

    crudo = serie_diaria()
    filtrado = filtrar(list(crudo), VENTANA_FILTRO)

    humedos = sum(1 for v in crudo if v >= DIA_HUMEDO_MM)

    print("=" * 78)
    print("EFECTO DEL FILTRO SOBRE LOS PERCENTILES DE PRECIPITACION (D-17)")
    print("=" * 78)
    print(f"  filtro         : {origen}")
    print(f"  serie          : sintetica, {ANIOS} anios, regimen de Guanacaste")
    print(f"  dias           : {len(crudo)}, de ellos {humedos} humedos (>= 1 mm)")
    print(f"  maximo         : {max(crudo):.1f} mm   media: {statistics.mean(crudo):.2f} mm")
    print(f"  ventana        : {VENTANA_FILTRO} muestras, polinomio de orden 2")

    comparar(
        "Diaria sobre dias humedos, que es como el ETCCDI define R95p y R99p",
        crudo,
        filtrado,
        solo_humedos=True,
    )
    comparar(
        "Acumulado de 72 h, que es el umbral de lluvia intensa del proyecto",
        acumulado(crudo),
        acumulado(filtrado),
        solo_humedos=False,
    )

    artefactos(crudo, filtrado)
    robustez(filtrar)

    print("\n" + "=" * 78)
    print("La conclusion esta en D-17. Recordatorio: esto es una serie sintetica.")
    print("Hay que repetirlo sobre CHIRPS cuando H1.1 entregue las series reales.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
