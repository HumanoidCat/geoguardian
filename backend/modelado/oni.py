"""
El indice ONI de la NOAA, leido de disco. Historia H3.10.

QUE ES Y POR QUE ENTRA

Para la vertiente pacifica de Costa Rica, **El Nino y La Nina son el motor de la
estacion seca**. Despues de H3.9 la matriz sabe **que mes** es -el par seno y
coseno del dia del anio- pero no sabe **que anio** es. El calendario dice «esto
es marzo»; el ONI dice «este marzo no es como los otros».

DE DONDE SALE, Y POR QUE DE ESTA FUENTE Y NO DE LA OTRA

`https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt`, el Climate Prediction
Center. Es la fuente **primaria**: es la tabla con la que NOAA declara
oficialmente El Nino y La Nina, con periodos base centrados de 30 anios que se
actualizan cada cinco.

**Hay otra fuente de NOAA que tambien se llama ONI y NO da los mismos numeros.**
`psl.noaa.gov/data/correlation/oni.data` es una redistribucion con otra
climatologia. Medido el 2026-09-14:

    1950 DJF    CPC -1.32    PSL -1.53
    1950 JFM    CPC -1.20    PSL -1.34

Dos archivos con el mismo nombre y distinto numero es exactamente como se cuela
un dato sin procedencia. Por eso la procedencia esta al lado del archivo, en
`procedencia-oni.md`, con fecha de descarga y suma SHA-256.

SE LEE DE DISCO, NUNCA DE LA RED

Es el **CA-2** de la historia, y el **CA-7**: la imagen `trabajos` de H11.7 corre
de madrugada sin nadie mirando. Si el indice se leyera por red y la red fallara,
la cadena entera caeria. El archivo versionado es la red de seguridad, y ademas
hace la corrida reproducible sin internet, que es algo que ninguna otra fuente de
este proyecto puede ofrecer.

**El ONI se revisa hacia atras**: la NOAA recalcula meses ya publicados. Por eso
el valor que se usa queda congelado en el archivo, con su fecha y su suma.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

#: El archivo versionado. Se lee de aca y de ningun otro lado.
ARCHIVO = Path(__file__).resolve().parent / "datos_oni" / "oni.ascii.txt"

#: Estacion de tres meses -> mes en el que esta **centrada**.
#:
#: EL ONI NO ES MENSUAL: es una media movil de tres meses, etiquetada por las
#: iniciales de esos tres. DJF es diciembre-enero-febrero y esta centrada en
#: **enero**; NDJ es noviembre-diciembre-enero y esta centrada en **diciembre**.
#: Asi cada anio trae exactamente doce estaciones y el mapeo a mes es uno a uno.
#:
#: El anio de la fila es el del mes central, no el del primer mes: `NDJ 1950`
#: usa noviembre y diciembre de 1950 y enero de 1951, y se le asigna diciembre
#: de 1950.
MES_DE_LA_ESTACION = {
    "DJF": 1,
    "JFM": 2,
    "FMA": 3,
    "MAM": 4,
    "AMJ": 5,
    "MJJ": 6,
    "JJA": 7,
    "JAS": 8,
    "ASO": 9,
    "SON": 10,
    "OND": 11,
    "NDJ": 12,
}

#: Los rezagos, **declarados antes de correr el arnes**. Es el CA-3.
#:
#: EL NOMBRE LLEVA LA UNIDAD A PROPOSITO. `backend/senales/caracteristicas.py`
#: exporta un `REZAGOS = (1, 2, 3, 7)` que esta **en dias**, y los dos modulos se
#: ven desde `generar_caracteristicas.py`. Dos constantes con el mismo nombre y
#: distinta unidad en el mismo archivo es un error que corre en silencio.
#:
#: MULTIPLOS DE TRES, Y NO ES ARBITRARIO. El indice ya es una media de tres
#: meses, asi que el valor de un mes y el del mes anterior **comparten dos de sus
#: tres meses**. Un rezago de 1 o de 2 no aporta una ventana nueva: aporta la
#: misma ventana corrida, y mete en el modelo columnas casi colineales -que es el
#: defecto que H3.9 ya tuvo que corregir al descartar `temp_min_c` y
#: `temp_media_c`-.
#:
#: Con 0, 3 y 6 las tres ventanas **no se solapan** y cubren los tres trimestres
#: anteriores al dia, que es donde la teleconexion del ENSO sobre la lluvia de
#: Centroamerica tiene efecto.
#:
#: **Probar rezagos hasta que salga bonito es sobreajustar al procedimiento.**
#: Esta lista se fija aca y no se toca despues de ver el resultado.
REZAGOS_MESES = (0, 3, 6)

#: El prefijo sigue la convencion de H3.9: los nombres terminan en la tabla de
#: coeficientes de H4.1 y ahi hay que poder leer de donde salio cada fila.
COLUMNAS_ONI = tuple(f"enso_oni_r{r}" if r else "enso_oni" for r in REZAGOS_MESES)

#: NO se agrega una columna de fase -Nino, Neutral, Nina-. El umbral de +-0,5 es
#: una **convencion para declarar eventos**, no una propiedad del clima: un
#: arbol puede encontrar su propio corte sobre el valor continuo, y una columna
#: categorica derivada del mismo numero seria redundante con el. Queda declarado
#: aca para que no parezca un olvido.
SIN_COLUMNA_DE_FASE = True

_FILA = re.compile(r"^\s*([A-Z]{3})\s+(\d{4})\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$")


class ErrorOni(RuntimeError):
    """El archivo del ONI no se puede usar tal como esta."""


def leer_oni(ruta: Path | None = None) -> dict[tuple[int, int], float]:
    """Devuelve {(anio, mes): anomalia} a partir del archivo del CPC.

    El archivo trae cuatro columnas -SEAS, YR, TOTAL, ANOM- y lo que se usa es
    **ANOM**, la anomalia. `TOTAL` es la temperatura absoluta de la region y no
    dice nada por si sola sin su climatologia.
    """
    ruta = ruta or ARCHIVO
    if not ruta.is_file():
        raise ErrorOni(
            f"No esta {ruta}. El indice se lee de disco y nunca de la red (CA-2, "
            "CA-7). Si falta, se baja con la orden de `procedencia-oni.md` y se "
            "vuelve a anotar su suma SHA-256."
        )

    valores: dict[tuple[int, int], float] = {}
    for numero, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
        if not linea.strip() or linea.lstrip().startswith("SEAS"):
            continue
        casa = _FILA.match(linea)
        if casa is None:
            raise ErrorOni(f"Linea {numero} no tiene la forma esperada: {linea!r}")

        estacion, anio, _total, anomalia = casa.groups()
        if estacion not in MES_DE_LA_ESTACION:
            raise ErrorOni(f"Linea {numero}: estacion desconocida {estacion!r}")

        clave = (int(anio), MES_DE_LA_ESTACION[estacion])
        if clave in valores:
            raise ErrorOni(f"Linea {numero}: {estacion} {anio} aparece dos veces")
        valores[clave] = float(anomalia)

    if not valores:
        raise ErrorOni(f"{ruta} no trajo ninguna fila.")
    return valores


def _mes_corrido(anio: int, mes: int, atras: int) -> tuple[int, int]:
    """(anio, mes) desplazado `atras` meses hacia el pasado."""
    total = anio * 12 + (mes - 1) - atras
    return total // 12, total % 12 + 1


def columnas_de(fecha: date, oni: dict[tuple[int, int], float]) -> dict[str, float]:
    """Las columnas del ENSO para una fecha, o revienta diciendo cual falta.

    NO DEVUELVE None NI CERO CUANDO FALTA UN MES, Y ESO ES A PROPOSITO. El
    estimador **no imputa**: una fila con una sola caracteristica nula no se usa
    ni para ajustar ni para predecir. Un ONI faltante se llevaria las filas de
    **los ocho distritos** de ese dia, en silencio y sin que ninguna cifra bajara
    de golpe. Es el mismo razonamiento con el que `agregar_contexto` de H3.9
    corta la corrida si a un distrito le falta la geometria.

    Un cero seria peor que un None: cero es «ENSO neutral», que es una
    afirmacion, y no «no se sabe».
    """
    salida: dict[str, float] = {}
    for rezago, nombre in zip(REZAGOS_MESES, COLUMNAS_ONI, strict=True):
        clave = _mes_corrido(fecha.year, fecha.month, rezago)
        if clave not in oni:
            raise ErrorOni(
                f"El ONI no tiene {clave[0]}-{clave[1]:02d}, que el rezago de "
                f"{rezago} meses necesita para {fecha}. Sin el, las filas de los "
                "ocho distritos de ese dia quedarian inservibles.\n"
                "El indice se publica con atraso: ver `atraso_meses()`. Para "
                "construir la matriz hasta donde el ONI alcanza, pasarle "
                "`--hasta` al generador con la fecha que devuelve "
                "`ultima_fecha_cubierta()`."
            )
        salida[nombre] = oni[clave]
    return salida


def agregar_enso(
    matriz: dict[tuple[str, date], dict[str, float | None]],
    oni: dict[tuple[int, int], float],
) -> dict[tuple[str, date], dict[str, float | None]]:
    """Le agrega a cada fila **que anio** es. Historia H3.10.

    SE APLICA ANTES DE `sin_columnas_constantes`, igual que `agregar_contexto`.
    Las columnas del ENSO son constantes **dentro de** un mes y distintas
    **entre** meses, asi que sobre la matriz entera no son constantes y ese
    filtro no se las lleva. Aplicarlo despues seria confiar en el orden por
    casualidad.

    EL VALOR SE REPITE EN TODOS LOS DIAS DE SU MES, Y EN LOS OCHO DISTRITOS. Eso
    no es hacer trampa: el indice describe el trimestre y el oceano Pacifico, no
    el dia ni el distrito. Pero hay que decirlo, porque el modelo va a ver la
    misma columna repetida unas 240 veces por mes -30 dias por 8 distritos- y eso
    **no son 240 observaciones independientes**. Es la misma razon por la que
    D-34 cuenta episodios a nivel canton.
    """
    for (_codigo, fecha), fila in matriz.items():
        fila.update(columnas_de(fecha, oni))
    return matriz


# --------------------------------------------------------------------------- #
# El atraso de publicacion. No es un detalle: es una limitacion operativa.      #
# --------------------------------------------------------------------------- #
#
# EL ONI NO ESTA DISPONIBLE PARA EL MES EN CURSO, Y NUNCA LO VA A ESTAR. El
# valor de un mes es la media de un trimestre centrado en el, asi que el
# trimestre **termina** mes y medio despues del centro, y recien entonces el CPC
# lo publica.
#
# Eso no se estima: se mide contra el archivo. Y hay que declararlo porque decide
# si el ENSO puede entrar a produccion: si el modelo usa el rezago 0, **no puede
# estimar los ultimos meses**, que son justamente los que a alguien operando el
# sistema le importan.


def ultimo_mes_con_dato(oni: dict[tuple[int, int], float]) -> tuple[int, int]:
    """El mes mas reciente que el archivo cubre."""
    return max(oni)


def atraso_meses(oni: dict[tuple[int, int], float], hoy: date) -> int:
    """Cuantos meses atras esta el ONI respecto de `hoy`. **Medido, no supuesto.**

    Es la cifra que el CA-7 de H3.10 necesita: una corrida programada que pida el
    ONI del mes en curso no lo va a encontrar, hoy ni nunca.
    """
    anio, mes = ultimo_mes_con_dato(oni)
    return (hoy.year * 12 + hoy.month) - (anio * 12 + mes)


def ultima_fecha_cubierta(oni: dict[tuple[int, int], float]) -> date:
    """El ultimo dia que se puede etiquetar con TODOS los rezagos declarados.

    Como el rezago mas chico es el que manda -mira el mes mas reciente- el limite
    lo pone el ultimo mes del archivo. Se devuelve su ultimo dia.
    """
    anio, mes = ultimo_mes_con_dato(oni)
    siguiente = (anio + 1, 1) if mes == 12 else (anio, mes + 1)
    return date(*siguiente, 1) - timedelta(days=1)
