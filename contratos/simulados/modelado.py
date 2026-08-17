"""
Estimador y evaluador simulados. Dueno: Alejandro. Cumple contratos/modelado.py.

POR QUE EXISTE

El plan de pruebas H10.1 planifica diez casos sobre `Estimador` y `Evaluador` que
no se podian implementar porque los contratos no tenian simulado. Junto con
`senales.py` desbloquean los 16 casos que Luna tenia detenidos, el 41 % de H10.2.

QUE SE SIMULA Y QUE NO

Lo que **no** se simula, porque es justamente lo que las pruebas tienen que
proteger:

- Un estimador sin entrenar lanza RuntimeError. No devuelve un valor plausible.
- La linea base ignora las caracteristicas de verdad, no de mentira.
- La linea base devuelve None en `explicar`, que significa "no disponible" y no
  "sin contribucion".
- La validacion por ventana expansiva rechaza una particion desordenada en vez de
  aceptarla en silencio.
- Un modelo que no supera la linea base es un resultado, no una excepcion.

Lo que **si** se simula es el aprendizaje: aqui no hay ajuste real. Un
`EstimadorSimulado` que no es la linea base predice a partir de un resumen trivial
de las caracteristicas, de forma determinista. Sirve para probar el contrato y el
flujo, no para medir desempeno. Los modelos reales son H3.6.

**Ninguna metrica que salga de aqui puede ir al documento.** Son numeros con la
forma correcta y sin significado: eso es lo que hace util un simulado y peligroso
un descuido.
"""

from __future__ import annotations

import logging
import math
from datetime import date, datetime

from ..enums import Algoritmo, NivelRiesgo, TipoEvento
from ..esquemas import ContribucionVariable, MetricasModelo

log = logging.getLogger(__name__)

VERSION_SIMULADO = "0.0.0-simulado"

# Orden de los tres niveles, de menor a mayor. Se usa para convertir un resumen
# numerico en un nivel sin escribir la escala dos veces.
_NIVELES = [NivelRiesgo.BAJO, NivelRiesgo.MEDIO, NivelRiesgo.ALTO]


def _resumen(caracteristicas: dict[str, float | None]) -> float:
    """
    Reduce un diccionario de caracteristicas a un numero, de forma determinista.

    Los None se omiten en lugar de contar como cero: contarlos como cero seria
    inventar una medicion, que es la regla que el proyecto no rompe.
    """
    presentes = [v for v in caracteristicas.values() if v is not None]
    if not presentes:
        return 0.0
    return sum(presentes) / len(presentes)


