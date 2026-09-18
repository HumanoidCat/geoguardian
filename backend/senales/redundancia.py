"""Redundancia entre las columnas de la matriz de caracteristicas. Historia H2.6.

===========================================================================
QUE MIDE, Y POR QUE NO ALCANZA CON LA CORRELACION
===========================================================================

`generar_caracteristicas.py` documenta seis descartes de variables. Cuatro de
ellos son razonamientos sin cifra. Este modulo les pone la cifra.

Mide tres cosas distintas sobre la matriz que consume el modelo:

  1. **Variacion espacial.** Para cada columna, en que fraccion de los dias los
     ocho distritos tienen al menos dos valores distintos. Una columna que da el
     mismo numero en los ocho no distingue distritos, y el sistema promete
     estimar riesgo POR distrito.

  2. **Redundancia exacta.** Pares donde una columna es `a*x + b` de la otra,
     **comprobado fila por fila**, no en promedio.

  3. **Redundancia alta.** Pares con `|r|` sobre el umbral pero sin relacion
     exacta. Se reportan y **no** se descartan: cuanto se pierde al quitar una
     columna con `r = 0.96` es una medicion de desempeno, y esa es del arnes de
     H3.6.

**La correlacion sola no sirve para declarar redundancia, y la matriz tiene el
contraejemplo adentro.** `cal_seno` y `cal_coseno` cumplen `sen^2 + cos^2 = 1`,
que es una dependencia funcional perfecta, y su correlacion lineal no es 1. Son
el caso donde la dependencia es deliberada: es lo que hace que el 31 de diciembre
y el 1 de enero queden pegados. Por eso todo par candidato pasa **dos**
comprobaciones y no una.

Y al reves: la correlacion **solo ve redundancia lineal**. Este modulo no barre
dependencias no lineales, y decirlo es parte del resultado.

===========================================================================
EL CSV REDONDEA A SEIS CIFRAS, Y ESO CAMBIA LA TOLERANCIA
===========================================================================

`generar_caracteristicas.escribir()` formatea cada celda con `%.6g`: **seis
cifras significativas**. Asi que una relacion que aguas arriba es exacta -por
ejemplo una media movil que es su acumulado dividido entre n- llega a este
modulo con un error relativo del orden de 1e-6.

Eso no es un defecto del CSV: es el archivo que el modelo consume de verdad, y
medir sobre el es lo que pide el CA-3. Pero obliga a dos cosas:

  - La tolerancia no puede ser `1e-12`, porque ninguna relacion exacta la
    pasaria, y se leeria como «no hay redundancia» cuando la hay.
  - **El residuo maximo observado se imprime siempre**, en vez de esconderse
    detras de un umbral. Un par que pasa con residuo 8e-07 y uno que pasa con
    residuo 9e-06 no son lo mismo, y quien lea el informe tiene que poder verlo.

===========================================================================
POR QUE NO USA pandas NI numpy
===========================================================================

Por lo mismo que `caracteristicas.py`: el resto de `backend/senales` no depende
de pandas, y agregarlo obligaria a una solicitud de cambio sobre
`requirements.txt`, que es archivo compartido.

No hace falta. Las parejas de la matriz -unos cientos, porque son unas decenas de
columnas- se calculan centrando cada columna en una sola pasada y multiplicando
los vectores con `map(operator.mul, ...)`, que corre en C. Sobre la matriz
completa son segundos.

Uso:
    python -m backend.senales.redundancia
    python -m backend.senales.redundancia --salida <archivo fuera del repositorio>
    python -m backend.senales.redundancia --temperaturas     # necesita PostgreSQL
"""

from __future__ import annotations

import argparse
import csv
import operator
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from math import sqrt
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

MATRIZ = RAIZ / "datos" / "procesados" / "caracteristicas.csv"

