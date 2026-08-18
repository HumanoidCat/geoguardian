"""
Filtrado de ruido de series climaticas. Historia H2.1.

Implementa `filtrar_ruido` del contrato `contratos/senales.py`.

Por que Savitzky-Golay y no una media movil: la media movil aplasta los
maximos, y en este proyecto los maximos no son ruido, son la senal. Los
umbrales de lluvia intensa se definen sobre los percentiles P95 y P99 de la
precipitacion acumulada, asi que achatar los picos sesga los umbrales hacia
abajo de forma sistematica. Savitzky-Golay ajusta un polinomio local por minimos
cuadrados y conserva la altura y el ancho de los extremos mucho mejor.

La justificacion completa, incluida la discusion sobre a que variables
corresponde aplicar el filtro y a cuales no, esta en
`docs/evidencias/senales-y-sistemas/H2.1-filtro-ruido.md`.
"""

from __future__ import annotations

from scipy.signal import savgol_filter

# Valores por defecto. La justificacion de cada uno esta en la evidencia.
VENTANA_POR_DEFECTO = 7  # una semana de datos diarios
ORDEN_POLINOMIO = 2


class FiltroSavitzkyGolay:
    """
    Suavizado que preserva los maximos y los huecos.

    Cumple el protocolo `ProcesadorSenales` en su metodo `filtrar_ruido`. Los
    demas metodos del protocolo los implementan otras historias: `espectro` en
    H2.2, `spi` en H2.3, `anomalia` en H2.4 y `remuestrear` en H2.6.
    """

    def __init__(self, orden: int = ORDEN_POLINOMIO) -> None:
        if orden < 1:
            raise ValueError(f"El orden del polinomio debe ser al menos 1, se recibio {orden}")
        self.orden = orden

    def filtrar_ruido(
        self,
        serie: list[float | None],
        ventana: int = VENTANA_POR_DEFECTO,
    ) -> list[float | None]:
        """
        Suaviza la serie preservando los huecos.

        Una posicion que entra como None sale como None, sin excepcion. El
        filtro no rellena: rellenar aqui escondería la falta de dato al resto
        del sistema y H1.5 no podria reportarla.

        Los tramos continuos de datos presentes se suavizan por separado. Un
        hueco corta el tramo: no se interpola a traves de el, porque hacerlo
        inventaria una transicion suave donde lo que hay es ausencia de
        medicion.

        Un tramo mas corto que la ventana se devuelve sin filtrar en lugar de
        filtrarse con una ventana reducida. Es deliberado: cambiar la ventana
        segun el tramo produciria un suavizado no uniforme a lo largo de la
        serie, y dos tramos vecinos quedarian tratados con criterios distintos.

        Args:
            serie: valores diarios, con None en los dias sin medicion.
            ventana: numero de muestras del filtro. Debe ser impar y mayor que
                el orden del polinomio.

        Returns:
            Una lista del mismo largo que la entrada, con None exactamente en
            las mismas posiciones.

        Raises:
            ValueError: si la ventana es par, o si no es mayor que el orden del
                polinomio.
        """
        if ventana % 2 == 0:
            raise ValueError(
                f"La ventana debe ser impar para que el filtro este centrado, "
                f"se recibio {ventana}"
            )
        if ventana <= self.orden:
            raise ValueError(
                f"La ventana ({ventana}) debe ser mayor que el orden del "
                f"polinomio ({self.orden}); si no, el ajuste no esta determinado"
            )

        salida: list[float | None] = list(serie)

        for desde, hasta in _tramos_continuos(serie):
            largo = hasta - desde
            if largo < ventana:
                # Tramo demasiado corto: se devuelve tal cual. Ver el docstring.
                continue

            tramo = [float(v) for v in serie[desde:hasta]]  # type: ignore[arg-type]
            suavizado = savgol_filter(tramo, window_length=ventana, polyorder=self.orden)
            salida[desde:hasta] = [float(v) for v in suavizado]

        return salida


def _tramos_continuos(serie: list[float | None]) -> list[tuple[int, int]]:
    """
    Indices de los tramos sin huecos, como pares [desde, hasta).

    Se filtra tramo por tramo en lugar de toda la serie de una vez porque
    Savitzky-Golay necesita muestras contiguas: aplicarlo sobre una serie con
    huecos rellenados, o sobre los valores presentes concatenados ignorando las
    fechas, produciria un suavizado que mezcla dias no vecinos.
    """
    tramos: list[tuple[int, int]] = []
    inicio: int | None = None

    for i, valor in enumerate(serie):
        if valor is None:
            if inicio is not None:
                tramos.append((inicio, i))
                inicio = None
        elif inicio is None:
            inicio = i

    if inicio is not None:
        tramos.append((inicio, len(serie)))

    return tramos
