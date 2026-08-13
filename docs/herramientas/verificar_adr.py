"""Comprueba que la bitacora de decisiones cumple el formato ADR.

Verifica que cada registro D-NN de docs/03-bitacora-decisiones.md tenga las seis
secciones obligatorias de docs/plantillas/plantilla-adr.md y un estado declarado.

Uso:
    python docs/herramientas/verificar_adr.py

Sale con codigo 1 si algun registro esta incompleto, para poder correrlo en CI.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MINIMO_REGISTROS = 6

SECCIONES = (
    "### Contexto",
    "### Decision",
    "### Justificacion",
    "### Alternativas descartadas",
    "### Consecuencias",
    "### Medicion",
)

ESTADOS = ("Aceptada", "Propuesta", "Revisada", "Sustituida por")


def registros(texto: str) -> list[tuple[str, str]]:
    """Parte el documento en (identificador, cuerpo) por cada encabezado ## D-NN."""
    partes = re.split(r"\n## (D-\d+)[^\n]*\n", texto)[1:]
    return [(partes[i], partes[i + 1]) for i in range(0, len(partes), 2)]


def estado_de(cuerpo: str) -> str | None:
    encontrado = re.search(r"\*\*Estado\.\*\*\s*(.+)", cuerpo)
    if not encontrado:
        return None
    valor = encontrado.group(1).strip()
    return valor if any(valor.startswith(e) for e in ESTADOS) else None


def main() -> int:
    raiz = Path(__file__).resolve().parents[2]
    archivo = raiz / "docs" / "03-bitacora-decisiones.md"

    if not archivo.exists():
        print(f"No se encuentra {archivo}")
        return 1

    encontrados = registros(archivo.read_text(encoding="utf-8"))
    print(f"Registros ADR encontrados: {len(encontrados)}")
    print()

    completos = 0
    for identificador, cuerpo in encontrados:
        faltan = [s for s in SECCIONES if s not in cuerpo]
        estado = estado_de(cuerpo)

        if faltan:
            detalle = "FALTA " + ", ".join(s.replace("### ", "") for s in faltan)
        elif estado is None:
            detalle = "FALTA estado declarado"
        else:
            detalle = f"completo   estado={estado}"
            completos += 1

        print(f"  {identificador}: {detalle}")

    print()
    print(f"{completos} de {len(encontrados)} registros completos")

    if completos < MINIMO_REGISTROS:
        print(f"\nFALLO: la historia H6.4 exige al menos {MINIMO_REGISTROS} registros completos.")
        return 1
    if completos != len(encontrados):
        print("\nFALLO: hay registros incompletos.")
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
