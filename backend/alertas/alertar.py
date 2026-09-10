"""
Avisa cuando el pipeline o el despliegue fallan. Dueno: Cesar. Historia H12.3, issue #80.

QUE HACE

Lee **una corrida** de GitHub Actions y, segun como termino:

  - si fallo, abre una issue etiquetada `alerta`, o **comenta en la que ya
    estaba abierta** para ese mismo flujo y esa misma rama;
  - si termino bien, **cierra** la alerta abierta de ese flujo y esa rama,
    nombrando la corrida que la arreglo.

POR QUE UNA ISSUE Y NO UN WEBHOOK

No hay entorno alojado (D-05) y el equipo no tiene un canal con secreto. Una
issue se verifica sin credenciales, queda como rastro en el repositorio y usa el
mismo permiso `issues: write` que el CI ya tiene para cerrar issues en `dev`.

LO QUE LA ALERTA NO AFIRMA

El riesgo de esta historia es el de I-29: **decir la verdad sobre lo que se midio
y mentir sobre lo que significa.** Aca la alerta declara **lo que leyo** -que
corrida, que conclusion devolvio la API, que trabajos terminaron en `failure`- y
nada mas. Una corrida cancelada no es un pipeline roto, y este programa no la
llama asi: no hace nada y lo dice.

USO

    python -m backend.alertas.alertar --corrida 33993914209 --simular
    python -m backend.alertas.alertar --corrida 33993914209

Sin `--simular` necesita un token en `GH_TOKEN` o `GITHUB_TOKEN`. Leer no lo
necesita: el repositorio es publico.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
REPOSITORIO = os.environ.get("GITHUB_REPOSITORY", "HumanoidCat/geoguardian")

#: Solo estas dos ramas alertan. Un fallo en una rama de trabajo es asunto de
#: quien la abrio y aparece en su Pull Request; alertarlo seria ruido, y una
#: alerta que se ignora no es una alerta.
RAMAS_VIGILADAS = ("dev", "main")

ETIQUETA = "alerta"
COLOR_ETIQUETA = "B60205"


class ErrorAlerta(Exception):
    """Falla que impide continuar."""


def _pedir(ruta: str, token: str | None = None, metodo: str = "GET", cuerpo: dict | None = None):
    url = ruta if ruta.startswith("http") else f"{API}{ruta}"
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    peticion = urllib.request.Request(url, data=datos, method=metodo)
    peticion.add_header("Accept", "application/vnd.github+json")
    peticion.add_header("User-Agent", "geoguardian-alertas")
    if token:
        peticion.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:
            return json.loads(respuesta.read() or "{}")
    except urllib.error.HTTPError as error:
        detalle = error.read().decode(errors="replace")[:300]
        raise ErrorAlerta(f"{metodo} {url} respondio {error.code}: {detalle}") from error


def leer_corrida(corrida: int, token: str | None = None) -> dict:
    """Lo que la API dice de esa corrida. Nada de esto se supone."""
    datos = _pedir(f"/repos/{REPOSITORIO}/actions/runs/{corrida}", token)
    return {
        "id": datos["id"],
        "numero": datos["run_number"],
        "flujo": datos["name"],
        "rama": datos["head_branch"],
        "conclusion": datos["conclusion"],
        "commit": datos["head_sha"][:7],
        "quien": (datos.get("triggering_actor") or datos.get("actor") or {}).get("login", "?"),
        "url": datos["html_url"],
        "evento": datos["event"],
    }


def trabajos_fallidos(corrida: int, token: str | None = None) -> list[str]:
    """Los nombres de los trabajos que terminaron en `failure`, y solo esos."""
    datos = _pedir(f"/repos/{REPOSITORIO}/actions/runs/{corrida}/jobs?per_page=100", token)
    return [t["name"] for t in datos.get("jobs", []) if t.get("conclusion") == "failure"]


def titulo_de(corrida: dict) -> str:
    """
    La clave de deduplicacion es el flujo y la rama, y vive en el titulo.

    Dos fallos del mismo flujo en la misma rama son el mismo problema hasta que
    alguien lo arregle; abrir una issue por corrida convertiria la alerta en el
    ruido que hace que se ignoren las alertas.
    """
    return f"[alerta] {corrida['flujo']} fallo en {corrida['rama']}"


def alerta_abierta(titulo: str, token: str | None = None) -> dict | None:
    issues = _pedir(f"/repos/{REPOSITORIO}/issues?state=open&labels={ETIQUETA}&per_page=100", token)
    for issue in issues:
        if issue["title"] == titulo and "pull_request" not in issue:
            return issue
    return None


def cuerpo_de(corrida: dict, fallidos: list[str]) -> str:
    lineas = [
        f"La corrida **{corrida['flujo']} #{corrida['numero']}** termino en "
        f"`{corrida['conclusion']}` sobre `{corrida['rama']}`.",
        "",
        f"- Commit: `{corrida['commit']}`",
        f"- Disparo: `{corrida['evento']}`, por @{corrida['quien']}",
        f"- Corrida: {corrida['url']}",
    ]
    if fallidos:
        lineas += ["", "Trabajos que terminaron en `failure`:", ""]
        lineas += [f"- `{t}`" for t in fallidos]
    else:
        lineas += [
            "",
            "**Ningun trabajo individual figura en `failure`.** La corrida fallo "
            "sin que la API atribuya el fallo a un trabajo: puede ser una "
            "cancelacion, un tiempo agotado o un error de la propia plataforma. "
            "Se dice asi porque es lo que se leyo.",
        ]
    lineas += [
        "",
        "---",
        "Abierta por `backend/alertas/alertar.py` (H12.3). Se cierra sola cuando "
        "una corrida posterior del mismo flujo y la misma rama termine bien.",
    ]
    return "\n".join(lineas)


def asegurar_etiqueta(token: str) -> None:
    """Crea `alerta` si no existe. Sin ella, abrir la issue falla con 422."""
    try:
        _pedir(f"/repos/{REPOSITORIO}/labels/{ETIQUETA}", token)
    except ErrorAlerta:
        _pedir(
            f"/repos/{REPOSITORIO}/labels",
            token,
            "POST",
            {
                "name": ETIQUETA,
                "color": COLOR_ETIQUETA,
                "description": "Fallo de pipeline o despliegue, avisado por H12.3",
            },
        )


#: Que hacer, segun como termino la corrida y si ya habia una alerta abierta.
#: Es una funcion pura a proposito: la decision se puede comprobar entera, sin
#: red y sin token, y el resto del programa solo la ejecuta.
def decidir(conclusion: str, hay_alerta_abierta: bool) -> str:
    """
    Devuelve `abrir`, `comentar`, `cerrar` o `nada`.

    **Solo `failure` y `success` significan algo.** Una corrida cancelada, o una
    saltada, no es un pipeline roto ni uno arreglado: el programa no la nombra
    de ninguna de las dos formas.
    """
    if conclusion == "failure":
        return "comentar" if hay_alerta_abierta else "abrir"
    if conclusion == "success":
        return "cerrar" if hay_alerta_abierta else "nada"
    return "nada"


def actuar(corrida: dict, fallidos: list[str], token: str | None, simular: bool) -> str:
    """Devuelve, en una linea, que se hizo o que se haria."""
    titulo = titulo_de(corrida)
    abierta = alerta_abierta(titulo, token)
    decision = decidir(corrida["conclusion"], abierta is not None)

    if decision == "abrir" or decision == "comentar":
        if decision == "comentar":
            accion = f"comentar en la issue #{abierta['number']} ya abierta"
            if not simular:
                _pedir(
                    f"/repos/{REPOSITORIO}/issues/{abierta['number']}/comments",
                    token,
                    "POST",
                    {"body": f"Volvio a fallar.\n\n{cuerpo_de(corrida, fallidos)}"},
                )
            return accion

        accion = f"abrir una issue nueva: {titulo!r}"
        if not simular:
            asegurar_etiqueta(token)
            nueva = _pedir(
                f"/repos/{REPOSITORIO}/issues",
                token,
                "POST",
                {"title": titulo, "body": cuerpo_de(corrida, fallidos), "labels": [ETIQUETA]},
            )
            accion += f" -> #{nueva['number']}"
        return accion

    if decision == "cerrar":
        accion = f"cerrar la issue #{abierta['number']}"
        if not simular:
            _pedir(
                f"/repos/{REPOSITORIO}/issues/{abierta['number']}/comments",
                token,
                "POST",
                {
                    "body": f"Arreglado por **{corrida['flujo']} #{corrida['numero']}** "
                    f"sobre `{corrida['rama']}`, commit `{corrida['commit']}`.\n\n"
                    f"{corrida['url']}",
                },
            )
            _pedir(
                f"/repos/{REPOSITORIO}/issues/{abierta['number']}",
                token,
                "PATCH",
                {"state": "closed", "state_reason": "completed"},
            )
        return accion

    if corrida["conclusion"] == "success":
        return "nada: termino bien y no habia alerta abierta"

    return (
        f"nada: la corrida termino en '{corrida['conclusion']}', que no es "
        "'failure' ni 'success'. No se llama roto a lo que no se midio roto"
    )


def principal(argumentos: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description="Alerta ante fallo de pipeline (H12.3)")
    analizador.add_argument("--corrida", type=int, required=True, help="id de la corrida")
    analizador.add_argument(
        "--simular", action="store_true", help="dice que haria y no escribe nada"
    )
    opciones = analizador.parse_args(argumentos)

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token and not opciones.simular:
        print("Falta GH_TOKEN o GITHUB_TOKEN. Para probar sin escribir: --simular", file=sys.stderr)
        return 2

    try:
        corrida = leer_corrida(opciones.corrida, token)
        print(
            f"{corrida['flujo']} #{corrida['numero']} · rama {corrida['rama']} · "
            f"conclusion {corrida['conclusion']} · commit {corrida['commit']}"
        )

        if corrida["rama"] not in RAMAS_VIGILADAS:
            print(
                f"No se alerta: {corrida['rama']} no es una rama vigilada "
                f"({', '.join(RAMAS_VIGILADAS)})."
            )
            return 0

        fallidos = trabajos_fallidos(opciones.corrida, token) if corrida["conclusion"] else []
        if fallidos:
            print(f"Trabajos en failure: {', '.join(fallidos)}")

        accion = actuar(corrida, fallidos, token, opciones.simular)
        print(f"{'Se haria' if opciones.simular else 'Hecho'}: {accion}")
        return 0

    except ErrorAlerta as error:
        print(f"FALLO: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(principal())
