"""
Procesador de senales simulado. Dueno: Alejandro. Cumple contratos/senales.py.

POR QUE EXISTE

El plan de pruebas H10.1 planifica seis casos sobre `ProcesadorSenales` que no se
podian implementar porque el contrato no tenia simulado. Este archivo los
desbloquea: Luna puede escribir y correr esas pruebas antes de que exista
`backend/senales`, y las mismas funciones de prueba deben pasar despues contra el
modulo real.

QUE ES Y QUE NO ES

Las operaciones son reales, no devuelven valores inventados: el filtro filtra de
verdad y la transformada es una transformada de verdad. Lo que es simulado es la
ELECCION DEL METODO, que en el modulo real sera distinta y esta documentada abajo
caso por caso.

**El SPI de aqui no es el SPI.** Ver la nota en `spi()`. No se debe usar para
ningun resultado que vaya al documento.

SIN DEPENDENCIAS EXTERNAS

El trabajo `contratos` del CI instala solo pydantic, asi que aqui no se puede
importar numpy ni scipy. La transformada esta escrita a mano por eso, no por
gusto. El modulo real de H2.2 si usa scipy.
"""

from __future__ import annotations

import cmath
import logging
import math

log = logging.getLogger(__name__)

# Un ano de datos diarios. Sirve para que `espectro` pueda anunciar donde deberia
# aparecer el ciclo anual sin que quien lo consume tenga que calcularlo.
DIAS_POR_ANO = 365.25

_AGREGACIONES = ("suma", "media", "max", "min")


def _sin_huecos(serie: list[float | None]) -> list[float]:
    """Devuelve la serie como floats, o lanza ValueError diciendo cuantos faltan."""
    faltantes = sum(1 for v in serie if v is None)
    if faltantes:
        raise ValueError(
            f"La serie tiene {faltantes} valores faltantes de {len(serie)}. "
            "Interpolar en silencio antes de una transformada introduce componentes "
            "espectrales que no estan en el dato. Imputar es una decision explicita: "
            "ver la historia H1.4."
        )
    return [float(v) for v in serie]


