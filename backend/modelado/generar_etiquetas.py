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

# ANTES SE SUPONIAN CINCO PLIEGUES Y SE DIVIDIA. AHORA SE MIDEN.
#
# Este modulo decia:
#
#     # H3.2 todavia no existe. Para poder decir algo hoy sobre "por particion",
#     # se supone la forma mas comun de ventana expansiva: cinco pliegues.
#     PLIEGUES_SUPUESTOS = 5
#
# y evaluaba CA-6 contra `episodios_totales / 5`. Era honesto cuando se escribio
# -H3.2 no existia- y **dejo de serlo el dia que H3.2 se cerro**, sin que nada
# avisara.
#
# EL PROBLEMA NO ES LA APROXIMACION: ES QUE MIDE OTRA COSA
#
# CA-6 dice «menos de 10 en **cualquier** particion de entrenamiento -> no se
# modela». Eso es un **minimo**, y una division da un **promedio**.
#
# Con ventana expansiva no son intercambiables: el pliegue 1 entrena con la
# rebanada mas chica y el 5 con casi toda la serie. El promedio puede quedar
# comodo mientras el primero no llega. **Un evento podria declararse modelable
# violando el criterio que dice serlo.**
#
# Se detecto el 2026-09-01, al revisar por que la sequia bajo de 110 a 78
# episodios con D-32 (ver I-18). 78/5 = 15,6 pasa el umbral de 10; lo que nadie
# habia medido es cuantos tiene el pliegue 1.
from backend.modelado.particion import particionar  # noqa: E402


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


def episodios_por_pliegue(
    por_distrito: dict[str, list[Etiqueta]], evento: TipoEvento
) -> list[int] | None:
    """Episodios en el **entrenamiento** de cada pliegue de H3.2.

    Devuelve `None` si la particion no se puede calcular -por ejemplo porque el
    periodo observado del evento no alcanza para los bloques pedidos-. `None` es
    «no se pudo medir», que no es lo mismo que cero y no se debe tratar igual.

    Se cuenta sobre el ENTRENAMIENTO y no sobre el pliegue entero porque CA-6
    habla de «particion de entrenamiento»: lo que hace falta para aprender una
    clase es haberla visto al ajustar, no al evaluar.
    """
    try:
        pliegues = particionar(evento)
    except Exception:  # noqa: BLE001 - periodo insuficiente u otro motivo declarado
        return None

    # Se cuenta a nivel CANTON, por D-34: un episodio que pega en los ocho
    # distritos es uno, no ocho.
    canton = rachas_del_canton(por_distrito, evento)
    return [
        sum(1 for i, f in canton if i >= desde and f <= hasta)
        for desde, hasta in (p.entrenamiento for p in pliegues)
    ]


def rachas_del_canton(
    por_distrito: dict[str, list[Etiqueta]], evento: TipoEvento
) -> list[tuple[date, date]]:
    """Episodios del **canton**: rachas de dias en que ALGUN distrito esta ALTO.

    POR QUE NO SE SUMAN LOS DE CADA DISTRITO. **D-34.**

    Una sequia que pega en los ocho distritos es UN fenomeno, no ocho. Sumando
    por distrito contaba ocho veces, y **seis de las trece sequias del periodo
    pegan en los ocho**.

    Peor: los ocho distritos comparten la misma celda de NASA POWER -(-85,0 ·
    10,5), medido en H1.5-, asi que buena parte de sus variables son literalmente
    el mismo numero. Tratarlas como observaciones independientes le hace creer al
    modelo que tiene ocho veces mas evidencia de la que hay.

    Es el mismo razonamiento que `comparar_escalas_spi.py` ya aplicaba al
    contrastar el catalogo -«los 7 registros son 1 fecha x 7 distritos, n
    efectivo ~ 1»-. Lo que faltaba era traerlo a CA-6.
    """
    dias = sorted(
        {
            e.fecha
            for lista in por_distrito.values()
            for e in lista
            if e.nivel(evento) is NivelRiesgo.ALTO
        }
    )
    salida: list[tuple[date, date]] = []
    inicio = anterior = None
    for dia in dias:
        if inicio is None:
            inicio = anterior = dia
        elif (dia - anterior).days == 1:
            anterior = dia
        else:
            salida.append((inicio, anterior))
            inicio = anterior = dia
    if inicio is not None:
        salida.append((inicio, anterior))
    return salida


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
        por_pliegue_real = episodios_por_pliegue(por_distrito, evento)

        # El porcentaje sobre el total mezcla filas observadas con filas que
        # nadie miro, y para incendio esa mezcla son 29 224 filas anteriores al
        # satelite. Se informan los dos, porque el que vale es el segundo.
        observadas = total - sin_dato
        print(f"\n  filas en alto            {filas_alto}")
        if sin_dato:
            print(f"    sobre el total         {100 * filas_alto / total:5.2f} %")
            print(f"    sobre las OBSERVADAS   {100 * filas_alto / observadas:5.2f} %   <- el real")
        # LAS DOS CUENTAS, Y CUAL DECIDE. D-34.
        #
        # Se imprimen las dos a proposito: la de por distrito es la que estuvo
        # en uso hasta el 2026-09-01 y aparece en documentos anteriores, asi que
        # esconderla haria imposible entender por que un numero cambio.
        canton = len(rachas_del_canton(por_distrito, evento))
        print(f"  episodios por distrito   {positivas}   (suma; un evento en 8 distritos cuenta 8)")
        print(f"  EPISODIOS DEL CANTON     {canton}   <- lo que decide CA-6, por D-34")
        if canton:
            print(f"    inflacion del conteo   {positivas / canton:.1f}x")
        if positivas:
            print(f"  filas por episodio       {filas_alto / positivas:.1f}")
        if por_pliegue_real is None:
            print("  episodios por pliegue    NO SE PUDO MEDIR: la particion de H3.2 no se calcula")
            minimo = None
        else:
            minimo = min(por_pliegue_real)
            detalle = ", ".join(str(n) for n in por_pliegue_real)
            print(f"  episodios por pliegue    {detalle}   (entrenamiento de cada uno)")
            print(f"    el MINIMO es           {minimo}   <- lo que evalua CA-6")
            print(
                f"    el promedio seria      {positivas / len(por_pliegue_real):.1f}   (no es el criterio)"
            )

        razones = []
        if canton < MINIMO_POSITIVAS_TOTAL:
            razones.append(
                f"{canton} episodios del canton en total, el minimo es {MINIMO_POSITIVAS_TOTAL}"
            )
        if minimo is None:
            razones.append(
                "no se pudo medir la distribucion por pliegue: sin eso CA-6 no se "
                "puede afirmar, y no afirmarlo es lo conservador"
            )
        elif minimo < MINIMO_POSITIVAS_POR_PARTICION:
            razones.append(
                f"el pliegue mas pobre tiene {minimo} episodios de entrenamiento, "
                f"y el minimo es {MINIMO_POSITIVAS_POR_PARTICION}"
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
