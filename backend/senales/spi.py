"""
Indice de Precipitacion Estandarizado (SPI). Historia H2.3.

Implementa `spi` del contrato `contratos/senales.py`, siguiendo a McKee, Doesken
y Kleist (1993), referencia [4], con las decisiones de calculo de la guia
operativa de la OMM, WMO-No. 1090, referencia [24].

El procedimiento es el de la referencia y tiene tres pasos:

1. **Acumular** la precipitacion sobre una ventana movil de `ventana_meses`
   meses. Es una convolucion con un nucleo rectangular de unos.
2. **Ajustar una distribucion gamma** a los acumulados, con la correccion para
   ceros de la OMM, porque la gamma no esta definida en cero y Tilaran tiene
   meses de 0 mm en estacion seca.
3. **Transformar** la probabilidad acumulada a la normal estandar. El resultado
   es el SPI: cuantas desviaciones tipicas se aparta ese acumulado de lo normal.

IMPORTANTE, decision D-17: **la serie entra cruda**. La precipitacion no se
filtra en ningun punto de la cadena. Pasar por `filtrar_ruido` antes de llamar
aqui produce valores negativos de lluvia, que rompen el ajuste gamma porque esta
definido sobre valores no negativos. Ver `docs/03-bitacora-decisiones.md`.

LIMITACION CONOCIDA: el ajuste no es por mes calendario. Ver la nota extensa en
`ajustar_gamma` y la solicitud de cambio en
`docs/investigacion/solicitud-cambio-spi-mes.md`.
"""

from __future__ import annotations

import math

from scipy.stats import gamma, norm

# La OMM recomienda al menos 30 anios de registro para un SPI estable. Por
# debajo de esto el ajuste existe pero sus colas no son confiables, y es
# justamente en las colas donde se declara la sequia.
MINIMO_RECOMENDADO_ANIOS = 30
MINIMO_AJUSTE = 4  # menos que esto no permite estimar dos parametros


class CalculadorSPI:
    """
    Calcula el SPI sobre una serie mensual de precipitacion.

    Cumple el metodo `spi` del protocolo `ProcesadorSenales`. Los demas metodos
    los implementan otras historias: `filtrar_ruido` en H2.1, `espectro` en
    H2.2, `anomalia` en H2.4 y `remuestrear` en H2.6.
    """

    def spi(
        self,
        precipitacion: list[float | None],
        ventana_meses: int,
    ) -> list[float | None]:
        """
        Indice de Precipitacion Estandarizado por convolucion de ventana movil.

        Args:
            precipitacion: acumulado **mensual** de precipitacion en mm, con
                None en los meses sin dato. La serie entra cruda, sin filtrar
                (D-17).
            ventana_meses: 1 para SPI-1, 3 para SPI-3. El proyecto usa SPI-3
                para el umbral de sequia de `contratos/enums.py`.

        Returns:
            Una lista del mismo largo que la entrada. Las primeras
            `ventana_meses` posiciones son None porque no hay historia
            suficiente para calcularlas, y no se rellenan con ceros: un cero es
            un valor de sequia neutra que nadie calculo.

        Raises:
            ValueError: si `ventana_meses` es menor que 1, o si algun valor de
                precipitacion es negativo.
        """
        if ventana_meses < 1:
            raise ValueError(f"La ventana debe ser al menos 1 mes, se recibio {ventana_meses}")

        negativos = [v for v in precipitacion if v is not None and v < 0]
        if negativos:
            raise ValueError(
                f"La precipitacion no puede ser negativa; se recibieron {len(negativos)} "
                f"valores negativos, el menor de {min(negativos):.2f} mm. "
                "Si la serie paso por filtrar_ruido, eso explica los negativos: la "
                "decision D-17 prohibe filtrar precipitacion, justamente por esto."
            )

        acumulados = acumular(precipitacion, ventana_meses)

        muestra = [v for v in acumulados if v is not None]
        if len(muestra) < MINIMO_AJUSTE:
            # Sin muestra suficiente no se ajusta nada. Se devuelve todo None y
            # no ceros: la ausencia de resultado no es un resultado neutro.
            return [None] * len(precipitacion)

        forma, escala, prob_cero = ajustar_gamma(muestra)
        if forma is None:
            return [None] * len(precipitacion)

        return [
            None if v is None else _a_normal_estandar(v, forma, escala, prob_cero)
            for v in acumulados
        ]


def acumular(serie: list[float | None], ventana: int) -> list[float | None]:
    """
    Convolucion con nucleo rectangular: suma movil de `ventana` posiciones.

    Una ventana que contiene algun hueco produce None, no la suma de lo que hay.
    Sumar solo los meses presentes daria un acumulado sistematicamente menor y
    el SPI lo leeria como sequia donde lo que hay es falta de dato.

    Las primeras `ventana` posiciones salen None por definicion del indice,
    aunque en la posicion `ventana - 1` la ventana ya este completa. Es la
    convencion del contrato y del simulado.
    """
    n = len(serie)
    salida: list[float | None] = [None] * n

    for i in range(ventana - 1, n):
        trozo = serie[i - ventana + 1 : i + 1]
        if any(v is None for v in trozo):
            continue
        salida[i] = sum(v for v in trozo if v is not None)

    for i in range(min(ventana, n)):
        salida[i] = None

    return salida


