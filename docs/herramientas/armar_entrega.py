"""Arma el .zip de una entrega, con todo lo que hay que subir.

POR QUE EXISTE

Una entrega armada a mano se olvida de un archivo. Este programa la construye
siempre igual, **comprueba que cada pieza existe antes de empaquetar** y falla si
falta alguna, en vez de producir un zip incompleto que parece correcto.

Es el mismo criterio de I-06: un paso que se salta en silencio se ve igual que
uno que se cumplio.

QUE METE

    Los documentos en PDF, que es lo que el evaluador abre.
    Los seis diagramas en PNG, por si hacen falta sueltos.
    Un LEEME.txt con que es cada archivo y como se reproduce.

QUE **NO** METE, y es deliberado

    El repositorio. Se evalua en GitHub, no en un zip.
    Los .md fuente. Estan en el repositorio, que es donde se leen.
    Los .docx, salvo que se pidan: el PDF es el formato de entrega.

Uso:
    python docs/herramientas/armar_entrega.py
    python docs/herramientas/armar_entrega.py --nombre "avance-semana-8-geoguardian"
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
GESTION = RAIZ.parent / "gestion"
DIAGRAMAS = RAIZ / "docs" / "diagramas"

#: (ruta de origen, nombre dentro del zip, obligatorio)
#:
#: El nombre dentro del zip **no** es el del archivo en disco: `13-` y `17-` son
#: numeros de documento del repositorio y no le dicen nada a quien lo recibe.
PIEZAS: list[tuple[Path, str, bool]] = [
    (GESTION / "16-avance-semana8.pdf", "1 - Avance Semana 8.pdf", True),
    (
        GESTION / "13-documento-ieee-IEEE.pdf",
        "2 - Documento de investigacion IEEE.pdf",
        True,
    ),
    (GESTION / "17-documento-tecnico-IEEE.pdf", "3 - Documento tecnico IEEE.pdf", True),
    (GESTION / "16-avance-semana8.docx", "1 - Avance Semana 8.docx", False),
]

LEEME = """GeoGuardian - Avance de Semana 8
Universidad Invenio - Ingenieria en Tecnologias de Informacion
III Trimestre 2026 - {fecha}

Alejandro Josue Rodriguez Zamora
Cesar Andres Ubau Calvo
Luis Alejandro Luna Garcia
Avril Madrigal Elizondo


QUE HAY EN ESTE ARCHIVO

  1 - Avance Semana 8.pdf
      Revision del MVP, arquitectura con los seis diagramas, resultados
      medidos y evaluacion de la documentacion. Es el documento que responde
      los tres puntos de la semana.

  2 - Documento de investigacion IEEE.pdf
      El articulo, en formato de conferencia IEEE a dos columnas.
      Las secciones VII y IX estan declaradas vacias: dependen de los tres
      algoritmos de aprendizaje, que todavia no estan entrenados. El propio
      documento dice que va en cada una y que hace falta para escribirla.

  3 - Documento tecnico IEEE.pdf
      Tecnologias con sus versiones, arquitectura, modelo de datos,
      contratos, procesamiento, API, visor, verificacion y despliegue.

  diagramas/
      Los seis diagramas en PNG, por si hacen falta sueltos.


EL SISTEMA, EN LINEA

  Repositorio   https://github.com/HumanoidCat/geoguardian
  Visor         publicado con GitHub Pages desde el 20 de agosto

  El visor publicado consulta la API, no la encuentra -no esta desplegada- y
  degrada a un respaldo estatico de datos simulados, que declara en pantalla.
  Es el comportamiento previsto en la decision D-23, y es una limitacion
  declarada del MVP, no un defecto.


COMO SE REPRODUCE TODO ESTO

  Los PDF no se editan: se generan desde los Markdown del repositorio.

      python docs/herramientas/generar_diagramas.py --png
      python docs/herramientas/construir_entregable.py docs/16-avance-semana8.md
      python docs/herramientas/construir_entregable.py docs/13-documento-ieee.md --ieee
      python docs/herramientas/construir_entregable.py docs/17-documento-tecnico.md --ieee

  Y este mismo archivo:

      python docs/herramientas/armar_entrega.py
"""


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--nombre", default="Avance Semana 8 - GeoGuardian")
    p.add_argument("--salida", type=Path, default=GESTION)
    p.add_argument("--con-docx", action="store_true", help="incluye tambien los .docx")
    args = p.parse_args()

    print(f"\nArmando la entrega: {args.nombre}\n")

    faltan = [origen for origen, _, obligatorio in PIEZAS if obligatorio and not origen.exists()]
    if faltan:
        print("  FALTAN PIEZAS OBLIGATORIAS:\n")
        for f in faltan:
            print(f"    {f.name}")
        print("\n  Se construyen con:\n")
        print("      python docs/herramientas/generar_diagramas.py --png")
        print("      python docs/herramientas/construir_entregable.py " "docs/16-avance-semana8.md")
        print(
            "      python docs/herramientas/construir_entregable.py "
            "docs/13-documento-ieee.md --ieee"
        )
        print(
            "      python docs/herramientas/construir_entregable.py "
            "docs/17-documento-tecnico.md --ieee\n"
        )
        return 1

    diagramas = sorted(DIAGRAMAS.glob("*.png"))
    if not diagramas:
        print("  No hay PNG de los diagramas. Se generan con:\n")
        print("      python docs/herramientas/generar_diagramas.py --png\n")
        return 1

    args.salida.mkdir(parents=True, exist_ok=True)
    destino = args.salida / f"{args.nombre}.zip"

    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zip_:
        zip_.writestr("LEEME.txt", LEEME.format(fecha=date.today().isoformat()))
        print("  LEEME.txt")

        for origen, nombre, obligatorio in PIEZAS:
            if not origen.exists():
                continue
            if origen.suffix == ".docx" and not args.con_docx:
                continue
            zip_.write(origen, nombre)
            marca = "" if obligatorio else "  (opcional)"
            print(f"  {nombre}{marca}")

        for diagrama in diagramas:
            zip_.write(diagrama, f"diagramas/{diagrama.name}")
        print(f"  diagramas/  ({len(diagramas)} PNG)")

    tamano = destino.stat().st_size / 1024 / 1024
    print(f"\n  {destino}")
    print(f"  {tamano:.1f} MB\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
