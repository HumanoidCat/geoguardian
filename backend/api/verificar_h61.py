"""
Verificador de la API. Dueno: Cesar. Historia H6.1, issue #59.

Cubre CA-1 a CA-10, mas CA-12 y CA-13, que saldan las dos garantias que
prometio SC-03. CA-11 (maquina limpia) se verifica por fuera.

POR QUE USA TestClient Y NO UN SERVIDOR

Dos motivos. Corre sin puerto ni proceso aparte, asi que entra en el CI sin
infraestructura. Y hace posible el CA-7: FastAPI permite sustituir una dependencia
en caliente, asi que se puede meter un repositorio falso y comprobar que los
endpoints devuelven SUS datos. Si algun endpoint tuviera la implementacion
cableada, esa comprobacion falla.

Levantar el servidor de verdad con uvicorn se verifica aparte, porque un cliente
de prueba no demuestra que el proceso arranque.

USO

    python -m backend.api.verificar_h61
    python backend/api/verificar_h61.py

Las dos formas funcionan. La segunda lo hace desde H6.2; ver el arreglo del
path mas abajo.
"""

from __future__ import annotations

import ast
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# El verificador se invoca de dos formas y las dos tienen que funcionar:
#
#     python -m backend.api.verificar_h61      agrega la raiz del repositorio
#     python backend/api/verificar_h61.py      agrega backend/api/, no la raiz
#
# Sin estas dos lineas la segunda falla con "No module named 'backend'". Es el
# mismo motivo por el que `pyproject.toml` declara `pythonpath` para pytest: si
# una forma de invocar funciona y la otra no, el CI y la maquina de quien
# escribe discrepan sobre si el control corre.
#
# `verificar_h60.py` no necesita nada de esto porque solo usa biblioteca
# estandar. Este importa `backend` y `contratos`. Deuda anotada al revisar SC-03
# y saldada en H6.2.
RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
if str(RAIZ_REPOSITORIO) not in sys.path:
    sys.path.insert(0, str(RAIZ_REPOSITORIO))

# Los imports que siguen van despues del arreglo del path A PROPOSITO, y por eso
# llevan la excepcion de E402: puestos arriba, el modulo no se puede importar
# invocado por ruta, que es exactamente lo que las lineas de arriba arreglan.
from fastapi.testclient import TestClient  # noqa: E402

from backend.api.aplicacion import crear_aplicacion  # noqa: E402
from backend.api.dependencias import obtener_repositorio  # noqa: E402
from contratos.enums import ModoOperacion, NivelRiesgo, TipoEvento  # noqa: E402
from contratos.esquemas import Distrito, MedicionDiaria, Riesgo, Salud  # noqa: E402
from contratos.simulados.datos import RepositorioSimulado  # noqa: E402

RAIZ_API = Path(__file__).resolve().parent

RUTAS_ESPERADAS = [
    "/salud",
    "/distritos",
    "/distritos/{codigo}",
    "/distritos/{codigo}/mediciones",
    "/distritos/{codigo}/riesgo",
    "/riesgos",
]

CODIGO = "50801"
FECHA = "2024-06-15"

# Varias fechas para la monotonia: con ocho distritos por fecha, una sola daria
# ocho pares (probabilidad, nivel) por evento y el orden no significaria gran
# cosa. Tres dan veinticuatro.
FECHAS_MONOTONIA = ["2024-01-15", "2024-06-15", "2024-11-15"]

# Orden de severidad. `NivelRiesgo` es un Enum de cadenas y no define orden, asi
# que se declara aca en vez de comparar los valores como texto, que daria
# alto < bajo < medio.
ORDEN_NIVEL = {
    NivelRiesgo.BAJO.value: 0,
    NivelRiesgo.MEDIO.value: 1,
    NivelRiesgo.ALTO.value: 2,
}


@dataclass
class Resultado:
    criterio: str
    titulo: str
    cumple: bool
    detalle: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# CA-1 · arranca y responde                                                    #
# --------------------------------------------------------------------------- #


def ca1_arranca(cliente: TestClient) -> Resultado:
    respuesta = cliente.get("/salud")
    ok = respuesta.status_code == 200
    return Resultado(
        "CA-1",
        "La API arranca y responde",
        ok,
        [f"  GET /salud -> {respuesta.status_code}"],
    )


