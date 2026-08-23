"""
Indice de Precipitacion Estandarizado (SPI). Historia H2.3.

Implementa `spi` del contrato `contratos/senales.py`, siguiendo a McKee, Doesken
y Kleist (1993), referencia [4].

De la guia operativa de la OMM, WMO-No. 1090, referencia [24], se toman tres
decisiones: el minimo de 30 anios de registro, el rango defendible de 1 a 24
meses de ventana, y el conjunto de comparacion por mes calendario. **No se toma
de ahi el tratamiento de ceros**: esa guia no contiene ninguna formula. Ver la
nota de `ajustar_gamma`.

El procedimiento es el de la referencia y tiene tres pasos:

1. **Acumular** la precipitacion sobre una ventana movil de `ventana_meses`
   meses. Es una convolucion con un nucleo rectangular de unos.
2. **Ajustar una distribucion gamma** a los acumulados, con la correccion para
   ceros de Stagge et al. (2015), referencia [27], porque la gamma no esta
   definida en cero y Tilaran tiene meses de 0 mm en estacion seca.
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

import logging
import math

from scipy.stats import gamma, norm

log = logging.getLogger(__name__)

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
        meses: list[int] | None = None,
    ) -> list[float | None]:
        """
        Indice de Precipitacion Estandarizado por convolucion de ventana movil.

        Args:
            precipitacion: acumulado **mensual** de precipitacion en mm, con
                None en los meses sin dato. La serie entra cruda, sin filtrar
                (D-17).
            ventana_meses: 1 para SPI-1, 3 para SPI-3. El proyecto usa SPI-3
                para el umbral de sequia de `contratos/enums.py`.
            meses: mes calendario de cada posicion, de 1 a 12. **Con este dato
                la gamma se ajusta por separado para cada mes del anio**, que es
                lo que convierte al SPI en un indice de anomalia (D-19). Sin el,
                el ajuste es unico y el indice sigue la estacionalidad: ver la
                advertencia que se registra en ese caso.

        Returns:
            Una lista del mismo largo que la entrada. Las primeras
            `ventana_meses` posiciones son None porque no hay historia
            suficiente para calcularlas, y no se rellenan con ceros: un cero es
            un valor de sequia neutra que nadie calculo.

            Una posicion cuyo mes no reune muestra suficiente sale None, aunque
            su acumulado exista. Es preferible a mezclarla con la distribucion
            de otros meses.

        Raises:
            ValueError: si `ventana_meses` es menor que 1, si algun valor de
                precipitacion es negativo, o si `meses` no tiene el mismo largo
                que la serie o contiene valores fuera de 1 a 12.
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

        if meses is not None:
            _validar_meses(meses, len(precipitacion))

        acumulados = acumular(precipitacion, ventana_meses)

        if meses is None:
            log.warning(
                "SPI calculado sin el parametro 'meses': el ajuste es unico para toda "
                "la serie y el resultado NO es un indice de anomalia. En un clima con "
                "estacion seca marcada sigue la estacionalidad: medido sobre 35 anios "
                "sinteticos, los 99 meses declarados en sequia caian los 99 en estacion "
                "seca. No usar para etiquetar la variable objetivo. Ver D-19 y "
                "docs/investigacion/solicitud-cambio-spi-mes.md"
            )
            return self._ajuste_unico(acumulados, len(precipitacion))

        return self._ajuste_por_mes(acumulados, meses, len(precipitacion))

    # ----------------------------------------------------------------- internos

    def _ajuste_unico(
        self,
        acumulados: list[float | None],
        largo: int,
    ) -> list[float | None]:
        """Una sola gamma para toda la serie. Comportamiento previo a D-19."""
        muestra = [v for v in acumulados if v is not None]
        if len(muestra) < MINIMO_AJUSTE:
            # Sin muestra suficiente no se ajusta nada. Se devuelve todo None y
            # no ceros: la ausencia de resultado no es un resultado neutro.
            return [None] * largo

        forma, escala, prob_cero = ajustar_gamma(muestra)
        if forma is None:
            return [None] * largo

        return [
            None if v is None else _a_normal_estandar(v, forma, escala, prob_cero)
            for v in acumulados
        ]

    def _ajuste_por_mes(
        self,
        acumulados: list[float | None],
        meses: list[int],
        largo: int,
    ) -> list[float | None]:
        """
        Una gamma por mes calendario. Es el SPI de McKee (D-19).

        Cada acumulado se compara contra la distribucion historica **de su
        propio mes**: los eneros contra los eneros, los febreros contra los
        febreros. Eso descuenta la estacionalidad y deja solo la anomalia.

        **Respaldo en la guia de la OMM**, WMO-No. 1090, referencia [24],
        seccion 5.1.1: describe el SPI de 1 mes como la comparacion del total
        de noviembre de un ano dado contra los totales de noviembre de todos
        los anos del registro. El 5.1.2 dice lo equivalente para el trimestre
        diciembre-enero-febrero y el 5.1.5 para los doce meses consecutivos.

        Es descriptivo, no imperativo: la guia nunca escribe "ajustese por mes
        calendario". Pero define el conjunto de comparacion como el mismo mes
        del calendario a traves de los anos, que es lo que hace este metodo.
        La cita se limita a eso y no se estira mas alla.

        Un mes con menos de `MINIMO_AJUSTE` acumulados no se ajusta y sus
        posiciones salen None. No se recurre a la distribucion conjunta como
        respaldo: eso reintroduciria en ese mes exactamente el sesgo que este
        ajuste existe para eliminar, y lo haria de forma invisible.
        """
        salida: list[float | None] = [None] * largo

        for mes in range(1, 13):
            posiciones = [i for i in range(largo) if meses[i] == mes and acumulados[i] is not None]
            muestra = [acumulados[i] for i in posiciones]

            if len(muestra) < MINIMO_AJUSTE:
                continue

            forma, escala, prob_cero = ajustar_gamma(muestra)  # type: ignore[arg-type]
            if forma is None:
                continue

            for i in posiciones:
                salida[i] = _a_normal_estandar(
                    acumulados[i],  # type: ignore[arg-type]
                    forma,
                    escala,
                    prob_cero,
                )

        return salida


