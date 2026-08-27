"""
Regla de imputacion de faltantes. Dueno: Cesar. Historia H1.4.

QUE ES ESTO Y POR QUE EXISTE HOY

Las series de H1.1 **no tienen un solo faltante en 12 784 dias**: CHIRPS y POWER son
productos de malla, generados por interpolacion y reanalisis, completos por
construccion. D-22 redujo esta historia por eso, y conservo dos cosas:

  1. declarar la regla ANTES de necesitarla, con su prueba contra huecos inyectados
  2. fijar la distincion entre ausencia de evento y ausencia de dato

Una regla escrita antes de que aparezca el primer hueco es una decision; escrita
despues, es una racionalizacion de lo que ya se hizo.

Quien va a traer huecos de verdad es **Sentinel-2** (H1.6, de Avril), que descarta
imagenes con mas de 20 % de nubosidad. En estacion lluviosa van a ser muchos.

DE DONDE SALEN LOS DOS UMBRALES

**No son criterio del equipo.** WMO-No. 1203, *Guidelines on the Calculation of
Climate Normals*, edicion 2017, seccion 4.4.1(a): un valor mensual **no se calcula**
si faltan observaciones **11 o mas dias** del mes, o **5 o mas dias consecutivos**.

Si la OMM considera que cinco dias seguidos inutilizan el mes entero, imputar por
encima de ese umbral es fabricar dato con apariencia de medicion.

  AVISO DE PROCEDENCIA: library.wmo.int y el espejo del NOAA bloquean la descarga
  automatica, asi que la redaccion exacta se leyo de un espejo web y NO del PDF
  oficial. Hay que confirmarla contra el documento de la OMM antes de la defensa.

UN SOLO METODO DE LOS CUATRO DEL CONTRATO

`MetodoImputacion` declara cuatro valores y esta regla usa uno:
`INTERPOLACION_LINEAL`. `MEDIA_MOVIL` y `CLIMATOLOGIA_MENSUAL` quedan declarados y
sin uso **a proposito**: elegir entre ellos para huecos de dos a cuatro dias exigiria
un corte que ninguna fuente sostiene, y este proyecto no inventa umbrales -los de
incendio salen de la Tabla 10 del manual de MODIS y los de lluvia del ETCCDI-.

El dia que Sentinel-2 traiga huecos de semanas, donde interpolar entre dos extremos
separados por quince dias no significa nada, la climatologia mensual va a tener su
razon y su fuente. Hoy no la tiene.

LA DISTINCION EVENTO / DATO ES UN TIPO, NO UNA ADVERTENCIA

Con FIRMS, un dia sin focos **es un cero**, no un faltante. Imputarlo invertiria el
sentido del riesgo de incendio, que es la clase de defecto que D-07 existe para
evitar. Por eso `imputar` recibe la clase de serie y **se niega** a tocar una de
eventos.

Un documento que dice "no confundan estas dos cosas" se lee una vez. Una funcion que
lo impide, lo impide siempre, incluida la vez que alguien este apurado.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from contratos.enums import MetodoImputacion

# WMO-No. 1203, 4.4.1(a). "5 o mas dias consecutivos" inutiliza el mes, asi que el
# hueco mas largo que se puede imputar es de cuatro.
DIAS_CONSECUTIVOS_QUE_INUTILIZAN = 5

# WMO-No. 1203, 4.4.1(a). "11 o mas dias" faltantes en el mes.
FALTANTES_QUE_INUTILIZAN_EL_MES = 11


class ClaseDeSerie(Enum):
    """
    De que clase de producto viene la serie. **No es un detalle de formato.**

    MALLA    CHIRPS, POWER. Interpolacion y reanalisis sobre todo el dominio: un
             dia sin valor es un dato que falta.
    EVENTOS  FIRMS. Un dia sin deteccion **es un cero**, no un faltante. Que la
             fila no exista significa que no paso nada, no que no se sepa.
    """

    MALLA = "malla"
    EVENTOS = "eventos"


class SerieDeEventosNoSeImputa(ValueError):
    """
    Se intento imputar una serie de eventos.

    Hereda de `ValueError` porque es un error de uso, no un fallo del sistema: quien
    llama pidio algo que no tiene sentido para esa clase de dato.
    """


@dataclass(frozen=True)
class Punto:
    """Un dia de la serie, con la marca de si su valor fue imputado."""

    fecha: date
    valor: float | None
    imputado: bool = False
    metodo: MetodoImputacion = MetodoImputacion.SIN_IMPUTAR


def _faltantes_por_mes(serie: list[Punto]) -> dict[tuple[int, int], int]:
    cuenta: dict[tuple[int, int], int] = {}
    for punto in serie:
        if punto.valor is None:
            clave = (punto.fecha.year, punto.fecha.month)
            cuenta[clave] = cuenta.get(clave, 0) + 1
    return cuenta


def _huecos(serie: list[Punto]) -> list[tuple[int, int]]:
    """Tramos contiguos sin valor, como pares (primero, ultimo) de indices."""
    tramos: list[tuple[int, int]] = []
    inicio: int | None = None
    for i, punto in enumerate(serie):
        if punto.valor is None and inicio is None:
            inicio = i
        elif punto.valor is not None and inicio is not None:
            tramos.append((inicio, i - 1))
            inicio = None
    if inicio is not None:
        tramos.append((inicio, len(serie) - 1))
    return tramos


def _interpolar(anterior: Punto, siguiente: Punto, fecha: date) -> float:
    """
    Interpolacion lineal por distancia en dias, no por posicion en la lista.

    Si la serie tuviera dias ausentes en vez de dias con valor nulo, interpolar por
    posicion pondria el punto medio en la fecha equivocada. Por fecha, el resultado
    es el mismo cuando la serie es contigua y correcto cuando no lo es.
    """
    total = (siguiente.fecha - anterior.fecha).days
    recorrido = (fecha - anterior.fecha).days
    return anterior.valor + (siguiente.valor - anterior.valor) * recorrido / total


def imputar(serie: list[Punto], clase: ClaseDeSerie) -> list[Punto]:
    """
    Devuelve la serie con los huecos cortos imputados y los largos intactos.

    No modifica la entrada. Los puntos que no se imputan salen tal como entraron,
    con `valor=None`, `imputado=False` y `SIN_IMPUTAR`, que es lo que D-07 pide: la
    ausencia de dato se representa como nulo y nunca como cero ni como un valor
    plausible.

    **Toda imputacion queda marcada** con `imputado=True` y su metodo. D-07:
    "toda imputacion deliberada debe quedar marcada con su MetodoImputacion". Una
    imputacion no declarada se vuelve invisible aguas abajo.

    Levanta `SerieDeEventosNoSeImputa` si la serie es de eventos.
    """
    if clase is ClaseDeSerie.EVENTOS:
        raise SerieDeEventosNoSeImputa(
            "No se imputa una serie de eventos. En un producto de eventos como FIRMS, "
            "un dia sin deteccion ES UN CERO, no un dato que falta: imputarlo "
            "inventaria focos que nadie vio e invertiria el sentido del riesgo de "
            "incendio. La distincion la fija D-07 y la conserva D-22. Si lo que "
            "queres es rellenar los dias sin evento con cero, eso no es imputar: es "
            "completar la serie, y se hace al cargar."
        )

    salida = list(serie)
    faltantes = _faltantes_por_mes(serie)

    for inicio, fin in _huecos(serie):
        largo = fin - inicio + 1

        # WMO 4.4.1(a): cinco dias seguidos inutilizan el mes.
        if largo >= DIAS_CONSECUTIVOS_QUE_INUTILIZAN:
            continue

        # Sin vecino de alguno de los dos lados no hay entre que interpolar, y
        # extender el ultimo valor conocido seria inventar.
        if inicio == 0 or fin == len(serie) - 1:
            continue

        anterior, siguiente = serie[inicio - 1], serie[fin + 1]
        if anterior.valor is None or siguiente.valor is None:
            continue

        # WMO 4.4.1(a): once faltantes inutilizan el mes aunque cada hueco sea de un
        # solo dia. Un hueco puede tocar dos meses: si CUALQUIERA de los dos esta
        # inutilizado, no se imputa. Es el criterio conservador, y el que evita
        # imputar la primera mitad de un hueco y la segunda no.
        meses = {(serie[i].fecha.year, serie[i].fecha.month) for i in range(inicio, fin + 1)}
        if any(faltantes.get(mes, 0) >= FALTANTES_QUE_INUTILIZAN_EL_MES for mes in meses):
            continue

        for i in range(inicio, fin + 1):
            salida[i] = Punto(
                fecha=serie[i].fecha,
                valor=_interpolar(anterior, siguiente, serie[i].fecha),
                imputado=True,
                metodo=MetodoImputacion.INTERPOLACION_LINEAL,
            )

    return salida
