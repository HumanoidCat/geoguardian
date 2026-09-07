"""
Verifica que la escala de riesgo cumple los criterios de accesibilidad.

Por que existe: elegir colores "que se vean bien" no es verificable. Esto lo es.
El script lee los colores directamente de frontend/src/estilos/tokens.css y
comprueba cuatro cosas, fallando si alguna no se cumple:

  1. La rampa mantiene un orden de luminancia monotono, asi que sigue leyendose
     impresa en blanco y negro o proyectada en un aula con mala luz.
  2. Los pasos vecinos se distinguen entre si.
  3. El orden se conserva bajo los tres tipos de dicromacia.
  4. El texto sobre cada nivel cumple el contraste minimo de WCAG AA, 4.5:1.
  5. El borde del distrito seleccionado se distingue sobre los cuatro fondos
     posibles, por luminancia y no por tono.

No usa ninguna biblioteca externa: solo la biblioteca estandar de Python.

Uso, desde la raiz del repositorio:

    python frontend/herramientas/verificar_escala.py

Historia H5.1. Rubrica de Computacion Grafica, criterio CG-1.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
TOKENS = RAIZ / "frontend" / "src" / "estilos" / "tokens.css"

CONTRASTE_MINIMO_AA = 4.5
CONTRASTE_MINIMO_VECINOS = 1.4

# Umbral de WCAG para elementos graficos y de interfaz, que no son texto. El
# borde de seleccion es exactamente eso: una forma, no una letra.
CONTRASTE_MINIMO_GRAFICO = 3.0

fallos: list[str] = []


# --------------------------------------------------------------------------- #
# Colorimetria                                                                  #
# --------------------------------------------------------------------------- #


def a_rgb(hexadecimal: str) -> tuple[int, int, int]:
    h = hexadecimal.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _lineal(canal: float) -> float:
    canal /= 255
    return canal / 12.92 if canal <= 0.04045 else ((canal + 0.055) / 1.055) ** 2.4


def luminancia(hexadecimal: str) -> float:
    r, g, b = (_lineal(c) for c in a_rgb(hexadecimal))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(uno: str, otro: str) -> float:
    """Razon de contraste de WCAG 2.1. Va de 1:1 a 21:1."""
    mayor, menor = sorted([luminancia(uno), luminancia(otro)], reverse=True)
    return (mayor + 0.05) / (menor + 0.05)


def gris(hexadecimal: str) -> int:
    """Luminancia percibida de 0 a 255. Es lo que ve una impresora en blanco y negro."""
    r, g, b = a_rgb(hexadecimal)
    return round(0.299 * r + 0.587 * g + 0.114 * b)


# Matrices de simulacion de dicromacia sobre RGB lineal.
# Fuente: Vienot, Brettel y Mollon (1999), "Digital video colourmaps for
# checking the legibility of displays by dichromats".
MATRICES = {
    "protanopia": ((0.1121, 0.8853, -0.0005), (0.1127, 0.8897, -0.0001), (0.0045, 0.0, 1.0)),
    "deuteranopia": ((0.292, 0.7054, -0.0003), (0.2934, 0.7089, 0.0), (-0.0209, 0.0257, 0.9997)),
    "tritanopia": ((1.0, 0.1502, -0.1387), (0.0, 0.8654, 0.1451), (0.0, 0.0, 1.0)),
}


def simular(hexadecimal: str, tipo: str) -> str:
    def a_srgb(canal: float) -> int:
        canal = min(max(canal, 0.0), 1.0)
        valor = 12.92 * canal if canal <= 0.0031308 else 1.055 * canal ** (1 / 2.4) - 0.055
        return round(valor * 255)

    rgb = [_lineal(c) for c in a_rgb(hexadecimal)]
    fila = MATRICES[tipo]
    salida = [sum(fila[i][j] * rgb[j] for j in range(3)) for i in range(3)]
    rojo, verde, azul = (a_srgb(c) for c in salida)
    return f"#{rojo:02x}{verde:02x}{azul:02x}"


# --------------------------------------------------------------------------- #
# Lectura de los tokens                                                         #
# --------------------------------------------------------------------------- #


def leer_tokens() -> dict[str, str]:
    """Lee los colores del CSS. Si el CSS cambia, esta verificacion lo sigue."""
    if not TOKENS.exists():
        raise SystemExit(f"ERROR: no existe {TOKENS}")
    texto = TOKENS.read_text(encoding="utf-8")
    return dict(re.findall(r"(--[a-z0-9-]+):\s*(#[0-9a-fA-F]{6})\s*;", texto))


def exigir(condicion: bool, descripcion: str, detalle: str = "") -> None:
    marca = "OK   " if condicion else "FALLA"
    print(f"  {marca} {descripcion}{('  ' + detalle) if detalle else ''}")
    if not condicion:
        fallos.append(descripcion)


def main() -> None:
    tokens = leer_tokens()

    try:
        rampa = {
            "bajo": tokens["--riesgo-bajo"],
            "medio": tokens["--riesgo-medio"],
            "alto": tokens["--riesgo-alto"],
        }
        textos = {
            "bajo": tokens["--texto-sobre-bajo"],
            "medio": tokens["--texto-sobre-medio"],
            "alto": tokens["--texto-sobre-alto"],
        }
    except KeyError as falta:
        raise SystemExit(f"ERROR: falta la variable {falta} en tokens.css") from None

    print(f"Escala de riesgo leida de {TOKENS.relative_to(RAIZ)}")
    for nivel, color in rampa.items():
        print(f"  {nivel:<6} {color}  gris {gris(color):>3}")

    print("\nLa rampa se lee en blanco y negro:")
    grises = [gris(c) for c in rampa.values()]
    exigir(
        grises == sorted(grises, reverse=True),
        "la luminancia baja de forma monotona de bajo a alto",
        str(grises),
    )

    print("\nLos pasos vecinos se distinguen:")
    niveles = list(rampa)
    for i in range(len(niveles) - 1):
        uno, otro = niveles[i], niveles[i + 1]
        razon = contraste(rampa[uno], rampa[otro])
        exigir(
            razon >= CONTRASTE_MINIMO_VECINOS,
            f"{uno} contra {otro}",
            f"{razon:.2f}:1  (minimo {CONTRASTE_MINIMO_VECINOS})",
        )

    print("\nEl orden se conserva con daltonismo:")
    for tipo in MATRICES:
        simulados = [gris(simular(c, tipo)) for c in rampa.values()]
        exigir(
            simulados == sorted(simulados, reverse=True),
            f"la rampa sigue ordenada bajo {tipo}",
            str(simulados),
        )

    print("\nEl texto sobre cada nivel es legible (WCAG AA, 4.5:1):")
    for nivel, color in rampa.items():
        razon = contraste(color, textos[nivel])
        exigir(
            razon >= CONTRASTE_MINIMO_AA,
            f"texto {textos[nivel]} sobre {nivel}",
            f"{razon:.2f}:1",
        )

    print("\nLa ausencia de dato no se confunde con un nivel de riesgo:")
    exigir(
        "--sin-dato-fondo" in tokens,
        "existe un color propio para la ausencia de dato",
    )
    exigir(
        tokens.get("--sin-dato-fondo") not in rampa.values(),
        "el color de ausencia de dato no es ninguno de la rampa",
    )
    exigir(
        ".trama-sin-dato" in TOKENS.read_text(encoding="utf-8"),
        "la ausencia de dato se distingue tambien por trama, no solo por color",
    )

    print("\nEl distrito seleccionado se distingue sobre cualquier relleno:")
    try:
        linea = tokens["--distrito-borde-activo"]
        halo = tokens["--distrito-halo-activo"]
    except KeyError as falta:
        raise SystemExit(f"ERROR: falta la variable {falta} en tokens.css") from None

    # Los cuatro fondos sobre los que puede caer el borde. La trama de ausencia
    # de dato aporta dos: el fondo y las rayas.
    fondos = {
        "riesgo bajo": rampa["bajo"],
        "riesgo medio": rampa["medio"],
        "riesgo alto": rampa["alto"],
        "trama sin dato": tokens.get("--sin-dato-trama", "#9e9e9e"),
        "fondo sin dato": tokens.get("--sin-dato-fondo", "#ffffff"),
    }

    # La marca no es una linea sola sino un par: linea clara con halo oscuro por
    # fuera. Ninguna de las dos contrasta sobre todos los fondos, y no hace falta
    # que lo haga: alcanza con que **alguna de las dos** lo consiga en cada uno.
    # Exigirselo a las dos obligaria a un color intermedio que no destaca sobre
    # ninguno, que es peor.
    for nombre, fondo in fondos.items():
        mejor = max(contraste(linea, fondo), contraste(halo, fondo))
        exigir(
            mejor >= CONTRASTE_MINIMO_GRAFICO,
            f"la marca de seleccion se ve sobre {nombre}",
            f"{mejor:.2f}:1  (minimo {CONTRASTE_MINIMO_GRAFICO})",
        )

    # Y las dos partes tienen que distinguirse entre si, o el halo desaparece
    # dentro de la linea y queda un trazo grueso de un solo color.
    razon = contraste(linea, halo)
    exigir(
        razon >= CONTRASTE_MINIMO_GRAFICO,
        "la linea y el halo se distinguen entre si",
        f"{razon:.2f}:1",
    )

    # El contraste de WCAG se calcula sobre luminancia, que es exactamente lo que
    # sobrevive a la dicromacia. Se comprueba igual bajo los tres tipos, porque
    # una marca que dependiera del tono pasaria el calculo anterior y fallaria
    # aqui.
    for tipo in MATRICES:
        peor = min(
            max(
                contraste(simular(linea, tipo), simular(fondo, tipo)),
                contraste(simular(halo, tipo), simular(fondo, tipo)),
            )
            for fondo in fondos.values()
        )
        exigir(
            peor >= CONTRASTE_MINIMO_GRAFICO,
            f"la seleccion se ve bajo {tipo}",
            f"{peor:.2f}:1 en el peor fondo",
        )

    # El negro puro se descarta explicitamente. No es una cuestion de gusto: a
    # 3 px sobre el amarillo palido era lo mas oscuro de la pantalla y competia
    # con las coropletas de riesgo alto, que son las que tienen que dominar.
    exigir(
        linea.lower() != "#000000",
        "la seleccion no se marca con negro puro",
        linea,
    )

    # ----------------------------------------------------------------------- #
    # H5.9, CA-5: los pares que faltaban.
    #
    # Hasta el 2026-09-06 este guion no miraba la trama de ausencia, el foco ni
    # el texto de la pagina, y la trama fallaba: #9e9e9e sobre blanco da 2.68:1,
    # por debajo del 3:1 grafico. Un control que solo mira lo que se arreglo no
    # sabe decir que no; estos pares se listan aca, no se deducen.
    # ----------------------------------------------------------------------- #
    print("\nLa ausencia de dato, el foco y el texto de la pagina cumplen (H5.9, CA-5):")
    fondo_sin_dato = tokens["--sin-dato-fondo"]
    pares_graficos = {
        "la trama de ausencia sobre su fondo": (tokens["--sin-dato-trama"], fondo_sin_dato),
        "el borde de ausencia sobre su fondo": (tokens["--sin-dato-borde"], fondo_sin_dato),
        "el foco sobre la superficie": (tokens["--foco"], tokens["--superficie"]),
        "el foco sobre la superficie alterna": (tokens["--foco"], tokens["--superficie-alterna"]),
        "el borde del distrito sobre riesgo bajo": (tokens["--distrito-borde"], rampa["bajo"]),
    }
    for descripcion, (figura, fondo) in pares_graficos.items():
        razon = contraste(figura, fondo)
        exigir(
            razon >= CONTRASTE_MINIMO_GRAFICO,
            descripcion,
            f"{razon:.2f}:1  (minimo {CONTRASTE_MINIMO_GRAFICO})",
        )

    pares_texto = {
        "el texto sobre la superficie": (tokens["--texto"], tokens["--superficie"]),
        "el texto suave sobre la superficie": (tokens["--texto-suave"], tokens["--superficie"]),
        "el texto suave sobre la superficie alterna": (
            tokens["--texto-suave"],
            tokens["--superficie-alterna"],
        ),
        "el texto sobre la ausencia de dato": (tokens["--texto-sobre-sin-dato"], fondo_sin_dato),
        "el texto sobre el fondo de aviso": (tokens["--texto"], tokens["--aviso-fondo"]),
        "el texto del modo simulado sobre su banda": (
            tokens["--simulado-texto"],
            tokens["--simulado-fondo"],
        ),
    }
    for descripcion, (texto, fondo) in pares_texto.items():
        razon = contraste(texto, fondo)
        exigir(
            razon >= CONTRASTE_MINIMO_AA,
            descripcion,
            f"{razon:.2f}:1  (minimo {CONTRASTE_MINIMO_AA})",
        )

    # `--texto-tenue` (#9e9e9e) NO se exige: da 2.68:1 y solo se usa para
    # metadatos decorativos que ya estan dichos en otro lado. Se deja anotado
    # para que nadie lo use como texto de lectura.
    razon = contraste(tokens["--texto-tenue"], tokens["--superficie"])
    print(f"  nota  el texto tenue sobre la superficie da {razon:.2f}:1: no sirve para leer")

    if fallos:
        print(f"\n{len(fallos)} verificaciones fallaron:")
        for fallo in fallos:
            print(f"  - {fallo}")
        sys.exit(1)

    print("\nTodas las verificaciones pasaron.")


if __name__ == "__main__":
    main()
