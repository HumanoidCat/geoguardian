"""
Ajuste de hiperparametros, sin mirar los pliegues de prueba. Historia H3.8.

QUE PROBLEMA RESUELVE

H3.6 comparo los tres algoritmos **con los hiperparametros de fabrica** y el
veredicto fue que ninguno supera a la climatologica fuera del ruido. Quedaba una
pregunta legitima: si eso es del problema o de no haber ajustado nada. XGBoost
en lluvia quedo a +0.025 de la climatologica con un rango de 0.031 entre
pliegues, o sea cerca y adentro del ruido.

Esta historia busca mejores hiperparametros y **vuelve a pasar por la misma
regla**. No inventa una regla nueva para dejar ganar al modelo: D-39 decide
igual que antes, y si el afinado no gana fuera del ruido, sigue escribiendo la
climatologica.

EL DEFECTO QUE ESTE MODULO EXISTE PARA NO COMETER

Elegir hiperparametros mirando el mismo conjunto sobre el que despues se
informa el resultado **no mide que tan bueno es el modelo: mide cuanto se
busco**. Con 28 combinaciones, la mejor de todas sobre los pliegues de prueba
va a verse bien aunque ninguna sirva, y el numero resultante no es comparable
con la tabla de H3.6. No deja rastro: sale mas alto y parece un logro.

Por eso hay **dos particiones**:

    externa   la de H3.2, cinco pliegues. Es la que informa. Se toca UNA vez,
              al final, con el ganador ya elegido.
    interna   tres pliegues construidos **dentro de la ventana de
              entrenamiento del PRIMER pliegue externo**, que es la unica
              enteramente anterior a todos los bloques de prueba. Es donde se
              busca; `pliegues_internos` explica por que el primero y no el
              ultimo, y que limitacion trae.

Ninguna fecha de prueba interna cae dentro de ninguna ventana de prueba
externa, y el verificador lo comprueba comparando los dos conjuntos de fechas.

LA REJILLA SE DECLARA DE LO MAS SIMPLE A LO MAS COMPLEJO

No es cosmetico: la posicion de cada valor en su eje **es** la medida de
capacidad que usa el desempate. La capacidad de una combinacion es la suma de
las posiciones de sus valores. Asi no hay que comparar escalas que no se
parecen -arboles contra profundidad contra regularizacion-, y el orden queda
escrito y revisable.

COMO SE ELIGE, Y POR QUE NO ES "EL DE MAYOR F1"

Igual que D-39 y que CA-5 de H3.6: si varias combinaciones quedan **dentro del
ruido** de la mejor -media mayor o igual a la mejor menos su propio rango entre
pliegues-, gana la de **menos capacidad**. Un tercer decimal no justifica un
modelo mas grande, porque ese tercer decimal es ruido y el modelo mas grande es
para siempre.

USO

    python -m backend.modelado.afinar                       # los dos eventos
    python -m backend.modelado.afinar --evento lluvia_intensa
    python -m backend.modelado.afinar --algoritmo xgboost
    python -m backend.modelado.afinar --sin-externa         # solo la busqueda
"""

from __future__ import annotations

import argparse
import itertools
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado.comparar import (  # noqa: E402
    NO_MODELABLES,
    Resultado,
    comparar,
    elegir_escritor,
    estimadores_disponibles,
    veredicto,
)
from backend.modelado.particion import PLIEGUES, Pliegue, particionar  # noqa: E402
from contratos.enums import TipoEvento  # noqa: E402

# --------------------------------------------------------------------------- #
# La rejilla                                                                   #
# --------------------------------------------------------------------------- #
#
# Chica a proposito. Cabe en el tiempo de la historia y en el de una corrida que
# alguien mas pueda repetir. Si el resultado quedara pegado al borde, lo
# correcto es decirlo, no ampliar la busqueda hasta que salga.
#
# **Cada eje va de lo mas simple a lo mas complejo.** Ese orden es la definicion
# de capacidad que usa el desempate; cambiarlo cambia la regla.

