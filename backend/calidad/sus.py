"""
Calculo del puntaje SUS. Historia H9.2a, rubrica OE4.

POR QUE ESTO ES CODIGO Y NO UNA CUENTA A MANO
---------------------------------------------

El SUS no se suma: se puntea distinto segun el item sea par o impar. Los impares
aportan `respuesta - 1` y los pares `5 - respuesta`, y el total se multiplica por
2,5.

Hacerlo a mano para cinco participantes son cincuenta restas alternadas, y un
error ahi **no lo detecta nadie despues**: el resultado sigue estando entre 0 y
100 y sigue pareciendo un puntaje. Por eso se calcula ejecutando y se prueba.

La regla es del instrumento original de Brooke, referencia `[7]`, y **no depende
de la traduccion**: la version en espanol validada de Sevilla-Gonzalez et al.,
ficha `[36]`, conserva el orden y el sentido de los diez items, que es
precisamente lo que la hace comparable.

EL PUNTAJE NO ES UN PORCENTAJE
------------------------------

Un 72 no significa "72 % de satisfaccion". Es una posicion en una escala de 0 a
100 que solo cobra sentido comparada contra valores de referencia. Por eso
`interpretar` devuelve la banda **y su advertencia**, y no un adjetivo suelto.
"""

from __future__ import annotations

from dataclasses import dataclass

# Los diez items del instrumento. No es configurable: cambiar la cantidad
# convierte el resultado en otra cosa que ya no se puede comparar.
CANTIDAD_DE_ITEMS = 10

# Escala de Likert de 1 a 5.
MINIMO, MAXIMO = 1, 5

# Bandas de interpretacion.
#
# **DEUDA DE VERIFICACION DECLARADA.** Estas dos cifras se tomaron de la ficha
# `[36]`, que si se leyo completa, y NO del texto de Bangor, Kortum y Miller,
# ficha `[13]`, que es la fuente primaria y no se ha leido directamente.
#
# Antes de que una banda concreta pase al documento IEEE hay que confirmarla
# contra Bangor et al. Es el mismo criterio que se aplico con WMO-No. 1090 en
# H2.3, donde leer la fuente completa cambio lo que se podia afirmar.
UMBRAL_BUENA = 68.0
UMBRAL_EXCELENTE = 85.0

# Por debajo de esto, el promedio no se reporta sin los valores individuales.
# H9.2 contempla de 3 a 5 participantes, asi que esto se activa siempre.
MUESTRA_SIN_PODER_ESTADISTICO = 20


@dataclass(frozen=True)
class Puntaje:
    """Resultado de un cuestionario. Inmutable: un puntaje calculado no se ajusta."""

    valor: float
    aporte_por_item: tuple[float, ...]

    def __str__(self) -> str:
        return f"{self.valor:.1f} / 100"


def puntuar(respuestas: list[int]) -> Puntaje:
    """
    Puntaje SUS de un cuestionario, de 0 a 100.

    Args:
        respuestas: las diez respuestas en orden, cada una de 1 a 5.

    Returns:
        El puntaje y el aporte de cada item, para poder auditar la cuenta.

    Raises:
        ValueError: si no son diez respuestas o si alguna cae fuera de 1 a 5.

    **No admite respuestas faltantes.** Un cuestionario incompleto no produce un
    puntaje parcial: produce un error. Rellenar el hueco con el punto medio
    seria inventar una respuesta que el participante no dio, y el instrumento
    perderia justamente lo que lo hace comparable.

    Si alguien deja un item en blanco, ese cuestionario se reporta como
    incompleto y se dice cuantos fueron.
    """
    _validar(respuestas)

    aportes = []
    for indice, respuesta in enumerate(respuestas):
        # Los items impares del instrumento (1, 3, 5, 7, 9) son afirmaciones
        # positivas y los pares negativas. La alternancia es deliberada: evita
        # el sesgo de quien responde en automatico marcando siempre la misma
        # columna. Por eso los items NO se pueden reordenar.
        es_impar = (indice + 1) % 2 == 1
        aportes.append(float(respuesta - MINIMO) if es_impar else float(MAXIMO - respuesta))

    return Puntaje(valor=sum(aportes) * 2.5, aporte_por_item=tuple(aportes))


def interpretar(valor: float) -> str:
    """
    Banda de interpretacion, con su advertencia.

    **Nunca devuelve un adjetivo solo.** Un "excelente" suelto se cita como si
    fuera un veredicto; la frase completa obliga a arrastrar de donde sale.
    """
    if not 0.0 <= valor <= 100.0:
        raise ValueError(f"Un puntaje SUS va de 0 a 100; se recibio {valor}")

    if valor >= UMBRAL_EXCELENTE:
        banda = "usabilidad excelente"
    elif valor >= UMBRAL_BUENA:
        banda = "usabilidad buena"
    else:
        banda = f"por debajo del umbral de {UMBRAL_BUENA:.0f}"

    return (
        f"{valor:.1f} / 100: {banda}. "
        "El puntaje NO es un porcentaje de satisfaccion. Las bandas salen de la "
        "ficha [36] y no del texto de [13], que es la fuente primaria y esta "
        "pendiente de verificar."
    )


def promediar(puntajes: list[Puntaje]) -> tuple[float, str]:
    """
    Promedio de varios cuestionarios, con la advertencia que corresponde.

    Returns:
        El promedio y una advertencia sobre el tamano de muestra.

    **Con 3 a 5 participantes el promedio es indicativo y no tiene poder
    estadistico.** Se devuelve junto a su advertencia y no solo, porque un
    numero sin ella se cita como si midiera algo que no mide.
    """
    if not puntajes:
        raise ValueError(
            "No hay puntajes que promediar. Un promedio de cero cuestionarios no "
            "es 0.0: no existe."
        )

    promedio = sum(p.valor for p in puntajes) / len(puntajes)

    if len(puntajes) < MUESTRA_SIN_PODER_ESTADISTICO:
        aviso = (
            f"Promedio de {len(puntajes)} participantes. **Indicativo, sin poder "
            f"estadistico**: con menos de {MUESTRA_SIN_PODER_ESTADISTICO} "
            "cuestionarios el promedio no sostiene una conclusion. Reportar "
            "SIEMPRE los puntajes individuales junto a este numero."
        )
    else:
        aviso = f"Promedio de {len(puntajes)} participantes."

    return promedio, aviso


def _validar(respuestas: list[int]) -> None:
    if len(respuestas) != CANTIDAD_DE_ITEMS:
        raise ValueError(
            f"El SUS tiene {CANTIDAD_DE_ITEMS} items y se recibieron "
            f"{len(respuestas)} respuestas. Un cuestionario incompleto no produce "
            "un puntaje parcial: rellenar el hueco seria inventar una respuesta."
        )

    fuera = [
        (posicion + 1, valor)
        for posicion, valor in enumerate(respuestas)
        if not MINIMO <= valor <= MAXIMO
    ]
    if fuera:
        detalle = ", ".join(f"item {p} vale {v}" for p, v in fuera)
        raise ValueError(f"Las respuestas van de {MINIMO} a {MAXIMO}: {detalle}")
