"""
Explicacion de predicciones individuales con SHAP. Historia H4.2.

Dueno: Luna, traspasada desde Alejandro el 2026-09-03 por **D-37**. La excepcion
sobre `backend/modelado` esta en `docs/07-propiedad-archivos.md`.

Criterios en `docs/evidencias/objetivos/H4.2-criterios-aceptacion.md`.

===========================================================================
LO PRIMERO, PORQUE CAMBIA COMO SE MIRA CADA FIGURA
===========================================================================

**Estos modelos no estan demostrados.**

  H3.6 y H3.8   ninguno le gana a la climatologica fuera del ruido.
  H4.1          de seis combinaciones de estimador y evento, cinco no tienen
                NINGUNA columna cuya importancia supere su propio rango entre
                pliegues; la sexta tiene una, y es negativa.

SHAP atribuye la salida del modelo a sus entradas. Lo hace igual de bien cuando
el modelo capta senal y cuando no capta nada: **descompone un numero, no explica
el mundo.** Una cascada de SHAP sobre un modelo que empata con un calendario se
ve exactamente igual que una sobre un modelo que funciona.

Por eso `encabezado()` existe y por eso ninguna figura se emite sin el. Es CA-7.

===========================================================================
LA REGLA DE SELECCION, FIJADA ANTES DE VER NINGUNA PREDICCION
===========================================================================

Elegir los ejemplos despues de mirarlos es la trampa clasica de esta tecnica: la
misma forma que **D-04** ataca en la particion y **H3.8** en la busqueda de
hiperparametros.

Cuatro por estimador y evento, uno por celda, definidas respecto de `alto`:

    ACIERTO_ALTO     verdad alto,    prediccion alto     -> el de MAYOR P(alto)
    FALSO_POSITIVO   verdad no alto, prediccion alto     -> el de MAYOR P(alto)
    FALSO_NEGATIVO   verdad alto,    prediccion no alto  -> el de MENOR P(alto)
    ACIERTO_BAJO     verdad bajo,    prediccion bajo     -> el de MAYOR P(alto)

Cada extremo esta elegido por una razon escrita, no por comodidad:

  * en el falso positivo, el de mayor probabilidad es **la alarma mas cara**;
  * en el falso negativo, el de menor probabilidad es el evento que el modelo
    **mas lejos estuvo de ver**;
  * en el acierto en bajo, el de mayor probabilidad es el que **mas cerca estuvo
    de equivocarse**, que es el unico acierto que informa algo.

Empates por fecha y luego por distrito. **No hay semilla porque no hay azar.**

**Las dos celdas de error son obligatorias.** Una seleccion que solo muestre
aciertos es el equivalente en SHAP a recortar los negativos en H4.1: una figura
mas prolija que esconde justo lo que hay que ver. Si una celda esta vacia se dice
que esta vacia; no se rellena con otra cosa.

===========================================================================
DOS DETALLES QUE DECIDEN SI LA ATRIBUCION VALE
===========================================================================

**1. La aditividad se comprueba, no se supone.** Las contribuciones tienen que
sumar la diferencia entre la salida del modelo y el valor base. SHAP puede
devolver numeros con cualquier forma; **esa suma es lo unico que demuestra que
son una descomposicion de la prediccion y no una ilustracion.** Es CA-4.

**2. El signo no se lee sin la clase.** En incendio la clase positiva es `bajo`,
por orden alfabetico ('alto' < 'bajo' < 'medio') y por SC-05. Una contribucion
positiva empuja hacia MENOS riesgo. Quien lea el signo sin mirar la clase
entiende el modelo exactamente al reves; `regresion_logistica.coeficientes` ya
documenta la misma trampa.

Uso:
    python -m backend.modelado.explicacion
    python -m backend.modelado.explicacion --salida <archivo>
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado.comparar import NO_MODELABLES, Observacion  # noqa: E402
from backend.modelado.evaluar_linea_base import COLUMNA  # noqa: E402
from backend.modelado.linea_base import DISTRITOS_CON_INCENDIO  # noqa: E402
from backend.modelado.particion import particionar  # noqa: E402
from contratos.enums import NivelRiesgo, TipoEvento  # noqa: E402

#: Tolerancia de la comprobacion de aditividad (CA-4). No es un umbral elegido
#: al gusto: es el error de redondeo acumulado de sumar decenas de flotantes de
#: doble precision. Si la diferencia lo supera, la atribucion esta mal.
TOLERANCIA_ADITIVIDAD = 1e-4

#: Las cuatro celdas, en el orden en que se muestran. El cuarto elemento dice si
#: dentro de la celda se toma la probabilidad MAYOR (True) o la MENOR (False).
CELDAS: tuple[tuple[str, str, bool], ...] = (
    ("acierto_alto", "acierto en alto: el que el modelo mas defiende", True),
    ("falso_positivo", "falso positivo: la alarma mas cara", True),
    ("falso_negativo", "falso negativo: el evento que mas lejos estuvo de ver", False),
    ("acierto_bajo", "acierto en bajo: el que mas cerca estuvo de equivocarse", True),
)


@dataclass(frozen=True)
class Caso:
    """Una fila elegida para explicar, con todo lo necesario para juzgarla."""

    celda: str
    descripcion: str
    codigo_distrito: str
    fecha: date
    verdad: NivelRiesgo
    prediccion: NivelRiesgo
    probabilidad_alto: float
    caracteristicas: dict[str, float]


@dataclass(frozen=True)
class Atribucion:
    """La descomposicion de UNA prediccion, con lo que la hace verificable."""

    caso: Caso
    clase_explicada: str
    valor_base: float
    salida: float
    contribuciones: dict[str, float]

    @property
    def suma(self) -> float:
        return sum(self.contribuciones.values())

    @property
    def residuo(self) -> float:
        """Lo que la descomposicion NO explica.

        Tiene que ser cero salvo redondeo. **Es la comprobacion de CA-4**, y va
        en el objeto y no en una prueba aparte porque quien lea una atribucion
        tiene que poder ver si esa atribucion cierra.
        """
        return (self.salida - self.valor_base) - self.suma

    @property
    def aditiva(self) -> bool:
        return abs(self.residuo) <= TOLERANCIA_ADITIVIDAD

    def ordenadas(self, cuantas: int | None = None) -> list[tuple[str, float]]:
        """Las contribuciones por magnitud, no por signo.

        Ordenar por valor pondria las negativas al fondo, y una contribucion
        negativa grande dice tanto como una positiva grande. Es la misma leccion
        que H4.1 aprendio cuando su unica columna distinguible quedo escondida al
        final de la tabla por ser negativa.
        """
        pares = sorted(self.contribuciones.items(), key=lambda kv: -abs(kv[1]))
        return pares[:cuantas] if cuantas else pares


def encabezado(evento: TipoEvento, nombre_estimador: str, veredicto: str, escritor: str) -> str:
    """Lo que tiene que viajar pegado a cada figura. Es CA-7.

    Una figura de SHAP **circula sola**: se pega en una presentacion, en el
    documento IEEE, en un mensaje. Si la advertencia vive en el texto que la
    rodea, se pierde en el primer copiado.
    """
    return (
        f"{evento.value.upper()} · {nombre_estimador}\n"
        f"  veredicto H3.6/H3.8: {veredicto}\n"
        f"  escribe analitico.riesgo: {escritor}\n"
        "  H4.1: ninguna columna de este modelo supera su propio ruido entre pliegues.\n"
        "  ESTA FIGURA DESCRIBE COMO DECIDE EL MODELO, NO POR QUE ACIERTA."
    )


def _p_alto(distribucion: dict[NivelRiesgo, float] | None) -> float | None:
    """P(alto) de una distribucion rotulada, o None si no hubo prediccion.

    Se lee por clave y no por posicion: `classes_` viene en orden alfabetico y
    `alto` no es siempre la primera. Es la misma razon por la que
    `probabilidades()` devuelve un diccionario rotulado.
    """
    if distribucion is None:
        return None
    return distribucion.get(NivelRiesgo.ALTO)


def elegir_casos(
    observaciones: list[Observacion],
    verdades: list[NivelRiesgo],
    predicciones: list[NivelRiesgo | None],
    probabilidades: list[dict[NivelRiesgo, float] | None],
) -> list[Caso]:
    """Los cuatro casos, por la regla del encabezado.

    Determinista: mismas entradas, mismos cuatro casos, en cualquier orden en que
    lleguen las filas. Es CA-1.
    """
    candidatos: dict[str, list[Caso]] = {celda: [] for celda, _, _ in CELDAS}

    for obs, verdad, prediccion, distribucion in zip(
        observaciones, verdades, predicciones, probabilidades, strict=True
    ):
        p = _p_alto(distribucion)
        if prediccion is None or p is None:
            # Una fila sin prediccion no se explica: no hay salida que
            # descomponer. Se cuenta aparte, no se rellena con cero.
            continue

        if verdad is NivelRiesgo.ALTO and prediccion is NivelRiesgo.ALTO:
            celda = "acierto_alto"
        elif verdad is not NivelRiesgo.ALTO and prediccion is NivelRiesgo.ALTO:
            celda = "falso_positivo"
        elif verdad is NivelRiesgo.ALTO and prediccion is not NivelRiesgo.ALTO:
            celda = "falso_negativo"
        elif verdad is NivelRiesgo.BAJO and prediccion is NivelRiesgo.BAJO:
            celda = "acierto_bajo"
        else:
            # Medio contra medio, y otras combinaciones sin celda. No se fuerzan
            # dentro de ninguna de las cuatro: la regla dice cuatro celdas y
            # meterlas donde entren seria cambiarla despues de mirar.
            continue

        candidatos[celda].append(
            Caso(
                celda=celda,
                descripcion=next(d for c, d, _ in CELDAS if c == celda),
                codigo_distrito=obs.codigo_distrito,
                fecha=obs.fecha,
                verdad=verdad,
                prediccion=prediccion,
                probabilidad_alto=p,
                caracteristicas=dict(obs.caracteristicas),
            )
        )

    elegidos = []
    for celda, _, mayor in CELDAS:
        if not candidatos[celda]:
            continue
        # El desempate por fecha y distrito hace la eleccion independiente del
        # orden de entrada, que es lo que el sabotaje del verificador comprueba.
        elegidos.append(
            sorted(
                candidatos[celda],
                key=lambda c: (
                    -c.probabilidad_alto if mayor else c.probabilidad_alto,
                    c.fecha,
                    c.codigo_distrito,
                ),
            )[0]
        )
    return elegidos


def celdas_vacias(casos: list[Caso]) -> list[str]:
    """Las celdas que no tuvieron ningun candidato.

    Se devuelven para poder DECIRLO. Una celda vacia es informacion -«este modelo
    no produjo ningun falso positivo en este pliegue»- y callarla deja la
    impresion de que se eligieron cuatro casos cuando fueron tres.
    """
    presentes = {c.celda for c in casos}
    return [celda for celda, _, _ in CELDAS if celda not in presentes]


def pliegues_de(
    evento: TipoEvento,
    filas: list,
    caracteristicas: dict[tuple[str, date], dict[str, float]],
    pliegues: list | None = None,
):
    """Los mismos cuatro pedazos que arman `comparar` e `importancia`.

    Se replica por lo mismo que en H4.1: `comparar` no lo expone por separado y
    esta historia no lo toca. El verificador comprueba la equivalencia contra
    `comparar()` en vez de darla por supuesta.
    """
    columna = COLUMNA[evento]
    if evento is TipoEvento.INCENDIO:
        filas = [f for f in filas if f[0] in DISTRITOS_CON_INCENDIO]

    def observacion(codigo: str, fecha: date) -> Observacion:
        return Observacion(codigo, fecha, caracteristicas.get((codigo, fecha), {}))

    for pliegue in pliegues if pliegues is not None else particionar(evento):
        ent = [
            (observacion(c, f), n[columna])
            for c, f, n in filas
            if pliegue.entrenamiento[0] <= f <= pliegue.entrenamiento[1] and n[columna] is not None
        ]
        pru = [
            (observacion(c, f), n[columna])
            for c, f, n in filas
            if pliegue.prueba[0] <= f <= pliegue.prueba[1] and n[columna] is not None
        ]
        if not ent or not pru:
            continue
        yield (
            [o for o, _ in ent],
            [e for _, e in ent],
            [o for o, _ in pru],
            [e for _, e in pru],
        )


def _valores_shap(
    funcion_probabilidad, columnas: list[str], filas: list[list[float]], fondo: list[list[float]]
):
    """Las atribuciones crudas de SHAP, con el valor base.

    EL CONJUNTO DE FONDO NO ES UN DETALLE TECNICO
    ---------------------------------------------

    SHAP no explica una prediccion en el vacio: la explica **respecto de una
    referencia**. El `valor_base` es la salida esperada del modelo sobre el
    conjunto de fondo, y cada contribucion dice cuanto se aleja esta fila de esa
    referencia. Cambiar el fondo cambia todos los numeros.

    Se descubrio al correr el verificador el 2026-09-07: sin fondo, SHAP se
    niega con «the passed model is not callable and cannot be analyzed directly
    with the given masker». La negativa es correcta y el criterio no lo preveia.

    **El fondo sale del ENTRENAMIENTO, nunca de la prueba.** Un fondo tomado del
    conjunto de prueba haria que el valor base dependiera de las filas que se
    estan explicando: la referencia y lo referido saldrian del mismo lugar. Es la
    misma fuga que D-04 prohibe en la particion, por una puerta mas discreta.

    Se explica sobre `probabilidades_crudas` del envoltorio y no sobre el objeto
    de la biblioteca: asi los
    tres estimadores se tratan igual, la salida vive en el espacio de
    probabilidad -que es el que el resto del proyecto usa por D-21- y **existe una
    funcion que se puede evaluar aparte** para comprobar el cableado.

    QUE COMPRUEBA DE VERDAD LA ADITIVIDAD, Y QUE NO
    -----------------------------------------------

    **Cualquier implementacion correcta de SHAP satisface la aditividad por
    construccion.** Comprobarla no verifica la matematica de la biblioteca: eso
    seria teatro, y el criterio lo decia mal.

    Lo que comprueba es **el cableado de esta historia**: que se tomo el indice
    de clase correcto, el valor base correcto y la fila correcta. Un error ahi no
    rompe nada visible -produce una figura impecable **de la clase equivocada**- y
    es exactamente el tipo de fallo contra el que sirve una identidad.

    Para eso hace falta la salida del modelo calculada por FUERA de SHAP. Por eso
    el explicador se construye sobre `predict_proba` -una funcion invocable- y la
    salida se pide al modelo directamente.

    La primera version calculaba la salida como `valor_base + suma`, con lo cual
    el residuo daba cero por construccion y **la comprobacion no podia fallar
    jamas**. Lo delato el verificador del 2026-09-07: `residuo maximo 0.00e+00`,
    exactamente cero sobre decenas de sumas de flotantes, que es demasiado limpio
    para ser cierto.
    """
    import numpy as np
    import shap

    entrada = np.asarray(filas, dtype=float)
    explicador = shap.Explainer(
        funcion_probabilidad, np.asarray(fondo, dtype=float), feature_names=columnas
    )
    return explicador(entrada), np.asarray(funcion_probabilidad(entrada))


def fondo_de(observaciones: list[Observacion], columnas: list[str]) -> list[list[float]]:
    """El conjunto de referencia, armado desde las observaciones de ENTRENAMIENTO.

    Se expone como funcion propia para que en la llamada se vea de donde sale.
    Si un dia alguien le pasa las de prueba, el cambio se lee en el diff en vez
    de esconderse dentro de `explicar`.
    """
    return [[o.caracteristicas.get(c, 0.0) for c in columnas] for o in observaciones]


def explicar(
    modelo,
    casos: list[Caso],
    columnas: list[str],
    fondo: list[list[float]],
    clase_alto: int | None = None,
) -> list[Atribucion]:
    """Descompone la prediccion de cada caso, respecto del conjunto de `fondo`.

    `fondo` tiene que venir del ENTRENAMIENTO. Ver `_valores_shap`: define el
    valor base, y tomarlo de la prueba seria una fuga.

    `clase_alto` es el indice de la clase `alto` en la salida del modelo, para
    los estimadores que devuelven una atribucion por clase. Se pasa desde afuera
    y no se adivina: adivinarlo por posicion es la forma de leer el signo al
    reves.
    """
    import numpy as np

    # Se explica la FUNCION del envoltorio, no el modelo desnudo. Ver
    # `probabilidades_crudas`: el objeto de la biblioteca es un objeto a medias
    # cuando el estimador guarda un escalador aparte, y explicarlo produce una
    # descomposicion impecable de un numero que no es la prediccion.
    funcion = modelo.probabilidades_crudas

    # EL ORDEN DE COLUMNAS LO MANDA EL MODELO, NO QUIEN LLAMA.
    #
    # Construir la matriz en otro orden no falla: entrena bien, predice bien y
    # explica al reves, atribuyendo a `pp_acum30` lo que hizo `hr_media7`. Se
    # toma de `columnas_ajustadas` para que no haya nada que adivinar.
    columnas = modelo.columnas_ajustadas or columnas
    if not fondo:
        raise ValueError("hace falta un conjunto de fondo, y tiene que salir del entrenamiento")

    filas = [[caso.caracteristicas.get(c, 0.0) for c in columnas] for caso in casos]
    if not filas:
        return []

    salida, salidas_modelo = _valores_shap(funcion, columnas, filas, fondo)

    atribuciones = []
    for i, caso in enumerate(casos):
        valores = np.asarray(salida.values[i])
        base = np.asarray(salida.base_values[i])

        # Modelos multiclase: SHAP devuelve una matriz (columnas x clases) y hay
        # que quedarse con la de `alto`. Se elige por INDICE RECIBIDO, nunca por
        # posicion supuesta.
        if valores.ndim > 1:
            if clase_alto is None:
                raise ValueError(
                    "el modelo devuelve una atribucion por clase y no se dijo cual es 'alto'"
                )
            valores = valores[:, clase_alto]
            base = base[clase_alto] if base.ndim else base

        # La salida REAL del modelo, por el otro camino. No se calcula como
        # base + suma: eso haria el residuo cero por construccion y CA-4 no
        # podria fallar nunca.
        real = np.asarray(salidas_modelo[i])
        if real.ndim:
            if clase_alto is None:
                raise ValueError(
                    "el modelo devuelve una salida por clase y no se dijo cual es 'alto'"
                )
            real = real[clase_alto]

        contribuciones = dict(zip(columnas, [float(v) for v in valores], strict=True))
        atribuciones.append(
            Atribucion(
                caso=caso,
                clase_explicada=NivelRiesgo.ALTO.value,
                valor_base=float(base),
                salida=float(real),
                contribuciones=contribuciones,
            )
        )
    return atribuciones


def main() -> int:
    p = argparse.ArgumentParser(description="Explicacion de predicciones · H4.2.")
    p.add_argument("--columnas", type=int, default=8, help="cuantas contribuciones mostrar")
    p.add_argument("--salida", type=Path, default=None, help="ademas de la pantalla, en UTF-8")
    args = p.parse_args()

    # El archivo lo escribe Python y no la consola, por lo mismo que en H4.1: con
    # `>` de PowerShell la pantalla queda muda y el archivo sale en UTF-16.
    archivo = open(args.salida, "w", encoding="utf-8") if args.salida else None  # noqa: SIM115

    def emitir(texto: str = "") -> None:
        print(texto, flush=True)
        if archivo:
            archivo.write(texto + "\n")
            archivo.flush()

    from backend.modelado.afinar import CARACTERISTICAS, ETIQUETAS, cargar, fabricas
    from backend.modelado.comparar import CON_CARACTERISTICAS, comparar, elegir_escritor, veredicto
    from backend.modelado.importancia import columnas_de

    if not ETIQUETAS.exists() or not CARACTERISTICAS.exists():
        emitir("\nHacen falta las dos: etiquetas.csv y caracteristicas.csv. Con la base levantada:")
        emitir("\n    python -m backend.modelado.generar_etiquetas")
        emitir("    python -m backend.modelado.generar_caracteristicas\n")
        return 1

    filas, caracteristicas = cargar()
    emitir("\nExplicacion de predicciones individuales · H4.2")
    emitir("  metodo    SHAP sobre el ultimo pliegue de H3.2")
    emitir("  modelos   los AFINADOS de H3.8, que son los que corre la tuberia")
    emitir("  casos     4 por estimador, por la regla de los criterios (sin azar)\n")

    for evento in TipoEvento:
        if evento in NO_MODELABLES:
            emitir(f"{evento.value.upper()}: no modelable. {NO_MODELABLES[evento]}\n")
            continue

        todas = fabricas(evento, True)
        resultados = comparar(evento, filas, todas, caracteristicas)
        escritor, _ = elegir_escritor(resultados)
        dictamen = veredicto(resultados)

        aprenden = {n: f for n, f in todas.items() if n in CON_CARACTERISTICAS}
        for nombre, fabrica in aprenden.items():
            emitir(encabezado(evento, nombre, dictamen, str(escritor)))

            ultimo = None
            for pedazo in pliegues_de(evento, filas, caracteristicas):
                ultimo = pedazo
            if ultimo is None:
                emitir("  sin pliegues evaluables\n")
                continue

            obs_ent, eti_ent, obs_pru, verdad = ultimo
            try:
                modelo = fabrica().ajustar(obs_ent, eti_ent)
                predicciones = modelo.predecir(obs_pru)
                distribuciones = modelo.probabilidades(obs_pru)
            except ValueError as motivo:
                emitir(f"  no se pudo ajustar: {motivo}\n")
                continue

            casos = elegir_casos(obs_pru, verdad, predicciones, distribuciones)
            vacias = celdas_vacias(casos)
            if vacias:
                emitir(f"  celdas SIN ningun caso: {', '.join(vacias)}")

            columnas = columnas_de(obs_pru)
            # El fondo sale de ENTRENAMIENTO. Ver `_valores_shap`.
            fondo = fondo_de(obs_ent, columnas)
            try:
                atribuciones = explicar(modelo, casos, columnas, fondo, clase_alto=0)
            except Exception as error:  # noqa: BLE001
                emitir(f"  SHAP no pudo explicar: {error}\n")
                continue

            for a in atribuciones:
                c = a.caso
                emitir(
                    f"\n  [{c.celda}] {c.descripcion}"
                    f"\n    distrito {c.codigo_distrito}  fecha {c.fecha}"
                    f"  verdad {c.verdad.value}  prediccion {c.prediccion.value}"
                    f"  P(alto) {c.probabilidad_alto:.3f}"
                )
                # La salida explicada tiene que ser la MISMA probabilidad que
                # decidio la celda. Si no coinciden, se explico otra cosa: es lo
                # que paso el 2026-09-07 con la regresion logistica, y lo que la
                # aditividad no puede ver porque sus dos lados salen del mismo
                # camino.
                coincide = abs(a.salida - c.probabilidad_alto) <= 1e-6
                emitir(
                    f"    valor base {a.valor_base:+.4f}   salida {a.salida:+.4f}"
                    f"   residuo {a.residuo:+.2e}"
                    f"   {'ADITIVA' if a.aditiva else 'NO ADITIVA — la atribucion esta mal'}"
                    f"   {'' if coincide else '  ¡SALIDA != P(alto): se explico otra cosa!'}"
                )
                for columna, valor in a.ordenadas(args.columnas):
                    emitir(f"      {columna:24}{valor:+.4f}")
            emitir()

    emitir(
        "Como leerla. La contribucion es cuanto mueve esa columna la salida del\n"
        "modelo para ESA fila, respecto del valor base. Se ordenan por MAGNITUD y\n"
        "no por signo. El residuo tiene que ser cero salvo redondeo: si no lo es,\n"
        "la descomposicion no cierra y la figura no significa nada (CA-4).\n"
    )
    if archivo:
        archivo.close()
        print(f"Escrito {args.salida}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