# --------------------------------------------------------------------------- #
# CA-2 · ningun esquema redefinido                                             #
# --------------------------------------------------------------------------- #


def ca2_sin_esquemas_propios() -> Resultado:
    """
    En backend/api/ solo puede haber un BaseModel propio: el de error.

    Un esquema copiado del contrato seria una segunda definicion que se
    desincroniza en silencio.
    """
    patron = re.compile(r"^\s*class\s+(\w+)\s*\(\s*BaseModel\s*\)", re.MULTILINE)
    hallazgos: list[str] = []

    for ruta in sorted(RAIZ_API.glob("*.py")):
        for nombre in patron.findall(ruta.read_text(encoding="utf-8")):
            hallazgos.append(f"{ruta.name}:{nombre}")

    permitidos = {"errores.py:Error"}
    sobrantes = [h for h in hallazgos if h not in permitidos]

    detalle = [f"  modelos propios encontrados: {hallazgos or 'ninguno'}"]
    if sobrantes:
        detalle.append(f"  SOBRAN: {sobrantes}")
    return Resultado("CA-2", "Ningun esquema del contrato esta redefinido", not sobrantes, detalle)


# --------------------------------------------------------------------------- #
# CA-3 · los seis endpoints devuelven la forma del contrato                    #
# --------------------------------------------------------------------------- #


def ca3_forma_de_respuestas(cliente: TestClient) -> Resultado:
    """Cada respuesta se valida construyendo el modelo del contrato."""
    comprobaciones = [
        ("GET /salud", "/salud", {}, Salud, False),
        ("GET /distritos", "/distritos", {}, Distrito, True),
        (f"GET /distritos/{CODIGO}", f"/distritos/{CODIGO}", {}, Distrito, False),
        (
            f"GET /distritos/{CODIGO}/mediciones",
            f"/distritos/{CODIGO}/mediciones",
            {"desde": "2024-06-01", "hasta": "2024-06-05"},
            MedicionDiaria,
            True,
        ),
        (
            f"GET /distritos/{CODIGO}/riesgo",
            f"/distritos/{CODIGO}/riesgo",
            {"fecha": FECHA, "tipo_evento": TipoEvento.SEQUIA.value},
            Riesgo,
            False,
        ),
        (
            "GET /riesgos",
            "/riesgos",
            {"fecha": FECHA, "tipo_evento": TipoEvento.INCENDIO.value},
            Riesgo,
            True,
        ),
    ]

    detalle: list[str] = []
    ok = True

    for titulo, ruta, parametros, modelo, es_lista in comprobaciones:
        respuesta = cliente.get(ruta, params=parametros)
        if respuesta.status_code != 200:
            ok = False
            detalle.append(f"  [MAL] {titulo:<38} {respuesta.status_code}")
            continue
        try:
            cuerpo = respuesta.json()
            if es_lista:
                elementos = [modelo.model_validate(x) for x in cuerpo]
                detalle.append(f"  [ok ] {titulo:<38} {len(elementos)} x {modelo.__name__}")
            else:
                modelo.model_validate(cuerpo)
                detalle.append(f"  [ok ] {titulo:<38} {modelo.__name__}")
        except Exception as error:  # noqa: BLE001 - se reporta cualquier fallo de forma
            ok = False
            detalle.append(f"  [MAL] {titulo:<38} {str(error).splitlines()[0][:44]}")

    return Resultado("CA-3", "Los seis endpoints devuelven la forma del contrato", ok, detalle)


# --------------------------------------------------------------------------- #
# CA-4 y CA-5 · OpenAPI                                                        #
# --------------------------------------------------------------------------- #


