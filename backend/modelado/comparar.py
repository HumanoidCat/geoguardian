"""Tabla comparativa de estimadores contra las lineas base. Historia H3.6.

===========================================================================
QUE PRODUCE, Y QUE NO
===========================================================================

**Produce la tabla**, no los modelos. H3.3, H3.4 y H3.5 -Regresion Logistica,
Random Forest y XGBoost- son de Cesar y todavia no existen. Esta historia decide
**como se comparan** y deja el hueco declarado, no escondido.

Hoy la tabla se puebla con las dos lineas base de **H3.1**, que si estan
implementadas. Cuando entren los tres algoritmos, se agregan al registro y la
tabla se llena sola: no hay que tocar nada mas.

===========================================================================
POR QUE EL CONTRATO VA ANTES QUE LOS MODELOS
===========================================================================

Es el mismo razonamiento de **D-06** y de los contratos congelados del 3 de
agosto: si cada historia define su propia forma de entrenar y de predecir, la
tabla de H3.6 termina comparando **cosas distintas** y hay que reescribir tres
historias para arreglarlo.

En particular, tres decisiones tienen que ser identicas para los cinco
estimadores, y si no lo son la comparacion no significa nada:

    la particion        de H3.2, `particionar(evento)`. Una sola definicion
    la metrica          F1-macro de D-10, la implementacion de H3.1
    que hacer con None  no se evalua y se cuenta aparte

Las tres viven aca y ningun estimador las decide.

===========================================================================
EL CONTRATO
===========================================================================

Un estimador es cualquier objeto con `nombre`, `ajustar()` y `predecir()`:

    ajustar(observaciones, etiquetas) -> self
    predecir(observaciones)           -> lista de NivelRiesgo | None

`Observacion` lleva **distrito, fecha y caracteristicas**. Las lineas base
ignoran las caracteristicas -miran solo el calendario, que es CA-1 de H3.1- y los
algoritmos las van a necesitar. La firma es la misma para que
`DesdeLineaBase` pueda envolver a las primeras sin que la tabla note la
diferencia.

**`caracteristicas` viene vacio por ahora.** No existe todavia una matriz de
caracteristicas: H2.x produjo estadisticos, no entradas de modelo. Construirla es
parte de H3.3, y **CA-6 de H3.2** ya dice la regla que va a tener que respetar:
toda normalizacion o percentil usado como ENTRADA se ajusta dentro del pliegue.

===========================================================================
LO QUE ESTA TABLA NO AFIRMA
===========================================================================

**No hay prueba de significancia, y no se va a poner una.** Son cinco pliegues, y
cinco pliegues de una serie temporal no son cinco muestras independientes: los
entrenamientos se solapan por construccion -la ventana es expansiva- asi que las
metricas estan correlacionadas y cualquier prueba que suponga independencia daria
un valor p inflado.

Lo que se reporta es la media, la desviacion **y los cinco valores**. Si un
estimador le gana a otro por menos de lo que se mueve entre pliegues, la tabla lo
marca y **no se declara ganador**. Es preferible decir «no se distinguen» a
inventar una certeza que cinco pliegues no dan.

Uso:
    python -m backend.modelado.comparar
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Protocol, runtime_checkable

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado.evaluar_linea_base import COLUMNA, leer  # noqa: E402
from backend.modelado.linea_base import (  # noqa: E402
    DISTRITOS_CON_INCENDIO,
    LineaBaseClimatologica,
    LineaBaseTrivial,
    f1_macro,
)
from backend.modelado.particion import particionar, resumen_f1  # noqa: E402
from contratos.enums import NivelRiesgo, TipoEvento  # noqa: E402

# --------------------------------------------------------------------------- #
# El contrato                                                                   #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Observacion:
    """Una fila que se puede predecir: donde, cuando y con que se cuenta.

    `caracteristicas` esta vacio hasta que H3.3 construya la matriz. Se declara
    ahora igual, porque el dia que aparezca **no puede cambiar la firma**: si
    cambia, las lineas base ya medidas dejan de ser comparables con lo que venga
    despues y la tabla de esta historia pierde su unica razon de existir.
    """

    codigo_distrito: str
    fecha: date
    caracteristicas: dict[str, float] = field(default_factory=dict)


@runtime_checkable
class Estimador(Protocol):
    """Lo que H3.3, H3.4 y H3.5 tienen que cumplir para entrar en la tabla."""

    nombre: str

    def ajustar(
        self, observaciones: list[Observacion], etiquetas: list[NivelRiesgo]
    ) -> Estimador: ...

    def predecir(self, observaciones: list[Observacion]) -> list[NivelRiesgo | None]: ...


class DesdeLineaBase:
    """Envuelve una linea base de H3.1 en el contrato de H3.6.

    Existe para que la tabla no tenga dos caminos. Un `if` que distinga «linea
    base» de «modelo» seria el lugar exacto donde con el tiempo se cuela una
    diferencia de trato -otro corte, otra forma de contar los None- y nadie la
    veria hasta que los resultados no cuadraran.

    Las caracteristicas se descartan a proposito: es **CA-1 de H3.1**. Una linea
    base que mira una variable meteorologica deja de ser linea base.
    """

    def __init__(self, nombre: str, fabrica) -> None:
        self.nombre = nombre
        self._fabrica = fabrica
        self._interno = None

    def ajustar(
        self, observaciones: list[Observacion], etiquetas: list[NivelRiesgo]
    ) -> DesdeLineaBase:
        entrenamiento = [
            (o.codigo_distrito, o.fecha, e) for o, e in zip(observaciones, etiquetas, strict=True)
        ]
        self._interno = self._fabrica().ajustar(entrenamiento)
        return self

    def predecir(self, observaciones: list[Observacion]) -> list[NivelRiesgo | None]:
        if self._interno is None:
            raise RuntimeError(f"{self.nombre} no fue ajustado")
        return [self._interno.predecir(o.codigo_distrito, o.fecha) for o in observaciones]


# --------------------------------------------------------------------------- #
# El registro                                                                   #
# --------------------------------------------------------------------------- #
#
# Los tres algoritmos se declaran **pendientes con su historia**, no se omiten.
# Una tabla que muestra dos filas sin decir que faltan tres se lee como si el
# contraste de D-10 ya estuviera hecho, y no lo esta.
#
# Es la misma regla que el documento IEEE aplica a sus secciones vacias: un
# apartado en blanco sin explicacion es indistinguible de un olvido.

DISPONIBLES: dict[str, callable] = {
    "trivial": lambda: DesdeLineaBase("trivial", LineaBaseTrivial),
    "climatologica": lambda: DesdeLineaBase("climatologica", LineaBaseClimatologica),
}

PENDIENTES: dict[str, str] = {
    "regresion logistica": "H3.3, Cesar",
    "random forest": "H3.4, Cesar",
    "xgboost": "H3.5, Cesar",
}

#: La referencia contra la que se mide todo. **D-10** compara contra la linea
#: base, y la trivial es el piso absoluto: con incendio al 1,23 %, «siempre BAJO»
#: acierta el 98,8 % de las veces.
REFERENCIA = "trivial"


# --------------------------------------------------------------------------- #
# La medicion                                                                   #
# --------------------------------------------------------------------------- #


@dataclass
class Resultado:
    nombre: str
    por_pliegue: list[float]
    media: float
    desviacion: float
    sin_evaluar: int

    @property
    def rango(self) -> float:
        """Cuanto se mueve entre pliegues. Es la vara para decir si dos empatan."""
        return max(self.por_pliegue) - min(self.por_pliegue) if self.por_pliegue else 0.0


def comparar(
    evento: TipoEvento, filas: list, estimadores: dict[str, callable] | None = None
) -> list[Resultado]:
    """Corre todos los estimadores sobre **los mismos** pliegues del mismo evento."""
    estimadores = estimadores if estimadores is not None else DISPONIBLES
    columna = COLUMNA[evento]

    # CA-6 de H3.0: el incendio solo donde D-25 dice que hay senal.
    if evento is TipoEvento.INCENDIO:
        filas = [f for f in filas if f[0] in DISTRITOS_CON_INCENDIO]

    acumulado: dict[str, list[float]] = {n: [] for n in estimadores}
    huecos: dict[str, int] = {n: 0 for n in estimadores}

    for pliegue in particionar(evento):
        ent = [
            (Observacion(c, f), n[columna])
            for c, f, n in filas
            if pliegue.entrenamiento[0] <= f <= pliegue.entrenamiento[1] and n[columna] is not None
        ]
        pru = [
            (Observacion(c, f), n[columna])
            for c, f, n in filas
            if pliegue.prueba[0] <= f <= pliegue.prueba[1] and n[columna] is not None
        ]
        if not ent or not pru:
            continue

        obs_ent = [o for o, _ in ent]
        eti_ent = [e for _, e in ent]
        obs_pru = [o for o, _ in pru]
        verdad = [e for _, e in pru]

        for nombre, fabrica in estimadores.items():
            modelo = fabrica().ajustar(obs_ent, eti_ent)
            prediccion = modelo.predecir(obs_pru)
            metrica, _, evaluadas = f1_macro(verdad, prediccion)
            acumulado[nombre].append(metrica)
            huecos[nombre] += len(verdad) - evaluadas

    resultados = []
    for nombre, valores in acumulado.items():
        media, desviacion, _ = resumen_f1(valores) if valores else (0.0, 0.0, [])
        resultados.append(Resultado(nombre, valores, media, desviacion, huecos[nombre]))

    return sorted(resultados, key=lambda r: -r.media)


def veredicto(resultados: list[Resultado]) -> str:
    """Quien gana, o por que no se puede decir.

    **La regla se fija antes de mirar el dato**, igual que el MARGEN de H3.1: si
    la ventaja del primero sobre el segundo es menor que lo que el propio primero
    se mueve entre pliegues, no se declara ganador. Con cinco pliegues
    correlacionados esa es toda la resolucion que hay.
    """
    if len(resultados) < 2:
        return "no hay con que comparar"

    primero, segundo = resultados[0], resultados[1]
    ventaja = primero.media - segundo.media
    if ventaja <= primero.rango:
        return (
            f"empate tecnico: {primero.nombre} le saca {ventaja:+.3f} a "
            f"{segundo.nombre}, y se mueve {primero.rango:.3f} entre pliegues"
        )
    return f"{primero.nombre}, por {ventaja:+.3f} sobre {segundo.nombre}"


# --------------------------------------------------------------------------- #
# La salida                                                                     #
# --------------------------------------------------------------------------- #


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--etiquetas", type=Path, default=RAIZ / "datos" / "procesados" / "etiquetas.csv"
    )
    args = p.parse_args()

    if not args.etiquetas.exists():
        print(f"\nNo existe {args.etiquetas}.\n")
        print("Se genera con la base levantada:\n")
        print("    python -m backend.modelado.generar_etiquetas\n")
        return 1

    filas = leer(args.etiquetas)

    print("\nTabla comparativa de estimadores · H3.6")
    print(f"  filas leidas    {len(filas)}")
    print(f"  particion       H3.2, {len(particionar(TipoEvento.SEQUIA))} pliegues")
    print("  metrica         F1-macro, D-10")
    print(f"  referencia      {REFERENCIA}\n")

    print(f"  estimadores en la tabla   {len(DISPONIBLES)}")
    for nombre, historia in PENDIENTES.items():
        print(f"  PENDIENTE  {nombre:22} {historia}")
    print()

    for evento in TipoEvento:
        resultados = comparar(evento, filas)
        if not resultados or not resultados[0].por_pliegue:
            print(f"{evento.value.upper()}: sin pliegues evaluables\n")
            continue

        referencia = next((r for r in resultados if r.nombre == REFERENCIA), None)

        print(evento.value.upper())
        print(f"  {'estimador':22}{'F1-macro':>10}{'desv':>8}{'vs ref':>9}   por pliegue")
        for r in resultados:
            contra = (
                ""
                if referencia is None or r is referencia
                else f"{r.media - referencia.media:+.3f}"
            )
            print(
                f"  {r.nombre:22}{r.media:>10.3f}{r.desviacion:>8.3f}{contra:>9}   "
                f"{[round(v, 3) for v in r.por_pliegue]}"
            )
        print(f"  {'veredicto':22}{veredicto(resultados)}")

        sin_evaluar = {r.nombre: r.sin_evaluar for r in resultados if r.sin_evaluar}
        if sin_evaluar:
            print(f"  filas sin prediccion, no evaluadas: {sin_evaluar}")
        print()

    print("La tabla esta incompleta a proposito: faltan los tres algoritmos de")
    print("D-09. Agregarlos a DISPONIBLES es todo lo que hace falta; la particion,")
    print("la metrica y el trato de los None ya estan decididos aca.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
