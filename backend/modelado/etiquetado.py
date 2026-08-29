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

    sequia          SPI-6, mensual
    lluvia intensa  acumulado de 72 h
    incendio        ventana de 7 dias

  * **Incendio** es el unico que calza natural: se cuentan los focos de la
    ventana. Con al menos uno, ALTO; sin ninguno, BAJO. **No hay MEDIO** para
    este evento, por **D-25** y **SC-05**.

    Pero solo **dentro de la cobertura del satelite**. La serie climatica arranca
    en 1991 y el archivo de focos en 2001: una ventana anterior a esa fecha sale
    `None`, no BAJO. Ver `COBERTURA_FOCOS`.

  * **Lluvia intensa** se resuelve tomando el **maximo acumulado de 72 h dentro
    de la ventana**. La pregunta que responde la etiqueta es "en los proximos
    siete dias, hubo algun episodio de 72 h que superara el umbral". Los
    umbrales son los P95 y P99 **del propio distrito** sobre 1991-2020.

  * **Sequia** usa el SPI-6 del **mes calendario que contiene a `t+7`**, que es
    el estado de sequia al final del horizonte.

    **Consecuencia que H3.2 tiene que conocer:** el SPI-6 de un mes no cambia
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
#: Escala del SPI, en meses. **Seis, por D-32, y sale de una medicion.**
#:
#: Fue 3 desde D-19 hasta el 2026-08-28, adoptada porque es la escala mas comun
#: en la literatura de sequia agricola. Nadie la habia medido.
#:
#: `comparar_escalas_spi.py` contrasto las tres contra el catalogo: SPI-3 dio
#: **0 de 7** y SPI-6 y SPI-12 dieron 7 de 7. El intervalo de Wilson del SPI-3,
#: 0,0 %-35,4 %, **no se solapa** con el de las otras dos, 64,6 %-100 %, y el
#: 1,0 cae dentro del rango de su realce: ante el unico episodio que el catalogo
#: permite probar, marcaba con la misma frecuencia que un dia cualquiera.
#:
#: Y el fallo no era aleatorio: **-37 dias en los ocho distritos**, identico. El
#: SPI-3 sale de sequia antes de que el dano se declare.
#:
#: Entre 6 y 12 el catalogo no decide -los dos dan 7 de 7 con intervalos
#: solapados- y la eleccion se hace por otro criterio, declarado en D-32: el
#: SPI-6 produce **casi el doble de episodios** que el SPI-12 con menor tasa
#: base, y es la escala que `[15]` toma para la estacion lluviosa del Pacifico.
VENTANA_SPI_MESES = 6

# El etiquetado se corta donde termina la fuente mas corta. Ver el encabezado.
ULTIMO_ANIO = 2024

# --------------------------------------------------------------------------- #
# La cobertura del satelite, que NO es la cobertura de la serie climatica       #
# --------------------------------------------------------------------------- #
#
# CHIRPS empieza en 1981 y la serie del proyecto en 1991. **El archivo de focos
# de calor no.** MODIS Terra/Aqua colecion 6.1 arranca su archivo operacional a
# finales del 2000, y los datos que R16 midio para este canton van de 2001 a
# 2024. Antes de eso no hay observacion: no es que no hubiera incendios, es que
# no habia satelite mirando.
#
# Sin esta cota, `nivel_incendio` devuelve BAJO para toda la decada de los
# noventa —**29 224 filas, el 29,4 % del conjunto**— por el unico motivo de que
# la cuenta de focos da cero. Es exactamente el defecto que **CA-8** existe para
# impedir: la ausencia de dato convertida en clase. Y el efecto no es cosmetico,
# porque la clase minoritaria de incendio es del orden del 1 %:
#
#     ALTO sobre las 99 296 filas             0,87 %
#     ALTO sobre las 70 072 observadas        1,23 %
#
# Se declara como constante y no se infiere del dato cargado. Inferirla del
# minimo de las detecciones diria que un distrito sin focos nunca fue observado,
# que es justo la confusion que esto viene a evitar.
COBERTURA_FOCOS = (date(2001, 1, 1), date(ULTIMO_ANIO, 12, 31))


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


