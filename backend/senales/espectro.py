"""
Analisis espectral de la precipitacion. Historia H2.2.

Implementa `espectro` del contrato `contratos/senales.py` y agrega las funciones
que hacen falta para la **interpretacion fisica**, que es lo que la historia pide
mas alla de la transformada.

QUE SE ESPERA ENCONTRAR, Y POR QUE

En la vertiente del Pacifico de Costa Rica el regimen de lluvia no es una sola
onda anual. Tiene dos componentes que deberian aparecer como picos separados:

- **Ciclo anual**, periodo de 365,25 dias. Es la estacion seca contra la
  lluviosa, y es el pico dominante esperable.
- **Ciclo semianual**, periodo de 182,6 dias. En esta region ese armonico es la
  firma del **veranillo**: la pausa de lluvias de julio y agosto que parte la
  estacion lluviosa en dos maximos, uno en junio y otro en setiembre-octubre.

El veranillo esta caracterizado para cuencas de la vertiente del Pacifico
costarricense por Alfaro (2014), referencia `[27]`. Que aparezca en el espectro
de Tilaran seria evidencia propia de que el regimen del canton es bimodal, y eso
importa para el modelo: **un julio seco puede ser veranillo normal y no sequia.**

DECISION D-17: LA SERIE ENTRA CRUDA

Aqui filtrar seria especialmente danino. Un filtro de suavizado **es** un filtro
paso bajo: atenua las componentes de alta frecuencia. Aplicarlo antes de medir
el contenido espectral altera justamente lo que se quiere medir, y el resultado
mostraria el espectro del filtro tanto como el de la lluvia.

DIFERENCIA CONOCIDA CON EL SIMULADO

El simulado rellena con ceros hasta la siguiente potencia de dos, porque su
transformada esta escrita a mano en Python puro y lo necesita. Este modulo usa
`scipy.fft`, que no lo necesita, y **no rellena**. El relleno interpola el
espectro pero no agrega resolucion, asi que los picos caen en los mismos
periodos; lo que cambia es en que casillero exacto caen.

Por eso las pruebas que corren contra las dos implementaciones comprueban
**cual es el casillero dominante respecto de la frecuencia buscada**, y no un
valor de periodo concreto.
"""

from __future__ import annotations

from scipy.fft import rfft, rfftfreq

DIAS_POR_ANO = 365.25
PERIODO_ANUAL = DIAS_POR_ANO
PERIODO_SEMIANUAL = DIAS_POR_ANO / 2

FRECUENCIA_ANUAL = 1 / PERIODO_ANUAL
FRECUENCIA_SEMIANUAL = 1 / PERIODO_SEMIANUAL

# Con menos de dos ciclos completos de la componente mas lenta que se busca, el
# espectro no la puede separar de la tendencia. Dos anios es el minimo para
# hablar del ciclo anual, y no alcanza para decir nada firme.
MINIMO_DIAS_RECOMENDADO = int(2 * DIAS_POR_ANO)


class AnalizadorEspectral:
    """
    Analisis en el dominio de la frecuencia de series climaticas.

    Cumple el metodo `espectro` del protocolo `ProcesadorSenales`. Los demas los
    implementan otras historias: `filtrar_ruido` en H2.1, `spi` en H2.3,
    `anomalia` en H2.4 y `remuestrear` en H2.6.
    """

    def espectro(
        self,
        serie: list[float | None],
        frecuencia_muestreo: float,
    ) -> tuple[list[float], list[float]]:
        """
        Espectro de amplitud de la serie.

        Args:
            serie: valores, **sin huecos**. La serie entra cruda, sin filtrar
                (D-17).
            frecuencia_muestreo: muestras por unidad de tiempo. Para datos
                diarios se pasa 1.0 y las frecuencias salen en ciclos por dia.

        Returns:
            `(frecuencias, magnitudes)`, ambas del mismo largo, desde la
            componente continua hasta la frecuencia de Nyquist. La otra mitad
            del espectro es su reflejo para una senal real y no se devuelve.

        Raises:
            ValueError: si la frecuencia de muestreo no es positiva, si hay
                menos de dos muestras, o si la serie tiene huecos.
        """
        if frecuencia_muestreo <= 0:
            raise ValueError(
                f"La frecuencia de muestreo debe ser positiva, se recibio {frecuencia_muestreo}"
            )

        valores = _sin_huecos(serie)
        n = len(valores)
        if n < 2:
            raise ValueError(f"Hacen falta al menos 2 muestras para un espectro, hay {n}")

        # Se resta la media antes de transformar. Sin esto la componente de
        # frecuencia cero, que es la media por el numero de muestras, domina el
        # espectro por completo: la magnitud mayor seria siempre esa, y no dice
        # nada del ciclo anual. Es la parte constante de la senal, no una
        # oscilacion.
        media = sum(valores) / n
        centrada = [v - media for v in valores]

        transformada = rfft(centrada)
        frecuencias = rfftfreq(n, d=1.0 / frecuencia_muestreo)

        # El factor 2/n devuelve la amplitud de cada componente en las unidades
        # de la serie: un ciclo anual de amplitud 10 mm sale como 10, no como un
        # numero que dependa del largo de la serie.
        magnitudes = [abs(c) * 2.0 / n for c in transformada]

        return list(frecuencias), magnitudes


