"""
Reporte de calidad de los datos climaticos. Historia H1.5, rubrica OE1.

Produce `ReporteCalidad` del contrato, **uno por fuente y variable**. Que el
esquema ya este partido asi no es casual: la completitud no es un numero del
proyecto, es un numero por fuente, y las fuentes de este proyecto no se
comportan igual.

LO QUE ESTE MODULO EXISTE PARA EVITAR
-------------------------------------

Un reporte que diga **"0 % de faltantes, calidad excelente"** seria tecnicamente
cierto y enganoso.

CHIRPS y POWER son productos de malla, no estaciones. Una estacion se averia y
deja un hueco; un producto de malla **siempre devuelve un valor**, porque lo que
entrega es una estimacion, no una observacion puntual.

    0 % de faltantes no significa 100 % observado:
    significa que el producto no puede reportar ausencia.

Y la prueba no es la documentacion de la fuente, es **medicion propia**: la
incidencia **I-05** registra que POWER devuelve valores identicos para los ocho
distritos, todos los dias. Ocho ubicaciones separadas por kilometros que
devuelven el mismo numero no fueron observadas en ninguna de las ocho. Y algo
que nunca se observo tampoco puede faltar.

TRES FORMAS DISTINTAS DE AUSENCIA
---------------------------------

| Fuente | Puede reportar ausencia | Por que |
|---|---|---|
| CHIRPS, POWER | No | Productos de malla: siempre hay valor |
| Sentinel-2 | Si | La nubosidad tapa el suelo y el hueco es real |
| FIRMS | No, al reves | Un dia sin detecciones es un **cero**, no un hueco |

Meterlas en la misma tabla pierde justo lo que hace util al reporte.

ATIPICOS: DOS CATEGORIAS QUE NO SE MEZCLAN
------------------------------------------

Un dia de 300 mm en Tilaran **no es un error de dato**: es el temporal del 5 de
octubre de 2017, que esta en el catalogo de H4.3. Un reporte que lo marque como
atipico invita a limpiarlo, y limpiarlo borraria justamente los dias que el
modelo tiene que aprender a predecir.

Por eso se separan:

- **Fuera de rango fisico**: humedad de 120 %, precipitacion negativa. Eso si es
  un error del dato y hay que corregirlo.
- **Extremo estadistico**: un valor en la cola alta. Es **candidato a evento
  real**, y se reporta como tal, no como defecto.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from contratos.enums import MetodoImputacion
from contratos.esquemas import ReporteCalidad

# Rangos fisicamente posibles para el canton. Un valor fuera de aqui es un error
# del dato, no un evento extremo. Se eligen anchos a proposito: la idea es
# atrapar errores groseros de la fuente, no discutir climatologia.
RANGOS_FISICOS: dict[str, tuple[float, float]] = {
    "temp_max_c": (0.0, 50.0),
    "temp_min_c": (-5.0, 40.0),
    "temp_media_c": (0.0, 45.0),
    "humedad_relativa_pct": (0.0, 100.0),
    "viento_ms": (0.0, 60.0),
    "radiacion_mj_m2": (0.0, 45.0),
    "precipitacion_mm": (0.0, 500.0),
}

# Que fuente aporta cada variable, segun la decision D-15.
FUENTE_DE: dict[str, str] = {
    "precipitacion_mm": "chirps",
    "temp_max_c": "power",
    "temp_min_c": "power",
    "temp_media_c": "power",
    "humedad_relativa_pct": "power",
    "viento_ms": "power",
    "radiacion_mj_m2": "power",
}

# Fuentes que no pueden reportar ausencia, y por que.
NO_REPORTAN_AUSENCIA: dict[str, str] = {
    "chirps": (
        "Producto de malla: satelite mas estaciones interpoladas. Cubre toda su "
        "malla, asi que un 0 % de faltantes no indica cobertura observacional."
    ),
    "power": (
        "Reanalisis MERRA-2: asimila observaciones dentro de un modelo y produce "
        "campo completo por construccion. No tiene mecanismo para devolver "
        "ausencia. Ver la incidencia I-05."
    ),
}

PERCENTIL_EXTREMO = 99.0


class Serie:
    """Una variable de un distrito: fechas y valores, con los huecos incluidos."""

    def __init__(
        self,
        codigo_distrito: str,
        variable: str,
        fechas: list[date],
        valores: list[float | None],
    ) -> None:
        if len(fechas) != len(valores):
            raise ValueError(
                f"{codigo_distrito}/{variable}: {len(fechas)} fechas y "
                f"{len(valores)} valores. Sin correspondencia uno a uno no se "
                "puede saber que dia falta."
            )
        self.codigo_distrito = codigo_distrito
        self.variable = variable
        self.fechas = fechas
        self.valores = valores


def completitud(series: list[Serie]) -> list[ReporteCalidad]:
    """
    Un `ReporteCalidad` por fuente y variable, con su interpretacion.

    **El porcentaje se calcula, no se declara.** Sale de contar los valores
    presentes contra los dias esperados del rango, no de lo que diga la fuente
    sobre si misma.

    `total_esperado` son los dias del calendario entre la primera y la ultima
    fecha, no el numero de filas. Si la carga omitio dias enteros, contar filas
    daria 100 % de completitud sobre una serie con huecos: el hueco estaria en
    las filas que no existen.

    **`total_presente` cuenta dias distintos, no filas.** Es la otra mitad del
    mismo argumento y se corrigio tras la revision del PR #144.

    Una fila duplicada compensa un dia ausente: si la carga metio el 3 de enero
    dos veces y por eso nunca cargo el 9, hay diez filas para nueve dias y
    contar filas daria 0 % de faltantes con un dia realmente ausente.

    Los duplicados **se reportan**, no se recortan. La version anterior
    recortaba el porcentaje negativo con `max(pct, 0.0)` para que no saliera un
    numero sin sentido, y con eso borraba la unica senal de que habia
    duplicados. Un porcentaje negativo no era un error de calculo: era el aviso.
    """
    por_variable: dict[str, list[Serie]] = defaultdict(list)
    for s in series:
        por_variable[s.variable].append(s)

    salida: list[ReporteCalidad] = []

    for variable, grupo in sorted(por_variable.items()):
        fuente = FUENTE_DE.get(variable, "desconocida")

        inicio = min(min(s.fechas) for s in grupo)
        fin = max(max(s.fechas) for s in grupo)
        dias_calendario = (fin - inicio).days + 1

        distritos = len({s.codigo_distrito for s in grupo})
        esperado = dias_calendario * distritos

        # Dias distintos con dato, no filas. Una fila repetida no aporta un dia
        # nuevo y no puede compensar uno ausente.
        dias_con_dato = {
            (s.codigo_distrito, f)
            for s in grupo
            for f, v in zip(s.fechas, s.valores, strict=True)
            if v is not None
        }
        presente = len(dias_con_dato)

        filas_con_dato = sum(1 for s in grupo for v in s.valores if v is not None)
        duplicados = filas_con_dato - presente

        pct = 0.0 if esperado == 0 else 100 * (esperado - presente) / esperado

        salida.append(
            ReporteCalidad(
                fuente=fuente,
                variable=variable,
                periodo_inicio=inicio,
                periodo_fin=fin,
                total_esperado=esperado,
                total_presente=presente,
                pct_faltantes=round(min(max(pct, 0.0), 100.0), 4),
                metodo_imputacion=MetodoImputacion.SIN_IMPUTAR,
                observaciones=_observacion_de_completitud(
                    fuente, pct, distritos, dias_calendario, duplicados
                ),
            )
        )

    return salida


def _observacion_de_completitud(
    fuente: str,
    pct_faltantes: float,
    distritos: int,
    dias: int,
    duplicados: int = 0,
) -> str:
    base = f"{distritos} distritos x {dias} dias de calendario."

    # El duplicado va primero y siempre: es un defecto de la carga, y ademas
    # puede estar tapando dias ausentes. Quien lea el reporte tiene que verlo
    # antes que cualquier interpretacion del porcentaje.
    if duplicados > 0:
        base = (
            f"{base} ATENCION: {duplicados} filas duplicadas, mismo distrito y "
            "misma fecha mas de una vez. Revisar la carga: un INSERT sin "
            "ON CONFLICT o un rango pedido dos veces lo produce. El porcentaje "
            "de faltantes de abajo ya descuenta los duplicados, pero mientras "
            "existan la serie no es lo que dice ser."
        )

    if fuente not in NO_REPORTAN_AUSENCIA:
        return f"{base} Fuente sin caracterizar: interpretar el porcentaje con cuidado."

    if pct_faltantes == 0:
        return (
            f"{base} 0 % de faltantes NO significa 100 % observado. "
            f"{NO_REPORTAN_AUSENCIA[fuente]}"
        )

    return (
        f"{base} Faltantes en una fuente que no deberia poder reportarlos "
        f"({NO_REPORTAN_AUSENCIA[fuente]}) Revisar la carga: es mas probable un "
        "fallo de descarga que un hueco de la fuente."
    )


def fuera_de_rango_fisico(series: list[Serie]) -> list[tuple[str, str, date, float]]:
    """
    Valores imposibles: `(distrito, variable, fecha, valor)`.

    **Esto si es error del dato.** Una humedad de 120 % o una precipitacion
    negativa no son eventos extremos: son defectos, y hay que corregirlos en la
    fuente o en la carga.
    """
    salida: list[tuple[str, str, date, float]] = []

    for s in series:
        rango = RANGOS_FISICOS.get(s.variable)
        if rango is None:
            continue
        minimo, maximo = rango

        for f, v in zip(s.fechas, s.valores, strict=True):
            if v is not None and not minimo <= v <= maximo:
                salida.append((s.codigo_distrito, s.variable, f, v))

    return salida


def extremos_estadisticos(
    series: list[Serie],
    percentil: float = PERCENTIL_EXTREMO,
) -> list[tuple[str, str, date, float]]:
    """
    Valores en la cola alta de su propia distribucion.

    **No son defectos: son candidatos a evento real.** Se calculan por distrito
    y variable, contra la distribucion de ese distrito, porque un acumulado
    normal en Arenal puede ser extremo en Libano.

    Se reportan para poder cruzarlos contra el catalogo de eventos historicos de
    H4.3. Un extremo que coincide con un evento catalogado no es un dato
    sospechoso: es la confirmacion de que la serie capta los eventos reales.

    **Solo mira la cola alta, y es deliberado.** Para lluvia intensa el extremo
    es el maximo. Para sequia el extremo es la cola **baja** de precipitacion, y
    ese caso no se cubre aqui a proposito: un dia de 0 mm en estacion seca es lo
    normal, no un atipico, y lo que convierte una racha seca en sequia es su
    duracion y no el valor de un dia. Eso lo resuelve el SPI de H2.3, que
    mide acumulados de tres meses contra la distribucion historica del mismo
    mes. Buscarlo aqui produciria miles de falsos positivos cada verano.
    """
    salida: list[tuple[str, str, date, float]] = []

    for s in series:
        presentes = [v for v in s.valores if v is not None]
        if len(presentes) < 20:
            continue

        umbral = _percentil(presentes, percentil)

        for f, v in zip(s.fechas, s.valores, strict=True):
            if v is not None and v > umbral:
                salida.append((s.codigo_distrito, s.variable, f, v))

    return salida


def cruzar_con_catalogo(
    extremos: list[tuple[str, str, date, float]],
    eventos: list[tuple[str, date, date | None]],
    holgura_dias: int = 3,
) -> tuple[int, int]:
    """
    Cuantos extremos coinciden con un evento catalogado.

    Args:
        extremos: salida de `extremos_estadisticos`.
        eventos: `(codigo_distrito, fecha_inicio, fecha_fin)` del catalogo de
            H4.3. `fecha_fin` puede ser None para eventos de un dia.
        holgura_dias: margen a cada lado. El evento se reporta cuando se
            registra el dano, que puede ser uno o dos dias despues de la lluvia
            que lo causo.

    Returns:
        `(coincidentes, total)`.

    **Un extremo que coincide con un evento catalogado no es un atipico
    sospechoso.** Es evidencia de que la serie capta lo que ocurrio.
    """
    if holgura_dias < 0:
        raise ValueError(f"La holgura no puede ser negativa, se recibio {holgura_dias}")

    ventanas: dict[str, list[tuple[date, date]]] = defaultdict(list)
    for distrito, inicio, fin in eventos:
        real_fin = fin or inicio
        ventanas[distrito].append(
            (inicio - timedelta(days=holgura_dias), real_fin + timedelta(days=holgura_dias))
        )

    coincidentes = sum(
        1
        for distrito, _, fecha, _ in extremos
        if any(desde <= fecha <= hasta for desde, hasta in ventanas.get(distrito, []))
    )

    return coincidentes, len(extremos)


def variacion_espacial(series: list[Serie]) -> dict[str, float]:
    """
    Porcentaje de dias en que una variable difiere entre distritos.

    Es la medida del sesgo espacial: una variable que da el mismo valor en los
    ocho distritos **no aporta ninguna capacidad de distinguirlos**, por mas
    filas que tenga.

    Un 0 % aqui es el sintoma de la incidencia I-05, y es tambien la prueba de
    que ese dato no fue observado en ninguno de los ocho puntos.
    """
    por_variable: dict[str, list[Serie]] = defaultdict(list)
    for s in series:
        por_variable[s.variable].append(s)

    salida: dict[str, float] = {}

    for variable, grupo in sorted(por_variable.items()):
        if len(grupo) < 2:
            continue

        por_fecha: dict[date, set[float]] = defaultdict(set)
        for s in grupo:
            for f, v in zip(s.fechas, s.valores, strict=True):
                if v is not None:
                    por_fecha[f].add(round(v, 6))

        if not por_fecha:
            continue

        distintos = sum(1 for valores in por_fecha.values() if len(valores) > 1)
        salida[variable] = round(100 * distintos / len(por_fecha), 2)

    return salida


def _percentil(muestra: list[float], percentil: float) -> float:
    """
    Interpolacion lineal, metodo 7 de Hyndman y Fan. Igual que en H2.7.

    Rechaza la muestra vacia en lugar de confiar en que quien llama la filtre.
    Hoy `extremos_estadisticos` descarta las series de menos de 20 valores, asi
    que el caso no se da; pero la proteccion vivia en el llamador y no en la
    funcion, y desde otro punto de llamada esto reventaba con un `IndexError`
    que no explicaba nada.
    """
    if not muestra:
        raise ValueError("No se puede calcular un percentil de una muestra vacia")

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
