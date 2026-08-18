"""
Valida el catalogo de eventos historicos contra los contratos congelados.

El catalogo se escribe a mano a partir de fuentes documentales, asi que es
propenso a errores humanos que ninguna revision visual detecta: un codigo de
distrito de otro canton, una fecha de fin anterior a la de inicio, un tipo de
evento mal escrito. Este script los detecta ejecutando.

No corrige nada ni completa nada. Reporta y devuelve codigo de salida distinto
de cero si hay algun problema, para que el CI pueda fallar.

Uso:  python -m backend.calidad.validar_catalogo
      python -m backend.calidad.validar_catalogo --csv otra/ruta.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from datetime import date
from pathlib import Path

from pydantic import ValidationError

from contratos.enums import NivelRiesgo, TipoEvento
from contratos.esquemas import EventoHistorico

RUTA_POR_DEFECTO = Path("docs/investigacion/catalogo-eventos.csv")

# Los ocho distritos del canton de Tilaran. Un codigo con forma valida pero de
# otro canton es un dato falso que la validacion de tipo no detecta: fue la
# incidencia I-04.
DISTRITOS_TILARAN = {
    "50801": "Tilaran",
    "50802": "Quebrada Grande",
    "50803": "Tronadora",
    "50804": "Santa Rosa",
    "50805": "Libano",
    "50806": "Tierras Morenas",
    "50807": "Arenal",
    "50808": "Cabeceras",
}

MINIMO_EVENTOS = 12


def _fecha(valor: str) -> date | None:
    """Convierte una fecha ISO. Cadena vacia significa ausente, no error."""
    valor = valor.strip()
    if not valor:
        return None
    return date.fromisoformat(valor)


def validar(ruta: Path) -> int:
    if not ruta.exists():
        print(f"ERROR: no existe {ruta}")
        return 1

    errores: list[str] = []
    avisos: list[str] = []
    sin_severidad: list[int] = []
    eventos: list[EventoHistorico] = []

    with ruta.open(encoding="utf-8", newline="") as f:
        filas = list(csv.DictReader(f))

    if not filas:
        print(f"ERROR: {ruta} no tiene filas de datos")
        return 1

    for n, fila in enumerate(filas, start=2):  # 2 = primera fila tras el encabezado
        try:
            evento = EventoHistorico(
                codigo_distrito=fila["codigo_distrito"].strip(),
                tipo_evento=TipoEvento(fila["tipo_evento"].strip()),
                fecha_inicio=_fecha(fila["fecha_inicio"]),
                fecha_fin=_fecha(fila["fecha_fin"]),
                severidad=(
                    NivelRiesgo(fila["severidad"].strip()) if fila["severidad"].strip() else None
                ),
                fuente=fila["fuente"].strip(),
                descripcion=fila["descripcion"].strip() or None,
            )
        except (ValidationError, ValueError, KeyError) as e:
            errores.append(f"fila {n}: no cumple el contrato EventoHistorico: {e}")
            continue

        eventos.append(evento)

        # Comprobaciones que el esquema no puede hacer por si solo.
        if evento.codigo_distrito not in DISTRITOS_TILARAN:
            errores.append(
                f"fila {n}: el codigo {evento.codigo_distrito} no es un distrito de Tilaran. "
                f"Los validos son 50801 a 50808 (ver incidencia I-04)"
            )

        if evento.fecha_fin is not None and evento.fecha_fin < evento.fecha_inicio:
            errores.append(
                f"fila {n}: fecha_fin ({evento.fecha_fin}) es anterior a "
                f"fecha_inicio ({evento.fecha_inicio})"
            )

        if evento.fecha_inicio > date.today():
            errores.append(f"fila {n}: fecha_inicio ({evento.fecha_inicio}) esta en el futuro")

        if not evento.fuente:
            errores.append(f"fila {n}: fuente vacia. Todo evento debe declarar de donde sale")

        if evento.severidad is None:
            sin_severidad.append(n)

    # ---------------------------------------------------------------- informe

    print(f"\nCatalogo: {ruta}")
    print(f"Filas leidas: {len(filas)}   Filas validas: {len(eventos)}\n")

    print("Filas por tipo de evento:")
    por_tipo = Counter(e.tipo_evento.value for e in eventos)
    for tipo in TipoEvento:
        n = por_tipo.get(tipo.value, 0)
        marca = "  " if n else "  <- sin cobertura"
        print(f"  {tipo.value:<16} {n:>3}{marca}")

    print("\nFilas por distrito:")
    por_distrito = Counter(e.codigo_distrito for e in eventos)
    for codigo, nombre in DISTRITOS_TILARAN.items():
        n = por_distrito.get(codigo, 0)
        marca = "  " if n else "  <- sin cobertura"
        print(f"  {codigo} {nombre:<16} {n:>3}{marca}")

    print("\nFilas por severidad:")
    por_severidad = Counter(e.severidad.value if e.severidad else "sin asignar" for e in eventos)
    for clave, n in sorted(por_severidad.items()):
        print(f"  {clave:<16} {n:>3}")

    # Un evento puede ocupar varias filas, una por distrito afectado. Se cuenta
    # como distinto por la combinacion de fecha de inicio y tipo.
    distintos = {(e.fecha_inicio, e.tipo_evento) for e in eventos}
    print(f"\nEventos distintos (fecha de inicio + tipo): {len(distintos)}")
    print(f"Minimo exigido por la historia H4.3: {MINIMO_EVENTOS}")

    if len(distintos) < MINIMO_EVENTOS:
        avisos.append(
            f"el catalogo tiene {len(distintos)} eventos distintos y la historia "
            f"exige {MINIMO_EVENTOS}. El catalogo esta incompleto"
        )

    # Se agrupa en un solo aviso: es una decision documentada del catalogo, no
    # un descuido fila por fila. Ver docs/investigacion/catalogo-eventos.md.
    if sin_severidad:
        avisos.append(
            f"{len(sin_severidad)} de {len(eventos)} filas sin severidad asignada. "
            f"Es deliberado: la fuente no reporta severidad y los umbrales de la "
            f"Tabla 1 no se pueden aplicar retroactivamente sin la serie climatica. "
            f"Ver docs/investigacion/catalogo-eventos.md"
        )

    distritos_vacios = [c for c in DISTRITOS_TILARAN if c not in por_distrito]
    if distritos_vacios:
        avisos.append(
            "distritos sin ningun evento registrado: "
            + ", ".join(f"{c} {DISTRITOS_TILARAN[c]}" for c in distritos_vacios)
        )

    if avisos:
        print(f"\nAvisos ({len(avisos)}):")
        for a in avisos:
            print(f"  - {a}")

    if errores:
        print(f"\nERRORES ({len(errores)}):")
        for e in errores:
            print(f"  - {e}")
        print("\nEl catalogo NO es valido.\n")
        return 1

    print("\nTodas las filas cumplen el contrato.\n")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, default=RUTA_POR_DEFECTO)
    args = p.parse_args()
    return validar(args.csv)


if __name__ == "__main__":
    sys.exit(main())
