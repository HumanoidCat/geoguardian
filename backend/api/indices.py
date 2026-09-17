"""
El SPI-6 de un distrito, calculado al pedirlo. Historia H14.5, decision D-53.

QUE HACE

Convierte la serie diaria de lluvia de un distrito en un `IndiceDerivado` por
mes, con `spi_6m`. Es una funcion pura: recibe un diccionario `fecha -> mm` y
devuelve una lista. Ni lee la base ni guarda nada; eso lo hace el repositorio, y
por eso esta funcion se prueba sin PostgreSQL.

POR EL MISMO CAMINO QUE EL ETIQUETADO, Y ESO ES LO QUE IMPORTA

El indice sale de `acumulado_mensual` y de `CalculadorSPI().spi(..., 6, meses)`,
que son las dos llamadas con las que `backend/modelado/etiquetado.py` marco las
sequias del etiquetado de H3.0. No hay una segunda implementacion del SPI en la
API: si la hubiera, la tarjeta y el etiquetado podrian dar dos numeros para el
mismo mes y nadie sabria cual es el bueno.

Eso obliga a que la imagen de la API lleve `scipy` -`CalculadorSPI` ajusta la
gamma con `scipy.stats.gamma.fit`- y `backend/senales/`. Esta escrito en la
enmienda de D-53 y en `infra/docker/api.Dockerfile`.

LA FECHA DEL INDICE ES EL ULTIMO DIA DEL MES, NO EL DIA DE LA CONSULTA

El SPI-6 de julio resume la lluvia de febrero a julio. Rotularlo con la fecha de
hoy diria que habla de hoy, y con CHIRPS el ultimo mes cerrado puede estar a 21 a
51 dias de distancia (D-40). La tarjeta muestra esa fecha al lado del numero
(CA-3), y el contrato lo dice en el docstring de `IndiceDerivado`.

UN MES INCOMPLETO SALE None, NO SE RELLENA

`acumulado_mensual` devuelve None para cualquier mes con un dia sin dato: un
total al que le faltan dias es menor por construccion y entraria como sequia. El
mes en curso y los que la fuente no ha entregado salen None, se devuelven igual
-una fila por mes- y el consumidor dibuja la ausencia (D-07). La primera fila con
valor necesita seis meses cerrados por delante.

EL AJUSTE USA TODA LA SERIE DISPONIBLE

La gamma de cada mes calendario se ajusta sobre todos los anios que la serie
tenga al momento de la consulta, igual que hizo el etiquetado sobre la serie que
tenia el 2026-09-01. D-34 (enmienda del 2026-09-15) midio que la base del ajuste
mueve el numero: la misma ventana da 11 episodios con base corta y 15 con base
larga. Por eso el periodo se declara en la evidencia de H14.5 y no se da por
sobreentendido.
"""

from __future__ import annotations

import calendar
from datetime import date

from backend.modelado.etiquetado import VENTANA_SPI_MESES, acumulado_mensual
from backend.senales.spi import CalculadorSPI
from contratos.esquemas import IndiceDerivado

#: Cuantos decimales se publican. El etiquetado compara contra -1,0 y la tarjeta
#: muestra uno; cuatro alcanzan para que dos consultas del mismo mes se puedan
#: comparar en la evidencia sin arrastrar ruido de coma flotante.
DECIMALES = 4


def ultimo_dia_del_mes(anio: int, mes: int) -> date:
    return date(anio, mes, calendar.monthrange(anio, mes)[1])


def indices_de(
    codigo_distrito: str, precipitacion: dict[date, float | None]
) -> list[IndiceDerivado]:
    """
    Un `IndiceDerivado` por mes de la serie, en orden, con `spi_6m`.

    Args:
        codigo_distrito: el distrito al que pertenece la serie.
        precipitacion: lluvia diaria en mm, con None donde falta. Entra cruda,
            sin filtrar (D-17).

    Returns:
        Una fila por cada mes que aparezca en la serie. `spi_6m` es None donde no
        se pudo calcular: los primeros seis meses, cualquier mes con un dia sin
        dato, y los meses calendario con menos de cuatro acumulados para ajustar.
        Los otros campos del contrato -`spi_1m`, `spi_3m`, `anomalia_temp_c`,
        `dias_sin_lluvia`- quedan None: nadie los calcula todavia y el contrato
        dice que None significa exactamente eso.
    """
    if not precipitacion:
        return []

    totales, meses, claves = acumulado_mensual(precipitacion)
    valores = CalculadorSPI().spi(totales, VENTANA_SPI_MESES, meses)

    return [
        IndiceDerivado(
            codigo_distrito=codigo_distrito,
            fecha=ultimo_dia_del_mes(anio, mes),
            spi_6m=None if valor is None else round(valor, DECIMALES),
        )
        for (anio, mes), valor in zip(claves, valores, strict=True)
    ]