#: Umbral de redundancia ALTA. Declarado en los criterios ANTES de ver la tabla,
#: que es el punto: un umbral elegido despues de mirar los numeros es el numero
#: eligiendose a si mismo.
UMBRAL_ALTO = 0.95

#: Tolerancia relativa para declarar una relacion afin exacta.
#:
#: Sale del formato del CSV y no de la intuicion. `%.6g` deja seis cifras
#: significativas, o sea un error relativo de hasta 5e-07 por celda; la
#: diferencia entre dos celdas asi puede llegar al orden de 1e-06. Se toma un
#: orden de margen. El residuo real se imprime igual, para que el umbral no
#: tenga la ultima palabra.
TOLERANCIA = 1e-5

COLUMNAS_LLAVE = ("codigo_distrito", "fecha")


@dataclass(frozen=True)
class Fila:
    codigo: str
    fecha: date
    valores: dict[str, float]


@dataclass(frozen=True)
class Par:
    """Un par de columnas relacionadas, con todo lo que hizo falta para decirlo."""

    a: str
    b: str
    r: float
    #: `b = pendiente * a + corte`, cuando la relacion afin se verifico fila a fila.
    pendiente: float | None = None
    corte: float | None = None
    #: El peor residuo relativo encontrado. Se imprime aunque el par pase.
    residuo: float | None = None

    @property
    def exacta(self) -> bool:
        return self.pendiente is not None

    def relacion(self) -> str:
        if not self.exacta:
            return f"|r| = {abs(self.r):.4f}"
        corte = "" if abs(self.corte) < 1e-12 else f" + {self.corte:.6g}"
        return f"{self.b} = {self.pendiente:.6g} * {self.a}{corte}"


# ===========================================================================
# LECTURA
# ===========================================================================


def leer_matriz(origen: Path) -> tuple[list[str], list[Fila]]:
    """Lee el CSV de `generar_caracteristicas`. Las celdas vacias se OMITEN.

    Omitirlas y no ponerlas en 0.0 es D-07 y es lo mismo que hace
    `generar_caracteristicas.leer()`: cero milimetros de lluvia es una medicion y
    ausencia de dato no lo es. Una media movil de precipitacion vale cero muy
    seguido, asi que confundirlos no se notaria en ningun promedio.
    """
    filas: list[Fila] = []
    with origen.open(encoding="utf-8", newline="") as archivo:
        lector = csv.DictReader(archivo)
        if lector.fieldnames is None:
            raise ValueError(f"{origen} no tiene encabezado.")
        columnas = [c for c in lector.fieldnames if c not in COLUMNAS_LLAVE]
        for cruda in lector:
            filas.append(
                Fila(
                    codigo=cruda["codigo_distrito"],
                    fecha=date.fromisoformat(cruda["fecha"]),
                    valores={c: float(cruda[c]) for c in columnas if cruda[c] != ""},
                )
            )
    return columnas, filas


def filas_completas(filas: list[Fila], columnas: list[str]) -> list[Fila]:
    """Las filas que tienen TODAS las columnas. Son las unicas que el modelo usa.

    El estimador no imputa: una fila a la que le falte una sola celda no se usa
    ni para ajustar ni para predecir. Medir correlaciones sobre el subconjunto
    que cada par tenga completo daria 496 coeficientes calculados sobre 496
    poblaciones distintas, que no se pueden comparar entre si ni con el
    desempeno.
    """
    total = len(columnas)
    return [f for f in filas if len(f.valores) == total]


def como_vectores(filas: list[Fila], columnas: list[str]) -> dict[str, list[float]]:
    """Una lista de floats por columna, alineadas fila a fila."""
    return {c: [f.valores[c] for f in filas] for c in columnas}


# ===========================================================================
# LAS DOS COMPROBACIONES
# ===========================================================================


