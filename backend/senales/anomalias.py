"""
Anomalias respecto a la normal climatologica 1991-2020. Historia H2.4.

Implementa `anomalia` del contrato `contratos/senales.py` y agrega el calculo de
las normales, que el contrato consume pero no produce.

QUE ES UNA ANOMALIA Y POR QUE IMPORTA EL MES
--------------------------------------------

La anomalia es la desviacion de un valor respecto de **lo normal para ese mes
del anio**. En Tilaran la normal de febrero ronda los 5 mm y la de octubre los
320: comparar octubre contra la normal de octubre dice si llovio mas o menos de
lo habitual; compararlo contra cualquier otro mes no dice nada sobre el clima,
dice en que mes estamos.

Es el mismo argumento que sostuvo la decision **D-19** para el SPI.

EL HUECO DEL CONTRATO
---------------------

`anomalia(serie, normal_por_mes)` **no recibe fechas**. Nada indica a que mes
corresponde cada posicion de la serie, asi que la implementacion no tiene forma
inequivoca de elegir la normal correcta.

Esta implementacion supone, como el simulado, que la serie es **mensual y
arranca en enero**: la posicion `i` es el mes `(i mod 12) + 1`.

**Esa suposicion no esta en el contrato y no se puede verificar desde dentro de
la funcion.** Si la serie empieza en otro mes, el resultado es silenciosamente
incorrecto: no falla, devuelve numeros equivocados.

Por eso el modulo **avisa por registro en cada llamada**, y por eso existe la
solicitud de cambio **SC-06**, en
`docs/investigacion/solicitud-cambio-anomalia-mes.md`.

El hueco ya estaba registrado en `docs/02-contratos.md` antes de esta historia.
Lo que aporta H2.4 es la medicion de cuanto cuesta.

LO QUE SI PUEDE RECIBIR FECHAS
------------------------------

`normales_por_mes` no es un metodo del contrato, asi que se diseno con fechas
desde el principio. El contraste es intencional: **calcular la normal
correctamente es facil cuando se sabe la fecha, y es justo lo que a `anomalia`
le falta.**
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date

log = logging.getLogger(__name__)

# Normal climatologica del proyecto. La fija el charter y la usa la linea base.
NORMAL_INICIO = date(1991, 1, 1)
NORMAL_FIN = date(2020, 12, 31)

# Anios minimos que la OMM recomienda para una normal climatologica.
# WMO-No. 1203, referencia [6].
MINIMO_ANIOS_NORMAL = 30

MESES_DEL_ANIO = 12

# Para que el aviso nombre el mes en vez de su numero. Quien lee un registro no
# tiene por que traducir "10" a octubre mientras revisa por que la normal es
# debil. El indice 0 no se usa.
NOMBRE_DEL_MES = (
    "",
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "setiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


class CalculadorAnomalias:
    """
    Anomalias respecto a la normal climatologica.

    Cumple el metodo `anomalia` del protocolo `ProcesadorSenales`. Los demas los
    implementan otras historias: `filtrar_ruido` en H2.1, `espectro` en H2.2,
    `spi` en H2.3 y `remuestrear` en H2.6.
    """

    def anomalia(
        self,
        serie: list[float | None],
        normal_por_mes: dict[int, float],
    ) -> list[float | None]:
        """
        Desviacion respecto a la normal climatologica de cada mes.

        Args:
            serie: valores **mensuales**, con None en los meses sin dato.
            normal_por_mes: normal indexada por mes calendario, de 1 a 12.

        Returns:
            Una lista del mismo largo. Una posicion sale None si su valor es
            None **o si su mes no esta en `normal_por_mes`**. No se sustituye
            por el promedio de los meses que si estan: eso mezclaria la normal
            de un mes con la de otro, que es el error que este indice existe
            para no cometer.

        Raises:
            ValueError: si `normal_por_mes` tiene claves fuera de 1 a 12.

        **ADVERTENCIA.** Se supone que la serie arranca en enero, porque el
        contrato no recibe fechas. Ver la nota del modulo y la solicitud SC-06.
        """
        _validar_normales(normal_por_mes)

        log.warning(
            "anomalia() supone que la serie es mensual y arranca en enero, porque el "
            "contrato no recibe fechas. Si no es asi, el resultado es silenciosamente "
            "incorrecto: cada valor se compara contra la normal del mes equivocado. En "
            "Tilaran las normales van de unos 5 mm en febrero a unos 320 en octubre, "
            "asi que un desfase de un mes produce errores del tamano del ciclo anual. "
            "Ver SC-06 y docs/02-contratos.md"
        )

        salida: list[float | None] = []

        for i, valor in enumerate(serie):
            if valor is None:
                salida.append(None)
                continue

            mes = (i % MESES_DEL_ANIO) + 1
            normal = normal_por_mes.get(mes)
            salida.append(None if normal is None else valor - normal)

        return salida


def normales_por_mes(
    serie: list[float | None],
    fechas: list[date],
    desde: date = NORMAL_INICIO,
    hasta: date = NORMAL_FIN,
) -> dict[int, float]:
    """
    Normal climatologica de cada mes, calculada desde la serie.

    **Esta funcion si recibe fechas**, porque no es un metodo del contrato. El
    contraste con `anomalia` es intencional: elegir la normal correcta es
    trivial cuando se conoce la fecha.

    Un mes sin datos en el periodo **no aparece en el resultado**. No se rellena
    con el promedio anual ni con el de los meses vecinos: la normal de un mes es
    la de ese mes, y una inventada produciria anomalias que parecen validas.

    Un mes **con pocos datos** si aparece, y se avisa por registro nombrandolo.
    Ver `_avisar_meses_cortos`: el conteo es de anios con dato y por mes, no del
    largo de la ventana pedida.

    Args:
        serie: valores mensuales, con None donde falta el dato.
        fechas: fecha de cada posicion, del mismo largo que la serie.
        desde, hasta: periodo de la normal, inclusive. Por defecto 1991-2020,
            que es la que fija el charter y usa la linea base.

    Returns:
        `{mes: normal}` con los meses que tienen dato. Puede tener menos de
        doce claves, y `anomalia` devuelve None en las posiciones de los meses
        ausentes.

    Raises:
        ValueError: si las listas tienen largos distintos, o si el periodo esta
            invertido.
    """
    if len(serie) != len(fechas):
        raise ValueError(
            f"La serie tiene {len(serie)} valores y {len(fechas)} fechas. Sin "
            "correspondencia uno a uno no se sabe a que mes pertenece cada valor, "
            "y asignarlo por posicion es justo la suposicion que SC-06 quiere evitar."
        )
    if desde > hasta:
        raise ValueError(f"El periodo esta invertido: desde {desde} hasta {hasta}")

    acumulado: dict[int, list[float]] = defaultdict(list)
    anios_con_dato: dict[int, set[int]] = defaultdict(set)

    for valor, fecha in zip(serie, fechas, strict=True):
        if valor is not None and desde <= fecha <= hasta:
            acumulado[fecha.month].append(valor)
            anios_con_dato[fecha.month].add(fecha.year)

    _avisar_meses_cortos(anios_con_dato)

    return {mes: sum(valores) / len(valores) for mes, valores in sorted(acumulado.items())}


def _avisar_meses_cortos(anios_con_dato: dict[int, set[int]]) -> None:
    """
    Avisa por registro de los meses cuya normal sale de menos de 30 anios.

    **Se cuentan los anios que hay, no la ventana que se pidio.** Una version
    anterior calculaba `(hasta.year - desde.year) + 1`, que es el largo del
    periodo solicitado y no dice nada sobre el dato disponible: con tres anios de
    serie y la ventana 1991-2020 por defecto, el aviso no se disparaba nunca y
    una "normal climatologica" de tres anios pasaba en silencio.

    Es el mismo defecto que `completitud` tenia en H1.5, en otro modulo: contar
    lo que se pidio en vez de lo que se tiene. Lo encontro Alejandro revisando
    H2.4.

    **El conteo es por mes y no global**, porque la normal se usa mes a mes. Un
    mes al que le faltan diez anios produce una normal debil mientras los otros
    once estan completos, y un promedio global no lo mostraria.

    No bloquea: la normal se devuelve igual. Lo que cambia es que el aviso ahora
    dice la verdad.
    """
    cortos = sorted(
        (mes, len(anios))
        for mes, anios in anios_con_dato.items()
        if len(anios) < MINIMO_ANIOS_NORMAL
    )
    if not cortos:
        return

    detalle = ", ".join(f"{NOMBRE_DEL_MES[mes]} ({cuantos})" for mes, cuantos in cortos)
    log.warning(
        "Hay %d mes(es) cuya normal sale de menos de %d anios con dato, que es el "
        "minimo que recomienda la OMM (WMO-No. 1203). Meses y anios disponibles: %s. "
        "La normal se devuelve igual, pero en esos meses es menos estable de lo que "
        "una normal climatologica deberia ser.",
        len(cortos),
        MINIMO_ANIOS_NORMAL,
        detalle,
    )


def anomalia_con_fechas(
    serie: list[float | None],
    fechas: list[date],
    normal_por_mes: dict[int, float],
) -> list[float | None]:
    """
    La anomalia calculada **correctamente**, usando el mes real de cada fecha.

    No es parte del contrato y no pretende serlo: existe para poder **medir**
    cuanto se aparta la version del contrato de la correcta, que es lo que
    sostiene la solicitud SC-06.

    Si SC-06 se aprueba, esta funcion deja de hacer falta: su logica pasa a
    `anomalia` cuando reciba el parametro `meses`.
    """
    if len(serie) != len(fechas):
        raise ValueError(f"La serie tiene {len(serie)} valores y {len(fechas)} fechas.")

    _validar_normales(normal_por_mes)

    salida: list[float | None] = []

    for valor, fecha in zip(serie, fechas, strict=True):
        if valor is None:
            salida.append(None)
            continue

        normal = normal_por_mes.get(fecha.month)
        salida.append(None if normal is None else valor - normal)

    return salida


def _validar_normales(normal_por_mes: dict[int, float]) -> None:
    invalidos = sorted(m for m in normal_por_mes if not 1 <= m <= MESES_DEL_ANIO)
    if invalidos:
        raise ValueError(
            f"Las claves de normal_por_mes deben ser meses de 1 a 12; " f"se recibieron {invalidos}"
        )
