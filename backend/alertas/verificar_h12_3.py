"""
Verificador de H12.3. Dueno: Cesar.

USO

    python -m backend.alertas.verificar_h12_3

**No necesita token ni escribe nada.** El repositorio es publico, asi que la
parte que lee corridas reales funciona sin credenciales; la parte que decide es
una funcion pura y se comprueba entera.

LO QUE ESTE VERIFICADOR NO PUEDE COMPROBAR

Que la alerta se abra, se comente y se cierre **de verdad** exige escribir en el
repositorio, y eso se hizo a mano contra corridas reales: las issues quedan como
evidencia, etiquetadas `alerta` y cerradas. Aca se comprueba que el numero de
esas issues este declarado en la evidencia, no se vuelve a escribir.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
FLUJO = RAIZ / ".github" / "workflows" / "alerta.yml"
CI = RAIZ / ".github" / "workflows" / "ci.yml"
CD = RAIZ / ".github" / "workflows" / "cd.yml"
EVIDENCIA = RAIZ / "docs" / "evidencias" / "arquitectura-software" / "H12.3-alertas.md"

#: Corridas reales contra las que se comprueba. Se eligen a proposito de tres
#: tipos distintos: un despliegue caido, un CI caido, y un fallo en una rama de
#: trabajo que **no** debe alertar.
CORRIDAS = {
    "cd_fallido_en_main": 33993914209,
    "ci_fallido_en_dev": 33952847254,
    "ci_fallido_en_rama_de_trabajo": 34074136037,
    "cd_bueno_en_main": 34084872237,
}


class Resultado:
    def __init__(self) -> None:
        self.filas: list[tuple[str, bool, str]] = []

    def marcar(self, criterio: str, cumple: bool, detalle: str = "") -> None:
        self.filas.append((criterio, cumple, detalle))

    def imprimir(self) -> bool:
        for criterio, cumple, detalle in self.filas:
            print(f"{criterio}: {'CUMPLE' if cumple else 'FALLA'}")
            if detalle:
                print(f"    {detalle}")
        return all(cumple for _, cumple, _ in self.filas)


def ca1_no_esta_cableado(resultado: Resultado) -> None:
    """
    El flujo escucha desde afuera, y ni ci.yml ni cd.yml saben que existe.

    **No compara hashes.** Un hash congelado responde "¿cambio este archivo
    desde que lo copie?", no "¿esta historia lo toco?", y el dia que Alejandro
    edite `ci.yml` por su cuenta diria que fue H12.3. Que los dos archivos no se
    tocan se ve en el diff del Pull Request, que es donde eso es cierto.
    """
    texto = FLUJO.read_text(encoding="utf-8")
    escucha = "workflow_run:" in texto and "workflows: [CI, CD]" in texto
    permisos = "issues: write" in texto and "actions: read" in texto

    ajenos = {}
    for ruta in (CI, CD):
        contenido = ruta.read_text(encoding="utf-8")
        menciones = [
            palabra
            for palabra in ("alerta.yml", "backend.alertas", "backend/alertas")
            if palabra in contenido
        ]
        if menciones:
            ajenos[ruta.name] = menciones

    resultado.marcar(
        "CA-1 el flujo escucha a CI y CD desde afuera, sin estar cableado en ellos",
        escucha and permisos and not ajenos,
        f"escucha CI y CD: {escucha} · permisos minimos declarados: {permisos} · "
        f"ci.yml y cd.yml lo nombran: {ajenos or 'no'}",
    )


def ca2_la_alerta_trae_lo_necesario(resultado: Resultado, alertar) -> None:
    corrida = alertar.leer_corrida(CORRIDAS["cd_fallido_en_main"])
    fallidos = alertar.trabajos_fallidos(CORRIDAS["cd_fallido_en_main"])
    cuerpo = alertar.cuerpo_de(corrida, fallidos)

    exigidos = {
        "flujo": corrida["flujo"],
        "rama": corrida["rama"],
        "commit": corrida["commit"],
        "quien": corrida["quien"],
        "enlace": corrida["url"],
        "trabajo que fallo": fallidos[0] if fallidos else "",
    }
    faltan = [nombre for nombre, valor in exigidos.items() if valor and valor not in cuerpo]

    resultado.marcar(
        "CA-2 la alerta trae flujo, rama, commit, quien, enlace y que trabajo fallo",
        not faltan,
        f"sobre la corrida real {corrida['flujo']} #{corrida['numero']}: "
        f"{', '.join(exigidos)} presentes"
        if not faltan
        else f"faltan en el cuerpo: {faltan}",
    )


def ca3_ca4_decision(resultado: Resultado, alertar) -> None:
    """La tabla entera de decisiones, sin red: `decidir` es una funcion pura."""
    tabla = {
        ("failure", False): "abrir",
        ("failure", True): "comentar",
        ("success", True): "cerrar",
        ("success", False): "nada",
        ("cancelled", True): "nada",
        ("cancelled", False): "nada",
        ("skipped", True): "nada",
        ("timed_out", False): "nada",
    }
    errores = {
        entrada: (esperado, alertar.decidir(*entrada))
        for entrada, esperado in tabla.items()
        if alertar.decidir(*entrada) != esperado
    }

    resultado.marcar(
        "CA-3 y CA-4 deduplica al fallar de nuevo y cierra sola al pasar",
        not errores,
        f"las {len(tabla)} combinaciones de conclusion y alerta abierta deciden bien; "
        "cancelled, skipped y timed_out no se llaman ni roto ni arreglado"
        if not errores
        else f"decisiones equivocadas: {errores}",
    )


def ca5_solo_ramas_vigiladas(resultado: Resultado, alertar) -> None:
    trabajo = alertar.leer_corrida(CORRIDAS["ci_fallido_en_rama_de_trabajo"])
    dev = alertar.leer_corrida(CORRIDAS["ci_fallido_en_dev"])

    correcto = (
        trabajo["rama"] not in alertar.RAMAS_VIGILADAS and dev["rama"] in alertar.RAMAS_VIGILADAS
    )

    resultado.marcar(
        "CA-5 solo alerta en dev y main",
        correcto,
        f"{trabajo['flujo']} #{trabajo['numero']} en '{trabajo['rama']}' queda fuera; "
        f"{dev['flujo']} #{dev['numero']} en '{dev['rama']}' entra",
    )


def ca6_demostrado_de_verdad(resultado: Resultado) -> None:
    if not EVIDENCIA.exists():
        resultado.marcar("CA-6 demostrado contra corridas reales", False, "falta la evidencia")
        return

    texto = EVIDENCIA.read_text(encoding="utf-8")
    # Solo las issues de alerta, que en la evidencia se escriben como
    # **Issue #284**. Buscar "issue #" a secas tambien traia la #80, que es la
    # de la historia: contar eso como evidencia seria afirmar mas de lo medido.
    issues = set(re.findall(r"\*\*Issue #(\d+)\*\*", texto))
    nombra_corridas = all(str(i) in texto for i in CORRIDAS.values())

    resultado.marcar(
        "CA-6 demostrado contra corridas reales, con las issues como evidencia",
        bool(issues) and nombra_corridas,
        f"issues declaradas en la evidencia: {sorted(issues) or 'ninguna'} · "
        f"nombra las cuatro corridas usadas: {nombra_corridas}",
    )


def ca7_no_es_h12_1_ni_h12_2(resultado: Resultado) -> None:
    fuente = (RAIZ / "backend" / "alertas" / "alertar.py").read_text(encoding="utf-8")
    toca_base = any(
        palabra in fuente for palabra in ("psycopg", "conectar(", "bitacora_etl", "basedatos.")
    )

    resultado.marcar(
        "CA-7 (declarado) no usa la base ni dibuja pantallas",
        not toca_base,
        "no importa psycopg ni basedatos, y no menciona control.bitacora_etl: "
        "la alerta sirve cuando la base esta caida, que es cuando hace falta"
        if not toca_base
        else "toca la base, y no deberia",
    )


def principal() -> int:
    sys.path.insert(0, str(RAIZ))
    from backend.alertas import alertar

    resultado = Resultado()
    ca1_no_esta_cableado(resultado)
    ca2_la_alerta_trae_lo_necesario(resultado, alertar)
    ca3_ca4_decision(resultado, alertar)
    ca5_solo_ramas_vigiladas(resultado, alertar)
    ca6_demostrado_de_verdad(resultado)
    ca7_no_es_h12_1_ni_h12_2(resultado)

    todo = resultado.imprimir()
    print()
    print("Los siete criterios cumplen." if todo else "Hay criterios que fallan.")
    return 0 if todo else 1


if __name__ == "__main__":
    raise SystemExit(principal())
