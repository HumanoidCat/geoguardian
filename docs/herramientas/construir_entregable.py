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


def _pesos_de_columnas(cuerpo: str, columnas: int) -> list[float]:
    """Ancho relativo de cada columna, segun el largo de su celda mas larga.

    **Por que hace falta.** Pandoc decide la especificacion de columnas contra
    el ancho de una pagina normal, y este documento va a dos columnas. Cuando
    calcula que la tabla cabe emite `l`, que **no corta linea**: una celda larga
    se sale de la caja y se imprime sobre el margen.

    Repartir en partes iguales lo arregla y desperdicia: en la tabla de umbrales
    dejaria «Evento» con el mismo ancho que una justificacion de tres lineas.
    Asi que se mide el contenido.

    Se usa el **maximo** y no el promedio porque lo que decide si una celda
    desborda es su caso peor, no su caso tipico.

    Los pesos se normalizan para que sumen `columnas`, que es lo que `tabularx`
    espera: con `\\hsize=#1\\hsize`, la suma de los pesos tiene que ser igual al
    numero de columnas o el ancho total deja de ser `\\textwidth`.
    """
    largos = [1.0] * columnas
    for linea in cuerpo.splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("\\"):
            continue
        celdas = linea.replace("\\tabularnewline", "").split("&")
        if len(celdas) != columnas:
            continue
        for i, celda in enumerate(celdas):
            # Se descuentan los comandos de LaTeX: `\textbf{...}` ocupa siete
            # caracteres en la fuente y cero en la pagina.
            visible = re.sub(r"\\[a-zA-Z]+\{?|\}", "", celda).strip()
            largos[i] = max(largos[i], float(len(visible)))

    # Un piso, para que una columna de una letra no quede impresa en vertical.
    largos = [max(x, 6.0) for x in largos]
    total = sum(largos)
    return [x * columnas / total for x in largos]


#: Caracteres que caben en una columna del documento IEEE, en tipografia
#: monoespaciada a cuerpo pequeno. Medido sobre la salida, no estimado: el
#: diagrama de modulos tiene 79 y se salia; los bloques de 44 no.
ANCHO_DE_COLUMNA = 48


def _bloques_anchos(latex: str) -> str:
    """Los bloques literales que no caben en una columna cruzan las dos.

    **Por que hace falta.** Un `verbatim` no corta linea: si la linea mas larga
    excede el ancho de la columna, el texto se imprime sobre el margen derecho
    y LaTeX lo reporta como un Overfull hbox, que no detiene la compilacion.

    Y **no se puede dejar que corte**. Estos bloques son diagramas de flechas
    alineados por espacios: partirlos por la mitad no los hace mas angostos,
    los destruye.

    Asi que se promueven a `figure*`, que ocupa el ancho de la pagina, igual que
    las tablas anchas. No llevan `\\caption` a proposito: no son figuras del
    documento, no se referencian, y numerarlas correria la numeracion de las que
    si se referencian.
    """

    def reemplazo(coincidencia: re.Match) -> str:
        contenido = coincidencia.group(1)
        lineas = contenido.strip("\n").split("\n")
        if max((len(x) for x in lineas), default=0) <= ANCHO_DE_COLUMNA:
            return coincidencia.group(0)
        return (
            "\\begin{figure*}[t]\n\\centering\n\\begin{minipage}{\\textwidth}\n"
            "\\footnotesize\n"
            f"\\begin{{verbatim}}{contenido}\\end{{verbatim}}\n"
            "\\end{minipage}\n\\end{figure*}"
        )

    return re.sub(
        r"\\begin\{verbatim\}(.*?)\\end\{verbatim\}",
        reemplazo,
        latex,
        flags=re.DOTALL,
    )


