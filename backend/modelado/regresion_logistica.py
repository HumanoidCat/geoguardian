"""Regresion Logistica dentro del arnes de H3.6. Historia H3.3.

===========================================================================
POR QUE ESTE ES EL PRIMER ALGORITMO, Y POR QUE ES REGRESION LOGISTICA
===========================================================================

No porque se espere que gane. Se espera que **no** gane contra un bosque o un
XGBoost si hay estructura no lineal, y eso es exactamente lo que se quiere saber.

Es el primero porque es el mas simple que produce probabilidades calibrables y
coeficientes legibles: si la Regresion Logistica ya supera la linea base
climatologica, el proyecto tiene una respuesta con un modelo que se puede
explicar en una frase. Si no la supera, **el problema no esta en el algoritmo**
y agregarle capacidad a la siguiente historia no lo va a arreglar.

===========================================================================
CA-6 DE H3.2 SE CUMPLE POR CONSTRUCCION, NO POR CUIDADO
===========================================================================

CA-6 dice: «ninguna caracteristica puede ajustarse con dato fuera de su pliegue
de entrenamiento». El estandarizador se ajusta **dentro de `ajustar()`**, y el
arnes de H3.6 llama a `ajustar()` con el pliegue de entrenamiento y a nada mas.

No hay forma de que este estimador vea el pliegue de prueba al normalizar, porque
**nunca recibe el pliegue de prueba en `ajustar()`**. La alternativa -normalizar
la matriz entera una vez, antes de partir- seria mas comoda, mas rapida, y
filtraria el futuro.

Los estadisticos que este modulo ajusta, clasificados como CA-6 exige:

    media y desviacion de cada columna    CARACTERISTICA -> dentro del pliegue
    coeficientes del modelo               CARACTERISTICA -> dentro del pliegue

Este modulo **no ajusta ningun estadistico de etiqueta**. Los P95/P99 y la
normal del SPI son de H3.0 y viven fuera de aca.

===========================================================================
LOS NULOS NO SE IMPUTAN. LA FILA NO SE PREDICE
===========================================================================

`LogisticRegression` no acepta NaN, asi que hay que decidir algo. Las opciones
eran imputar -media, mediana, cero- o no predecir.

**Se elige no predecir**, y devolver `None` para esa fila. Tres razones:

  1. **D-07.** Rellenar con la media convierte «no se midio» en «llovio lo
     normal», que es una afirmacion que nadie hizo.
  2. **El arnes ya sabe que hacer con `None`.** Su contrato dice «no se evalua y
     se cuenta aparte». Imputar seria fabricar una prediccion evaluable a partir
     de una fila que no lo es, y eso mueve las metricas sin que nadie lo vea.
  3. **Imputar sesga hacia el modelo.** Una linea base que devuelve `None` en
     esas filas y un algoritmo que las imputa no se estan comparando sobre el
     mismo conjunto, y la tabla de H3.6 dejaria de significar lo que dice.

La consecuencia se reporta: `filas_sin_prediccion` dice cuantas fueron. Si son
muchas, el problema es de las caracteristicas y no del algoritmo.

===========================================================================
EL DESBALANCE SE DECLARA, NO SE ESCONDE
===========================================================================

H3.0 midio las clases sobre 99 296 filas reales: lluvia 3,22 % en ALTO, sequia
7,34 %, incendio 0,87 %. Con esa proporcion, un modelo que prediga siempre BAJO
acierta el 99 % de las veces y tiene un F1-macro pesimo -que es la razon de que
D-10 eligiera F1-macro y no exactitud-.

Se usa `class_weight="balanced"`. **Es una decision, no un valor por omision**:
pesa cada clase por el inverso de su frecuencia, lo que sube la exhaustividad de
la clase minoritaria y baja su precision. Para este problema el error caro es no
avisar de un evento, asi que la direccion es la que se quiere; pero cambia los
numeros y por eso queda escrito aca y en la evidencia.

Uso:
    from backend.modelado.regresion_logistica import RegresionLogistica
    python -m backend.modelado.regresion_logistica --evento sequia
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from contratos.enums import NivelRiesgo

from .comparar import Observacion

#: Semilla fija. `lbfgs` es determinista, pero se declara igual: un estimador que
#: no da lo mismo dos veces no se puede comparar contra otro, y la tabla de H3.6
#: existe para comparar.
SEMILLA = 20260901

#: Tope de iteraciones. El valor por omision de sklearn es 100 y con datos
#: estandarizados y 13 columnas converge muy antes; se sube para que un caso
#: raro no salga con `ConvergenceWarning` y metricas silenciosamente peores.
MAXIMO_ITERACIONES = 1000


@dataclass
class RegresionLogistica:
    """Estimador del contrato de H3.6, con normalizacion dentro del pliegue."""

    nombre: str = "regresion_logistica"
    balancear: bool = True

    #: Se llenan en `ajustar()`. Antes de eso el estimador no predice.
    _columnas: list[str] = field(default_factory=list, init=False)
    _escalador: StandardScaler | None = field(default=None, init=False)
    _modelo: LogisticRegression | None = field(default=None, init=False)
    _filas_sin_prediccion: int = field(default=0, init=False)
    _filas_descartadas_al_ajustar: int = field(default=0, init=False)

    # ----------------------------------------------------------------- #
    # Ajuste                                                             #
    # ----------------------------------------------------------------- #
    def ajustar(
        self, observaciones: list[Observacion], etiquetas: list[NivelRiesgo]
    ) -> RegresionLogistica:
        if len(observaciones) != len(etiquetas):
            raise ValueError(
                f"{len(observaciones)} observaciones y {len(etiquetas)} etiquetas: "
                "no se pueden alinear"
            )
        if not observaciones:
            raise ValueError("no se puede ajustar sin observaciones")

        # ORDEN ESTABLE Y EXPLICITO.
        #
        # `dict` conserva el orden de insercion, pero el orden de insercion
        # depende de como venga la primera observacion. Se ordena alfabeticamente
        # para que dos corridas con las mismas columnas en distinto orden den el
        # MISMO modelo. Sin esto, los coeficientes cambian de sitio entre
        # corridas y la interpretacion del modelo deja de ser reproducible.
        self._columnas = sorted({c for o in observaciones for c in o.caracteristicas})
        if not self._columnas:
            raise ValueError(
                "las observaciones no traen caracteristicas. H2.5 las produce; "
                "sin ellas este estimador no tiene entrada y la linea base de "
                "H3.1 ya cubre el caso de predecir solo con el calendario"
            )

        filas, objetivo = [], []
        for observacion, etiqueta in zip(observaciones, etiquetas, strict=True):
            fila = self._fila(observacion)
            if fila is None:
                continue
            filas.append(fila)
            objetivo.append(etiqueta.value)

        self._filas_descartadas_al_ajustar = len(observaciones) - len(filas)
        if not filas:
            raise ValueError(
                "ninguna observacion tiene todas sus caracteristicas. "
                "No se imputa: ver la cabecera de este modulo"
            )
        if len(set(objetivo)) < 2:
            raise ValueError(
                f"el pliegue de entrenamiento tiene una sola clase ({objetivo[0]}). "
                "No hay nada que aprender, y un modelo de una clase no es "
                "comparable con la linea base"
            )

        X = np.asarray(filas, dtype=float)
        self._escalador = StandardScaler().fit(X)  # CA-6: dentro del pliegue
        self._modelo = LogisticRegression(
            max_iter=MAXIMO_ITERACIONES,
            class_weight="balanced" if self.balancear else None,
            random_state=SEMILLA,
        ).fit(self._escalador.transform(X), objetivo)
        return self

    # ----------------------------------------------------------------- #
    # Prediccion                                                         #
    # ----------------------------------------------------------------- #
    def predecir(self, observaciones: list[Observacion]) -> list[NivelRiesgo | None]:
        if self._modelo is None or self._escalador is None:
            raise ValueError("hay que llamar a ajustar() antes de predecir()")

        salida: list[NivelRiesgo | None] = [None] * len(observaciones)
        indices, filas = [], []
        for i, observacion in enumerate(observaciones):
            fila = self._fila(observacion)
            if fila is not None:
                indices.append(i)
                filas.append(fila)

        self._filas_sin_prediccion = len(observaciones) - len(filas)
        if filas:
            X = self._escalador.transform(np.asarray(filas, dtype=float))
            for i, etiqueta in zip(indices, self._modelo.predict(X), strict=True):
                salida[i] = NivelRiesgo(etiqueta)
        return salida

    # ----------------------------------------------------------------- #
    def _fila(self, observacion: Observacion) -> list[float] | None:
        """Los valores en el orden de `_columnas`, o None si falta alguno.

        **Se indexa por nombre y no por posicion.** Si una observacion trae las
        caracteristicas en otro orden, o trae una de mas, esto sigue siendo
        correcto. Confiar en el orden es el defecto que alinea mal las columnas
        y produce un modelo que entrena sobre `acum3` creyendo que es `media30`:
        no levanta ninguna excepcion y da metricas plausibles.
        """
        valores = []
        for columna in self._columnas:
            valor = observacion.caracteristicas.get(columna)
            if valor is None:
                return None
            valores.append(float(valor))
        return valores

    # ----------------------------------------------------------------- #
    @property
    def filas_sin_prediccion(self) -> int:
        """Cuantas filas quedaron en `None` en la ultima llamada a `predecir`."""
        return self._filas_sin_prediccion

    @property
    def filas_descartadas_al_ajustar(self) -> int:
        return self._filas_descartadas_al_ajustar

    @property
    def coeficientes(self) -> dict[str, dict[str, float]]:
        """Coeficiente por clase y por columna, para leer el modelo.

        Estan en la escala **estandarizada**, asi que se pueden comparar entre
        si: cada uno dice cuanto empuja una desviacion estandar de esa variable.
        En la escala original no serian comparables -milimetros contra dias- y
        alguien los ordenaria por magnitud sin darse cuenta.

        CUIDADO CON EL SIGNO EN EL CASO BINARIO
        ---------------------------------------
        Con dos clases, `sklearn` devuelve **una sola fila de coeficientes**, la
        de `classes_[1]`. Y `classes_` viene **ordenada alfabeticamente**, no por
        severidad:

            'alto' < 'bajo' < 'medio'

        Asi que en un evento binario -incendio, por **SC-05**- la clase positiva
        del modelo es **`bajo`**, y un coeficiente positivo empuja hacia **menos**
        riesgo. Quien lea «coeficiente positivo» como «empuja hacia alto» va a
        entender el modelo exactamente al reves.

        Por eso este diccionario se devuelve **rotulado con el nombre real de la
        clase** en vez de con una etiqueta fija: para que el signo no se pueda
        interpretar sin mirar de que clase es. Lo comprueba
        `test_dos_clases_como_el_incendio`.
        """
        if self._modelo is None:
            raise ValueError("hay que llamar a ajustar() antes de leer coeficientes")
        clases = [str(c) for c in self._modelo.classes_]
        matriz = np.atleast_2d(self._modelo.coef_)
        if len(clases) == 2 and matriz.shape[0] == 1:
            clases = clases[1:]
        return {
            clase: dict(zip(self._columnas, fila.tolist(), strict=True))
            for clase, fila in zip(clases, matriz, strict=True)
        }


def main() -> int:
    p = argparse.ArgumentParser(description="Regresion Logistica de H3.3.")
    p.add_argument("--evento", default="sequia", help="lluvia_intensa, sequia o incendio")
    p.parse_args()
    print(
        "\nEste modulo es un estimador del arnes de H3.6, no un guion suelto.\n"
        "La tabla comparativa, con las lineas base y la particion de H3.2, sale de:\n\n"
        "    python -m backend.modelado.comparar\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
