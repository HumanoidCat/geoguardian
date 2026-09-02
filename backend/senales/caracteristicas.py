"""Rezagos, acumulados y medias moviles sobre las series diarias. Historia H2.5.

===========================================================================
LA REGLA QUE GOBIERNA TODO ESTE MODULO
===========================================================================

**Ninguna caracteristica de la fila `t` puede mirar un dia posterior a `t`.**

No es una preferencia de estilo. El etiquetado de H3.0 define el riesgo del dia
`t` sobre **los siete dias posteriores a `t`, sin incluir `t`**. Si una entrada
mirara hacia adelante, el modelo estaria viendo parte de la respuesta y las
metricas de H3.6 medirian la fuga en vez del aprendizaje.

Ese error no se nota mirando los numeros: **produce metricas mejores**, que es
justo lo que uno querria ver. Por eso la comprobacion no puede ser una lectura
del codigo, y `prueba_no_mira_al_futuro()` la hace por construccion: cambia el
futuro de una serie y exige que el pasado no se mueva ni un decimal.

La ventana INCLUYE el dia `t`. Eso es correcto y no es fuga: la etiqueta empieza
en `t+1`, asi que la lluvia del propio dia `t` es informacion disponible al
momento de predecir.

===========================================================================
LOS NULOS NO SON CEROS
===========================================================================

Por **D-07**, y por la misma razon que lo dice el DDL de `crudo.medicion_diaria`:
cero milimetros de lluvia es una medicion, ausencia de dato no lo es.

Una media movil que trate los huecos como ceros **inventa sequias**. Un acumulado
que los ignore reporta 40 mm en una ventana de la que se observaron dos dias, y
lo hace indistinguible de una ventana completa con los mismos 40 mm.

La regla de este modulo: una ventana con **algun** hueco devuelve `None`, salvo
que se declare explicitamente `minimo_observado`. Y cuando se declara, la funcion
devuelve tambien **cuantos dias vio**, para que quien la use pueda decidir. Nunca
se rellena, nunca se interpola: eso es H1.4 y tiene su propia historia.

===========================================================================
POR QUE NO USA pandas
===========================================================================

`rolling(...).sum()` haria esto en una linea, y la linea seria correcta. Se
escribe a mano por dos razones concretas:

  1. **El manejo de nulos de pandas no es el de este proyecto.** `min_periods`
     por omision descarta la ventana entera, y `skipna=True` suma ignorando los
     huecos: las dos son decisiones legitimas y **ninguna es la que D-07 pide**.
     Envolverlas para corregirlas cuesta mas que escribir el bucle.

  2. **El resto de `backend/senales` no depende de pandas** y agregar la
     dependencia por esto obligaria a una solicitud de cambio sobre
     `requirements.txt`, que es archivo compartido.

===========================================================================
CADA SERIE ES DE UN DISTRITO
===========================================================================

Las funciones reciben **una serie de un solo distrito, ordenada por fecha**. No
reciben la tabla entera y no agrupan: agrupar mal es el defecto clasico de este
calculo -una media movil que cruza el limite entre Tilaran y Quebrada Grande- y
se evita no dandole a la funcion la oportunidad de cometerlo.

`caracteristicas_por_distrito()` hace el agrupamiento, una sola vez, y comprueba
que las fechas vengan ordenadas y sin repetir antes de calcular nada.

Uso:
    from backend.senales.caracteristicas import matriz_de_caracteristicas
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

#: Rezagos y ventanas por omision. Son los que usa H3.3 al construir su matriz.
#:
#: El 3 y el 7 no son redondos por casualidad: 72 h es la ventana del etiquetado
#: de lluvia (D-08) y 7 dias es el horizonte del sistema. El 30 entra para que el
#: modelo pueda ver una escala mensual sin que se le imponga el SPI, que ya es
#: una entrada aparte.
REZAGOS = (1, 2, 3, 7)
VENTANAS = (3, 7, 30)


@dataclass(frozen=True)
class Punto:
    """Un dia de una serie de un distrito. `valor` es None si no se observo."""

    fecha: date
    valor: float | None


@dataclass(frozen=True)
class Resumen:
    """El resultado de una ventana, con cuantos dias se pudieron mirar.

    `observados` NO es decoracion. Un acumulado de 40 mm sobre 3 dias observados
    y uno de 40 mm sobre 1 dia observado son numeros distintos disfrazados de
    iguales, y quien consuma esto tiene derecho a distinguirlos.
    """

    valor: float | None
    observados: int
    esperados: int

    @property
    def completa(self) -> bool:
        return self.observados == self.esperados


def _validar(serie: Sequence[Punto]) -> None:
    """Fechas ordenadas, sin repetir y sin huecos de calendario.

    Un hueco de calendario -que falte la fila del 3 de marzo- **no es lo mismo
    que un valor nulo**: el nulo dice «ese dia no se midio» y la fila ausente
    dice «nadie sabe si ese dia existio». Las ventanas de abajo cuentan
    posiciones, asi que una fila ausente correria la ventana sin avisar y un
    acumulado de 3 dias podria abarcar 5 dias de calendario.
    """
    if not serie:
        return
    for anterior, actual in zip(serie, serie[1:], strict=False):
        if actual.fecha <= anterior.fecha:
            raise ValueError(
                f"la serie no esta ordenada o repite fecha: {anterior.fecha} -> {actual.fecha}"
            )
        if actual.fecha - anterior.fecha != timedelta(days=1):
            raise ValueError(
                f"hueco de calendario entre {anterior.fecha} y {actual.fecha}. "
                "Una fila ausente no es un valor nulo: hay que completar el "
                "calendario con filas de valor None antes de llamar aca."
            )


def rezago(serie: Sequence[Punto], k: int) -> list[float | None]:
    """El valor de hace `k` dias. `None` en las primeras `k` filas y en los huecos.

    Las primeras `k` filas devuelven `None` y **no se recortan**: la salida tiene
    siempre el mismo largo que la entrada, para que se pueda poner al lado de
    otras caracteristicas sin alinear indices a mano. Alinear a mano es de donde
    salen los desfases de un dia que nadie encuentra despues.
    """
    if k < 1:
        raise ValueError(f"el rezago tiene que ser al menos 1 dia, no {k}")
    _validar(serie)
    return [serie[i - k].valor if i >= k else None for i in range(len(serie))]


def _ventana(serie: Sequence[Punto], i: int, dias: int) -> tuple[list[float], int]:
    """Los valores observados de la ventana que TERMINA en `i`, y cuantos son."""
    inicio = i - dias + 1
    if inicio < 0:
        return [], 0
    trozo = serie[inicio : i + 1]
    return [p.valor for p in trozo if p.valor is not None], len(trozo)


def acumulado(
    serie: Sequence[Punto], dias: int, minimo_observado: int | None = None
) -> list[Resumen]:
    """Suma de la ventana de `dias` que **termina en la fila actual**.

    Sin `minimo_observado`, una ventana con cualquier hueco devuelve `None`. Con
    el, se suma si hay al menos esa cantidad de dias observados, y `Resumen` dice
    cuantos fueron.

    La ventana incluye el dia actual. Para lluvia con `dias=3` esto es el
    acumulado de 72 h del etiquetado, y es la entrada que mas se parece a la
    respuesta **sin serla**: la etiqueta mira los 7 dias siguientes.
    """
    if dias < 1:
        raise ValueError(f"la ventana tiene que ser de al menos 1 dia, no {dias}")
    _validar(serie)
    salida: list[Resumen] = []
    for i in range(len(serie)):
        vistos, esperados = _ventana(serie, i, dias)
        if esperados == 0:
            salida.append(Resumen(None, 0, dias))
            continue
        suficiente = (
            len(vistos) == esperados
            if minimo_observado is None
            else len(vistos) >= minimo_observado
        )
        salida.append(Resumen(sum(vistos) if suficiente else None, len(vistos), esperados))
    return salida


def media_movil(
    serie: Sequence[Punto], dias: int, minimo_observado: int | None = None
) -> list[Resumen]:
    """Media de la ventana de `dias` que termina en la fila actual.

    **Se divide entre los dias OBSERVADOS, no entre `dias`.** Dividir entre el
    largo nominal contando los huecos como ceros es el error que inventa sequias:
    una ventana de 30 dias con 10 observados y 60 mm daria 2 mm/dia en vez de 6.
    """
    if dias < 1:
        raise ValueError(f"la ventana tiene que ser de al menos 1 dia, no {dias}")
    _validar(serie)
    salida: list[Resumen] = []
    for i in range(len(serie)):
        vistos, esperados = _ventana(serie, i, dias)
        if esperados == 0:
            salida.append(Resumen(None, 0, dias))
            continue
        suficiente = (
            len(vistos) == esperados
            if minimo_observado is None
            else len(vistos) >= minimo_observado
        )
        valor = sum(vistos) / len(vistos) if suficiente and vistos else None
        salida.append(Resumen(valor, len(vistos), esperados))
    return salida


def matriz_de_caracteristicas(
    serie: Sequence[Punto],
    *,
    prefijo: str,
    rezagos: Sequence[int] = REZAGOS,
    ventanas: Sequence[int] = VENTANAS,
    minimo_observado: int | None = None,
) -> list[dict[str, float | None]]:
    """Una fila de caracteristicas por dia, con nombres estables.

    Los nombres se arman como `{prefijo}_rez{k}`, `{prefijo}_acum{n}` y
    `{prefijo}_media{n}`. Son estables a proposito: la tabla de H3.6 compara
    estimadores entre si, y si los nombres cambian entre corridas deja de poder
    hacerlo.

    Se agrega `{prefijo}_acum{n}_observados` porque el modelo tiene derecho a
    saber que una ventana venia incompleta. Es la diferencia entre «llovio poco»
    y «no se midio», que es la misma distincion de D-07 llevada a la entrada del
    modelo.
    """
    _validar(serie)
    filas: list[dict[str, float | None]] = [{} for _ in serie]

    for k in rezagos:
        for i, v in enumerate(rezago(serie, k)):
            filas[i][f"{prefijo}_rez{k}"] = v

    for n in ventanas:
        for i, r in enumerate(acumulado(serie, n, minimo_observado)):
            filas[i][f"{prefijo}_acum{n}"] = r.valor
            filas[i][f"{prefijo}_acum{n}_observados"] = float(r.observados)
        for i, r in enumerate(media_movil(serie, n, minimo_observado)):
            filas[i][f"{prefijo}_media{n}"] = r.valor

    return filas


def caracteristicas_por_distrito(
    series: dict[str, Sequence[Punto]], *, prefijo: str, **opciones
) -> dict[str, list[dict[str, float | None]]]:
    """Aplica `matriz_de_caracteristicas` por distrito, sin cruzar fronteras.

    Existe para que nadie tenga que acordarse de agrupar. Una media movil que
    cruza de un distrito a otro es un defecto que no levanta ninguna excepcion y
    que no se ve en los numeros: da un valor plausible, calculado sobre dos
    lugares distintos.
    """
    return {
        distrito: matriz_de_caracteristicas(serie, prefijo=prefijo, **opciones)
        for distrito, serie in series.items()
    }
