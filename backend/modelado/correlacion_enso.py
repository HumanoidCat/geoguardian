"""Por que el ENSO no movio el F1. Historia H3.10, criterios CA-5 y CA-6.

===========================================================================
LA PREGUNTA QUE ESTE GUION CONTESTA, Y LA QUE NO
===========================================================================

El arnes de H3.6 ya dijo **que** paso: con las tres columnas del ONI ningun
estimador mejora, cuatro de seis empeoran y la desviacion entre pliegues sube.
Eso es el CA-5 y no necesita mas.

Lo que el arnes **no** puede decir es **por que**, y las dos explicaciones
posibles llevan a evidencias opuestas:

  (a) la senal del ENSO ya esta adentro de lo que el modelo ya ve. Agregar el
      indice seria agregar algo que ya estaba, y para un canton de la vertiente
      del Pacifico eso es un hallazgo publicable.

  (b) las tres columnas casi no varian dentro de un pliegue. El ONI es mensual,
      se repite en los 31 dias del mes y en los ocho distritos, y los rezagos
      son de 0, 3 y 6 meses. Si dentro de una ventana de prueba el indice toma
      cuatro valores distintos, no puede discriminar nada ahi adentro: es ruido
      con nombre de variable.

**Escribir (a) sin haber descartado (b) seria inventar un hallazgo.** Las dos
producen el mismo F1 plano y la unica diferencia es si el proyecto midio bien.
Este guion mide las dos y **no elige**: imprime los numeros y quien escribe la
evidencia decide con ellos a la vista.

===========================================================================
UN DATO QUE CONVIENE TENER ENFRENTE AL LEER LA SALIDA
===========================================================================

**La memoria mas larga del modelo son 30 dias** (`pp_acum30`, `pp_media30`), y
el ONI es una media de **tres meses**. No hay en la matriz ninguna variable de
escala estacional: `cal_seno` y `cal_coseno` dicen en que parte del ano estamos,
no si **este** ano viene seco. Asi que la explicacion (a) no se puede dar por
supuesta -no hay un candidato obvio donde la senal ya estuviera metida- y por eso
hay que medirla en vez de razonarla.

===========================================================================
POR QUE LA CORRELACION VA POR DISTRITO Y NO SOBRE LA MATRIZ ENTERA
===========================================================================

El ONI de una fecha es **el mismo para los ocho distritos**. La lluvia no. Si se
calcula Pearson sobre las 103 968 filas juntas, la varianza *entre* distritos
-que el ONI no puede explicar porque no la ve- entra al denominador y **hunde**
la correlacion hacia cero. Saldria un numero chico que parece decir "el ONI no
tiene nada que ver con la lluvia" cuando lo unico que dice es que se promedio mal.

Asi que se calcula **dentro de cada distrito** y se reporta el rango entre los
ocho, ademas del valor agrupado para que se vea la diferencia. Es el mismo
cuidado que D-34 tuvo al contar episodios por canton y no por distrito.

Uso:
    python -m backend.modelado.correlacion_enso
    python -m backend.modelado.correlacion_enso --matriz datos/procesados/otra.csv
"""

from __future__ import annotations

import argparse
import statistics
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado.generar_caracteristicas import COLUMNAS_CONTEXTO, leer  # noqa: E402
from backend.modelado.oni import COLUMNAS_ONI  # noqa: E402
from backend.modelado.particion import particionar  # noqa: E402
from contratos.enums import TipoEvento  # noqa: E402

#: La matriz de H3.10, la que lleva las tres columnas del indice.
MATRIZ = RAIZ / "datos" / "procesados" / "caracteristicas-h310.csv"

#: Cuantas parejas hacen falta para que un Pearson signifique algo. Por debajo
#: de esto no se imprime un numero: se imprime que no alcanzo.
MINIMO_PAREJAS = 30

#: Arriba de esto se lee como "el ONI ya esta adentro de esa columna". No es un
#: umbral de la literatura, es el corte que este proyecto declara **antes** de
#: mirar los resultados, para no elegirlo despues de verlos. Es la misma regla
#: del CA-3 de esta historia aplicada al analisis y no solo a las columnas.
FUERTE = 0.30


