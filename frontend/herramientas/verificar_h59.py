"""
Verifica dos criterios de H5.9 que se pueden comprobar sin navegador.

  CA-2  Ninguna frase visible afirma algo falso sobre el sistema. En concreto,
        ninguna variante de "no hay modelo entrenado" sobrevive en frontend/src,
        comentarios incluidos: los comentarios fueron los que sobrevivieron al
        cierre de H3.4 y son la version de I-41 en el frontend.

  CA-9  El visor tiene jerarquia tipografica EN USO, no solo declarada. La escala
        (--texto-xs a --texto-xl) existia desde H5.1; lo que estaba mal, medido el
        2026-09-06, era la distribucion: xs 32 veces, sm 15, md 2, lg 2, xl 1.
        Casi todo el visor estaba escrito en 12 y 14 px. Se exige que xs no pase
        de un tercio de los usos y que md o mayor sea al menos otro tercio, y que
        ningun archivo fuera de tokens.css escriba un font-size literal.

Por que existe: los dos criterios se pueden poner en verde sin hacer nada si
solo los mira una persona. Este control sabe decir que no, y lo demuestra: antes
de mirar el repositorio se prueba a si mismo con una frase prohibida (tiene que
detectarla) y una parecida pero correcta (no tiene que detectarla).

No usa ninguna biblioteca externa: solo la biblioteca estandar de Python.

Uso, desde la raiz del repositorio:

    python frontend/herramientas/verificar_h59.py

Historia H5.9. Rubrica de Computacion Grafica, criterio CG-1.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
FUENTE = RAIZ / "frontend" / "src"
TOKENS = FUENTE / "estilos" / "tokens.css"
EXTENSIONES = {".js", ".jsx", ".css", ".html"}

# Se comparan sin acentos y en minusculas, asi que "existía" y "existia" son lo
# mismo. La lista es de AFIRMACIONES falsas; "el modelo entrenado estima a siete
# dias" no esta y no debe dispararse.
FRASES_PROHIBIDAS = (
    "no hay modelo entrenado",
    "no hay modelos entrenados",
    "no existe un modelo entrenado",
    "no existe modelo entrenado",
    "no exista un modelo entrenado",
    "mientras no exista un modelo",
    "sin modelo entrenado",
    "hasta que exista un modelo",
)

# Orden de la escala, de menor a mayor. `--texto-2xl` se acepta por si el
# rediseno la agrega; hoy no existe y cuenta cero.
ESCALA = ("xs", "sm", "md", "lg", "xl", "2xl")
TERCIO = 1 / 3

PATRON_TOKEN = re.compile(r"var\(--texto-(xs|sm|md|lg|xl|2xl)\)")
# Un font-size con numero y unidad. `font-size: var(...)`, `inherit` o `1em`
# dentro de tokens.css no cuentan; un `13px` o un `0.8em` en un componente si.
PATRON_LITERAL = re.compile(r"font-size\s*:\s*[0-9.]+\s*(px|rem|em|pt|%)", re.I)


def normalizar(texto: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sin_acentos if not unicodedata.combining(c)).lower()


def archivos_fuente() -> list[Path]:
    return sorted(p for p in FUENTE.rglob("*") if p.suffix in EXTENSIONES and p.is_file())


def frases_encontradas(texto: str) -> list[str]:
    plano = normalizar(texto)
    return [frase for frase in FRASES_PROHIBIDAS if frase in plano]


class Resultado:
    def __init__(self) -> None:
        self.fallos = 0

    def anotar(self, condicion: bool, mensaje: str, detalle: str = "") -> None:
        marca = "OK   " if condicion else "FALLA"
        if not condicion:
            self.fallos += 1
        print(f"  {marca} {mensaje}" + (f"  {detalle}" if detalle else ""))


def autoprueba(r: Resultado) -> None:
    print("El control se prueba a si mismo antes de mirar el repositorio:")
    positiva = "// El sistema no estima a futuro mientras no exista un modelo entrenado."
    negativa = "// El modelo entrenado estima a siete dias desde lo observado (H3.0)."
    con_acento = "No se puede: no existe un modelo entrenado todavía."
    r.anotar(bool(frases_encontradas(positiva)), "detecta la frase prohibida")
    r.anotar(not frases_encontradas(negativa), "no dispara con una frase parecida pero correcta")
    r.anotar(bool(frases_encontradas(con_acento)), "detecta la frase aunque lleve acentos")
    r.anotar(bool(PATRON_LITERAL.search("  font-size: 13px;")), "detecta un font-size literal")
    r.anotar(
        not PATRON_LITERAL.search("  font-size: var(--texto-md);"),
        "no dispara con un font-size que usa la escala",
    )


def verificar_ca2(r: Resultado, archivos: list[Path]) -> None:
    print("\nCA-2, ninguna frase visible afirma algo falso sobre el sistema:")
    hallazgos: list[tuple[str, int, str]] = []
    for archivo in archivos:
        for numero, linea in enumerate(archivo.read_text(encoding="utf-8").splitlines(), 1):
            for frase in frases_encontradas(linea):
                hallazgos.append((str(archivo.relative_to(RAIZ)), numero, frase))
    r.anotar(
        not hallazgos,
        f"ninguna de las {len(FRASES_PROHIBIDAS)} frases prohibidas en {len(archivos)} archivos",
    )
    for ruta, numero, frase in hallazgos:
        print(f"         {ruta}:{numero}  «{frase}»")


def verificar_ca9(r: Resultado, archivos: list[Path]) -> None:
    print("\nCA-9, la jerarquia tipografica esta en uso:")
    conteo: Counter[str] = Counter()
    literales: list[str] = []
    for archivo in archivos:
        if archivo == TOKENS:
            continue
        texto = archivo.read_text(encoding="utf-8")
        conteo.update(PATRON_TOKEN.findall(texto))
        for numero, linea in enumerate(texto.splitlines(), 1):
            if PATRON_LITERAL.search(linea):
                literales.append(f"{archivo.relative_to(RAIZ)}:{numero}  {linea.strip()}")

    total = sum(conteo.values())
    distribucion = " · ".join(f"{t} {conteo.get(t, 0)}" for t in ESCALA)
    print(f"         usos de la escala: {distribucion}  (total {total})")

    r.anotar(total > 0, "los componentes usan la escala de tokens.css")
    if total:
        xs = conteo.get("xs", 0) / total
        grandes = sum(conteo.get(t, 0) for t in ("md", "lg", "xl", "2xl")) / total
        r.anotar(xs <= TERCIO, "xs no pasa de un tercio de los usos", f"{xs:.0%}")
        r.anotar(
            grandes >= TERCIO, "md o mayor es al menos un tercio de los usos", f"{grandes:.0%}"
        )

    declarados = [t for t in ESCALA if f"--texto-{t}:" in TOKENS.read_text(encoding="utf-8")]
    r.anotar(len(declarados) >= 3, "la escala declara al menos tres niveles", ", ".join(declarados))
    r.anotar(not literales, "ningun archivo fuera de tokens.css escribe un font-size literal")
    for literal in literales:
        print(f"         {literal}")


def main() -> int:
    print("Verificacion de H5.9: CA-2 y CA-9\n")
    r = Resultado()
    autoprueba(r)
    if r.fallos:
        print("\nLa autoprueba fallo: el control no sabe decir que no. No se mira el repositorio.")
        return 1
    archivos = archivos_fuente()
    verificar_ca2(r, archivos)
    verificar_ca9(r, archivos)
    if r.fallos:
        print(f"\n{r.fallos} comprobaciones fallaron.")
        return 1
    print("\nTodas las verificaciones pasaron.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
