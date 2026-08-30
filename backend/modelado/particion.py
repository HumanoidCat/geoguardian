"""Particion temporal por ventana expansiva. Historia H3.2.

QUE PRODUCE

La particion que **todos** los modelos consumen: H3.1 la linea base, H3.3, H3.4 y
H3.5 los algoritmos, y H3.6 la tabla comparativa. Una sola definicion, para que
la comparacion de H3.6 compare modelos y no conjuntos distintos.

No entrena nada. Decide **donde se corta el tiempo**.

POR QUE ESTA HISTORIA DECIDE SI LOS RESULTADOS VALEN

Un error aca no se ve en ninguna metrica -al contrario, las mejora- y solo
aparece cuando el modelo se usa contra dato que no vio. **D-04** prohibe la
particion aleatoria por eso, citando a Bergmeir y Benitez (2012).

EL EMBARGO NO ES UNA CONSTANTE: SE CALCULA

Si la ultima fila de entrenamiento es `T` y la primera de prueba es `T+1`, la
etiqueta de `T` ya miro hacia adelante. Cuanto, depende del evento:

    incendio        focos en (t, t+7]                      -> alcanza t+7
    lluvia intensa  maximo acumulado de 72 h en la ventana -> alcanza t+7
    sequia          SPI-6 del mes que contiene a t+7       -> alcanza el FIN
                                                              de ese mes

**La sequia es la que manda**, y por mucho. `ultima_fecha_que_mira()` lo calcula
en vez de suponerlo, y el embargo sale de ahi.

DOS CORRECCIONES A LOS CRITERIOS, MEDIDAS AL IMPLEMENTAR

**CA-2 estimo mal el embargo de dos de los tres eventos.** Las dos veces por lo
mismo: supuse el alcance en vez de calcularlo.

    evento           CA-2 estimo    lo que sale     por que
    incendio          7 dias         7 dias         acertado
    lluvia intensa    9 dias         7 dias         ver abajo
    sequia           38 dias         7 dias         ver abajo

**Lluvia.** CA-2 sumo los 2 dias que cierran el acumulado de 72 h. El etiquetado
ya los tiene en cuenta: acota el ultimo acumulado a que **empiece** en `t+5`, de
modo que termine exactamente en `t+7` y no se pase.

    ultimo_inicio = fin - (VENTANA_ACUMULADO_DIAS - 1)

**Sequia.** Este es el interesante. La etiqueta si alcanza el fin del mes que
contiene a `t+7` -eso CA-2 lo tenia bien- pero **el corte cae en frontera de
mes**, que es CA-3. Y con el corte ahi, exigir que la etiqueta no mire dentro de
la prueba equivale a exigir que `t+7` caiga en un mes anterior: siete dias.

Es decir: **CA-3 absorbe el alcance de la sequia.** Los dos criterios se
escribieron por separado y juntos salen mas baratos que cada uno solo. No estaba
previsto.

LO QUE ESTO **NO** RESUELVE, Y HAY QUE SABERLO EN H3.4

El embargo protege de que una etiqueta de entrenamiento mire dentro de la prueba.
No dice nada sobre las **caracteristicas**: si alguien usa como entrada «el SPI-6
del mes en curso», en la fila `t = corte` eso exige el mes completo, que en
operacion no se tiene el dia 1. Es un defecto de diseno de caracteristicas, no de
particion, y le toca a **H3.4** con **CA-6**.

LOS CORTES CAEN EN FRONTERA DE MES

Porque el SPI-6 no cambia dentro del mes. Un corte a mitad de mes deja el mismo
valor del indice a los dos lados.

H3.0 mide **100,1 filas por episodio de sequia** con SPI-6, sobre 78 episodios
distintos. Eran 66,3 con SPI-3: al integrar seis meses los episodios duran mas,
como corresponde, y **la razon para cortar en frontera de mes se refuerza**.

El precio esta en la otra columna: **15,6 episodios por pliegue** con cinco
pliegues. Es poco, y hay que decirlo cuando se lean las metricas de sequia.

**Lo que NO cambia es el embargo de siete dias.** Sale de que el corte cae en
frontera de mes -CA-3- y no del ancho de la ventana del indice: exigir que la
etiqueta no mire dentro de la prueba equivale a exigir que `t+7` caiga en un mes
anterior, con SPI-3 o con SPI-6.

CADA EVENTO SE PARTE SOBRE SU PROPIO PERIODO OBSERVADO

La serie climatica arranca en 1991 y el archivo de focos en 2001 (**I-11**).
Partir el incendio sobre 1991-2024 pondria **cero episodios observados** en el
primer bloque de entrenamiento.
"""

