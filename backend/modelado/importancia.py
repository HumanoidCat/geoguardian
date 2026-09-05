"""
Importancia de variables global, por permutacion. Historia H4.1.

Dueno: Luna, traspasada desde Alejandro el 2026-09-03 por **D-37**. La excepcion
sobre `backend/modelado` esta en `docs/07-propiedad-archivos.md`.

Criterios en `docs/evidencias/objetivos/H4.1-criterios-aceptacion.md`.

===========================================================================
LO PRIMERO, PORQUE CAMBIA COMO SE LEE TODO LO DEMAS
===========================================================================

El titulo de H4.1 dice «del mejor modelo». **No hay un mejor modelo.**

  lluvia_intensa   el primero por media es la CLIMATOLOGICA (0.346), que es una
                   linea base y no pondera columnas porque no las consume.
                   XGBoost afinado quedo en 0.327.
  incendio         el bosque afinado tiene la media mas alta (0.5567) pero el
                   que escribe es la regresion logistica (0.5299), por ser la
                   mas simple dentro de la banda de ruido del bosque, y por un
                   margen de 0.0024 sobre la climatologica. Es **I-34**.
  sequia           `NO_MODELABLES`. No aparece aca.

Ninguno de los tres que aprenden le gana a la climatologica fuera del ruido.

**Una tabla de importancias es persuasiva por su forma**: se lee como una
explicacion causal aunque debajo no haya senal que explicar, y el lector no tiene
como distinguir los dos casos porque la tabla se ve igual. Por eso este modulo
**no elige un ganador**: calcula los tres y quien lo use tiene que imprimir el
veredicto de H3.6 y H3.8 al lado. Es CA-8.

===========================================================================
POR QUE PERMUTACION Y NO SOLO `feature_importances_`
===========================================================================

El bosque y XGBoost ya exponen `importancias`, que es la reduccion media de
impureza (MDI). `random_forest.py` documenta su propio problema: **las columnas
correlacionadas se reparten la importancia de forma arbitraria**, y una columna
con muchos valores distintos se ve mas importante de lo que es.

Las caracteristicas de este proyecto son el peor caso para eso: acumulados y
medias moviles de la misma variable a distintas ventanas, correlacionadas entre
si **por construccion**.

La permutacion mide otra cosa: cuanto empeora la metrica en el conjunto de
PRUEBA si esta columna se vuelve ruido. Tampoco resuelve la correlacion -dos
columnas que dicen lo mismo se tapan mutuamente y las dos salen bajas- pero
**falla hacia el lado seguro: subestima en vez de inventar.**

Se reportan las dos. Su desacuerdo es un resultado, no algo que esconder.

===========================================================================
TRES DETALLES QUE DECIDEN SI EL NUMERO VALE
===========================================================================

**1. Se permuta sobre PRUEBA, con el modelo ya ajustado.** Permutar sobre
entrenamiento mide cuanto memorizo, no cuanto sirve. El error no se ve en ningun
numero: sale una tabla mas nitida, que parece un mejor resultado. Es la misma
forma que **D-04** ataca en la particion y **H3.8** en la busqueda de
hiperparametros. Es CA-2.

**2. Se permuta SOLO entre las filas que tienen la columna.** Meter valores en
filas que la tenian ausente cambiaria cuantas filas el estimador puede predecir,
y entonces la metrica se moveria por una razon que **no tiene nada que ver con la
informacion de la columna**. El patron de ausencia se conserva intacto.

**3. Una importancia negativa NO se recorta a cero.** Es CA-5, y es la mentira
comoda de esta tecnica: una tabla sin negativos se ve prolija. `sklearn` no
recorta; muchos tutoriales si. Una columna cuya permutacion **mejora** la metrica
esta diciendo que el modelo la estaba usando en contra, y eso es exactamente lo
que hay que poder ver.

===========================================================================
LOS PLIEGUES SON LOS DE H3.2, Y ESO SE COMPRUEBA
===========================================================================

Este modulo arma los pliegues con la misma receta que `comparar.comparar`. Dos
implementaciones de la misma medida terminan midiendo cosas distintas, asi que
el verificador **comprueba la equivalencia en vez de confiar en ella**: el F1 de
referencia por pliegue que sale de aca tiene que ser identico, valor por valor,
al `Resultado.por_pliegue` que devuelve `comparar()` para el mismo estimador.

Si alguien cambia la particion en un lado y no en el otro, sale en rojo.

Uso:
    python -m backend.modelado.importancia
    python -m backend.modelado.importancia --repeticiones 10
"""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado.comparar import (  # noqa: E402
    NO_MODELABLES,
    Observacion,
)
from backend.modelado.evaluar_linea_base import COLUMNA  # noqa: E402
from backend.modelado.linea_base import DISTRITOS_CON_INCENDIO, f1_macro  # noqa: E402
from backend.modelado.particion import particionar  # noqa: E402
from contratos.enums import TipoEvento  # noqa: E402

