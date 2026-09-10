"""
Verifica que la primera pantalla hable en palabras y no en jerga.

Por que existe: «ninguna sigla en la primera pantalla» es una regla de tono, y
una regla de tono que nadie comprueba se rompe en el tercer cambio. Esto la
convierte en algo que falla en el CI, igual que hizo H5.9 con la escala
tipografica.

Lee `frontend/src/datos/palabras.js` -donde vive todo lo que la pantalla le dice
a una persona- y `frontend/src/componentes/HoyEnTuDistrito.jsx`, y comprueba:

  1. Ninguna sigla tecnica en el texto visible. CHIRPS, POWER, FIRMS, SPI, R95p,
     P95, P99, ETCCDI, SHAP, XGBoost y los nombres de algoritmo viven un nivel
     mas abajo, dentro de «de donde sale esto», que arranca cerrado.
  2. Los tres niveles tienen su palabra Y su termino tecnico. La traduccion se
     muestra, no se esconde: es lo que evita que el producto hable dos idiomas
     en dos pantallas.
  3. Cada frase de nivel esta en segunda persona y lleva un verbo de accion.
  4. Cada evento declara que decir cuando NO hay estimacion. Sin eso, un evento
     sin dato se dibuja en blanco y se lee como un fallo.
  5. Ninguna frase promete «tiempo real».

No usa ninguna biblioteca externa: solo la biblioteca estandar de Python.

Uso, desde la raiz del repositorio:

    python frontend/herramientas/verificar_frases.py

Historia H14.2, CA-6. Rubrica de Computacion Grafica, CG-1.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PALABRAS = RAIZ / "frontend" / "src" / "datos" / "palabras.js"
PANTALLA = RAIZ / "frontend" / "src" / "componentes" / "HoyEnTuDistrito.jsx"

# Lo que no puede aparecer en la primera pantalla. No es una lista de palabras
# feas: es la lista de cosas que solo significan algo si ya sabes de que van.
SIGLAS = [
    "CHIRPS",
    "POWER",
    "FIRMS",
    "SPI",
    "R95p",
    "R99p",
    "ETCCDI",
    "SHAP",
    "XGBoost",
    "random forest",
    "regresion logistica",
    "percentil",
    "P95",
    "P99",
    "NDVI",
    "NDWI",
    "GeoJSON",
    "API",
]

# Verbos en segunda persona del voseo, que es como se habla en el canton. Una
# frase de accion sin verbo es una descripcion, y una descripcion no dice que
# hacer.
VERBOS = re.compile(
    r"\b(revisa|compra|evita|segui|fijate|avisa|llama|prepara|no quemes|no salgas|elegi)\b",
    re.IGNORECASE,
)

fallos: list[str] = []


def exigir(condicion: bool, descripcion: str, detalle: str = "") -> None:
    marca = "OK   " if condicion else "FALLA"
    print(f"  {marca} {descripcion}{('  ' + detalle) if detalle else ''}")
    if not condicion:
        fallos.append(descripcion)


def texto_visible(fuente: str) -> str:
    """El texto que una persona puede leer, sin comentarios ni nombres de codigo.

    Los comentarios se quitan porque ahi SI se nombran las siglas, y con razon:
    explicar por que una sigla no puede estar en pantalla obliga a escribirla.
    """
    sin_bloques = re.sub(r"/\*.*?\*/", " ", fuente, flags=re.S)
    sin_linea = re.sub(r"^\s*//.*$", " ", sin_bloques, flags=re.M)
    return sin_linea


def autoprueba() -> None:
    """Comprueba que este guion sabe decir que NO.

    Un control que solo mira lo que ya esta arreglado no sabe fallar, y entonces
    su verde no significa nada. Antes de revisar los archivos de verdad, se le
    dan casos que TIENEN que reprobar y casos que tienen que pasar.
    """
    print("El propio verificador sabe fallar:")
    casos = [
        (
            "detecta una sigla escondida en una frase",
            re.search(r"\bCHIRPS\b", "Lluvia medida por CHIRPS esta semana", re.IGNORECASE)
            is not None,
        ),
        (
            "no confunde una sigla con parte de otra palabra",
            re.search(r"\bAPI\b", "Rapido y facil", re.IGNORECASE) is None,
        ),
        (
            "acepta una frase con verbo en segunda persona",
            VERBOS.search("Revisa el camino antes de salir.") is not None,
        ),
        (
            "rechaza una frase sin verbo de accion",
            VERBOS.search("Se recomienda precaucion en la zona.") is None,
        ),
        (
            "quita los comentarios antes de buscar",
            "CHIRPS"
            not in texto_visible("// se explica por que CHIRPS no puede estar\nconst a = 1"),
        ),
    ]
    for descripcion, condicion in casos:
        exigir(condicion, descripcion)
    print()


def main() -> None:
    autoprueba()

    for ruta in (PALABRAS, PANTALLA):
        if not ruta.exists():
            raise SystemExit(f"ERROR: no existe {ruta}")

    fuente_palabras = PALABRAS.read_text(encoding="utf-8")
    fuente_pantalla = PANTALLA.read_text(encoding="utf-8")
    visible_palabras = texto_visible(fuente_palabras)
    visible_pantalla = texto_visible(fuente_pantalla)

    # El bloque «de donde sale esto» SI puede nombrarlas: es el nivel de abajo, y
    # arranca cerrado. Se recorta antes de buscar.
    sin_detalle = re.sub(
        r"<details className=\"hoy-de-donde\">.*?</details>",
        " ",
        visible_pantalla,
        flags=re.S,
    )

    print("Ninguna sigla en la primera pantalla (H14.2, CA-6):")
    for sigla in SIGLAS:
        patron = re.compile(rf"\b{re.escape(sigla)}\b", re.IGNORECASE)
        donde = []
        if patron.search(visible_palabras):
            donde.append(PALABRAS.name)
        if patron.search(sin_detalle):
            donde.append(PANTALLA.name)
        exigir(not donde, f"no aparece «{sigla}»", ", ".join(donde))

    print("\nEl bloque de detalle existe y arranca cerrado:")
    exigir(
        'className="hoy-de-donde"' in fuente_pantalla,
        "hay un nivel de abajo donde viven las siglas",
    )
    exigir(
        not re.search(r"<details className=\"hoy-de-donde\"\s+open", fuente_pantalla),
        "arranca cerrado, para que no compita con las tarjetas",
    )

    print("\nLos tres niveles traen palabra y termino tecnico:")
    for nivel, palabra in (("bajo", "tranquilo"), ("medio", "atento"), ("alto", "cuidado")):
        bloque = re.search(rf"{nivel}:\s*\{{(.*?)\}},", fuente_palabras, flags=re.S)
        cuerpo = bloque.group(1) if bloque else ""
        exigir(f"'{palabra}'" in cuerpo, f"{nivel} se dice «{palabra}»")
        exigir(
            re.search(r"tecnico:\s*'riesgo ", cuerpo) is not None,
            f"{nivel} muestra tambien su termino tecnico",
        )

    print("\nCada frase de accion lleva un verbo en segunda persona:")
    acciones = re.findall(r"hacer:\s*\[(.*?)\]", fuente_palabras, flags=re.S)
    exigir(bool(acciones), "hay listas de acciones que revisar", f"{len(acciones)} listas")
    for lista in acciones:
        for frase in re.findall(r"'([^']+)'", lista):
            exigir(VERBOS.search(frase) is not None, f"«{frase}»")

    print("\nCada evento sabe que decir cuando no hay estimacion:")
    ausencias = re.findall(r"ausencia:\s*\n?\s*'([^']*)'", fuente_palabras)
    exigir(
        len(ausencias) >= 3,
        "los tres eventos declaran su frase de ausencia",
        f"{len(ausencias)} encontradas",
    )

    print("\nNadie promete «tiempo real»:")
    exigir(
        not re.search(r"tiempo real", visible_palabras + sin_detalle, re.IGNORECASE),
        "la pantalla no dice «tiempo real» en ningun lado",
    )

    if fallos:
        print(f"\n{len(fallos)} verificaciones fallaron:")
        for fallo in fallos:
            print(f"  - {fallo}")
        sys.exit(1)

    print("\nTodas las verificaciones pasaron.")


if __name__ == "__main__":
    main()
