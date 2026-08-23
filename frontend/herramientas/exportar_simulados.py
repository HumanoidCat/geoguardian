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

Para producir el caso de ausencia de estimacion, que es el que va a devolver la
API real mientras no exista un modelo entrenado:

    python frontend/herramientas/exportar_simulados.py --sin-estimacion 2

Para producir el caso de nivel sin probabilidad, que es el que describe el
docstring de `Riesgo` en contratos/esquemas.py:

    python frontend/herramientas/exportar_simulados.py --sin-probabilidad 50807
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from contratos.enums import TipoEvento  # noqa: E402
from contratos.simulados.datos import RepositorioSimulado, salud_simulada  # noqa: E402

SALIDA = RAIZ / "frontend" / "public" / "simulados"

# Fecha de referencia de la exportacion. Fija para que el resultado sea
# reproducible: dos corridas del mismo commit producen archivos identicos.
FECHA_REFERENCIA = date(2026, 8, 16)

# Los ocho distritos del canton de Tilaran, provincia 5 Guanacaste, canton 08.
# Se usa solo para verificar que el contrato devuelve lo que se espera. Los
# codigos que terminan en los archivos salen del contrato, no de aqui.
CODIGOS_ESPERADOS = {"50801", "50802", "50803", "50804", "50805", "50806", "50807", "50808"}

ADVERTENCIA_GEOMETRIA = (
    "Geometrias de marcador de posicion, no son los limites reales de los "
    "distritos. Se reemplazan en la historia H1.3 con la capa del SNIT."
)

ADVERTENCIA_RIESGO = (
    "NIVELES SIMULADOS. No hay ningun modelo entrenado todavia: estos valores "
    "los sortea contratos/simulados/datos.py y no representan riesgo real. "
    "Existen unicamente para poder construir y verificar la representacion "
    "visual. El visor los declara como simulados de forma permanente."
)


def construir_geojson(repositorio: RepositorioSimulado) -> dict:
    """
    Arma un FeatureCollection con los ocho distritos.

    ATENCION: las geometrias del simulado son cuadrados generados por la funcion
    _cuadro() de contratos/simulados/datos.py. NO son la forma real de los
    distritos. Las reales se cargan de la capa IGN_5_CO:limitedistrital_5k del
    SNIT en la historia H1.3, que no es de esta carpeta.
    """
    rasgos = []
    for distrito in repositorio.listar_distritos():
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
        "advertencia": ADVERTENCIA_GEOMETRIA,
        "features": rasgos,
    }


def construir_riesgos(
    repositorio: RepositorioSimulado,
    evento: TipoEvento,
    sin_estimacion: int = 0,
    sin_probabilidad: tuple[str, ...] = (),
) -> dict:
    """
    Riesgo de un evento para los ocho distritos en la fecha de referencia.

    El nivel y la probabilidad los inventa el simulado. Se exportan igual porque
    sin ellos no hay forma de construir ni de verificar la representacion visual
    de la escala, que es lo que evalua el criterio CG-1. Cada archivo lleva la
    advertencia adentro, y el visor la repite en la leyenda y en la ficha del
    distrito.

    `sin_estimacion` deja los primeros N distritos, por orden de codigo, con
    nivel y probabilidad en None. No es un capricho de prueba: mientras no exista
    un modelo entrenado, ese es el estado que la API real va a devolver para
    todos los distritos, durante semanas. El contrato lo permite explicitamente y
    el visor tiene que seguir funcionando. Sin esta bandera no habria forma de
    capturar ese caso, porque el simulado siempre asigna nivel.

    `sin_probabilidad` es OTRO caso, y no el mismo mas suave: deja el nivel y
    borra la probabilidad de los distritos indicados. Es literalmente lo que dice
    el docstring de `Riesgo` en contratos/esquemas.py, "probabilidad y explicacion
    son None mientras no exista un modelo entrenado", y es coherente con el
    roadmap: la linea base climatologica de H3.1 puede clasificar un distrito sin
    que exista todavia el clasificador de H3.4 que estima P(nivel = alto). Por eso
    `algoritmo` y `version_modelo` tambien quedan en None.

    Existe porque sin ella este estado no se puede mirar en pantalla, y ordenar
    una tabla por un campo que puede faltar es exactamente donde estuvo el defecto
    que el Lead PM encontro en el PR #147.
    """
    riesgos = {}
    for riesgo in repositorio.obtener_riesgos_por_fecha(FECHA_REFERENCIA, evento):
        riesgos[riesgo.codigo_distrito] = {
            "nivel": riesgo.nivel.value if riesgo.nivel else None,
            "probabilidad": riesgo.probabilidad,
            "algoritmo": riesgo.algoritmo.value if riesgo.algoritmo else None,
            "version_modelo": riesgo.version_modelo,
        }

    for codigo in sorted(riesgos)[:sin_estimacion]:
        riesgos[codigo] = {
            "nivel": None,
            "probabilidad": None,
            "algoritmo": None,
            "version_modelo": None,
        }

    # Despues del anterior a proposito: si un distrito cae en las dos banderas,
    # queda sin estimacion, que es el estado mas pobre de los dos.
    for codigo in sin_probabilidad:
        if codigo not in riesgos:
            raise SystemExit(
                f"ERROR: el contrato no devolvio el distrito {codigo} para "
                f"{evento.value}, asi que --sin-probabilidad no puede aplicarse."
            )
        if riesgos[codigo]["nivel"] is None:
            continue
        riesgos[codigo] |= {"probabilidad": None, "algoritmo": None, "version_modelo": None}

    return {
        "tipo_evento": evento.value,
        "fecha": FECHA_REFERENCIA.isoformat(),
        "simulado": True,
        "advertencia": ADVERTENCIA_RIESGO,
        "riesgos": riesgos,
    }


