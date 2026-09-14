"""Genera las figuras de resultados del documento de investigacion.

POR QUE ESTAN SEPARADAS DE LOS DIAGRAMAS

`generar_diagramas.py` produce **arquitectura**: cosas que se declaran. Esto
produce **resultados**: cosas que se miden. Se separan porque tienen fuentes
distintas y porque una de las dos no puede correr en la integracion continua.

Las figuras salen del conjunto etiquetado, que es un artefacto derivado de la
base y no se versiona. Asi que **estas se regeneran a mano cuando hay datos**, y
los diagramas de arquitectura se regeneran siempre.

QUE PRODUCE

    1. lineas-base.png       F1-macro de las dos lineas base, por evento, con la
                             dispersion entre pliegues
    2. contraste-catalogo.png  cobertura y realce contra los eventos reales
    3. cobertura-datos.png   que periodo cubre cada fuente, y donde no hay dato
    4. nate-por-distrito.png el problema, en un solo dia
    5. comparativa-algoritmos.png  los tres algoritmos contra las dos lineas
                             base, con el rango entre pliegues
    6. episodios-por-pliegue.png   episodios de cada evento por pliegue de
                             entrenamiento, contra el umbral de CA-6

Las cuatro primeras se dibujan **desde la medicion**, no desde numeros escritos
a mano. Las dos ultimas se dibujan **desde una tabla versionada** en
`docs/figuras/datos/`, que transcribe una corrida real y lo declara: es lo que
pidio el profesor el 2026-08-27, «tabular los datos para hacer los graficos».

Si el dato cambia, la figura cambia. Es el mismo criterio que el resto del
proyecto aplica a la matriz de trazabilidad y a las cifras de la documentacion.

Uso:
    python docs/herramientas/generar_figuras.py               # todas; necesita etiquetas.csv
    python docs/herramientas/generar_figuras.py --tabuladas   # solo las 5 y 6, sin base
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

SALIDA = RAIZ / "docs" / "figuras"

# Misma paleta que los diagramas, y por la misma razon: el documento puede
# terminar impreso en blanco y negro, y estos tres se distinguen en gris.
AZUL = "#4a6fa5"
ARENA = "#c8a15a"
GRIS = "#8a9199"
TINTA = "#1f2328"

#: El enum de eventos usa identificadores sin tilde -`sequia`- porque son claves,
#: no texto para leer. Las figuras si son para leer, asi que se rotulan aparte.
ROTULO = {
    "lluvia_intensa": "Lluvia intensa",
    "sequia": "Sequía",
    "incendio": "Incendio",
}


def _coma(valor: float, decimales: int = 2) -> str:
    """Separador decimal espanol. El resto del documento usa coma."""
    return f"{valor:.{decimales}f}".replace(".", ",")


def _matplotlib():
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as error:  # pragma: no cover
        raise RuntimeError("Falta matplotlib. pip install matplotlib") from error

    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 9,
            "axes.edgecolor": GRIS,
            "axes.labelcolor": TINTA,
            "text.color": TINTA,
            "xtick.color": TINTA,
            "ytick.color": TINTA,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 200,
        }
    )
    return plt


# =========================================================================== #
# 1 · Las dos lineas base                                                      #
# =========================================================================== #


def figura_lineas_base(plt) -> Path:
    """F1-macro por evento, con la dispersion entre pliegues como barra de error.

    **La barra de error es el punto de la figura, no un adorno.** Sin ella, la
    columna del incendio y la de la trivial se ven distintas y la conclusion de
    la seccion VI-D -que no se pueden distinguir- resulta incomprensible. Con
    ella se ve de un vistazo que los intervalos se solapan.
    """
    from backend.modelado.comparar import comparar
    from backend.modelado.evaluar_linea_base import leer
    from contratos.enums import TipoEvento

    filas = leer(RAIZ / "datos" / "procesados" / "etiquetas.csv")

    eventos, trivial, clima, dt, dc = [], [], [], [], []
    for evento in TipoEvento:
        resultados = {r.nombre: r for r in comparar(evento, filas)}
        if "trivial" not in resultados:
            continue
        eventos.append(ROTULO[evento.value])
        trivial.append(resultados["trivial"].media)
        dt.append(resultados["trivial"].desviacion)
        clima.append(resultados["climatologica"].media)
        dc.append(resultados["climatologica"].desviacion)

    figura, eje = plt.subplots(figsize=(6.4, 3.2))
    x = range(len(eventos))
    ancho = 0.36
    eje.bar(
        [i - ancho / 2 for i in x],
        trivial,
        ancho,
        yerr=dt,
        capsize=3,
        label="Línea base trivial",
        color=GRIS,
        error_kw={"ecolor": TINTA, "lw": 0.9},
    )
    eje.bar(
        [i + ancho / 2 for i in x],
        clima,
        ancho,
        yerr=dc,
        capsize=3,
        label="Línea base climatológica",
        color=AZUL,
        error_kw={"ecolor": TINTA, "lw": 0.9},
    )

    eje.set_xticks(list(x))
    eje.set_xticklabels(eventos)
    eje.set_ylabel("F1-macro")
    eje.set_ylim(0, 0.65)
    eje.legend(frameon=False, fontsize=8, loc="upper left")
    eje.set_title("Desempeño de las dos líneas base, por evento", fontsize=10, loc="left")
    eje.grid(axis="y", color=GRIS, alpha=0.25, lw=0.6)
    eje.set_axisbelow(True)

    figura.tight_layout()
    destino = SALIDA / "lineas-base.png"
    figura.savefig(destino, bbox_inches="tight")
    plt.close(figura)
    return destino


# =========================================================================== #
# 2 · Contraste contra el catalogo                                             #
# =========================================================================== #


def figura_contraste(plt) -> Path:
    """Cobertura contra tasa base, que es lo que hace interpretable al realce.

    Una cobertura del 64,7 % no dice nada sola. Puesta al lado de su tasa base,
    la figura muestra de un vistazo de donde sale el realce.

    **Todas las barras usan la ventana estricta de siete dias.** Antes la sequia
    se dibujaba con su ventana ampliada, porque con SPI-3 era la unica en la que
    detectaba algo, y la figura lo rotulaba «(ventana 90 d)». Eso ponia en el
    mismo grafico dos barras que no eran comparables: **una ventana mas larga
    detecta mas por construccion**, y el rotulo lo advertia sin arreglarlo.

    Desde D-32 la sequia detecta los siete con la ventana estricta, asi que la
    excepcion sobra. Se retira, y con eso las tres barras miden lo mismo.
    """
    from backend.modelado.contrastar_catalogo import (
        CATALOGO,
        ETIQUETAS,
        contrastar,
        leer_catalogo,
    )
    from backend.modelado.etiquetado import HORIZONTE_DIAS
    from backend.modelado.evaluar_linea_base import leer
    from contratos.enums import TipoEvento

    registros = leer_catalogo(CATALOGO)
    filas = leer(ETIQUETAS)

    etiquetas, cobertura, base = [], [], []
    for evento in TipoEvento:
        r = contrastar(evento, registros, filas, HORIZONTE_DIAS)
        if not r.contrastables:
            continue
        etiquetas.append(ROTULO[evento.value])
        cobertura.append(r.cobertura * 100)
        base.append(r.tasa_base * 100)

    figura, eje = plt.subplots(figsize=(6.4, 3.2))
    x = range(len(etiquetas))
    ancho = 0.36
    eje.bar(
        [i - ancho / 2 for i in x],
        cobertura,
        ancho,
        label="Eventos reales con marca previa",
        color=ARENA,
    )
    eje.bar(
        [i + ancho / 2 for i in x],
        base,
        ancho,
        label="Tasa base: días marcados en general",
        color=GRIS,
    )

    for i, (c, b) in enumerate(zip(cobertura, base, strict=True)):
        if b > 0:
            eje.text(
                i,
                max(c, b) + 3,
                f"{_coma(c / b)}×",
                ha="center",
                fontsize=9,
                color=TINTA,
                fontweight="bold",
            )

    eje.set_xticks(list(x))
    eje.set_xticklabels(etiquetas)
    eje.set_ylabel("Porcentaje")
    eje.set_ylim(0, 132)
    eje.legend(frameon=False, fontsize=8, loc="upper left", ncol=1)
    eje.set_title(
        "Etiquetado contra 46 eventos históricos: cobertura, tasa base y realce",
        fontsize=10,
        loc="left",
    )
    eje.grid(axis="y", color=GRIS, alpha=0.25, lw=0.6)
    eje.set_axisbelow(True)

    figura.tight_layout()
    destino = SALIDA / "contraste-catalogo.png"
    figura.savefig(destino, bbox_inches="tight")
    plt.close(figura)
    return destino


# =========================================================================== #
# 3 · Cobertura temporal de las fuentes                                        #
# =========================================================================== #


def figura_cobertura(plt) -> Path:
    """Que periodo cubre cada evento, y donde el dato no existe.

    Es la figura que explica de un vistazo por que el incendio es el componente
    mas debil: su barra empieza diez anios despues y termina antes.
    """
    from datetime import timedelta

    from backend.modelado.etiquetado import HORIZONTE_DIAS
    from backend.modelado.evaluar_linea_base import COLUMNA, leer
    from contratos.enums import TipoEvento

    filas = leer(RAIZ / "datos" / "procesados" / "etiquetas.csv")

    # El periodo que se dibuja es el que la etiqueta **describe**, no la fecha en
    # que esta escrita. La etiqueta del dia t habla de la ventana (t, t+7].
    #
    # Sin esta correccion la figura decia que el incendio empieza en 2000, porque
    # la primera etiqueta es del 2000-12-31 -su ventana arranca el 2001-01-01- y
    # contradecia al texto, que dice 2001. Las dos cifras eran ciertas y hablaban
    # de cosas distintas.
    tramos = []
    for evento in TipoEvento:
        columna = COLUMNA[evento]
        fechas = [f for _, f, n in filas if n[columna] is not None]
        if fechas:
            desde = min(fechas) + timedelta(days=1)
            hasta = max(fechas) + timedelta(days=HORIZONTE_DIAS)
            tramos.append((ROTULO[evento.value], desde.year, hasta.year))

    figura, eje = plt.subplots(figsize=(6.4, 2.4))
    minimo = min(t[1] for t in tramos)
    maximo = max(t[2] for t in tramos)

    for i, (_nombre, desde, hasta) in enumerate(tramos):
        eje.barh(i, hasta - desde + 1, left=desde, height=0.5, color=AZUL)
        if desde > minimo:
            eje.barh(
                i,
                desde - minimo,
                left=minimo,
                height=0.5,
                color=GRIS,
                alpha=0.28,
                hatch="///",
                edgecolor="white",
            )
        eje.text(hasta + 0.6, i, f"{desde}–{hasta}", va="center", fontsize=8, color=TINTA)

    eje.set_yticks(range(len(tramos)))
    eje.set_yticklabels([t[0] for t in tramos])
    eje.set_xlim(minimo - 1, maximo + 11)
    eje.set_xlabel("Año")
    eje.set_title(
        "Período que describe cada etiqueta. La trama marca dónde no hay dato",
        fontsize=10,
        loc="left",
    )
    eje.grid(axis="x", color=GRIS, alpha=0.25, lw=0.6)
    eje.set_axisbelow(True)
    eje.invert_yaxis()

    figura.tight_layout()
    destino = SALIDA / "cobertura-datos.png"
    figura.savefig(destino, bbox_inches="tight")
    plt.close(figura)
    return destino


# =========================================================================== #
# 4 · El problema, en un solo dia                                              #
# =========================================================================== #


def figura_nate(plt) -> Path:
    """Perdidas por distrito el 2017-10-05, el dia que Nate cruzo el canton.

    **Es la unica figura que ilustra el problema y no un resultado.** Va en la
    seccion I porque ahi es donde pega: los siete distritos con registro
    reportaron danos el mismo dia, por el mismo temporal, y entre el mayor y el
    menor hay un factor de cuatrocientos.

    Eso es lo que un aviso a escala de canton no puede decir, y decirlo con una
    tabla de siete filas no tiene la misma fuerza que verlo.

    **La escala es logaritmica, y hay que saberlo al leerla.** En escala lineal,
    seis de las siete barras quedan pegadas al cero y la figura solo muestra que
    Quebrada Grande fue lo peor -que es cierto y no es el punto-. El punto es el
    *rango*, y el rango solo se ve en logaritmo. Se rotula en el eje.

    Los datos salen del catalogo, no escritos a mano: si el catalogo se corrige,
    la figura se corrige.
    """
    import csv
    import re

    catalogo = RAIZ / "docs" / "investigacion" / "catalogo-eventos.csv"
    #: Nombre legible de cada distrito. El codigo no le dice nada al lector.
    NOMBRES = {
        "50801": "Tilarán",
        "50802": "Quebrada Grande",
        "50803": "Tronadora",
        "50804": "Santa Rosa",
        "50805": "Líbano",
        "50806": "Tierras Morenas",
        "50807": "Arenal",
        "50808": "Arenal (Nuevo)",
    }

    perdidas: dict[str, float] = {}
    with catalogo.open(encoding="utf-8", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            if fila.get("fecha_inicio", "").strip() != "2017-10-05":
                continue
            # «Perdidas: 726148 USD» o «Perdidas registradas: 1808 USD».
            hallado = re.search(r"[Pp]érdidas[^.]*?(\d[\d\s.,]*)\s*USD", fila["descripcion"])
            if not hallado:
                hallado = re.search(r"[Pp]erdidas[^.]*?(\d[\d\s.,]*)\s*USD", fila["descripcion"])
            if hallado:
                perdidas[fila["codigo_distrito"]] = float(
                    hallado.group(1).replace(" ", "").replace(",", "").replace(".", "")
                )

    if not perdidas:
        raise RuntimeError(
            "no se hallaron perdidas del 2017-10-05 en el catalogo; "
            "si cambio el formato de las descripciones, hay que ajustar el patron"
        )

    orden = sorted(perdidas.items(), key=lambda par: par[1])
    nombres = [NOMBRES.get(codigo, codigo) for codigo, _ in orden]
    valores = [valor for _, valor in orden]

    figura, eje = plt.subplots(figsize=(6.4, 3.0))
    barras = eje.barh(nombres, valores, color=AZUL, height=0.62)
    # El extremo se destaca porque el contraste entre extremos ES la figura.
    barras[-1].set_color(ARENA)
    barras[0].set_color(GRIS)

    eje.set_xscale("log")
    eje.set_xlabel("Pérdidas del 5 de octubre de 2017, en dólares · escala logarítmica")
    eje.set_xlim(1_000, 2_000_000)

    for barra, valor in zip(barras, valores, strict=True):
        eje.text(
            valor * 1.15,
            barra.get_y() + barra.get_height() / 2,
            f"{valor:,.0f}".replace(",", " "),
            va="center",
            fontsize=8,
            color=TINTA,
        )

    # **El rotulo cuenta las barras, no los distritos afectados.** La primera
    # version decia «siete distritos» y la figura mostraba seis: Libano reporto
    # dano ese mismo dia -15 400 m de via- sin cifra en dolares, asi que no
    # tiene barra. Un titulo que no coincide con lo que se ve es peor que un
    # titulo pobre, y en una figura sobre disparidad entre distritos, contar mal
    # los distritos es el error mas caro posible.
    razon = max(valores) / min(valores)
    eje.set_title(
        f"Un temporal, un día, {len(valores)} distritos con pérdidas cuantificadas:\n"
        f"{_coma(razon, 0)}× entre el mayor y el menor",
        fontsize=9,
        color=TINTA,
        pad=10,
    )
    eje.spines[["top", "right"]].set_visible(False)
    eje.tick_params(labelsize=8)
    figura.tight_layout()

    destino = SALIDA / "nate-por-distrito.png"
    figura.savefig(destino, dpi=200)
    plt.close(figura)
    return destino


# =========================================================================== #
# 5 y 6 · Figuras que salen de una tabla, no del conjunto etiquetado           #
# =========================================================================== #
#
# El profesor pidio el 2026-08-27 «tabular los datos para hacer los graficos».
# Estas dos figuras siguen esa regla al pie de la letra: la tabla es un CSV en
# `docs/figuras/datos/`, versionado, y la figura se dibuja desde ahi. No leen
# el conjunto etiquetado, asi que se pueden regenerar en cualquier maquina.
#
# Las tablas son TRANSCRIPCIONES de corridas reales -H3.8 del 2026-09-04 y
# D-34- y lo dicen en su README. Si el arnes vuelve a correr y una cifra
# cambia, se cambia el CSV y se regenera; nunca se retoca el PNG.

DATOS = SALIDA / "datos"

NOMBRE_ESTIMADOR = {
    "trivial": "Trivial",
    "climatologica": "Climatológica",
    "regresion_logistica": "Regresión logística",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
}


def _leer_csv(nombre: str) -> list[dict[str, str]]:
    import csv

    with (DATOS / nombre).open(encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


def figura_comparativa(plt) -> Path:
    """F1-macro de los cinco estimadores por evento, con el rango entre pliegues.

    Es la figura del resultado central del documento: **ningun algoritmo
    supera a la linea base climatologica fuera del ruido**. Como en
    `figura_lineas_base`, la barra de error es el punto: sin ella se ve una
    barra mas alta que otra y no se entiende por que no hay ganador.

    La sequia aparece solo con sus dos lineas base, porque no es modelable
    (D-34) y no se entreno nada sobre ella. Omitirla haria parecer un olvido.
    """
    filas = _leer_csv("comparativa-algoritmos.csv")
    orden_eventos = ["lluvia_intensa", "sequia", "incendio"]
    orden_estimadores = [
        "trivial",
        "climatologica",
        "regresion_logistica",
        "random_forest",
        "xgboost",
    ]
    colores = {
        "trivial": GRIS,
        "climatologica": AZUL,
        "regresion_logistica": "#9fb3cf",
        "random_forest": ARENA,
        "xgboost": "#8c6d3a",
    }

    figura, eje = plt.subplots(figsize=(6.4, 3.4))
    ancho = 0.15
    for j, evento in enumerate(orden_eventos):
        presentes = [f for f in filas if f["evento"] == evento]
        for k, estimador in enumerate(orden_estimadores):
            fila = next((f for f in presentes if f["estimador"] == estimador), None)
            x = j + (k - 2) * ancho
            if fila is None:
                continue
            valor = float(fila["f1_macro"])
            rango = float(fila["rango_entre_pliegues"])
            eje.bar(
                x,
                valor,
                ancho,
                yerr=rango / 2,
                capsize=2,
                color=colores[estimador],
                error_kw={"ecolor": TINTA, "lw": 0.8},
                edgecolor="white" if fila["escribe"] == "no" else TINTA,
                linewidth=0.6 if fila["escribe"] == "no" else 1.4,
            )
            if fila["escribe"] == "si":
                eje.text(
                    x, valor + rango / 2 + 0.02, "escribe", ha="center", fontsize=6.5, color=TINTA
                )

    # La leyenda se arma con parches propios y no con la primera barra de cada
    # estimador: si no, el borde grueso de «escribe» se cuela en la leyenda.
    from matplotlib.patches import Patch

    parches = [Patch(color=colores[e], label=NOMBRE_ESTIMADOR[e]) for e in orden_estimadores]
    eje.legend(handles=parches, frameon=False, fontsize=7.5, loc="upper left", ncol=2)
    eje.text(
        1 + 1.5 * ancho,
        0.05,
        "no modelable:\nsolo las dos\nlíneas base",
        ha="left",
        va="bottom",
        fontsize=7,
        color=TINTA,
    )
    eje.set_xticks(range(len(orden_eventos)))
    eje.set_xticklabels([ROTULO[e] for e in orden_eventos])
    eje.set_ylabel("F1-macro")
    eje.set_ylim(0, 0.72)
    eje.set_title(
        "Tres algoritmos contra dos líneas base, con la dispersión entre pliegues",
        fontsize=10,
        loc="left",
    )
    eje.grid(axis="y", color=GRIS, alpha=0.25, lw=0.6)
    eje.set_axisbelow(True)

    figura.tight_layout()
    destino = SALIDA / "comparativa-algoritmos.png"
    figura.savefig(destino, bbox_inches="tight")
    plt.close(figura)
    return destino


def figura_episodios(plt) -> Path:
    """Episodios independientes en el entrenamiento de cada pliegue, contra CA-6.

    Es la figura que explica por que la sequia no se modela: no falla por poco,
    falla en los cinco pliegues, y el umbral se fijo antes de mirar el dato.
    """
    filas = _leer_csv("episodios-por-pliegue.csv")
    orden = ["lluvia_intensa", "sequia", "incendio"]
    colores = {"lluvia_intensa": AZUL, "sequia": ARENA, "incendio": GRIS}

    figura, eje = plt.subplots(figsize=(6.4, 3.0))
    ancho = 0.26
    umbral = None
    for j, evento in enumerate(orden):
        fila = next(f for f in filas if f["evento"] == evento)
        umbral = int(fila["umbral_minimo_por_pliegue"])
        valores = [int(fila[f"pliegue_{i}"]) for i in range(1, 6)]
        xs = [i + (j - 1) * ancho for i in range(5)]
        eje.bar(xs, valores, ancho, color=colores[evento], label=ROTULO[evento])
        for x, v in zip(xs, valores, strict=True):
            # Escala logaritmica: el desplazamiento del rotulo es multiplicativo.
            eje.text(x, v * 1.12, str(v), ha="center", fontsize=7, color=TINTA)

    # El umbral va a la leyenda y no como texto sobre la linea: en escala
    # logaritmica cualquier rotulo pegado a la linea choca con las barras.
    eje.axhline(
        umbral,
        color=TINTA,
        lw=0.9,
        ls="--",
        label=f"mínimo que exige el criterio: {umbral} por pliegue",
    )
    eje.set_xticks(range(5))
    eje.set_xticklabels([f"Pliegue {i}" for i in range(1, 6)])
    eje.set_ylabel("Episodios en el entrenamiento")
    eje.set_yscale("log")
    eje.set_ylim(1, 400)
    eje.legend(frameon=False, fontsize=7.5, loc="upper left", ncol=2)
    eje.set_title(
        "Episodios a nivel cantón por pliegue de entrenamiento (escala logarítmica)",
        fontsize=10,
        loc="left",
    )
    eje.grid(axis="y", color=GRIS, alpha=0.25, lw=0.6, which="both")
    eje.set_axisbelow(True)

    figura.tight_layout()
    destino = SALIDA / "episodios-por-pliegue.png"
    figura.savefig(destino, bbox_inches="tight")
    plt.close(figura)
    return destino


TABULADAS = (figura_comparativa, figura_episodios)


def main() -> int:
    import argparse

    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument(
        "--tabuladas",
        action="store_true",
        help="solo las figuras que salen de docs/figuras/datos/, sin el conjunto etiquetado",
    )
    argumentos = analizador.parse_args()

    SALIDA.mkdir(parents=True, exist_ok=True)
    plt = _matplotlib()

    print("\nFiguras de resultados\n")
    for fabrica in TABULADAS:
        destino = fabrica(plt)
        print(f"  {destino.relative_to(RAIZ)}   (desde docs/figuras/datos/)")

    if argumentos.tabuladas:
        print()
        return 0

    etiquetas = RAIZ / "datos" / "procesados" / "etiquetas.csv"
    if not etiquetas.exists():
        print(f"\nNo existe {etiquetas}.\n")
        print("Las demas figuras salen de la medicion, no de numeros escritos a mano.")
        print("Se generan con la base levantada:\n")
        print("    python -m backend.modelado.generar_etiquetas\n")
        print("O solo las tabuladas:  python docs/herramientas/generar_figuras.py --tabuladas\n")
        return 1

    for fabrica in (figura_nate, figura_lineas_base, figura_contraste, figura_cobertura):
        destino = fabrica(plt)
        print(f"  {destino.relative_to(RAIZ)}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
