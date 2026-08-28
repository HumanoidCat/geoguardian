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
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
#: Hermana del repositorio y **fuera de el**: los entregables no se versionan.
SALIDA = RAIZ.parent / "gestion"

PLANTILLA_IEEE = RAIZ / "docs" / "plantillas" / "ieee.latex"
LOGO = RAIZ / "docs" / "plantillas" / "logo-invenio.png"


# =========================================================================== #
# El formato IEEE, y lo que hay que arreglarle a la salida de pandoc           #
# =========================================================================== #
#
# Pandoc no sabe que va a dos columnas. Emite `longtable` para toda tabla y
# `figure` para toda imagen, y **ninguno de los dos funciona en una columna de
# 3,5 pulgadas**: longtable no esta permitido en modo `twocolumn` -LaTeX falla- y
# una figura de un diagrama sale ilegible a ese ancho.
#
# La correccion es mecanica y se hace aca, sobre el LaTeX intermedio, en vez de
# ensuciar el Markdown con codigo de un formato. El Markdown sigue siendo la
# fuente y sigue sirviendo igual para el .docx.


def _longtable_a_tabla(latex: str) -> str:
    """Convierte los `longtable` de pandoc en `table*` que cruza las columnas."""

    def reemplazo(coincidencia: re.Match) -> str:
        especificacion = coincidencia.group(1)
        cuerpo = coincidencia.group(2)

        # `\endfirsthead` viene precedido de una copia del encabezado. Si esta,
        # se descarta todo lo anterior: en una tabla que no se parte en paginas
        # ese encabezado duplicado saldria dos veces.
        if "\\endfirsthead" in cuerpo:
            cuerpo = cuerpo.split("\\endfirsthead", 1)[1]
        for marca in ("\\endhead", "\\endfoot", "\\endlastfoot"):
            cuerpo = cuerpo.replace(marca, "")

        # Dentro de `table*` el ancho disponible es el del texto, no el de una
        # columna. Sin esto las celdas se calculan contra 3,5 in y la tabla sale
        # apretada en la mitad izquierda.
        cuerpo = cuerpo.replace("\\columnwidth", "\\textwidth")

        return (
            "\\begin{table*}[t]\n\\centering\\footnotesize\n"
            f"\\begin{{tabular}}{{{especificacion}}}\n{cuerpo}\n"
            "\\end{tabular}\n\\end{table*}"
        )

    return re.sub(
        r"\\begin\{longtable\}\[\]\{([^}]*)\}(.*?)\\end\{longtable\}",
        reemplazo,
        latex,
        flags=re.DOTALL,
    )


def _figuras_anchas(latex: str) -> str:
    """Las figuras cruzan las dos columnas y se ajustan al ancho del texto.

    Todas las imagenes de estos documentos son diagramas. A 3,5 in de ancho no se
    leen las etiquetas, asi que no hay caso en el que convenga dejarlas dentro de
    una columna.

    **Solo toca lo que esta dentro de un entorno `figure`.** La primera version
    reescribia todo `\\includegraphics` del archivo, incluido el del logo en el
    bloque de titulo, y le encajaba un ancho de pagina entera a un logo de 12 mm.
    """
    latex = latex.replace("\\begin{figure}", "\\begin{figure*}[t]").replace(
        "\\end{figure}", "\\end{figure*}"
    )

    def ensanchar(bloque: re.Match) -> str:
        # `\includegraphics` sin ancho usa el tamano natural del PNG, que a 2x de
        # escala se sale de la pagina. `keepaspectratio` evita deformarlas y el
        # tope de alto impide que una figura alta ocupe una pagina entera.
        return re.sub(
            r"\\includegraphics(?:\[[^\]]*\])?\{",
            # 0,55 y no 0,40: con el tope mas bajo los diagramas de componentes
            # y de despliegue -mas altos que anchos- quedaban a media pagina y
            # sus etiquetas no se leian impresas. Medido sobre el PDF, no
            # estimado.
            "\\\\includegraphics[width=\\\\textwidth,height=0.55\\\\textheight,"
            "keepaspectratio]{",
            bloque.group(0),
        )

    return re.sub(r"\\begin\{figure\*\}.*?\\end\{figure\*\}", ensanchar, latex, flags=re.DOTALL)


