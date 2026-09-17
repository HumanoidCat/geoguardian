"""
Precalcula la normal climatologica 1991-2020 y la publica como archivo estatico.

QUE PROBLEMA RESUELVE

H2.4 dejo el calculo de anomalias contra la normal 1991-2020 en
`backend/senales/anomalias.py`, probado. El contrato las lleva en
`IndiceDerivado.anomalia_temp_c`, y `IndiceDerivado` vive en `analitico.indice`.

**`analitico.indice` no existe.** `obtener_indices` lanza `TablaPendiente`
(repositorio_postgres.py, linea 543) y ninguna ruta de la API expone indices. Es
el mismo hueco que H7.3 encontro con los eventos.

**D-53** ya resolvio esta forma para el SPI-6 de H14.5: calcular al pedirlo en vez
de almacenar. Aca sale todavia mas barato, porque **una normal es diminuta**: doce
valores por distrito y por variable. No es una serie, es una tabla de referencia
de unos kilobytes, y `frontend/public/` ya sirve estaticos por el camino de H6.6.

EL CALCULO NO SE REIMPLEMENTA

`normales_por_mes` es de H2.4 y esta probada. Este guion la llama. Reescribir la
media por mes aca crearia dos implementaciones de la misma cifra, que es
exactamente lo que el CA-5 pide evitar.

TRES DECISIONES QUE CAMBIAN EL NUMERO, TOMADAS A PROPOSITO

**1. Las filas imputadas NO entran.** `crudo.medicion_diaria` marca `imputado`.
El CA-1 pide declarar «cuantos anios tenian dato **de verdad**», y un valor
imputado no es un dato de verdad: es una reconstruccion. Incluirlo inflaria la
cobertura declarada sin agregar observacion. Se cuentan aparte y se informan.

**2. La precipitacion se SUMA por mes; el resto se PROMEDIA.** La normal de lluvia
de octubre es un acumulado mensual -unos 320 mm en Tilaran-, no una media diaria.
Promediar la lluvia daria milimetros por dia, que es otra magnitud. La temperatura
y la humedad si son medias.

**3. Un mes al que le faltan dias no cuenta como mes.** Para una suma esto no es
un detalle: un octubre con veinte dias de dato da un acumulado bajo que parece un
octubre seco. Se exige `COBERTURA_MINIMA` de los dias del mes, y los meses que no
llegan se descartan **antes** de promediar entre anios.

LA RESOLUCION NO ES LA MISMA PARA TODAS LAS VARIABLES

POWER tiene **una sola celda de 0,5 grados sobre todo el canton**, medido en
`basedatos/consultas/extension_y_celdas.sql` y declarado en
`docs/17-documento-tecnico.md`. Solo `precipitacion_mm` varia por distrito; la
temperatura, la humedad y el viento son el mismo valor en los ocho.

Asi que la salida separa las dos cosas: la precipitacion va por distrito y el
resto va como **cantonal**, con su resolucion declarada en el propio archivo. Un
panel que mostrara ocho temperaturas identicas prometeria un detalle que la fuente
no tiene.

Uso, desde la raiz del repositorio y con la base levantada:

    docker compose up -d db
    python frontend/herramientas/generar_normales.py

Historia H7.4. Rubrica de Computacion Grafica, CG-2.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from backend.senales.anomalias import (  # noqa: E402
    MINIMO_ANIOS_NORMAL,
    NORMAL_FIN,
    NORMAL_INICIO,
    normales_por_mes,
)

DESTINO = RAIZ / "frontend" / "public" / "normales" / "normales.json"

# Fraccion de los dias del mes que tienen que traer dato para que el mes cuente.
#
# 0,9 y no 1,0: exigir el mes completo descartaria meses buenos por un dia suelto,
# y POWER tiene huecos aislados. 0,9 sobre un mes de 31 dias deja pasar hasta tres
# dias faltantes. El numero se declara aca, antes de mirar el resultado, para que
# no se elija despues segun que cifra sale mas bonita.
COBERTURA_MINIMA = 0.9

# POR QUE SON SEIS Y NO SIETE: FALTA RADIACION, Y NO ES POR FALTA DE DATO
#
# `frontend/src/datos/cliente.js` ofrece SIETE variables en el grafico de serie;
# aqui hay seis. La que falta es `radiacion_mj_m2`, y conviene decir por que,
# porque el archivo generado declara lo que cubre (CA-1) y un lector que cuente
# las variables va a preguntar.
#
# No es que no haya dato. Medido contra la base el 2026-09-16, en el periodo de
# la normal (1991-01-01 a 2020-12-31):
#
#     filas totales            87664
#     con precipitacion        87664
#     con temperatura media    87664
#     con radiacion            87664     <- cobertura del 100 %, los 8 distritos
#
# Y es una serie CANTONAL, como temperatura, humedad y viento: en los 10958 dias
# del periodo hay CERO dias en que los ocho distritos traigan valores distintos.
# El maximo de valores distintos en un mismo dia es 1.
#
# Asi que quedo fuera por descuido al elegir las seis, no por una limitacion de
# la fuente. Se deja escrito en vez de corregirlo en silencio, y no se agrega
# dentro de H7.4 porque moveria `filas_leidas`, el numero de series, las cuentas
# de `verificar_h74.mjs` y las cifras de la evidencia a ocho dias del Invenio
# Fest, por una variable que ningun criterio de esta historia pide.
#
# Cuando se agregue, es una linea:
#
#     "radiacion_mj_m2": ("media", "Radiacion", "MJ/m2", "canton"),
#
# Como se agrega cada variable de dia a mes, y como se llama en pantalla.
#
# `suma` para la lluvia y `media` para el resto. Ver la nota 2 del encabezado.
VARIABLES = {
    "precipitacion_mm": ("suma", "Precipitacion", "mm", "distrito"),
    "temp_max_c": ("media", "Temperatura maxima", "grados C", "canton"),
    "temp_min_c": ("media", "Temperatura minima", "grados C", "canton"),
    "temp_media_c": ("media", "Temperatura media", "grados C", "canton"),
    "humedad_relativa_pct": ("media", "Humedad relativa", "%", "canton"),
    "viento_ms": ("media", "Viento", "m/s", "canton"),
}

SQL = """
    SELECT codigo_distrito, fecha, {columnas}
      FROM crudo.medicion_diaria
     WHERE fecha BETWEEN %s AND %s
       AND NOT imputado
     ORDER BY codigo_distrito, fecha