def _fft(muestras: list[complex]) -> list[complex]:
    """
    Transformada rapida de Fourier, Cooley-Tukey iterativo de base 2.

    Requiere que la longitud sea potencia de dos; de eso se encarga quien llama.
    Escrita a mano porque este paquete no puede depender de numpy.
    """
    n = len(muestras)
    if n <= 1:
        return muestras

    # Reordenamiento por inversion de bits.
    salida = muestras[:]
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j |= bit
        if i < j:
            salida[i], salida[j] = salida[j], salida[i]

    # Mariposas.
    longitud = 2
    while longitud <= n:
        paso = cmath.exp(-2j * math.pi / longitud)
        for inicio in range(0, n, longitud):
            w = 1 + 0j
            for k in range(inicio, inicio + longitud // 2):
                par = salida[k]
                impar = salida[k + longitud // 2] * w
                salida[k] = par + impar
                salida[k + longitud // 2] = par - impar
                w *= paso
        longitud <<= 1

    return salida


class ProcesadorSenalesSimulado:
    """
    Cumple el protocolo ProcesadorSenales. Determinista: no usa azar en ninguna
    operacion, asi que dos corridas con la misma entrada dan lo mismo.
    """

    nombre = "SIMULADO-senales"

    def __init__(self) -> None:
        log.warning(
            "ProcesadorSenalesSimulado en uso: los metodos son simplificaciones, "
            "no el procesamiento real de H2.x"
        )

    # ----------------------------------------------------------------- filtrado

    def filtrar_ruido(
        self,
        serie: list[float | None],
        ventana: int,
    ) -> list[float | None]:
        """
        Media movil centrada que preserva los huecos.

        Una posicion que entra como None sale como None, siempre: el filtro no
        rellena. Rellenar aqui escondaria la falta de dato al resto del sistema y
        H1.5 no podria reportarla.

        Los valores presentes se promedian solo con los valores presentes de su
        ventana. Al inicio y al final la ventana se recorta en lugar de asumir
        ceros, que introducirian un descenso artificial en los extremos.

        Simulacion: el modulo real de H2.2 usara un filtro de Savitzky-Golay,
        que preserva mejor los maximos de precipitacion.
        """
        if ventana < 1:
            raise ValueError(f"La ventana debe ser al menos 1, se recibio {ventana}")

        n = len(serie)
        radio = ventana // 2
        salida: list[float | None] = []

        for i in range(n):
            if serie[i] is None:
                salida.append(None)
                continue

            desde = max(0, i - radio)
            hasta = min(n, i + radio + 1)
            presentes = [v for v in serie[desde:hasta] if v is not None]
            salida.append(sum(presentes) / len(presentes))

        return salida

    # ---------------------------------------------------------------- espectro

    def espectro(
        self,
        serie: list[float | None],
        frecuencia_muestreo: float,
    ) -> tuple[list[float], list[float]]:
        """
        Analisis en el dominio de la frecuencia. Devuelve (frecuencias, magnitudes).

        Rechaza series con huecos, como exige el contrato.

        Dos decisiones que afectan el resultado y conviene conocer:

        1. **Se resta la media antes de transformar.** Sin eso la componente de
           frecuencia cero domina el espectro por completo y "la magnitud
           dominante" seria siempre esa, que no dice nada del ciclo anual.
        2. **Se rellena con ceros hasta la siguiente potencia de dos.** Es lo que
           permite usar una transformada rapida en vez de una directa, que sobre
           diez anos de datos diarios tardaria minutos en Python puro. El relleno
           no agrega informacion: interpola el espectro, no lo cambia.

        Se devuelve solo la mitad util del espectro, hasta la frecuencia de
        Nyquist: la otra mitad es su reflejo para una senal real.

        AVISO PARA QUIEN ESCRIBA LA PRUEBA DEL CICLO ANUAL

        La resolucion en frecuencia es `frecuencia_muestreo / N`, donde N es la
        longitud despues del relleno. Con cuatro anos de datos diarios, N vale
        2048 y los dos casilleros vecinos al ciclo anual caen en 341 y 410 dias:
        **el pico dominante sale en 341 dias, no en 365, y eso es correcto.** No
        es un defecto del filtro ni de los datos, es donde cae el casillero.

        Por eso una prueba del tipo `assert abs(periodo - 365) < 1` falla siempre.
        Lo robusto es comprobar que el casillero dominante es el mas cercano a la
        frecuencia anual:

            frecuencias, magnitudes = procesador.espectro(serie, 1.0)
            dominante = max(range(1, len(magnitudes)), key=lambda i: magnitudes[i])
            esperado = min(
                range(1, len(frecuencias)),
                key=lambda i: abs(frecuencias[i] - 1 / DIAS_POR_ANO),
            )
            assert dominante == esperado

        Cuanto mas larga la serie, mas fino el casillero y mas cerca de 365 queda.
        """
        if frecuencia_muestreo <= 0:
            raise ValueError(
                f"La frecuencia de muestreo debe ser positiva, se recibio {frecuencia_muestreo}"
            )

        valores = _sin_huecos(serie)
        n = len(valores)
        if n < 2:
            raise ValueError(f"Hacen falta al menos 2 muestras para un espectro, hay {n}")

        media = sum(valores) / n
        centrada = [v - media for v in valores]

        tamano = 1 << (n - 1).bit_length()
        centrada.extend([0.0] * (tamano - n))

        transformada = _fft([complex(v, 0.0) for v in centrada])

        mitad = tamano // 2
        frecuencias = [k * frecuencia_muestreo / tamano for k in range(mitad)]
        magnitudes = [abs(transformada[k]) * 2.0 / n for k in range(mitad)]

        return frecuencias, magnitudes

    # --------------------------------------------------------------------- SPI

    def spi(
        self,
        precipitacion: list[float | None],
        ventana_meses: int,
    ) -> list[float | None]:
        """
        Aproximacion al Indice de Precipitacion Estandarizado.

        **ESTE NO ES EL SPI.** El SPI de McKee, Doesken y Kleist (1993) ajusta una
        distribucion gamma a los acumulados y despues la transforma a normal
        estandar. Aqui se calcula una simple puntuacion z sobre los acumulados,
        que es otra cosa: la precipitacion acumulada tiene sesgo positivo fuerte y
        una z asume simetria.

        La diferencia importa donde mas duele, en las colas, que es justo donde se
        declara la sequia. Un valor de -1.5 de aqui no significa lo mismo que un
        SPI de -1.5, y los umbrales de `contratos/enums.py` estan escritos contra
        el SPI de verdad.

        Sirve para probar la FORMA del resultado: longitud, posicion de los nulos y
        que no se rellenen huecos. No sirve para ningun numero que vaya al
        documento. El calculo real es la historia H2.3 y usa scipy.

        Las primeras `ventana_meses` posiciones salen None porque no hay historia
        suficiente, y no se rellenan con ceros: un cero seria un valor de sequia
        neutra que nadie calculo.
        """
        if ventana_meses < 1:
            raise ValueError(f"La ventana debe ser al menos 1 mes, se recibio {ventana_meses}")

        n = len(precipitacion)
        acumulados: list[float | None] = [None] * n

        for i in range(ventana_meses - 1, n):
            trozo = precipitacion[i - ventana_meses + 1 : i + 1]
            if any(v is None for v in trozo):
                acumulados[i] = None
            else:
                acumulados[i] = sum(v for v in trozo if v is not None)

        # Las primeras `ventana_meses` posiciones son None por definicion del
        # indice, aunque la ventana ya estuviera completa en la posicion
        # ventana_meses - 1.
        for i in range(min(ventana_meses, n)):
            acumulados[i] = None

        presentes = [v for v in acumulados if v is not None]
        if len(presentes) < 2:
            return [None] * n

        media = sum(presentes) / len(presentes)
        varianza = sum((v - media) ** 2 for v in presentes) / (len(presentes) - 1)
        desviacion = math.sqrt(varianza)

        if desviacion == 0:
            # Serie constante: no hay anomalia posible. Se devuelve None y no 0.0,
            # porque cero es un valor de indice, no una ausencia de resultado.
            return [None] * n

        return [None if v is None else (v - media) / desviacion for v in acumulados]

    # --------------------------------------------------------------- anomalia

    def anomalia(
        self,
        serie: list[float | None],
        normal_por_mes: dict[int, float],
    ) -> list[float | None]:
        """
        Desviacion respecto a la normal climatologica 1991-2020.

        Si falta el mes en `normal_por_mes`, esa posicion sale None: no se
        sustituye por el promedio de los meses que si estan.

        HUECO DEL CONTRATO, REGISTRADO Y NO RESUELTO AQUI

        El contrato no recibe fechas, solo la serie y las normales por mes, de modo
        que no hay forma inequivoca de saber a que mes corresponde cada posicion.
        Este simulado asume que la serie es MENSUAL y ARRANCA EN ENERO, es decir
        que la posicion i es el mes (i mod 12) + 1.

        Esa suposicion es fragil y no esta en el contrato. Si la serie empieza en
        otro mes, o es diaria, el resultado es silenciosamente incorrecto: no falla,
        devuelve numeros equivocados, que es el peor modo de fallo posible.

        Corregirlo exige cambiar la firma para que reciba las fechas, y eso es una
        solicitud de cambio sobre un contrato congelado. Queda anotado en
        docs/02-contratos.md para la proxima version.
        """
        salida: list[float | None] = []

        for i, valor in enumerate(serie):
            if valor is None:
                salida.append(None)
                continue

            mes = (i % 12) + 1
            normal = normal_por_mes.get(mes)
            salida.append(None if normal is None else valor - normal)

        return salida

    # ------------------------------------------------------------ remuestreo

    def remuestrear(
        self,
        serie: list[float | None],
        factor: int,
        agregacion: str,
    ) -> list[float | None]:
        """
        Cambia la frecuencia de muestreo agrupando de `factor` en `factor`.

        Una ventana con MAS DE LA MITAD de valores faltantes produce None. Es la
        regla que evita que un promedio de dos dias se presente con la misma
        autoridad que uno de treinta.

        Una ventana con exactamente la mitad presente SI se agrega: el contrato
        dice "mas de la mitad", y el limite se documenta aqui porque es
        exactamente el tipo de borde que despues nadie recuerda.
        """
        if factor < 1:
            raise ValueError(f"El factor debe ser al menos 1, se recibio {factor}")
        if agregacion not in _AGREGACIONES:
            raise ValueError(
                f"Agregacion '{agregacion}' no reconocida. Las validas son: "
                f"{', '.join(_AGREGACIONES)}"
            )

        salida: list[float | None] = []

        for inicio in range(0, len(serie), factor):
            ventana = serie[inicio : inicio + factor]
            presentes = [v for v in ventana if v is not None]
            faltantes = len(ventana) - len(presentes)

            # "Mas de la mitad faltantes" -> None. Con la mitad justa se agrega.
            if not presentes or faltantes * 2 > len(ventana):
                salida.append(None)
            elif agregacion == "suma":
                salida.append(sum(presentes))
            elif agregacion == "media":
                salida.append(sum(presentes) / len(presentes))
            elif agregacion == "max":
                salida.append(max(presentes))
            else:
                salida.append(min(presentes))

        return salida
