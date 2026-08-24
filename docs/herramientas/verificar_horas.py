"""Compara las horas estimadas con las reales, historia por historia.

POR QUE EXISTE

El 20 de agosto Avril reporto que H7.1 le llevo **2 h** contra las **5.8 h** del
backlog, y de paso pregunto por el modelo que produjo ese 5.8. Al mirarlo, el
modelo resulto ser una constante:

    H5.1   3 pts    2.9 h   0.97 h/pt
    H5.2   5 pts    4.8 h   0.96 h/pt
    H5.3   7 pts    6.7 h   0.96 h/pt
    H7.1   6 pts    5.8 h   0.97 h/pt

Cuatro de sus cinco historias son **puntos x 0.96**. No hay modelo: hay una
multiplicacion. Ninguna de las cuatro variables que ella observo esta adentro,
porque no hay donde meterlas. Ver **D-24**.

Para poder corregirlo hace falta medir, y para medir hace falta un lugar donde
escribir el numero. Antes de este archivo no habia ninguno: las horas reales
vivian en mensajes sueltos y se perdian. Es el mismo problema que H1.7 tiene con
la evidencia, aplicado a la gestion del proyecto.

QUE SE ESCRIBE, Y DONDE

En `docs/tareas/<persona>.md`, debajo de la historia cerrada:

    - [x] **H7.1** · Semaforo de riesgo ... (2026-08-20)
      - `E7` · 6 pts · 5.8 h · rubrica: CG-2 · depende de: H5.3
      - horas: estimada 4.0 · real 2.0

**Dos numeros, no tres.** Las horas del backlog ya estan en `backlog.csv` y se
muestran en la linea de arriba. Volver a escribirlas aqui seria un tercer lugar
para el mismo dato, que es exactamente la incidencia **I-07**.

    estimada  lo que la persona dijo ANTES de arrancar, sin mirar el backlog
    real      lo que tardo

Las dos por separado, porque son dos errores distintos: el del modelo del
proyecto y el de quien estima. En H7.1 el backlog dijo 5.8, Avril dijo 4 y el
real fue 2: los dos fallaron, y no por lo mismo.

DESDE CUANDO SE EXIGE

Desde el **2026-08-20**, no hacia atras. Estimar hoy una historia cerrada la
semana pasada, sabiendo lo que decia el backlog, produce un numero anclado a ese
valor por construccion. El argumento es de Avril y es correcto: una direccion
honesta —"mucho mas larga", "mas corta"— vale mas que un numero inventado con un
decimal.

QUE COMPRUEBA

1. Toda historia cerrada a partir del 2026-08-20 declara sus horas.
2. Ninguna historia abierta declara horas reales.
3. Los numeros son positivos y la historia existe en el backlog.

QUE NO COMPRUEBA

Si el numero es cierto. Nadie puede comprobarlo, y por eso el valor de esto
depende de que cada quien lo anote al terminar y no al final del sprint.

Uso:
    python docs/herramientas/verificar_horas.py

Sale con codigo 1 si algo no cuadra, para poder correrlo en CI.
"""

from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

PERSONAS = ("alejandro", "cesar", "luna", "avril")

# Desde este dia se exige el registro. Ver el docstring: hacia atras el numero
# estaria anclado al del backlog y no mediria nada.
DESDE = date(2026, 8, 20)

# - [x] **H7.1** · titulo (2026-08-20)
PATRON_CERRADA = re.compile(
    r"^- \[x\] \*\*(H[0-9.]+[a-z]?)\*\*[^\n]*?\((\d{4}-\d{2}-\d{2})\)", re.M
)

# - [ ] **H1.6** · titulo
PATRON_ABIERTA = re.compile(r"^- \[[ ]\] \*\*(H[0-9.]+[a-z]?)\*\*", re.M)

#   - horas: estimada 4.0 · real 2.0
#   - horas: estimada n/d (no se pidio al arrancar) · real 3.0
#
# `n/d` SIEMPRE EXIGE UN MOTIVO ESCRITO, y esa regla sustituye a la anterior.
#
# La primera version aceptaba `n/d` solo en las historias cerradas el mismo
# 2026-08-20, razonando que eran las unicas terminadas antes de que la regla
# existiera. **El razonamiento estaba mal y lo encontro Luna al cerrar H9.1:**
# esa historia se cerro despues del corte y tampoco tenia estimacion previa,
# porque nadie se la pidio al arrancar.
#
# Atar la excepcion a una FECHA suponia que la unica causa posible de no tener
# estimacion era el momento del corte. La causa real es otra —si alguien la pidio
# o no— y esa el verificador no puede conocerla. Lo unico que puede exigir es que
# quien escriba `n/d` diga por que.
#
# El diseno viejo obligaba a elegir entre inventar un numero o dejar el CI rojo.
# Un numero inventado se ve igual que uno medido y contamina justo la serie que
# D-24 quiere construir: es peor que el hueco que venia a tapar.
PATRON_HORAS = re.compile(
    r"^\s+- horas: estimada (n/d\s*\([^)]+\)|n/d|[0-9]+(?:[.,][0-9]+)?)"
    r" . real ([0-9]+(?:[.,][0-9]+)?)",
    re.M,
)

SIN_DECLARAR = -1.0


