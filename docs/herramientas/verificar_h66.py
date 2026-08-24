"""
Comprueba los criterios de aceptacion de H6.6: el visor consume la API real.

POR QUE ESTA EN docs/herramientas Y NO EN backend/api

El verificador de H6.1 vive en `backend/api/verificar_h61.py` porque esa carpeta
es de Cesar y la historia era suya. Esta comprueba una historia de Alejandro que
cruza las dos orillas: la forma que devuelve la API, que es de Cesar, y el modulo
que la consume, que es de Avril salvo por la excepcion de H6.6. No cabe en
ninguna de las dos carpetas sin invadirla, y `docs/herramientas/` ya es donde
viven los verificadores de Alejandro.

QUE COMPRUEBA

Sin levantar ningun servidor: usa el cliente de pruebas de FastAPI contra la
aplicacion de H6.1, y lee `frontend/src/datos/cliente.js` como texto.

    CA-1  el origen se resuelve una sola vez y no se mezcla
    CA-4  origen y modo son campos distintos
    CA-5  la fecha se arma en hora local, no en UTC
    CA-6  no hay ningun origen absoluto ni CORS
    I-08  la lectura es idempotente
    D-21  el nivel es coherente con la probabilidad

Y la que de verdad importa: que **cada campo que leen los componentes de Avril
exista en lo que produce el camino de la API**. Un campo que se pierde en la
traduccion no rompe nada: deja un hueco en pantalla.

Uso, desde la raiz del repositorio:

    python docs/herramientas/verificar_h66.py
"""

from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

CLIENTE = RAIZ / "frontend" / "src" / "datos" / "cliente.js"
CONFIG_VITE = RAIZ / "frontend" / "vite.config.js"
RESPALDO = RAIZ / "frontend" / "public" / "simulados"
COMPONENTES = RAIZ / "frontend" / "src" / "componentes"

# Los campos que los componentes de Avril leen de verdad. Salen de buscarlos en
# frontend/src/, no de suponerlos.
CAMPOS_DISTRITO = ("codigo", "nombre", "area_km2", "poblacion")
CAMPOS_RIESGO = ("nivel", "probabilidad", "version_modelo")

fallos: list[str] = []


def comprobar(descripcion: str, condicion: bool) -> None:
    print(f"  {'OK  ' if condicion else 'FALLO'}  {descripcion}")
    if not condicion:
        fallos.append(descripcion)


def sin_comentarios(codigo: str) -> str:
    """
    Quita comentarios antes de buscar en el codigo.

    No es refinamiento: la primera version de este verificador daba FALLO en
    "no se usa toISOString" porque `cliente.js` **explica en un comentario** por
    que no lo usa. Buscar en el texto crudo confunde lo que el codigo hace con lo
    que el codigo cuenta.
    """
    codigo = re.sub(r"/\*.*?\*/", "", codigo, flags=re.S)
    return re.sub(r"^\s*//.*$", "", codigo, flags=re.M)


