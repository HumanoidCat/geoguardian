"""Comprueba los criterios de aceptacion de H3.6, la tabla comparativa.

QUE COMPRUEBA, Y CONTRA QUE

    CA-1  todos los estimadores ven exactamente los mismos pliegues y filas
    CA-2  la metrica es la unica de D-10, no una reimplementacion
    CA-3  los estimadores que faltan se declaran, no se omiten
    CA-4  el contrato es intercambiable: linea base y modelo pasan por el mismo camino
    CA-5  no se declara ganador cuando la ventaja es menor que la dispersion
    CA-6  dos corridas dan el mismo numero
    CA-7  la tabla coincide con lo que reporta H3.1 por su propio camino

**CA-7 es el que de verdad sostiene a los demas.** `comparar.py` y
`evaluar_linea_base.py` llegan a las mismas dos lineas base por rutas distintas:
el primero a traves del contrato `Estimador` y el adaptador `DesdeLineaBase`, el
segundo llamandolas directo. Si el adaptador introdujera cualquier diferencia
-otro corte, otro trato de los None- las dos rutas divergirian. Que coincidan
hasta el ultimo decimal es lo que prueba que envolver una linea base en el
contrato no la cambia.

CA-5 se comprueba **con una prueba negativa**: se inyecta un estimador ficticio
construido para ganar por poco y se exige que el veredicto NO lo declare ganador.
Un criterio que solo se comprueba con dato que ya lo cumple no comprueba nada; es
el mismo modo de fallo de I-06.

CORRE SIEMPRE, CON DATO REAL O SIN EL

`datos/procesados/etiquetas.csv` **no esta versionado** -lo ignora `.gitignore`,
linea 11- porque es un artefacto derivado de la base. La primera version de este
verificador se saltaba solo cuando el archivo no estaba, y en el CI el archivo
**nunca** esta: habria quedado verde sin ejecutar una sola comprobacion, que es
exactamente I-06.

Asi que cuando el CSV real no aparece, se construye uno **sintetico y
determinista**: mismas fechas, mismos distritos, clases asignadas por una funcion
de dispersion sobre (distrito, fecha) sin ningun generador aleatorio. No hay
semilla que fijar porque no hay azar.

Lo que se comprueba son propiedades del **arnes** -que todos vean los mismos
pliegues, que la metrica sea una sola, que el veredicto respete su regla- y
ninguna necesita que el dato sea el verdadero. La linea al final dice cual de los
dos se uso, para que nadie confunda una corrida con la otra.

Uso:
    python -m backend.modelado.verificar_h36

Sale con codigo 1 si algo no se cumple, para poder correrlo en CI.
"""

from __future__ import annotations

import inspect
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado import comparar as mod  # noqa: E402
from backend.modelado import evaluar_linea_base as h31  # noqa: E402
from backend.modelado.comparar import (  # noqa: E402
    DISPONIBLES,
    REFERENCIA,
    DesdeLineaBase,
    Estimador,
    Observacion,
    Resultado,
    comparar,
    estimadores_disponibles,
    pendientes,
    veredicto,
)
from backend.modelado.linea_base import LineaBaseTrivial, f1_macro  # noqa: E402
from backend.modelado.particion import particionar  # noqa: E402
from contratos.enums import NivelRiesgo, TipoEvento  # noqa: E402

ETIQUETAS = RAIZ / "datos" / "procesados" / "etiquetas.csv"

fallos: list[str] = []


def comprobar(descripcion: str, condicion: bool, detalle: str = "") -> None:
    print(f"  {'OK  ' if condicion else 'FALLO'}  {descripcion}")
    if not condicion:
        fallos.append(descripcion)
        if detalle:
            print(f"        {detalle}")


# --------------------------------------------------------------------------- #
# Un estimador ficticio, para las pruebas negativas                             #
# --------------------------------------------------------------------------- #


class EstimadorDeMentira:
    """Devuelve lo que se le diga. Solo existe para este verificador.

    Sirve para dos cosas: probar que el contrato acepta algo que **no** es una
    linea base -CA-4- y fabricar una ventaja pequeña a proposito para CA-5.
    """

    def __init__(self, nombre: str = "de mentira", clase: NivelRiesgo | None = None) -> None:
        self.nombre = nombre
        self.clase = clase
        self.filas_vistas = 0

    def ajustar(self, observaciones, etiquetas):
        self.filas_vistas = len(observaciones)
        if self.clase is None:
            self.clase = etiquetas[0] if etiquetas else None
        return self

    def predecir(self, observaciones):
        return [self.clase for _ in observaciones]