def _portada(markdown: str, base: Path) -> tuple[str, str]:
    """Arma la portada del .docx: titulo, autores, logo. Devuelve (texto, titulo).

    ===========================================================================
    EL DEFECTO QUE ESTO CORRIGE, Y LO INTRODUJE YO
    ===========================================================================

    Pandoc toma como **titulo del documento** el primer `#` del cuerpo, y solo
    si es el primer bloque. Al insertar el logo delante para cumplir el pedido
    del profesor, el primer bloque paso a ser la imagen: el `#` dejo de ser el
    titulo y quedo como un encabezado cualquiera.

    El resultado en la portada era exactamente al reves de lo que corresponde:
    los autores arriba de todo, el logo suelto en el medio, y el nombre del
    documento **impreso mas chico que la seccion que le sigue**.

    La leccion: `--shift-heading-level-by=-1` **depende del orden de los
    bloques**, y por eso es fragil. Aca se reemplaza por metadatos explicitos,
    que no dependen de nada.

    ===========================================================================
    QUE HACE
    ===========================================================================

    Saca el `#` del cuerpo y lo declara como `title:` en el YAML. Con el titulo
    en los metadatos, pandoc usa el estilo «Title» -grande, arriba de todo- sin
    importar que venga despues, y el logo puede ir donde corresponda sin romper
    nada.
    """
    if not markdown.startswith("---\n"):
        return markdown, ""

    partes = markdown.split("---\n", 2)
    if len(partes) != 3:
        return markdown, ""
    _, yaml, cuerpo = partes

    titulo = ""
    lineas = cuerpo.lstrip("\n").split("\n")
    if lineas and lineas[0].startswith("# "):
        titulo = lineas[0][2:].strip()
        cuerpo = "\n".join(lineas[1:])

    if titulo and "title:" not in yaml:
        # Va **primero** en el YAML por legibilidad del archivo intermedio; a
        # pandoc el orden de las claves le da igual.
        yaml = f'title: "{titulo}"\n' + yaml

    if LOGO.exists():
        relativo = LOGO.relative_to(base).as_posix()
        # Despues del bloque de titulo, no antes: antes es lo que rompia la
        # deteccion del titulo.
        cuerpo = f"\n![]({relativo}){{width=42mm}}\n{cuerpo}"

    return f"---\n{yaml}---\n{cuerpo}", titulo


def _tabla_ancha(especificacion: str, cuerpo: str) -> str:
    """Un `longtable` de pandoc convertido en `table*` que cruza las columnas."""
    # `\endfirsthead` viene precedido de una copia del encabezado. Si esta, se
    # descarta todo lo anterior: en una tabla que no se parte en paginas ese
    # encabezado duplicado saldria dos veces.
    if "\\endfirsthead" in cuerpo:
        cuerpo = cuerpo.split("\\endfirsthead", 1)[1]
    for marca in ("\\endhead", "\\endfoot", "\\endlastfoot"):
        cuerpo = cuerpo.replace(marca, "")

    # Dentro de `table*` el ancho disponible es el del texto, no el de una
    # columna. Sin esto las celdas se calculan contra 3,5 in y la tabla sale
    # apretada en la mitad izquierda.
    cuerpo = cuerpo.replace("\\columnwidth", "\\textwidth")

    # Cuantas columnas tiene. Se cuentan los tipos de columna, no los `@{}` ni
    # los `>{...}`, que se sustituyen antes por un marcador neutro.
    sin_grupos = re.sub(r"@\{[^}]*\}|>\{[^}]*\}", "", especificacion)
    sin_grupos = re.sub(r"[pmb]\{[^}]*\}", "P", sin_grupos)
    columnas = len(re.findall(r"[lcrPX]", sin_grupos))

    if columnas < 2:
        # Una tabla de una columna no tiene problema de reparto.
        return (
            "\\begin{table*}[t]\n\\centering\\footnotesize\n"
            f"\\begin{{tabular}}{{{especificacion}}}\n{cuerpo}\n"
            "\\end{tabular}\n\\end{table*}"
        )

    pesos = _pesos_de_columnas(cuerpo, columnas)
    nueva = "@{}" + "".join(f"L{{{p:.3f}}}" for p in pesos) + "@{}"

    # `tabularx` y no `tabular`: es el que reparte un ancho fijo entre las
    # columnas `X`. Con `tabular` los pesos no significan nada.
    return (
        "\\begin{table*}[t]\n\\centering\\footnotesize\n"
        f"\\begin{{tabularx}}{{\\textwidth}}{{{nueva}}}\n{cuerpo}\n"
        "\\end{tabularx}\n\\end{table*}"
    )


