"""Random Forest dentro del arnes de H3.6. Historia H3.4.

===========================================================================
POR QUE UN BOSQUE, Y QUE SE ESPERA DE EL
===========================================================================

H3.3 puso la Regresion Logistica primero por ser el modelo mas simple que da
probabilidades y coeficientes legibles, y dejo dicho que **si hay estructura no
lineal, no deberia ganar**. El bosque es la primera prueba de esa hipotesis: si
tampoco supera la linea base climatologica, el problema no esta en la capacidad
del algoritmo sino en la senal que traen las caracteristicas, y XGBoost (H3.5)
no lo va a arreglar.

Entra por el mismo contrato que la regresion -`ajustar()` y `predecir()` sobre
`Observacion`- y con el **mismo trato de los nulos**: no se imputa, la fila no
se predice y se cuenta. Sin eso la tabla de H3.6 compararia dos estimadores
sobre conjuntos distintos.

===========================================================================
NO NORMALIZA, Y ESO ES CORRECTO
===========================================================================

Un arbol parte por umbrales sobre cada columna por separado. Multiplicar una
columna por diez mueve el umbral por diez y **no cambia ninguna decision**. Por
eso este modulo no lleva `StandardScaler`, y CA-6 de H3.2 -«ningun estadistico
se ajusta con dato de fuera del pliegue»- se cumple de la forma mas simple: no
hay ningun estadistico que ajustar fuera de `ajustar()`. Lo comprueba
`verificar_h34`, criterio 8, con la invariancia a escala.

===========================================================================
HIPERPARAMETROS: LOS DE FABRICA, SALVO DOS
===========================================================================

Ajustarlos es **H3.8**, y hacerlo aqui contaminaria la comparacion de H3.6: un
modelo ajustado contra dos que no lo estan no es una comparacion. Se declaran
los dos que no son de fabrica:

    n_estimators  200        el valor por omision es 100; se sube porque con
                             incendio al 0,87 % de ALTO, cien arboles con
                             muestreo bootstrap dejan pliegues donde la clase
                             minoritaria casi no aparece, y la varianza entre
                             corridas con distinta semilla se nota en la tabla
    class_weight  balanced   la misma decision de H3.3, por la misma razon:
                             el error caro es no avisar de un evento.
                             **En un bosque pesa menos que en la regresion**:
                             si cada hoja termina pura, el voto es el mismo
                             con o sin pesos. Actua donde las hojas no pueden
                             ser puras, o sea donde muchas filas comparten
                             las mismas caracteristicas con etiquetas
                             distintas -dias con lluvia 0,0 y focos 0 se
                             repiten por miles-. Se midio al escribir la
                             prueba: con valores continuos y separables, con y
                             sin pesos dieron identico; con valores repetidos,
                             no. Ver `test_balancear_cambia_el_resultado...`

`random_state` fijo, porque un estimador que no da lo mismo dos veces no se
puede comparar contra otro. Y **`n_jobs = 1`, a proposito.** La primera version
llevaba `n_jobs = -1` con el argumento de que la semilla fija hace que cada
arbol se construya igual en cualquier proceso, y eso es cierto para el ajuste,
pero no para `predict_proba`: scikit-learn suma las probabilidades de los
arboles desde varios hilos y el orden de la suma cambia entre llamadas, asi que
**el mismo modelo devuelve probabilidades distintas en el ultimo decimal
(2e-16) dos veces seguidas**. Lo encontro el criterio 9 de `verificar_h34`
sobre datos con ruido, y se confirmo aislando `n_jobs`. Una diferencia de 2e-16
no mueve el F1, pero si puede voltear un empate exacto en el voto, y CA-6 de
H3.6 exige que dos corridas den el mismo numero. Cuesta tiempo de calculo y se
paga.

===========================================================================
LO QUE SALE ADEMAS DEL NIVEL
===========================================================================

`importancias`: la reduccion media de impureza por columna, **rotulada por
nombre**. Es lo que H4.1 va a leer. Cuidado con leerla como causalidad: dos
columnas correlacionadas se reparten la importancia de forma arbitraria.

`probabilidades()`: una distribucion por fila, rotulada por clase. La tabla de
H3.6 no la usa -D-10 compara niveles con F1-macro- pero la tuberia hacia
`analitico.riesgo` necesita **P(nivel = alto)** por D-21, y sacarla despues
obligaria a reentrenar.

Uso:
    from backend.modelado.random_forest import BosqueAleatorio
    python -m backend.modelado.comparar
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from contratos.enums import NivelRiesgo

from .comparar import Observacion

#: La misma semilla de H3.3, para que nadie pueda atribuir una diferencia entre
#: los dos estimadores a que se sembraron distinto.
SEMILLA = 20260901

#: Ver la cabecera: es lo unico que no es de fabrica, junto con class_weight.
ARBOLES = 200


@dataclass
class BosqueAleatorio:
    """Estimador del contrato de H3.6. Sin normalizacion: no la necesita."""

    nombre: str = "random_forest"
    balancear: bool = True

    _columnas: list[str] = field(default_factory=list, init=False)
    _modelo: RandomForestClassifier | None = field(default=None, init=False)
    _filas_sin_prediccion: int = field(default=0, init=False)
    _filas_descartadas_al_ajustar: int = field(default=0, init=False)

    # ----------------------------------------------------------------- #
    # Ajuste                                                             #
    # ----------------------------------------------------------------- #
    def ajustar(
        self, observaciones: list[Observacion], etiquetas: list[NivelRiesgo]
    ) -> BosqueAleatorio:
        if len(observaciones) != len(etiquetas):
            raise ValueError(
                f"{len(observaciones)} observaciones y {len(etiquetas)} etiquetas: "
                "no se pueden alinear"
            )
        if not observaciones:
            raise ValueError("no se puede ajustar sin observaciones")

        # Orden alfabetico y explicito, como en H3.3: dos corridas con las
        # columnas en distinto orden tienen que dar el MISMO bosque, y las
        # importancias tienen que poder leerse por nombre.
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

        self._modelo = RandomForestClassifier(
            n_estimators=ARBOLES,
            class_weight="balanced" if self.balancear else None,
            random_state=SEMILLA,
            n_jobs=1,  # ver la cabecera: con -1 predict_proba no es reproducible
        ).fit(np.asarray(filas, dtype=float), objetivo)
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
            for i, etiqueta in zip(indices, self._modelo.predict(X), strict=True):
                salida[i] = NivelRiesgo(etiqueta)
        return salida

    def probabilidades(
        self, observaciones: list[Observacion]
    ) -> list[dict[NivelRiesgo, float] | None]:
        """Una distribucion por fila, rotulada por clase; `None` donde no se predice.

        Rotulada y no posicional por la misma razon que los coeficientes de
        H3.3: `classes_` viene en orden alfabetico ('alto' < 'bajo' < 'medio'),
        y quien lea la columna 1 como «alto» en un evento de dos clases se va a
        equivocar de nivel.
        """
        if self._modelo is None:
            raise ValueError("hay que llamar a ajustar() antes de probabilidades()")

        salida: list[dict[NivelRiesgo, float] | None] = [None] * len(observaciones)
        indices, filas = self._completas(observaciones)
        if filas:
            clases = [NivelRiesgo(c) for c in self._modelo.classes_]
            matriz = self._modelo.predict_proba(np.asarray(filas, dtype=float))
            for i, fila in zip(indices, matriz, strict=True):
                salida[i] = dict(zip(clases, fila.tolist(), strict=True))
        return salida

    # ----------------------------------------------------------------- #
    def _completas(self, observaciones: list[Observacion]) -> tuple[list[int], list[list[float]]]:
        """Indices y filas de las observaciones que traen todas sus columnas.

        Es un solo lugar para que `predecir()` y `probabilidades()` no puedan
        discrepar sobre que fila se predice: si discreparan, la probabilidad de
        una fila podria existir sin su nivel, o al reves.
        """
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

        Por nombre y no por posicion, como en H3.3: confiar en el orden es el
        defecto que entrena sobre `acum3` creyendo que es `media30` sin
        levantar ninguna excepcion.
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
        """Cuantas filas quedaron en `None` en la ultima llamada a `predecir`."""
        return self._filas_sin_prediccion

    @property
    def filas_descartadas_al_ajustar(self) -> int:
        return self._filas_descartadas_al_ajustar

    @property
    def importancias(self) -> dict[str, float]:
        """Reduccion media de impureza por columna, por nombre. Suma 1.

        Es lo que H4.1 lee. No es causalidad: dos columnas correlacionadas se
        reparten la importancia de forma arbitraria, y una columna con muchos
        valores distintos recibe mas de la que merece. Para explicar una
        prediccion concreta esta H4.2.
        """
        if self._modelo is None:
            raise ValueError("hay que llamar a ajustar() antes de leer importancias")
        return dict(zip(self._columnas, self._modelo.feature_importances_.tolist(), strict=True))


def main() -> int:
    print(
        "\nEste modulo es un estimador del arnes de H3.6, no un guion suelto.\n"
        "La tabla comparativa, con las lineas base y la particion de H3.2, sale de:\n\n"
        "    python -m backend.modelado.comparar\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