def _centrada(x: list[float]) -> tuple[list[float], float]:
    """La columna menos su media, y su norma. Es la mitad de un coeficiente.

    SE CENTRA ANTES DE MULTIPLICAR, Y NO ES UN CAPRICHO. La forma corta de
    Pearson -`n*Sxy - Sx*Sy` sobre raices del mismo estilo- resta dos numeros
    grandes y casi iguales, y sobre cien mil filas eso deja al coeficiente con
    error suficiente para **pasarse de 1**. La primera corrida de este modulo
    imprimio `r = 1.0000000172`, que no es un valor posible y en un informe se
    lee como un defecto del calculo.

    Centrar primero cuesta una pasada mas por columna y quita el problema de
    raiz. Las columnas se centran **una vez** y se reusan en las 496 parejas.
    """
    media = sum(x) / len(x)
    centrada = [v - media for v in x]
    return centrada, sqrt(sum(map(operator.mul, centrada, centrada)))


def _coeficiente(cx: list[float], nx: float, cy: list[float], ny: float) -> float | None:
    if nx <= 0 or ny <= 0:
        return None
    r = sum(map(operator.mul, cx, cy)) / (nx * ny)
    # Aun centrado quedan ulps: se acota al rango que el coeficiente tiene.
    return max(-1.0, min(1.0, r))


def correlacion(x: list[float], y: list[float]) -> float | None:
    """Pearson. Devuelve None si alguna de las dos es constante.

    Una columna constante no tiene correlacion definida -la desviacion es cero y
    el coeficiente seria una division por cero-. Devolver None y no 0.0 importa:
    un 0.0 se leeria como «no se parecen», y lo que pasa es que la pregunta no
    aplica. Las constantes sobre toda la matriz ya las quita
    `sin_columnas_constantes()`, pero una columna puede volverse constante al
    quedarse solo con las filas completas, y ahi este caso aparece.
    """
    if len(x) < 2:
        return None
    cx, nx = _centrada(x)
    cy, ny = _centrada(y)
    return _coeficiente(cx, nx, cy, ny)


def matriz_de_correlaciones(
    vectores: dict[str, list[float]], columnas: list[str]
) -> dict[tuple[str, str], float | None]:
    """Las 496 parejas, centrando cada columna UNA vez.

    Calcular cada pareja con `correlacion()` centraria 992 veces las mismas 32
    columnas. Sobre cien mil filas eso es la diferencia entre segundos y
    minutos, y el resultado es el mismo.
    """
    centradas = {c: _centrada(vectores[c]) for c in columnas}
    salida: dict[tuple[str, str], float | None] = {}
    for i, a in enumerate(columnas):
        cx, nx = centradas[a]
        for b in columnas[i + 1 :]:
            cy, ny = centradas[b]
            salida[(a, b)] = _coeficiente(cx, nx, cy, ny)
    return salida


def relacion_afin(
    x: list[float], y: list[float], tolerancia: float = TOLERANCIA
) -> tuple[float, float, float] | None:
    """Si `y = a*x + b` en TODAS las filas. Devuelve `(a, b, residuo_maximo)`.

    La pendiente y el corte se derivan de los dos puntos mas separados en `x`
    -no de un ajuste por minimos cuadrados- y despues se **verifican fila por
    fila**. La diferencia no es cosmetica: un ajuste siempre devuelve una recta,
    incluso para una nube sin ninguna relacion, y el error cuadratico medio puede
    ser chico mientras una sola fila se sale por completo. Una relacion exacta
    tiene que valer en todas.

    Se usan los dos extremos en `x` y no dos filas cualesquiera porque dos puntos
    casi pegados dan una pendiente dominada por el redondeo del CSV.

    El residuo es **relativo**, porque las columnas de esta matriz viven en
    escalas muy distintas: un acumulado de 30 dias de lluvia llega a cientos de
    milimetros y un seno vale entre -1 y 1. Una tolerancia absoluta seria
    generosa con una y severa con la otra.
    """
    if len(x) < 2:
        return None
    i_min = min(range(len(x)), key=x.__getitem__)
    i_max = max(range(len(x)), key=x.__getitem__)
    if x[i_max] - x[i_min] <= 0:
        return None  # x es constante: no hay recta que derivar

    pendiente = (y[i_max] - y[i_min]) / (x[i_max] - x[i_min])
    corte = y[i_min] - pendiente * x[i_min]

    peor = 0.0
    for xi, yi in zip(x, y, strict=True):
        esperado = pendiente * xi + corte
        escala = max(1.0, abs(yi), abs(esperado))
        residuo = abs(yi - esperado) / escala
        if residuo > peor:
            peor = residuo
            if peor > tolerancia:
                return None
    return pendiente, corte, peor