REJILLA: dict[str, dict[str, tuple]] = {
    "regresion logistica": {
        # C mas grande es menos regularizacion, o sea mas capacidad.
        "C": (0.01, 0.1, 1.0, 10.0),
    },
    "random forest": {
        "n_estimators": (200, 400),
        # None es sin limite: el arbol crece hasta agotar la senal.
        "max_depth": (6, None),
        # Hojas mas grandes son mas restrictivas. 20 es mas simple que 1.
        "min_samples_leaf": (20, 1),
    },
    "xgboost": {
        "max_depth": (3, 6),
        "learning_rate": (0.05, 0.3),
        "n_estimators": (100, 300),
        # Igual que min_samples_leaf: exigir mas peso por hoja es regularizar.
        "min_child_weight": (10, 1),
    },
}

#: Cuantos pliegues internos. Menos que los cinco de H3.2 porque la ventana
#: interna es mas corta -es solo el entrenamiento- y con cinco los bloques de
#: prueba internos quedarian demasiado chicos para que la media signifique algo.
PLIEGUES_INTERNOS = 3


def combinaciones(algoritmo: str) -> list[dict]:
    """El producto cartesiano de la rejilla, en el orden declarado."""
    ejes = REJILLA[algoritmo]
    nombres = list(ejes)
    return [
        dict(zip(nombres, valores, strict=True)) for valores in itertools.product(*ejes.values())
    ]


def capacidad(algoritmo: str, parametros: dict) -> int:
    """
    Cuanta capacidad pide esta combinacion, como suma de posiciones en la rejilla.

    Es una medida ordinal, no fisica: sirve para comparar combinaciones del
    mismo algoritmo y para nada mas. Se apoya en que los ejes estan declarados
    de simple a complejo, que es una decision escrita y no una convencion.
    """
    return sum(REJILLA[algoritmo][clave].index(valor) for clave, valor in parametros.items())


# --------------------------------------------------------------------------- #
# Constructores con hiperparametros                                            #
# --------------------------------------------------------------------------- #
#
# Importaciones diferidas por el mismo motivo que en `comparar.py`: el contrato
# tiene que poder leerse sin cargar scikit-learn ni xgboost.


def _construir(algoritmo: str, parametros: dict):
    if algoritmo == "regresion logistica":
        from backend.modelado.regresion_logistica import RegresionLogistica

        return RegresionLogistica(parametros=dict(parametros))
    if algoritmo == "random forest":
        from backend.modelado.random_forest import BosqueAleatorio

        return BosqueAleatorio(parametros=dict(parametros))
    if algoritmo == "xgboost":
        from backend.modelado.xgboost_ import XGBoostEstimador

        return XGBoostEstimador(parametros=dict(parametros))
    raise ValueError(f"algoritmo {algoritmo!r} desconocido; hay rejilla para {sorted(REJILLA)}")


def fabrica(algoritmo: str, parametros: dict) -> Callable:
    """Una fabrica sin argumentos, que es lo que `comparar()` sabe llamar."""
    return lambda: _construir(algoritmo, parametros)


# --------------------------------------------------------------------------- #
# La particion interna                                                         #
# --------------------------------------------------------------------------- #