def ca4_openapi(cliente: TestClient) -> Resultado:
    respuesta = cliente.get("/openapi.json")
    if respuesta.status_code != 200:
        return Resultado("CA-4", "OpenAPI describe todo", False, ["  /openapi.json no responde"])

    documento = respuesta.json()
    rutas = documento.get("paths", {})
    componentes = documento.get("components", {}).get("schemas", {})

    detalle: list[str] = []
    ok = True

    for esperada in RUTAS_ESPERADAS:
        if esperada not in rutas:
            ok = False
            detalle.append(f"  [MAL] falta la ruta {esperada}")
            continue

        operacion = rutas[esperada].get("get", {})
        contenido = operacion.get("responses", {}).get("200", {}).get("content", {})
        esquema = contenido.get("application/json", {}).get("schema")

        if not esquema:
            ok = False
            detalle.append(f"  [MAL] {esperada} no declara esquema de respuesta")
            continue

        # La referencia puede ser directa o a traves de un array de items.
        referencia = esquema.get("$ref") or esquema.get("items", {}).get("$ref")
        nombre = referencia.rsplit("/", 1)[-1] if referencia else None

        if nombre and nombre not in componentes:
            ok = False
            detalle.append(f"  [MAL] {esperada} referencia {nombre}, que no esta en components")
        else:
            detalle.append(f"  [ok ] {esperada:<34} -> {nombre or esquema.get('type')}")

    detalle.append(f"  esquemas en components: {len(componentes)}")
    return Resultado("CA-4", "OpenAPI describe todos los endpoints", ok, detalle)


def ca5_docs(cliente: TestClient) -> Resultado:
    respuesta = cliente.get("/docs")
    return Resultado(
        "CA-5",
        "La documentacion interactiva esta disponible",
        respuesta.status_code == 200,
        [f"  GET /docs -> {respuesta.status_code}"],
    )


# --------------------------------------------------------------------------- #
# CA-6 y CA-7 · arquitectura                                                   #
# --------------------------------------------------------------------------- #


def _lineas_de_prosa(texto: str) -> set[int]:
    """
    Numeros de linea que son comentario o docstring, no codigo ejecutable.

    Misma leccion que en H1.8: la primera version de esta comprobacion marcaba el
    docstring de rutas.py, donde esta escrito por que ese modulo no debe importar
    una implementacion concreta. Explicar la regla no es violarla, y un criterio
    que da falsos positivos se termina ignorando.
    """
    prosa = {n for n, linea in enumerate(texto.splitlines(), 1) if linea.strip().startswith("#")}

    try:
        arbol = ast.parse(texto)
    except SyntaxError:
        return prosa

    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Module | ast.ClassDef | ast.FunctionDef):
            continue
        cuerpo = getattr(nodo, "body", [])
        if cuerpo and isinstance(cuerpo[0], ast.Expr):
            valor = cuerpo[0].value
            if isinstance(valor, ast.Constant) and isinstance(valor.value, str):
                prosa.update(range(valor.lineno, (valor.end_lineno or valor.lineno) + 1))

    return prosa


def ca6_sin_implementacion_concreta() -> Resultado:
    """
    Ningun modulo de rutas puede conocer una implementacion concreta.

    dependencias.py queda fuera a proposito: es el unico lugar donde se decide, y
    ese es justamente el punto del patron.
    """
    hallazgos: list[str] = []
    revisados: list[str] = []

    for ruta in sorted(RAIZ_API.glob("*.py")):
        if ruta.name in ("dependencias.py", "verificar_h61.py"):
            continue
        revisados.append(ruta.name)
        texto = ruta.read_text(encoding="utf-8")
        prosa = _lineas_de_prosa(texto)
        for n, linea in enumerate(texto.splitlines(), 1):
            if n in prosa:
                continue
            if "contratos.simulados" in linea or "RepositorioSimulado" in linea:
                hallazgos.append(f"  {ruta.name}:{n}  {linea.strip()[:56]}")

    detalle = hallazgos or [
        f"  ninguno de {len(revisados)} modulos conoce una implementacion concreta",
        f"  revisados: {', '.join(revisados)}",
    ]
    return Resultado("CA-6", "Los endpoints dependen del protocolo", not hallazgos, detalle)


