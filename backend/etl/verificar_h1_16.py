"""
Verificador de H1.16: la serie larga del canton entra, y NO entra por distrito.

QUE COMPRUEBA Y POR QUE

D-47 decidio algo que es facil de escribir y facil de romper sin darse cuenta:
Open-Meteo entra **solo** como serie del canton, para contar episodios de sequia
en H3.11, y **no** alimenta el nivel de riesgo, ni el SPI de la tarjeta de H14.5,
ni la matriz de caracteristicas.

Una decision que solo vive en un documento se rompe el dia que alguien tiene
prisa. Este guion la comprueba en el codigo y en la base:

  * la tabla no tiene columna `codigo_distrito`, asi que no hay donde escribirlo;
  * el extractor no esta registrado en la fabrica, asi que el orquestador no
    puede pedirlo por nombre;
  * ningun archivo fuera de la lista de abajo nombra la tabla ni el extractor,
    asi que no hay un camino lateral hasta el riesgo o hasta la API;
  * el modelo va declarado y nunca es `best_match` (D-50).

Las comprobaciones offline no necesitan red ni base. Con `--con-base` se agregan
las que miran la tabla cargada.

    python -m backend.etl.verificar_h1_16
    python -m backend.etl.verificar_h1_16 --con-base
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from basedatos.conexion import ErrorConexion, conectar  # noqa: E402

DDL = RAIZ / "basedatos" / "ddl" / "020_serie_canton.sql"
FABRICA = RAIZ / "backend" / "etl" / "fuentes" / "fabrica.py"
EXTRACTOR = RAIZ / "backend" / "etl" / "fuentes" / "open_meteo.py"
HERRAMIENTA = RAIZ / "docs" / "herramientas" / "verificar_resolucion_fuente.py"

#: Los unicos archivos de codigo que pueden nombrar la serie del canton o su
#: extractor. Cualquier otro seria un camino hacia un uso que D-47 prohibe.
#: `docs/` queda fuera del barrido a proposito: ahi se nombra para explicarlo.
PERMITIDOS = {
    "basedatos/ddl/020_serie_canton.sql",
    "backend/etl/cargar_serie_canton.py",
    "backend/etl/fuentes/open_meteo.py",
    "backend/etl/fuentes/test_open_meteo.py",
    "backend/etl/verificar_h1_16.py",
}

#: Donde se barre. Es donde vive el codigo que podria usar el dato sin permiso.
CARPETAS_BARRIDAS = ("backend", "basedatos", "frontend", "contratos")

MARCAS = (re.compile(r"serie_canton"), re.compile(r"ExtractorOpenMeteoCanton"))


class Resultado:
    def __init__(self) -> None:
        self.pasadas = 0
        self.fallas: list[str] = []

    def comprobar(self, etiqueta: str, condicion: bool, detalle: str = "") -> None:
        if condicion:
            self.pasadas += 1
            print(f"  ok    {etiqueta}")
        else:
            self.fallas.append(etiqueta)
            print(f"  FALLA {etiqueta}")
            if detalle:
                print(f"        {detalle}")


def archivos_de_codigo() -> list[Path]:
    encontrados: list[Path] = []
    for carpeta in CARPETAS_BARRIDAS:
        raiz = RAIZ / carpeta
        if not raiz.is_dir():
            continue
        for ruta in raiz.rglob("*"):
            if not ruta.is_file() or ruta.suffix not in {".py", ".sql", ".js", ".mjs", ".json"}:
                continue
            if "__pycache__" in ruta.parts or "node_modules" in ruta.parts:
                continue
            encontrados.append(ruta)
    return encontrados


def offline(r: Resultado) -> None:
    print("\nSIN BASE NI RED")

    ddl = DDL.read_text(encoding="utf-8") if DDL.is_file() else ""
    r.comprobar("CA-9 · existe la migracion 020", bool(ddl), f"no esta {DDL}")
    # La palabra aparece en los comentarios del DDL a proposito, explicando por
    # que no esta. Lo que no puede existir es una COLUMNA que se llame asi.
    columna_prohibida = re.search(r"^\s*codigo_distrito\s", ddl, re.MULTILINE)
    r.comprobar(
        "CA-9 · la tabla NO tiene columna codigo_distrito",
        bool(ddl) and not columna_prohibida,
        "si la columna existe, D-47 se puede romper con un INSERT",
    )
    r.comprobar(
        "CA-9 · la clave primaria es la fecha sola",
        bool(re.search(r"fecha\s+date\s+PRIMARY KEY", ddl, re.IGNORECASE)),
        "una serie del canton tiene una fila por dia y nada mas",
    )
    r.comprobar(
        "D-50 · la tabla rechaza best_match y el modelo vacio",
        "best_match" in ddl and "CHECK" in ddl.upper(),
        "el CHECK del DDL es lo que impide guardar un modelo que no se eligio",
    )

    codigo_extractor = EXTRACTOR.read_text(encoding="utf-8") if EXTRACTOR.is_file() else ""
    r.comprobar(
        "el modelo declarado no es best_match",
        'MODELO = "era5"' in codigo_extractor,
        "D-50: el modelo lo elige el proyecto, no la API",
    )
    r.comprobar(
        "el extractor se niega a guardar una serie enteramente nula",
        "ninguno con" in codigo_extractor,
        "era5_land devuelve dias sin lluvia en cualquier punto del mundo",
    )

    fabrica = FABRICA.read_text(encoding="utf-8") if FABRICA.is_file() else ""
    r.comprobar(
        "CA-2 · el extractor NO esta registrado en la fabrica",
        "ExtractorOpenMeteoCanton" not in fabrica,
        "registrarlo lo volveria pedible por nombre, y por ahi entra por distrito",
    )

    herramienta = HERRAMIENTA.read_text(encoding="utf-8") if HERRAMIENTA.is_file() else ""
    r.comprobar(
        "la malla era5 esta declarada en el test de resolucion",
        '"era5":' in herramienta,
        "D-15 pide poder repetir el test sobre la fuente que de verdad se uso",
    )

    intrusos: list[str] = []
    for ruta in archivos_de_codigo():
        relativa = ruta.relative_to(RAIZ).as_posix()
        if relativa in PERMITIDOS:
            continue
        texto = ruta.read_text(encoding="utf-8", errors="ignore")
        if any(marca.search(texto) for marca in MARCAS):
            intrusos.append(relativa)
    r.comprobar(
        "D-47 · ningun otro archivo de codigo nombra la serie ni su extractor",
        not intrusos,
        "aparece en: " + ", ".join(intrusos) if intrusos else "",
    )


def con_base(r: Resultado) -> None:
    print("\nCONTRA LA BASE")
    try:
        with conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name FROM information_schema.columns
                 WHERE table_schema = 'crudo' AND table_name = 'serie_canton'
                """
            )
            columnas = {fila[0] for fila in cursor.fetchall()}
            r.comprobar("la tabla existe en crudo", bool(columnas))
            r.comprobar(
                "CA-9 · la tabla cargada no tiene codigo_distrito",
                "codigo_distrito" not in columnas,
            )

            cursor.execute(
                """
                SELECT count(*), min(fecha), max(fecha),
                       count(*) FILTER (WHERE precipitacion_mm IS NOT NULL),
                       count(DISTINCT modelo)
                  FROM crudo.serie_canton
                """
            )
            total, primera, ultima, con_dato, modelos = cursor.fetchone()
            print(f"        {total} filas, {primera} a {ultima}, {con_dato} con dato")
            r.comprobar("hay serie cargada", bool(total))
            r.comprobar(
                "el archivo arranca en 1950",
                primera is not None and primera.year == 1950,
                f"arranca en {primera}",
            )
            r.comprobar("CA-3 · un solo modelo en toda la serie", modelos == 1)

            cursor.execute(
                """
                SELECT count(*) FROM crudo.serie_canton
                 WHERE modelo IS NULL OR modelo = '' OR modelo = 'best_match'
                """
            )
            r.comprobar("CA-3 · ninguna fila sin modelo declarado", cursor.fetchone()[0] == 0)

            cursor.execute("SELECT count(*), count(DISTINCT fecha) FROM crudo.serie_canton")
            filas, fechas = cursor.fetchone()
            r.comprobar("una fila por dia, sin repetidos", filas == fechas)

            cursor.execute("SELECT count(DISTINCT (celda_lat, celda_lon)) FROM crudo.serie_canton")
            r.comprobar("toda la serie viene de una sola celda", cursor.fetchone()[0] == 1)
    except ErrorConexion as causa:
        r.comprobar("conexion a la base", False, str(causa))


def main() -> int:
    analizador = argparse.ArgumentParser(description="Verificador de H1.16 (D-47)")
    analizador.add_argument("--con-base", action="store_true", help="agrega las que miran la tabla")
    argumentos = analizador.parse_args()

    print("H1.16 · Open-Meteo como serie larga del canton · D-47")
    r = Resultado()
    offline(r)
    if argumentos.con_base:
        con_base(r)

    total = r.pasadas + len(r.fallas)
    print(f"\n{r.pasadas} de {total} comprobaciones pasan.")
    if r.fallas:
        print("FALLAN: " + ", ".join(r.fallas))
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