def pliegues_internos(evento: TipoEvento, cuantos: int = PLIEGUES_INTERNOS) -> list[Pliegue]:
    """
    Pliegues construidos dentro de la ventana de entrenamiento del **primer** externo.

    EL PRIMERO, Y NO EL ULTIMO, Y ESTO SE ESCRIBIO DESPUES DE EQUIVOCARSE

    La primera version uso la ventana del ultimo pliegue externo, razonando que
    es la mas larga y la que mas se parece a lo que el modelo vera en
    produccion. **Filtraba 7 752 dias de prueba**, y lo detecto el criterio CA-2
    antes de que existiera ningun resultado.

    El motivo es la ventana expansiva de H3.2: el entrenamiento del ultimo
    pliegue **contiene los bloques de prueba de los cuatro anteriores**. Buscar
    ahi es elegir hiperparametros sobre cuatro quintos del conjunto con el que
    despues se informa.

    La unica ventana enteramente anterior a **todos** los bloques de prueba
    externos es la de entrenamiento del primero. Esa se usa.

    **La limitacion que esto trae, dicha y no escondida.** La busqueda ve unos
    cinco anios y medio de datos, mientras que el modelo final se ajusta con
    treinta y cuatro. Unos hiperparametros elegidos sobre una muestra chica
    pueden no ser los mejores para la grande -es esperable que pidan mas
    regularizacion de la necesaria-. Lo correcto seria una validacion anidada:
    buscar dentro del entrenamiento de **cada** pliegue y evaluar en su prueba.
    Cuesta cinco veces mas y deja un juego de parametros por pliegue, que D-39
    no sabe usar porque necesita un escritor con **unos** parametros. Queda como
    trabajo futuro declarado, no como algo que se paso por alto.
    """
    externos = particionar(evento)
    if not externos:
        raise ValueError(f"{evento.value} no produjo pliegues externos")
    desde, hasta = externos[0].entrenamiento
    return particionar(evento, pliegues=cuantos, desde=desde, hasta=hasta)


def fechas_de_prueba(pliegues: list[Pliegue]) -> set[date]:
    """Todos los dias que caen en algun bloque de prueba. Para comprobar el solape."""
    dias: set[date] = set()
    for pliegue in pliegues:
        inicio, fin = pliegue.prueba
        actual = inicio
        while actual <= fin:
            dias.add(actual)
            actual = date.fromordinal(actual.toordinal() + 1)
    return dias


# --------------------------------------------------------------------------- #
# La busqueda                                                                  #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Candidato:
    """Una combinacion probada, con lo que rindio en la particion interna."""

    algoritmo: str
    parametros: dict
    media: float
    rango: float
    por_pliegue: list[float]
    capacidad: int
    saltados: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        valores = ", ".join(f"{k}={v}" for k, v in self.parametros.items())
        return (
            f"{self.media:.3f} +-{self.rango:.3f}  capacidad {self.capacidad}  "
            f"{valores}  ({len(self.por_pliegue)} pliegues)"
        )


def buscar(
    evento: TipoEvento,
    filas: list,
    caracteristicas: dict,
    algoritmo: str,
    internos: list[Pliegue] | None = None,
    registrar: Callable[..., None] = print,
) -> list[Candidato]:
    """
    Prueba cada combinacion sobre la particion interna. **No toca la externa.**

    Evalua con el mismo `comparar()` de H3.6 -misma metrica, mismo trato de
    nulos, mismos huecos- para que el numero interno y el externo se midan
    igual. Escribir un segundo bucle de evaluacion seria tener dos definiciones
    de lo mismo, que es como empiezan las cifras que no coinciden.
    """
    internos = internos if internos is not None else pliegues_internos(evento)
    salida: list[Candidato] = []
    for parametros in combinaciones(algoritmo):
        tabla = comparar(
            evento,
            filas,
            {algoritmo: fabrica(algoritmo, parametros)},
            caracteristicas,
            pliegues=internos,
        )
        fila: Resultado = tabla[0]
        salida.append(
            Candidato(
                algoritmo=algoritmo,
                parametros=parametros,
                media=fila.media,
                rango=fila.rango,
                por_pliegue=list(fila.por_pliegue),
                capacidad=capacidad(algoritmo, parametros),
                saltados=list(fila.saltados),
            )
        )
        registrar(f"    {salida[-1]}")
    return salida