def _imagenes_junto_al_tex(latex: str, origen: Path, trabajo: Path) -> str:
    """Copia cada imagen al lado del .tex y deja solo su nombre en el codigo.

    `\\includegraphics` de LaTeX **no admite espacios en la ruta**, y la carpeta
    de trabajo de este proyecto se llama «Proyecto integrador». La primera
    version fallaba con «Argument of \\Gin@ii has an extra }», que no dice nada
    sobre el espacio y cuesta un rato relacionar.

    Copiar es mas robusto que escapar: funciona igual con acentos, con espacios y
    con rutas de red.
    """
    rutas = set(re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", latex))
    for ruta in rutas:
        candidato = Path(ruta)
        if not candidato.is_absolute():
            candidato = origen / ruta
        if not candidato.exists():
            continue
        seguro = re.sub(r"[^A-Za-z0-9._-]", "-", candidato.name)
        shutil.copy(candidato, trabajo / seguro)
        latex = latex.replace(f"{{{ruta}}}", f"{{{seguro}}}")
    return latex


#: Marca de bloque que **no** va al entregable.
#:
#: Los documentos del repositorio llevan notas de gestion -que historia los
#: cubre, que secciones estan vacias y por que, quien las escribe- que le sirven
#: al equipo y no tienen lugar en un articulo academico.
#:
#: La alternativa era mantener dos versiones del documento, y esa es exactamente
#: la incidencia que este archivo existe para evitar. Una marca en la fuente
#: cuesta una linea y no puede desincronizarse.
#:
#:     ::: no-entregable
#:     Nota interna que el equipo necesita y el lector del PDF no.
#:     :::
MARCA_INTERNA = "no-entregable"


def sin_bloques_internos(markdown: str) -> str:
    """Quita los `::: no-entregable ... :::` antes de que pandoc los vea."""
    patron = re.compile(
        rf"^:::+\s*{re.escape(MARCA_INTERNA)}\s*$.*?^:::+\s*$\n?",
        re.DOTALL | re.MULTILINE,
    )
    return patron.sub("", markdown)


def _sin_saltos_de_pagina_sueltos(latex: str) -> str:
    """Quita los `\\pagebreak` que pandoc arrastra de los `---` del Markdown."""
    return latex.replace("\\begin{center}\\rule{0.5\\linewidth}{0.5pt}\\end{center}", "")


#: Ancho util de una pagina carta con margenes de 1 pulgada, en twips.
#: 8,5 in - 2 in = 6,5 in, y 1 in son 1440 twips.
ANCHO_UTIL_TWIPS = 9360


def anchos_de_tabla(docx: Path) -> int:
    """Le pone anchos de columna a las tablas del .docx. Devuelve cuantas arreglo.

    ===========================================================================
    EL DEFECTO, QUE ES SILENCIOSO Y POR ESO GRAVE
    ===========================================================================

    Pandoc 2.9 emite las tablas con la rejilla **vacia**:

        <w:tblGrid />

    sin un solo `<w:gridCol>`. Word lo tolera y calcula los anchos solo, asi que
    **el .docx se ve perfecto**. LibreOffice no: colapsa todas las columnas menos
    la primera.

    Y como el PDF se produce convirtiendo el .docx con LibreOffice, el resultado
    es el peor de los casos: **el documento que se revisa esta bien y el que se
    entrega esta mal.** Se detecto extrayendo el texto del PDF del zip y buscando
    una cifra que tenia que estar; la tabla de la primera pagina mostraba los
    rotulos y ningun valor.

    ===========================================================================
    LA CORRECCION
    ===========================================================================

    Se cuentan las celdas de la primera fila de cada tabla y se escribe una
    rejilla con columnas iguales, mas un ancho de tabla del 100 %. Es lo que Word
    hubiera calculado, escrito de forma explicita para que no dependa del lector.

    Columnas iguales y no proporcionales al contenido: repartir por longitud de
    texto exigiria medir la fuente, y el reparto parejo ya resuelve el defecto.
    """
    with zipfile.ZipFile(docx) as archivo:
        piezas = {n: archivo.read(n) for n in archivo.namelist()}

    documento = piezas["word/document.xml"].decode("utf-8")
    arregladas = 0

    def rejilla(coincidencia: re.Match) -> str:
        nonlocal arregladas
        tabla = coincidencia.group(0)
        if "<w:gridCol" in tabla:
            return tabla

        primera = re.search(r"<w:tr\b.*?</w:tr>", tabla, re.DOTALL)
        if not primera:
            return tabla
        columnas = len(re.findall(r"<w:tc\b", primera.group(0)))
        if columnas == 0:
            return tabla

        ancho = ANCHO_UTIL_TWIPS // columnas
        celdas = "".join(f'<w:gridCol w:w="{ancho}" />' for _ in range(columnas))
        arregladas += 1
        return tabla.replace("<w:tblGrid />", f"<w:tblGrid>{celdas}</w:tblGrid>").replace(
            '<w:tblW w:type="pct" w:w="0.0" />', '<w:tblW w:type="pct" w:w="5000" />'
        )

    documento = re.sub(r"<w:tbl>.*?</w:tbl>", rejilla, documento, flags=re.DOTALL)
    piezas["word/document.xml"] = documento.encode("utf-8")

    with zipfile.ZipFile(docx, "w", zipfile.ZIP_DEFLATED) as archivo:
        for nombre, contenido in piezas.items():
            archivo.writestr(nombre, contenido)

    return arregladas


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


def construir_ieee(documento: Path, salida: Path) -> int:
    """PDF en formato de conferencia IEEE: dos columnas, Times, logo."""
    # xelatex y no pdflatex: los documentos usan ≈ × · ± ≤ ≥ — °, y pdflatex
    # exige declarar cada uno a mano. Ver el encabezado de la plantilla.
    if not shutil.which("xelatex"):
        print("\n  Falta XeLaTeX.")
        print("      Windows: winget install MiKTeX.MiKTeX")
        print(
            "      Debian:  sudo apt install texlive-xetex "
            "texlive-latex-recommended texlive-fonts-recommended\n"
        )
        return 1

    trabajo = salida / f".{documento.stem}-ieee"
    trabajo.mkdir(parents=True, exist_ok=True)
    shutil.copy(LOGO, trabajo / LOGO.name)

    # Se le da a pandoc una copia sin las notas internas. El original no se toca.
    original = documento.read_text(encoding="utf-8")
    limpio = sin_bloques_internos(original)
    if limpio != original:
        quitados = original.count(f"::: {MARCA_INTERNA}")
        print(f"  {quitados} bloque(s) marcados como internos, fuera del entregable")
    fuente = trabajo / documento.name
    fuente.write_text(limpio, encoding="utf-8")

    tex = trabajo / f"{documento.stem}.tex"
    orden = [
        _pandoc(),
        str(fuente),
        "-o",
        str(tex),
        f"--resource-path={documento.parent}",
        f"--template={PLANTILLA_IEEE}",
        f"--variable=logo:{LOGO.name}",
        "--standalone",
        "--from=markdown+pipe_tables+yaml_metadata_block",
        "--to=latex",
        # Sin esto pandoc parte las tablas anchas por el ancho de la terminal.
        "--columns=200",
        # El `#` de nivel 1 del Markdown es el TITULO del documento, no una
        # seccion. Con este desplazamiento `##` pasa a seccion y `###` a
        # subseccion, que es la jerarquia que los documentos ya usan.
        "--shift-heading-level-by=-1",
    ]
    proceso = subprocess.run(orden, capture_output=True, text=True, check=False)
    if proceso.returncode != 0:
        print(f"\n  pandoc fallo:\n{proceso.stderr}")
        return 1

    latex = tex.read_text(encoding="utf-8")
    latex = _longtable_a_tabla(latex)
    # Ensanchar ANTES de copiar: la primera pasada mira el entorno `figure`, y la
    # segunda ya no distingue de donde vino cada ruta.
    latex = _figuras_anchas(latex)
    latex = _imagenes_junto_al_tex(latex, documento.parent, trabajo)
    latex = _sin_saltos_de_pagina_sueltos(latex)
    tex.write_text(latex, encoding="utf-8")

    # Dos pasadas: la primera resuelve las referencias, la segunda las coloca.
    for pasada in (1, 2):
        proceso = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex.name],
            cwd=trabajo,
            capture_output=True,
            text=True,
            # pdflatex emite su registro en la codificacion del sistema, no en
            # UTF-8, y con acentos en los titulos revienta al decodificar. El
            # registro es para leerlo, no para procesarlo: sustituir el byte
            # ilegible es preferible a perder el mensaje de error entero.
            errors="replace",
            check=False,
        )
        if proceso.returncode != 0:
            print(f"\n  xelatex fallo en la pasada {pasada}. Ultimas lineas:\n")
            for linea in proceso.stdout.splitlines()[-25:]:
                print(f"    {linea}")
            print(f"\n  El .tex quedo en {tex} para poder mirarlo.\n")
            return 1

    producido = trabajo / f"{documento.stem}.pdf"
    destino = salida / f"{documento.stem}-IEEE.pdf"
    shutil.copy(producido, destino)
    print(f"  {destino}")

    # La carpeta de trabajo se borra: son .aux, .log y copias de las imagenes.
    # Si algo falla NO se llega hasta aca, y queda para poder mirar el .tex.
    shutil.rmtree(trabajo, ignore_errors=True)
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("documento", type=Path)
    p.add_argument("--salida", type=Path, default=SALIDA)
    p.add_argument("--sin-pdf", action="store_true")
    p.add_argument(
        "--ieee",
        action="store_true",
        help="PDF en formato de conferencia IEEE, dos columnas, con logo",
    )
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

    if args.ieee:
        return construir_ieee(documento, salida)

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

    arregladas = anchos_de_tabla(docx)
    if arregladas:
        print(f"  {arregladas} tabla(s) con anchos de columna escritos, para LibreOffice")
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