def _numero(texto: str) -> float:
    if texto.startswith("n/d"):
        return SIN_DECLARAR
    return float(texto.replace(",", "."))


def _tiene_motivo(texto: str) -> bool:
    """`n/d` sin motivo no se acepta: seria un hueco sin explicacion."""
    return texto.startswith("n/d") and "(" in texto


def backlog() -> dict[str, dict[str, str]]:
    with (RAIZ / "docs" / "backlog.csv").open(encoding="utf-8-sig") as archivo:
        return {fila["id"]: fila for fila in csv.DictReader(archivo)}


def registros() -> tuple[dict[str, tuple[str, date, float, float]], list[str]]:
    """Identificador -> (persona, fecha, estimada, real), mas los problemas."""
    encontrados: dict[str, tuple[str, date, float, float]] = {}
    problemas: list[str] = []

    for persona in PERSONAS:
        ruta = RAIZ / "docs" / "tareas" / f"{persona}.md"
        texto = ruta.read_text(encoding="utf-8")

        # Se recorre bloque a bloque: cada historia y las lineas que la siguen
        # hasta la proxima historia. Asi la linea de horas queda atada a SU
        # historia y no a la primera del archivo.
        trozos = re.split(r"(?m)^(?=- \[[ x]\] \*\*H)", texto)

        for trozo in trozos:
            cerrada = PATRON_CERRADA.match(trozo)
            abierta = PATRON_ABIERTA.match(trozo)
            horas = PATRON_HORAS.search(trozo)

            if abierta and horas:
                problemas.append(
                    f"{abierta.group(1)} ({persona}) declara horas y no esta marcada [x]. "
                    "Las horas reales de algo sin terminar no son horas reales."
                )
                continue

            if not cerrada:
                continue

            identificador, iso = cerrada.groups()
            cerrada_el = date.fromisoformat(iso)

            if horas is None:
                if cerrada_el >= DESDE:
                    problemas.append(
                        f"{identificador} ({persona}) se cerro el {iso} y no declara horas.\n"
                        "      Se agrega debajo de la linea de la historia:\n"
                        "        - horas: estimada <lo que dijiste antes> . real <lo que tardo>"
                    )
                continue

            estimada, real = _numero(horas.group(1)), _numero(horas.group(2))

            if estimada == SIN_DECLARAR and not _tiene_motivo(horas.group(1)):
                problemas.append(
                    f"{identificador} ({persona}) pone 'estimada n/d' sin motivo.\n"
                    "      Se escribe entre parentesis, en la misma linea:\n"
                    "        - horas: estimada n/d (no se pidio al arrancar) . real 2.5\n"
                    "      Un hueco sin explicacion no se distingue de un olvido, y en la\n"
                    "      retro no se va a poder saber cuales huecos eran inevitables."
                )
                continue

            if real <= 0 or (estimada != SIN_DECLARAR and estimada <= 0):
                problemas.append(
                    f"{identificador} ({persona}) declara horas no positivas: "
                    f"estimada {estimada}, real {real}"
                )
                continue

            encontrados[identificador] = (persona, cerrada_el, estimada, real)

    return encontrados, problemas


def main() -> int:
    fichas = backlog()
    medidos, problemas = registros()

    for identificador in sorted(medidos):
        if identificador not in fichas:
            problemas.append(f"{identificador} declara horas y no existe en el backlog")

    print("\nHoras estimadas contra horas reales\n")

    if not medidos:
        print("  Todavia no hay ninguna historia con horas registradas.")
        print(f"  Se exige a partir del {DESDE.isoformat()}. Ver D-24.")
    else:
        print(f"  {'Historia':9} {'pts':>4} {'backlog':>8} {'estimada':>9} {'real':>7}   desvio")
        print(f"  {'-' * 9} {'-' * 4} {'-' * 8} {'-' * 9} {'-' * 7}   {'-' * 24}")

        suma_backlog = suma_real = 0.0

        for identificador in sorted(medidos, key=lambda i: medidos[i][1]):
            _, _, estimada, real = medidos[identificador]
            ficha = fichas.get(identificador, {})
            del_backlog = float(ficha.get("horas", 0) or 0)
            puntos = ficha.get("puntos", "?")

            suma_backlog += del_backlog
            suma_real += real

            veces = f"backlog {del_backlog / real:.1f}x" if real else ""
            columna = "      n/d" if estimada == SIN_DECLARAR else f"{estimada:>9.1f}"
            print(
                f"  {identificador:9} {puntos:>4} {del_backlog:>8.1f} "
                f"{columna} {real:>7.1f}   {veces}"
            )

        print(f"\n  {'TOTAL':9} {'':>4} {suma_backlog:>8.1f} {'':>9} {suma_real:>7.1f}")
        if suma_real:
            print(f"\n  El backlog estima {suma_backlog / suma_real:.2f} veces lo que cuesta.")
        print(
            f"\n  {len(medidos)} historias medidas. El coeficiente no se cambia hasta\n"
            "  tener suficientes: ver D-24, que decide medir y no todavia corregir."
        )

    if problemas:
        print(f"\n{len(problemas)} problemas:\n")
        for problema in problemas:
            print(f"  - {problema}")
        return 1

    print("\nTodas las historias cerradas desde el corte declaran sus horas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