def elegir(candidatos: list[Candidato]) -> tuple[Candidato | None, str]:
    """
    El mejor por F1 interno, o el mas simple dentro de su ruido.

    Es la regla de D-39 aplicada a hiperparametros en vez de a algoritmos: la
    ventaja tiene que ser mayor que lo que el propio candidato se mueve entre
    pliegues, o no hay ventaja que declarar.
    """
    utiles = [c for c in candidatos if c.por_pliegue]
    if not utiles:
        return None, "ninguna combinacion pudo ajustarse en la particion interna"

    utiles.sort(key=lambda c: (-c.media, c.capacidad))
    mejor = utiles[0]
    dentro = [c for c in utiles if c.media >= mejor.media - mejor.rango]
    elegido = min(dentro, key=lambda c: (c.capacidad, -c.media))

    if elegido is mejor and len(dentro) == 1:
        return mejor, f"gana sola: F1 interno {mejor.media:.3f}"
    if elegido is mejor:
        return mejor, (
            f"la mejor tambien es la mas simple de las {len(dentro)} que caen "
            f"dentro de su ruido ({mejor.rango:.3f})"
        )
    return elegido, (
        f"empate tecnico: {len(dentro)} combinaciones dentro del ruido de la mejor "
        f"({mejor.media:.3f} +-{mejor.rango:.3f}); se elige la de menos capacidad, "
        f"que rinde {elegido.media:.3f}"
    )


# --------------------------------------------------------------------------- #
# Lo elegido, y como lo usa la tuberia                                         #
# --------------------------------------------------------------------------- #
#
# Se llena con la corrida real de CA-8 y **queda versionado aca**: unos
# hiperparametros que viven en la memoria de quien corrio el guion no son un
# resultado, son una anecdota.
#
# Vacio significa "de fabrica", que es lo que H3.6 midio. No es un pendiente
# escondido: mientras este vacio, la tuberia se comporta exactamente como antes
# de esta historia.
#
# LO QUE SALIO, Y QUE SIGNIFICA (corrida del 2026-09-04, evidencia H3.8-afinado.md)
#
# Los seis resultados son **la esquina mas regularizada de su rejilla**, y no
# por casualidad: en las seis busquedas *todas* las combinaciones cayeron dentro
# del ruido de la mejor -4 de 4, 8 de 8, 16 de 16-, asi que el F1 interno no
# distinguio nada y decidio entero el desempate por simplicidad. Con tres
# pliegues internos sobre una ventana de cinco anios y medio, esta busqueda no
# puede separar una combinacion de otra. Eso es un resultado, no un defecto del
# guion, y esta dicho aca en vez de presentado como un ajuste fino.
#
# Contra la particion externa, el efecto real fue uno solo y en incendio: el
# bosque de fabrica venia **degenerado** -F1 0.494, por debajo del piso trivial,
# con las mismas cifras por pliegue que la trivial-, y regularizarlo lo llevo a
# 0.557. En lluvia el ajuste **empeoro** a xgboost, de 0.371 a 0.327: la esquina
# que conviene en cinco anios subajusta en treinta y cuatro.
#
# Se versionan igual los tres algoritmos por evento, incluidos los que
# empeoraron, porque quien escribe no se elige aca: lo decide D-39 con la tabla
# externa, en cada corrida. Guardar solo los que mejoraron seria elegir despues
# de ver el resultado.

AFINADOS: dict[str, dict[str, dict]] = {
    "lluvia_intensa": {
        "regresion logistica": {"C": 0.01},
        "random forest": {"n_estimators": 200, "max_depth": 6, "min_samples_leaf": 20},
        "xgboost": {
            "max_depth": 3,
            "learning_rate": 0.05,
            "n_estimators": 100,
            "min_child_weight": 10,
        },
    },
    "incendio": {
        "regresion logistica": {"C": 0.01},
        "random forest": {"n_estimators": 200, "max_depth": 6, "min_samples_leaf": 20},
        "xgboost": {
            "max_depth": 3,
            "learning_rate": 0.05,
            "n_estimators": 100,
            "min_child_weight": 10,
        },
    },
}


