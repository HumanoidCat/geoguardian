"""Arma el .zip de una entrega, con todo lo que hay que subir.

POR QUE EXISTE

Una entrega armada a mano se olvida de un archivo. Este programa la construye
siempre igual, **comprueba que cada pieza existe y que esta al dia**, y falla si
alguna no cumple, en vez de producir un zip que parece correcto.

Es el mismo criterio de I-06: un paso que se salta en silencio se ve igual que
uno que se cumplio.

LO DE «AL DIA» SE AGREGO POR I-15, Y ES LA MITAD QUE FALTABA

Comprobar solo la existencia dejaba pasar el caso peor. El 2026-08-30 fallo la
construccion de los PDF -faltaban pandoc y XeLaTeX- y esta herramienta armo el
zip igual, con los documentos anteriores al cambio de escala del SPI: nombre
correcto, fecha de hoy, 1,9 MB, contenido viejo.

**Un paquete al que le falta un archivo se nota al abrirlo. Uno que trae el
archivo equivocado, no.**

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

#: (ruta de origen, nombre dentro del zip, obligatorio, fuente de la que se deriva)
#:
#: El nombre dentro del zip **no** es el del archivo en disco: `13-` y `17-` son
#: numeros de documento del repositorio y no le dicen nada a quien lo recibe.
#:
#: **La cuarta columna existe por un defecto real, del 2026-08-30.** Ese dia el
#: constructor de PDF fallo -faltaban pandoc y XeLaTeX- y esta herramienta armo
#: el zip igual: comprobaba que los PDF **existieran**, no que estuvieran **al
#: dia**. El paquete salio con 1,9 MB de documentos anteriores al cambio de
#: escala del SPI, con nombre correcto y fecha reciente. Nada advirtio nada.
#:
#: Es I-06 llegando hasta el artefacto que se entrega, que es el peor lugar
#: donde puede llegar: un zip incompleto se nota, uno desactualizado no.
PIEZAS: list[tuple[Path, str, bool, Path | None]] = [
    (
        GESTION / "13-documento-ieee-IEEE.pdf",
        "1 - Documento de investigacion IEEE.pdf",
        True,
        RAIZ / "docs" / "13-documento-ieee.md",
    ),
    # SIN formato IEEE: el profesor lo pidio explicitamente el 2026-08-27.
    # «Documentacion tecnica no va en IEEE».
    (
        GESTION / "17-documento-tecnico.pdf",
        "2 - Documentacion tecnica del MVP.pdf",
        True,
        RAIZ / "docs" / "17-documento-tecnico.md",
    ),
    (
        GESTION / "17-documento-tecnico.docx",
        "2 - Documentacion tecnica del MVP.docx",
        False,
        RAIZ / "docs" / "17-documento-tecnico.md",
    ),
    # La guia de entregables de la carrera pide, ademas de la documentacion
    # tecnica, el manual de usuario y el manual tecnico de instalacion. Entran
    # desde el 2026-09-10, para la entrega de semana 12.
    (
        GESTION / "18-manual-de-usuario.pdf",
        "3 - Manual de usuario del visor.pdf",
        True,
        RAIZ / "docs" / "18-manual-de-usuario.md",
    ),
    (
        GESTION / "10-manual-tecnico.pdf",
        "4 - Manual tecnico de instalacion.pdf",
        True,
        RAIZ / "docs" / "10-manual-tecnico.md",
    ),
    (
        GESTION / "20-manual-de-operacion.pdf",
        "5 - Manual de operacion.pdf",
        False,
        RAIZ / "docs" / "20-manual-de-operacion.md",
    ),
]

#: Ademas del Markdown, un PDF depende de las figuras que incrusta. Si se
#: regeneran las figuras y no el PDF, el PDF queda mostrando graficos viejos, que
#: es exactamente lo que paso con `contraste-catalogo.png` al cambiar la escala.
FIGURAS = RAIZ / "docs" / "figuras"


def desactualizados() -> list[tuple[Path, Path]]:
    """Piezas cuyo origen es **mas viejo** que algo de lo que se deriva.

    Devuelve (pieza, el archivo que la dejo obsoleta).

    Se compara por fecha de modificacion y no por suma: el PDF no contiene al
    Markdown, asi que no hay suma que cruzar. Es un criterio mas debil -tocar un
    .md sin cambiarlo dispara el aviso- y se prefiere asi: **el falso positivo
    cuesta una reconstruccion; el falso negativo cuesta entregar el documento
    equivocado.**
    """
    fuentes_comunes = sorted(FIGURAS.glob("*.png"))
    obsoletas: list[tuple[Path, Path]] = []

    for origen, _, _, fuente in PIEZAS:
        if not origen.exists():
            continue
        momento = origen.stat().st_mtime
        candidatas = ([fuente] if fuente else []) + fuentes_comunes
        posteriores = [c for c in candidatas if c.exists() and c.stat().st_mtime > momento]
        if posteriores:
            obsoletas.append((origen, max(posteriores, key=lambda c: c.stat().st_mtime)))

    return obsoletas


#: **El avance de Semana 8 no va aca, y es deliberado.** Ya se entrego, es una
#: foto de esa semana y no se vuelve a tocar. Queda en el repositorio como
#: registro. Los entregables vivos son los dos documentos de arriba.

LEEME = """GeoGuardian - Documentacion
Universidad Invenio - Ingenieria en Tecnologias de Informacion
III Trimestre 2026 - {fecha}

Alejandro Josue Rodriguez Zamora
Cesar Andres Ubau Calvo
Luis Alejandro Luna Garcia
Avril Madrigal Elizondo


