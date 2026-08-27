"""Convierte un documento del repositorio a Word y PDF, para entregar.

POR QUE EXISTE

El documento se escribe **una sola vez**, en Markdown, dentro del repositorio.
De ahi salen el .docx y el .pdf que se suben a la plataforma.

La alternativa -mantener un Word aparte- es la que produce la incidencia que este
proyecto ya conoce: dos copias del mismo contenido, una se corrige y la otra no,
y nadie sabe cual es la buena. Es I-04 con otro formato.

**El Markdown es la fuente. El .docx y el .pdf son artefactos**, no se editan.
Si hay que corregir algo, se corrige el .md y se vuelve a construir.

QUE HACE FALTA

    pandoc        Markdown -> docx.  https://pandoc.org
    libreoffice   docx -> pdf.       Cualquiera de los dos soffice/libreoffice

En Windows:
    winget install JohnMacFarlane.Pandoc
    winget install TheDocumentFoundation.LibreOffice

Los diagramas se referencian como PNG desde el Markdown, asi que hay que
generarlos antes. Esta herramienta lo comprueba y lo dice, en vez de producir un
documento con los recuadros vacios.

Uso:
    python docs/herramientas/construir_entregable.py docs/16-avance-semana8.md
    python docs/herramientas/construir_entregable.py docs/16-avance-semana8.md --salida ../gestion
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
#: Hermana del repositorio y **fuera de el**: los entregables no se versionan.
SALIDA = RAIZ.parent / "gestion"


def _pandoc() -> str:
    ruta = shutil.which("pandoc")
    if not ruta:
        raise RuntimeError(
            "Falta pandoc.\n"
            "  Windows: winget install JohnMacFarlane.Pandoc\n"
            "  Debian:  sudo apt install pandoc"
        )
    return ruta


def _libreoffice() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice")


def comprobar_imagenes(documento: Path) -> list[str]:
    """Devuelve las imagenes referenciadas que no existen.

    Pandoc no falla cuando una imagen no esta: la omite y sigue. El documento
    sale con secciones de diagramas vacias y **parece correcto**, que es
    exactamente el modo de fallo que este proyecto persigue desde I-06.
    """
    texto = documento.read_text(encoding="utf-8")
    faltantes = []
    for referencia in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", texto):
        if referencia.startswith(("http://", "https://")):
            continue
        if not (documento.parent / referencia).exists():
            faltantes.append(referencia)
    return faltantes


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("documento", type=Path)
    p.add_argument("--salida", type=Path, default=SALIDA)
    p.add_argument("--sin-pdf", action="store_true")
    args = p.parse_args()

    documento = args.documento if args.documento.is_absolute() else RAIZ / args.documento
    if not documento.exists():
        print(f"\nNo existe {documento}\n")
        return 1

    salida = args.salida if args.salida.is_absolute() else RAIZ / args.salida
    salida.mkdir(parents=True, exist_ok=True)

    print(f"\nConstruyendo el entregable desde {documento.relative_to(RAIZ)}\n")

    faltantes = comprobar_imagenes(documento)
    if faltantes:
        print("  FALTAN IMAGENES. El documento saldria con los diagramas en blanco:\n")
        for f in faltantes:
            print(f"    {f}")
        print("\n  Se generan con:\n")
        print("      python docs/herramientas/generar_diagramas.py --png\n")
        return 1
    print("  todas las imagenes referenciadas existen")

    docx = salida / f"{documento.stem}.docx"
    orden = [
        _pandoc(),
        str(documento),
        "-o",
        str(docx),
        # Sin esto, pandoc busca las imagenes desde el directorio actual y no
        # desde el del documento.
        f"--resource-path={documento.parent}",
        # SIN indice automatico, y es deliberado. Pandoc inserta en el .docx un
        # **campo** de tabla de contenidos que solo Word rellena al abrirlo;
        # LibreOffice no lo actualiza al convertir, asi que el PDF salia con un
        # "Table of Contents" en ingles y vacio debajo.
        #
        # Se probo y se vio. Los documentos llevan su propia numeracion de
        # secciones, que cumple la misma funcion y aparece en los dos formatos.
        "--standalone",
        # Las tablas de este documento llevan celdas largas; sin `pipe_tables`
        # explicito pandoc a veces las lee como texto.
        "--from=markdown+pipe_tables+yaml_metadata_block",
    ]
    proceso = subprocess.run(orden, capture_output=True, text=True, check=False)
    if proceso.returncode != 0:
        print(f"\n  pandoc fallo:\n{proceso.stderr}")
        return 1
    print(f"  {docx}")

    if args.sin_pdf:
        print()
        return 0

    oficina = _libreoffice()
    if not oficina:
        print("\n  Sin PDF: falta LibreOffice.")
        print("      Windows: winget install TheDocumentFoundation.LibreOffice")
        print("  El .docx ya esta, se puede exportar a PDF desde Word.\n")
        return 0

    proceso = subprocess.run(
        [oficina, "--headless", "--convert-to", "pdf", "--outdir", str(salida), str(docx)],
        capture_output=True,
        text=True,
        check=False,
    )
    pdf = salida / f"{documento.stem}.pdf"
    if proceso.returncode != 0 or not pdf.exists():
        print(f"\n  La conversion a PDF fallo:\n{proceso.stderr or proceso.stdout}")
        print("  El .docx ya esta, se puede exportar a PDF desde Word.\n")
        return 0
    print(f"  {pdf}")

    print("\n  Recordatorio: el .docx y el .pdf son artefactos. Si hay que")
    print(f"  corregir algo, se corrige {documento.name} y se vuelve a construir.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