def nivel_incendio(focos_en_ventana: int, ventana_observada: bool = True) -> NivelRiesgo | None:
    """ALTO con al menos un foco, BAJO sin ninguno. **No existe MEDIO.**

    Es **D-25**, sobre la medicion de R16: 242 focos en 24 anios, con entre el
    97 % y el 99,9 % de las ventanas vacias, asi que el P90 del conteo vale 0,0
    en los ocho distritos y el umbral por percentiles no producia tres clases.

    `ventana_observada` en False devuelve **None**, no BAJO. Cero focos en una
    ventana que **nadie miro** no es ausencia de incendio: es ausencia de dato, y
    **D-07** y **D-22** dicen que eso se representa, no se rellena. Ver
    `COBERTURA_FOCOS`.
    """
    if not ventana_observada:
        return None
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


def nivel_sequia(spi: float | None) -> NivelRiesgo | None:
    """SPI con los cortes de McKee, Doesken y Kleist (1993), adoptados por la OMM.

    **Los cortes no dependen de la escala.** El SPI esta normalizado por
    construccion, asi que -1,0 y -1,5 significan lo mismo en SPI-3, SPI-6 o
    SPI-12. El cambio de escala de D-32 no los toca, y el parametro se llama
    `spi` y no `spi3` justamente para que eso quede a la vista.
    """
    if spi is None:
        return None
    if spi <= -1.5:
        return NivelRiesgo.ALTO
    if spi <= -1.0:
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
    cobertura_focos: tuple[date, date] = COBERTURA_FOCOS,
) -> list[Etiqueta]:
    """Etiqueta un distrito completo. Todo el calculo por distrito vive aca.

    Args:
        precipitacion: precipitacion diaria en mm, con None donde falta.
        focos: fechas de los focos de calor de ESE distrito. Se cuentan
            repeticiones: dos focos el mismo dia son dos.
        desde, hasta: rango de fechas `t` a etiquetar, inclusive.
        cobertura_focos: periodo en que el satelite **estuvo mirando**. Una fila
            cuya ventana `(t, t+7]` no cae entera adentro sale con
            `incendio=None`, no BAJO. Ver `COBERTURA_FOCOS`.
    """
    fechas = sorted(precipitacion)
    serie = [precipitacion[f] for f in fechas]

    # Umbrales del propio distrito sobre el periodo base 1991-2020. La funcion
    # los calcula sobre su periodo por omision.
    p95 = percentil_acumulado(serie, fechas, 95, VENTANA_ACUMULADO_DIAS)
    p99 = percentil_acumulado(serie, fechas, 99, VENTANA_ACUMULADO_DIAS)

    # SPI-6 por mes calendario. El parametro `meses` NO es opcional aca: sin el,
    # el indice sigue la estacionalidad en vez de la anomalia. Ver CA-3.
    totales, meses, claves = acumulado_mensual(precipitacion)
    valores = CalculadorSPI().spi(totales, VENTANA_SPI_MESES, meses)
    spi_por_mes = dict(zip(claves, valores, strict=True))

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
        # La ventana entera tiene que caer dentro de la cobertura del satelite.
        # Si asoma aunque sea un dia por fuera, la cuenta esta incompleta y no se
        # sabe si hubo focos ese dia: la fila sale None.
        observada = cobertura_focos[0] <= inicio and fin <= cobertura_focos[1]

        # -- lluvia: el mayor acumulado de 72 h que empieza dentro ---------- #
        # El ultimo acumulado que cabe entero empieza en fin - 2.
        ultimo_inicio = fin - timedelta(days=VENTANA_ACUMULADO_DIAS - 1)
        maximo = maximo_acumulado_en_ventana(precipitacion, inicio, ultimo_inicio)

        # -- sequia: el SPI-6 del mes que contiene al final del horizonte --- #
        spi = spi_por_mes.get((fin.year, fin.month))

        etiquetas.append(
            Etiqueta(
                codigo_distrito=codigo,
                fecha=t,
                sequia=nivel_sequia(spi),
                lluvia_intensa=nivel_lluvia(maximo, p95, p99),
                incendio=nivel_incendio(cuenta, observada),
            )
        )
        t += timedelta(days=1)

    return etiquetas
