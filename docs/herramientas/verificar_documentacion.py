"""Comprueba que las cifras afirmadas en la documentacion sigan siendo ciertas.

POR QUE EXISTE

Este verificador nace de la accion 12.2 de la retrospectiva, y esa accion nace de
cinco defectos encontrados en dos dias, todos del mismo tipo: un numero escrito
una vez en la documentacion y nunca vuelto a comprobar.

    docs/02-contratos.md      decia 28 comprobaciones     eran 31
    docs/ARRANQUE.md          decia 17 verificaciones      eran 31
    README.md                 decia 17 verificaciones      eran 31
    docs/ARRANQUE.md          daba usuarios geo_etl/geo_api  el acuerdo es otro
    docs/03-bitacora-...      decia 492 entidades del SNIT  son 494

Ninguno tuvo consecuencia tecnica. Pero es exactamente el defecto que produjo la
incidencia I-04 —un dato con forma valida y contenido falso— y el que inflo el
avance reportado en un documento ya entregado. Contar a mano fallo cinco veces;
lo que corresponde no es tener mas cuidado, es que lo cuente una maquina.

QUE HACE

Para cada afirmacion numerica registrada abajo: calcula el valor real desde el
repositorio, lo busca en los archivos que lo declaran, y compara.

Falla con codigo 1 si alguno no coincide, para poder correrlo en CI.

QUE NO HACE

No corrige nada. Informa donde esta la discrepancia y con que valor, porque
decidir cual de los dos numeros es el correcto no siempre es obvio: a veces el
codigo cambio y la documentacion tiene razon.

COMO SE AGREGA UNA AFIRMACION

Una entrada en AFIRMACIONES con: nombre, funcion que calcula el valor real, y la
lista de (archivo, expresion regular con un grupo numerico).

Uso:
    python docs/herramientas/verificar_documentacion.py
"""

from __future__ import annotations

import csv
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

# Las lineas de tarea reales empiezan en columna cero. El bloque de instrucciones
# que llevan los cuatro archivos de tareas incluye un ejemplo indentado, marcado
# [x] a proposito para mostrar como se marca. Ese ejemplo NO es una historia
# cerrada, y contarlo fue uno de los cinco defectos que originaron esta
# herramienta.
PATRON_HISTORIA_CERRADA = re.compile(r"^- \[x\] \*\*(H[0-9.]+[a-z]?)\*\*", re.M)

PERSONAS = ("alejandro", "cesar", "luna", "avril")


# --------------------------------------------------------------------------- #
# Calculo de los valores reales                                                 #
# --------------------------------------------------------------------------- #


def comprobaciones_de_contratos() -> int:
    """Cuenta las comprobaciones que ejecuta contratos.verificar, corriendolo."""
    resultado = subprocess.run(
        [sys.executable, "-m", "contratos.verificar"],
        cwd=RAIZ,
        capture_output=True,
        text=True,
    )
    return len(re.findall(r"^  (?:OK  |FALLO)", resultado.stdout, re.M))


def version_de_contratos() -> str:
    texto = (RAIZ / "contratos" / "__init__.py").read_text(encoding="utf-8")
    encontrado = re.search(r'VERSION_CONTRATOS\s*=\s*"([^"]+)"', texto)
    return encontrado.group(1) if encontrado else "?"


def historias_del_backlog() -> int:
    with (RAIZ / "docs" / "backlog.csv").open(encoding="utf-8-sig") as archivo:
        return sum(1 for _ in csv.DictReader(archivo))


def puntos_del_backlog() -> int:
    with (RAIZ / "docs" / "backlog.csv").open(encoding="utf-8-sig") as archivo:
        return sum(int(f["puntos"]) for f in csv.DictReader(archivo))


def horas_del_backlog() -> str:
    """Total de horas con un decimal, que es como lo escriben los documentos."""
    with (RAIZ / "docs" / "backlog.csv").open(encoding="utf-8-sig") as archivo:
        return f"{sum(float(f['horas']) for f in csv.DictReader(archivo)):.1f}"


