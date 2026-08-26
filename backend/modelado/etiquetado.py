"""Etiquetado de los tres eventos a siete dias. Historia H3.0.

QUE PRODUCE

Para cada distrito y cada fecha `t`, el nivel de riesgo que **efectivamente
ocurrio** en la ventana `(t, t+7]`. Es la variable objetivo de toda la epica de
modelado.

LA VENTANA ES `(t, t+7]` Y NO `[t, t+7]`

Los siete dias **posteriores** a `t`, sin incluir `t`. Un foco que cae el mismo
dia `t` NO etiqueta la fila de `t`.

Si `t` entrara en la ventana, el modelo veria en la etiqueta un dia del que ya
tiene las caracteristicas: es fuga temporal, y produce metricas excelentes con
un modelo inservible. Es el criterio **CA-4** y lo comprueba `verificar_h30.py`.

LAS TRES ESCALAS NO COINCIDEN, Y ASI SE CONCILIAN

    sequia          SPI-3, mensual
    lluvia intensa  acumulado de 72 h
    incendio        ventana de 7 dias

  * **Incendio** es el unico que calza natural: se cuentan los focos de la
    ventana. Con al menos uno, ALTO; sin ninguno, BAJO. **No hay MEDIO** para
    este evento, por **D-25** y **SC-05**.

  * **Lluvia intensa** se resuelve tomando el **maximo acumulado de 72 h dentro
    de la ventana**. La pregunta que responde la etiqueta es "en los proximos
    siete dias, hubo algun episodio de 72 h que superara el umbral". Los
    umbrales son los P95 y P99 **del propio distrito** sobre 1991-2020.

  * **Sequia** usa el SPI-3 del **mes calendario que contiene a `t+7`**, que es
    el estado de sequia al final del horizonte.

    **Consecuencia que H3.2 tiene que conocer:** el SPI-3 de un mes no cambia
    dentro del mes, asi que todas las filas de un mismo mes comparten su
    etiqueta de sequia. No es un defecto -es lo que el indice mide- pero **infla
    la correlacion entre filas vecinas**, y una particion que corte por el medio
    de un mes deja informacion del mismo indice a los dos lados.

LOS UMBRALES NO SE DECIDEN AQUI

Salen de `contratos/enums.py`, que a su vez los toma de **D-08** con su revision,
**D-19** y **D-25**. Este modulo los aplica; `verificar_h30.py` comprueba que los
aplique como el contrato los declara, **leyendolos del contrato** en vez de
repetirlos.

LA AUSENCIA NO ES UNA CLASE

Si falta el dato que decide una etiqueta, la etiqueta sale `None`. Un dia sin
precipitacion no es un dia sin lluvia: **D-07** y **D-22**.

LA VENTANA LLEGA A 2024

Las series climaticas llegan a 2025-12-31 y los focos a 2024-12-31. El etiquetado
se acota a **2024** porque juntar las dos escalas exige que las dos existan. Ver
la nota en `procedencia-focos.md` y el acuerdo del 25 de agosto.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.senales.percentiles import percentil_acumulado  # noqa: E402
from backend.senales.spi import CalculadorSPI  # noqa: E402
from contratos.enums import NivelRiesgo, TipoEvento  # noqa: E402

HORIZONTE_DIAS = 7
VENTANA_ACUMULADO_DIAS = 3  # las "72 h" del contrato
VENTANA_SPI_MESES = 3

# El etiquetado se corta donde termina la fuente mas corta. Ver el encabezado.
ULTIMO_ANIO = 2024


@dataclass(frozen=True)
class Etiqueta:
    """Una fila etiquetada: distrito, fecha y el nivel de los tres eventos."""

    codigo_distrito: str
    fecha: date
    sequia: NivelRiesgo | None
    lluvia_intensa: NivelRiesgo | None
    incendio: NivelRiesgo | None

    def nivel(self, evento: TipoEvento) -> NivelRiesgo | None:
        return {
            TipoEvento.SEQUIA: self.sequia,
            TipoEvento.LLUVIA_INTENSA: self.lluvia_intensa,
            TipoEvento.INCENDIO: self.incendio,
        }[evento]


# --------------------------------------------------------------------------- #
# Los tres eventos                                                              #
# --------------------------------------------------------------------------- #


def nivel_incendio(focos_en_ventana: int) -> NivelRiesgo:
    """ALTO con al menos un foco, BAJO sin ninguno. **No existe MEDIO.**

    Es **D-25**, sobre la medicion de R16: 242 focos en 24 anios, con entre el
    97 % y el 99,9 % de las ventanas vacias, asi que el P90 del conteo vale 0,0
    en los ocho distritos y el umbral por percentiles no producia tres clases.
    """
    return NivelRiesgo.ALTO if focos_en_ventana >= 1 else NivelRiesgo.BAJO


def nivel_lluvia(
    maximo_72h: float | None, p95: float | None, p99: float | None
) -> NivelRiesgo | None:
    """Sobre el **acumulado de 72 h**, contra los percentiles del distrito.

    NO es R95p. R95p se define sobre precipitacion diaria de dias humedos, y
    sobre los mismos treinta anios los dos umbrales difieren en un factor de
    1,6: usar el equivocado multiplica por 8,5 las filas en ALTO. Ver la nota de
    revision de **D-08** y el criterio **CA-2**.
    """
    if maximo_72h is None or p95 is None or p99 is None:
        return None
    if maximo_72h > p99:
        return NivelRiesgo.ALTO
    if maximo_72h > p95:
        return NivelRiesgo.MEDIO
    return NivelRiesgo.BAJO


def nivel_sequia(spi3: float | None) -> NivelRiesgo | None:
    """SPI-3 con los cortes de McKee, Doesken y Kleist (1993), adoptados por la OMM."""
    if spi3 is None:
        return None
    if spi3 <= -1.5:
        return NivelRiesgo.ALTO
    if spi3 <= -1.0:
        return NivelRiesgo.MEDIO
    return NivelRiesgo.BAJO


# --------------------------------------------------------------------------- #
# Piezas de calculo                                                             #
# --------------------------------------------------------------------------- #


def maximo_acumulado_en_ventana(
    precipitacion: dict[date, float | None],
    desde: date,
    hasta: date,
    ventana_dias: int = VENTANA_ACUMULADO_DIAS,
) -> float | None:
    """Mayor acumulado de `ventana_dias` que empieza dentro de `[desde, hasta]`.

    Devuelve None si **algun** dia necesario falta. No se acumula sobre huecos:
    sumar tratando el None como cero diria que no llovio, y lo que pasa es que
    no se sabe. Es **D-07**.
    """
    mejor: float | None = None
    dia = desde
    while dia <= hasta:
        total = 0.0
        completo = True
        for desplazamiento in range(ventana_dias):
            valor = precipitacion.get(dia + timedelta(days=desplazamiento))
            if valor is None:
                completo = False
                break
            total += valor
        if completo:
            mejor = total if mejor is None else max(mejor, total)
        dia += timedelta(days=1)
    return mejor


def acumulado_mensual(
    precipitacion: dict[date, float | None],
) -> tuple[list[float | None], list[int], list[tuple[int, int]]]:
    """Serie mensual para el SPI: totales, mes calendario y la clave (anio, mes).

    Un mes con **cualquier** dia sin dato sale None. El SPI compara el total del
    mes contra la distribucion historica de ese mes, y un total al que le faltan
    dias es menor por construccion: entraria como sequia.
    """
    por_mes: dict[tuple[int, int], list[float | None]] = defaultdict(list)
    for dia, valor in precipitacion.items():
        por_mes[(dia.year, dia.month)].append(valor)

    claves = sorted(por_mes)
    totales: list[float | None] = []
    for clave in claves:
        valores = por_mes[clave]
        totales.append(None if any(v is None for v in valores) else sum(valores))  # type: ignore[arg-type]

    return totales, [mes for _, mes in claves], claves


# --------------------------------------------------------------------------- #
# Etiquetado                                                                    #
# --------------------------------------------------------------------------- #


def etiquetar_distrito(
    codigo: str,
    precipitacion: dict[date, float | None],
    focos: list[date],
    desde: date,
    hasta: date,
) -> list[Etiqueta]:
    """Etiqueta un distrito completo. Todo el calculo por distrito vive aca.

    Args:
        precipitacion: precipitacion diaria en mm, con None donde falta.
        focos: fechas de los focos de calor de ESE distrito. Se cuentan
            repeticiones: dos focos el mismo dia son dos.
        desde, hasta: rango de fechas `t` a etiquetar, inclusive.
    """
    fechas = sorted(precipitacion)
    serie = [precipitacion[f] for f in fechas]

    # Umbrales del propio distrito sobre el periodo base 1991-2020. La funcion
    # los calcula sobre su periodo por omision.
    p95 = percentil_acumulado(serie, fechas, 95, VENTANA_ACUMULADO_DIAS)
    p99 = percentil_acumulado(serie, fechas, 99, VENTANA_ACUMULADO_DIAS)

    # SPI-3 por mes calendario. El parametro `meses` NO es opcional aca: sin el,
    # el indice sigue la estacionalidad en vez de la anomalia. Ver CA-3.
    totales, meses, claves = acumulado_mensual(precipitacion)
    spi3 = CalculadorSPI().spi(totales, VENTANA_SPI_MESES, meses)
    spi_por_mes = dict(zip(claves, spi3, strict=True))

    focos_por_dia: dict[date, int] = defaultdict(int)
    for dia in focos:
        focos_por_dia[dia] += 1

    etiquetas: list[Etiqueta] = []
    t = desde
    while t <= hasta:
        inicio = t + timedelta(days=1)
        fin = t + timedelta(days=HORIZONTE_DIAS)

        # -- incendio: cuenta de focos en (t, t+7] -------------------------- #
        cuenta = sum(
            focos_por_dia.get(inicio + timedelta(days=d), 0) for d in range((fin - inicio).days + 1)
        )

        # -- lluvia: el mayor acumulado de 72 h que empieza dentro ---------- #
        # El ultimo acumulado que cabe entero empieza en fin - 2.
        ultimo_inicio = fin - timedelta(days=VENTANA_ACUMULADO_DIAS - 1)
        maximo = maximo_acumulado_en_ventana(precipitacion, inicio, ultimo_inicio)

        # -- sequia: el SPI-3 del mes que contiene al final del horizonte --- #
        spi = spi_por_mes.get((fin.year, fin.month))

        etiquetas.append(
            Etiqueta(
                codigo_distrito=codigo,
                fecha=t,
                sequia=nivel_sequia(spi),
                lluvia_intensa=nivel_lluvia(maximo, p95, p99),
                incendio=nivel_incendio(cuenta),
            )
        )
        t += timedelta(days=1)

    return etiquetas
