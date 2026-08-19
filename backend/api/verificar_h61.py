"""
Verificador de la API. Dueno: Cesar. Historia H6.1, issue #59.

Cubre CA-1 a CA-10. CA-11 (maquina limpia) se verifica por fuera.

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
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from fastapi.testclient import TestClient

from backend.api.aplicacion import crear_aplicacion
from backend.api.dependencias import obtener_repositorio
from contratos.enums import ModoOperacion, TipoEvento
from contratos.esquemas import Distrito, MedicionDiaria, Riesgo, Salud

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
    print("Los diez criterios verificados aqui se cumplen.")
    print("Falta CA-11, que se verifica levantando el servidor en una maquina limpia.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