def construir_salud() -> dict:
    """Estado que el visor consulta al arrancar para saber si debe avisar."""
    return json.loads(salud_simulada().model_dump_json())


def verificar_geojson(geojson: dict) -> None:
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


def verificar_riesgos(paquete: dict) -> None:
    """Los riesgos tienen que cubrir los mismos ocho distritos que el mapa."""
    codigos = set(paquete["riesgos"])
    if codigos != CODIGOS_ESPERADOS:
        faltan = CODIGOS_ESPERADOS - codigos
        sobran = codigos - CODIGOS_ESPERADOS
        raise SystemExit(
            f"ERROR en {paquete['tipo_evento']}: faltan {faltan}, sobran {sobran}. "
            "Un distrito sin entrada en el mapa de riesgos se dibujaria en blanco "
            "sin que nadie sepa por que."
        )


def escribir(ruta: Path, contenido: dict) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8")


def leer_argumentos() -> argparse.Namespace:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument(
        "--sin-estimacion",
        type=int,
        default=0,
        metavar="N",
        help=(
            "Deja los primeros N distritos sin nivel de riesgo, para reproducir "
            "el estado que devolvera la API mientras no exista modelo entrenado"
        ),
    )
    analizador.add_argument(
        "--sin-probabilidad",
        nargs="+",
        default=[],
        metavar="CODIGO",
        help=(
            "Deja los distritos indicados con nivel pero sin probabilidad, que es "
            "lo que el contrato permite mientras no exista un modelo entrenado"
        ),
    )
    argumentos = analizador.parse_args()

    if not 0 <= argumentos.sin_estimacion <= 8:
        raise SystemExit("ERROR: --sin-estimacion tiene que estar entre 0 y 8")

    desconocidos = sorted(set(argumentos.sin_probabilidad) - CODIGOS_ESPERADOS)
    if desconocidos:
        raise SystemExit(
            f"ERROR: --sin-probabilidad no reconoce {desconocidos}. "
            f"Los codigos del canton son {sorted(CODIGOS_ESPERADOS)}"
        )

    return argumentos


def main() -> None:
    argumentos = leer_argumentos()
    repositorio = RepositorioSimulado()

    geojson = construir_geojson(repositorio)
    verificar_geojson(geojson)
    escribir(SALIDA / "distritos.geojson", geojson)

    salud = construir_salud()
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

    print(f"\nRiesgos simulados para el {FECHA_REFERENCIA.isoformat()}:")
    if argumentos.sin_estimacion:
        print(f"  ({argumentos.sin_estimacion} distritos forzados a sin estimacion)")
    if argumentos.sin_probabilidad:
        forzados = ", ".join(sorted(set(argumentos.sin_probabilidad)))
        print(f"  ({forzados} forzados a nivel sin probabilidad)")
    for evento in TipoEvento:
        paquete = construir_riesgos(
            repositorio,
            evento,
            argumentos.sin_estimacion,
            tuple(argumentos.sin_probabilidad),
        )
        verificar_riesgos(paquete)
        escribir(SALIDA / f"riesgos-{evento.value}.json", paquete)

        conteo: dict[str, int] = {}
        for datos in paquete["riesgos"].values():
            clave = datos["nivel"] or "sin estimacion"
            conteo[clave] = conteo.get(clave, 0) + 1
        detalle = ", ".join(f"{cantidad} {nivel}" for nivel, cantidad in sorted(conteo.items()))
        print(f"  {evento.value:<16} {detalle}")

    print(f"\nModo de la API: {salud['modo']}")
    print(f"Version de contratos: {salud['version_contratos']}")
    print(f"\nEscritos en {SALIDA.relative_to(RAIZ)}:")
    print("  distritos.geojson")
    print("  salud.json")
    for evento in TipoEvento:
        print(f"  riesgos-{evento.value}.json")
    print("\nGeometrias de marcador de posicion. Se reemplazan en H1.3.")
    print("Niveles de riesgo sorteados por el simulado. No son estimaciones reales.")


if __name__ == "__main__":
    main()