def ajustar_gamma(muestra: list[float]) -> tuple[float | None, float | None, float]:
    """
    Ajusta una gamma de dos parametros a los acumulados no nulos.

    Devuelve (forma, escala, probabilidad_de_cero).

    **Por que se separan los ceros.** La distribucion gamma no esta definida en
    cero, y Tilaran tiene meses de 0,0 mm en estacion seca. La OMM (WMO-No.
    1090) resuelve esto con una distribucion mixta: la probabilidad acumulada
    es H(x) = q + (1 - q) G(x), donde q es la proporcion de ceros de la muestra
    y G la gamma ajustada solo sobre los valores positivos. Descartar los ceros
    sin contarlos en q inflaria el indice en los climas con estacion seca, que
    es exactamente el caso de este canton.

    **LIMITACION: el ajuste no es por mes calendario.**

    El SPI de McKee ajusta una gamma distinta para cada mes del anio: los
    eneros contra la distribucion historica de los eneros, los febreros contra
    los febreros. Eso es lo que lo convierte en un indice de anomalia.

    La firma del contrato `spi(precipitacion, ventana_meses)` no recibe fechas,
    asi que aqui no se puede saber a que mes corresponde cada posicion y el
    ajuste es unico para toda la serie.

    En un clima con estacion seca marcada la diferencia no es menor: con ajuste
    unico, los meses secos salen con SPI negativo *siempre* y los lluviosos
    positivo *siempre*, de modo que el indice sigue la estacionalidad en vez de
    la anomalia. La medicion de cuanto se desvia esta en
    `docs/herramientas/medir_spi_por_mes.py` y la solicitud de cambio de
    contrato en `docs/investigacion/solicitud-cambio-spi-mes.md`.

    **Este modulo no corrige el contrato por su cuenta.** Se implementa lo que
    el contrato permite, se mide el costo y se pide el cambio.
    """
    positivos = [v for v in muestra if v > 0]
    prob_cero = (len(muestra) - len(positivos)) / len(muestra)

    if len(positivos) < MINIMO_AJUSTE:
        return None, None, prob_cero

    # Sin dispersion no hay anomalia que medir, y ademas el ajuste diverge: la
    # forma de la gamma tiende a infinito cuando todos los valores son iguales,
    # y scipy lanza al no poder resolver. Se devuelve None en vez de un numero,
    # porque un SPI de 0.0 seria un valor de sequia neutra que nadie calculo.
    media = sum(positivos) / len(positivos)
    if media <= 0:
        return None, None, prob_cero
    dispersion = max(positivos) - min(positivos)
    if dispersion / media < 1e-9:
        return None, None, prob_cero

    # floc=0 fija el origen de la gamma en cero, que es lo correcto para
    # precipitacion: no existe lluvia por debajo de cero y dejar que el ajuste
    # desplace el origen produciria un umbral negativo sin sentido fisico.
    try:
        forma, _, escala = gamma.fit(positivos, floc=0)
    except (ValueError, RuntimeError):
        # El ajuste no convergio. Es un resultado, no una excepcion que deba
        # propagarse: quien llama recibe None y sabe que no hay indice.
        return None, None, prob_cero

    if not math.isfinite(forma) or not math.isfinite(escala) or escala <= 0:
        return None, None, prob_cero

    return float(forma), float(escala), prob_cero


def _a_normal_estandar(
    acumulado: float,
    forma: float,
    escala: float,
    prob_cero: float,
) -> float:
    """
    Transforma un acumulado a SPI mediante la probabilidad acumulada mixta.

    H(x) = q + (1 - q) * G(x), y despues el cuantil de la normal estandar.

    Los extremos se acotan para que la transformacion no devuelva infinito
    cuando la probabilidad cae exactamente en 0 o en 1, que ocurre con muestras
    cortas. El limite equivale a un SPI de aproximadamente +-3,7, mas alla del
    cual la clasificacion de sequia no distingue nada: los umbrales del
    proyecto estan en -1,0 y -1,5.

    **El caso del acumulado cero, y una atribucion que hay que verificar.**

    Con la distribucion mixta, en x = 0 se tiene G(0) = 0 y por lo tanto
    H(0) = q. La lectura directa seria entonces `ppf(q)`.

    Aqui se usa `ppf(q / 2)`, que es la variante de centro de masa: reparte la
    masa de probabilidad de los ceros en lugar de acumularla toda en su
    extremo superior, y evita la discontinuidad que produce usar q entre el
    ultimo cero y el primer valor positivo.

    **La eleccion se mantiene; lo que no esta resuelto es a quien se atribuye.**
    Una version anterior de este archivo la atribuia a la OMM, lo cual es
    incorrecto: WMO-No. 1090 plantea la distribucion mixta pero no se verifico
    que recomiende la mitad. Alejandro sugirio Stagge et al. (2015),
    *Candidate Distributions for Climatological Drought Indices (SPI and
    SPEI)*, Int. J. Climatology 35(13), 4027-4040, DOI 10.1002/joc.4267. Se
    confirmo que ese articulo existe con esos datos, pero **no** que sea la
    fuente de esta correccion en particular.

    Queda pendiente confirmarlo contra el texto de una de las dos fuentes antes
    de que la afirmacion pase al documento IEEE. Mientras tanto no se cita
    ninguna: es preferible una decision sin atribucion a una atribucion falsa.

    Con 35 anios y SPI-3 el efecto numerico entre `q` y `q / 2` es menor.
    """
    if acumulado <= 0:
        # ATRIBUCION PENDIENTE DE VERIFICAR. Ver la nota de abajo.
        probabilidad = prob_cero / 2
    else:
        probabilidad = prob_cero + (1 - prob_cero) * gamma.cdf(acumulado, forma, scale=escala)

    probabilidad = min(max(probabilidad, 1e-4), 1 - 1e-4)

    return float(norm.ppf(probabilidad))