def pares_relacionados(
    vectores: dict[str, list[float]],
    columnas: list[str],
    umbral: float = UMBRAL_ALTO,
    tolerancia: float = TOLERANCIA,
) -> tuple[list[Par], list[Par]]:
    """Devuelve `(exactos, altos)`, cada uno ordenado de mas a menos relacionado.

    Un par exacto NO aparece tambien en la lista de altos: son dos decisiones
    distintas -uno se descarta, el otro solo se reporta- y repetirlo invitaria a
    contar dos veces la misma columna.
    """
    coeficientes = matriz_de_correlaciones(vectores, columnas)
    exactos: list[Par] = []
    altos: list[Par] = []
    for i, a in enumerate(columnas):
        for b in columnas[i + 1 :]:
            r = coeficientes[(a, b)]
            if r is None:
                continue
            x, y = vectores[a], vectores[b]
            afin = relacion_afin(x, y, tolerancia)
            if afin is not None:
                pendiente, corte, residuo = afin
                exactos.append(Par(a, b, r, pendiente, corte, residuo))
            elif abs(r) >= umbral:
                altos.append(Par(a, b, r))
    exactos.sort(key=lambda p: p.residuo)
    altos.sort(key=lambda p: -abs(p.r))
    return exactos, altos


# ===========================================================================
# VARIACION ESPACIAL
# ===========================================================================


def variacion_espacial(filas: list[Fila], columnas: list[str]) -> dict[str, tuple[int, int]]:
    """Por columna: `(dias con al menos dos valores distintos, dias utilizables)`.

    Es la misma medida que H1.5 aplico a las variables crudas, llevada a las
    columnas derivadas. Un dia es utilizable si al menos dos distritos tienen el
    valor: con uno solo la pregunta no se puede hacer.

    Se mide sobre TODAS las filas y no solo sobre las completas, a proposito.
    Esto no es una correlacion: no se compara con otra columna, asi que no hay
    nada que alinear, y restringirlo a las filas completas contestaria la
    pregunta sobre un subconjunto elegido por el estado de las otras 31 columnas.
    """
    por_fecha: dict[date, dict[str, set[float]]] = defaultdict(lambda: defaultdict(set))
    for fila in filas:
        # El codigo del distrito no se usa: lo que se cuenta es cuantos valores
        # DISTINTOS hay ese dia, no quien aporto cada uno.
        for columna, valor in fila.valores.items():
            por_fecha[fila.fecha][columna].add(valor)

    salida = {c: [0, 0] for c in columnas}
    for columnas_del_dia in por_fecha.values():
        for columna, valores in columnas_del_dia.items():
            if columna not in salida:
                continue
            salida[columna][1] += 1
            if len(valores) >= 2:
                salida[columna][0] += 1
    return {c: (d, u) for c, (d, u) in salida.items()}


# ===========================================================================
# LAS TEMPERATURAS: LA UNICA PARTE QUE NECESITA LA BASE
# ===========================================================================


