"""Comprueba los criterios de aceptacion de H3.1, la linea base.

Criterios en `docs/evidencias/objetivos/H3.1-criterios-aceptacion.md`.

CORRE SIN BASE DE DATOS

Todo lo de aca son propiedades de la **linea base**, no del dato cargado. Los
numeros contra el dato real -y la prediccion falsable sobre la sequia- los mide
`evaluar_linea_base.py`.

CONTRASTA `f1_macro` CONTRA SCIKIT-LEARN

La metrica se implemento a mano porque hay que decidir que hacer con las filas sin
prediccion, y ninguna biblioteca decide eso por uno. **Pero en los casos donde no
hay ausencias, tiene que dar exactamente lo mismo que sklearn.** Si difiere, la
implementacion propia esta mal, no sklearn.

Uso:
    python -m backend.modelado.verificar_h31

Sale con codigo 1 si algun criterio se rompe.
"""

from __future__ import annotations

import inspect
import random
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado.linea_base import (  # noqa: E402
    DISTRITOS_CON_INCENDIO,
    LineaBaseClimatologica,
    LineaBaseTrivial,
    f1_macro,
)
from backend.modelado.particion import (  # noqa: E402
    filas_de_entrenamiento,
    filas_de_prueba,
    particionar,
)
from contratos.enums import NivelRiesgo, TipoEvento  # noqa: E402

fallos: list[str] = []


def comprobar(descripcion: str, condicion: bool, detalle: str = "") -> None:
    print(f"  {'OK  ' if condicion else 'FALLO'}  {descripcion}")
    if not condicion:
        fallos.append(descripcion)
        if detalle:
            print(f"        {detalle}")


def serie_estacional(
    codigo: str, desde: date, hasta: date, semilla: int = 3
) -> list[tuple[str, date, NivelRiesgo]]:
    """Filas con estacionalidad fuerte: de enero a abril casi siempre ALTO.

    Sirve para comprobar que la climatologica **puede** capturar un patron
    mensual cuando existe. Si no lo capturara aca, no lo capturaria nunca.
    """
    g = random.Random(semilla)
    salida = []
    dia = desde
    while dia <= hasta:
        seco = dia.month in (1, 2, 3, 4)
        nivel = NivelRiesgo.ALTO if (g.random() < (0.85 if seco else 0.05)) else NivelRiesgo.BAJO
        salida.append((codigo, dia, nivel))
        dia += timedelta(days=1)
    return salida


