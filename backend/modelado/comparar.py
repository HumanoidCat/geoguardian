"""Tabla comparativa de estimadores contra las lineas base. Historia H3.6.

===========================================================================
QUE PRODUCE, Y QUE NO
===========================================================================

**Produce la tabla**, no los modelos. H3.3, H3.4 y H3.5 -Regresion Logistica,
Random Forest y XGBoost- son historias aparte. Esta historia decide **como se
comparan** y deja el hueco declarado, no escondido.

Arranco con las dos lineas base de **H3.1**. La regresion entro con H3.3 el
2026-09-01 y el bosque con H3.4 el 2026-09-03, cada uno agregandose al registro
`CON_CARACTERISTICAS` sin tocar nada mas, y XGBoost con H3.5 el mismo dia.
`PENDIENTES` queda vacio: los tres de D-09 estan en la tabla.

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

    def probabilidades(
        self, observaciones: list[Observacion]
    ) -> list[dict[NivelRiesgo, float] | None]:
        """D-21 para una linea base: la distribucion empirica de su celda.

        Solo la climatologica sabe darla -es la tasa de cada clase en ese
        distrito y mes-. La trivial no la tiene y no la necesita: por D-39
        nunca escribe. Pedirsela es un error de programa, no un dato ausente.
        """
        if self._interno is None:
            raise RuntimeError(f"{self.nombre} no fue ajustado")
        if not hasattr(self._interno, "distribucion"):
            raise TypeError(f"{self.nombre} no entrega probabilidades: no puede escribir riesgo")
        return [self._interno.distribucion(o.codigo_distrito, o.fecha) for o in observaciones]

    @property
    def necesita_caracteristicas(self) -> bool:
        """Una linea base predice con el calendario: puede escribir fechas sin matriz."""
        return False


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


def _regresion_logistica():
    """Importacion diferida, para romper el ciclo con `regresion_logistica.py`.

    Ese modulo importa `Observacion` de aca -tiene que hacerlo: es el contrato-,
    asi que importarlo arriba cerraria el ciclo y Python fallaria al cargar
    cualquiera de los dos.

    Se difiere aca y no alla porque **el contrato tiene que poder leerse sin
    cargar ningun estimador**. Al reves, `comparar.py` no se podria importar sin
    arrastrar scikit-learn.
    """
    from .regresion_logistica import RegresionLogistica

    return RegresionLogistica()


def _random_forest():
    """Diferida por la misma razon que la regresion: `random_forest.py` importa
    `Observacion` de aca, y el contrato tiene que poder leerse sin scikit-learn."""
    from .random_forest import BosqueAleatorio

    return BosqueAleatorio()


def _xgboost():
    """Diferida, y ademas porque `xgboost` es una libreria aparte que no hace
    falta para leer el contrato ni para correr las lineas base."""
    from .xgboost_ import XGBoostEstimador

    return XGBoostEstimador()


#: Las lineas base de H3.1. **No necesitan caracteristicas** -es CA-1 de esa
#: historia- asi que estan siempre.
DISPONIBLES: dict[str, callable] = {
    "trivial": lambda: DesdeLineaBase("trivial", LineaBaseTrivial),
    "climatologica": lambda: DesdeLineaBase("climatologica", LineaBaseClimatologica),
}

#: Los que necesitan la matriz de H3.3 para poder correr. Entran a la tabla
#: **solo si la matriz esta cargada**, y si no siguen apareciendo como pendientes
#: con el motivo real.
#:
#: Registrarlos incondicionalmente rompe la herramienta: sin caracteristicas el
#: estimador falla con «las observaciones no traen caracteristicas» -que es el
#: comportamiento correcto- y se lleva por delante la comparacion entera.
#: Comprobado el 2026-09-01: `verificar_h36` pasaba de verde a rojo.
CON_CARACTERISTICAS: dict[str, callable] = {
    "regresion logistica": _regresion_logistica,
    "random forest": _random_forest,
    "xgboost": _xgboost,
}


def estimadores_disponibles(hay_caracteristicas: bool) -> dict[str, callable]:
    """Que estimadores pueden correr con lo que hay cargado."""
    if not hay_caracteristicas:
        return dict(DISPONIBLES)
    return {**DISPONIBLES, **CON_CARACTERISTICAS}


def pendientes(hay_caracteristicas: bool) -> dict[str, str]:
    """Los que faltan, con el motivo real y no solo el numero de historia."""
    faltan = dict(PENDIENTES)
    if not hay_caracteristicas:
        # Uno por cada estimador que aprende, y no una lista escrita a mano:
        # el dia que entre otro (H3.5) tiene que aparecer aca sin que nadie se
        # acuerde de agregarlo. Un pendiente que falta en esta lista es
        # indistinguible de uno que ya esta hecho.
        historias = {"regresion logistica": "H3.3", "random forest": "H3.4", "xgboost": "H3.5"}
        for nombre in CON_CARACTERISTICAS:
            faltan[nombre] = (
                f"{historias.get(nombre, '?')}, escrita y probada; necesita "
                "datos/procesados/caracteristicas.csv, que produce "
                "`python -m backend.modelado.generar_caracteristicas`"
            )
    return faltan


# --------------------------------------------------------------------------- #
# Lo que D-34 declara no modelable                                              #
# --------------------------------------------------------------------------- #
#
# **La sequia no se modela, y eso es un resultado, no una omision.**
#
# D-34 conto los episodios a nivel canton -contarlos por distrito multiplicaba la
# muestra por 6 sin agregar informacion, porque una sequia en Tilaran no es ocho
# sequias- y midio cuantos cae en cada pliegue de H3.2:
#
#     lluvia intensa    31, 60, 89, 109, 129
#     incendio          16, 21, 28,  44,  55
#     sequia             2,  3,  3,   6,   9
#
# **CA-6 de H3.0** pide 30 episodios en total y 10 como minimo por particion de
# entrenamiento. La sequia falla los dos: 9 en total y 2 en el peor pliegue.
#
# Es consecuencia directa de **D-32**, que cambio SPI-3 por SPI-6: una ventana
# mas larga detecta sequias mas reales y por eso encuentra muchas menos. La
# decision se tomo sabiendo el costo; esto es el costo.
#
# POR QUE SE DECLARA Y NO SE OMITE
#
# Una tabla a la que le falta una fila se lee como un olvido. Una que dice «no
# modelable, 9 episodios, hacen falta 30» es un hallazgo, y es de los que van en
# la seccion de limitaciones del documento. Es la misma regla que PENDIENTES.
#
# Las lineas base **si** se corren sobre la sequia: no aprenden de episodios, y
# saber que la climatologica hace sobre ella es informacion util.
NO_MODELABLES: dict[TipoEvento, str] = {
    TipoEvento.SEQUIA: (
        "D-34: 9 episodios en el canton, 2 en el peor pliegue. "
        "CA-6 de H3.0 pide 30 y 10. Consecuencia medida de D-32 (SPI-6)"
    ),
}

# El texto dice el estado real y no solo la historia, para que nadie lea
# «pendiente» como «no empezado».
#
# `regresion logistica` ya no vive aca: desde H3.3 esta escrita, probada y
# **conectada**, y `pendientes()` la vuelve a listar solo si falta la matriz.
PENDIENTES: dict[str, str] = {}


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

    #: Motivo por cada pliegue que el estimador no pudo ajustar. Va en el
    #: resultado y no en un registro aparte porque **una media sobre tres
    #: pliegues no es comparable con una sobre cinco**, y quien lea la tabla
    #: tiene que poder verlo sin ir a buscarlo.
    saltados: list[str] = field(default_factory=list)

    @property
    def rango(self) -> float:
        """Cuanto se mueve entre pliegues. Es la vara para decir si dos empatan."""
        return max(self.por_pliegue) - min(self.por_pliegue) if self.por_pliegue else 0.0


def comparar(
    evento: TipoEvento,
    filas: list,
    estimadores: dict[str, callable] | None = None,
    caracteristicas: dict[tuple[str, date], dict[str, float]] | None = None,
) -> list[Resultado]:
    """Corre todos los estimadores sobre **los mismos** pliegues del mismo evento.

    `caracteristicas` mapea (distrito, fecha) a las entradas que produjo H3.3. Si
    viene vacio, las `Observacion` salen sin caracteristicas y **solo las lineas
    base pueden correr**: es CA-1 de H3.1 que ellas no las miren.

    Si el evento esta en `NO_MODELABLES`, los estimadores que aprenden se
    descartan y solo quedan las lineas base. No se lanza una excepcion porque la
    tabla tiene que poder mostrar la fila con su motivo, y una excepcion la
    dejaria vacia.
    """
    estimadores = estimadores if estimadores is not None else DISPONIBLES
    if evento in NO_MODELABLES:
        estimadores = {n: f for n, f in estimadores.items() if n in DISPONIBLES}
    caracteristicas = caracteristicas or {}
    columna = COLUMNA[evento]

    # CA-6 de H3.0: el incendio solo donde D-25 dice que hay senal.
    if evento is TipoEvento.INCENDIO:
        filas = [f for f in filas if f[0] in DISTRITOS_CON_INCENDIO]

    def observacion(codigo: str, fecha: date) -> Observacion:
        return Observacion(codigo, fecha, caracteristicas.get((codigo, fecha), {}))

    acumulado: dict[str, list[float]] = {n: [] for n in estimadores}
    huecos: dict[str, int] = {n: 0 for n in estimadores}
    saltados: dict[str, list[str]] = {n: [] for n in estimadores}

    for pliegue in particionar(evento):
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

        obs_ent = [o for o, _ in ent]
        eti_ent = [e for _, e in ent]
        obs_pru = [o for o, _ in pru]
        verdad = [e for _, e in pru]

        for nombre, fabrica in estimadores.items():
            # UN PLIEGUE QUE NO SE PUEDE AJUSTAR SE SALTA, NO TUMBA LA TABLA.
            #
            # `RegresionLogistica.ajustar` se niega en dos casos legitimos: si el
            # entrenamiento tiene una sola clase -no hay nada que aprender- o si
            # ninguna fila trae todas sus caracteristicas. Los dos son
            # informacion, no errores del programa.
            #
            # Se salta el pliegue **de ese estimador**, no de todos: las lineas
            # base si pueden con el, y compararlas sobre pliegues distintos seria
            # peor que no compararlas. Por eso `por_pliegue` puede tener largos
            # distintos y la tabla imprime cuantos entraron.
            try:
                modelo = fabrica().ajustar(obs_ent, eti_ent)
                prediccion = modelo.predecir(obs_pru)
            except ValueError as motivo:
                saltados[nombre].append(str(motivo))
                continue
            metrica, _, evaluadas = f1_macro(verdad, prediccion)
            acumulado[nombre].append(metrica)
            huecos[nombre] += len(verdad) - evaluadas

    resultados = []
    for nombre, valores in acumulado.items():
        media, desviacion, _ = resumen_f1(valores) if valores else (0.0, 0.0, [])
        resultados.append(
            Resultado(nombre, valores, media, desviacion, huecos[nombre], saltados[nombre])
        )

    return sorted(resultados, key=lambda r: -r.media)


#: Orden de simplicidad de D-39, del mas simple al mas complejo. La trivial no
#: aparece porque nunca escribe: es el piso, no una estimacion.
SIMPLICIDAD: tuple[str, ...] = ("climatologica", "regresion logistica", "random forest", "xgboost")

#: El piso. Un estimador que no lo alcanza no escribe.
PISO = "trivial"


def elegir_escritor(resultados: list[Resultado]) -> tuple[str | None, str]:
    """Quien escribe `analitico.riesgo` para este evento, por la regla de D-39.

    Devuelve (nombre, motivo). `None` cuando nadie puede escribir, con el motivo
    escrito, porque «sin fila» tambien es una decision y tiene que poder
    leerse.

    La regla, en el orden en que se aplica:

      1. La trivial nunca escribe (D-07: «siempre BAJO» no es una estimacion).
      2. Nadie escribe por debajo del piso: media < media de la trivial.
      3. Si el primero elegible supera al segundo fuera del ruido -ventaja mayor
         que su propio rango, la regla de CA-5-, escribe el primero.
      4. Si no, escribe el mas simple de los elegibles que quedan dentro del
         ruido del primero: media >= media del primero - rango del primero.

    Lo que NO hace: mirar nombres para preferir modelos. Si un dia un modelo
    gana fuera del ruido, sale de aca sin tocar nada.
    """
    if not resultados:
        return None, "no hay resultados"
    piso = next((r.media for r in resultados if r.nombre == PISO), None)
    elegibles = [
        r
        for r in resultados
        if r.nombre in SIMPLICIDAD and r.por_pliegue and (piso is None or r.media >= piso)
    ]
    if not elegibles:
        detalle = f"; el piso trivial esta en {piso:.3f}" if piso is not None else ""
        return None, f"ningun estimador elegible alcanza el piso{detalle}: el evento queda sin fila"

    elegibles.sort(key=lambda r: -r.media)
    primero = elegibles[0]
    if len(elegibles) == 1 or (primero.media - elegibles[1].media) > primero.rango:
        return primero.nombre, f"gana fuera del ruido: F1-macro {primero.media:.3f}"

    dentro = [r for r in elegibles if r.media >= primero.media - primero.rango]
    mas_simple = min(dentro, key=lambda r: SIMPLICIDAD.index(r.nombre))
    return mas_simple.nombre, (
        f"empate tecnico: {primero.nombre} le saca {primero.media - elegibles[1].media:+.3f} "
        f"al siguiente con rango {primero.rango:.3f}; escribe el mas simple dentro del ruido"
    )


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
    p.add_argument(
        "--caracteristicas",
        type=Path,
        default=RAIZ / "datos" / "procesados" / "caracteristicas.csv",
        help="matriz de H3.3. Si no existe, corren solo las lineas base.",
    )
    args = p.parse_args()

    if not args.etiquetas.exists():
        print(f"\nNo existe {args.etiquetas}.\n")
        print("Se genera con la base levantada:\n")
        print("    python -m backend.modelado.generar_etiquetas\n")
        return 1

    filas = leer(args.etiquetas)

    # LA AUSENCIA DE LA MATRIZ NO ES UN ERROR, ES UNA TABLA MAS CORTA.
    #
    # Las lineas base de H3.1 no la necesitan, y poder correr la comparacion sin
    # ella mantiene el guion util cuando alguien solo quiere ver las referencias.
    # Lo que si seria un error es correr sin ella **y no decirlo**: por eso el
    # encabezado imprime cuantas filas y columnas se cargaron, y `pendientes()`
    # vuelve a listar la regresion con el motivo real.
    caracteristicas: dict[tuple[str, date], dict[str, float]] = {}
    if args.caracteristicas.exists():
        from backend.modelado.generar_caracteristicas import leer as leer_caracteristicas

        caracteristicas = leer_caracteristicas(args.caracteristicas)
    n_columnas = len({c for f in caracteristicas.values() for c in f})

    print("\nTabla comparativa de estimadores · H3.6")
    print(f"  filas leidas    {len(filas)}")
    print(f"  particion       H3.2, {len(particionar(TipoEvento.SEQUIA))} pliegues")
    print("  metrica         F1-macro, D-10")
    print(f"  referencia      {REFERENCIA}\n")

    estimadores = estimadores_disponibles(bool(caracteristicas))
    print(f"  caracteristicas {len(caracteristicas)} filas, {n_columnas} columnas")
    print(f"  estimadores en la tabla   {len(estimadores)}")
    for nombre, historia in pendientes(bool(caracteristicas)).items():
        print(f"  PENDIENTE  {nombre:22} {historia}")
    for evento, motivo in NO_MODELABLES.items():
        print(f"  NO MODELABLE  {evento.value:19} {motivo}")
    print()

    for evento in TipoEvento:
        resultados = comparar(evento, filas, estimadores, caracteristicas)
        if not resultados or not resultados[0].por_pliegue:
            print(f"{evento.value.upper()}: sin pliegues evaluables\n")
            continue

        referencia = next((r for r in resultados if r.nombre == REFERENCIA), None)

        print(evento.value.upper())
        if evento in NO_MODELABLES:
            print(f"  solo lineas base. {NO_MODELABLES[evento]}")
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
        for r in resultados:
            for motivo in r.saltados:
                print(f"  pliegue saltado por {r.nombre}: {motivo}")
        print()

    faltan = pendientes(bool(caracteristicas))
    if faltan:
        print("La tabla esta incompleta a proposito: faltan " + ", ".join(faltan))
        print("Agregarlos a CON_CARACTERISTICAS es todo lo que hace falta; la particion,")
        print("la metrica y el trato de los None ya estan decididos aca.\n")
    else:
        print("Los tres algoritmos de D-09 estan en la tabla.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
