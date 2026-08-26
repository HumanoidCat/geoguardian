"""Genera las etiquetas de los tres eventos y mide su distribucion de clases.

Historia **H3.0**. Criterios en
`docs/evidencias/objetivos/H3.0-criterios-aceptacion.md`.

QUE HACE

1. Lee de la base la precipitacion diaria y los focos de calor.
2. Etiqueta cada distrito y cada fecha a siete dias, con `etiquetado.py`.
3. **Mide la distribucion de clases** por evento y por distrito.
4. Aplica el umbral de **CA-6** y declara que eventos NO son modelables.

El umbral se fijo **antes** de mirar el dato, y esta escrito en los criterios:

    menos de 30 ventanas positivas en total          -> no se modela
    menos de 10 en cualquier particion de entrenamiento -> no se modela

POR QUE NO ESCRIBE EN LA BASE TODAVIA

Este programa produce el artefacto y la medicion. Persistir las etiquetas es
util cuando H3.2 haya decidido las particiones, porque la tabla tendria que
llevar a que pliegue va cada fila. Escribirla antes seria adivinar el esquema.

Uso:
    python -m backend.modelado.generar_etiquetas
    python -m backend.modelado.generar_etiquetas --salida datos/procesados/etiquetas.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado.etiquetado import (  # noqa: E402
    HORIZONTE_DIAS,
    ULTIMO_ANIO,
    Etiqueta,
    etiquetar_distrito,
)
from contratos.enums import NivelRiesgo, TipoEvento  # noqa: E402

# CA-6, fijado antes de ver el dato.
MINIMO_POSITIVAS_TOTAL = 30
MINIMO_POSITIVAS_POR_PARTICION = 10

# H3.2 todavia no existe. Para poder decir algo hoy sobre "por particion", se
# supone la forma mas comun de ventana expansiva: cinco pliegues. Si H3.2 elige
# otra, esta cuenta se rehace, y por eso se declara en la salida.
PLIEGUES_SUPUESTOS = 5


def leer_precipitacion(cursor) -> dict[str, dict[date, float | None]]:
    cursor.execute(
        """
        SELECT codigo_distrito, fecha, precipitacion_mm
        FROM crudo.medicion_diaria
        ORDER BY codigo_distrito, fecha
        """
    )
    salida: dict[str, dict[date, float | None]] = defaultdict(dict)
    for codigo, fecha, valor in cursor.fetchall():
        salida[codigo][fecha] = None if valor is None else float(valor)
    return salida


def leer_focos(cursor) -> dict[str, list[date]]:
    """Solo los focos con distrito asignado. Los 252 de fuera del canton no etiquetan nada."""
    cursor.execute(
        """
        SELECT codigo_distrito, fecha
        FROM crudo.foco_calor
        WHERE codigo_distrito IS NOT NULL
        ORDER BY codigo_distrito, fecha
        """
    )
    salida: dict[str, list[date]] = defaultdict(list)
    for codigo, fecha in cursor.fetchall():
        salida[codigo].append(fecha)
    return salida


def distribucion(etiquetas: list[Etiqueta], evento: TipoEvento) -> Counter:
    return Counter(e.nivel(evento) for e in etiquetas)


def episodios(etiquetas: list[Etiqueta], evento: TipoEvento) -> int:
    """Rachas de filas ALTO consecutivas. **Es la cuenta que importa.**

    Descubierto al correr el etiquetado: **un solo foco de calor marca siete
    filas como ALTO**, porque es la misma deteccion vista desde siete `t`
    distintos. Contar filas positivas sobreestima la muestra por un factor de
    hasta siete.

    Las siete filas comparten la etiqueta y casi todas sus caracteristicas: no
    son siete observaciones, son una. Un modelo que las vea como independientes
    cree tener siete veces mas evidencia de la que hay, y una particion que las
    corte por el medio deja el mismo episodio a los dos lados, que es fuga.

    Vale igual para lluvia intensa: un temporal de 72 h aparece en varias filas
    seguidas.

    **CA-6 se evalua contra este numero, no contra el conteo de filas.**
    """
    cuenta = 0
    anterior_alto = False
    for e in sorted(etiquetas, key=lambda x: (x.codigo_distrito, x.fecha)):
        alto = e.nivel(evento) is NivelRiesgo.ALTO
        if alto and not anterior_alto:
            cuenta += 1
        anterior_alto = alto
    return cuenta


def informar(todas: list[Etiqueta], por_distrito: dict[str, list[Etiqueta]]) -> list[str]:
    """Imprime la distribucion y devuelve los eventos que NO son modelables."""
    no_modelables: list[str] = []

    for evento in TipoEvento:
        print(f"\n{evento.value.upper()}")
        cuenta = distribucion(todas, evento)
        total = sum(cuenta.values())
        sin_dato = cuenta.get(None, 0)

        for nivel in (NivelRiesgo.ALTO, NivelRiesgo.MEDIO, NivelRiesgo.BAJO):
            n = cuenta.get(nivel, 0)
            if n == 0 and nivel is NivelRiesgo.MEDIO and evento is TipoEvento.INCENDIO:
                print(f"  {nivel.value:6} {n:>8}          no existe para este evento (D-25)")
                continue
            print(f"  {nivel.value:6} {n:>8}   {100 * n / total:5.2f} %")
        if sin_dato:
            print(f"  {'sin dato':6} {sin_dato:>8}   {100 * sin_dato / total:5.2f} %")

        # La clase minoritaria es la que decide. Para incendio y lluvia es ALTO.
        #
        # Se cuentan EPISODIOS, no filas: un foco marca siete filas seguidas y
        # las siete son la misma deteccion. Ver `episodios()`.
        filas_alto = cuenta.get(NivelRiesgo.ALTO, 0)
        positivas = sum(episodios(lista, evento) for lista in por_distrito.values())
        por_pliegue = positivas / PLIEGUES_SUPUESTOS

        # El porcentaje sobre el total mezcla filas observadas con filas que
        # nadie miro, y para incendio esa mezcla son 29 224 filas anteriores al
        # satelite. Se informan los dos, porque el que vale es el segundo.
        observadas = total - sin_dato
        print(f"\n  filas en alto            {filas_alto}")
        if sin_dato:
            print(f"    sobre el total         {100 * filas_alto / total:5.2f} %")
            print(f"    sobre las OBSERVADAS   {100 * filas_alto / observadas:5.2f} %   <- el real")
        print(f"  EPISODIOS distintos      {positivas}   <- lo que decide CA-6")
        if positivas:
            print(f"  filas por episodio       {filas_alto / positivas:.1f}")
        print(f"  episodios por pliegue    {por_pliegue:.1f}   (con {PLIEGUES_SUPUESTOS} pliegues)")

        razones = []
        if positivas < MINIMO_POSITIVAS_TOTAL:
            razones.append(f"{positivas} episodios en total, el minimo es {MINIMO_POSITIVAS_TOTAL}")
        if por_pliegue < MINIMO_POSITIVAS_POR_PARTICION:
            razones.append(
                f"{por_pliegue:.1f} por pliegue, el minimo es {MINIMO_POSITIVAS_POR_PARTICION}"
            )

        if razones:
            no_modelables.append(evento.value)
            print(f"\n  NO MODELABLE (CA-6): {'; '.join(razones)}")
        else:
            print("\n  modelable")

        # Por distrito, que es donde se ve si el evento vive en pocos.
        #
        # El denominador son las filas OBSERVADAS del distrito, no todas. Con
        # todas, el porcentaje de incendio queda diluido por las 3 652 fechas
        # anteriores al satelite y **deja de ser comparable con lo que midio
        # R16**, que solo pudo medir sobre el periodo con datos. Ver I-11.
        print(f"\n  {'distrito':10}{'alto':>8}{'observadas':>12}{'%':>8}")
        porcentajes: dict[str, float] = {}
        for codigo in sorted(por_distrito):
            c = distribucion(por_distrito[codigo], evento)
            observadas_d = sum(n for nivel, n in c.items() if nivel is not None)
            a = c.get(NivelRiesgo.ALTO, 0)
            porcentajes[codigo] = 100 * a / observadas_d if observadas_d else 0.0
            print(f"  {codigo:10}{a:>8}{observadas_d:>12}{porcentajes[codigo]:>7.2f}%")

        if evento is TipoEvento.INCENDIO:
            comprobar_r16(porcentajes)

    return no_modelables


# R16, medido por Cesar en H1.2 sobre los 242 focos del canton: entre 2,6 % y
# 2,9 % de las ventanas positivas en Santa Rosa, Libano y Tierras Morenas.
DISTRITOS_ACTIVOS = ("50804", "50805", "50806")  # D-25
BANDA_R16 = (2.4, 3.1)  # la medicion es 2,6-2,9; se admite un margen de 0,2


def comprobar_r16(porcentajes: dict[str, float]) -> None:
    """CA-7 contrastado con **numeros**, no leyendo el orden de una tabla.

    Escrito el 2026-08-26, despues de I-11. CA-7 pedia reproducir R16 y la
    evidencia comparo **el ranking** de los ocho distritos —que salia bien— sin
    comparar nunca los porcentajes contra la banda medida.

    Con el defecto de cobertura adentro, los tres activos daban 2,07 %, 1,83 % y
    1,80 % contra una banda de 2,6-2,9 %. **Los tres por debajo, y nadie lo
    noto**, porque el orden seguia siendo el correcto.

    Un criterio que dice «se contrasta contra X» y se cumple mirando otra cosa no
    es un criterio: es una intencion.
    """
    print(f"\n  CA-7 · contra R16, banda {BANDA_R16[0]:.1f}-{BANDA_R16[1]:.1f} %:")
    for codigo in DISTRITOS_ACTIVOS:
        p = porcentajes.get(codigo, 0.0)
        dentro = BANDA_R16[0] <= p <= BANDA_R16[1]
        print(f"    {codigo}   {p:5.2f} %   {'OK' if dentro else 'FUERA DE BANDA'}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--salida", type=Path, default=RAIZ / "datos" / "procesados" / "etiquetas.csv")
    argumentos = p.parse_args()

    from basedatos.conexion import conectar

    print("Etiquetado de los tres eventos · H3.0")
    print(f"  horizonte      {HORIZONTE_DIAS} dias, ventana (t, t+{HORIZONTE_DIAS}]")
    print(f"  hasta          {ULTIMO_ANIO}, donde termina la serie de focos")

    with conectar() as conexion, conexion.cursor() as cursor:
        precipitacion = leer_precipitacion(cursor)
        focos = leer_focos(cursor)

    por_distrito: dict[str, list[Etiqueta]] = {}
    for codigo, serie in sorted(precipitacion.items()):
        fechas = sorted(serie)
        # El ultimo `t` etiquetable es aquel cuyo horizonte completo cabe dentro
        # del ultimo anio con focos.
        hasta = min(max(fechas), date(ULTIMO_ANIO, 12, 31)) - timedelta(days=HORIZONTE_DIAS)
        por_distrito[codigo] = etiquetar_distrito(
            codigo, serie, focos.get(codigo, []), min(fechas), hasta
        )

    todas = [e for lista in por_distrito.values() for e in lista]
    print(f"  filas          {len(todas)} · {len(por_distrito)} distritos")

    no_modelables = informar(todas, por_distrito)

    argumentos.salida.parent.mkdir(parents=True, exist_ok=True)
    with argumentos.salida.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["codigo_distrito", "fecha", "sequia", "lluvia_intensa", "incendio"])
        for e in todas:
            escritor.writerow(
                [
                    e.codigo_distrito,
                    e.fecha.isoformat(),
                    e.sequia.value if e.sequia else "",
                    e.lluvia_intensa.value if e.lluvia_intensa else "",
                    e.incendio.value if e.incendio else "",
                ]
            )
    print(f"\nEscrito {argumentos.salida.relative_to(RAIZ)}")

    if no_modelables:
        print(f"\nEventos NO modelables por CA-6: {', '.join(no_modelables)}")
        print("Es un resultado, no un fallo. Se declara y se registra.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