from __future__ import annotations

import sys
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado.etiquetado import (  # noqa: E402
    COBERTURA_FOCOS,
    HORIZONTE_DIAS,
    ULTIMO_ANIO,
)
from contratos.enums import TipoEvento  # noqa: E402

# Cinco pliegues sobre seis bloques: cada pliegue entrena con todo el pasado
# disponible y evalua el bloque siguiente. Fijado en CA-4 **antes** de mirar el
# dato, y comprobado ahi mismo que el pliegue mas chico alcanza el minimo de
# episodios que exige CA-6 de H3.0.
PLIEGUES = 5

# El periodo con observacion de cada evento. Sequia y lluvia salen de CHIRPS;
# el incendio, de FIRMS. Ver I-11.
PRIMER_ANIO_CLIMA = 1991


@dataclass(frozen=True)
class Pliegue:
    """Un corte: con que se entrena, que se descarta, y sobre que se evalua."""

    indice: int
    entrenamiento: tuple[date, date]
    prueba: tuple[date, date]
    #: Fechas `t` descartadas entre los dos conjuntos. None si no hizo falta
    #: ninguna, que no deberia pasar con ningun evento de este proyecto.
    embargo: tuple[date, date] | None

    @property
    def dias_de_embargo(self) -> int:
        if self.embargo is None:
            return 0
        return (self.embargo[1] - self.embargo[0]).days + 1


# --------------------------------------------------------------------------- #
# El alcance de cada etiqueta                                                   #
# --------------------------------------------------------------------------- #


def fin_de_mes(dia: date) -> date:
    return date(dia.year, dia.month, monthrange(dia.year, dia.month)[1])


def ultima_fecha_que_mira(evento: TipoEvento, t: date) -> date:
    """La fecha mas lejana de la que depende la etiqueta de la fila `t`.

    **Es la funcion que decide el embargo**, y por eso se calcula en vez de
    escribirse como constante. Si el etiquetado cambia su ventana, esto tiene que
    cambiar con el, y `verificar_h32.py` lo comprueba contra `etiquetado.py` en
    lugar de repetir los numeros.
    """
    fin = t + timedelta(days=HORIZONTE_DIAS)

    if evento is TipoEvento.SEQUIA:
        # El SPI-6 del mes que contiene a `t+7`. El indice de ese mes se conoce
        # cuando el mes termina, asi que la etiqueta depende de precipitacion
        # posterior a `t+7`: hasta el ultimo dia de ese mes.
        return fin_de_mes(fin)

    # Incendio: los focos de (t, t+7].
    #
    # Lluvia: el ultimo acumulado de 72 h que cabe entero empieza en `fin - 2` y
    # termina en `fin`. NO se pasa de `t+7`. Ver la nota del encabezado.
    return fin


def periodo_observado(evento: TipoEvento) -> tuple[date, date]:
    """Donde hay observacion para etiquetar ese evento. Ver I-11."""
    if evento is TipoEvento.INCENDIO:
        return COBERTURA_FOCOS
    return date(PRIMER_ANIO_CLIMA, 1, 1), date(ULTIMO_ANIO, 12, 31)


# --------------------------------------------------------------------------- #
# Los cortes                                                                    #
# --------------------------------------------------------------------------- #


def meses_entre(desde: date, hasta: date) -> int:
    return (hasta.year - desde.year) * 12 + (hasta.month - desde.month) + 1


