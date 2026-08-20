"""
Percentiles de precipitacion por distrito. Historia H2.7.

Calcula los umbrales que separan los niveles de riesgo de lluvia intensa en
`contratos/enums.py`. Referencia: Zhang et al. (2011), `[18]`, que define los
indices del ETCCDI adoptados por la OMM.

DOS CANTIDADES DISTINTAS, Y NO SON LO MISMO
-------------------------------------------

Este modulo calcula dos cosas que conviene no confundir, porque el proyecto usa
una y el ETCCDI define la otra:

1. **Percentil ETCCDI**, `percentil_dias_humedos`. Se calcula sobre la
   precipitacion **diaria** de los **dias humedos** del periodo base, donde dia
   humedo es 1,0 mm o mas. Es la definicion de Zhang et al. y es la que
   corresponde citar cuando se escriba "R95p" o "R99p" en el documento.

2. **Percentil sobre acumulado de 72 h**, `percentil_acumulado`. Es el que usan
   los umbrales de `contratos/enums.py`: "precipitacion acumulada en 72 h por
   distrito: bajo si <= P95; medio si P95 < acum <= P99; alto si > P99".

**El segundo no es R95p.** Es un percentil legitimo y probablemente mas
adecuado para riesgo de inundacion, porque un evento de lluvia intensa dura mas
de un dia, pero **no es el indice del ETCCDI** y no deberia llamarse asi en el
paper sin aclararlo. La diferencia esta medida en la evidencia de esta historia.

DECISION D-17
-------------

La serie entra **cruda**, sin filtrar. Filtrar precipitacion convierte en
humedos el 31,6 % de los dias secos, y el umbral de dia humedo es exactamente
1 mm: filtrar reescribe cual es el denominador del indice.
"""

from __future__ import annotations

from datetime import date

# Umbral de dia humedo del ETCCDI. No es un parametro ajustable: es parte de la
# definicion del indice. Zhang et al. (2011).
UMBRAL_DIA_HUMEDO_MM = 1.0

# Periodo base del proyecto. Es la normal climatologica que fija el charter y
# que usa la linea base, no el 1961-1990 clasico del ETCCDI. La diferencia esta
# declarada en la evidencia.
PERIODO_BASE_INICIO = date(1991, 1, 1)
PERIODO_BASE_FIN = date(2020, 12, 31)

# Por debajo de esto un percentil de cola no significa nada: con 19 dias
# humedos, el P95 es simplemente el maximo.
MINIMO_DIAS_HUMEDOS = 20


def percentil_dias_humedos(
    precipitacion: list[float | None],
    fechas: list[date],
    percentil: float,
    desde: date = PERIODO_BASE_INICIO,
    hasta: date = PERIODO_BASE_FIN,
) -> float | None:
    """
    Percentil del ETCCDI sobre la precipitacion diaria de los dias humedos.

    Es la definicion de R95p y R99p de Zhang et al. (2011): el percentil se
    calcula **solo sobre los dias humedos** del periodo base, donde dia humedo
    es 1,0 mm o mas.

    **Por que se excluyen los dias secos.** En el Pacifico Norte la estacion
    seca aporta meses enteros de 0,0 mm. Si esos dias entraran al calculo, la
    masa de ceros desplazaria los percentiles hacia abajo y el P95 dejaria de
    representar "lluvia muy intensa" para representar "llovio algo". En Tilaran
    el efecto seria grande, no marginal.

    Args:
        precipitacion: serie diaria en mm, con None en los dias sin dato.
        fechas: fecha de cada posicion. Debe tener el mismo largo que la serie.
        percentil: 95 para R95p, 99 para R99p.
        desde, hasta: periodo base, inclusive en ambos extremos.

    Returns:
        El umbral en mm, o None si no hay dias humedos suficientes en el
        periodo. **None y no 0.0**: un umbral de cero declararia lluvia intensa
        cualquier dia con una gota.

    Raises:
        ValueError: si las listas tienen largos distintos, si el percentil esta
            fuera de (0, 100), o si hay precipitacion negativa.
    """
    humedos = _dias_humedos_del_periodo(precipitacion, fechas, percentil, desde, hasta)

    if len(humedos) < MINIMO_DIAS_HUMEDOS:
        return None

    return _percentil(humedos, percentil)


