"""Genera los diagramas del proyecto. Historias H6.5 y H10.5c.

===========================================================================
POR QUE UN GENERADOR Y NO SEIS ARCHIVOS DIBUJADOS
===========================================================================

Un diagrama dibujado a mano es una **copia** del sistema, y toda copia se
desactualiza. El proyecto ya tuvo esa incidencia dos veces con cifras -I-04 y el
anexo del documento IEEE, donde cinco numeros dejaron de ser ciertos en ocho
dias- y la respuesta fue siempre la misma: una sola fuente, vistas derivadas, y
una maquina que comprueba que coinciden.

Aca se aplica igual, y con una diferencia que importa:

    entidad-relacion    **derivado**. Sale de parsear basedatos/ddl/*.sql.
                        Si alguien agrega una tabla y no regenera, el
                        verificador lo detecta.

    los otros cinco     **declarados aca**. Este archivo ES su fuente, asi que no
                        hay copia que se desactualice porque no hay dos lugares.

**Pero declarado no quiere decir que no se pueda comprobar nada, y hasta H6.5
aqui decia que si.** La frase era «no se pueden derivar del codigo con
honestidad», y era demasiado ancha. Lo que no se deriva son **las capas, las
flechas y la degradacion de D-23**: eso es criterio de quien dibuja.

Los **nombres** si se derivan. Un componente es un archivo, y una ruta de la API
esta escrita en `rutas.py`. Mientras esa distincion no estuvo hecha, los dos
diagramas decian `GET /riesgo` -en singular- contra una API que expone
`/riesgos`, y nadie lo detecto: el dibujo se ve autorizado y no falla.

Por eso `COMPONENTES` declara la ruta real de cada componente y `RUTA_RIESGOS`
se escribe una sola vez. `verificar_diagramas.py` lo comprueba en CA-6 y CA-7.

**Los SVG que quedan en docs/diagramas/ son artefactos.** Se versionan porque
GitHub los renderiza y porque hacen falta para el documento, pero nadie los edita
a mano: se regeneran.

===========================================================================
POR QUE GRAPHVIZ Y NO MERMAID
===========================================================================

Mermaid renderiza en GitHub sin herramientas, que es una ventaja real. Pero
convertirlo a imagen para el documento de Word necesita Chromium, y en el entorno
de construccion no esta disponible.

Se eligio no tener **dos** fuentes -Mermaid para leer, otra cosa para el
documento- porque dos fuentes del mismo diagrama es exactamente el problema que
este archivo existe para evitar. Graphviz produce SVG directo, el SVG es texto
-o sea que se revisa en un Pull Request como cualquier codigo- y de ahi sale el
PNG para el documento.

El diagrama de secuencia se emite como SVG escrito a mano, sin Graphviz: las
lineas de vida de UML no son un grafo dirigido y forzarlas produce algo que se
parece a un diagrama de secuencia sin serlo.

Uso:
    python docs/herramientas/generar_diagramas.py
    python docs/herramientas/generar_diagramas.py --png    (necesita cairosvg)
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DDL = RAIZ / "basedatos" / "ddl"
SALIDA = RAIZ / "docs" / "diagramas"

# Paleta. Sobria a proposito: los diagramas van a un documento academico
# impreso, y un color que no sobreviva a la escala de grises comunica menos que
# ninguno. Todos estos se distinguen en gris.
TINTA = "#1f2328"
SUAVE = "#5b636d"
LINEA = "#b9c0c8"
FONDOS = {
    "geo": "#e8f0e4",
    "crudo": "#e6eef7",
    "analitico": "#f6ecdc",
    "control": "#efe8f4",
    "externo": "#f2f2f4",
    "acento": "#dde7f2",
}

FUENTE = "Helvetica,Arial,sans-serif"


# =========================================================================== #
# 1 · Entidad-relacion, DERIVADO del DDL                                       #
# =========================================================================== #


@dataclass
class Columna:
    nombre: str
    tipo: str
    es_pk: bool = False
    es_fk: bool = False
    obligatoria: bool = False


@dataclass
class Tabla:
    esquema: str
    nombre: str
    columnas: list[Columna] = field(default_factory=list)
    #: (columnas_propias, tabla_destino)
    referencias: list[tuple[list[str], str]] = field(default_factory=list)
    comentario: str = ""

    @property
    def calificado(self) -> str:
        return f"{self.esquema}.{self.nombre}"


def _sin_comentarios(sql: str) -> str:
    return re.sub(r"--[^\n]*", "", sql)


def leer_ddl(carpeta: Path = DDL) -> list[Tabla]:
    """Parsea los CREATE TABLE del DDL. **No se conecta a la base.**

    Es deliberado: el diagrama tiene que poder generarse en la integracion
    continua, donde no hay PostgreSQL cargado, y tiene que describir **lo que el
    repositorio declara**. Si el diagrama saliera de la base viva, describiria el
    estado de una maquina en vez del estado del proyecto, y dos personas con
    bases distintas obtendrian diagramas distintos del mismo commit.
    """
    tablas: list[Tabla] = []

    for archivo in sorted(carpeta.glob("*.sql")):
        sql = _sin_comentarios(archivo.read_text(encoding="utf-8"))

        for encabezado, cuerpo in re.findall(
            r"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+([\w.]+)\s*\((.*?)\n\);",
            sql,
            re.DOTALL | re.IGNORECASE,
        ):
            esquema, _, nombre = encabezado.partition(".")
            tabla = Tabla(esquema=esquema, nombre=nombre or esquema)

            claves_primarias: set[str] = set()
            claves_foraneas: set[str] = set()

            for linea in _partir_en_definiciones(cuerpo):
                pk = re.search(r"PRIMARY KEY\s*\(([^)]*)\)", linea, re.IGNORECASE)
                if pk:
                    claves_primarias |= {c.strip() for c in pk.group(1).split(",")}
                    continue

                fk = re.search(
                    r"FOREIGN KEY\s*\(([^)]*)\)\s*REFERENCES\s+([\w.]+)",
                    linea,
                    re.IGNORECASE | re.DOTALL,
                )
                if fk:
                    propias = [c.strip() for c in fk.group(1).split(",")]
                    claves_foraneas |= set(propias)
                    tabla.referencias.append((propias, fk.group(2)))
                    continue

                if re.match(r"CONSTRAINT\b", linea, re.IGNORECASE):
                    continue

                columna = re.match(r"([a-z_][a-z0-9_]*)\s+(.+)", linea, re.IGNORECASE)
                if not columna:
                    continue
                tipo = re.split(r"\s+(?:NOT NULL|NULL|DEFAULT|CONSTRAINT)\b", columna.group(2))[0]
                tabla.columnas.append(
                    Columna(
                        nombre=columna.group(1),
                        tipo=tipo.strip().rstrip(","),
                        obligatoria="NOT NULL" in linea.upper(),
                    )
                )

            for c in tabla.columnas:
                c.es_pk = c.nombre in claves_primarias
                c.es_fk = c.nombre in claves_foraneas

            comentario = re.search(
                rf"COMMENT ON TABLE {re.escape(encabezado)} IS\s*'((?:[^']|'')*)'",
                sql,
                re.IGNORECASE,
            )
            if comentario:
                tabla.comentario = comentario.group(1).replace("''", "'")

            tablas.append(tabla)

    return tablas


def _partir_en_definiciones(cuerpo: str) -> list[str]:
    """Parte por comas de primer nivel, respetando los parentesis de los CHECK."""
    partes, actual, profundidad = [], [], 0
    for caracter in cuerpo:
        if caracter == "(":
            profundidad += 1
        elif caracter == ")":
            profundidad -= 1
        if caracter == "," and profundidad == 0:
            partes.append("".join(actual).strip())
            actual = []
            continue
        actual.append(caracter)
    if "".join(actual).strip():
        partes.append("".join(actual).strip())
    return [" ".join(p.split()) for p in partes if p.strip()]


def _escapar(texto: str) -> str:
    return (
        texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def dot_entidad_relacion(tablas: list[Tabla]) -> str:
    lineas = [
        "digraph entidad_relacion {",
        # `splines=ortho` no sabe colocar etiquetas de arista, y las de aca dicen
        # por que columna se relaciona cada par de tablas, que es justo lo que un
        # entidad-relacion tiene que comunicar. Se prefiere la curva.
        '  graph [rankdir=LR, splines=spline, nodesep=0.6, ranksep=1.2, bgcolor="white",',
        f'         fontname="{FUENTE}", fontsize=11, pad=0.3];',
        f'  node  [shape=plaintext, fontname="{FUENTE}", fontsize=10];',
        f'  edge  [color="{SUAVE}", arrowsize=0.7, penwidth=1.1];',
    ]

    por_esquema: dict[str, list[Tabla]] = {}
    for t in tablas:
        por_esquema.setdefault(t.esquema, []).append(t)

    for indice, (esquema, grupo) in enumerate(sorted(por_esquema.items())):
        fondo = FONDOS.get(esquema, FONDOS["externo"])
        lineas += [
            f"  subgraph cluster_{indice} {{",
            f'    label="esquema {esquema}"; labeljust="l"; fontsize=12; '
            f'color="{LINEA}"; style="rounded"; bgcolor="{fondo}";',
        ]
        for tabla in grupo:
            lineas.append(f'    "{tabla.calificado}" [label=<{_html_tabla(tabla)}>];')
        lineas.append("  }")

    for tabla in tablas:
        for propias, destino in tabla.referencias:
            etiqueta = ", ".join(propias)
            # Pata de gallo del lado de la tabla que referencia -muchos- y barra
            # del lado referenciado -uno-. Con `dir=both` se dibujan las dos
            # puntas; la primera version usaba `dir=back`, que suprime la de
            # adelante, y el diagrama salio sin ninguna marca de cardinalidad.
            lineas.append(
                f'  "{destino}" -> "{tabla.calificado}" '
                f'[label=" {_escapar(etiqueta)} ", fontsize=8, fontcolor="{SUAVE}", '
                f"dir=both, arrowtail=tee, arrowhead=crow];"
            )

    lineas.append("}")
    return "\n".join(lineas)


def _html_tabla(tabla: Tabla) -> str:
    filas = [
        f'<TR><TD BGCOLOR="white" COLSPAN="3" ALIGN="LEFT">'
        f"<B>{_escapar(tabla.nombre)}</B></TD></TR>"
    ]
    for c in tabla.columnas:
        # Un <FONT> vacio es un error de sintaxis para Graphviz, no una celda en
        # blanco. El espacio duro es lo que la deja vacia sin romper el parser.
        marca = "PK" if c.es_pk else ("FK" if c.es_fk else "&nbsp;")
        nombre = f"<B>{_escapar(c.nombre)}</B>" if c.es_pk else _escapar(c.nombre)
        if c.obligatoria and not c.es_pk:
            nombre = f"{nombre}*"
        # El tipo va en su propia celda y no pegado al nombre: con nombres largos
        # -humedad_relativa_pct, radiacion_mj_m2- el texto se encimaba.
        filas.append(
            f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="9">{marca}</FONT></TD>'
            f'<TD ALIGN="LEFT">{nombre}</TD>'
            f'<TD ALIGN="LEFT"><FONT COLOR="{SUAVE}" POINT-SIZE="8">'
            f"{_escapar(c.tipo)}</FONT></TD></TR>"
        )
    return (
        '<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="3" '
        f'BGCOLOR="white" COLOR="{LINEA}">' + "".join(filas) + "</TABLE>"
    )


# =========================================================================== #
# 2 · Los cinco diagramas declarados                                           #
# =========================================================================== #
#
# Este archivo es su fuente. No hay copia en otro lado que pueda desactualizarse.


def dot_flujo_datos() -> str:
    return f"""digraph flujo_datos {{
  graph [rankdir=LR, splines=ortho, nodesep=0.45, ranksep=0.9, bgcolor="white",
         fontname="{FUENTE}", pad=0.3];
  node  [shape=box, style="rounded,filled", fontname="{FUENTE}", fontsize=10,
         color="{LINEA}", fontcolor="{TINTA}", margin="0.18,0.10"];
  edge  [color="{SUAVE}", arrowsize=0.7, fontname="{FUENTE}", fontsize=8,
         fontcolor="{SUAVE}"];

  subgraph cluster_fuentes {{
    label="Fuentes abiertas  ·  D-01, D-15"; labeljust="l"; fontsize=11;
    color="{LINEA}"; style="rounded"; bgcolor="{FONDOS["externo"]}";
    chirps [label="CHIRPS 2.0\\nvia ClimateSERV\\n0,05°  ·  precipitacion",
            fillcolor="white"];
    power  [label="NASA POWER\\n0,5 x 0,625°  ·  temperatura,\\nhumedad, viento, radiacion",
            fillcolor="white"];
    firms  [label="NASA FIRMS\\nMODIS C6.1  ·  focos\\ndesde 2001",
            fillcolor="white"];
    snit   [label="SNIT / IGN\\nlimite distrital 5k\\nEPSG:4326", fillcolor="white"];
  }}

  etl [label="ETL\\nbackend/etl", fillcolor="{FONDOS["acento"]}"];

  subgraph cluster_base {{
    label="PostgreSQL 16 + PostGIS 3.4"; labeljust="l"; fontsize=11;
    color="{LINEA}"; style="rounded"; bgcolor="{FONDOS["crudo"]}";
    geo      [label="geo\\nprovincia, canton,\\ndistrito", fillcolor="{FONDOS["geo"]}"];
    crudo    [label="crudo\\nmedicion_diaria,\\nfoco_calor", fillcolor="white"];
    analitico [label="analitico\\nriesgo\\n(sin duenio)",
               fillcolor="{FONDOS["analitico"]}", style="rounded,filled,dashed"];
  }}

  subgraph cluster_modelo {{
    label="Modelado  ·  epica E3"; labeljust="l"; fontsize=11;
    color="{LINEA}"; style="rounded"; bgcolor="{FONDOS["control"]}";
    etiquetas [label="Etiquetado\\nH3.0\\n99 296 filas", fillcolor="white"];
    modelo    [label="Estimadores\\nH3.1 lineas base\\nH3.3-H3.5 pendientes",
               fillcolor="white"];
  }}

  api   [label="API REST\\nFastAPI  ·  OpenAPI\\nH6.1", fillcolor="{FONDOS["acento"]}"];
  visor [label="Visor\\nReact + Leaflet\\nGitHub Pages", fillcolor="{FONDOS["acento"]}"];
  respaldo [label="Respaldo estatico\\nJSON simulado\\nD-23", fillcolor="white",
            style="rounded,filled,dashed"];

  chirps -> etl [label="precipitacion"];
  power  -> etl;
  firms  -> etl;
  snit   -> etl [label="geometrias"];

  etl -> geo;
  etl -> crudo;
  crudo -> etiquetas;
  geo   -> etiquetas;
  etiquetas -> modelo;
  modelo -> analitico [style=dashed, label="pendiente"];
  analitico -> api [style=dashed];
  api -> visor [label="/riesgo"];
  respaldo -> visor [style=dashed, label="si /api falla"];
}}"""


# --------------------------------------------------------------------------- #
# Lo que el diagrama de componentes AFIRMA, y que se puede comprobar             #
# --------------------------------------------------------------------------- #
#
# Cada componente dibujado, con el archivo o la carpeta que representa.
#
# LA RUTA NO ES DECORATIVA. `verificar_diagramas.py` comprueba que exista, y en
# las dos direcciones: que ningun componente dibujado apunte a algo que ya no
# esta, y que ningun nombre aparezca en el SVG sin estar declarado aca.
#
# POR QUE SE AGREGO, EN H6.5
#
# El README de esta carpeta decia que estos cinco diagramas no se pueden derivar
# del codigo «con honestidad», y por eso no tenian ninguna comprobacion de
# contenido. La afirmacion era demasiado ancha: lo que no se puede derivar son
# **las capas, las flechas y la degradacion de D-23**, que son criterio. Los
# **nombres** si: un componente es un archivo y una ruta de la API esta en
# `rutas.py`.
#
# Se descubrio porque el diagrama decia `GET /riesgo` y la API expone `/riesgos`.
# Quien leyera ese diagrama y probara la ruta se comia un 404, y el dibujo se ve
# autorizado. Es el mismo modo de fallo que I-04 y que las cifras del anexo del
# documento IEEE: una copia que se desactualiza sin que nadie se entere.
#
# La capa de presentacion, ademas, se habia quedado en agosto: mostraba solo el
# mapa, sin el semaforo de H7.1 ni la ficha con coordenadas de H5.6.
COMPONENTES: dict[str, tuple[str, str, str]] = {
    # id          capa            etiqueta                                                    ruta real
    "visor": ("pres", "«componente»\\nVisor React", "frontend/src/App.jsx"),
    "mapa": ("pres", "«componente»\\nMapaCanton\\nLeaflet", "frontend/src/componentes/MapaCanton.jsx"),
    "semaforo": ("pres", "«componente»\\nTableroSemaforo\\ntres eventos  ·  H7.1", "frontend/src/componentes/TableroSemaforo.jsx"),
    "ficha": ("pres", "«componente»\\nPanelDistrito\\ncoordenadas  ·  H5.6", "frontend/src/componentes/PanelDistrito.jsx"),
    "cliente": ("pres", "«componente»\\nCliente de datos\\nnegocia origen  ·  D-23", "frontend/src/datos/cliente.js"),
    "api": ("serv", "«componente»\\nAPI FastAPI\\nOpenAPI  ·  H6.1", "backend/api/rutas.py"),
    "repositorio": ("serv", "«componente»\\nRepositorio\\npatron Repository  ·  H6.2", "contratos/repositorio.py"),
    "contratos": ("dom", "«componente»\\nContratos\\nProtocol congelados  ·  D-06", "contratos"),
    "modelado": ("dom", "«componente»\\nModelado\\netiquetado, particion,\\ncomparacion", "backend/modelado"),
    "etl": ("datos", "«componente»\\nETL", "backend/etl"),
}

# La ruta de la API que los dos diagramas nombran. Se escribe una sola vez para
# que no puedan discrepar entre ellos: antes de H6.5 los dos decian `/riesgo`, en
# singular, y ninguno de los dos existia.
RUTA_RIESGOS = "/riesgos"


def _nodos_de_capa(capa: str) -> str:
    """Los nodos de una capa, tal como los escribe Graphviz."""
    return "\n".join(
        f'    {ident} [label="{etiqueta}", fillcolor="white"];'
        for ident, (suya, etiqueta, _) in COMPONENTES.items()
        if suya == capa
    )


def dot_componentes() -> str:
    return f"""digraph componentes {{
  graph [rankdir=TB, splines=ortho, nodesep=0.5, ranksep=0.8, bgcolor="white",
         fontname="{FUENTE}", pad=0.3];
  node  [shape=box, style="filled", fontname="{FUENTE}", fontsize=10,
         color="{LINEA}", fontcolor="{TINTA}", margin="0.2,0.12"];
  edge  [color="{SUAVE}", arrowsize=0.7, fontname="{FUENTE}", fontsize=8,
         fontcolor="{SUAVE}"];

  subgraph cluster_pres {{
    label="Presentacion"; labeljust="l"; fontsize=11; color="{LINEA}";
    style="rounded"; bgcolor="{FONDOS["acento"]}";
{_nodos_de_capa("pres")}
  }}

  subgraph cluster_serv {{
    label="Servicio"; labeljust="l"; fontsize=11; color="{LINEA}";
    style="rounded"; bgcolor="{FONDOS["crudo"]}";
{_nodos_de_capa("serv")}
  }}

  subgraph cluster_dom {{
    label="Dominio"; labeljust="l"; fontsize=11; color="{LINEA}";
    style="rounded"; bgcolor="{FONDOS["control"]}";
{_nodos_de_capa("dom")}
  }}

  subgraph cluster_datos {{
    label="Datos"; labeljust="l"; fontsize=11; color="{LINEA}";
    style="rounded"; bgcolor="{FONDOS["geo"]}";
{_nodos_de_capa("datos")}
    base [label="«base de datos»\\nPostgreSQL + PostGIS", shape=cylinder,
          fillcolor="white"];
  }}

  visor -> mapa     [arrowhead=none];
  visor -> semaforo [arrowhead=none];
  visor -> ficha    [arrowhead=none];
  visor -> cliente  [arrowhead=none];
  cliente -> api    [label="HTTP  ·  {RUTA_RIESGOS}", style=dashed];
  api -> repositorio;
  repositorio -> base;
  modelado -> base;
  etl -> base;

  // Dependencias de uso. **Sin la etiqueta «usa», y no es un olvido.**
  //
  // Con `splines=ortho`, Graphviz coloca mal las etiquetas de las aristas que
  // cruzan un cluster: dos de las tres quedaban flotando en el borde derecho del
  // lienzo, sin ninguna linea que las uniera a nada. Se ve en el diagrama
  // publicado hasta H6.5.
  //
  // La flecha punteada **ya significa dependencia** en UML, asi que la palabra
  // no aportaba nada y el defecto se lleva por delante. La alternativa era sacar
  // `ortho`, que reordena el diagrama entero por una palabra redundante.
  api -> contratos      [style=dashed];
  modelado -> contratos [style=dashed];
  etl -> contratos      [style=dashed];
}}"""


def dot_despliegue() -> str:
    return f"""digraph despliegue {{
  graph [rankdir=TB, splines=ortho, nodesep=0.5, ranksep=0.85, bgcolor="white",
         fontname="{FUENTE}", pad=0.3];
  node  [shape=box, style="rounded,filled", fontname="{FUENTE}", fontsize=10,
         color="{LINEA}", fontcolor="{TINTA}", margin="0.18,0.11"];
  edge  [color="{SUAVE}", arrowsize=0.7, fontname="{FUENTE}", fontsize=8,
         fontcolor="{SUAVE}"];

  subgraph cluster_dev {{
    label="Maquina de desarrollo"; labeljust="l"; fontsize=11; color="{LINEA}";
    style="rounded"; bgcolor="{FONDOS["externo"]}";
    compose [label="docker compose\\nH6.0", fillcolor="white"];
    k3d     [label="k3d  ·  Kubernetes local\\nH8.6  ·  D-05", fillcolor="white"];
  }}

  subgraph cluster_ci {{
    label="GitHub Actions  ·  6 trabajos"; labeljust="l"; fontsize=11;
    color="{LINEA}"; style="rounded"; bgcolor="{FONDOS["acento"]}";
    ci       [label="CI\\ncontratos, gestion, calidad,\\nfrontend, pruebas",
              fillcolor="white"];
    publicar [label="publicar-visor\\nsolo desde main  ·  H11.5", fillcolor="white"];
    ghcr     [label="ghcr.io\\nimagenes  ·  H11.1\\n(pendiente)", fillcolor="white",
              style="rounded,filled,dashed"];
  }}

  subgraph cluster_prod {{
    label="Publicado"; labeljust="l"; fontsize=11; color="{LINEA}";
    style="rounded"; bgcolor="{FONDOS["geo"]}";
    pages [label="GitHub Pages\\nvisor estatico\\ncon respaldo JSON", fillcolor="white"];
    apiprod [label="API en linea\\nSIN DESPLEGAR\\nver la limitacion", fillcolor="white",
             style="rounded,filled,dashed"];
    baseprod [label="Base en linea\\nSIN DESPLEGAR", shape=cylinder, fillcolor="white",
              style="filled,dashed"];
  }}

  compose -> ci [style=dashed, label="mismo Dockerfile"];
  k3d -> ci [style=invis];
  ci -> publicar [label="si main"];
  ci -> ghcr [style=dashed];
  publicar -> pages;
  pages -> apiprod [style=dashed, label="/api  ·  404 hoy"];
  apiprod -> baseprod [style=dashed];
}}"""


def dot_flujo_modelado() -> str:
    return f"""digraph flujo_modelado {{
  graph [rankdir=LR, splines=ortho, nodesep=0.4, ranksep=0.75, bgcolor="white",
         fontname="{FUENTE}", pad=0.3];
  node  [shape=box, style="rounded,filled", fontname="{FUENTE}", fontsize=10,
         color="{LINEA}", fontcolor="{TINTA}", margin="0.18,0.11", fillcolor="white"];
  edge  [color="{SUAVE}", arrowsize=0.7, fontname="{FUENTE}", fontsize=8,
         fontcolor="{SUAVE}"];

  series [label="Series diarias\\n1991-2025\\ncrudo.medicion_diaria",
          fillcolor="{FONDOS["crudo"]}"];
  focos  [label="Focos de calor\\n2001-2024\\ncrudo.foco_calor",
          fillcolor="{FONDOS["crudo"]}"];

  etiquetado [label="H3.0  Etiquetado\\nSPI-3 por mes  ·  D-19\\nP95/P99 de 72 h\\nfocos en (t, t+7]",
              fillcolor="{FONDOS["control"]}"];
  particion  [label="H3.2  Particion\\nventana expansiva  ·  D-04\\n5 pliegues\\nembargo de 7 dias",
              fillcolor="{FONDOS["control"]}"];

  subgraph cluster_est {{
    label="Estimadores  ·  contrato de H3.6"; labeljust="l"; fontsize=11;
    color="{LINEA}"; style="rounded"; bgcolor="{FONDOS["analitico"]}";
    trivial [label="Linea base trivial\\nH3.1"];
    clima   [label="Linea base climatologica\\nrealce  ·  H3.1"];
    algos   [label="Regresion Logistica\\nRandom Forest\\nXGBoost\\nH3.3-H3.5  PENDIENTES",
             style="rounded,filled,dashed"];
  }}

  tabla [label="H3.6  Tabla comparativa\\nF1-macro  ·  D-10\\nsin ganador si la ventaja\\nes menor que la dispersion",
         fillcolor="{FONDOS["acento"]}"];

  series -> etiquetado;
  focos  -> etiquetado [label="I-11: nada antes de 2001"];
  etiquetado -> particion;
  particion -> trivial;
  particion -> clima;
  particion -> algos [style=dashed];
  trivial -> tabla;
  clima   -> tabla;
  algos   -> tabla [style=dashed];
}}"""


# =========================================================================== #
# 3 · Secuencia, en SVG escrito a mano                                         #
# =========================================================================== #


def svg_secuencia() -> str:
    """Consulta de riesgo desde el visor, con la degradacion de D-23.

    Se escribe a mano y no con Graphviz porque una linea de vida no es una
    arista: forzarla produce algo que se parece a un diagrama de secuencia sin
    respetar su semantica, y en un documento academico eso se nota.
    """
    actores = [
        ("Persona", 90),
        ("Visor React", 265),
        ("Cliente de datos", 460),
        ("API FastAPI", 655),
        ("PostgreSQL\n+ PostGIS", 850),
    ]
    mensajes = [
        (0, 1, "selecciona evento y fecha", False),
        (1, 2, "obtenerRiesgos(evento, fecha)", False),
        (2, 3, f"GET {RUTA_RIESGOS}?evento=&fecha=", False),
        (3, 4, "SELECT por distrito", False),
        (4, 3, "filas", True),
        (3, 2, "200  ·  JSON del contrato", True),
        (2, 1, "paquete de riesgos", True),
        (1, 0, "mapa coloreado + semaforo", True),
    ]
    alterno = [
        (2, 2, "si /api no responde: respaldo estatico  ·  D-23", False),
        (2, 1, "paquete, con modo = simulado", True),
    ]

    alto_cabeza = 62
    # 132 y no 110: con 110 la cabecera de los actores pisaba el subtitulo. Se
    # midio sobre el PNG renderizado, no se estimo.
    y0 = 132
    paso = 46
    ancho = 980

    # El alto sale de donde termina el ultimo elemento, no de una formula
    # aproximada: la primera version dejaba un tercio de lienzo en blanco abajo.
    inicio_alt = y0 + 26 + (len(mensajes) - 0.4) * paso
    fin_alt = y0 + 26 + (len(mensajes) + len(alterno) + 0.05) * paso
    alto = int(fin_alt + 34)

    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho} {alto}" '
        f'width="{ancho}" height="{alto}" font-family="{FUENTE}">',
        f'<rect width="{ancho}" height="{alto}" fill="white"/>',
        '<defs><marker id="f" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{SUAVE}"/>'
        "</marker></defs>",
        f'<text x="24" y="34" font-size="15" font-weight="600" fill="{TINTA}">'
        "Consulta de riesgo por distrito</text>",
        f'<text x="24" y="52" font-size="11" fill="{SUAVE}">'
        "Flujo principal y degradacion al respaldo estatico (D-23)</text>",
    ]

    for nombre, x in actores:
        renglones = nombre.split("\n")
        h = alto_cabeza if len(renglones) == 1 else alto_cabeza + 12
        partes.append(
            f'<rect x="{x - 78}" y="{y0 - h}" width="156" height="{h - 12}" rx="6" '
            f'fill="{FONDOS["acento"]}" stroke="{LINEA}"/>'
        )
        for i, renglon in enumerate(renglones):
            partes.append(
                f'<text x="{x}" y="{y0 - h + 24 + i * 14}" font-size="11" '
                f'text-anchor="middle" fill="{TINTA}">{_escapar(renglon)}</text>'
            )
        partes.append(
            f'<line x1="{x}" y1="{y0 - 8}" x2="{x}" y2="{alto - 16}" '
            f'stroke="{LINEA}" stroke-dasharray="4 4"/>'
        )

    def flecha(indice: int, origen: int, destino: int, texto: str, respuesta: bool) -> None:
        y = y0 + 26 + indice * paso
        x1, x2 = actores[origen][1], actores[destino][1]
        guion = ' stroke-dasharray="6 4"' if respuesta else ""
        if origen == destino:
            partes.append(
                f'<path d="M{x1},{y} h56 v22 h-56" fill="none" stroke="{SUAVE}"{guion} '
                'marker-end="url(#f)"/>'
            )
            partes.append(
                f'<text x="{x1 + 66}" y="{y + 4}" font-size="10" fill="{SUAVE}">'
                f"{_escapar(texto)}</text>"
            )
            return
        partes.append(
            f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{SUAVE}"{guion} '
            'marker-end="url(#f)"/>'
        )
        partes.append(
            f'<text x="{(x1 + x2) / 2}" y="{y - 7}" font-size="10" text-anchor="middle" '
            f'fill="{TINTA}">{_escapar(texto)}</text>'
        )

    for i, (o, d, t, r) in enumerate(mensajes):
        flecha(i, o, d, t, r)

    partes.append(
        f'<rect x="52" y="{inicio_alt}" width="{ancho - 104}" '
        f'height="{fin_alt - inicio_alt}" rx="4" '
        f'fill="none" stroke="{LINEA}" stroke-dasharray="5 4"/>'
    )
    partes.append(
        f'<rect x="52" y="{inicio_alt}" width="52" height="17" '
        f'fill="{FONDOS["externo"]}" stroke="{LINEA}"/>'
    )
    partes.append(f'<text x="60" y="{inicio_alt + 12}" font-size="10" fill="{TINTA}">alt</text>')
    for i, (o, d, t, r) in enumerate(alterno):
        flecha(len(mensajes) + i + 0.3, o, d, t, r)

    partes.append("</svg>")
    return "\n".join(partes)


# =========================================================================== #
# Emision                                                                      #
# =========================================================================== #

DECLARADOS = {
    "flujo-datos": dot_flujo_datos,
    "componentes": dot_componentes,
    "despliegue": dot_despliegue,
    "flujo-modelado": dot_flujo_modelado,
}


def renderizar(dot: str) -> str:
    if not shutil.which("dot"):
        raise RuntimeError(
            "Falta Graphviz. En Windows: winget install Graphviz.Graphviz\n"
            "En Debian/Ubuntu: sudo apt install graphviz"
        )
    proceso = subprocess.run(
        ["dot", "-Tsvg"], input=dot, capture_output=True, text=True, check=False
    )
    if proceso.returncode != 0:
        raise RuntimeError(f"dot fallo:\n{proceso.stderr}")
    # `dot` escribe una cabecera XML y un comentario con su version. La version
    # cambia entre maquinas y haria que el verificador reportara diferencias que
    # no son del diagrama, asi que se recorta desde <svg.
    return proceso.stdout[proceso.stdout.index("<svg") :]


def generar() -> dict[str, str]:
    """Nombre -> contenido SVG. Todo lo que este archivo produce, en un lugar."""
    salida = {"entidad-relacion": renderizar(dot_entidad_relacion(leer_ddl()))}
    for nombre, fabrica in DECLARADOS.items():
        salida[nombre] = renderizar(fabrica())
    salida["secuencia-consulta-riesgo"] = svg_secuencia()
    return salida


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--png", action="store_true", help="ademas del SVG, para el documento")
    p.add_argument("--salida", type=Path, default=SALIDA)
    args = p.parse_args()

    args.salida.mkdir(parents=True, exist_ok=True)

    tablas = leer_ddl()
    print("\nDiagramas de GeoGuardian\n")
    print(f"  tablas leidas del DDL: {len(tablas)}")
    for t in tablas:
        print(
            f"    {t.calificado:28} {len(t.columnas)} columnas, "
            f"{len(t.referencias)} referencia(s)"
        )
    print()

    for nombre, contenido in generar().items():
        destino = args.salida / f"{nombre}.svg"
        destino.write_text(contenido, encoding="utf-8")
        print(f"  {destino.relative_to(RAIZ)}")

        if args.png:
            try:
                import cairosvg
            except ImportError:
                print("        (sin PNG: falta cairosvg. pip install cairosvg)")
                continue
            cairosvg.svg2png(
                bytestring=contenido.encode("utf-8"),
                write_to=str(args.salida / f"{nombre}.png"),
                scale=2,
            )
            print(f"  {(args.salida / f'{nombre}.png').relative_to(RAIZ)}")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