def _validar_meses(meses: list[int], largo_serie: int) -> None:
    """El mes de cada posicion debe existir y estar entre 1 y 12."""
    if len(meses) != largo_serie:
        raise ValueError(
            f"'meses' tiene {len(meses)} elementos y la serie {largo_serie}. "
            "Sin correspondencia uno a uno no se sabe a que mes pertenece cada "
            "acumulado, y asignarlo por posicion seria suponer que la serie "
            "empieza en enero y no tiene meses ausentes."
        )

    invalidos = sorted({m for m in meses if not 1 <= m <= 12})
    if invalidos:
        raise ValueError(f"Los meses deben estar entre 1 y 12; se recibieron {invalidos}")


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
    cero, y Tilaran tiene meses de 0,0 mm en estacion seca. Se usa una
    distribucion mixta: la probabilidad acumulada es H(x) = q + (1 - q) G(x),
    donde q es la proporcion de ceros de la muestra y G la gamma ajustada solo
    sobre los valores positivos. Descartar los ceros sin contarlos en q
    inflaria el indice en los climas con estacion seca, que es exactamente el
    caso de este canton.

    **Correccion de atribucion, 2026-08-22.** Una version anterior de este
    comentario atribuia la distribucion mixta a la guia de la OMM, WMO-No.
    1090. **Es falso.** Se leyo el documento completo, las 16 paginas: no
    contiene ninguna formula, y su seccion 6 remite explicitamente a McKee et
    al. (1993, 1995) y a Edwards y McKee (1997) para el procedimiento de
    calculo. La distribucion mixta no aparece ahi.

    La atribucion correcta es Stagge et al. (2015), referencia [27]. Ver la
    ficha de esa referencia para el alcance exacto de su verificacion, que es
    parcial y esta declarado.

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

    **El caso del acumulado cero: el estimador de centro de masa.**

    Con la distribucion mixta, en x = 0 se tiene G(0) = 0 y por lo tanto
    H(0) = q. La lectura directa seria entonces `ppf(q)`.

    Aqui se usa `ppf(q / 2)`, que es la variante de centro de masa: reparte la
    masa de probabilidad de los ceros en lugar de acumularla toda en su extremo
    superior, y evita la discontinuidad que produce usar q entre el ultimo cero
    y el primer valor positivo.

    **Atribucion, resuelta el 2026-08-22.** Es de Stagge et al. (2015),
    referencia [27]. Su forma exacta es (n0 + 1) / (2 (n + 1)), con n0 el
    numero de meses nulos y n el tamano de muestra.

    **Lo que se usa aqui es q / 2, que no es identico sino su limite cuando n
    es grande.** Con n0 / n = q, la expresion de Stagge tiende a q / 2 al
    crecer n; con los 35 anios de este proyecto la diferencia es despreciable,
    pero no son la misma formula y este comentario no las presenta como tal.

    **Alcance de la verificacion.** El articulo esta tras muro de pago y no se
    leyo. Lo que se leyo es la documentacion de `fitSCI` del paquete R `SCI`,
    firmada por Gudmundsson y Stagge, dos de los cinco autores, que atribuye el
    estimador a Stagge et al. y da la formula. Es la mejor confirmacion
    disponible, y no equivale a haber leido el articulo. Ver la ficha de [27].

    Con 35 anios y SPI-3 el efecto numerico entre `q` y `q / 2` es menor.
    """
    if acumulado <= 0:
        # Centro de masa de Stagge et al. (2015), ref. [27], en su forma limite
        # para n grande. Ver la nota del docstring.
        probabilidad = prob_cero / 2
    else:
        probabilidad = prob_cero + (1 - prob_cero) * gamma.cdf(acumulado, forma, scale=escala)

    probabilidad = min(max(probabilidad, 1e-4), 1 - 1e-4)

    return float(norm.ppf(probabilidad))