def percentil_acumulado(
    precipitacion: list[float | None],
    fechas: list[date],
    percentil: float,
    ventana_dias: int = 3,
    desde: date = PERIODO_BASE_INICIO,
    hasta: date = PERIODO_BASE_FIN,
) -> float | None:
    """
    Percentil sobre el acumulado movil de `ventana_dias` dias.

    Es el umbral que usa `contratos/enums.py` para lluvia intensa, con ventana
    de 3 dias, o sea 72 horas.

    **No es el indice R95p del ETCCDI.** Ver la nota del encabezado del modulo.
    Se calcula sobre acumulados de varios dias y no sobre lluvia diaria de dias
    humedos, de modo que su valor y su interpretacion son distintos.

    Los acumulados que contienen algun hueco no entran al calculo: sumar solo
    los dias presentes daria un acumulado sistematicamente menor y bajaria el
    umbral.

    A diferencia del percentil ETCCDI, **aqui no se filtran los acumulados
    secos**. Un acumulado de 72 h de 0 mm es informacion valida sobre la
    distribucion de la lluvia acumulada, mientras que en el indice diario el
    ETCCDI los excluye por definicion.
    """
    _validar(precipitacion, fechas, percentil)
    if ventana_dias < 1:
        raise ValueError(f"La ventana debe ser al menos 1 dia, se recibio {ventana_dias}")

    acumulados: list[float] = []

    for i in range(ventana_dias - 1, len(precipitacion)):
        if not (desde <= fechas[i] <= hasta):
            continue
        trozo = precipitacion[i - ventana_dias + 1 : i + 1]
        if any(v is None for v in trozo):
            continue
        acumulados.append(sum(v for v in trozo if v is not None))

    if len(acumulados) < MINIMO_DIAS_HUMEDOS:
        return None

    return _percentil(acumulados, percentil)


def umbrales_por_distrito(
    series: dict[str, tuple[list[float | None], list[date]]],
    ventana_dias: int = 3,
) -> dict[str, dict[str, float | None]]:
    """
    Umbrales P95 y P99 de cada distrito, en las dos definiciones.

    Los umbrales del proyecto son **por distrito**: cada uno se compara contra
    su propia distribucion historica, no contra una del canton. Un distrito
    seco y uno lluvioso no pueden compartir umbral, porque entonces el seco no
    alcanzaria nunca el nivel alto y el lluvioso lo alcanzaria siempre.

    Args:
        series: codigo de distrito -> (precipitacion diaria, fechas).

    Returns:
        codigo -> {"p95_diario", "p99_diario", "p95_acumulado", "p99_acumulado"}.
        Cualquiera puede ser None si ese distrito no tiene datos suficientes, y
        se devuelve None en vez de un valor del canton: rellenar con el umbral
        de otro distrito seria inventar.
    """
    salida: dict[str, dict[str, float | None]] = {}

    for codigo, (precipitacion, fechas) in series.items():
        salida[codigo] = {
            "p95_diario": percentil_dias_humedos(precipitacion, fechas, 95),
            "p99_diario": percentil_dias_humedos(precipitacion, fechas, 99),
            "p95_acumulado": percentil_acumulado(precipitacion, fechas, 95, ventana_dias),
            "p99_acumulado": percentil_acumulado(precipitacion, fechas, 99, ventana_dias),
        }

    return salida


# --------------------------------------------------------------------------- #
# Internos                                                                      #
# --------------------------------------------------------------------------- #


def _validar(precipitacion: list[float | None], fechas: list[date], percentil: float) -> None:
    if len(precipitacion) != len(fechas):
        raise ValueError(
            f"La serie tiene {len(precipitacion)} valores y {len(fechas)} fechas. "
            "Sin correspondencia uno a uno no se puede acotar el periodo base."
        )
    if not 0 < percentil < 100:
        raise ValueError(f"El percentil debe estar entre 0 y 100 exclusive, se recibio {percentil}")

    negativos = [v for v in precipitacion if v is not None and v < 0]
    if negativos:
        raise ValueError(
            f"La precipitacion no puede ser negativa; se recibieron {len(negativos)} "
            f"valores negativos, el menor de {min(negativos):.2f} mm. "
            "Si la serie paso por filtrar_ruido, eso lo explica: la decision D-17 "
            "prohibe filtrar precipitacion."
        )


def _dias_humedos_del_periodo(
    precipitacion: list[float | None],
    fechas: list[date],
    percentil: float,
    desde: date,
    hasta: date,
) -> list[float]:
    _validar(precipitacion, fechas, percentil)

    return [
        v
        for v, f in zip(precipitacion, fechas, strict=True)
        if v is not None and v >= UMBRAL_DIA_HUMEDO_MM and desde <= f <= hasta
    ]


def _percentil(muestra: list[float], percentil: float) -> float:
    """
    Percentil por interpolacion lineal entre los dos valores mas cercanos.

    Es el metodo 7 de Hyndman y Fan, el mismo que usan numpy por defecto y R.
    Se escribe a mano y no se importa numpy para no agregar una dependencia a
    un modulo que no la necesita para nada mas.
    """
    ordenada = sorted(muestra)
    n = len(ordenada)

    if n == 1:
        return ordenada[0]

    posicion = (percentil / 100) * (n - 1)
    inferior = int(posicion)
    resto = posicion - inferior

    if inferior + 1 >= n:
        return ordenada[-1]

    return ordenada[inferior] + resto * (ordenada[inferior + 1] - ordenada[inferior])