#: Cuantas veces se permuta cada columna en cada pliegue. Cinco es suficiente
#: para que la dispersion signifique algo y barato de correr; se puede subir por
#: linea de comandos y el resultado no cambia de forma, solo de ruido.
REPETICIONES = 5

#: Semilla base. **Se declara y se imprime**, porque un resultado que no se puede
#: repetir no es un resultado. Es CA-3 y CA-12.
SEMILLA = "H4.1"


@dataclass(frozen=True)
class ImportanciaColumna:
    """Cuanto cae la metrica al volver ruido esta columna, pliegue por pliegue."""

    nombre: str

    #: Un valor por pliegue: la media de las repeticiones dentro de ese pliegue.
    #: **Se guarda la lista y no solo el promedio** porque una media que oculta un
    #: cambio de signo entre pliegues no es una importancia, es un promedio de
    #: dos cosas distintas. Es CA-4, la misma razon por la que `Resultado` de
    #: H3.6 guarda `por_pliegue`.
    por_pliegue: list[float]

    @property
    def media(self) -> float:
        return sum(self.por_pliegue) / len(self.por_pliegue) if self.por_pliegue else 0.0

    @property
    def rango(self) -> float:
        """Cuanto se mueve entre pliegues. Misma definicion que `Resultado.rango`."""
        return max(self.por_pliegue) - min(self.por_pliegue) if self.por_pliegue else 0.0

    @property
    def distinguible(self) -> bool:
        """La caida supera a su propio movimiento entre pliegues.

        Es la regla de CA-5 de H3.1 y del `veredicto` de H3.6, aplicada a una
        columna en vez de a un estimador: **si la senal es menor que el ruido
        propio, no se afirma.** Sin esto, ordenar columnas por media inventa un
        ranking donde no hay diferencias.
        """
        return abs(self.media) > self.rango


@dataclass(frozen=True)
class ImportanciaEstimador:
    """Todo lo que se puede decir de un estimador sobre un evento."""

    nombre: str

    #: F1-macro sin permutar nada, por pliegue. Tiene que coincidir con el
    #: `por_pliegue` de `comparar()`; el verificador lo comprueba.
    referencia_por_pliegue: list[float]

    permutacion: list[ImportanciaColumna]

    #: MDI, solo si el estimador lo expone. La regresion logistica no.
    mdi: dict[str, float] | None = None

    #: Coeficientes, solo la regresion logistica. **Rotulados por clase**, y eso
    #: no es decorativo: en un evento binario como el incendio la clase positiva
    #: es `bajo` por orden alfabetico (SC-05), asi que un coeficiente positivo
    #: empuja hacia MENOS riesgo. Quien lea el signo sin mirar la clase entiende
    #: el modelo exactamente al reves. Lo documenta `regresion_logistica.py`.
    coeficientes: dict[str, dict[str, float]] | None = None

    #: Pliegues que el estimador no pudo ajustar, con su motivo.
    saltados: list[str] = field(default_factory=list)

    @property
    def ninguna_distinguible(self) -> bool:
        """Ninguna columna supera su propio ruido: el modelo no distingue variables.

        **Es un resultado valido y hay que poder emitirlo** (CA-10). Es ademas lo
        coherente con que ningun estimador supere a la climatologica fuera del
        ruido: un modelo que no gana no tiene por que tener una explicacion
        nitida, y si la tuviera habria que sospechar de ella.
        """
        return bool(self.permutacion) and not any(c.distinguible for c in self.permutacion)


def _permutar(
    observaciones: list[Observacion], columna: str, generador: random.Random
) -> list[Observacion]:
    """Devuelve las observaciones con `columna` barajada entre ellas.

    **Solo entre las filas que la tienen.** Ver el detalle 2 del encabezado: si
    se rellenaran las ausentes, cambiaria cuantas filas el estimador puede
    predecir y la metrica se moveria por un motivo ajeno a la columna.
    """
    indices = [i for i, o in enumerate(observaciones) if columna in o.caracteristicas]
    if len(indices) < 2:
        return list(observaciones)

    valores = [observaciones[i].caracteristicas[columna] for i in indices]
    generador.shuffle(valores)

    salida = list(observaciones)
    for i, valor in zip(indices, valores, strict=True):
        rasgos = dict(observaciones[i].caracteristicas)
        rasgos[columna] = valor
        salida[i] = Observacion(observaciones[i].codigo_distrito, observaciones[i].fecha, rasgos)
    return salida


