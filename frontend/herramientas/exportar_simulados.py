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
from datetime import date, timedelta
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
    "Contornos oficiales de la capa IGN_5_CO:limitedistrital_5k del SNIT, "
    "simplificados para el mapa web. La forma de los distritos es real; el "
    "riesgo que se pinta encima es simulado."
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

    Las geometrias son las **reales** del SNIT desde el 24 de agosto. Antes eran
    ocho cuadrados sobre una grilla de 3x3 que genero _cuadro() en los contratos
    congelados del 3 de agosto, y que sobrevivieron hasta el sitio publicado.
    Ver la incidencia **I-10**.

    Lo que sigue siendo simulado es el **riesgo**, no la forma del distrito.
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
                    # Bandera que lee docs/herramientas/verificar_h115.py: si
                    # llegara en true al dist publicado, el despliegue falla.
                    # Fue el defecto I-10 y ahora tiene quien lo vigile.
                    "geometria_simulada": False,
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


# --------------------------------------------------------------------------- #
# Mediciones diarias, para H7.2                                                 #
# --------------------------------------------------------------------------- #
#
# POR QUE EL RESPALDO NECESITA LA SERIE
#
# La grafica de H7.2 vive en la ficha del distrito. Sin este archivo existiria
# solo contra la API, y **el visor publicado por H11.5 no tiene API**: es el
# unico sitio donde alguien puede abrir el proyecto sin levantar nada, y ahi la
# grafica estaria vacia.
#
# POR QUE UNA VENTANA FIJA Y NO "TODO"
#
# La API acepta cualquier rango; un archivo estatico no puede. Se exporta una
# ventana declarada y **el archivo dice cual es**, para que el visor pueda
# limitar el selector en vez de dibujar vacio fuera de rango. Un rango que se
# ofrece y no tiene datos se lee como «no llovio», no como «no hay dato».
#
# POR QUE LAS CLAVES SON CORTAS
#
# `tx` en vez de `temp_max_c`, y demas. Con nombres completos el archivo pasa de
# 238 KB a mas de 600 KB para lo mismo, y esto se descarga entero en el visor
# publicado. El diccionario esta abajo, en `CAMPOS`.

DIAS_DE_SERIE = 365

#: clave corta -> atributo del contrato `MedicionDiaria`
CAMPOS = {
    "tx": "temp_max_c",
    "tn": "temp_min_c",
    "tm": "temp_media_c",
    "p": "precipitacion_mm",
    "h": "humedad_relativa_pct",
    "v": "viento_ms",
    "r": "radiacion_mj_m2",
}

ADVERTENCIA_MEDICIONES = (
    "SERIES SIMULADAS. Las sortea contratos/simulados/datos.py de forma "
    "determinista por distrito y fecha; no son observaciones reales. Los huecos "
    "-una de cada veinte fechas- son deliberados: existen para que la grafica "
    "tenga que demostrar que distingue un dia sin dato de un dia con valor cero."
)


def construir_mediciones(repositorio: RepositorioSimulado) -> dict:
    """La serie diaria de los ocho distritos, en la ventana declarada."""
    hasta = FECHA_REFERENCIA
    desde = hasta - timedelta(days=DIAS_DE_SERIE - 1)

    series: dict[str, list[dict]] = {}
    for distrito in repositorio.listar_distritos():
        filas = []
        for medicion in repositorio.obtener_mediciones(distrito.codigo, desde, hasta):
            fila = {"f": medicion.fecha.isoformat()}
            # `None` se conserva como `null`. NO se omite la clave ni se rellena
            # con cero: las dos cosas convertirian un dia sin medir en un dia
            # medido, que es justo lo que la grafica tiene que poder distinguir.
            fila.update({corto: getattr(medicion, largo) for corto, largo in CAMPOS.items()})
            filas.append(fila)
        series[distrito.codigo] = filas

    return {
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "campos": CAMPOS,
        "simulado": True,
        "advertencia": ADVERTENCIA_MEDICIONES,
        "series": series,
    }


def verificar_mediciones(paquete: dict) -> None:
    """Los mismos ocho distritos, la ventana completa, y huecos de verdad."""
    codigos = set(paquete["series"])
    if codigos != CODIGOS_ESPERADOS:
        faltan = CODIGOS_ESPERADOS - codigos
        sobran = codigos - CODIGOS_ESPERADOS
        raise SystemExit(f"ERROR en mediciones: faltan {faltan}, sobran {sobran}")

    for codigo, filas in paquete["series"].items():
        if len(filas) != DIAS_DE_SERIE:
            raise SystemExit(
                f"ERROR en mediciones de {codigo}: se esperaban {DIAS_DE_SERIE} dias "
                f"y llegaron {len(filas)}. Un dia faltante corre la serie y la "
                f"grafica dibujaria fechas equivocadas sin fallar."
            )

    # QUE HAYA HUECOS SE COMPRUEBA, NO SE SUPONE.
    #
    # El simulado promete una de cada veinte fechas sin dato. Si algun dia dejara
    # de cumplirlo, el criterio de aceptacion de H7.2 -que la linea se corte-
    # pasaria en verde sin haber dibujado un solo hueco: un control que no puede
    # fallar. Es la forma de I-06.
    con_hueco = sum(1 for filas in paquete["series"].values() for f in filas if f["tx"] is None)
    if con_hueco == 0:
        raise SystemExit(
            "ERROR: la serie exportada no tiene ningun hueco. El simulado promete "
            "uno de cada veinte dias; sin huecos, H7.2 no puede demostrar que los "
            "distingue de un valor cero."
        )


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


def escribir_compacto(ruta: Path, contenido: dict) -> None:
    """Sin sangria. Solo para `mediciones.json`, y por un motivo concreto.

    Los demas archivos se sangran porque **se leen**: son cortos y su diferencia
    en un Pull Request tiene que poder revisarse a ojo.

    La serie diaria no. Son 2920 filas que nadie va a leer, y sangrarla la lleva
    de 238 KB a 519 KB. **Ese archivo se descarga entero cada vez que alguien
    abre el visor publicado**, que es donde el respaldo es el unico origen que
    hay. Duplicar el peso de la unica descarga grande, para una sangria que nadie
    va a mirar, no se paga.
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(contenido, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )


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

    mediciones = construir_mediciones(repositorio)
    verificar_mediciones(mediciones)
    escribir_compacto(SALIDA / "mediciones.json", mediciones)

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
    huecos = sum(1 for filas in mediciones["series"].values() for f in filas if f["tx"] is None)
    total = sum(len(filas) for filas in mediciones["series"].values())
    print(
        f"\nSeries diarias: {mediciones['desde']} a {mediciones['hasta']}, "
        f"{DIAS_DE_SERIE} dias por distrito"
    )
    print(f"  {total} filas, {huecos} sin dato ({huecos / total:.1%}), deliberados")

    print(f"\nEscritos en {SALIDA.relative_to(RAIZ)}:")
    print("  distritos.geojson")
    print("  salud.json")
    print("  mediciones.json")
    for evento in TipoEvento:
        print(f"  riesgos-{evento.value}.json")
    print("\nGeometrias reales del SNIT. Niveles de riesgo sorteados por el")
    print("simulado: no son estimaciones reales.")


if __name__ == "__main__":
    main()