class RepositorioFalso:
    """
    Repositorio de prueba, con datos reconocibles y distintos a los del simulado.

    No hereda de nada: cumple el protocolo por estructura, igual que exige
    `contratos/repositorio.py`. Si los endpoints devuelven ESTOS datos, la
    inyeccion de dependencias funciona de verdad.
    """

    MARCA = "Distrito de prueba CA-7"

    def _distrito(self) -> Distrito:
        return Distrito(
            codigo="59999",
            nombre=self.MARCA,
            area_km2=1.0,
            poblacion=None,
            geometria={"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]]},
        )

    def listar_distritos(self) -> list[Distrito]:
        return [self._distrito()]

    def obtener_distrito(self, codigo: str) -> Distrito | None:
        return self._distrito() if codigo == "59999" else None

    def obtener_mediciones(self, codigo_distrito, desde, hasta):  # noqa: ANN001, ARG002
        return []

    def obtener_riesgo(self, codigo_distrito, fecha, tipo_evento):  # noqa: ANN001
        return Riesgo(codigo_distrito=codigo_distrito, fecha=fecha, tipo_evento=tipo_evento)

    def obtener_riesgos_por_fecha(self, fecha, tipo_evento):  # noqa: ANN001
        return [self.obtener_riesgo("59999", fecha, tipo_evento)]


def ca7_sustitucion() -> Resultado:
    """Cambiar la implementacion no toca ningun endpoint."""
    aplicacion = crear_aplicacion()
    aplicacion.dependency_overrides[obtener_repositorio] = RepositorioFalso

    detalle: list[str] = []
    ok = True

    with TestClient(aplicacion) as cliente:
        distritos = cliente.get("/distritos").json()
        nombres = [d["nombre"] for d in distritos]
        if nombres != [RepositorioFalso.MARCA]:
            ok = False
            detalle.append(f"  [MAL] /distritos devolvio {nombres}")
        else:
            detalle.append(f"  [ok ] /distritos devolvio los datos del falso: {nombres}")

        # El simulado si conoce 50801; el falso no. Si responde 404, el endpoint
        # esta usando de verdad la implementacion inyectada.
        codigo_simulado = cliente.get(f"/distritos/{CODIGO}").status_code
        if codigo_simulado != 404:
            ok = False
            detalle.append(
                f"  [MAL] /distritos/{CODIGO} devolvio {codigo_simulado}, se esperaba 404"
            )
        else:
            detalle.append(f"  [ok ] /distritos/{CODIGO} -> 404, el simulado ya no responde")

        salud = cliente.get("/salud").json()
        if salud["modo"] != ModoOperacion.REAL.value:
            ok = False
            detalle.append(f"  [MAL] /salud dice modo={salud['modo']}, se esperaba real")
        else:
            detalle.append("  [ok ] /salud deduce el modo de la implementacion, no de un literal")

    detalle.append("  ningun archivo de rutas fue modificado para esta prueba")
    return Resultado("CA-7", "Sustituir la implementacion no toca ningun endpoint", ok, detalle)


# --------------------------------------------------------------------------- #
# CA-8, CA-9 y CA-10 · honestidad del dato                                     #
# --------------------------------------------------------------------------- #


def ca8_modo_simulado(cliente: TestClient) -> Resultado:
    salud = cliente.get("/salud").json()
    modo_ok = salud["modo"] == ModoOperacion.SIMULADO.value
    bd_ok = salud["base_datos_conectada"] is False

    fuente = (RAIZ_API / "rutas.py").read_text(encoding="utf-8")
    sin_literal = '"simulado"' not in fuente and "'simulado'" not in fuente

    detalle = [
        f"  modo: {salud['modo']} (esperado simulado)",
        f"  base_datos_conectada: {salud['base_datos_conectada']} (esperado False)",
        f"  el valor no esta escrito a mano en rutas.py: {sin_literal}",
    ]
    return Resultado(
        "CA-8",
        "La API declara que sirve datos simulados",
        modo_ok and bd_ok and sin_literal,
        detalle,
    )


def ca9_nulos(cliente: TestClient) -> Resultado:
    """Los nulos del contrato viajan como nulos, no como ceros."""
    detalle: list[str] = []
    ok = True

    distritos = cliente.get("/distritos").json()
    poblaciones = {d["codigo"]: d["poblacion"] for d in distritos}
    if any(p is not None for p in poblaciones.values()):
        ok = False
        detalle.append(f"  [MAL] hay poblacion no nula: {poblaciones}")
    else:
        detalle.append(f"  [ok ] poblacion null en los {len(poblaciones)} distritos")

    mediciones = cliente.get(
        f"/distritos/{CODIGO}/mediciones", params={"desde": "2024-06-01", "hasta": "2024-06-30"}
    ).json()
    con_hueco = [m for m in mediciones if m["precipitacion_mm"] is None]
    if not con_hueco:
        ok = False
        detalle.append("  [MAL] ninguna medicion trae huecos; el simulado deberia tenerlos")
    else:
        detalle.append(f"  [ok ] {len(con_hueco)} de {len(mediciones)} dias con hueco como null")

    ceros = [m for m in mediciones if m["precipitacion_mm"] == 0]
    detalle.append(f"  dias con precipitacion 0.0, que es una medicion y no un hueco: {len(ceros)}")

    return Resultado("CA-9", "Los nulos del contrato viajan como nulos", ok, detalle)


def ca10_no_encontrado(cliente: TestClient) -> Resultado:
    respuesta = cliente.get("/distritos/00000")
    cuerpo = respuesta.json()
    ok = respuesta.status_code == 404 and "detail" in cuerpo
    return Resultado(
        "CA-10",
        "Un distrito inexistente devuelve 404",
        ok,
        [f"  GET /distritos/00000 -> {respuesta.status_code}  {cuerpo}"],
    )


# --------------------------------------------------------------------------- #
# CA-12 y CA-13 - las dos garantias que prometio SC-03                         #
# --------------------------------------------------------------------------- #


def ca12_idempotencia(cliente: TestClient) -> Resultado:
    """
    La misma consulta de riesgo devuelve siempre lo mismo.

    SC-03 lo prometio con estas palabras: "dentro de un proceso y entre procesos
    distintos". Se comprueban las dos mitades, y la segunda es la que vale: la
    primera sola pasaria aunque el simulado guardara la respuesta en una cache.

    LO QUE ESTA COMPROBACION **NO** ES

    No es "un GET devuelve siempre lo mismo". La idempotencia de HTTP restringe
    el efecto sobre el servidor, no la representacion devuelta: `/salud` cambia
    entre llamadas y no viola ninguna regla. Lo que se comprueba aca es la
    garantia que el simulado dio sobre sus propios datos, que es otra cosa y mas
    fuerte. La correccion esta en SC-03, aportada al aprobar la solicitud.
    """
    detalle: list[str] = []
    ok = True

    parametros = {"fecha": FECHA, "tipo_evento": TipoEvento.SEQUIA.value}
    primera = cliente.get("/riesgos", params=parametros).json()
    segunda = cliente.get("/riesgos", params=parametros).json()

    if primera != segunda:
        ok = False
        cambiados = [
            a.get("codigo_distrito") for a, b in zip(primera, segunda, strict=False) if a != b
        ]
        detalle.append(f"  [MAL] dos peticiones identicas difieren en: {cambiados}")
    else:
        detalle.append(
            f"  [ok ] dos GET /riesgos identicos devolvieron las mismas {len(primera)} filas"
        )

    # La instancia de la API esta cacheada con lru_cache. Esta es otra, con su
    # propio generador recien creado: si los valores dependieran del estado del
    # generador, esta mitad falla y la de arriba no.
    aparte = RepositorioSimulado()
    fecha = date.fromisoformat(FECHA)
    discrepan: list[str] = []
    for fila in primera:
        propio = aparte.obtener_riesgo(fila["codigo_distrito"], fecha, TipoEvento.SEQUIA)
        if propio is None:
            discrepan.append(f"{fila['codigo_distrito']}: la instancia nueva devolvio None")
        elif propio.nivel.value != fila["nivel"] or propio.probabilidad != fila["probabilidad"]:
            discrepan.append(
                f"{fila['codigo_distrito']}: la API dice {fila['nivel']}/{fila['probabilidad']}"
                f" y la instancia nueva {propio.nivel.value}/{propio.probabilidad}"
            )

    if discrepan:
        ok = False
        detalle.append("  [MAL] una instancia nueva del simulado no reproduce los valores:")
        detalle.extend(f"    {d}" for d in discrepan)
    else:
        detalle.append(
            f"  [ok ] una instancia nueva del simulado, ajena a la que la API cachea,"
            f" reprodujo los {len(primera)} valores"
        )

    return Resultado("CA-12", "La misma consulta de riesgo devuelve siempre lo mismo", ok, detalle)


def ca13_monotonia(cliente: TestClient) -> Resultado:
    """
    Una probabilidad mayor nunca produce un nivel menor.

    Segunda garantia de SC-03. El defecto que la origino fue concreto: el 20 de
    agosto el distrito 50802 salio con nivel `bajo` y probabilidad 0,90, porque
    el simulado sorteaba las dos cosas por separado. Bajo D-21 `probabilidad` es
    P(nivel = alto), asi que esa fila era imposible.

    De esta propiedad dependen el mapa de calor de H5.4, que interpola la
    probabilidad, y el semaforo continuo de H7.1.
    """
    detalle: list[str] = []
    ok = True

    for tipo in TipoEvento:
        pares: list[tuple[float, str]] = []
        for fecha in FECHAS_MONOTONIA:
            filas = cliente.get(
                "/riesgos", params={"fecha": fecha, "tipo_evento": tipo.value}
            ).json()
            pares.extend(
                (f["probabilidad"], f["nivel"])
                for f in filas
                if f["probabilidad"] is not None and f["nivel"] is not None
            )

        if not pares:
            ok = False
            detalle.append(f"  [MAL] {tipo.value}: ninguna fila trae nivel y probabilidad")
            continue

        pares.sort()
        inversiones = [
            (pares[i], pares[i + 1])
            for i in range(len(pares) - 1)
            if ORDEN_NIVEL[pares[i + 1][1]] < ORDEN_NIVEL[pares[i][1]]
        ]
        if inversiones:
            ok = False
            antes, despues = inversiones[0]
            detalle.append(
                f"  [MAL] {tipo.value}: {len(inversiones)} inversiones."
                f" La primera: {antes} y despues {despues}"
            )
        else:
            niveles = sorted({n for _, n in pares}, key=lambda n: ORDEN_NIVEL[n])
            detalle.append(
                f"  [ok ] {tipo.value}: {len(pares)} pares ordenados por probabilidad,"
                f" niveles {niveles}"
            )

    # SC-05 dejo el incendio binario: emitir MEDIO seria producir un valor que el
    # contrato ya no admite, y un doble que emite valores imposibles no sirve
    # para sustituir al original.
    incendio = [
        f
        for fecha in FECHAS_MONOTONIA
        for f in cliente.get(
            "/riesgos", params={"fecha": fecha, "tipo_evento": TipoEvento.INCENDIO.value}
        ).json()
    ]
    con_medio = [f for f in incendio if f["nivel"] == NivelRiesgo.MEDIO.value]
    if con_medio:
        ok = False
        detalle.append(
            f"  [MAL] incendio emitio nivel medio en {len(con_medio)} filas; SC-05 lo hizo binario"
        )
    else:
        detalle.append(f"  [ok ] incendio no emite nivel medio en {len(incendio)} filas (SC-05)")

    return Resultado("CA-13", "Una probabilidad mayor nunca da un nivel menor", ok, detalle)


# --------------------------------------------------------------------------- #


def main() -> int:
    print("Verificacion de la API de H6.1 (issue #59)")
    print("=" * 74)

    aplicacion = crear_aplicacion()
    resultados: list[Resultado] = []

    with TestClient(aplicacion) as cliente:
        resultados.append(ca1_arranca(cliente))
        resultados.append(ca2_sin_esquemas_propios())
        resultados.append(ca3_forma_de_respuestas(cliente))
        resultados.append(ca4_openapi(cliente))
        resultados.append(ca5_docs(cliente))
        resultados.append(ca6_sin_implementacion_concreta())
        resultados.append(ca8_modo_simulado(cliente))
        resultados.append(ca9_nulos(cliente))
        resultados.append(ca10_no_encontrado(cliente))
        resultados.append(ca12_idempotencia(cliente))
        resultados.append(ca13_monotonia(cliente))

    resultados.append(ca7_sustitucion())
    resultados.sort(key=lambda r: int(r.criterio.split("-")[1]))

    for r in resultados:
        print(f"\n{r.criterio} · {r.titulo} ... {'CUMPLE' if r.cumple else 'NO CUMPLE'}")
        for linea in r.detalle:
            print(linea)

    fallidos = [r for r in resultados if not r.cumple]
    print("\n" + "=" * 74)
    if fallidos:
        print("NO CUMPLEN: " + ", ".join(r.criterio for r in fallidos))
        return 1
    print("Los doce criterios verificados aqui se cumplen.")
    print("Falta CA-11, que se verifica levantando el servidor en una maquina limpia.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