def a_coleccion(distritos: list[dict]) -> dict:
    """La misma traduccion que hace cliente.js. Si una cambia, esta comprobacion
    deja de valer: por eso se comparan campos y no se copia la funcion entera."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": d["geometria"],
                "properties": {campo: d[campo] for campo in CAMPOS_DISTRITO},
            }
            for d in distritos
        ],
    }


def main() -> int:
    from fastapi.testclient import TestClient

    from backend.api.aplicacion import crear_aplicacion

    print("\nH6.6: el visor consume la API real\n")

    cliente = TestClient(crear_aplicacion())
    texto_cliente = sin_comentarios(CLIENTE.read_text(encoding="utf-8"))

    # ---------------------------------------------------------------- CA-6 -- #
    print("CA-6, el visor no necesita CORS:")
    comprobar(
        "cliente.js no escribe ningun origen absoluto",
        not re.search(r"https?://", texto_cliente),
    )
    comprobar(
        "la ruta de la API es relativa",
        "'/api'" in texto_cliente,
    )
    comprobar(
        "vite.config.js reenvia /api",
        "proxy" in sin_comentarios(CONFIG_VITE.read_text(encoding="utf-8")),
    )
    comprobar(
        "la API de H6.1 sigue sin middleware de CORS",
        "CORS" not in (RAIZ / "backend" / "api" / "aplicacion.py").read_text(encoding="utf-8"),
    )

    # ---------------------------------------------------------------- CA-1 -- #
    print("\nCA-1, el origen se resuelve una sola vez:")
    comprobar(
        "hay una unica promesa de negociacion memorizada",
        "let negociacion = null" in texto_cliente,
    )
    comprobar(
        "las tres funciones publicas la esperan",
        texto_cliente.count("await resolverOrigen()") == 3,
    )

    # ---------------------------------------------------------------- CA-4 -- #
    print("\nCA-4, origen y modo son dos campos distintos:")
    comprobar("obtenerSalud agrega el origen", "origen," in texto_cliente)
    comprobar("y el motivo de la degradacion", "motivo_respaldo" in texto_cliente)
    comprobar(
        "el modo no se sobreescribe: sigue viniendo de /salud",
        "modo:" not in texto_cliente,
    )

    # ---------------------------------------------------------------- CA-5 -- #
    print("\nCA-5, la fecha es local y no UTC:")
    comprobar("no se usa toISOString para armar la fecha", "toISOString" not in texto_cliente)
    comprobar("se arma con getFullYear/getMonth/getDate", "getFullYear()" in texto_cliente)

    # ---------------------------------------------------------------- CA-2 -- #
    print("\nCA-2, ningun componente cambia:")
    comprobar(
        "los componentes siguen sin saber de la API",
        not any("/api" in ruta.read_text(encoding="utf-8") for ruta in COMPONENTES.glob("*.jsx")),
    )
    comprobar(
        "ningun componente hace su propio fetch",
        not any("fetch(" in ruta.read_text(encoding="utf-8") for ruta in COMPONENTES.glob("*.jsx")),
    )

    # ------------------------------------------------------- forma de la API - #
    print("\nLa API produce todo lo que los componentes leen:")

    distritos = cliente.get("/distritos").json()
    comprobar("GET /distritos devuelve los ocho", len(distritos) == 8)

    coleccion = a_coleccion(distritos)
    propiedades = coleccion["features"][0]["properties"]
    for campo in CAMPOS_DISTRITO:
        comprobar(f"el distrito traducido conserva '{campo}'", campo in propiedades)
    comprobar(
        "la geometria llega como GeoJSON dibujable",
        coleccion["features"][0]["geometry"].get("type") == "Polygon",
    )

    hoy = date.today().isoformat()
    lista = cliente.get("/riesgos", params={"fecha": hoy, "tipo_evento": "sequia"}).json()
    comprobar("GET /riesgos responde para la fecha de hoy", isinstance(lista, list))
    for campo in CAMPOS_RIESGO:
        comprobar(f"el riesgo trae '{campo}'", all(campo in r for r in lista))

    # ---------------------------------------------------------------- I-08 -- #
    print("\nI-08, la lectura es idempotente:")
    tres = [
        cliente.get("/riesgos", params={"fecha": hoy, "tipo_evento": "sequia"}).json()
        for _ in range(3)
    ]
    comprobar("tres peticiones identicas devuelven lo mismo", tres[0] == tres[1] == tres[2])

    # ---------------------------------------------------------------- D-21 -- #
    print("\nD-21, la probabilidad es P(nivel = alto) y el nivel la respeta:")

    # Este bloque comprobaba `nivel == f(probabilidad)` con los cortes en tercios
    # escritos a mano aqui. Era una SEGUNDA COPIA de una regla que vive en el
    # contrato, y se desfaso en cuanto el contrato cambio: SC-05 hizo binario el
    # incendio y esta comprobacion siguio exigiendo tres clases.
    #
    # Copiar el corte nuevo habria arreglado el sintoma y dejado la copia. Lo que
    # se comprueba ahora es la propiedad que D-21 realmente exige y que vale para
    # cualquier productor, simulado o modelo entrenado:
    #
    #     MONOTONIA: ninguna fila con nivel menor tiene probabilidad mayor que
    #     una de nivel mayor, dentro del mismo evento.
    #
    # Los cortes concretos son del productor y pueden cambiar -SC-03 los declara
    # arbitrarios-. La monotonia no puede, porque de ella dependen el mapa de
    # calor de H5.4 y el orden del semaforo de H7.1.
    orden = {"bajo": 0, "medio": 1, "alto": 2}
    desordenados = []

    for evento in ("sequia", "incendio", "lluvia_intensa"):
        filas = [
            r
            for r in cliente.get("/riesgos", params={"fecha": hoy, "tipo_evento": evento}).json()
            if r["nivel"] is not None and r["probabilidad"] is not None
        ]
        for una in filas:
            for otra in filas:
                if orden[una["nivel"]] < orden[otra["nivel"]] and (
                    una["probabilidad"] > otra["probabilidad"]
                ):
                    desordenados.append((evento, una, otra))

    comprobar("ninguna fila con nivel bajo y probabilidad alta", desordenados == [])

    # SC-05: incendio es binario. Se comprueba contra el vocabulario del contrato
    # y no contra un corte escrito aqui.
    de_incendio = cliente.get("/riesgos", params={"fecha": hoy, "tipo_evento": "incendio"}).json()
    comprobar(
        "incendio no devuelve nivel medio, que SC-05 elimino para ese evento",
        all(r["nivel"] != "medio" for r in de_incendio),
    )

    # ---------------------------------------------------------------- CA-3 -- #
    print("\nCA-3, el respaldo estatico sigue completo:")
    for nombre in ("salud.json", "distritos.geojson"):
        comprobar(f"existe {nombre}", (RESPALDO / nombre).exists())
    for evento in ("sequia", "incendio", "lluvia_intensa"):
        comprobar(f"existe riesgos-{evento}.json", (RESPALDO / f"riesgos-{evento}.json").exists())

    # Que EXISTA no basta, y lo demostro SC-05.
    #
    # Estos archivos son artefactos derivados: los produce
    # `frontend/herramientas/exportar_simulados.py` desde el simulado. Al volver
    # binario el incendio, el respaldo se quedo con **cuatro distritos en nivel
    # medio** que el contrato ya no admite, y este bloque solo comprobaba que el
    # archivo estuviera ahi.
    #
    # Importa mas de lo que parece: el respaldo es lo que el visor sirve cuando la
    # API no responde, y es lo unico que se sirve en el sitio publico de H11.5.
    # Un respaldo desfasado es una pantalla publica contradiciendo al contrato.
    import json  # noqa: PLC0415

    for evento in ("sequia", "incendio", "lluvia_intensa"):
        ruta = RESPALDO / f"riesgos-{evento}.json"
        if not ruta.exists():
            continue
        filas = list(json.loads(ruta.read_text(encoding="utf-8"))["riesgos"].values())

        peor_bajo = max(
            (r["probabilidad"] for r in filas if r["nivel"] == "bajo" and r["probabilidad"]),
            default=-1.0,
        )
        mejor_alto = min(
            (r["probabilidad"] for r in filas if r["nivel"] == "alto" and r["probabilidad"]),
            default=2.0,
        )
        comprobar(
            f"el respaldo de {evento} respeta la monotonia de D-21",
            peor_bajo < mejor_alto,
        )

    incendio_estatico = json.loads(
        (RESPALDO / "riesgos-incendio.json").read_text(encoding="utf-8")
    )["riesgos"].values()
    comprobar(
        "el respaldo de incendio no trae nivel medio (SC-05)",
        all(r["nivel"] != "medio" for r in incendio_estatico),
    )

    # El respaldo AFIRMA una version de contratos, y `AvisoModoSimulado.jsx` la
    # pinta en pantalla: `contratos v{salud.version_contratos}`.
    #
    # Estuvo declarando **1.3.1 durante tres versiones**. Cada vez que el visor
    # caia al respaldo le mostraba al usuario una version falsa, y nada lo
    # detectaba: se encontro dos veces el mismo dia, por casualidad y por dos
    # caminos distintos.
    #
    # Es el unico artefacto derivado del proyecto que no tenia una maquina
    # comprobandolo. La matriz la comprueba `verificar_estado.py`; las cifras de
    # la documentacion, `verificar_documentacion.py`; esto, nada.
    #
    # No evita el conflicto de fusion -son seis lineas y dos ramas tocan siempre
    # la misma-, pero un conflicto es ruidoso y se resuelve regenerando. Lo que
    # esto evita es el desfase SILENCIOSO, que es el que hizo dano.
    from contratos import VERSION_CONTRATOS  # noqa: PLC0415

    declarada = json.loads((RESPALDO / "salud.json").read_text(encoding="utf-8")).get(
        "version_contratos"
    )
    comprobar(
        f"el respaldo declara la version de contratos vigente ({VERSION_CONTRATOS})",
        declarada == VERSION_CONTRATOS,
    )
    if declarada != VERSION_CONTRATOS:
        print(
            f"        salud.json dice {declarada!r} y el contrato va en "
            f"{VERSION_CONTRATOS!r}.\n"
            "        Se arregla regenerando, no editando:\n"
            "          python frontend/herramientas/exportar_simulados.py"
        )

    if fallos:
        print(f"\n{len(fallos)} criterios fallaron:\n")
        for f in fallos:
            print(f"  - {f}")
        print()
        return 1

    print("\nLos criterios de H6.6 se cumplen.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