def sumar_meses(dia: date, meses: int) -> date:
    """El primer dia del mes que esta `meses` adelante del de `dia`."""
    total = (dia.year * 12 + dia.month - 1) + meses
    return date(total // 12, total % 12 + 1, 1)


def cortes_mensuales(desde: date, hasta: date, bloques: int) -> list[date]:
    """Los `bloques - 1` cortes que parten `[desde, hasta]` en partes parejas.

    **Cada corte es el primer dia de un mes**, que es el criterio CA-3: el SPI-6
    no cambia dentro del mes, asi que cortar a mitad de mes deja el mismo valor
    del indice a los dos lados.
    """
    if bloques < 2:
        raise ValueError("hacen falta al menos dos bloques para poder cortar")

    total = meses_entre(desde, hasta)
    if total < bloques:
        raise ValueError(f"{total} meses no alcanzan para {bloques} bloques")

    # El primer mes completo del rango. Si `desde` no es dia 1, su mes queda
    # incompleto y el primer corte se corre al siguiente.
    origen = date(desde.year, desde.month, 1)
    por_bloque = total / bloques
    return [sumar_meses(origen, round(por_bloque * i)) for i in range(1, bloques)]


# --------------------------------------------------------------------------- #
# La particion                                                                  #
# --------------------------------------------------------------------------- #


def particionar(
    evento: TipoEvento,
    pliegues: int = PLIEGUES,
    desde: date | None = None,
    hasta: date | None = None,
) -> list[Pliegue]:
    """Ventana expansiva sobre el periodo observado del evento.

    Cada pliegue entrena con **todo** el pasado disponible y evalua el bloque
    siguiente. Entre los dos se descarta el embargo que exige `CA-2`.

    Args:
        evento: decide el periodo observado y el alcance de la etiqueta.
        pliegues: cuantos cortes. Por omision `PLIEGUES`, fijado en CA-4.
        desde, hasta: para las pruebas. En produccion salen del evento.
    """
    inicio, fin = periodo_observado(evento)
    desde = desde or inicio
    hasta = hasta or fin

    cortes = cortes_mensuales(desde, hasta, pliegues + 1)

    salida: list[Pliegue] = []
    for i, corte in enumerate(cortes):
        # El bloque de prueba va del corte al siguiente, o al final.
        fin_prueba = (cortes[i + 1] - timedelta(days=1)) if i + 1 < len(cortes) else hasta

        # -- el embargo ----------------------------------------------------- #
        #
        # La ultima fila de entrenamiento admisible es la mayor `t` cuya etiqueta
        # NO mire dentro del bloque de prueba. Se busca hacia atras desde el
        # corte en vez de restar una constante, porque el alcance de la sequia
        # depende de en que dia del mes cae `t+7`.
        ultima_util = corte - timedelta(days=1)
        while ultima_util >= desde and ultima_fecha_que_mira(evento, ultima_util) >= corte:
            ultima_util -= timedelta(days=1)

        if ultima_util < desde:
            raise ValueError(
                f"el embargo de {evento.value} se come el primer bloque entero. "
                "Hay que reducir pliegues o alargar el periodo."
            )

        descartadas = ultima_util + timedelta(days=1)
        embargo = (descartadas, corte - timedelta(days=1)) if descartadas < corte else None

        salida.append(
            Pliegue(
                indice=i + 1,
                entrenamiento=(desde, ultima_util),
                prueba=(corte, fin_prueba),
                embargo=embargo,
            )
        )

    return salida


# --------------------------------------------------------------------------- #
# CA-6 · que se puede ajustar con toda la serie y que no                        #
# --------------------------------------------------------------------------- #
#
# La distincion no es obvia y por eso se declara en una estructura que una
# maquina puede leer, no en prosa que nadie cruza:
#
#   ETIQUETA        puede usar estadisticos de toda la serie. Es la verdad de
#                   terreno, no una prediccion. Los P95/P99 de 72 h y el ajuste
#                   del SPI-6 salen de la normal climatologica 1991-2020, que es
#                   una referencia fija publicada por la OMM y conocida de
#                   antemano en operacion.
#
#   CARACTERISTICA  NO puede. Una media, un percentil o una normalizacion
#                   calculados sobre toda la serie y usados como ENTRADA del
#                   modelo filtran el futuro, y se ajustan dentro del pliegue.
#
# **Un estadistico sin clasificar es un defecto**, no una omision de redaccion.
# `verificar_h32.py` falla si aparece uno que no este en esta tabla.

ETIQUETA = "etiqueta"
CARACTERISTICA = "caracteristica"

ESTADISTICOS: dict[str, str] = {
    "percentil_acumulado P95": ETIQUETA,
    "percentil_acumulado P99": ETIQUETA,
    "CalculadorSPI.spi por mes calendario": ETIQUETA,
    "conteo de focos en la ventana": ETIQUETA,
}


def filas_de_entrenamiento(pliegue: Pliegue, fechas: list[date]) -> list[date]:
    """Las fechas que ese pliegue puede usar para entrenar. **Se pide, no se deriva.**

    Existe para que H3.1, H3.3, H3.4 y H3.5 no vuelvan a calcular el corte cada
    una. Si dos historias derivan sus propios limites, la tabla comparativa de
    H3.6 compara modelos evaluados sobre conjuntos distintos y no significa nada.
    Es **CA-1** y **CA-5**.
    """
    inicio, fin = pliegue.entrenamiento
    return [f for f in fechas if inicio <= f <= fin]


def filas_de_prueba(pliegue: Pliegue, fechas: list[date]) -> list[date]:
    """Las fechas sobre las que se evalua ese pliegue."""
    inicio, fin = pliegue.prueba
    return [f for f in fechas if inicio <= f <= fin]


# --------------------------------------------------------------------------- #
# La metrica                                                                    #
# --------------------------------------------------------------------------- #


def resumen_f1(por_pliegue: list[float]) -> tuple[float, float, list[float]]:
    """Media y desviacion del F1-macro sobre los pliegues. Es **CA-7**.

    Se agrega **promediando los pliegues**, no agrupando sus predicciones. Las
    dos formas dan numeros distintos y hay que elegir una de antemano: la primera
    pesa igual a todos los pliegues, la segunda pesa por tamano y en una ventana
    expansiva el ultimo bloque dominaria.

    **La desviacion se reporta siempre.** Con clases minoritarias del 0,87 % un
    solo pliegue afortunado mueve el promedio, y sin la dispersion nadie puede
    saberlo. Los cinco valores tambien se devuelven: un promedio sin sus partes
    no se puede auditar.
    """
    if not por_pliegue:
        raise ValueError("no hay pliegues que resumir")
    n = len(por_pliegue)
    media = sum(por_pliegue) / n
    varianza = sum((v - media) ** 2 for v in por_pliegue) / n
    return media, varianza**0.5, list(por_pliegue)


# --------------------------------------------------------------------------- #
# El artefacto                                                                  #
# --------------------------------------------------------------------------- #


def describir(evento: TipoEvento, pliegues: list[Pliegue]) -> str:
    """La particion en texto, con fechas. Es **CA-9**.

    Dentro de un mes «cinco pliegues expansivos» no le dice nada a nadie.
    """
    inicio, fin = periodo_observado(evento)
    lineas = [
        f"{evento.value.upper()}",
        f"  periodo observado : {inicio} a {fin}",
        f"  pliegues          : {len(pliegues)}",
        "",
        f"  {'#':<3}{'entrenamiento':<26}{'embargo':<8}{'prueba':<26}",
    ]
    for p in pliegues:
        ent = f"{p.entrenamiento[0]} a {p.entrenamiento[1]}"
        pru = f"{p.prueba[0]} a {p.prueba[1]}"
        lineas.append(f"  {p.indice:<3}{ent:<26}{p.dias_de_embargo:<8}{pru:<26}")
    return "\n".join(lineas)


if __name__ == "__main__":
    for evento in TipoEvento:
        print()
        print(describir(evento, particionar(evento)))
    print()