def _longtable_a_tabla(latex: str) -> str:
    """Convierte los `longtable` de pandoc en `table*` que cruza las columnas."""
    # LA ESPECIFICACION SE EXTRAE CONTANDO LLAVES, NO CON `[^}]*`
    #
    # **Este era el defecto que hacia que las tablas se salieran de la pagina.**
    # La primera version usaba `\\{([^}]*)\\}` para capturar la especificacion de
    # columnas. Pandoc emite `@{}lll@{}`, y `[^}]*` se detiene en la llave de
    # `@{}`: la especificacion salia **vacia** y `lll@{}}` se fugaba al cuerpo
    # de la tabla.
    #
    # El resultado era una tabla sin especificacion de columnas valida. LaTeX no
    # se quejaba lo suficiente como para hacer fallar la compilacion -solo
    # emitia un Overfull hbox- asi que el PDF salia con el texto impreso sobre
    # el margen derecho y el proceso terminaba en verde.
    #
    # Es el mismo patron que I-15: un paso que produce algo incorrecto sin
    # fallar. Aca ademas era visible en el PDF, y aun asi hubo que mirarlo.
    salida: list[str] = []
    resto = latex
    ABRE = "\\begin{longtable}[]{"

    while ABRE in resto:
        antes, despues = resto.split(ABRE, 1)
        salida.append(antes)

        # La llave que cierra la especificacion es la que equilibra a la que
        # abre. `@{}` mete un par completo que no cuenta como cierre.
        nivel, corte = 1, None
        for i, caracter in enumerate(despues):
            if caracter == "{":
                nivel += 1
            elif caracter == "}":
                nivel -= 1
                if nivel == 0:
                    corte = i
                    break
        if corte is None:
            salida.append(ABRE)
            resto = despues
            continue

        especificacion = despues[:corte]
        tras_especificacion = despues[corte + 1 :]
        if "\\end{longtable}" not in tras_especificacion:
            salida.append(ABRE + despues)
            resto = ""
            break
        cuerpo, resto = tras_especificacion.split("\\end{longtable}", 1)
        salida.append(_tabla_ancha(especificacion, cuerpo))

    salida.append(resto)
    return "".join(salida)


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

        # ANCHOS PROPORCIONALES AL CONTENIDO, NO IGUALES
        #
        # El reparto parejo resolvia el defecto de LibreOffice y producia uno
        # visual: en la tabla de contenido, la columna de numeros -«1», «2»…-
        # se llevaba la mitad del ancho y quedaba un hueco enorme antes del
        # nombre de la seccion.
        #
        # Se mide el texto de cada columna en **todas** las filas y se reparte
        # en proporcion, con un piso para que ninguna quede impresa en vertical.
        # Es la misma idea que `_pesos_de_columnas` aplica al camino IEEE.
        largos = [1.0] * columnas
        for fila in re.findall(r"<w:tr\b.*?</w:tr>", tabla, re.DOTALL):
            celdas_fila = re.findall(r"<w:tc\b.*?</w:tc>", fila, re.DOTALL)
            if len(celdas_fila) != columnas:
                continue
            for i, celda in enumerate(celdas_fila):
                texto = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", celda, re.DOTALL))
                largos[i] = max(largos[i], float(len(texto)))

        largos = [max(x, 4.0) for x in largos]
        total = sum(largos)
        anchos = [max(1, int(ANCHO_UTIL_TWIPS * x / total)) for x in largos]
        celdas = "".join(f'<w:gridCol w:w="{a}" />' for a in anchos)
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


