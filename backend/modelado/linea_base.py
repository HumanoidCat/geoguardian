"""Lineas base climatologica y trivial. Historia H3.1.

QUE PRODUCE

El **piso** contra el que se mide todo lo demas. La pregunta del charter no es
«el modelo acierta» sino **«acierta mas que saber en que mes estamos»**, y sin
esta historia cualquier F1-macro de H3.3 en adelante es un numero sin referencia.

Es lo que hace que **H1 sea refutable**, que es lo que el charter promete.

SON DOS, Y LAS DOS SE REPORTAN

    Trivial          siempre la clase mayoritaria del entrenamiento
    Climatologica    la clase mas frecuente de ese distrito en ese mes

La trivial no es un chiste. Con incendio al 1,23 % de las filas observadas,
«siempre BAJO» acierta el 98,8 % de las veces: **su F1-macro no es cero** y es el
numero que de verdad hay que superar. Si la climatologica no le gana, eso ya es un
resultado -quiere decir que el mes no aporta informacion para ese evento- y hay
que decirlo en vez de esconderlo detras de la comparacion siguiente.

MIRAN EL CALENDARIO Y NADA MAS

Entrada: **distrito y fecha**. Ni precipitacion reciente, ni acumulados, ni focos
previos. En cuanto una linea base usa una variable meteorologica deja de ser linea
base y pasa a ser un modelo, y el contraste de **D-10** compararia dos modelos en
vez de comparar un modelo contra el almanaque.

La firma es el criterio: `predecir(codigo_distrito, fecha)`.

SE AJUSTAN SOLO CON SU PLIEGUE

Es el error clasico y es facil de cometer sin notarlo: se calcula la frecuencia
por distrito-mes **sobre toda la serie** porque parece inofensivo -«si es solo el
promedio historico»- y esa frecuencia ya vio el conjunto de prueba.

**Una linea base con fuga es peor que una con error**: se vuelve dificil de
superar, y entonces un modelo honesto parece malo.

LA AUSENCIA NO SE RELLENA EN SILENCIO

Un distrito-mes sin dato de entrenamiento devuelve `None`, y se cuenta aparte. Es
**D-07** y **D-22**, lo mismo que H3.0 aplico a las etiquetas.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from contratos.enums import NivelRiesgo  # noqa: E402

#: Los tres distritos con senal de incendio. **D-25**. Una linea base de incendio
#: para Arenal -un solo foco en veinticuatro anios- no mide nada.
DISTRITOS_CON_INCENDIO = ("50804", "50805", "50806")


@dataclass
class LineaBaseTrivial:
    """Siempre la clase mayoritaria del entrenamiento. **El piso absoluto.**

    No mira el distrito ni la fecha: es deliberado. Existe para responder «cuanto
    saca alguien que no sabe nada», y con clases minoritarias del 1 % la respuesta
    no es cero.
    """

    clase: NivelRiesgo | None = None

    def ajustar(self, entrenamiento: list[tuple[str, date, NivelRiesgo]]) -> LineaBaseTrivial:
        cuenta = Counter(nivel for _, _, nivel in entrenamiento)
        self.clase = cuenta.most_common(1)[0][0] if cuenta else None
        return self

    def predecir(self, codigo_distrito: str, fecha: date) -> NivelRiesgo | None:
        # Los dos argumentos se ignoran a proposito, y la firma se conserva para
        # que sea intercambiable con la climatologica y con cualquier modelo.
        del codigo_distrito, fecha
        return self.clase


@dataclass
class LineaBaseClimatologica:
    """La clase con mas **realce** en ese distrito y ese mes calendario.

    Es el almanaque: «en Santa Rosa, en marzo, que es lo que mas se sale de lo
    normal». Nada de lo que haya ocurrido los ultimos dias entra.

    POR QUE REALCE Y NO LA CLASE MAS FRECUENTE

    La primera version predecia **la clase mas frecuente** de cada distrito-mes,
    que es la definicion de manual. Corriendola sobre el dato real dio
    exactamente el mismo F1-macro que la trivial en los tres eventos, hasta el
    tercer decimal y en los cinco pliegues. No era casualidad:

        lluvia_intensa   clase modal por distrito-mes: {bajo: 96}  (96 celdas)
        incendio         clase modal por distrito-mes: {bajo: 96}  (96 celdas)

    **Con una clase minoritaria del 1 % al 7 %, BAJO es modal en las noventa y
    seis celdas.** La climatologica modal degenera en la trivial por
    construccion, y una linea base que no puede diferenciarse del piso absoluto
    no sirve como piso informado: haria pasar por «el mes no informa» a un evento
    donde el mes si informa.

    Asi que se compara cada clase contra **su propia tasa base**:

        realce(clase) = tasa en este distrito-mes / tasa en todo el entrenamiento

    Se predice la clase de mayor realce. Un mes donde ALTO ocurre tres veces mas
    que el promedio predice ALTO, aunque siga siendo minoritario ahi.

    **Sigue mirando solo el calendario**, que es CA-1: el realce se calcula con
    dato de entrenamiento, no con nada de la fila que se predice.
    """

    #: (codigo_distrito, mes) -> clase de mayor realce en el entrenamiento
    tabla: dict[tuple[str, int], NivelRiesgo] = field(default_factory=dict)
    #: cuantas filas de entrenamiento respaldan cada celda, para poder auditarla
    respaldo: dict[tuple[str, int], int] = field(default_factory=dict)
    #: la tasa de cada clase en todo el entrenamiento, que es el denominador
    tasa_base: dict[NivelRiesgo, float] = field(default_factory=dict)

    def ajustar(self, entrenamiento: list[tuple[str, date, NivelRiesgo]]) -> LineaBaseClimatologica:
        por_celda: dict[tuple[str, int], Counter] = defaultdict(Counter)
        global_: Counter = Counter()
        for codigo, fecha, nivel in entrenamiento:
            por_celda[(codigo, fecha.month)][nivel] += 1
            global_[nivel] += 1

        total = sum(global_.values())
        self.tasa_base = {c: n / total for c, n in global_.items()} if total else {}
        self.tabla = {}
        self.respaldo = {}

        for celda, cuenta in por_celda.items():
            filas = sum(cuenta.values())

            def realce(clase: NivelRiesgo, cuenta: Counter = cuenta, filas: int = filas) -> float:
                base = self.tasa_base.get(clase, 0.0)
                return (cuenta[clase] / filas) / base if base else 0.0

            # El desempate va por el nombre de la clase y no por el orden en que
            # llego el dato: CA-3 exige que dos ajustes iguales den lo mismo, y un
            # empate resuelto por orden de insercion lo rompe.
            self.tabla[celda] = max(cuenta, key=lambda c: (realce(c), c.value))
            self.respaldo[celda] = filas
        return self

    def predecir(self, codigo_distrito: str, fecha: date) -> NivelRiesgo | None:
        """None si ese distrito-mes no tuvo dato de entrenamiento. **No se rellena.**

        Sustituirlo por el promedio del canton sin decirlo seria inventar un dato
        y esconder que el pliegue no alcanzaba. Es **D-07**.
        """
        return self.tabla.get((codigo_distrito, fecha.month))


# --------------------------------------------------------------------------- #
# La metrica                                                                    #
# --------------------------------------------------------------------------- #


def f1_macro(
    verdad: list[NivelRiesgo | None], prediccion: list[NivelRiesgo | None]
) -> tuple[float, dict[NivelRiesgo, float], int]:
    """F1-macro de **D-10**, y el F1 por clase, y cuantas filas se pudieron usar.

    Se implementa aca en vez de llamar a scikit-learn por una razon: **hay que
    decidir que hacer con las filas sin prediccion**, y ninguna implementacion de
    biblioteca toma esa decision por uno.

    La decision: **una fila sin verdad o sin prediccion no se evalua, y se cuenta
    aparte.** Contarla como fallo castigaria a la linea base por ser honesta -por
    devolver None en vez de inventar- y contarla como acierto seria peor. El
    tercer valor del retorno es cuantas quedaron, y **hay que reportarlo**.

    El macro promedia el F1 de **todas las clases presentes en la verdad**,
    incluidas las que el modelo nunca predice. Ese es el punto de la metrica con
    clases desbalanceadas: una clase minoritaria que nunca se predice aporta F1
    cero y baja el promedio.
    """
    pares = [
        (v, p) for v, p in zip(verdad, prediccion, strict=True) if v is not None and p is not None
    ]
    evaluadas = len(pares)
    if not pares:
        return 0.0, {}, 0

    clases = {v for v, _ in pares}
    por_clase: dict[NivelRiesgo, float] = {}
    for c in clases:
        vp = sum(1 for v, p in pares if v is c and p is c)
        fp = sum(1 for v, p in pares if v is not c and p is c)
        fn = sum(1 for v, p in pares if v is c and p is not c)
        precision = vp / (vp + fp) if vp + fp else 0.0
        cobertura = vp / (vp + fn) if vp + fn else 0.0
        por_clase[c] = (
            2 * precision * cobertura / (precision + cobertura) if precision + cobertura else 0.0
        )

    return sum(por_clase.values()) / len(por_clase), por_clase, evaluadas
