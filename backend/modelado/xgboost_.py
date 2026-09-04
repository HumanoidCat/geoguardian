"""XGBoost dentro del arnes de H3.6. Historia H3.5.

El archivo se llama `xgboost_.py`, con guion bajo, porque `xgboost.py` a secas
haria que `import xgboost` dentro de este paquete se resolviera a si mismo y no
a la libreria. Es el mismo choque de nombres que Python documenta para
`random.py` y `math.py`.

===========================================================================
QUE SE ESPERA DE EL, DESPUES DE H3.4
===========================================================================

H3.4 dejo medido por que el bosque sin ajustar empata con la trivial en
incendio: arboles sin poda sobre 0,87 % de positivos terminan en hojas puras
que memorizan cada ALTO de entrenamiento, y el peso de clase no actua en hojas
puras. XGBoost es la contraprueba natural: arboles **poco profundos**
(`max_depth = 6` por omision), regularizados, ajustados uno sobre el residuo
del anterior. Si tampoco supera la linea base climatologica, el problema no
esta en la familia de algoritmos sino en la senal de las caracteristicas, y
H3.6 puede decirlo con los tres de D-09 sobre la mesa.

===========================================================================
SABE MANEJAR NULOS, Y AQUI NO SE LE PERMITE
===========================================================================

XGBoost aprende, para cada particion, hacia que rama va un valor ausente. Es
una capacidad real y util. Pero usarla aqui haria que este estimador viera
filas que la regresion y el bosque descartan, y la tabla de H3.6 dejaria de
comparar tres algoritmos sobre el mismo conjunto: compararia dos algoritmos
sobre un conjunto y uno sobre otro mas grande. Se mantiene **D-07 tal como en
H3.3 y H3.4**: la fila incompleta no se predice y se cuenta. Lo comprueba
`verificar_h35`, criterios 7 y 12. Aprovechar la rama de ausentes queda anotado
para H3.8, donde ya no se compara contra nadie.

===========================================================================
LAS ETIQUETAS VIAJAN COMO ENTEROS
===========================================================================

XGBoost exige clases `0..K-1`. Se traduce de `NivelRiesgo` al entero al ajustar
y de vuelta al predecir, con la lista de clases **ordenada y guardada** en el
estimador. Las probabilidades salen rotuladas por clase, como en H3.4, para
que nadie lea la columna 1 como «alto» en un evento de dos clases donde
`sorted` la puso en la 0.

===========================================================================
EL DESBALANCE SE TRATA CON PESOS POR FILA
===========================================================================

`class_weight="balanced"` no existe en XGBoost. `scale_pos_weight` existe, pero
solo para el caso binario, y lluvia intensa tiene tres clases. Se calcula el
equivalente exacto a `balanced` como peso por fila: cada fila pesa
`n / (K * n_clase)`, y se pasa a `fit(sample_weight=...)`. Sirve para dos y
para tres clases con la misma formula.

**A diferencia del bosque, aqui las hojas no son puras**: profundidad 6 y
regularizacion por omision dejan hojas mezcladas, asi que el peso tiene sobre
que actuar. Se comprueba en `test_balancear_cambia_el_resultado...` con los
mismos cajones repetidos de H3.4.

===========================================================================
HIPERPARAMETROS: LOS DE FABRICA
===========================================================================

Ajustarlos es **H3.8**. Se usan los valores por omision de la libreria
(`n_estimators = 100`, `max_depth = 6`, `learning_rate = 0.3`) salvo lo que hace
falta para que el resultado sea comparable y repetible:

    tree_method   hist          el unico determinista con n_jobs = 1
    n_jobs        1             lo que H3.4 midio en el bosque aplica igual:
                                con varios hilos el orden de las sumas cambia
    random_state  SEMILLA       la misma de H3.3 y H3.4

Uso:
    from backend.modelado.xgboost_ import XGBoostEstimador
    python -m backend.modelado.comparar
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

import numpy as np
from xgboost import XGBClassifier

from contratos.enums import NivelRiesgo

from .comparar import Observacion

#: La misma semilla de H3.3 y H3.4.
SEMILLA = 20260901


@dataclass
class XGBoostEstimador:
    """Estimador del contrato de H3.6. Sin normalizacion: no la necesita."""

    nombre: str = "xgboost"
    balancear: bool = True

    _columnas: list[str] = field(default_factory=list, init=False)
    _clases: list[NivelRiesgo] = field(default_factory=list, init=False)
    _modelo: XGBClassifier | None = field(default=None, init=False)
    _filas_sin_prediccion: int = field(default=0, init=False)
    _filas_descartadas_al_ajustar: int = field(default=0, init=False)

    # ----------------------------------------------------------------- #
    # Ajuste                                                             #
    # ----------------------------------------------------------------- #
    def ajustar(
        self, observaciones: list[Observacion], etiquetas: list[NivelRiesgo]
    ) -> XGBoostEstimador:
        if len(observaciones) != len(etiquetas):
            raise ValueError(
                f"{len(observaciones)} observaciones y {len(etiquetas)} etiquetas: "
                "no se pueden alinear"
            )
        if not observaciones:
            raise ValueError("no se puede ajustar sin observaciones")

        self._columnas = sorted({c for o in observaciones for c in o.caracteristicas})
        if not self._columnas:
            raise ValueError(
                "las observaciones no traen caracteristicas. H3.3 las produce; "
                "sin ellas este estimador no tiene entrada y la linea base de "
                "H3.1 ya cubre el caso de predecir solo con el calendario"
            )

        filas, objetivo = [], []
        for observacion, etiqueta in zip(observaciones, etiquetas, strict=True):
            fila = self._fila(observacion)
            if fila is None:
                continue
            filas.append(fila)
            objetivo.append(etiqueta)

        self._filas_descartadas_al_ajustar = len(observaciones) - len(filas)
        if not filas:
            raise ValueError(
                "ninguna observacion tiene todas sus caracteristicas. "
                "No se imputa ni se usa la rama de ausentes: ver la cabecera"
            )
        self._clases = sorted(set(objetivo), key=lambda n: n.value)
        if len(self._clases) < 2:
            raise ValueError(
                f"el pliegue de entrenamiento tiene una sola clase ({objetivo[0].value}). "
                "No hay nada que aprender, y un modelo de una clase no es "
                "comparable con la linea base"
            )

        indice = {clase: i for i, clase in enumerate(self._clases)}
        y = np.asarray([indice[e] for e in objetivo], dtype=int)
        X = np.asarray(filas, dtype=float)

        # El equivalente exacto de class_weight="balanced": n / (K * n_clase).
        pesos = None
        if self.balancear:
            conteo = np.bincount(y, minlength=len(self._clases))
            pesos = (len(y) / (len(self._clases) * conteo))[y]

        self._modelo = XGBClassifier(
            tree_method="hist",
            n_jobs=1,  # ver la cabecera: con varios hilos no es reproducible
            random_state=SEMILLA,
        ).fit(X, y, sample_weight=pesos)
        return self

    # ----------------------------------------------------------------- #
    # Prediccion                                                         #
    # ----------------------------------------------------------------- #
    def predecir(self, observaciones: list[Observacion]) -> list[NivelRiesgo | None]:
        if self._modelo is None:
            raise ValueError("hay que llamar a ajustar() antes de predecir()")

        salida: list[NivelRiesgo | None] = [None] * len(observaciones)
        indices, filas = self._completas(observaciones)
        if filas:
            X = np.asarray(filas, dtype=float)
            for i, k in zip(indices, self._modelo.predict(X), strict=True):
                salida[i] = self._clases[int(k)]
        return salida

    def probabilidades(
        self, observaciones: list[Observacion]
    ) -> list[dict[NivelRiesgo, float] | None]:
        """Una distribucion por fila, rotulada por clase; `None` donde no se predice."""
        if self._modelo is None:
            raise ValueError("hay que llamar a ajustar() antes de probabilidades()")

        salida: list[dict[NivelRiesgo, float] | None] = [None] * len(observaciones)
        indices, filas = self._completas(observaciones)
        if filas:
            matriz = self._modelo.predict_proba(np.asarray(filas, dtype=float))
            for i, fila in zip(indices, matriz, strict=True):
                salida[i] = dict(zip(self._clases, fila.tolist(), strict=True))
        return salida

    # ----------------------------------------------------------------- #
    def _completas(self, observaciones: list[Observacion]) -> tuple[list[int], list[list[float]]]:
        """Un solo lugar para decidir que fila se predice, como en H3.4."""
        indices, filas = [], []
        for i, observacion in enumerate(observaciones):
            fila = self._fila(observacion)
            if fila is not None:
                indices.append(i)
                filas.append(fila)
        self._filas_sin_prediccion = len(observaciones) - len(filas)
        return indices, filas

    def _fila(self, observacion: Observacion) -> list[float] | None:
        """Los valores en el orden de `_columnas`, o None si falta alguno.

        Aca es donde D-07 se sostiene contra la rama de ausentes: XGBoost
        aceptaria un NaN sin quejarse, y por eso la fila incompleta se corta
        ANTES de que la libreria la vea.
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
    def necesita_caracteristicas(self) -> bool:
        return True

    @property
    def filas_sin_prediccion(self) -> int:
        return self._filas_sin_prediccion

    @property
    def filas_descartadas_al_ajustar(self) -> int:
        return self._filas_descartadas_al_ajustar

    @property
    def importancias(self) -> dict[str, float]:
        """Ganancia total por columna, normalizada a suma 1, por nombre.

        XGBoost trae varias definiciones de importancia; se usa la ganancia
        (`gain`) porque es la que responde «cuanto mejoro el modelo al partir
        por esta columna», y no cuantas veces la uso. Una columna que el modelo
        nunca uso vale 0 y aparece igual: una importancia ausente seria
        indistinguible de una columna que no existia.
        """
        if self._modelo is None:
            raise ValueError("hay que llamar a ajustar() antes de leer importancias")
        ganancia = self._modelo.get_booster().get_score(importance_type="gain")
        # get_score rotula las columnas f0, f1, ... en el orden de la matriz.
        crudo = [float(ganancia.get(f"f{i}", 0.0)) for i in range(len(self._columnas))]
        total = sum(crudo)
        return dict(zip(self._columnas, [v / total if total else 0.0 for v in crudo], strict=True))


def main() -> int:
    print(
        "\nEste modulo es un estimador del arnes de H3.6, no un guion suelto.\n"
        "La tabla comparativa, con las lineas base y la particion de H3.2, sale de:\n\n"
        "    python -m backend.modelado.comparar\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