def datos_sinteticos() -> list[tuple[str, date, dict[str, NivelRiesgo | None]]]:
    """Etiquetas construidas, con la misma forma que las de H3.0.

    **Sin azar.** La clase sale de `hash_estable(distrito, fecha, evento)`, una
    funcion de dispersion escrita aca abajo. Dos corridas dan byte por byte lo
    mismo en cualquier maquina, que es lo que CA-6 exige y lo que `hash()` de
    Python **no** garantiza entre procesos.

    Tres propiedades se imitan a proposito, porque sin ellas el arnes no se
    ejercita de verdad:

    1. **Clases desbalanceadas.** Con todo repartido en tercios, la trivial
       sacaria un F1-macro alto y la diferencia con la climatologica se
       aplastaria. Aca ALTO y MEDIO son minoritarios, como en el dato real.
    2. **Estacionalidad en un evento y no en los otros.** `lluvia_intensa` carga
       la clase ALTA en los meses de setiembre y octubre. Asi la climatologica
       le gana a la trivial en un evento y no en los demas, y las dos ramas del
       veredicto se recorren.
    3. **El incendio no existe antes de 2001.** Es I-11 y COBERTURA_FOCOS. Si el
       sintetico lo ignorara, el primer pliegue tendria dato donde el real no lo
       tiene y CA-1 pasaria por un camino que en produccion no ocurre.
    """
    distritos = ("50801", "50802", "50803", "50804", "50805", "50806", "50807", "50808")

    def hash_estable(*partes: object) -> int:
        h = 2166136261
        for parte in partes:
            for byte in str(parte).encode("utf-8"):
                h = ((h ^ byte) * 16777619) & 0xFFFFFFFF
        return h

    def clase(codigo: str, dia: date, evento: str, por_mil_alto: int, por_mil_medio: int):
        valor = hash_estable(codigo, dia.isoformat(), evento) % 1000
        if valor < por_mil_alto:
            return NivelRiesgo.ALTO
        if valor < por_mil_alto + por_mil_medio:
            return NivelRiesgo.MEDIO
        return NivelRiesgo.BAJO

    # Las tasas se eligieron **midiendo**, no estimando. La primera version puso
    # ALTO al 15 % en temporada y MEDIO al 17 % fuera de ella, y la climatologica
    # perdio contra la trivial en los tres eventos: con MEDIO tan alto fuera de
    # temporada, su realce superaba al de BAJO y el modelo predecia MEDIO diez
    # meses al anio.
    #
    # Es una propiedad real de la linea base de realce -sobre-predice clases
    # minoritarias cuando estan cerca de su propia tasa base- y vale la pena
    # dejarla anotada, pero no servia para lo que este sintetico tiene que hacer.
    #
    #                        en temporada        fuera de temporada
    #   lluvia   ALTO             400 / 1000            10 / 1000
    #            MEDIO            100 / 1000            40 / 1000
    LLUVIA_TEMPORADA = (400, 100)
    LLUVIA_RESTO = (10, 40)

    filas = []
    dia = date(1991, 1, 1)
    fin = date(2025, 12, 31)
    while dia <= fin:
        # Setiembre y octubre son el pico de la estacion lluviosa en la vertiente
        # del Pacifico Norte. Aca no se afirma nada del clima real: es solo el
        # mes en el que este sintetico concentra la senal.
        alto, medio = LLUVIA_TEMPORADA if dia.month in (9, 10) else LLUVIA_RESTO
        for codigo in distritos:
            niveles = {
                # Sin estacionalidad: el mes no informa, como en el dato real
                # despues de D-19.
                "sequia": clase(codigo, dia, "sequia", 30, 60),
                "lluvia_intensa": clase(codigo, dia, "lluvia_intensa", alto, medio),
                # Binario y solo desde 2001, por D-25 e I-11.
                "incendio": clase(codigo, dia, "incendio", 12, 0) if dia.year >= 2001 else None,
            }
            filas.append((codigo, dia, niveles))
        dia = date.fromordinal(dia.toordinal() + 1)
    return filas


