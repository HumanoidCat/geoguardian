"""
Exporta los simulados de contratos/ a archivos estaticos que el visor puede leer.

Por que existe: los simulados de contratos/simulados/datos.py son objetos de
Python, y el navegador no los puede consumir. La API todavia no existe: segun el
roadmap llega en la semana 6. Este script traduce el simulado a archivos que el
frontend sirve desde public/, para no quedar bloqueada esperando.

Este script SOLO LEE contratos/. No lo modifica. Todo lo que escribe queda dentro
de frontend/, que es la carpeta propia.

Cuando la API exista, estos archivos se descartan y el visor cambia la URL del
fetch. Ningun componente tiene que cambiar.

Uso, desde la raiz del repositorio y con el entorno virtual activo:

    python frontend/herramientas/exportar_simulados.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from contratos.simulados.datos import RepositorioSimulado, salud_simulada  # noqa: E402

SALIDA = RAIZ / "frontend" / "public" / "simulados"

# Los ocho distritos del canton de Tilaran, provincia 5 Guanacaste, canton 08.
# Se usa solo para verificar que el contrato devuelve lo que se espera. Los
# codigos que terminan en los archivos salen del contrato, no de aqui.
CODIGOS_ESPERADOS = {"50801", "50802", "50803", "50804", "50805", "50806", "50807", "50808"}


def construir_geojson() -> dict:
    """
    Arma un FeatureCollection con los ocho distritos.

    ATENCION: las geometrias del simulado son cuadrados generados por la funcion
    _cuadro() de contratos/simulados/datos.py. NO son la forma real de los
    distritos. Las reales se cargan de la capa IGN_5_CO:limitedistrital_5k del
    SNIT en la historia H1.3, que no es de esta carpeta.

    Por eso el archivo lleva la marca simulado en sus propiedades y el visor
    muestra el aviso de modo simulado de forma permanente.
    """
    repositorio = RepositorioSimulado()
    distritos = repositorio.listar_distritos()

    rasgos = []
    for distrito in distritos:
        rasgos.append(
            {
                "type": "Feature",
                "geometry": distrito.geometria,
                "properties": {
                    "codigo": distrito.codigo,
                    "nombre": distrito.nombre,
                    "area_km2": distrito.area_km2,
                    # None en el contrato se conserva como null. Un distrito sin
                    # dato censal no tiene cero habitantes: no se sabe cuantos.
                    "poblacion": distrito.poblacion,
                    "geometria_simulada": True,
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "name": "distritos_tilaran_simulados",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"},
        },
        "advertencia": (
            "Geometrias de marcador de posicion, no son los limites reales de los "
            "distritos. Se reemplazan en la historia H1.3 con la capa del SNIT."
        ),
        "features": rasgos,
    }


def construir_salud() -> dict:
    """Estado que el visor consulta al arrancar para saber si debe avisar."""
    return json.loads(salud_simulada().model_dump_json())


def verificar(geojson: dict) -> None:
    """
    Falla ruidosamente si el resultado no es el esperado.

    Un archivo mal generado que se ve bien es peor que uno que no se genera:
    el mapa dibujaria algo y nadie se daria cuenta de que esta mal.
    """
    rasgos = geojson["features"]
    if len(rasgos) != 8:
        raise SystemExit(f"ERROR: se esperaban 8 distritos y llegaron {len(rasgos)}")

    codigos = {r["properties"]["codigo"] for r in rasgos}
    if codigos != CODIGOS_ESPERADOS:
        faltan = CODIGOS_ESPERADOS - codigos
        sobran = codigos - CODIGOS_ESPERADOS
        raise SystemExit(f"ERROR: codigos incorrectos. Faltan {faltan}, sobran {sobran}")

    sin_geometria = [
        r["properties"]["codigo"] for r in rasgos if not r["geometry"].get("coordinates")
    ]
    if sin_geometria:
        raise SystemExit(f"ERROR: distritos sin geometria: {sin_geometria}")


def escribir(ruta: Path, contenido: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    geojson = construir_geojson()
    verificar(geojson)

    salud = construir_salud()

    escribir(SALIDA / "distritos.geojson", geojson)
    escribir(SALIDA / "salud.json", salud)

    print(f"Distritos exportados: {len(geojson['features'])}")
    for rasgo in geojson["features"]:
        propiedades = rasgo["properties"]
        poblacion = propiedades["poblacion"]
        print(
            f"  {propiedades['codigo']}  {propiedades['nombre']:<16} "
            f"{propiedades['area_km2']:>6.1f} km2  "
            f"poblacion: {'sin dato' if poblacion is None else poblacion}"
        )
    print(f"\nModo de la API: {salud['modo']}")
    print(f"Version de contratos: {salud['version_contratos']}")
    print(f"\nEscritos en {SALIDA.relative_to(RAIZ)}:")
    print("  distritos.geojson")
    print("  salud.json")
    print("\nGeometrias de marcador de posicion. Se reemplazan en H1.3.")


if __name__ == "__main__":
    main()
