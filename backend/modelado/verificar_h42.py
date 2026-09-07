"""
Verificador de H4.2 · Explicacion de predicciones individuales con SHAP.

Dueno: Luna, traspasada desde Alejandro por **D-37**.
Criterios en `docs/evidencias/objetivos/H4.2-criterios-aceptacion.md`.

CORRE SIN BASE Y SIN RED. Necesita `shap` y `scikit-learn`, que estan en
`requirements.txt` y en el CI. Es CA-9.

LO QUE ESTE VERIFICADOR DECIDE
------------------------------

No comprueba que SHAP calcule bien: eso lo hace una biblioteca probada por otros
y desconfiar de ella aqui seria teatro. Comprueba **todo lo que la rodea**, que es
donde esta historia puede fallar produciendo figuras igual de convincentes:

  * que la seleccion no dependa del orden de entrada,
  * que las celdas de error aparezcan,
  * que la descomposicion CIERRE contra la prediccion real del modelo,
  * y que un error en cualquiera de esas tres se NOTE.

LOS TRES SABOTAJES
------------------

 10. Se rompe la aditividad a mano y se exige que `aditiva` lo diga. Sin esto,
     CA-4 seria una propiedad que nadie comprobo que sepa fallar.
 11. Se explica un modelo SIN ajustar y se exige que se niegue, en vez de
     devolver ceros con cara de explicacion.
 12. Se le da un conjunto donde NO hay falsos positivos y se exige que la celda
     salga declarada vacia, en vez de rellenarse con otro caso.

Uso:
    python -m backend.modelado.verificar_h42
"""

from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado.comparar import Observacion  # noqa: E402
from backend.modelado.explicacion import (  # noqa: E402
    TOLERANCIA_ADITIVIDAD,
    Atribucion,
    celdas_vacias,
    elegir_casos,
    encabezado,
    explicar,
    fondo_de,
    pliegues_de,
)
from backend.modelado.particion import Pliegue  # noqa: E402
from contratos.enums import NivelRiesgo, TipoEvento  # noqa: E402

ALTO = NivelRiesgo.ALTO
BAJO = NivelRiesgo.BAJO
INICIO = date(2022, 1, 1)
COLUMNAS = ["util", "ruido"]


class Resultado:
    def __init__(self) -> None:
        self.fallos: list[str] = []
        self.hechos = 0

    def comprobar(self, nombre: str, condicion: bool, detalle: str = "") -> None:
        self.hechos += 1
        print(f"  {'ok   ' if condicion else 'FALLA'}  {nombre}")
        if not condicion:
            self.fallos.append(f"{nombre}{': ' + detalle if detalle else ''}")
        elif detalle:
            print(f"           {detalle}")


def _p(valor: float) -> dict[NivelRiesgo, float]:
    return {ALTO: valor, BAJO: 1.0 - valor}


def _obs(dia: int, codigo: str = "50801", x: float = 0.0) -> Observacion:
    return Observacion(codigo, INICIO + timedelta(days=dia), {"util": x, "ruido": float(dia % 3)})


def escenario():
    """Las cuatro celdas pobladas, con un extremo claro en cada una."""
    filas = [
        (0, ALTO, ALTO, 0.70),
        (1, ALTO, ALTO, 0.95),
        (2, BAJO, ALTO, 0.60),
        (3, BAJO, ALTO, 0.99),
        (4, ALTO, BAJO, 0.40),
        (5, ALTO, BAJO, 0.02),
        (6, BAJO, BAJO, 0.05),
        (7, BAJO, BAJO, 0.49),
    ]
    return (
        [_obs(d) for d, _, _, _ in filas],
        [v for _, v, _, _ in filas],
        [p for _, _, p, _ in filas],
        [_p(q) for _, _, _, q in filas],
    )


def _modelo_real():
    """Una regresion logistica de verdad, ajustada sobre una senal conocida.

    Se usa el estimador DEL PROYECTO y no uno de sklearn suelto: lo que hay que
    comprobar es que `modelo_interno` entregue algo que SHAP pueda descomponer, y
    eso solo lo demuestra el objeto real.
    """
    from backend.modelado.regresion_logistica import RegresionLogistica

    observaciones, etiquetas = [], []
    for i in range(80):
        util = 1.0 if i % 2 == 0 else 0.0
        observaciones.append(_obs(i, x=util))
        etiquetas.append(ALTO if util else BAJO)
    return RegresionLogistica().ajustar(observaciones, etiquetas), observaciones, etiquetas


