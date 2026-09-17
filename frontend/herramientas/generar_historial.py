"""
Lleva el catalogo de eventos historicos a un archivo que el visor pueda leer.

QUE PROBLEMA RESUELVE

H4.3 dejo 46 eventos documentados en `docs/investigacion/catalogo-eventos.csv`,
escritos a mano desde fuentes documentales y validados contra los contratos
congelados por `backend/calidad/validar_catalogo.py`. Son datos buenos que ya
pasaron un control. Lo unico que les faltaba era un camino hasta la pantalla.

El camino largo -tabla `analitico.evento`, `RepositorioPostgres.listar_eventos`,
una ruta nueva en la API, el visor- no existe: `listar_eventos` lanza
`TablaPendiente` y la tabla no esta en ninguna migracion. Construirlo entero no
cabe en los 3 puntos de H7.3.

El camino corto ya estaba inventado en este proyecto: **`frontend/public/` sirve
archivos estaticos** y es el respaldo de H6.6, lo que hace que el visor funcione
sin API. Este guion escribe ahi.

POR QUE UN GENERADOR Y NO UN JSON ESCRITO A MANO

Es el CA-1. Una segunda copia escrita a mano se desincroniza el dia que alguien
agregue un evento al catalogo, y nadie se entera hasta que las dos listas dicen
cosas distintas. El CSV es la fuente; esto es una vista derivada, como la matriz
de trazabilidad o los diagramas.

Para que eso sea comprobable y no una promesa, la salida lleva la **huella
sha256 del CSV del que salio**. `verificar_h73.py` la compara contra el CSV de
hoy. Es el mismo mecanismo que I-59 puso para los PNG del documento, y por la
misma razon: un artefacto derivado que nadie cruza contra su fuente termina
diciendo algo que dejo de ser cierto.

SE VALIDA ANTES DE GENERAR, Y SI NO VALIDA NO SE ESCRIBE NADA

Es el CA-2. `validar_catalogo` ya comprueba codigos de distrito de otro canton,
fechas de fin anteriores a las de inicio y tipos de evento mal escritos. Publicar
un CSV que el propio proyecto considera invalido seria peor que no publicar nada,
porque el visor lo mostraria con la misma cara de dato bueno.

LOS NOMBRES DE DISTRITO SE IMPORTAN, NO SE COPIAN

`DISTRITOS_TILARAN` vive en `validar_catalogo.py`, que este guion importa de
todos modos. Copiar los ocho nombres aca crearia la segunda lista que el CA-1
existe para evitar, en el mismo archivo que la evita.

Uso, desde la raiz del repositorio:

    python frontend/herramientas/generar_historial.py
    python frontend/herramientas/generar_historial.py --salida otra/carpeta

Historia H7.3. Rubrica de Computacion Grafica, CG-2.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

from backend.calidad.validar_catalogo import (  # noqa: E402
    DISTRITOS_TILARAN,
    RUTA_POR_DEFECTO,
    validar,
)

CATALOGO = RAIZ / RUTA_POR_DEFECTO
DESTINO = RAIZ / "frontend" / "public" / "historial" / "eventos.json"

# Las columnas que viajan al visor, en el orden en que se muestran.
#
# `codigo_distrito` viaja ademas del nombre porque el filtro trabaja con el
# codigo -que es lo que el contrato congela- y la pantalla muestra el nombre.
COLUMNAS = (
    "codigo_distrito",
    "tipo_evento",
    "fecha_inicio",
    "fecha_fin",
    "severidad",
    "fuente",
    "descripcion",
)


def huella(texto: str) -> str:
    """sha256 del CSV con los saltos de linea normalizados.

    Sin normalizar diria cosas distintas en Windows y en Ubuntu para el mismo
    archivo, que es I-56. La misma razon y la misma forma que en
    `generar_diagramas.huella`.
    """
    return hashlib.sha256(texto.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def leer_catalogo(ruta: Path) -> list[dict[str, str]]:
    """Las filas del CSV, con las llaves de `COLUMNAS` y nada mas.

    `utf-8-sig` y no `utf-8`: el catalogo se edito en Excel y arranca con BOM.
    Sin el `-sig`, la primera columna se llamaria `\\ufeffcodigo_distrito` y el
    filtro de distrito no encontraria nunca su campo.
    """
    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        filas = list(csv.DictReader(archivo))
    return [{c: (fila.get(c) or "").strip() for c in COLUMNAS} for fila in filas]


def construir(filas: list[dict[str, str]], texto_csv: str) -> dict:
    """El paquete que consume el visor."""
    por_distrito = Counter(fila["codigo_distrito"] for fila in filas)
    por_tipo = Counter(fila["tipo_evento"] for fila in filas)
    fechas = sorted(fila["fecha_inicio"] for fila in filas if fila["fecha_inicio"])

    return {
        # De donde salio y de que version. Lo lee `verificar_h73.py` y lo muestra
        # el pie de la pantalla: una lista de eventos sin procedencia no se
        # distingue de una lista inventada, y esta historia es CG-2.
        "fuente": str(RUTA_POR_DEFECTO).replace("\\", "/"),
        "generado": datetime.date.today().isoformat(),
        "huella": huella(texto_csv),
        # LOS OCHO DISTRITOS VIAJAN, TAMBIEN LOS QUE NO TIENEN NINGUN EVENTO.
        #
        # Cabeceras tiene cero. Si el desplegable ofreciera solo los siete con
        # datos, quien busca Cabeceras concluiria que el filtro esta roto o que
        # el distrito no existe. Ofrecerlo con su cuenta en cero dice la verdad
        # antes de hacer clic: no hay eventos documentados ahi, que es un
        # resultado del catalogo y no un defecto de la pantalla.
        "distritos": [
            {"codigo": codigo, "nombre": nombre, "eventos": por_distrito.get(codigo, 0)}
            for codigo, nombre in sorted(DISTRITOS_TILARAN.items())
        ],
        # Solo el identificador. El nombre para mostrar sale de
        # `frontend/src/datos/eventos.js`, que ya lo deriva del contrato: dos
        # lugares con el nombre serian dos lugares que se pueden contradecir.
        "tipos": [{"id": tipo, "eventos": por_tipo[tipo]} for tipo in sorted(por_tipo)],
        "rango": {"desde": fechas[0] if fechas else None, "hasta": fechas[-1] if fechas else None},
        "eventos": filas,
    }


def mostrar(ruta: Path) -> str:
    """Relativa al repositorio si esta dentro; absoluta si no.

    `--salida` acepta cualquier carpeta -se usa para probar el guion sin ensuciar
    el arbol- y `relative_to` lanza `ValueError` cuando el destino queda fuera de
    RAIZ. Sin esta guarda el generador **moria al imprimir, despues de haber
    escrito bien el archivo**: salia con codigo 1 habiendo hecho su trabajo.

    No es una precaucion teorica. Es el mismo defecto que ya tenia
    `generar_diagramas.py` y que su propio helper documenta; aca se reprodujo
    entero al escribir este archivo, y lo encontro el control de contraste de la
    prueba del CA-2 -la corrida con el catalogo bueno, que tenia que salir con 0
    y salia con 1-. Sin esa corrida de contraste, los tres sabotajes habrian
    salido en verde y el defecto se habria ido al Pull Request.
    """
    try:
        return str(ruta.relative_to(RAIZ))
    except ValueError:
        return str(ruta)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, default=CATALOGO)
    p.add_argument("--salida", type=Path, default=DESTINO)
    args = p.parse_args()

    print("\nHistorial de eventos para el visor\n")

    if not args.csv.exists():
        print(f"  no existe el catalogo: {args.csv}")
        return 1

    # CA-2. Primero se valida; si no valida, no se escribe nada.
    #
    # `validar` imprime su propio informe, asi que no se traduce ni se resume:
    # quien corra esto ve exactamente lo que vería corriendo el validador solo.
    print("  validando el catalogo contra los contratos congelados...\n")
    if validar(args.csv) != 0:
        print("\n  EL CATALOGO NO VALIDA. No se escribio ningun archivo.")
        print("  El visor sigue mostrando el historial anterior, que si validaba.\n")
        return 1

    texto = args.csv.read_text(encoding="utf-8-sig")
    filas = leer_catalogo(args.csv)
    paquete = construir(filas, texto)

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(
        json.dumps(paquete, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"\n  {len(filas)} eventos")
    for tipo in paquete["tipos"]:
        print(f"    {tipo['id']:16s} {tipo['eventos']:3d}")
    sin_eventos = [d["nombre"] for d in paquete["distritos"] if d["eventos"] == 0]
    if sin_eventos:
        print(f"    sin ningun evento documentado: {', '.join(sin_eventos)}")
    print(f"    {paquete['rango']['desde']} a {paquete['rango']['hasta']}")
    print(f"\n  {mostrar(args.salida)}")
    print(f"  huella del catalogo: {paquete['huella'][:16]}...\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
