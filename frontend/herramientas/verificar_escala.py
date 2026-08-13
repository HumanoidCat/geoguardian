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
    return "#%02x%02x%02x" % tuple(a_srgb(c) for c in salida)


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

    if fallos:
        print(f"\n{len(fallos)} verificaciones fallaron:")
        for fallo in fallos:
            print(f"  - {fallo}")
        sys.exit(1)

    print("\nTodas las verificaciones pasaron.")


if __name__ == "__main__":
    main()
