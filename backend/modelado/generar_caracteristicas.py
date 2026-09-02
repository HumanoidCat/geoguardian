"""Matriz de caracteristicas para los estimadores. Historia H3.3.

===========================================================================
QUE HACE, Y POR QUE EXISTE APARTE
===========================================================================

Lee `crudo.medicion_diaria`, aplica las transformaciones de **H2.5** y escribe
`datos/procesados/caracteristicas.csv`: una fila por distrito y dia, con las
entradas que los tres algoritmos van a consumir.

Va aparte de `comparar.py` por la misma razon que `generar_etiquetas.py` va
aparte: **la comparacion no debe necesitar la base**. Quien evalua modelos corre
un guion sobre dos CSV y obtiene siempre lo mismo; quien reconstruye los CSV
necesita PostgreSQL levantado y lo hace una vez.

Si la matriz se armara dentro de `comparar()`, cada corrida dependeria del estado
de la base y **dos ejecuciones del mismo dia podrian no coincidir**.

===========================================================================
POR QUE ESTAS VARIABLES Y NO TODAS
===========================================================================

`crudo.medicion_diaria` trae siete variables. Aca entran cuatro, elegidas por su
relacion con los eventos que se estiman, no por estar disponibles:

    precipitacion_mm       lluvia intensa es un umbral sobre ella (D-08), y la
                           sequia es su ausencia sostenida
    temp_max_c             calor y sequedad son las condiciones de incendio
    humedad_relativa_pct   la variable de combustible fino mas directa que hay
    viento_ms              propagacion; entra con rezagos cortos nada mas

Quedan fuera `temp_min_c` y `temp_media_c` **a proposito**: las tres temperaturas
de un mismo dia estan casi perfectamente correlacionadas, y meter las tres no
agrega senal, agrega colinealidad. En una regresion logistica eso no empeora la
prediccion pero **arruina la interpretacion de los coeficientes**, que es lo que
H4.1 va a necesitar.

Un modelo con menos entradas que se puede explicar vale mas aca que uno con todas
que no.

===========================================================================
EL VALOR IMPUTADO NO ES UNA OBSERVACION
===========================================================================

`medicion_diaria` marca con `imputado` las filas cuyo valor lo puso H1.4, no la
fuente. Por omision **esas filas entran como NULL**, no como su valor imputado.

El motivo es el de **D-07**: un rezago de un valor imputado es el rezago de una
suposicion, y una media movil que la promedia le da a la suposicion el mismo peso
que a una medicion. La imputacion sirve para no romper una serie que se grafica;
no sirve para alimentar un modelo que despues se va a interpretar.

Se puede cambiar con `--incluir-imputados`, y el informe dice **cuanto cambia el
rendimiento de la matriz** en cada caso, para que la decision se tome mirando el
numero y no la intuicion.

===========================================================================
POR QUE ESTAS CARACTERISTICAS NO SE AJUSTAN DENTRO DEL PLIEGUE
===========================================================================

**CA-6 de H3.2** dice que toda normalizacion usada como ENTRADA se ajusta dentro
del pliegue. Estas caracteristicas no la violan, y conviene entender por que:

    rezago(k)        mira k dias hacia atras de la propia fila
    acumulado(n)     suma la ventana que TERMINA en la fila
    media_movil(n)   promedia esa misma ventana

Ninguna usa un estadistico calculado sobre el conjunto: son **transformaciones
causales de cada serie**, y el valor de una fila no cambia si se agregan filas
posteriores. Por eso se pueden calcular una sola vez, antes de partir.

Lo que si necesita ajustarse dentro del pliegue es el **escalado**, y eso vive en
el estimador: `RegresionLogistica.ajustar()` construye su `StandardScaler` con el
entrenamiento del pliegue y nada mas.

La distincion importa: si algun dia se agrega una caracteristica de tipo
percentil o anomalia estandarizada -que si usan estadisticos del conjunto-,
**esa tendria que calcularse dentro del pliegue** y este guion dejaria de ser el
lugar donde ponerla.

Uso:
    docker compose up -d
    python -m backend.modelado.generar_caracteristicas
    python -m backend.modelado.generar_caracteristicas --incluir-imputados
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from datetime import date, timedelta
from math import ceil
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.senales.caracteristicas import (  # noqa: E402
    REZAGOS,
    VENTANAS,
    Punto,
    caracteristicas_por_distrito,
)

SALIDA = RAIZ / "datos" / "procesados" / "caracteristicas.csv"

#: Columna de la base -> prefijo con el que aparecen sus caracteristicas.
#: El prefijo es corto porque termina en el nombre de cada columna del CSV y en
#: los coeficientes que H4.1 va a mostrar.
VARIABLES: dict[str, str] = {
    "precipitacion_mm": "pp",
    "temp_max_c": "tmax",
    "humedad_relativa_pct": "hr",
    "viento_ms": "viento",
}

#: El viento solo con rezagos cortos. Una media movil de 30 dias del viento no
#: describe ninguna condicion de incendio: describe el clima de la estacion, que
#: el calendario de la linea base climatologica ya captura mejor.
VENTANAS_POR_PREFIJO: dict[str, tuple[int, ...]] = {
    "viento": (3,),
}
REZAGOS_POR_PREFIJO: dict[str, tuple[int, ...]] = {
    "viento": (1, 2),
}

#: SOLO LA PRECIPITACION SE ACUMULA, Y ESTO NO ES UN DETALLE.
#:
#: `acumulado` y `media_movil` sobre la misma ventana son **el mismo numero
#: multiplicado por n** cuando la ventana esta completa. Para la lluvia las dos
#: tienen sentido por separado -«llovieron 120 mm en 7 dias» es la magnitud que
#: define el evento- pero para la temperatura, la humedad y el viento la suma no
#: significa nada: sumar porcentajes de humedad no da un porcentaje.
#:
#: Dejarlas todas metia pares **perfectamente colineales** en el modelo, que es
#: exactamente lo que se evito al descartar `temp_min_c` y `temp_media_c`.
#: Se detecto midiendo la matriz, no leyendo el codigo.
SE_ACUMULAN = frozenset({"pp"})


def leer_mediciones(cursor, incluir_imputados: bool) -> tuple[dict[str, list[Punto]], dict]:
    """Devuelve las series por distrito y un recuento de lo que se descarto.

    Las series salen **completas y ordenadas**: un dia por fecha entre el minimo
    y el maximo del distrito, con `None` donde no hubo fila. H2.5 rechaza las
    series con huecos de calendario, y con razon: un rezago de 1 sobre una serie
    a la que le faltan dias no es el valor de ayer, es el valor de la fila
    anterior, que puede ser de hace una semana.
    """
    columnas = ", ".join(VARIABLES)
    cursor.execute(
        f"""
        SELECT codigo_distrito, fecha, imputado, {columnas}
        FROM crudo.medicion_diaria
        ORDER BY codigo_distrito, fecha
        """  # noqa: S608 - las columnas salen de VARIABLES, no de entrada externa
    )

    crudo: dict[str, dict[date, dict[str, float | None]]] = defaultdict(dict)
    recuento = {"filas": 0, "imputadas": 0, "valores_nulos": 0}

    for fila in cursor.fetchall():
        codigo, fecha, imputado = fila[0], fila[1], fila[2]
        recuento["filas"] += 1
        if imputado:
            recuento["imputadas"] += 1

        valores: dict[str, float | None] = {}
        for columna, valor in zip(VARIABLES, fila[3:], strict=True):
            if valor is None or (imputado and not incluir_imputados):
                valores[VARIABLES[columna]] = None
                recuento["valores_nulos"] += 1
            else:
                valores[VARIABLES[columna]] = float(valor)
        crudo[codigo][fecha] = valores

    # Se rellena el calendario. Un dia ausente y un dia sin valor son la misma
    # cosa para el modelo -no se observo- y H2.5 necesita verlos igual.
    series: dict[str, list[Punto]] = {}
    vacio = dict.fromkeys(VARIABLES.values())
    for codigo, por_fecha in crudo.items():
        inicio, fin = min(por_fecha), max(por_fecha)
        dias = [inicio + timedelta(days=i) for i in range((fin - inicio).days + 1)]
        series[codigo] = [(d, por_fecha.get(d, vacio)) for d in dias]
        recuento["dias_rellenados"] = recuento.get("dias_rellenados", 0) + (
            len(dias) - len(por_fecha)
        )
    return series, recuento


def _util(columna: str, prefijo: str) -> bool:
    """Si la columna que produjo H2.5 entra al modelo.

    Se descartan dos familias:

    **Los acumulados de lo que no se acumula.** Ver `SE_ACUMULAN`.

    **Los contadores `_observados` de las ventanas estrictas.** H2.5 los emite a
    proposito -«el modelo tiene derecho a saber que la ventana venia
    incompleta»- y tiene razon **cuando la ventana se relaja**. Bajo la regla
    estricta la ventana o esta completa o vale None, asi que en las filas que
    sobreviven el contador vale siempre n: es una **columna constante**, no
    aporta nada y le mete una fila inutil a la tabla de coeficientes de H4.1.
    Con `--minimo-observado` el contador si varia y se conserva.
    """
    if columna.endswith("_observados"):
        return False  # se re-agregan abajo si la ventana esta relajada
    return not ("_acum" in columna and prefijo not in SE_ACUMULAN)


def construir(
    series: dict[str, list[tuple[date, dict[str, float | None]]]],
    fraccion_minima: float | None,
) -> dict[tuple[str, date], dict[str, float | None]]:
    """Aplica H2.5 a cada variable y junta todo por (distrito, fecha).

    `fraccion_minima` es una **fraccion de la ventana**, no un numero de dias.

    Ser una fraccion no es cosmetica. `minimo_observado` de H2.5 es un conteo
    absoluto, y pasarle el mismo a todas las ventanas es una trampa: con 20, la
    ventana de 3 dias **no puede cumplirlo nunca** -solo tiene 3 casillas- y la
    matriz sale vacia. Medido: con 20 dias el rendimiento cayo de 17,5 % a 0 %.
    Con una fraccion, cada ventana recibe su propio umbral.
    """
    matriz: dict[tuple[str, date], dict[str, float | None]] = defaultdict(dict)
    relajada = fraccion_minima is not None

    for prefijo in VARIABLES.values():
        por_distrito = {
            codigo: [Punto(fecha, valores[prefijo]) for fecha, valores in filas]
            for codigo, filas in series.items()
        }
        rezagos = REZAGOS_POR_PREFIJO.get(prefijo, REZAGOS)
        ventanas = VENTANAS_POR_PREFIJO.get(prefijo, VENTANAS)

        # Una llamada por ventana, porque cada una lleva su propio umbral.
        for indice, n in enumerate(ventanas):
            resultado = caracteristicas_por_distrito(
                por_distrito,
                prefijo=prefijo,
                # Los rezagos no dependen de la ventana: se piden una sola vez.
                rezagos=rezagos if indice == 0 else (),
                ventanas=(n,),
                minimo_observado=ceil(fraccion_minima * n) if relajada else None,
            )
            for codigo, filas in resultado.items():
                fechas = [f for f, _ in series[codigo]]
                for fecha, caracteristicas in zip(fechas, filas, strict=True):
                    matriz[(codigo, fecha)].update(
                        {
                            c: v
                            for c, v in caracteristicas.items()
                            if _util(c, prefijo) or (relajada and c.endswith("_observados"))
                        }
                    )

    return dict(matriz)


def sin_columnas_constantes(
    matriz: dict[tuple[str, date], dict[str, float | None]],
) -> tuple[dict[tuple[str, date], dict[str, float | None]], list[str]]:
    """Quita las columnas que valen lo mismo en todas las filas observadas.

    Una columna constante no aporta informacion y **si aporta ruido**: ocupa una
    fila en la tabla de coeficientes de H4.1 con un numero que no significa nada.
    `StandardScaler` la deja pasar sin fallar -sklearn sustituye la desviacion
    cero por uno- asi que no se nota sola.

    Se mide sobre el conjunto entero y no por pliegue a proposito: una columna
    constante en todo el historico lo es en cualquier pliegue, y una que solo lo
    es dentro de un pliegue es informacion legitima que ese pliegue no vio.
    """
    if not matriz:
        return matriz, []
    vistos: dict[str, set] = defaultdict(set)
    for fila in matriz.values():
        for columna, valor in fila.items():
            if valor is not None and len(vistos[columna]) < 2:
                vistos[columna].add(valor)
    constantes = sorted(c for c, valores in vistos.items() if len(valores) < 2)
    if not constantes:
        return matriz, []
    fuera = set(constantes)
    limpia = {
        clave: {c: v for c, v in fila.items() if c not in fuera} for clave, fila in matriz.items()
    }
    return limpia, constantes


def rendimiento(matriz: dict[tuple[str, date], dict[str, float | None]]) -> dict[str, float]:
    """Que fraccion de las filas tiene TODAS sus caracteristicas.

    Es la cifra que importa: el estimador **no imputa**, asi que una fila con una
    sola caracteristica nula no se usa ni para ajustar ni para predecir. Una
    matriz con muchas columnas y poco rendimiento entrena con menos datos que una
    matriz mas pobre y completa.
    """
    if not matriz:
        return {"filas": 0, "completas": 0, "porcentaje": 0.0}
    completas = sum(1 for f in matriz.values() if all(v is not None for v in f.values()))
    return {
        "filas": len(matriz),
        "completas": completas,
        "porcentaje": 100.0 * completas / len(matriz),
    }


def escribir(matriz: dict[tuple[str, date], dict[str, float | None]], destino: Path) -> list[str]:
    columnas = sorted({c for f in matriz.values() for c in f})
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["codigo_distrito", "fecha", *columnas])
        for (codigo, fecha), caracteristicas in sorted(matriz.items()):
            escritor.writerow(
                [
                    codigo,
                    fecha.isoformat(),
                    # Vacio y no 0: **D-07**. Quien lea esto tiene que poder
                    # distinguir «no se pudo calcular» de «dio cero», y una
                    # media movil de precipitacion vale cero muy seguido.
                    *[
                        "" if caracteristicas.get(c) is None else f"{caracteristicas[c]:.6g}"
                        for c in columnas
                    ],
                ]
            )
    return columnas


def leer(origen: Path) -> dict[tuple[str, date], dict[str, float]]:
    """Lee el CSV para `comparar.py`. **Las celdas vacias se omiten, no valen 0.**

    Omitirlas y no ponerlas en None es deliberado: `RegresionLogistica._fila`
    descarta la observacion si le falta **alguna** columna de las que aprendio, y
    para eso le basta con que la clave no este. Un None explicito daria el mismo
    resultado por un camino mas largo.
    """
    salida: dict[tuple[str, date], dict[str, float]] = {}
    with origen.open(encoding="utf-8", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            codigo = fila.pop("codigo_distrito")
            fecha = date.fromisoformat(fila.pop("fecha"))
            salida[(codigo, fecha)] = {c: float(v) for c, v in fila.items() if v != ""}
    return salida


def main() -> int:
    p = argparse.ArgumentParser(description="Matriz de caracteristicas de H3.3.")
    p.add_argument("--salida", type=Path, default=SALIDA)
    p.add_argument(
        "--incluir-imputados",
        action="store_true",
        help="usar los valores que puso H1.4. Por omision entran como nulos.",
    )
    p.add_argument(
        "--minimo-observado",
        type=float,
        default=None,
        metavar="FRACCION",
        help=(
            "fraccion de la ventana que debe estar observada, entre 0 y 1. "
            "0.8 pide 24 de 30 dias y 3 de 3. Sin el, cualquier hueco anula la "
            "ventana."
        ),
    )
    args = p.parse_args()

    if args.minimo_observado is not None and not 0 < args.minimo_observado <= 1:
        print("\n--minimo-observado es una FRACCION de la ventana: 0 < f <= 1.\n")
        return 1

    try:
        from basedatos.conexion import conectar
    except ImportError as error:
        print(f"\nNo se pudo importar la conexion: {error}\n")
        return 1

    try:
        conexion = conectar()
    except Exception as error:  # noqa: BLE001
        print(f"\nLa base no responde: {error}")
        print("\n  Se levanta con:  docker compose up -d\n")
        return 1

    try:
        series, recuento = leer_mediciones(conexion.cursor(), args.incluir_imputados)
    finally:
        conexion.close()

    if not series:
        print("\n`crudo.medicion_diaria` esta vacia. Se carga con H1.1.\n")
        return 1

    matriz = construir(series, args.minimo_observado)
    matriz, constantes = sin_columnas_constantes(matriz)
    columnas = escribir(matriz, args.salida)
    r = rendimiento(matriz)

    print("\nMatriz de caracteristicas · H3.3\n")
    print(f"  distritos          {len(series)}")
    print(f"  filas leidas       {recuento['filas']}")
    print(
        f"  imputadas          {recuento['imputadas']} "
        f"({'incluidas' if args.incluir_imputados else 'tratadas como nulas'})"
    )
    print(f"  dias rellenados    {recuento.get('dias_rellenados', 0)}")
    print(f"  columnas           {len(columnas)}")
    if constantes:
        print(f"  constantes fuera   {len(constantes)}: {', '.join(constantes)}")
    print(f"  filas en la matriz {r['filas']}")
    print(f"  filas COMPLETAS    {r['completas']}  ({r['porcentaje']:.1f} %)\n")

    if r["porcentaje"] < 50:
        print("  AVISO: menos de la mitad de las filas sirven para entrenar.")
        print("  El estimador no imputa, asi que las otras no se usan. Opciones:")
        print("    --minimo-observado 0.8 relaja las ventanas")
        print("    --incluir-imputados    usa lo que puso H1.4\n")

    print(f"  escrito en {args.salida.relative_to(RAIZ)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