def _pliegues_de(
    evento: TipoEvento,
    filas: list,
    caracteristicas: dict[tuple[str, date], dict[str, float]],
    pliegues: list | None = None,
):
    """Los mismos cuatro pedazos que arma `comparar.comparar`, pliegue por pliegue.

    Se replica la receta en vez de importarla porque `comparar` no la expone por
    separado, y **esta historia no toca `comparar.py`** (lo dicen los criterios).
    El riesgo de que las dos se separen es real, y por eso el verificador compara
    las metricas de referencia contra las de `comparar()` en vez de dar la
    equivalencia por supuesta.
    """
    columna = COLUMNA[evento]
    if evento is TipoEvento.INCENDIO:
        filas = [f for f in filas if f[0] in DISTRITOS_CON_INCENDIO]

    def observacion(codigo: str, fecha: date) -> Observacion:
        return Observacion(codigo, fecha, caracteristicas.get((codigo, fecha), {}))

    for pliegue in pliegues if pliegues is not None else particionar(evento):
        ent = [
            (observacion(c, f), n[columna])
            for c, f, n in filas
            if pliegue.entrenamiento[0] <= f <= pliegue.entrenamiento[1] and n[columna] is not None
        ]
        pru = [
            (observacion(c, f), n[columna])
            for c, f, n in filas
            if pliegue.prueba[0] <= f <= pliegue.prueba[1] and n[columna] is not None
        ]
        if not ent or not pru:
            continue
        yield (
            [o for o, _ in ent],
            [e for _, e in ent],
            [o for o, _ in pru],
            [e for _, e in pru],
        )


def columnas_de(observaciones: list[Observacion]) -> list[str]:
    """Los nombres de columna presentes, ordenados. CA-6: se leen por nombre."""
    return sorted({c for o in observaciones for c in o.caracteristicas})


def importancia(
    evento: TipoEvento,
    filas: list,
    estimadores: dict[str, callable],
    caracteristicas: dict[tuple[str, date], dict[str, float]],
    pliegues: list | None = None,
    repeticiones: int = REPETICIONES,
    semilla: str = SEMILLA,
) -> list[ImportanciaEstimador]:
    """Importancia por permutacion de cada estimador que aprende, sobre este evento.

    Devuelve una entrada por estimador, con las columnas ordenadas por media
    descendente. **No decide cual estimador es el mejor** y no filtra ninguno por
    su metrica: eso lo deciden H3.6 y H3.8, y esta historia solo describe.

    Un evento de `NO_MODELABLES` devuelve la lista vacia (CA-9).
    """
    if evento in NO_MODELABLES:
        return []

    acumulado: dict[str, dict[str, list[float]]] = {n: {} for n in estimadores}
    referencia: dict[str, list[float]] = {n: [] for n in estimadores}
    saltados: dict[str, list[str]] = {n: [] for n in estimadores}
    ajustados: dict[str, object] = {}

    for indice, (obs_ent, eti_ent, obs_pru, verdad) in enumerate(
        _pliegues_de(evento, filas, caracteristicas, pliegues)
    ):
        columnas = columnas_de(obs_pru)

        for nombre, fabrica in estimadores.items():
            # Un pliegue que no se puede ajustar se salta, no tumba la tabla.
            # Mismo criterio que `comparar`, y por el mismo motivo: negarse a
            # ajustar con una sola clase o sin caracteristicas completas es
            # informacion, no un error del programa.
            try:
                modelo = fabrica().ajustar(obs_ent, eti_ent)
                base, _, _ = f1_macro(verdad, modelo.predecir(obs_pru))
            except ValueError as motivo:
                saltados[nombre].append(str(motivo))
                continue

            referencia[nombre].append(base)
            # El ultimo pliegue ajustado es el que se usa para leer MDI y
            # coeficientes: es el que vio mas historia, porque la ventana es
            # expansiva. Se dice en la evidencia; no es un promedio.
            ajustados[nombre] = modelo

            for columna in columnas:
                caidas = []
                for repeticion in range(repeticiones):
                    # La semilla se deriva de una CADENA y no de una tupla: el
                    # `hash()` de Python se aleatoriza por proceso, asi que una
                    # tupla como semilla daria resultados distintos en cada
                    # corrida y CA-12 fallaria sin motivo visible.
                    generador = random.Random(f"{semilla}|{indice}|{columna}|{repeticion}")
                    permutadas = _permutar(obs_pru, columna, generador)
                    metrica, _, _ = f1_macro(verdad, modelo.predecir(permutadas))
                    # SIN max(0, ...). Es CA-5.
                    caidas.append(base - metrica)
                acumulado[nombre].setdefault(columna, []).append(sum(caidas) / len(caidas))

    salida = []
    for nombre in estimadores:
        columnas = [
            ImportanciaColumna(columna, valores)
            for columna, valores in acumulado[nombre].items()
        ]
        columnas.sort(key=lambda c: -c.media)
        modelo = ajustados.get(nombre)
        salida.append(
            ImportanciaEstimador(
                nombre=nombre,
                referencia_por_pliegue=referencia[nombre],
                permutacion=columnas,
                mdi=_leer(modelo, "importancias"),
                coeficientes=_leer(modelo, "coeficientes"),
                saltados=saltados[nombre],
            )
        )
    return salida


