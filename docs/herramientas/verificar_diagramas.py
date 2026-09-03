"""Comprueba que los diagramas describen el repositorio de hoy.

QUE PROBLEMA RESUELVE

Un diagrama desactualizado es peor que ninguno: se ve autorizado y dice algo
falso. El proyecto ya perdio ocho dias con cinco cifras del documento IEEE que
habian dejado de ser ciertas sin que nadie lo notara, y la respuesta fue poner
una maquina a cruzarlas. Esto es lo mismo, para los dibujos.

QUE COMPRUEBA

    CA-1  cada tabla del DDL aparece en el entidad-relacion
    CA-2  cada clave foranea del DDL aparece como relacion
    CA-3  los seis diagramas existen y no estan vacios
    CA-4  el generador sigue produciendo lo que hay versionado
    CA-5  el control distingue: una tabla que no esta, se detecta

POR QUE **NO** SE COMPARAN LOS BYTES

La primera idea fue regenerar y exigir que el SVG saliera identico. Se descarto
antes de escribirla: **Graphviz no garantiza la misma salida entre versiones**.
Alejandro trabaja en Windows, la integracion continua en Ubuntu, y un cambio de
version del motor de dibujo habria puesto todo en rojo sin que ningun diagrama
estuviera mal.

Ese modo de fallo ya se conoce -es el de I-13, un control que se dispara por algo
que no es el defecto que busca- y un control que la gente aprende a ignorar es
peor que no tenerlo.

Asi que se compara el **contenido**: que cada nombre de tabla, cada columna y
cada relacion que el DDL declara esten presentes en el SVG versionado. Eso
sobrevive a cualquier version de Graphviz y sigue detectando lo unico que
importa: que alguien cambio el esquema y no regenero.

Uso:
    python docs/herramientas/verificar_diagramas.py

Sale con codigo 1 si algo no se cumple, para poder correrlo en CI.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "docs" / "herramientas"))

from generar_diagramas import (  # noqa: E402
    COMPONENTES,
    DECLARADOS,
    SALIDA,
    Tabla,
    dot_entidad_relacion,
    leer_ddl,
    renderizar,
)

ESPERADOS = ["entidad-relacion", *DECLARADOS, "secuencia-consulta-riesgo"]

fallos: list[str] = []


def comprobar(descripcion: str, condicion: bool, detalle: str = "") -> None:
    print(f"  {'OK  ' if condicion else 'FALLO'}  {descripcion}")
    if not condicion:
        fallos.append(descripcion)
        if detalle:
            print(f"        {detalle}")


def texto_de(svg: str) -> str:
    """Todo el texto visible del SVG, sin las etiquetas ni los atributos.

    Graphviz parte los textos largos en varios `<text>`, asi que se concatena
    todo y se busca por subcadena. Es tosco a proposito: lo que interesa es si el
    nombre esta o no esta, no como quedo maquetado.
    """
    return " ".join(re.findall(r"<text[^>]*>(.*?)</text>", svg, re.DOTALL))


def main() -> int:
    print("\nDiagramas contra el repositorio\n")

    tablas: list[Tabla] = leer_ddl()
    comprobar("el DDL declara al menos una tabla", len(tablas) > 0)
    if not tablas:
        return 1

    # ------------------------------------------------------------------ CA-3 - #
    print("CA-3, los seis diagramas existen:")

    svgs: dict[str, str] = {}
    for nombre in ESPERADOS:
        ruta = SALIDA / f"{nombre}.svg"
        existe = ruta.exists() and ruta.stat().st_size > 500
        comprobar(
            f"{ruta.relative_to(RAIZ)}",
            existe,
            "se genera con: python docs/herramientas/generar_diagramas.py",
        )
        if existe:
            svgs[nombre] = ruta.read_text(encoding="utf-8")

    if "entidad-relacion" not in svgs:
        print("\nSin el entidad-relacion no hay nada mas que comprobar.\n")
        return 1

    contenido = texto_de(svgs["entidad-relacion"])

    # ------------------------------------------------------------------ CA-1 - #
    print("\nCA-1, cada tabla del DDL esta en el entidad-relacion:")

    for tabla in tablas:
        comprobar(
            f"{tabla.calificado}",
            tabla.nombre in contenido,
            "esta en basedatos/ddl/ y no en el diagrama. Hay que regenerar",
        )

    print("\ny cada columna tambien:")
    faltantes = [
        f"{t.nombre}.{c.nombre}" for t in tablas for c in t.columnas if c.nombre not in contenido
    ]
    total_columnas = sum(len(t.columnas) for t in tablas)
    comprobar(
        f"las {total_columnas} columnas del DDL aparecen",
        not faltantes,
        f"no aparecen: {faltantes}",
    )

    # ------------------------------------------------------------------ CA-2 - #
    print("\nCA-2, cada clave foranea esta dibujada:")

    relaciones = [(t, propias, destino) for t in tablas for propias, destino in t.referencias]
    comprobar("el DDL declara al menos una clave foranea", len(relaciones) > 0)

    for tabla, propias, destino in relaciones:
        etiqueta = ", ".join(propias)
        comprobar(
            f"{tabla.calificado} -> {destino}  por {etiqueta}",
            etiqueta in contenido,
            "la relacion existe en el DDL y su etiqueta no esta en el diagrama",
        )

    # ------------------------------------------------------------------ CA-4 - #
    print("\nCA-4, el generador sigue produciendo lo versionado:")

    recien = texto_de(renderizar(dot_entidad_relacion(tablas)))
    palabras_recien = {p for p in re.findall(r"[a-z_][a-z0-9_]{3,}", recien)}
    palabras_disco = {p for p in re.findall(r"[a-z_][a-z0-9_]{3,}", contenido)}
    perdidas = palabras_recien - palabras_disco

    comprobar(
        "lo que el generador produce hoy esta en el SVG versionado",
        not perdidas,
        f"aparecen al regenerar y no estan en disco: {sorted(perdidas)[:12]}. "
        "Hay que correr generar_diagramas.py y versionar el resultado",
    )

    # ------------------------------------------------------------------ CA-5 - #
    #
    # Sin esto, las comprobaciones de arriba podrian estar pasando porque el
    # diagrama contiene todo el diccionario y no porque describa el esquema. Es
    # el modo de fallo de I-06 y se cierra igual: probando que el control sabe
    # decir que no.
    print("\nCA-5, el control distingue una tabla que no esta:")

    inventada = Tabla(esquema="crudo", nombre="tabla_que_no_existe_zzz")
    comprobar(
        "una tabla inventada NO aparece en el diagrama",
        inventada.nombre not in contenido,
        "si aparece, esta comprobacion no esta mirando lo que cree",
    )

    # ------------------------------------------------------------------ CA-6 - #
    #
    # Agregado en H6.5. No reemplaza nada de lo de arriba: los cinco criterios
    # del entidad-relacion quedan como estaban.
    #
    # POR QUE EXISTE
    #
    # Hasta hoy, de los seis diagramas solo el entidad-relacion tenia una maquina
    # que comprobara su contenido. Los otros cinco estaban "declarados en el
    # generador", y el README decia que no se pueden derivar del codigo con
    # honestidad.
    #
    # Esa afirmacion era demasiado ancha. Lo que no se puede derivar son las
    # capas, las flechas y la degradacion de D-23, que son criterio. **Los
    # nombres si**: una ruta de la API esta escrita en `rutas.py`.
    #
    # Y hacia falta: los dos diagramas decian `GET /riesgo`, en singular, y la API
    # expone `/riesgos`. Quien leyera el diagrama y probara esa ruta se comia un
    # 404, con un dibujo que se ve autorizado.
    print("\nCA-6, las rutas que nombran los diagramas existen en la API:")

    fuente_rutas = (RAIZ / "backend" / "api" / "rutas.py").read_text(encoding="utf-8")
    rutas_reales = set(re.findall(r'@router\.(?:get|post|put|delete)\(\s*"([^"]+)"', fuente_rutas))
    comprobar(
        f"rutas.py declara al menos una ruta ({len(rutas_reales)} encontradas)",
        bool(rutas_reales),
        "si esto falla, cambio la forma de declarar rutas y hay que ajustar el patron",
    )

    # Se leen del SVG y no del generador: lo que importa es lo que alguien lee en
    # el dibujo, no lo que el generador pretendia escribir.
    for nombre in ("componentes", "secuencia-consulta-riesgo"):
        if nombre not in svgs:
            continue
        nombradas = set(re.findall(r"(/[a-z][a-z0-9_/-]*)", texto_de(svgs[nombre])))
        # Se ignoran las que no pretenden ser rutas de la API.
        nombradas = {r for r in nombradas if not r.startswith(("/api", "/etc", "/usr", "/docker"))}
        for ruta in sorted(nombradas):
            base = "/" + ruta.strip("/").split("/")[0]
            comprobar(
                f"{nombre}: la ruta {ruta} existe en la API",
                base in rutas_reales or ruta in rutas_reales,
                f"rutas.py expone: {sorted(rutas_reales)}",
            )

    # ------------------------------------------------------------------ CA-7 - #
    #
    # Cada componente dibujado corresponde a un archivo o carpeta que existe, y
    # **en las dos direcciones**:
    #
    #   1. ningun componente declarado apunta a algo que ya se borro
    #   2. ningun componente declarado falta del SVG
    #   3. el control sabe decir que no: un componente inventado se detecta
    #
    # La segunda y la tercera son las que se olvidan. Sin la tercera, esto podria
    # estar pasando por mirar el lugar equivocado; es lo mismo que CA-5 hace por
    # el entidad-relacion.
    print("\nCA-7, cada componente dibujado existe en el repositorio:")

    contenido_comp = texto_de(svgs.get("componentes", ""))
    for ident, (_capa, etiqueta, ruta) in COMPONENTES.items():
        comprobar(
            f"{ident}: {ruta}",
            (RAIZ / ruta).exists(),
            "el diagrama muestra un componente que ya no esta en el repositorio",
        )
        # La etiqueta llega al SVG partida en varios <text>; se busca la ultima
        # linea, que es la mas especifica.
        visible = etiqueta.replace("\\n", "\n").split("\n")[1]
        comprobar(
            f"{ident}: «{visible}» aparece en el diagrama",
            visible in contenido_comp,
            "esta declarado y no se dibujo: hay que regenerar",
        )

    print("\nCA-7b, el control distingue un componente que no existe:")
    comprobar(
        "una ruta inventada NO existe en el repositorio",
        not (RAIZ / "frontend/src/componentes/ComponenteQueNoExisteZzz.jsx").exists(),
        "si existe, esta comprobacion no esta mirando lo que cree",
    )
    comprobar(
        "un nombre inventado NO aparece en el diagrama",
        "ComponenteQueNoExisteZzz" not in contenido_comp,
        "si aparece, esta comprobacion no esta mirando lo que cree",
    )

    if fallos:
        print(f"\n{len(fallos)} comprobaciones fallaron:\n")
        for f in fallos:
            print(f"  - {f}")
        print("\nSe regeneran con:\n")
        print("    python docs/herramientas/generar_diagramas.py\n")
        return 1

    print(f"\nLos {len(ESPERADOS)} diagramas coinciden con el repositorio.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