def centrar_imagenes_solas(docx: Path) -> int:
    """Centra los parrafos que contienen **solo** una imagen. Devuelve cuantos.

    Pandoc no centra imagenes en el .docx: las deja alineadas a la izquierda,
    que es lo correcto para una figura dentro del texto y **queda mal en la
    portada**, con el logo pegado al margen debajo de un titulo y unos autores
    centrados.

    Se probaron las dos formas de escribirlo en Markdown -con y sin texto
    alternativo- y ninguna cambia la alineacion: es una decision de la plantilla
    de referencia, no del Markdown. Asi que se corrige donde se decide, sobre el
    XML, igual que `anchos_de_tabla`.

    **Solo toca parrafos sin texto.** Una imagen intercalada en un parrafo con
    palabras alrededor se centraria arrastrando el texto con ella.
    """
    with zipfile.ZipFile(docx) as archivo:
        piezas = {n: archivo.read(n) for n in archivo.namelist()}

    documento = piezas["word/document.xml"].decode("utf-8")
    centrados = 0

    def centrar(coincidencia: re.Match) -> str:
        nonlocal centrados
        parrafo = coincidencia.group(0)
        if "<w:drawing>" not in parrafo:
            return parrafo
        # Con texto adentro no es un parrafo de imagen sola.
        if re.search(r"<w:t[ >]", parrafo):
            return parrafo
        if 'w:jc w:val="center"' in parrafo:
            return parrafo

        centrados += 1
        if "<w:pPr>" in parrafo:
            return parrafo.replace("<w:pPr>", '<w:pPr><w:jc w:val="center" />', 1)
        # Sin propiedades previas, el bloque va justo despues de abrir `w:p`.
        return re.sub(
            r"(<w:p\b[^>]*>)",
            r'\1<w:pPr><w:jc w:val="center" /></w:pPr>',
            parrafo,
            count=1,
        )

    documento = re.sub(r"<w:p\b[^>]*>.*?</w:p>", centrar, documento, flags=re.DOTALL)
    piezas["word/document.xml"] = documento.encode("utf-8")

    with zipfile.ZipFile(docx, "w", zipfile.ZIP_DEFLATED) as archivo:
        for nombre, contenido in piezas.items():
            archivo.writestr(nombre, contenido)

    return centrados


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
    latex = _bloques_anchos(latex)
    # Ensanchar ANTES de copiar: la primera pasada mira el entorno `figure`, y la
    # segunda ya no distingue de donde vino cada ruta.
    latex = _figuras_anchas(latex)
    latex = _imagenes_junto_al_tex(latex, documento.parent, trabajo)
    latex = _sin_saltos_de_pagina_sueltos(latex)
    tex.write_text(latex, encoding="utf-8")

    # Dos pasadas: la primera resuelve las referencias, la segunda las coloca.
    #
    # LA SALIDA VA EN VIVO, Y NO ES UN DETALLE DE COMODIDAD
    #
    # La primera version capturaba la salida y la mostraba solo al fallar. Con
    # una distribucion de TeX ya armada eso esta bien: la compilacion tarda
    # segundos. **En una instalacion recien hecha, no.** MiKTeX descarga los
    # paquetes que faltan sobre la marcha, tarda minutos, y a veces abre un
    # dialogo pidiendo confirmacion.
    #
    # Capturando la salida, todo eso ocurre detras de una pantalla en blanco:
    # el proceso **esta trabajando y parece colgado**, que es indistinguible de
    # estar colgado de verdad. Costo varias vueltas de diagnostico equivocado el
    # 2026-08-30, ninguna sobre el problema real.
    #
    # Mostrarla en vivo cuesta perder el resumen de las ultimas lineas al
    # fallar. No importa: xelatex ya escribe todo en su `.log`, que queda al
    # lado del `.tex` y se puede leer entero en vez de en un extracto.
    print("\n  Compilando con xelatex. La salida va en vivo:")
    print("  si es la primera vez, MiKTeX descarga paquetes y tarda minutos.\n")

    registro = trabajo / f"{documento.stem}.log"
    for pasada in (1, 2):
        print(f"  --- pasada {pasada} de 2 " + "-" * 52)
        proceso = subprocess.run(
            ["xelatex", "-interaction=nonstopmode", "-halt-on-error", tex.name],
            cwd=trabajo,
            check=False,
        )
        if proceso.returncode != 0:
            print(f"\n  xelatex fallo en la pasada {pasada}.\n")
            print(f"  El registro completo esta en {registro}")
            print(f"  y el .tex en {tex}\n")
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

    # Las notas internas se quitan en **los dos** caminos. La primera version
    # solo las quitaba en el IEEE, y el documento tecnico -que el profesor pidio
    # que NO fuera IEEE- salio con «Historia: H10.4 · Responsable: Alejandro» en
    # la portada. Se detecto leyendo el PDF, no el Markdown.
    trabajo = salida / f".{documento.stem}"
    trabajo.mkdir(parents=True, exist_ok=True)
    original = documento.read_text(encoding="utf-8")
    limpio = sin_bloques_internos(original)
    if limpio != original:
        quitados = original.count(f"::: {MARCA_INTERNA}")
        print(f"  {quitados} bloque(s) marcados como internos, fuera del entregable")

    # EL LOGO VA EN LOS DOS DOCUMENTOS, Y HASTA HOY SOLO IBA EN UNO
    #
    # El profesor pidio los dos documentos con el logo de la universidad. El
    # camino IEEE lo recibe por `--variable=logo:`, que la plantilla coloca
    # sobre el bloque de titulo. **El camino .docx no usa esa plantilla**, asi
    # que nunca lo recibio: el tecnico salio sin logo desde el primer dia y
    # nadie lo noto, porque para notarlo hay que abrir el PDF y mirar la
    # portada, no leer el Markdown.
    #
    # Se resuelve anteponiendo la imagen al contenido en vez de con una
    # plantilla de Word. Es menos elegante y tiene una ventaja que aca pesa
    # mas: **se ve igual en el .docx y en el .pdf**, sin depender de que el
    # convertidor respete encabezados de pagina.
    limpio, titulo = _portada(limpio, documento.parent)
    if titulo:
        print(f"  portada: «{titulo}»")

    fuente = trabajo / documento.name
    fuente.write_text(limpio, encoding="utf-8")

    docx = salida / f"{documento.stem}.docx"
    orden = [
        _pandoc(),
        str(fuente),
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
        # El `#` de nivel 1 es el TITULO, igual que en el camino IEEE. Sin esto
        # pandoc arma el bloque de titulo solo con autores y fecha, y el titulo
        # real aparece despues como un encabezado suelto: en el PDF salian los
        # cuatro nombres arriba y el nombre del documento debajo.
        "--shift-heading-level-by=-1",
    ]
    proceso = subprocess.run(orden, capture_output=True, text=True, check=False)
    if proceso.returncode != 0:
        print(f"\n  pandoc fallo:\n{proceso.stderr}")
        return 1

    arregladas = anchos_de_tabla(docx)
    if arregladas:
        print(f"  {arregladas} tabla(s) con anchos de columna escritos, para LibreOffice")
    centradas = centrar_imagenes_solas(docx)
    if centradas:
        print(f"  {centradas} imagen(es) centradas")
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
        shutil.rmtree(trabajo, ignore_errors=True)
        return 0
    print(f"  {pdf}")
    shutil.rmtree(trabajo, ignore_errors=True)

    print("\n  Recordatorio: el .docx y el .pdf son artefactos. Si hay que")
    print(f"  corregir algo, se corrige {documento.name} y se vuelve a construir.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