def correlacion(x: list[float], y: list[float]) -> float | None:
    """Pearson, o None cuando la pregunta no tiene respuesta.

    Se apoya en `statistics.correlation` de la biblioteca estandar **a proposito**:
    una implementacion propia habria que probarla contra algo, y lo unico que
    habria a mano para probarla es ella misma.

    Devuelve None en dos casos, y los dos son informacion y no errores:

    - **menos de `MINIMO_PAREJAS`**: un Pearson sobre seis puntos se mueve
      entero con un punto.
    - **alguna serie constante**: el denominador es cero. Devolver 0.0 ahi
      afirmaria "no hay relacion" cuando lo cierto es "no se puede saber", y esa
      confusion es la que este guion existe para evitar: el ONI dentro de un
      pliegue corto puede ser casi constante.
    """
    if len(x) < MINIMO_PAREJAS:
        return None
    try:
        return statistics.correlation(x, y)
    except statistics.StatisticsError:
        return None


def por_distrito(
    matriz: dict[tuple[str, date], dict[str, float]],
) -> dict[str, dict[str, list[float | None]]]:
    """Reagrupa la matriz por distrito y columna, en **una sola pasada**.

    Recorrer el diccionario entero una vez por pareja de columnas serian cientos
    de pasadas sobre cien mil filas. Aca se paga una y despues todo es aritmetica.

    Las filas quedan **alineadas por posicion** y los huecos entran como None en
    vez de saltarse: si cada columna descartara sus propios huecos, dos listas de
    la misma longitud podrian corresponder a fechas distintas y el Pearson seria
    entre cosas que no pasaron el mismo dia. `alineadas` los quita despues, de a
    pares.
    """
    codigos = sorted({codigo for codigo, _ in matriz})
    columnas = sorted({c for fila in matriz.values() for c in fila})
    salida: dict[str, dict[str, list[float | None]]] = {
        codigo: {c: [] for c in columnas} for codigo in codigos
    }
    for (codigo, _), fila in sorted(matriz.items()):
        for c in columnas:
            salida[codigo][c].append(fila.get(c))
    return salida


def alineadas(
    columnas: dict[str, list[float | None]], a: str, b: str
) -> tuple[list[float], list[float]]:
    """Las posiciones donde **las dos** columnas tienen valor.

    `leer` omite las celdas vacias en vez de ponerles None, asi que la ausencia
    llega aca como un None puesto por `por_distrito`. Se descarta la posicion
    entera: imputarla daria una correlacion entre un dato y un invento.
    """
    xs: list[float] = []
    ys: list[float] = []
    for va, vb in zip(columnas[a], columnas[b], strict=True):
        if va is not None and vb is not None:
            xs.append(va)
            ys.append(vb)
    return xs, ys


def columnas_comparables(matriz: dict[tuple[str, date], dict[str, float]]) -> list[str]:
    """Contra que columnas tiene sentido preguntar si el ONI ya esta adentro.

    Se excluyen dos familias, y ninguna por comodidad:

    **Las del propio ONI.** Correlacionar `enso_oni` con `enso_oni_r3` daria un
    numero alto que no dice nada: son la misma serie corrida tres meses.

    **Las cinco de contexto de H3.9.** `geo_lon`, `geo_lat` y `geo_km_tam` son
    constantes dentro de un distrito, asi que la correlacion ni siquiera existe;
    `cal_seno` y `cal_coseno` describen el calendario, y que el ONI se parezca al
    calendario es un artefacto del ciclo anual, no una senal climatica.
    """
    todas = {c for fila in matriz.values() for c in fila}
    return sorted(todas - set(COLUMNAS_ONI) - set(COLUMNAS_CONTEXTO))


def informe_correlacion(matriz: dict[tuple[str, date], dict[str, float]]) -> int:
    """(a): si el ONI ya esta adentro, tiene que verse contra lo que el modelo ve."""
    agrupada = {"": {c: [] for c in {k for fila in matriz.values() for k in fila}}}
    for fila in sorted(matriz.items()):
        for c in agrupada[""]:
            agrupada[""][c].append(fila[1].get(c))
    tablas = por_distrito(matriz)
    objetivo = columnas_comparables(matriz)

    print("\n(a) El ONI contra lo que el modelo ya ve")
    print(f"    distritos {len(tablas)} · columnas comparables {len(objetivo)}")
    print(f"    corte declarado de antemano: |r| >= {FUERTE:.2f} se lee como 'ya esta adentro'")
    print("    el agrupado esta hundido a proposito; el que vale es el rango por distrito\n")

    fuertes: list[str] = []
    print(f"    {'columna ONI':<14}{'contra':<26}{'agrupado':>10}{'por distrito (min .. max)':>28}")
    for enso in COLUMNAS_ONI:
        for columna in objetivo:
            juntos = correlacion(*alineadas(agrupada[""], enso, columna))
            valores = [
                r
                for tabla in tablas.values()
                if (r := correlacion(*alineadas(tabla, enso, columna))) is not None
            ]
            if not valores:
                print(f"    {enso:<14}{columna:<26}{'sin parejas':>10}")
                continue
            peor, mejor = min(valores), max(valores)
            if max(abs(peor), abs(mejor)) >= FUERTE:
                fuertes.append(f"{enso} ~ {columna}")
            agr = f"{juntos:.3f}" if juntos is not None else "n/d"
            print(f"    {enso:<14}{columna:<26}{agr:>10}{f'{peor:+.3f} .. {mejor:+.3f}':>28}")

    print(f"\n    parejas con |r| >= {FUERTE:.2f} en algun distrito: {len(fuertes)}")
    for pareja in fuertes:
        print(f"      {pareja}")
    if not fuertes:
        print("      ninguna. La explicacion (a) NO tiene respaldo en estos numeros.")
    return 0