def fabricas(evento: TipoEvento, hay_caracteristicas: bool) -> dict[str, Callable]:
    """
    Los estimadores que la tuberia usa para este evento, ya afinados si los hay.

    Es la unica puerta: `estimar_riesgo` arma la tabla **y** el modelo que
    escribe con esta misma funcion, para que el que se evalua y el que escribe
    no puedan ser distintos.
    """
    base = estimadores_disponibles(hay_caracteristicas)
    for algoritmo, parametros in AFINADOS.get(evento.value, {}).items():
        if algoritmo in base:
            base[algoritmo] = fabrica(algoritmo, parametros)
    return base


# --------------------------------------------------------------------------- #
# Programa                                                                     #
# --------------------------------------------------------------------------- #


def afinables() -> list[str]:
    return [a for a in REJILLA]


ETIQUETAS = RAIZ / "datos" / "procesados" / "etiquetas.csv"
CARACTERISTICAS = RAIZ / "datos" / "procesados" / "caracteristicas.csv"


def cargar(etiquetas: Path = ETIQUETAS, caracteristicas: Path = CARACTERISTICAS):
    """Las mismas dos entradas que usa `estimar_riesgo`, leidas con sus mismos lectores."""
    from backend.modelado.evaluar_linea_base import leer as leer_etiquetas
    from backend.modelado.generar_caracteristicas import leer as leer_caracteristicas

    return leer_etiquetas(etiquetas), leer_caracteristicas(caracteristicas)


def afinar_evento(
    evento: TipoEvento,
    filas: list,
    caracteristicas: dict,
    algoritmos: list[str],
    con_externa: bool,
    registrar: Callable[..., None] = print,
) -> dict[str, dict]:
    """Busca, elige, y -si se pide- mide al ganador contra la particion externa."""
    if evento in NO_MODELABLES:
        registrar(f"\n{evento.value}: no es modelable (D-34). No se afina nada.")
        return {}

    internos = pliegues_internos(evento)
    externos = particionar(evento)
    registrar(
        f"\n{evento.value}: {len(externos)} pliegues externos, "
        f"{len(internos)} internos dentro del entrenamiento del primero "
        f"({internos[0].entrenamiento[0]} a {internos[-1].prueba[1]})"
    )

    elegidos: dict[str, dict] = {}
    for algoritmo in algoritmos:
        cuantas = len(combinaciones(algoritmo))
        registrar(f"\n  {algoritmo}: {cuantas} combinaciones x {len(internos)} pliegues internos")
        arranque = time.perf_counter()
        candidatos = buscar(evento, filas, caracteristicas, algoritmo, internos, registrar)
        elegido, motivo = elegir(candidatos)
        tardo = time.perf_counter() - arranque
        if elegido is None:
            registrar(f"  -> nada que elegir: {motivo} ({tardo:.1f} s)")
            continue
        registrar(f"  -> {elegido.parametros}")
        registrar(f"     {motivo} ({tardo:.1f} s)")
        elegidos[algoritmo] = elegido.parametros

    if not con_externa or not elegidos:
        return elegidos

    # La UNICA vez que se tocan los pliegues externos, con los ganadores ya
    # elegidos. Se corre dos veces sobre los MISMOS pliegues: la tabla de
    # fabrica -que es la de H3.6- y la afinada. Asi el antes y el despues salen
    # de la misma corrida y no de comparar contra un numero copiado.
    #
    # LOS AFINADOS ENTRAN CON SU NOMBRE DE SIEMPRE, Y ESTO IMPORTA.
    #
    # La primera version los llamaba "xgboost afinado". El verificador lo
    # detecto: `elegir_escritor` solo considera los cuatro nombres de
    # `SIMPLICIDAD`, asi que una fila con nombre nuevo **nunca podria escribir**
    # por bien que rindiera, y la regla de D-39 la habria ignorado en silencio.
    # Afinar hiperparametros no convierte a un algoritmo en otro: xgboost
    # afinado sigue siendo xgboost, y compite bajo ese nombre.
    registrar(f"\n  contra la particion externa de H3.2, {evento.value}:")
    de_fabrica = comparar(
        evento, filas, estimadores_disponibles(bool(caracteristicas)), caracteristicas
    )
    estimadores = estimadores_disponibles(bool(caracteristicas))
    for algoritmo, parametros in elegidos.items():
        estimadores[algoritmo] = fabrica(algoritmo, parametros)
    afinada = comparar(evento, filas, estimadores, caracteristicas)

    antes = {f.nombre: f for f in de_fabrica}
    registrar(f"    {'estimador':24} {'de fabrica':>16}   {'afinado':>16}")
    for fila in afinada:
        previa = antes.get(fila.nombre)
        columna_antes = f"{previa.media:.3f} +-{previa.rango:.3f}" if previa else "-"
        cambio = "" if fila.nombre not in elegidos else f"   ({fila.media - previa.media:+.3f})"
        registrar(
            f"    {fila.nombre:24} {columna_antes:>16}   "
            f"{fila.media:.3f} +-{fila.rango:.3f}{cambio}"
        )
    registrar(f"    veredicto de fabrica: {veredicto(de_fabrica)}")
    registrar(f"    veredicto afinado   : {veredicto(afinada)}")
    escritor_antes, _ = elegir_escritor(de_fabrica)
    escritor, motivo = elegir_escritor(afinada)
    registrar(f"    escribia: {escritor_antes or 'NADIE'}")
    registrar(f"    escribiria: {escritor or 'NADIE'} · {motivo}")
    return elegidos


