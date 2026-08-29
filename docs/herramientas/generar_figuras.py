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

Las tres se dibujan **desde la medicion**, no desde numeros escritos a mano. Si
el dato cambia, la figura cambia. Es el mismo criterio que el resto del proyecto
aplica a la matriz de trazabilidad y a las cifras de la documentacion.

Uso:
    python docs/herramientas/generar_figuras.py
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


def main() -> int:
    etiquetas = RAIZ / "datos" / "procesados" / "etiquetas.csv"
    if not etiquetas.exists():
        print(f"\nNo existe {etiquetas}.\n")
        print("Las figuras salen de la medicion, no de numeros escritos a mano.")
        print("Se genera con la base levantada:\n")
        print("    python -m backend.modelado.generar_etiquetas\n")
        return 1

    SALIDA.mkdir(parents=True, exist_ok=True)
    plt = _matplotlib()

    print("\nFiguras de resultados\n")
    for fabrica in (figura_lineas_base, figura_contraste, figura_cobertura):
        destino = fabrica(plt)
        print(f"  {destino.relative_to(RAIZ)}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