def informe_variacion(matriz: dict[tuple[str, date], dict[str, float]]) -> int:
    """(b): cuantos valores distintos toma el indice DENTRO de cada pliegue.

    Se mira el entrenamiento y la prueba por separado, y por una razon distinta
    cada uno. En el entrenamiento, pocos valores distintos quieren decir que el
    estimador tuvo poco de donde aprender. En la prueba, pocos valores distintos
    quieren decir que la columna **no puede** separar nada ahi adentro, aprenda
    lo que aprenda: si el ONI vale lo mismo para todas las filas de la ventana,
    no distingue una de otra.

    Se cuenta sobre `COLUMNAS_ONI[0]`, el indice sin rezago. Los rezagos son la
    misma serie corrida, asi que sobre una ventana larga cuentan casi lo mismo y
    repetirlo tres veces alargaria la tabla sin agregar nada.
    """
    print("\n(b) Cuanto varia el indice dentro de cada pliegue")
    print("    el ONI es mensual y se repite en los 8 distritos; aca se ve cuanto sobra\n")
    indice = COLUMNAS_ONI[0]

    for evento in TipoEvento:
        print(f"    {evento.value.upper()}")
        print(
            f"    {'#':<4}{'entrenamiento':<26}{'valores':>8}  "
            f"{'prueba':<26}{'valores':>8}{'meses':>7}"
        )
        for p in particionar(evento):
            vistos_ent = {
                fila[indice]
                for (_, f), fila in matriz.items()
                if p.entrenamiento[0] <= f <= p.entrenamiento[1] and indice in fila
            }
            vistos_pru = {
                fila[indice]
                for (_, f), fila in matriz.items()
                if p.prueba[0] <= f <= p.prueba[1] and indice in fila
            }
            meses = (
                (p.prueba[1].year - p.prueba[0].year) * 12
                + (p.prueba[1].month - p.prueba[0].month)
                + 1
            )
            ent = f"{p.entrenamiento[0]} a {p.entrenamiento[1]}"
            pru = f"{p.prueba[0]} a {p.prueba[1]}"
            print(
                f"    {p.indice:<4}{ent:<26}{len(vistos_ent):>8}  "
                f"{pru:<26}{len(vistos_pru):>8}{meses:>7}"
            )
        print()
    print("    Un pliegue de prueba de N meses no puede traer mas de N valores distintos.")
    print("    Si 'valores' se le parece, la columna esta casi agotada ahi adentro.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--matriz", type=Path, default=MATRIZ)
    args = p.parse_args()

    if not args.matriz.exists():
        print(f"\nNo existe {args.matriz}.\n")
        print("Se genera con:\n")
        print("    python -m backend.modelado.generar_caracteristicas --salida <ruta>\n")
        return 1

    matriz = leer(args.matriz)
    presentes = [c for c in COLUMNAS_ONI if any(c in fila for fila in matriz.values())]
    print("\nPor que el ENSO no movio el F1 · H3.10")
    print(f"  matriz     {args.matriz}")
    print(f"  filas      {len(matriz)}")
    print(f"  columnas   {len({c for fila in matriz.values() for c in fila})}")
    print(f"  del ONI    {len(presentes)} de {len(COLUMNAS_ONI)}: {', '.join(presentes)}")

    if len(presentes) != len(COLUMNAS_ONI):
        print("\n  Esta matriz no trae las tres columnas del ONI. Es la de H3.9, no la de H3.10.")
        return 1

    codigo = informe_correlacion(matriz)
    codigo |= informe_variacion(matriz)
    print("  Este guion NO concluye. Los dos informes de arriba son la entrada del CA-5.\n")
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