def correlacion_de_temperaturas(cursor) -> dict[str, object]:
    """Mide la correlacion entre las tres temperaturas. CA-5.

    `temp_min_c` y `temp_media_c` NO estan en el CSV: se descartaron antes de
    escribirlo, con el argumento de que las tres estan «casi perfectamente
    correlacionadas» y sin ninguna cifra al lado. Esta funcion es esa cifra.

    SE MIDE SOBRE LOS DIAS, NO SOBRE LAS FILAS. Por I-05, los ocho distritos
    caen en la misma celda de NASA POWER, asi que las tres temperaturas son una
    sola serie repetida ocho veces. Calcular la correlacion sobre las 102 272
    filas da el mismo coeficiente que sobre los 12 784 dias, con una `n` inflada
    ocho veces que invita a leer significancia donde no la hay.

    **Y no se supone: se comprueba.** Si algun dia tuviera valores distintos
    entre distritos, la funcion se niega en vez de promediar por lo bajo. Que
    I-05 siga vigente es probable, no seguro, y un promedio silencioso
    convertiria un hallazgo en un numero prolijo.
    """
    cursor.execute(
        """
        SELECT fecha,
               MIN(temp_max_c),   MAX(temp_max_c),
               MIN(temp_min_c),   MAX(temp_min_c),
               MIN(temp_media_c), MAX(temp_media_c)
          FROM crudo.medicion_diaria
         WHERE temp_max_c   IS NOT NULL
           AND temp_min_c   IS NOT NULL
           AND temp_media_c IS NOT NULL
      GROUP BY fecha
      ORDER BY fecha
        """
    )
    series: dict[str, list[float]] = {"tmax": [], "tmin": [], "tmedia": []}
    desacuerdos = {"tmax": 0, "tmin": 0, "tmedia": 0}
    dias = 0

    for fila in cursor.fetchall():
        dias += 1
        for nombre, (minimo, maximo) in zip(
            ("tmax", "tmin", "tmedia"),
            ((fila[1], fila[2]), (fila[3], fila[4]), (fila[5], fila[6])),
            strict=True,
        ):
            if minimo != maximo:
                desacuerdos[nombre] += 1
            series[nombre].append(float(minimo))

    return {
        "dias": dias,
        "desacuerdos": desacuerdos,
        "series": series,
        "una_sola_serie": all(v == 0 for v in desacuerdos.values()),
    }


# ===========================================================================
# INFORME
# ===========================================================================