"""

SQL_IMPUTADAS = """
    SELECT count(*)
      FROM crudo.medicion_diaria
     WHERE fecha BETWEEN %s AND %s
       AND imputado
"""


def dias_del_mes(anio: int, mes: int) -> int:
    siguiente = datetime.date(anio + (mes == 12), mes % 12 + 1, 1)
    return (siguiente - datetime.date(anio, mes, 1)).days


def mensualizar(
    diarios: dict[datetime.date, float], modo: str
) -> tuple[list[float | None], list[datetime.date]]:
    """Valores diarios -> (serie mensual, fecha del primer dia de cada mes).

    Un mes que no llega a `COBERTURA_MINIMA` sale de la serie con `None`, no con
    el valor incompleto. `normales_por_mes` ignora los `None`, asi que el mes
    corto simplemente no participa del promedio entre anios en vez de arrastrarlo
    hacia abajo.
    """
    por_mes: dict[tuple[int, int], list[float]] = defaultdict(list)
    for fecha, valor in diarios.items():
        por_mes[(fecha.year, fecha.month)].append(valor)

    serie: list[float | None] = []
    fechas: list[datetime.date] = []
    for (anio, mes), valores in sorted(por_mes.items()):
        fechas.append(datetime.date(anio, mes, 1))
        if len(valores) < COBERTURA_MINIMA * dias_del_mes(anio, mes):
            serie.append(None)
        elif modo == "suma":
            serie.append(sum(valores))
        else:
            serie.append(sum(valores) / len(valores))
    return serie, fechas


def anios_por_mes(serie: list[float | None], fechas: list[datetime.date]) -> dict[int, int]:
    """Cuantos anios aportaron dato a la normal de cada mes.

    Es la cifra que el CA-1 pide mostrar en pantalla. `normales_por_mes` la
    calcula internamente para avisar por registro, pero no la devuelve; contarla
    aca es la unica forma de que llegue al archivo. Se cuenta con el mismo
    criterio -anios distintos con valor no nulo dentro del periodo- para que las
    dos cifras no puedan discrepar.
    """
    anios: dict[int, set[int]] = defaultdict(set)
    for valor, fecha in zip(serie, fechas, strict=True):
        if valor is not None and NORMAL_INICIO <= fecha <= NORMAL_FIN:
            anios[fecha.month].add(fecha.year)
    return {mes: len(a) for mes, a in sorted(anios.items())}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--salida", type=Path, default=DESTINO)
    args = p.parse_args()

    from basedatos.conexion import conectar

    print("\nNormal climatologica para el visor · H7.4\n")
    print(f"  periodo   {NORMAL_INICIO} a {NORMAL_FIN}")
    print(f"  cobertura minima por mes  {COBERTURA_MINIMA:.0%} de sus dias")
    print(f"  minimo de anios (OMM)     {MINIMO_ANIOS_NORMAL}")
    print("  filas imputadas           excluidas\n")

    columnas = ", ".join(VARIABLES)
    with conectar() as conexion, conexion.cursor() as cursor:
        cursor.execute(SQL_IMPUTADAS, (NORMAL_INICIO, NORMAL_FIN))
        imputadas = cursor.fetchone()[0]
        cursor.execute(SQL.format(columnas=columnas), (NORMAL_INICIO, NORMAL_FIN))
        filas = cursor.fetchall()

    if not filas:
        print("  la consulta no devolvio ninguna fila.")
        print("  La base esta levantada pero crudo.medicion_diaria esta vacia,")
        print("  o el periodo no tiene datos. No se escribio ningun archivo.\n")
        return 1

    print(f"  {len(filas)} filas leidas, {imputadas} imputadas excluidas")

    # diarios[variable][codigo_distrito][fecha] = valor
    diarios: dict[str, dict[str, dict[datetime.date, float]]] = {
        v: defaultdict(dict) for v in VARIABLES
    }
    for fila in filas:
        codigo, fecha = fila[0], fila[1]
        for indice, variable in enumerate(VARIABLES, start=2):
            if fila[indice] is not None:
                diarios[variable][codigo][fecha] = float(fila[indice])

    salida: dict = {
        "periodo": {"desde": NORMAL_INICIO.isoformat(), "hasta": NORMAL_FIN.isoformat()},
        "generado": datetime.date.today().isoformat(),
        "fuente": "crudo.medicion_diaria",
        "cobertura_minima_del_mes": COBERTURA_MINIMA,
        "minimo_anios_omm": MINIMO_ANIOS_NORMAL,
        "filas_imputadas_excluidas": imputadas,
        # Cuantas filas diarias entraron al calculo. No es una huella criptografica
        # como la de H7.3 -la fuente es una tabla, no un archivo que se pueda
        # resumir-, pero es lo que permite decir si el archivo salio de la serie
        # completa o de una base a medio cargar: 8 distritos por 30 anios son unas
        # 87 600 filas, y cualquier cifra muy por debajo delata una carga parcial.
        "filas_leidas": len(filas),
        "distritos_esperados": 8,
        "variables": {},
    }

    for variable, (modo, etiqueta, unidad, resolucion) in VARIABLES.items():
        por_distrito = diarios[variable]
        if not por_distrito:
            continue

        # La resolucion cantonal no es una simplificacion nuestra: POWER entrega
        # una sola celda. Se toma el primer distrito y se declara, en vez de
        # promediar ocho copias del mismo numero y aparentar un detalle que no hay.
        codigos = sorted(por_distrito) if resolucion == "distrito" else [sorted(por_distrito)[0]]

        normales = {}
        for codigo in codigos:
            serie, fechas = mensualizar(por_distrito[codigo], modo)
            valores = normales_por_mes(serie, fechas)
            anios = anios_por_mes(serie, fechas)
            normales[codigo if resolucion == "distrito" else "canton"] = {
                "normal": {str(m): round(v, 2) for m, v in valores.items()},
                "anios": {str(m): anios.get(m, 0) for m in valores},
            }

        salida["variables"][variable] = {
            "etiqueta": etiqueta,
            "unidad": unidad,
            "agregacion": modo,
            "resolucion": resolucion,
            "normales": normales,
        }

        flacos = sorted(
            m for d in normales.values() for m, n in d["anios"].items() if n < MINIMO_ANIOS_NORMAL
        )
        aviso = (
            f"  meses con menos de {MINIMO_ANIOS_NORMAL} anios: {sorted(set(flacos))}"
            if flacos
            else ""
        )
        print(f"    {etiqueta:22s} {modo:6s} {resolucion:9s} {len(normales)} serie(s){aviso}")

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(
        json.dumps(salida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    try:
        mostrar = args.salida.relative_to(RAIZ)
    except ValueError:
        mostrar = args.salida
    print(f"\n  {mostrar}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