class EstimadorSimulado:
    """
    Cumple el protocolo Estimador.

    Sirve tanto para la linea base como para los tres algoritmos, porque el
    contrato es el mismo para todos. La diferencia de comportamiento se decide por
    el algoritmo con el que se construye, no por una clase aparte:

        EstimadorSimulado(Algoritmo.LINEA_BASE, TipoEvento.SEQUIA)
        EstimadorSimulado(Algoritmo.RANDOM_FOREST, TipoEvento.SEQUIA)

    Que la linea base cumpla el mismo contrato es deliberado y viene del contrato:
    se evalua con el mismo codigo y sobre las mismas particiones, sin margen para
    una comparacion sesgada.
    """

    def __init__(
        self,
        algoritmo: Algoritmo = Algoritmo.RANDOM_FOREST,
        tipo_evento: TipoEvento = TipoEvento.SEQUIA,
        version: str = VERSION_SIMULADO,
    ) -> None:
        log.warning(
            "EstimadorSimulado en uso (%s): no hay aprendizaje real, "
            "las predicciones NO significan nada",
            algoritmo.value,
        )
        self.algoritmo = algoritmo
        self.tipo_evento = tipo_evento
        self.version = version

        self._entrenado = False
        self._nivel_mas_frecuente: NivelRiesgo = NivelRiesgo.BAJO
        self._por_mes: dict[int, NivelRiesgo] = {}
        self._umbrales: tuple[float, float] = (0.0, 0.0)
        self._variables: list[str] = []

    @property
    def es_linea_base(self) -> bool:
        return self.algoritmo is Algoritmo.LINEA_BASE

    # ------------------------------------------------------------------ estado

    def entrenado(self) -> bool:
        """False mientras no se haya ajustado. Se consulta antes de predecir."""
        return self._entrenado

    # --------------------------------------------------------------- ajuste

    def entrenar(
        self,
        caracteristicas: list[dict[str, float | None]],
        etiquetas: list[NivelRiesgo],
    ) -> None:
        """
        Ajusta el estimador.

        La linea base ignora `caracteristicas` salvo la clave `mes`, que es parte
        de su definicion: estima a partir de la distribucion historica del distrito
        para ese mes calendario y de nada mas. Si `mes` no viene, se queda con el
        nivel mas frecuente del entrenamiento.

        Los demas algoritmos derivan dos umbrales de la distribucion del resumen de
        caracteristicas. No es aprendizaje: es una regla fija que produce
        resultados deterministas y distintos segun la entrada, que es lo que hace
        falta para probar el contrato.
        """
        if len(caracteristicas) != len(etiquetas):
            raise ValueError(
                f"Hay {len(caracteristicas)} observaciones y {len(etiquetas)} etiquetas. "
                "Deben ser iguales: una etiqueta por observacion."
            )
        if not etiquetas:
            raise ValueError("No se puede entrenar sin observaciones")

        conteo: dict[NivelRiesgo, int] = {}
        for etiqueta in etiquetas:
            conteo[etiqueta] = conteo.get(etiqueta, 0) + 1
        self._nivel_mas_frecuente = max(conteo, key=lambda k: (conteo[k], _NIVELES.index(k)))

        if self.es_linea_base:
            # Solo `mes`. Se ignora deliberadamente todo lo demas.
            por_mes: dict[int, dict[NivelRiesgo, int]] = {}
            for fila, etiqueta in zip(caracteristicas, etiquetas, strict=True):
                mes_valor = fila.get("mes")
                if mes_valor is None:
                    continue
                mes = int(mes_valor)
                por_mes.setdefault(mes, {})
                por_mes[mes][etiqueta] = por_mes[mes].get(etiqueta, 0) + 1

            self._por_mes = {
                mes: max(c, key=lambda k: (c[k], _NIVELES.index(k))) for mes, c in por_mes.items()
            }
            self._variables = []
        else:
            resumenes = sorted(_resumen(f) for f in caracteristicas)
            n = len(resumenes)
            self._umbrales = (resumenes[n // 3], resumenes[(2 * n) // 3])
            self._variables = sorted({clave for fila in caracteristicas for clave in fila})

        self._entrenado = True

    # ------------------------------------------------------------ prediccion

    def predecir(
        self,
        caracteristicas: list[dict[str, float | None]],
    ) -> list[tuple[NivelRiesgo, float]]:
        """
        Devuelve (nivel, probabilidad) por observacion.

        Lanza RuntimeError si no esta entrenado. Nunca devuelve una prediccion por
        defecto: un estimador sin entrenar no tiene nada que decir, y devolver
        NivelRiesgo.BAJO con probabilidad 0.5 seria inventar un dato con la forma
        correcta, que es exactamente el error que este proyecto persigue.
        """
        if not self._entrenado:
            raise RuntimeError(
                f"El estimador {self.algoritmo.value} no esta entrenado. "
                "Llamar a entrenar() antes de predecir(). No hay prediccion por defecto."
            )

        salida: list[tuple[NivelRiesgo, float]] = []

        for fila in caracteristicas:
            if self.es_linea_base:
                mes_valor = fila.get("mes")
                if mes_valor is None:
                    nivel = self._nivel_mas_frecuente
                else:
                    nivel = self._por_mes.get(int(mes_valor), self._nivel_mas_frecuente)
                # La linea base no modela incertidumbre: reporta la frecuencia
                # historica como una constante declarada, no calculada.
                salida.append((nivel, 0.5))
                continue

            valor = _resumen(fila)
            bajo, alto = self._umbrales
            if valor <= bajo:
                nivel = NivelRiesgo.BAJO
            elif valor <= alto:
                nivel = NivelRiesgo.MEDIO
            else:
                nivel = NivelRiesgo.ALTO

            # Probabilidad determinista en (0, 1), monotona respecto del resumen.
            probabilidad = 1.0 / (1.0 + math.exp(-valor))
            salida.append((nivel, round(probabilidad, 6)))

        return salida

    # ---------------------------------------------------------- explicabilidad

    def explicar(
        self,
        caracteristicas: dict[str, float | None],
    ) -> list[ContribucionVariable] | None:
        """
        Aporte de cada variable a una prediccion concreta.

        Devuelve None cuando el estimador no soporta explicabilidad, que es el caso
        de la linea base. **None significa "no disponible", no "sin contribucion".**
        Una lista vacia diria que todas las variables aportan cero, que es una
        afirmacion distinta y falsa.
        """
        if self.es_linea_base:
            return None

        if not self._entrenado:
            raise RuntimeError(
                f"El estimador {self.algoritmo.value} no esta entrenado. "
                "No hay contribuciones que explicar."
            )

        media = _resumen(caracteristicas)
        contribuciones = [
            ContribucionVariable(variable=nombre, aporte=round((valor - media), 6))
            for nombre, valor in sorted(caracteristicas.items())
            if valor is not None
        ]
        return sorted(contribuciones, key=lambda c: abs(c.aporte), reverse=True)


class EvaluadorSimulado:
    """
    Cumple el protocolo Evaluador.

    Las comprobaciones temporales son reales: es lo unico que no tiene sentido
    simular, porque una fuga temporal no rompe ninguna prueba por si sola. Infla
    las metricas y no se descubre hasta el analisis final, cuando ya invalido el
    contraste de H1.
    """

    nombre = "SIMULADO-evaluador"

    def __init__(self) -> None:
        log.warning("EvaluadorSimulado en uso: las metricas NO miden desempeno real")

    def validar_ventana_expansiva(
        self,
        estimador,
        caracteristicas: list[dict[str, float | None]],
        etiquetas: list[NivelRiesgo],
        fechas: list[date],
        n_cortes: int,
    ) -> MetricasModelo:
        """
        Valida por ventana expansiva: entrena con el pasado, prueba con el futuro.

        Cuatro reglas que se hacen cumplir, no se suponen:

        1. **Las fechas deben venir en orden ascendente.** Una particion construida
           al azar sobre las mismas fechas se rechaza con ValueError. Aceptarla en
           silencio es la definicion de fuga temporal.
        2. **La ventana se expande, no se desliza.** Cada pliegue de entrenamiento
           contiene integramente al anterior. Una ventana deslizante descartaria
           historia que si estaba disponible en operacion.
        3. **Ningun dato de entrenamiento es posterior al inicio de su prueba.**
        4. **Se producen exactamente `n_cortes` evaluaciones**, o se falla diciendo
           por que no alcanzan los datos. Un corte omitido en silencio cambia el
           denominador de la metrica.
        """
        n = len(caracteristicas)
        if not (n == len(etiquetas) == len(fechas)):
            raise ValueError(
                f"Longitudes distintas: {n} caracteristicas, {len(etiquetas)} etiquetas, "
                f"{len(fechas)} fechas."
            )
        if n_cortes < 1:
            raise ValueError(f"Hacen falta al menos 1 corte, se pidieron {n_cortes}")

        desordenadas = [i for i in range(1, len(fechas)) if fechas[i] < fechas[i - 1]]
        if desordenadas:
            raise ValueError(
                f"Las fechas no estan en orden ascendente: {len(desordenadas)} posiciones "
                f"rompen el orden, la primera en el indice {desordenadas[0]}. "
                "La validacion por ventana expansiva exige orden temporal. Una particion "
                "aleatoria entrena con datos posteriores a los que evalua e infla las "
                "metricas sin que ninguna prueba falle."
            )

        if n < n_cortes + 1:
            raise ValueError(
                f"Con {n} observaciones no se pueden hacer {n_cortes} cortes: "
                f"hacen falta al menos {n_cortes + 1}."
            )

        paso = n // (n_cortes + 1)
        aciertos = 0
        evaluadas = 0
        cortes_hechos = 0
        matriz = [[0, 0, 0] for _ in range(3)]
        fin_entrenamiento_anterior = 0

        for corte in range(1, n_cortes + 1):
            fin_entrenamiento = paso * corte
            fin_prueba = paso * (corte + 1) if corte < n_cortes else n

            # Regla 2: la ventana crece.
            if fin_entrenamiento < fin_entrenamiento_anterior:
                raise ValueError(
                    f"El corte {corte} reduce el conjunto de entrenamiento respecto del "
                    "anterior. La ventana debe expandirse, no deslizarse."
                )
            fin_entrenamiento_anterior = fin_entrenamiento

            # Regla 3: nada del entrenamiento es posterior al inicio de la prueba.
            if fechas[fin_entrenamiento - 1] > fechas[fin_entrenamiento]:
                raise ValueError(
                    f"En el corte {corte} la ultima fecha de entrenamiento "
                    f"({fechas[fin_entrenamiento - 1]}) es posterior a la primera de prueba "
                    f"({fechas[fin_entrenamiento]})."
                )

            estimador.entrenar(
                caracteristicas[:fin_entrenamiento],
                etiquetas[:fin_entrenamiento],
            )
            predicciones = estimador.predecir(caracteristicas[fin_entrenamiento:fin_prueba])

            for (nivel, _), esperado in zip(
                predicciones, etiquetas[fin_entrenamiento:fin_prueba], strict=True
            ):
                matriz[_NIVELES.index(esperado)][_NIVELES.index(nivel)] += 1
                aciertos += int(nivel == esperado)
                evaluadas += 1

            cortes_hechos += 1

        # Regla 4.
        if cortes_hechos != n_cortes:
            raise ValueError(f"Se pidieron {n_cortes} cortes y se completaron {cortes_hechos}.")

        exactitud = aciertos / evaluadas if evaluadas else None

        return MetricasModelo(
            algoritmo=estimador.algoritmo,
            tipo_evento=estimador.tipo_evento,
            version=estimador.version,
            entrenado_en=datetime.now(),
            # Se reporta la misma cifra en los tres promedios macro a proposito:
            # este simulado no calcula F1 real. Es un numero con la forma correcta.
            # El calculo de verdad es H3.6 y usa scikit-learn.
            f1_macro=exactitud,
            precision_macro=exactitud,
            exhaustividad_macro=exactitud,
            matriz_confusion=matriz,
            supera_linea_base=None,
        )

    def comparar_con_linea_base(
        self,
        metricas_modelo: MetricasModelo,
        metricas_linea_base: MetricasModelo,
    ) -> tuple[bool, float]:
        """
        Contrasta H1. Devuelve (supera, valor_p).

        **Un resultado negativo no es un fallo ni una excepcion.** Significa que los
        datos abiertos globales no bastan a escala cantonal, que es un hallazgo
        valido, publicable, y previsto desde el diseno: H1 es refutable a proposito.

        El valor_p de aqui es una cifra con la forma correcta y sin significado
        estadistico. La prueba real es H3.6.
        """
        f1_modelo = metricas_modelo.f1_macro
        f1_base = metricas_linea_base.f1_macro

        if f1_modelo is None or f1_base is None:
            raise ValueError(
                "Alguna de las dos metricas no tiene F1-macro calculado. "
                "No se contrasta contra un valor ausente: se evalua primero."
            )

        diferencia = f1_modelo - f1_base
        supera = diferencia > 0

        # Cifra determinista en (0, 1] que decrece cuando la diferencia crece.
        valor_p = round(math.exp(-abs(diferencia) * 10), 6)

        return supera, valor_p