def main() -> int:
    print("\nCriterios de aceptacion de H3.6\n")

    if ETIQUETAS.exists():
        filas = h31.leer(ETIQUETAS)
        origen = f"dato real, {ETIQUETAS.relative_to(RAIZ)}"
    else:
        filas = datos_sinteticos()
        origen = "etiquetas SINTETICAS, deterministas. El CSV real no esta versionado"

    print(f"  Origen: {origen}")
    print(f"  Filas:  {len(filas)}\n")

    # ------------------------------------------------------------------ CA-1 - #
    print("CA-1, todos los estimadores ven los mismos pliegues y las mismas filas:")

    # Dos estimadores que anotan cuantas filas recibieron en cada pliegue. Si la
    # tabla le diera a uno un conjunto distinto que al otro, las dos listas
    # diferirian y la comparacion entera seria falsa sin que nada mas lo delate.
    vistas: dict[str, list[int]] = {"a": [], "b": []}

    class Testigo(EstimadorDeMentira):
        def __init__(self, registro: list[int]) -> None:
            super().__init__("testigo")
            self._registro = registro

        def ajustar(self, observaciones, etiquetas):
            self._registro.append(len(observaciones))
            return super().ajustar(observaciones, etiquetas)

    comparar(
        TipoEvento.LLUVIA_INTENSA,
        filas,
        {"a": lambda: Testigo(vistas["a"]), "b": lambda: Testigo(vistas["b"])},
    )

    comprobar(
        "los dos estimadores recibieron el mismo numero de pliegues",
        len(vistas["a"]) == len(vistas["b"]) and len(vistas["a"]) > 0,
        f"a vio {len(vistas['a'])} pliegues y b vio {len(vistas['b'])}",
    )
    comprobar(
        "y en cada pliegue, exactamente las mismas filas de entrenamiento",
        vistas["a"] == vistas["b"],
        f"a: {vistas['a']}\n        b: {vistas['b']}",
    )
    comprobar(
        "la particion sale de H3.2 y no se recalcula aca",
        "particionar" in inspect.getsource(mod.comparar),
        "si comparar() derivara sus propios cortes, la tabla compararia conjuntos distintos",
    )

    # ------------------------------------------------------------------ CA-2 - #
    print("\nCA-2, la metrica es la unica de D-10:")

    fuente = inspect.getsource(mod)
    comprobar(
        "comparar.py importa f1_macro de H3.1",
        "from backend.modelado.linea_base import" in fuente and "f1_macro" in fuente,
    )
    comprobar(
        "y no define una propia",
        "def f1_macro" not in fuente,
        "una segunda implementacion de la metrica es una segunda definicion de que "
        "significa 'mejor'",
    )
    comprobar(
        "el f1_macro que usa es exactamente el objeto de H3.1",
        mod.f1_macro is f1_macro,
    )

    # ------------------------------------------------------------------ CA-3 - #
    print("\nCA-3, lo que falta se declara:")

    # DESDE H3.3 LA LISTA DEPENDE DE LO QUE HAYA CARGADO.
    #
    # `regresion logistica` entra a la tabla **solo si la matriz de
    # caracteristicas existe**, asi que preguntarle al diccionario estatico
    # daria una respuesta falsa en uno de los dos casos. Se comprueban **los
    # dos**: con matriz y sin ella, ningun algoritmo de D-09 puede desaparecer.
    for hay_matriz in (False, True):
        etiqueta = "con matriz" if hay_matriz else "sin matriz"
        disponibles = estimadores_disponibles(hay_matriz)
        faltantes = pendientes(hay_matriz)

        for algoritmo in ("regresion logistica", "random forest", "xgboost"):
            comprobar(
                f"[{etiqueta}] '{algoritmo}' de D-09 esta en la tabla o declarado pendiente",
                algoritmo in disponibles or algoritmo in faltantes,
                "D-09 comprometio tres algoritmos. Uno que no aparece ni como pendiente "
                "es un compromiso que se perdio en silencio",
            )
        comprobar(
            f"[{etiqueta}] ningun pendiente esta tambien disponible",
            not (set(faltantes) & set(disponibles)),
            "si entra a la tabla, tiene que salir de la lista de pendientes",
        )
        comprobar(
            f"[{etiqueta}] cada pendiente dice a que historia pertenece",
            all("H3." in v for v in faltantes.values()),
        )

    comprobar(
        "sin matriz quedan mas pendientes que con ella",
        len(pendientes(False)) > len(pendientes(True)),
        "el registro condicional de H3.3 no esta teniendo efecto",
    )
    comprobar(
        f"la referencia '{REFERENCIA}' esta disponible",
        REFERENCIA in DISPONIBLES,
        "sin la linea base en la tabla, la columna 'vs ref' no significa nada",
    )

    # ------------------------------------------------------------------ CA-4 - #
    print("\nCA-4, el contrato es intercambiable:")

    envuelta = DesdeLineaBase("trivial", LineaBaseTrivial)
    comprobar("una linea base envuelta cumple el contrato", isinstance(envuelta, Estimador))
    comprobar(
        "un estimador que no es linea base tambien lo cumple",
        isinstance(EstimadorDeMentira(), Estimador),
        "si el contrato solo lo cumplen las lineas base, no sirve para H3.3",
    )

    obs = [Observacion("50801", date(2020, 3, 1)), Observacion("50802", date(2020, 3, 2))]
    envuelta.ajustar(obs, [NivelRiesgo.BAJO, NivelRiesgo.BAJO])
    comprobar(
        "la envoltura predice una lista del mismo largo que la entrada",
        len(envuelta.predecir(obs)) == len(obs),
    )
    comprobar(
        "predecir antes de ajustar falla en vez de devolver algo",
        _falla(lambda: DesdeLineaBase("x", LineaBaseTrivial).predecir(obs)),
        "devolver None sin ajustar se veria igual que 'no hay dato para ese distrito-mes'",
    )
    comprobar(
        "la envoltura descarta las caracteristicas, que es CA-1 de H3.1",
        "codigo_distrito, o.fecha" in inspect.getsource(DesdeLineaBase.predecir),
        "una linea base que mira una variable meteorologica deja de ser linea base",
    )

    # ------------------------------------------------------------------ CA-5 - #
    print("\nCA-5, no se declara ganador sin resolucion para decirlo:")

    apretado = [
        Resultado("gana por poco", [0.50, 0.60, 0.55], 0.55, 0.04, 0),
        Resultado("segundo", [0.53, 0.54, 0.53], 0.533, 0.005, 0),
    ]
    comprobar(
        "una ventaja menor que la dispersion se declara empate tecnico",
        "empate tecnico" in veredicto(apretado),
        f"ventaja 0.017, rango 0.100, y dijo: {veredicto(apretado)}",
    )

    claro = [
        Resultado("gana claro", [0.80, 0.81, 0.80], 0.803, 0.005, 0),
        Resultado("segundo", [0.50, 0.51, 0.50], 0.503, 0.005, 0),
    ]
    comprobar(
        "una ventaja mayor que la dispersion si declara ganador",
        "empate" not in veredicto(claro),
        f"ventaja 0.300, rango 0.010, y dijo: {veredicto(claro)}",
    )
    comprobar(
        "con un solo estimador no se inventa un veredicto",
        "no hay con que comparar" in veredicto(claro[:1]),
    )

    # ------------------------------------------------------------------ CA-6 - #
    print("\nCA-6, dos corridas dan lo mismo:")

    primera = comparar(TipoEvento.LLUVIA_INTENSA, filas)
    segunda = comparar(TipoEvento.LLUVIA_INTENSA, filas)
    comprobar(
        "el orden y los valores son identicos entre corridas",
        [(r.nombre, r.por_pliegue) for r in primera]
        == [(r.nombre, r.por_pliegue) for r in segunda],
        "un resultado que cambia entre corridas no se puede citar en el documento IEEE",
    )

    # ------------------------------------------------------------------ CA-7 - #
    print("\nCA-7, la tabla coincide con H3.1 por su propio camino:")

    for evento in TipoEvento:
        triviales, climaticas, _ = h31.evaluar(evento, filas)
        tabla = {r.nombre: r.por_pliegue for r in comparar(evento, filas)}

        for nombre, esperado in (("trivial", triviales), ("climatologica", climaticas)):
            medido = tabla.get(nombre, [])
            iguales = len(medido) == len(esperado) and all(
                abs(a - b) < 1e-12 for a, b in zip(medido, esperado, strict=True)
            )
            comprobar(
                f"{evento.value} · {nombre}: H3.6 y H3.1 dan lo mismo",
                iguales,
                f"H3.1 {[round(v, 4) for v in esperado]}\n"
                f"        H3.6 {[round(v, 4) for v in medido]}",
            )

    # ------------------------------------------------------------------------ #
    print("\nCoherencia con la particion de H3.2:")

    for evento in TipoEvento:
        pliegues = len(particionar(evento))
        medidos = len(comparar(evento, filas)[0].por_pliegue)
        comprobar(
            f"{evento.value}: se evaluaron {medidos} de los {pliegues} pliegues de H3.2",
            medidos == pliegues,
            "un pliegue que se salta sin decirlo cambia la media y nadie lo nota",
        )

    if fallos:
        print(f"\n{len(fallos)} criterios fallaron:\n")
        for f in fallos:
            print(f"  - {f}")
        print()
        return 1

    print("\nLos criterios de H3.6 se cumplen.\n")
    return 0


def _falla(accion) -> bool:
    try:
        accion()
    except Exception:
        return True
    return False


if __name__ == "__main__":
    sys.exit(main())