def horas_del_sprint(sprint: str) -> str:
    """Horas comprometidas en un sprint, con un decimal."""
    with (RAIZ / "docs" / "backlog.csv").open(encoding="utf-8-sig") as archivo:
        total = sum(float(f["horas"]) for f in csv.DictReader(archivo) if f["sprint"] == sprint)
    return f"{total:.1f}"


def historias_del_sprint(sprint: str) -> int:
    with (RAIZ / "docs" / "backlog.csv").open(encoding="utf-8-sig") as archivo:
        return sum(1 for f in csv.DictReader(archivo) if f["sprint"] == sprint)


def registros_adr() -> int:
    texto = (RAIZ / "docs" / "03-bitacora-decisiones.md").read_text(encoding="utf-8")
    return len(re.findall(r"^## D-\d+", texto, re.M))


def incidencias() -> int:
    texto = (RAIZ / "docs" / "04-bitacora-incidencias.md").read_text(encoding="utf-8")
    # I-00 es la plantilla, no una incidencia.
    return len([i for i in re.findall(r"^## (I-\d+)", texto, re.M) if i != "I-00"])


def trabajos_de_ci() -> int:
    """
    Cuenta los trabajos del pipeline.

    Se recorre solo el bloque que sigue a `jobs:` y se para al volver a la
    columna cero. Contar todas las claves con dos espacios de sangria daria 7:
    incluiria `push:` y `pull_request:`, que cuelgan de `on:` y no son trabajos.
    Ese error estuvo en la primera version de esta herramienta.
    """
    texto = (RAIZ / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    trabajos = 0
    dentro = False

    for linea in texto.splitlines():
        if linea.startswith("jobs:"):
            dentro = True
            continue
        if not dentro:
            continue
        if linea.strip() and not linea.startswith(" "):
            break  # se acabo el bloque de trabajos
        # `publicar-visor`, de H11.5, lleva GUION. Con `[a-z_]+` no calzaba y
        # esta herramienta contaba 5 trabajos cuando ya eran 6, sin avisar de
        # nada: el manual decia "cinco" y la comprobacion le daba la razon.
        if re.fullmatch(r"  [a-z][a-z0-9_-]*:", linea):
            trabajos += 1

    return trabajos


def historias_cerradas() -> int:
    """Historias efectivamente marcadas, sin contar el ejemplo de la plantilla."""
    total = 0
    for persona in PERSONAS:
        texto = (RAIZ / "docs" / "tareas" / f"{persona}.md").read_text(encoding="utf-8")
        total += len(PATRON_HISTORIA_CERRADA.findall(texto))
    return total


# --------------------------------------------------------------------------- #
# Registro de afirmaciones                                                      #
# --------------------------------------------------------------------------- #


@dataclass
class Afirmacion:
    nombre: str
    real: Callable[[], object]
    apariciones: list[tuple[str, str]] = field(default_factory=list)


AFIRMACIONES = [
    Afirmacion(
        "comprobaciones de contratos.verificar",
        comprobaciones_de_contratos,
        [
            ("README.md", r"(\d+) verificaciones en `python -m contratos\.verificar`"),
            ("docs/ARRANQUE.md", r"pasar las \*\*(\d+) verificaciones\*\*"),
            ("docs/02-contratos.md", r"ejecuta \*\*(\d+) comprobaciones\*\*"),
            ("docs/10-manual-tecnico.md", r"con \*\*(\d+) comprobaciones\*\*"),
            ("docs/10-manual-tecnico.md", r"simulados y (\d+) comprobaciones automáticas"),
            # La hoja de verificacion de la seccion 10 lleva la cifra en la
            # columna de observaciones. Se agrego el 20 de agosto: decia 31
            # cuando ya eran 36, y ninguno de los dos patrones de arriba la
            # alcanzaba. Es la hoja que va a llenar una persona de OTRO equipo:
            # una cifra vieja ahi la haria anotar un fallo que no existe.
            ("docs/10-manual-tecnico.md", r"\| Contratos \| 5\.2 \| \| (\d+) comprobaciones \|"),
        ],
    ),
    Afirmacion(
        "version de contratos",
        version_de_contratos,
        [
            ("README.md", r"Contratos \| v([\d.]+), congelados"),
            ("docs/ARRANQUE.md", r'"Contratos version ([\d.]+)"'),
            ("docs/02-contratos.md", r"Version de contratos: \*\*([\d.]+)\*\*"),
            # El manual afirma la version en su seccion 5.2, y NADIE la
            # comprobaba: el verificador miraba el numero de comprobaciones y no
            # la version. Se quedo en 1.2.0 mientras los contratos iban por
            # 1.3.2, tres cambios de version despues. Lo detecto Cesar
            # verificando el manual, y su diagnostico es el que importa: "un
            # verificador que no mira ese dato deja que envejezca en silencio".
            ("docs/10-manual-tecnico.md", r'declarar \*\*"Contratos version ([\d.]+)"\*\*'),
        ],
    ),
    # Los tres inventarios del backlog se comprueban en los tres documentos que
    # los declaran. La auditoria del 18 de agosto encontro que `08-backlog.md` y
    # `tareas/README.md` seguian en 83 historias y 417 puntos, y que la tabla de
    # `tareas/README.md` tenia ademas mal el reparto de Avril entre S1 y S2,
    # desde que H1.6 se adelanto de sprint. Ninguno de los dos estaba cubierto.
    Afirmacion(
        "historias del backlog",
        historias_del_backlog,
        [
            ("README.md", r"Backlog \| (\d+) historias"),
            ("docs/08-backlog.md", r"\*\*(\d+) historias · "),
            ("docs/tareas/README.md", r"\*\*(\d+) historias · "),
        ],
    ),
    Afirmacion(
        "puntos del backlog",
        puntos_del_backlog,
        [
            ("README.md", r"historias, (\d+) puntos"),
            ("docs/08-backlog.md", r"historias · (\d+) puntos"),
            ("docs/tareas/README.md", r"historias · (\d+) puntos"),
        ],
    ),
    Afirmacion(
        "horas del backlog",
        horas_del_backlog,
        [
            ("docs/08-backlog.md", r"puntos · ([\d.]+) horas"),
            ("docs/tareas/README.md", r"puntos · ([\d.]+) horas"),
        ],
    ),
    Afirmacion(
        "trabajos del pipeline de CI",
        trabajos_de_ci,
        [
            ("README.md", r"Integración continua \| (\w+) trabajos"),
            ("docs/10-manual-tecnico.md", r"Integración continua, (\w+) trabajos"),
        ],
    ),
    # Se agrego al integrar D-17 y D-18: el manual tecnico decia 15 decisiones
    # cuando ya habia 18. Es el mismo defecto que esta herramienta existe para
    # detectar, y estaba fuera de su alcance porque el conteo de ADR solo se
    # imprimia como informativo.
    Afirmacion(
        "registros ADR",
        registros_adr,
        [("docs/10-manual-tecnico.md", r"Las (\d+) decisiones de arquitectura")],
    ),
]

# El reparto por sprint de docs/08-backlog.md: el encabezado de cada sprint y la
# columna de ese sprint en la fila del equipo de la tabla de carga.
#
# Se agrego el 20 de agosto, al insertar la historia H11.5. Toda la tabla de carga
# estaba desfasada y nadie se habia enterado: Cesar figuraba con 30.9 h en el
# Sprint 1 cuando ya eran 27.8 —D-22 le redujo H1.4 el dia anterior—, el total del
# equipo decia 618.7 contra 620.3 y los puntos 422 contra 423.
#
# Es el defecto de I-07 en otra tabla: cifras derivadas escritas a mano. La
# diferencia importante es que estas NO cambian al cerrar una historia, solo al
# cambiar el backlog, que hace una sola persona. Por eso comprobarlas no le rompe
# el CI a nadie por trabajo ajeno, que fue lo que obligo a retirar la linea de
# avance.
_COLUMNA_DEL_SPRINT = {"S0": 1, "S1": 2, "S2": 3, "S3": 4, "S4": 5}


def _patron_fila_equipo(sprint: str) -> str:
    """Captura la columna de ese sprint en la fila `| **Equipo** | ... |`."""
    saltar = r"[\d.]+ \| " * (_COLUMNA_DEL_SPRINT[sprint] - 1)
    return r"\| \*\*Equipo\*\* \| " + saltar + r"([\d.]+) \|"


for _s in ("S0", "S1", "S2", "S3", "S4"):
    AFIRMACIONES.append(
        Afirmacion(
            f"horas comprometidas en el {_s}",
            (lambda s: lambda: horas_del_sprint(s))(_s),
            [
                (
                    "docs/08-backlog.md",
                    rf"## Sprint {_s[1]} · semanas [\d-]+ · \d+ historias · ([\d.]+) h",
                ),
                ("docs/08-backlog.md", _patron_fila_equipo(_s)),
            ],
        )
    )
    AFIRMACIONES.append(
        Afirmacion(
            f"historias del {_s}",
            (lambda s: lambda: historias_del_sprint(s))(_s),
            [
                (
                    "docs/08-backlog.md",
                    rf"## Sprint {_s[1]} · semanas [\d-]+ · (\d+) historias",
                )
            ],
        )
    )

# El avance ya NO se comprueba aqui: se saco de docs/08-backlog.md el 20 de
# agosto. Era una cifra derivada que cambia cada vez que alguien cierra una
# historia, y ponerla bajo verificacion obligatoria hacia que el CI se rompiera
# para quien no la habia tocado. Ver la incidencia I-07.
#
# La imprime `verificar_estado.py`, que corre en el mismo trabajo del CI.

# Las cifras que no aparecen escritas en ningun documento pero conviene tener a
# mano al redactar: la herramienta las imprime para que nadie las cuente a mano.
INFORMATIVAS = [
    ("incidencias registradas", incidencias),
]

# Palabras que valen como numero en las tablas del README.
NUMEROS_ESCRITOS = {
    "cero": 0,
    "una": 1,
    "uno": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
    "ocho": 8,
    "nueve": 9,
    "diez": 10,
}


def normalizar(valor: str) -> str:
    """Convierte 'cinco' en '5' para poder comparar con el valor calculado."""
    return str(NUMEROS_ESCRITOS.get(valor.lower(), valor))


def main() -> int:
    print("\nVerificacion de cifras afirmadas en la documentacion\n")

    problemas: list[str] = []
    revisadas = 0

    for afirmacion in AFIRMACIONES:
        esperado = str(afirmacion.real())
        print(f"  {afirmacion.nombre}: {esperado}")

        for ruta_relativa, patron in afirmacion.apariciones:
            ruta = RAIZ / ruta_relativa
            if not ruta.exists():
                problemas.append(f"{ruta_relativa}: el archivo no existe")
                continue

            encontrados = re.findall(patron, ruta.read_text(encoding="utf-8"))
            if not encontrados:
                problemas.append(
                    f"{ruta_relativa}: no se encontro la afirmacion "
                    f"'{afirmacion.nombre}'. Si el texto cambio, hay que "
                    f"actualizar el patron en esta herramienta."
                )
                continue

            for encontrado in encontrados:
                revisadas += 1
                if normalizar(encontrado) != esperado:
                    problemas.append(
                        f"{ruta_relativa}: dice '{encontrado}' y el valor real es "
                        f"'{esperado}'  ({afirmacion.nombre})"
                    )

    print("\n  Para redactar, sin contar a mano:")
    for nombre, calcular in INFORMATIVAS:
        print(f"    {nombre}: {calcular()}")

    print(f"\n{revisadas} apariciones revisadas en la documentacion.")

    if problemas:
        print(f"\n{len(problemas)} discrepancias:\n")
        for problema in problemas:
            print(f"  - {problema}")
        print(
            "\nCorregir el documento, o la herramienta si fue el codigo el que "
            "cambio. No dejar la discrepancia: es como empezo la incidencia I-04.\n"
        )
        return 1

    print("\nTodas las cifras de la documentacion coinciden con el repositorio.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