# --------------------------------------------------------------------------- #
# Interpretacion fisica                                                         #
# --------------------------------------------------------------------------- #


def casillero_mas_cercano(frecuencias: list[float], objetivo: float) -> int:
    """
    Indice del casillero cuya frecuencia esta mas cerca de `objetivo`.

    Se excluye el casillero 0, que es la componente continua: con la media ya
    restada vale practicamente cero y no representa ninguna oscilacion.
    """
    return min(range(1, len(frecuencias)), key=lambda i: abs(frecuencias[i] - objetivo))


def periodo_de(frecuencia: float) -> float | None:
    """Periodo en dias, o None para la componente continua."""
    return None if frecuencia == 0 else 1 / frecuencia


def picos_principales(
    frecuencias: list[float],
    magnitudes: list[float],
    cuantos: int = 5,
    separacion_minima: int = 3,
) -> list[tuple[float, float]]:
    """
    Los `cuantos` picos de mayor magnitud, como `(periodo_en_dias, magnitud)`.

    **Por que hace falta la separacion minima.** Un pico real no ocupa un solo
    casillero: se reparte entre sus vecinos por el largo finito de la serie. Sin
    separacion, los cinco "picos" mas altos serian los cinco casilleros
    contiguos del mismo maximo, y el resultado diria que hay cinco ciclos donde
    hay uno.

    Se descarta el casillero 0 por el mismo motivo que en
    `casillero_mas_cercano`.
    """
    if separacion_minima < 1:
        raise ValueError(
            f"La separacion minima debe ser al menos 1 casillero, se recibio {separacion_minima}"
        )

    candidatos = sorted(range(1, len(magnitudes)), key=lambda i: magnitudes[i], reverse=True)

    elegidos: list[int] = []
    for i in candidatos:
        if len(elegidos) >= cuantos:
            break
        if all(abs(i - j) >= separacion_minima for j in elegidos):
            elegidos.append(i)

    return [(periodo_de(frecuencias[i]), magnitudes[i]) for i in elegidos]  # type: ignore[misc]


def magnitud_en(frecuencias: list[float], magnitudes: list[float], objetivo: float) -> float:
    """Magnitud del casillero mas cercano a una frecuencia dada."""
    return magnitudes[casillero_mas_cercano(frecuencias, objetivo)]


def razon_semianual_anual(frecuencias: list[float], magnitudes: list[float]) -> float | None:
    """
    Cuanta amplitud tiene el ciclo semianual respecto del anual.

    Es el numero que resume si el regimen es bimodal. Un valor alto significa
    que la componente de medio anio pesa, y en esta region esa componente es la
    firma del veranillo (Alfaro, 2014).

    Devuelve None si el ciclo anual no tiene amplitud, en cuyo caso la razon no
    esta definida y **no se devuelve cero**: cero seria "no hay semianual", que
    es una afirmacion distinta.
    """
    anual = magnitud_en(frecuencias, magnitudes, FRECUENCIA_ANUAL)
    if anual == 0:
        return None

    return magnitud_en(frecuencias, magnitudes, FRECUENCIA_SEMIANUAL) / anual


# --------------------------------------------------------------------------- #
# Internos                                                                      #
# --------------------------------------------------------------------------- #


def _sin_huecos(serie: list[float | None]) -> list[float]:
    """
    La serie como floats, o ValueError diciendo cuantos faltan.

    Lo exige el contrato, y el motivo es concreto: interpolar en silencio antes
    de una transformada introduce componentes espectrales que no estan en el
    dato. El error dice cuantos faltan para que quien lo reciba sepa si es un
    hueco aislado o media serie.
    """
    faltantes = sum(1 for v in serie if v is None)
    if faltantes:
        raise ValueError(
            f"La serie tiene {faltantes} valores faltantes de {len(serie)}. "
            "Interpolar en silencio antes de una transformada introduce componentes "
            "espectrales que no estan en el dato. Imputar es una decision explicita: "
            "ver la historia H1.4."
        )
    return [float(v) for v in serie]  # type: ignore[arg-type]