def escribir_tabla(vectores: dict[str, list[float]], columnas: list[str], destino: Path) -> int:
    """Las 496 parejas con su coeficiente, para que la evidencia cite y no pegue."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    coeficientes = matriz_de_correlaciones(vectores, columnas)
    with destino.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["columna_a", "columna_b", "r"])
        for (a, b), r in coeficientes.items():
            escritor.writerow([a, b, "" if r is None else f"{r:.10g}"])
    return len(coeficientes)


def escribir_sin(origen: Path, destino: Path, fuera: set[str]) -> tuple[list[str], int]:
    """Copia la matriz sin las columnas indicadas. Devuelve `(las que quedan, filas)`.

    Existe para que el «despues» del CA-8 salga de un comando y no de una edicion
    a mano: la herramienta que encontro la redundancia es la que la quita, y
    cualquiera puede reproducir las dos matrices desde la misma fuente.

    **Las celdas se copian tal cual, sin pasarlas por `float()`.** Reformatear
    los numeros cambiaria la ultima cifra de algunas, y entonces el «antes» y el
    «despues» diferirian en dos cosas a la vez -las columnas quitadas y el
    redondeo- en vez de en una. Una comparacion con dos variables no mide
    ninguna.

    **No decide QUE quitar.** Los nombres se pasan a mano y el motivo se escribe
    en la evidencia. Una herramienta que eligiera sola cual mitad de cada par
    sobrevive estaria tomando una decision de modelado sin que nadie la lea.
    """
    with origen.open(encoding="utf-8", newline="") as archivo:
        lector = csv.reader(archivo)
        encabezado = next(lector)
        desconocidas = sorted(fuera - set(encabezado))
        if desconocidas:
            raise ValueError(
                f"{origen} no tiene estas columnas: {', '.join(desconocidas)}. "
                "Sin este control, un nombre mal escrito produciria una copia "
                "identica y el CA-8 mediria la misma matriz dos veces."
            )
        quedan = [i for i, c in enumerate(encabezado) if c not in fuera]
        destino.parent.mkdir(parents=True, exist_ok=True)
        filas = 0
        with destino.open("w", encoding="utf-8", newline="") as salida:
            escritor = csv.writer(salida)
            escritor.writerow([encabezado[i] for i in quedan])
            for fila in lector:
                escritor.writerow([fila[i] for i in quedan])
                filas += 1
    return [encabezado[i] for i in quedan if encabezado[i] not in COLUMNAS_LLAVE], filas


def main() -> int:
    p = argparse.ArgumentParser(description="Redundancia entre columnas. H2.6.")
    p.add_argument("--matriz", type=Path, default=MATRIZ)
    p.add_argument("--umbral", type=float, default=UMBRAL_ALTO)
    p.add_argument("--tolerancia", type=float, default=TOLERANCIA)
    p.add_argument(
        "--salida",
        type=Path,
        default=None,
        metavar="ARCHIVO",
        help="escribe la tabla completa de 496 coeficientes en un CSV",
    )
    p.add_argument(
        "--temperaturas",
        action="store_true",
        help=(
            "mide la correlacion entre temp_max, temp_min y temp_media contra la "
            "base. Es el CA-5, y es lo unico de esta historia que necesita "
            "PostgreSQL: esas dos columnas no estan en la matriz."
        ),
    )
    p.add_argument(
        "--escribir-sin",
        default=None,
        metavar="COLUMNAS",
        help=(
            "escribe una copia de la matriz sin esas columnas, separadas por "
            "comas, y no mide nada. Es el «despues» del CA-8. Necesita --destino."
        ),
    )
    p.add_argument("--destino", type=Path, default=None, metavar="ARCHIVO")
    args = p.parse_args()

    if not args.matriz.exists():
        print(f"\nNo encuentro {args.matriz}.")
        print("\n  Se produce con:  python -m backend.modelado.generar_caracteristicas\n")
        return 1

    if args.escribir_sin is not None:
        if args.destino is None:
            print("\n--escribir-sin necesita --destino.\n")
            return 1
        fuera = {c.strip() for c in args.escribir_sin.split(",") if c.strip()}
        try:
            quedan, filas_escritas = escribir_sin(args.matriz, args.destino, fuera)
        except ValueError as error:
            print(f"\n{error}\n")
            return 1
        print(f"\nMatriz sin {len(fuera)} columnas · H2.6 · CA-8\n")
        print(f"  origen    {args.matriz}")
        print(f"  quitadas  {', '.join(sorted(fuera))}")
        print(f"  quedan    {len(quedan)} columnas")
        print(f"  filas     {filas_escritas}")
        print(f"  escrito en {args.destino}\n")
        return 0

    columnas, filas = leer_matriz(args.matriz)
    if not filas:
        print(f"\n{args.matriz} no tiene filas.\n")
        return 1

    completas = filas_completas(filas, columnas)
    distritos = {f.codigo for f in filas}
    fechas = [f.fecha for f in filas]

    print("\nRedundancia de la matriz de caracteristicas · H2.6\n")
    print(f"  archivo            {args.matriz}")
    print(f"  filas              {len(filas)}")
    print(f"  columnas           {len(columnas)}")
    print(f"  distritos          {len(distritos)}")
    print(f"  rango              {min(fechas)} a {max(fechas)}")
    if not completas:
        print(
            f"\n  Ninguna fila tiene las {len(columnas)} columnas: "
            "no hay nada que correlacionar."
        )
        print("  El estimador tampoco podria entrenar con esta matriz.\n")
        return 1
    print(f"  filas COMPLETAS    {len(completas)}  ({100.0 * len(completas) / len(filas):.1f} %)")
    print("  La tabla de abajo describe ESAS filas, que son las que el modelo usa.")

    # --- CA-2: variacion espacial -----------------------------------------
    espacial = variacion_espacial(filas, columnas)
    distinguen = sorted(c for c, (d, _u) in espacial.items() if d > 0)
    identicas = sorted(c for c, (d, u) in espacial.items() if d == 0 and u > 0)

    print("\nVariacion espacial · CA-2\n")
    print(f"  distinguen distritos       {len(distinguen)} de {len(columnas)}")
    print(f"  identicas en los distritos {len(identicas)} de {len(columnas)}")
    for columna in identicas:
        _dias, usables = espacial[columna]
        print(f"      {columna:<28} mismo valor en los {len(distritos)} distritos, {usables} dias")
    if distinguen:
        print("\n  Distinguen:")
        for columna in distinguen:
            dias, usables = espacial[columna]
            print(f"      {columna:<28} {100.0 * dias / usables:6.2f} % de {usables} dias")

    # --- CA-6 y CA-7: los pares -------------------------------------------
    vectores = como_vectores(completas, columnas)
    exactos, altos = pares_relacionados(vectores, columnas, args.umbral, args.tolerancia)

    print(f"\nRedundancia EXACTA · CA-6 y CA-7 · tolerancia relativa {args.tolerancia:.0e}\n")
    if not exactos:
        print("  Ninguna. La hipotesis declarada en los criterios no se cumple.")
    for par in exactos:
        print(f"  {par.relacion()}")
        print(f"      r = {par.r:.10f}   residuo relativo maximo {par.residuo:.2e}")

    print(f"\nRedundancia ALTA · |r| >= {args.umbral} · se reporta y NO se descarta\n")
    if not altos:
        print("  Ninguna.")
    for par in altos:
        print(f"  {par.a:<24} {par.b:<24} r = {par.r:+.4f}")

    print("\n  LIMITE DECLARADO: la correlacion solo ve redundancia LINEAL.")
    print("  `cal_seno` y `cal_coseno` cumplen sen^2 + cos^2 = 1 -dependencia")
    print("  funcional perfecta- y no aparecen en ninguna de las dos listas.")

    # --- la tabla completa -------------------------------------------------
    if args.salida is not None:
        escritas = escribir_tabla(vectores, columnas, args.salida)
        print(f"\n  {escritas} parejas escritas en {args.salida}")

    # --- CA-5: las temperaturas -------------------------------------------
    if args.temperaturas:
        print("\nLas tres temperaturas · CA-5\n")
        try:
            from basedatos.conexion import conectar
        except ImportError as error:
            print(f"  No se pudo importar la conexion: {error}\n")
            return 1
        try:
            conexion = conectar()
        except Exception as error:  # noqa: BLE001
            print(f"  La base no responde: {error}")
            print("\n    Se levanta con:  docker compose up -d\n")
            return 1
        try:
            medida = correlacion_de_temperaturas(conexion.cursor())
        finally:
            conexion.close()

        if not medida["una_sola_serie"]:
            print("  Los distritos NO coinciden, asi que no son una sola serie:")
            for nombre, cuantos in medida["desacuerdos"].items():
                print(f"      {nombre:<8} {cuantos} dias con valores distintos entre distritos")
            print("\n  I-05 dejo de valer para la temperatura, y eso es un hallazgo.")
            print("  No se promedia por lo bajo: hay que medirlo por distrito.\n")
            return 1

        series = medida["series"]
        print(f"  {medida['dias']} dias. Una sola serie: los ocho distritos coinciden")
        print("  en todos los dias, que es I-05 y por eso no se cuentan las filas.\n")
        for a, b in (("tmax", "tmin"), ("tmax", "tmedia"), ("tmin", "tmedia")):
            r = correlacion(series[a], series[b])
            print(f"      {a:<8} {b:<8} r = {r:+.6f}")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