def main(argumentos: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description="Ajusta hiperparametros sin mirar la prueba")
    analizador.add_argument(
        "--evento", action="append", choices=[e.value for e in TipoEvento], help="Repetible"
    )
    analizador.add_argument("--algoritmo", action="append", choices=afinables(), help="Repetible")
    analizador.add_argument(
        "--sin-externa", action="store_true", help="Solo la busqueda interna, sin medir al ganador"
    )
    analizador.add_argument("--etiquetas", type=Path, default=ETIQUETAS)
    analizador.add_argument("--caracteristicas", type=Path, default=CARACTERISTICAS)
    opciones = analizador.parse_args(argumentos)

    if not opciones.etiquetas.exists() or not opciones.caracteristicas.exists():
        print("\nHacen falta las dos: etiquetas.csv y caracteristicas.csv. Con la base levantada:")
        print("    python -m backend.modelado.generar_etiquetas")
        print("    python -m backend.modelado.generar_caracteristicas\n")
        return 1

    eventos = (
        [TipoEvento(e) for e in opciones.evento]
        if opciones.evento
        else [e for e in TipoEvento if e not in NO_MODELABLES]
    )
    algoritmos = opciones.algoritmo or afinables()

    print(f"Rejilla declarada, {sum(len(combinaciones(a)) for a in algoritmos)} combinaciones:")
    for algoritmo in algoritmos:
        print(
            f"  {algoritmo}: {len(combinaciones(algoritmo))} = "
            + " x ".join(f"{len(v)} {k}" for k, v in REJILLA[algoritmo].items())
        )
    print(f"Pliegues: {PLIEGUES} externos (H3.2), {PLIEGUES_INTERNOS} internos para buscar.")
    print("La particion externa se toca una sola vez, con el ganador ya elegido.\n")

    filas, caracteristicas = cargar(opciones.etiquetas, opciones.caracteristicas)
    print(f"Filas: {len(filas)} · caracteristicas: {len(caracteristicas)}")

    todos: dict[str, dict] = {}
    for evento in eventos:
        elegidos = afinar_evento(
            evento, filas, caracteristicas, algoritmos, not opciones.sin_externa
        )
        if elegidos:
            todos[evento.value] = elegidos

    print("\nAFINADOS, para pegar en afinar.py:\n")
    print(f"AFINADOS: dict[str, dict[str, dict]] = {todos!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