def verificar() -> Resultado:
    r = Resultado()
    print("\nExplicacion de predicciones individuales · H4.2\n")

    obs, verdades, predicciones, probabilidades = escenario()
    casos = elegir_casos(obs, verdades, predicciones, probabilidades)

    # ------------------------------------------------------------------ 1
    r.comprobar(
        "1. elige una por celda, y las cuatro celdas",
        [c.celda for c in casos]
        == ["acierto_alto", "falso_positivo", "falso_negativo", "acierto_bajo"],
        f"salieron {[c.celda for c in casos]}",
    )

    # ------------------------------------------------------------------ 2
    porcelda = {c.celda: c for c in casos}
    r.comprobar(
        "2. dentro de cada celda toma el extremo declarado",
        porcelda["acierto_alto"].probabilidad_alto == 0.95
        and porcelda["falso_positivo"].probabilidad_alto == 0.99
        and porcelda["falso_negativo"].probabilidad_alto == 0.02
        and porcelda["acierto_bajo"].probabilidad_alto == 0.49,
        "en el falso negativo se toma la MENOR: el evento que mas lejos estuvo de ver",
    )

    # ------------------------------------------------------------------ 3
    esperados = [(c.celda, c.fecha) for c in casos]
    indices = list(range(len(obs)))
    generador = random.Random("H4.2")
    estable = True
    for _ in range(8):
        generador.shuffle(indices)
        revueltos = elegir_casos(
            [obs[i] for i in indices],
            [verdades[i] for i in indices],
            [predicciones[i] for i in indices],
            [probabilidades[i] for i in indices],
        )
        estable = estable and [(c.celda, c.fecha) for c in revueltos] == esperados
    r.comprobar(
        "3. la seleccion no depende del orden de entrada (CA-1)",
        estable,
        "ocho barajadas, la misma eleccion",
    )

    # ------------------------------------------------------------------ 4
    sin_prediccion = elegir_casos([_obs(0), _obs(1)], [ALTO, ALTO], [None, ALTO], [None, _p(0.9)])
    r.comprobar(
        "4. una fila sin prediccion no se explica",
        len(sin_prediccion) == 1,
        "no hay salida que descomponer; no se inventa una",
    )

    # ------------------------------------------------------------------ 5
    r.comprobar(
        "5. el encabezado lleva la advertencia pegada (CA-7)",
        "NO POR QUE ACIERTA"
        in encabezado(TipoEvento.LLUVIA_INTENSA, "xgboost", "empate", "climatologica"),
        "una figura circula sola; la advertencia tiene que viajar con ella",
    )

    # ------------------------------------------------------------------ 6
    pliegue = Pliegue(
        indice=0,
        entrenamiento=(INICIO, INICIO + timedelta(days=9)),
        prueba=(INICIO + timedelta(days=10), INICIO + timedelta(days=19)),
        embargo=None,
    )
    filas = [
        ("50801", INICIO + timedelta(days=i), {"lluvia_intensa": ALTO if i % 2 else BAJO})
        for i in range(20)
    ]
    caracteristicas = {(c, f): {"util": 1.0} for c, f, _ in filas}
    pedazos = list(pliegues_de(TipoEvento.LLUVIA_INTENSA, filas, caracteristicas, [pliegue]))
    _, _, obs_pru, _ = pedazos[0]
    r.comprobar(
        "6. lo que se explica sale del bloque de PRUEBA (CA-2)",
        bool(obs_pru) and all(o.fecha >= pliegue.prueba[0] for o in obs_pru),
        f"{len(obs_pru)} filas, todas desde {pliegue.prueba[0]}",
    )

    # ------------------------------------------------------------------ 7, 8 y 9
    #
    # Aca entra SHAP de verdad, sobre el estimador del proyecto.
    modelo, observaciones, _ = _modelo_real()
    fondo = fondo_de(observaciones, COLUMNAS)
    a_explicar = elegir_casos(
        observaciones,
        [ALTO if o.caracteristicas["util"] else BAJO for o in observaciones],
        modelo.predecir(observaciones),
        modelo.probabilidades(observaciones),
    )
    try:
        atribuciones = explicar(modelo, a_explicar, COLUMNAS, fondo, clase_alto=0)
        fallo_shap = ""
    except Exception as error:  # noqa: BLE001
        atribuciones, fallo_shap = [], str(error).splitlines()[0]

    r.comprobar(
        "7. `modelo_interno` entrega algo que SHAP puede descomponer",
        bool(atribuciones),
        fallo_shap or f"{len(atribuciones)} atribuciones",
    )

    if atribuciones:
        r.comprobar(
            "8. la descomposicion CIERRA contra la prediccion (CA-4)",
            all(a.aditiva for a in atribuciones),
            f"residuo maximo {max(abs(a.residuo) for a in atribuciones):.2e}"
            f", tolerancia {TOLERANCIA_ADITIVIDAD:.0e}",
        )
        r.comprobar(
            "9. las contribuciones se leen por nombre de columna (CA-5)",
            all(set(a.contribuciones) == set(COLUMNAS) for a in atribuciones),
        )

    # ------------------------------------------------------------------ 9b
    #
    # EL FONDO ES OBLIGATORIO, Y NO ES UN TRAMITE.
    #
    # SHAP explica una prediccion RESPECTO DE UNA REFERENCIA: el valor base es la
    # salida esperada sobre el conjunto de fondo. Sin fondo no hay contra que
    # medir, y SHAP se niega -lo descubrio este verificador el 2026-09-07-.
    #
    # Que el fondo salga del ENTRENAMIENTO no es cosmetico: si saliera de la
    # prueba, la referencia y lo referido vendrian del mismo lugar. Es la fuga de
    # D-04 por una puerta mas discreta, y ninguna metrica la mostraria.
    sin_fondo = False
    try:
        explicar(modelo, a_explicar[:1], COLUMNAS, [], clase_alto=0)
    except ValueError:
        sin_fondo = True
    r.comprobar(
        "9b. explicar SIN conjunto de fondo se niega",
        sin_fondo,
        "el fondo define el valor base; sin el no hay contra que medir",
    )

    # ------------------------------------------------------------------ 10
    #
    # SABOTAJE: una descomposicion que no cierra.
    rota = Atribucion(
        caso=a_explicar[0] if a_explicar else casos[0],
        clase_explicada=ALTO.value,
        valor_base=0.2,
        salida=0.9,
        contribuciones={"util": 0.1},
    )
    r.comprobar(
        "10. SABOTAJE: una descomposicion que no cierra se marca",
        not rota.aditiva and abs(rota.residuo) > 0.5,
        f"residuo {rota.residuo:+.3f}: sin esto, CA-4 seria una propiedad que nunca fallo",
    )

    # ------------------------------------------------------------------ 11
    #
    # SABOTAJE: explicar un modelo sin ajustar.
    from backend.modelado.regresion_logistica import RegresionLogistica

    try:
        explicar(RegresionLogistica(), casos[:1], COLUMNAS, fondo, clase_alto=0)
        se_nego = False
    except ValueError:
        se_nego = True
    r.comprobar(
        "11. SABOTAJE: un modelo sin ajustar se niega a explicarse",
        se_nego,
        "devolver ceros con cara de explicacion seria peor que fallar",
    )

    # ------------------------------------------------------------------ 12
    #
    # SABOTAJE: un conjunto sin falsos positivos.
    solo_aciertos = elegir_casos([_obs(0)], [ALTO], [ALTO], [_p(0.9)])
    vacias = celdas_vacias(solo_aciertos)
    r.comprobar(
        "12. SABOTAJE: las celdas sin casos se declaran, no se rellenan (CA-3)",
        vacias == ["falso_positivo", "falso_negativo", "acierto_bajo"],
        f"vacias: {', '.join(vacias)}",
    )

    return r


def main() -> int:
    try:
        import shap  # noqa: F401
    except ImportError:
        print(
            f"\nEste Python no tiene shap:\n  {sys.executable}\n\n"
            "Comproba primero que el entorno virtual este activo:\n\n"
            "    .\\.venv\\Scripts\\Activate.ps1\n\n"
            "Solo si YA estas dentro del venv y aun asi falta:\n\n"
            "    pip install -r requirements.txt\n"
        )
        return 1

    resultado = verificar()
    print(f"\n{resultado.hechos - len(resultado.fallos)} de {resultado.hechos} comprobaciones")
    if resultado.fallos:
        print("\nNO se cumplen:")
        for f in resultado.fallos:
            print(f"  - {f}")
        print()
        return 1
    print(
        "\nEl arnes de H4.2 cumple. Lo que NO comprueba este verificador:\n"
        "la corrida real, que necesita etiquetas.csv y caracteristicas.csv, y\n"
        "**si las explicaciones significan algo**, que no es una pregunta de\n"
        "codigo: los modelos que explica no superan a la climatologica.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