def _leer(modelo, atributo: str):
    """Lee una propiedad opcional del estimador, o None si no la tiene.

    No todos los estimadores exponen las mismas lecturas y **eso no es una
    carencia**: la regresion logistica no tiene MDI porque no hay impureza que
    reducir, y el bosque no tiene coeficientes porque no es lineal. Devolver None
    y decirlo es mas honesto que fabricar un cero.
    """
    if modelo is None or not hasattr(modelo, atributo):
        return None
    try:
        return getattr(modelo, atributo)
    except ValueError:
        return None


# --------------------------------------------------------------------------- #
# La salida                                                                     #
# --------------------------------------------------------------------------- #


def main() -> int:
    p = argparse.ArgumentParser(description="Importancia de variables global · H4.1.")
    p.add_argument("--repeticiones", type=int, default=REPETICIONES)
    p.add_argument("--semilla", default=SEMILLA)
    p.add_argument("--columnas", type=int, default=10, help="cuantas mostrar por estimador")
    args = p.parse_args()

    from backend.modelado.afinar import CARACTERISTICAS, ETIQUETAS, cargar, fabricas
    from backend.modelado.comparar import CON_CARACTERISTICAS, comparar, elegir_escritor, veredicto

    if not ETIQUETAS.exists() or not CARACTERISTICAS.exists():
        print("\nHacen falta las dos: etiquetas.csv y caracteristicas.csv. Con la base levantada:")
        print("\n    python -m backend.modelado.generar_etiquetas")
        print("    python -m backend.modelado.generar_caracteristicas\n")
        return 1

    filas, caracteristicas = cargar()

    print("\nImportancia de variables global · H4.1")
    print("  metrica         F1-macro, D-10, sobre los pliegues de H3.2")
    print(f"  metodo          permutacion sobre PRUEBA, {args.repeticiones} repeticiones")
    print(f"  semilla         {args.semilla}")
    print("  modelos         los AFINADOS de H3.8, que son los que corre la tuberia\n")
    print("  NINGUN ESTIMADOR SUPERA A LA CLIMATOLOGICA FUERA DEL RUIDO.")
    print("  Esta tabla describe como decide cada modelo, NO por que acierta.\n")

    for evento in TipoEvento:
        if evento in NO_MODELABLES:
            print(f"{evento.value.upper()}: no modelable. {NO_MODELABLES[evento]}\n")
            continue

        todas = fabricas(evento, True)
        resultados = comparar(evento, filas, todas, caracteristicas)
        escritor, motivo = elegir_escritor(resultados)

        print(evento.value.upper())
        print(f"  veredicto de H3.6/H3.8   {veredicto(resultados)}")
        print(f"  escribe                  {escritor} ({motivo})\n")

        aprenden = {n: f for n, f in todas.items() if n in CON_CARACTERISTICAS}
        for est in importancia(
            evento, filas, aprenden, caracteristicas, None, args.repeticiones, args.semilla
        ):
            media = (
                sum(est.referencia_por_pliegue) / len(est.referencia_por_pliegue)
                if est.referencia_por_pliegue
                else 0.0
            )
            print(f"  {est.nombre}  (F1-macro {media:.3f}, {len(est.referencia_por_pliegue)} pliegues)")
            if not est.permutacion:
                print(f"    sin columnas evaluables. {'; '.join(est.saltados) or 'sin motivo'}\n")
                continue
            if est.ninguna_distinguible:
                print("    NINGUNA COLUMNA SUPERA SU PROPIO RUIDO ENTRE PLIEGUES.")
                print("    El modelo no distingue variables. Es un resultado (CA-10).")
            print(f"    {'columna':28}{'caida media':>12}{'rango':>9}  distinguible")
            for columna in est.permutacion[: args.columnas]:
                marca = "si" if columna.distinguible else "no"
                print(
                    f"    {columna.nombre:28}{columna.media:>12.4f}"
                    f"{columna.rango:>9.4f}  {marca}"
                )
            print()

    print(
        "Como leerla. La caida es cuanto empeora el F1-macro al volver ruido esa\n"
        "columna. Un valor NEGATIVO significa que permutarla MEJORO la metrica, y\n"
        "no se recorta a cero (CA-5). 'distinguible' es que la caida supera a su\n"
        "propio movimiento entre pliegues; donde dice no, no hay que ordenar.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