def main() -> int:
    print("\nCriterios de aceptacion de H3.1\n")

    datos = serie_estacional("50804", date(2001, 1, 1), date(2020, 12, 31))

    # ---------------------------------------------------------------- CA-1 -- #
    print("CA-1, la linea base mira el calendario y nada mas:")

    for nombre, clase in (("trivial", LineaBaseTrivial), ("climatologica", LineaBaseClimatologica)):
        parametros = list(inspect.signature(clase.predecir).parameters)
        comprobar(
            f"{nombre}: predecir recibe solo distrito y fecha",
            parametros == ["self", "codigo_distrito", "fecha"],
            f"recibe {parametros}. Una variable meteorologica la convertiria en "
            "modelo, y el contraste de D-10 compararia dos modelos.",
        )

    fuente = inspect.getsource(LineaBaseClimatologica)
    comprobar(
        "y su codigo no menciona ninguna variable meteorologica",
        not any(p in fuente for p in ("precipitacion", "spi", "acumulado", "foco", "brillo")),
    )

    # ---------------------------------------------------------------- CA-2 -- #
    print("\nCA-2, son dos y las dos funcionan:")

    trivial = LineaBaseTrivial().ajustar(datos)
    clima = LineaBaseClimatologica().ajustar(datos)

    comprobar(
        "la trivial devuelve la clase mayoritaria del entrenamiento",
        trivial.clase is NivelRiesgo.BAJO,
        f"dio {trivial.clase}. En la serie de prueba manda BAJO por 2 a 1.",
    )
    comprobar(
        "y devuelve lo mismo sin importar distrito ni fecha",
        len({trivial.predecir(c, date(2010, m, 1)) for c in ("50801", "50808") for m in (2, 9)})
        == 1,
    )

    comprobar(
        "la climatologica distingue la estacion seca de la lluviosa",
        clima.predecir("50804", date(2015, 3, 1)) is NivelRiesgo.ALTO
        and clima.predecir("50804", date(2015, 9, 1)) is NivelRiesgo.BAJO,
        "si no capturara un patron mensual tan marcado, no lo capturaria nunca",
    )

    # Y la comparacion que CA-2 exige: sobre dato estacional, la climatologica
    # tiene que ganarle a la trivial. Es la unica forma de saber que el aparato
    # de comparacion sirve antes de aplicarlo al dato real.
    verdad = [n for _, _, n in datos]
    macro_t, _, _ = f1_macro(verdad, [trivial.predecir(c, f) for c, f, _ in datos])
    macro_c, _, _ = f1_macro(verdad, [clima.predecir(c, f) for c, f, _ in datos])
    comprobar(
        "sobre dato estacional, la climatologica le gana a la trivial",
        macro_c > macro_t,
        f"trivial {macro_t:.3f}, climatologica {macro_c:.3f}",
    )
    comprobar(
        "y la trivial NO da cero, que es el punto de reportarla",
        macro_t > 0.0,
        f"da {macro_t:.3f}. Con clases del 1 % «siempre BAJO» acierta el 99 %.",
    )

    # ---------------------------------------------------------------- CA-3 -- #
    print("\nCA-3, se ajusta solo con su pliegue, y se comprueba:")

    fechas = [f for _, f, _ in datos]
    pliegue = particionar(TipoEvento.INCENDIO)[1]
    del_pliegue = set(filas_de_entrenamiento(pliegue, fechas))
    solo_pliegue = [fila for fila in datos if fila[1] in del_pliegue]

    honesta = LineaBaseClimatologica().ajustar(solo_pliegue)
    con_fuga = LineaBaseClimatologica().ajustar(datos)

    comprobar(
        "el ajuste usa solo las filas que se le pasan",
        max(f for _, f, _ in solo_pliegue) <= pliegue.entrenamiento[1],
    )
    comprobar(
        "ajustar con el pliegue y con todo NO da la misma tabla de respaldo",
        honesta.respaldo != con_fuga.respaldo,
        "si diera igual, esta comprobacion no distinguiria una linea base honesta "
        "de una con fuga, y CA-3 no protegeria de nada",
    )
    comprobar(
        "la version con fuga se respalda en mas filas, que es como se detecta",
        sum(con_fuga.respaldo.values()) > sum(honesta.respaldo.values()),
    )
    comprobar(
        "dos ajustes con el mismo dato dan la misma tabla",
        LineaBaseClimatologica().ajustar(solo_pliegue).tabla == honesta.tabla,
        "los empates se desempatan por el nombre de la clase, no por el orden "
        "en que llego el dato",
    )

    # ---------------------------------------------------------------- CA-4 -- #
    print("\nCA-4, un distrito-mes sin dato no se rellena en silencio:")

    solo_marzo = [fila for fila in datos if fila[1].month == 3]
    parcial = LineaBaseClimatologica().ajustar(solo_marzo)

    comprobar(
        "marzo se predice porque tuvo entrenamiento",
        parcial.predecir("50804", date(2020, 3, 15)) is not None,
    )
    comprobar(
        "septiembre devuelve None, no la clase del canton",
        parcial.predecir("50804", date(2020, 9, 15)) is None,
        "rellenarlo con el promedio sin decirlo seria inventar un dato y esconder "
        "que el pliegue no alcanzaba. Es D-07.",
    )
    comprobar(
        "un distrito que no estuvo en el entrenamiento tambien devuelve None",
        parcial.predecir("50807", date(2020, 3, 15)) is None,
    )
    comprobar(
        "y la tabla de respaldo permite auditar cuantas filas hay detras",
        parcial.respaldo.get(("50804", 3), 0) > 0,
    )

    # ---------------------------------------------------------------- CA-5 -- #
    print("\nCA-5, se evalua sobre los mismos pliegues que todos los modelos:")

    comprobar(
        "la particion se pide a H3.2, no se deriva aca",
        "particionar" in inspect.getsource(sys.modules[__name__]),
    )
    for p in particionar(TipoEvento.SEQUIA):
        entrena = set(filas_de_entrenamiento(p, fechas))
        prueba = set(filas_de_prueba(p, fechas))
        comprobar(
            f"pliegue {p.indice}: entrenamiento y prueba no se tocan",
            not (entrena & prueba),
        )

    # ---------------------------------------------------------------- CA-6 -- #
    print("\nCA-6, el incendio se evalua solo donde D-25 dice:")

    comprobar(
        "los tres distritos con senal estan declarados",
        DISTRITOS_CON_INCENDIO == ("50804", "50805", "50806"),
    )
    comprobar(
        "y Arenal y Cabeceras quedan fuera",
        "50807" not in DISTRITOS_CON_INCENDIO and "50808" not in DISTRITOS_CON_INCENDIO,
        "una linea base de incendio para un distrito con un foco en 24 anios no mide nada",
    )

    # ---------------------------------------------------------------- CA-7 -- #
    print("\nCA-7, la metrica contrastada contra scikit-learn:")

    from sklearn.metrics import f1_score

    g = random.Random(11)
    niveles = list(NivelRiesgo)
    for caso in range(4):
        v = [g.choice(niveles) for _ in range(400)]
        p = [g.choice(niveles) if g.random() < 0.4 else v[i] for i in range(400)]
        mio, _, n = f1_macro(v, p)
        suyo = f1_score(
            [x.value for x in v], [x.value for x in p], average="macro", zero_division=0
        )
        comprobar(
            f"caso {caso + 1}: coincide con sklearn en las {n} filas evaluables",
            abs(mio - suyo) < 1e-9,
            f"propio {mio:.9f}, sklearn {suyo:.9f}",
        )

    # Y la decision propia, que sklearn no toma: las ausencias.
    v = [NivelRiesgo.ALTO, NivelRiesgo.BAJO, NivelRiesgo.ALTO]
    con_hueco = [NivelRiesgo.ALTO, None, NivelRiesgo.ALTO]
    macro, _, evaluadas = f1_macro(v, con_hueco)
    comprobar(
        "una prediccion ausente no se evalua y se cuenta aparte",
        evaluadas == 2,
        f"evaluo {evaluadas} de 3. Contarla como fallo castigaria a la linea base "
        "por devolver None en vez de inventar.",
    )
    comprobar(
        "y no se castiga: las dos que acerto siguen valiendo",
        macro > 0.0,
    )

    # Prueba negativa: un modelo que nunca predice la clase minoritaria tiene que
    # salir castigado. Es el punto del macro sobre clases desbalanceadas.
    v = [NivelRiesgo.BAJO] * 99 + [NivelRiesgo.ALTO]
    siempre_bajo = [NivelRiesgo.BAJO] * 100
    macro_ciego, por_clase, _ = f1_macro(v, siempre_bajo)
    comprobar(
        "quien nunca predice la clase rara recibe F1 cero en esa clase",
        por_clase.get(NivelRiesgo.ALTO) == 0.0,
    )
    comprobar(
        "y aun asi su macro no es cero, por eso hay que reportar la trivial",
        0.0 < macro_ciego < 0.6,
        f"da {macro_ciego:.3f} acertando el 99 % de las filas. Un modelo que "
        "reporte solo exactitud pareceria excelente.",
    )

    # ----------------------------------------------------------------------- #
    print()
    if fallos:
        print(f"{len(fallos)} criterios fallaron:\n")
        for f in fallos:
            print(f"  - {f}")
        return 1

    print("Los criterios verificables sin base de datos se cumplen.")
    print("Los numeros contra el dato real los mide evaluar_linea_base.py.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