QUE HAY EN ESTE ARCHIVO

  1 - Documento de investigacion IEEE.pdf
      El articulo, en formato de conferencia IEEE a dos columnas: tres
      preguntas de investigacion, la hipotesis H1 -rechazada con la
      medicion-, siete hallazgos sobre los datos abiertos, seis figuras con
      sus tablas, y las conclusiones sobre lo medido.

  2 - Documentacion tecnica del MVP.pdf
      Descripcion funcional y casos de uso, tecnologias con sus versiones,
      arquitectura, modelo de datos, procesamiento y modelado, API, visor,
      verificacion y evidencia de pruebas, despliegue, decisiones, y como
      leer los identificadores. NO va en formato IEEE.

  3 - Manual de usuario del visor.pdf
      Como se usa el visor publicado, pantalla por pantalla.

  4 - Manual tecnico de instalacion.pdf
      Levantar el sistema en una maquina limpia, paso a paso; verificado por
      una persona ajena al proyecto.

  5 - Manual de operacion.pdf  (si esta construido)
      Como se atiende el sistema publicado dia a dia.

  diagramas/
      Los diagramas de arquitectura en PNG, por si hacen falta sueltos.


EL SISTEMA, EN LINEA

  Repositorio       https://github.com/HumanoidCat/geoguardian
  Visor, dato real  https://visor-production-40b5.up.railway.app/
  Visor, demo       https://humanoidcat.github.io/geoguardian/

  El segundo es el visor sin servidor detras: degrada a un respaldo estatico
  de datos simulados y lo declara en pantalla. Es la degradacion que el
  propio diseno exige, no un sobrante.


COMO SE REPRODUCE TODO ESTO

  Los PDF no se editan: se generan desde los Markdown del repositorio.

      python docs/herramientas/generar_diagramas.py --png
      python docs/herramientas/generar_figuras.py --tabuladas
      python docs/herramientas/construir_entregable.py docs/13-documento-ieee.md --ieee
      python docs/herramientas/construir_entregable.py docs/17-documento-tecnico.md
      python docs/herramientas/construir_entregable.py docs/18-manual-de-usuario.md
      python docs/herramientas/construir_entregable.py docs/10-manual-tecnico.md
      python docs/herramientas/construir_entregable.py docs/20-manual-de-operacion.md

  Y este mismo archivo:

      python docs/herramientas/armar_entrega.py
"""


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--nombre", default="GeoGuardian - Documentacion")
    p.add_argument("--salida", type=Path, default=GESTION)
    p.add_argument("--con-docx", action="store_true", help="incluye tambien los .docx")
    p.add_argument(
        "--aunque-esten-viejos",
        action="store_true",
        help="empaqueta aunque los PDF sean anteriores a sus fuentes. Se declara en la salida.",
    )
    args = p.parse_args()

    print(f"\nArmando la entrega: {args.nombre}\n")

    def como_se_construyen() -> None:
        print("\n  Se construyen con:\n")
        print("      python docs/herramientas/generar_diagramas.py --png")
        print("      python docs/herramientas/generar_figuras.py --tabuladas")
        print(
            "      python docs/herramientas/construir_entregable.py "
            "docs/13-documento-ieee.md --ieee"
        )
        print(
            "      python docs/herramientas/construir_entregable.py "
            "docs/17-documento-tecnico.md\n"
        )

    faltan = [origen for origen, _, obligatorio, _ in PIEZAS if obligatorio and not origen.exists()]
    if faltan:
        print("  FALTAN PIEZAS OBLIGATORIAS:\n")
        for f in faltan:
            print(f"    {f.name}")
        como_se_construyen()
        return 1

    # ----------------------------------------------------------------------- #
    # Y el control que faltaba: que ademas de existir, esten al dia
    # ----------------------------------------------------------------------- #
    obsoletas = desactualizados()
    if obsoletas and not args.aunque_esten_viejos:
        print("  HAY PIEZAS DESACTUALIZADAS. No se arma el zip.\n")
        for pieza, culpable in obsoletas:
            print(f"    {pieza.name}")
            print(f"        es anterior a {culpable.relative_to(RAIZ)}\n")
        print("  Esto pasa cuando el constructor de PDF falla y su salida se pierde")
        print("  entre otros comandos. El zip quedaria con nombre correcto, fecha")
        print("  reciente y **contenido viejo**, que no se nota al abrirlo.")
        como_se_construyen()
        print("  Si de verdad se quiere empaquetar asi: --aunque-esten-viejos\n")
        return 1

    diagramas = sorted(DIAGRAMAS.glob("*.png"))
    if not diagramas:
        print("  No hay PNG de los diagramas. Se generan con:\n")
        print("      python docs/herramientas/generar_diagramas.py --png\n")
        return 1

    args.salida.mkdir(parents=True, exist_ok=True)
    destino = args.salida / f"{args.nombre}.zip"

    # Si se forzo el empaquetado con piezas viejas, **el zip lo dice**. Una
    # bandera que evita el control y no deja rastro dentro del artefacto es peor
    # que no tener el control: da permiso y borra la evidencia de haberlo usado.
    aviso = ""
    if obsoletas:
        lineas = "\n".join(f"      {p.name}" for p, _ in obsoletas)
        aviso = (
            "\n\nATENCION: ESTE PAQUETE SE ARMO CON PIEZAS DESACTUALIZADAS\n\n"
            "  Los siguientes archivos son anteriores a las fuentes de las que\n"
            "  se derivan, y se empaquetaron con --aunque-esten-viejos:\n\n"
            f"{lineas}\n"
        )

    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zip_:
        zip_.writestr("LEEME.txt", LEEME.format(fecha=date.today().isoformat()) + aviso)
        print("  LEEME.txt" + ("   CON AVISO DE PIEZAS VIEJAS" if aviso else ""))

        for origen, nombre, obligatorio, _ in PIEZAS:
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
