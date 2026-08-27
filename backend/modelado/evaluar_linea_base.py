"""Mide las dos lineas base sobre el dato real. Historia H3.1.

QUE HACE

1. Lee `datos/procesados/etiquetas.csv`, el artefacto de H3.0.
2. Para cada evento y cada pliegue de H3.2: ajusta con el entrenamiento, predice
   sobre la prueba, y calcula el F1-macro de **las dos** lineas base.
3. Contrasta el resultado contra la **prediccion escrita antes de medir**.

NO NECESITA LA BASE DE DATOS

Consume el CSV que `generar_etiquetas.py` ya produjo. Si no existe, lo dice y
explica como generarlo, en vez de fallar con un rastro.

LA PREDICCION QUE HAY QUE CONTRASTAR

Escrita en los criterios **antes** de correr esto:

    lluvia intensa   claramente arriba de la trivial
    incendio         claramente arriba de la trivial
    sequia           CERCA de la trivial

La tercera es la interesante. **Si la climatologica predice bien la sequia, D-19
no esta haciendo lo que dice**: el SPI-3 se ajusta por mes calendario justamente
para remover la estacionalidad, asi que el mes no deberia informar casi nada.

Seria el mismo defecto que D-19 se escribio para corregir, reaparecido un nivel
mas arriba, y esta historia lo detecta gratis.

Uso:
    python -m backend.modelado.evaluar_linea_base
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado.linea_base import (  # noqa: E402
    DISTRITOS_CON_INCENDIO,
    LineaBaseClimatologica,
    LineaBaseTrivial,
    f1_macro,
)
from backend.modelado.particion import (  # noqa: E402
    particionar,
    resumen_f1,
)
from contratos.enums import NivelRiesgo, TipoEvento  # noqa: E402

COLUMNA = {
    TipoEvento.SEQUIA: "sequia",
    TipoEvento.LLUVIA_INTENSA: "lluvia_intensa",
    TipoEvento.INCENDIO: "incendio",
}

#: Cuanto tiene que sacarle la climatologica a la trivial para decir que el mes
#: informa. Fijado **antes** de mirar el resultado, como el umbral de CA-6 en
#: H3.0: un margen elegido despues del dato es un margen que el dato eligio.
MARGEN = 0.02


def leer(ruta: Path) -> list[tuple[str, date, dict[str, NivelRiesgo | None]]]:
    filas = []
    with ruta.open(encoding="utf-8", newline="") as archivo:
        for f in csv.DictReader(archivo):
            niveles = {
                c: (NivelRiesgo(f[c]) if f[c] else None)
                for c in ("sequia", "lluvia_intensa", "incendio")
            }
            filas.append((f["codigo_distrito"], date.fromisoformat(f["fecha"]), niveles))
    return filas


def evaluar(evento: TipoEvento, filas: list) -> tuple[list[float], list[float], int]:
    """F1-macro de trivial y climatologica, pliegue por pliegue."""
    columna = COLUMNA[evento]

    # CA-6: el incendio se evalua solo donde D-25 dice.
    if evento is TipoEvento.INCENDIO:
        filas = [f for f in filas if f[0] in DISTRITOS_CON_INCENDIO]

    triviales: list[float] = []
    climaticas: list[float] = []
    sin_prediccion = 0

    for pliegue in particionar(evento):
        ent = [
            (c, f, n[columna])
            for c, f, n in filas
            if pliegue.entrenamiento[0] <= f <= pliegue.entrenamiento[1] and n[columna] is not None
        ]
        pru = [
            (c, f, n[columna])
            for c, f, n in filas
            if pliegue.prueba[0] <= f <= pliegue.prueba[1] and n[columna] is not None
        ]
        if not ent or not pru:
            continue

        trivial = LineaBaseTrivial().ajustar(ent)
        clima = LineaBaseClimatologica().ajustar(ent)

        verdad = [n for _, _, n in pru]
        pred_t = [trivial.predecir(c, f) for c, f, _ in pru]
        pred_c = [clima.predecir(c, f) for c, f, _ in pru]

        mt, _, _ = f1_macro(verdad, pred_t)
        mc, _, evaluadas = f1_macro(verdad, pred_c)
        triviales.append(mt)
        climaticas.append(mc)
        sin_prediccion += len(pru) - evaluadas

    return triviales, climaticas, sin_prediccion


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--etiquetas", type=Path, default=RAIZ / "datos" / "procesados" / "etiquetas.csv"
    )
    args = p.parse_args()

    if not args.etiquetas.exists():
        print(f"\nNo existe {args.etiquetas}.\n")
        print("Se genera con la base levantada:\n")
        print("    python -m backend.modelado.generar_etiquetas\n")
        return 1

    filas = leer(args.etiquetas)
    print("\nLineas base sobre el dato real · H3.1")
    print(f"  filas leidas   {len(filas)}")
    print(f"  pliegues       {len(particionar(TipoEvento.SEQUIA))}, de H3.2")
    print(f"  margen para decir que el mes informa: {MARGEN:+.2f} de F1-macro\n")

    veredictos: dict[TipoEvento, bool] = {}

    for evento in TipoEvento:
        triviales, climaticas, huecos = evaluar(evento, filas)
        if not triviales:
            print(f"{evento.value.upper()}: sin pliegues evaluables\n")
            continue

        mt, dt, vt = resumen_f1(triviales)
        mc, dc, vc = resumen_f1(climaticas)
        gana = mc - mt > MARGEN
        veredictos[evento] = gana

        print(f"{evento.value.upper()}")
        print(f"  {'':16}{'F1-macro':>10}{'desv':>8}   por pliegue")
        print(f"  {'trivial':16}{mt:>10.3f}{dt:>8.3f}   {[round(v, 3) for v in vt]}")
        print(f"  {'climatologica':16}{mc:>10.3f}{dc:>8.3f}   {[round(v, 3) for v in vc]}")
        print(f"  {'diferencia':16}{mc - mt:>+10.3f}")
        print(f"  {'el mes informa?':16}{'SI' if gana else 'no':>10}")
        if huecos:
            print(f"  filas sin prediccion, no evaluadas: {huecos}")
        print()

    # ----------------------------------------------------------------------- #
    # El contraste contra lo que se predijo antes de medir
    # ----------------------------------------------------------------------- #
    print("Contra la prediccion escrita ANTES de medir\n")

    esperado = {
        TipoEvento.LLUVIA_INTENSA: True,
        TipoEvento.INCENDIO: True,
        TipoEvento.SEQUIA: False,
    }
    desvios = []
    for evento, se_esperaba in esperado.items():
        if evento not in veredictos:
            continue
        real = veredictos[evento]
        marca = "coincide" if real == se_esperaba else "NO COINCIDE"
        if real != se_esperaba:
            desvios.append(evento)
        print(
            f"  {evento.value:16} esperado {'arriba' if se_esperaba else 'cerca':>7}"
            f" · medido {'arriba' if real else 'cerca':>7}   {marca}"
        )

    print()
    if TipoEvento.SEQUIA in desvios:
        print("  ATENCION: la climatologica predice la sequia mejor de lo esperado.")
        print("  D-19 ajusta el SPI-3 por mes calendario para remover la")
        print("  estacionalidad. Si el mes informa, hay que revisar si ese ajuste")
        print("  esta funcionando: seria el defecto que D-19 vino a corregir,")
        print("  reaparecido un nivel mas arriba.\n")
    elif desvios:
        print(f"  {len(desvios)} evento(s) no coinciden con lo predicho. Hay que")
        print("  explicarlo en la evidencia, no ajustar la prediccion.\n")
    else:
        print("  Las tres coinciden.\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
