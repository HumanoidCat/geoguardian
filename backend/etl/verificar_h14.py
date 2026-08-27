"""
Verificador de la regla de imputacion. Dueno: Cesar. Historia H1.4.

Cubre CA-1 a CA-8. La Definition of Done en maquina limpia se verifica por fuera.

POR QUE NO REIMPLEMENTA LAS COMPROBACIONES

Las pruebas viven en `backend/etl/test_imputacion.py`. Este verificador las EJECUTA
en un subproceso y despues comprueba que las que sostienen cada criterio existieron
y pasaron. Reescribirlas aca daria dos implementaciones del mismo control, y el dia
que discrepen no habria forma de saber cual tiene razon.

Lo que si hace por su cuenta es CA-8: que los dos umbrales sean los que la fuente
citada declara, y que la advertencia de procedencia siga escrita. Eso no es una
prueba unitaria, es una comprobacion sobre el propio codigo.

**NO NECESITA BASE DE DATOS.** La regla es una funcion pura sobre listas.

USO

    python backend/etl/verificar_h14.py
    python -m backend.etl.verificar_h14
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
if str(RAIZ_REPOSITORIO) not in sys.path:
    sys.path.insert(0, str(RAIZ_REPOSITORIO))

from backend.etl import imputacion as modulo  # noqa: E402
from contratos.enums import MetodoImputacion  # noqa: E402

RUTA_PRUEBAS = Path(__file__).resolve().parent / "test_imputacion.py"
TIEMPO_MAXIMO = 180

PATRON_PRUEBA = re.compile(r"::(?P<nombre>test_\w+)(?:\[[^\]]*\])?\s+(?P<estado>\w+)")


@dataclass
class Resultado:
    criterio: str
    titulo: str
    cumple: bool
    detalle: list[str] = field(default_factory=list)


@dataclass
class Corrida:
    """
    `pasaron` son NOMBRES de funcion; `ejecuciones_ok` son casos.

    Los dos numeros se guardan aparte a proposito: una prueba parametrizada es un
    nombre y varias ejecuciones, y reportar el numero equivocado subdeclara lo que
    se comprobo. Paso en el verificador de H6.2 y se corrige de entrada aca.
    """

    pasaron: set[str]
    fallaron: set[str]
    ejecuciones_ok: int
    ejecuciones_mal: int
    salida: str
    expiro: bool = False

    def resumen(self) -> str:
        if self.fallaron:
            return f"{self.ejecuciones_ok} ejecuciones en verde y {self.ejecuciones_mal} en rojo"
        return f"{self.ejecuciones_ok} ejecuciones de {len(self.pasaron)} pruebas"


def correr_pruebas() -> Corrida:
    try:
        proceso = subprocess.run(
            [sys.executable, "-m", "pytest", str(RUTA_PRUEBAS), "-v"],
            cwd=str(RAIZ_REPOSITORIO),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIEMPO_MAXIMO,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return Corrida(set(), set(), 0, 0, "", expiro=True)

    salida = (proceso.stdout or "") + (proceso.stderr or "")
    pasaron, fallaron = set(), set()
    ok = mal = 0
    for linea in salida.splitlines():
        encontrado = PATRON_PRUEBA.search(linea)
        if not encontrado:
            continue
        if encontrado.group("estado") == "PASSED":
            pasaron.add(encontrado.group("nombre"))
            ok += 1
        elif encontrado.group("estado") in ("FAILED", "ERROR"):
            fallaron.add(encontrado.group("nombre"))
            mal += 1
    return Corrida(pasaron, fallaron, ok, mal, salida)


def apoyado_en(corrida: Corrida, criterio: str, titulo: str, nombres: list[str]) -> Resultado:
    """
    Un criterio se cumple si TODAS sus pruebas existieron y pasaron.

    Que una prueba no aparezca es tan malo como que falle: significa que el criterio
    quedo sin cubrir, y un verificador que no distinga esas dos cosas da por bueno
    un criterio que nadie comprobo.
    """
    detalle, ok = [], True
    for nombre in nombres:
        if nombre in corrida.pasaron:
            detalle.append(f"  [ok ] {nombre}")
        elif nombre in corrida.fallaron:
            ok = False
            detalle.append(f"  [MAL] {nombre} fallo")
        else:
            ok = False
            detalle.append(f"  [MAL] {nombre} no aparecio en la corrida")
    return Resultado(criterio, titulo, ok, detalle)


def ca8_umbrales_citados() -> Resultado:
    """
    Los dos umbrales tienen que ser los de la fuente, y la fuente tiene que estar.

    Este proyecto no inventa umbrales: los de incendio salen de la Tabla 10 del
    manual de MODIS y los de lluvia del ETCCDI. Si alguien mueve estas dos
    constantes sin cambiar la cita, el codigo diria una cosa y el documento otra.
    """
    detalle, ok = [], True
    fuente = Path(modulo.__file__).read_text(encoding="utf-8")

    for nombre, esperado in (
        ("DIAS_CONSECUTIVOS_QUE_INUTILIZAN", 5),
        ("FALTANTES_QUE_INUTILIZAN_EL_MES", 11),
    ):
        valor = getattr(modulo, nombre)
        if valor == esperado:
            detalle.append(f"  [ok ] {nombre} = {valor}, como WMO-No. 1203 4.4.1(a)")
        else:
            ok = False
            detalle.append(f"  [MAL] {nombre} = {valor} y la fuente citada dice {esperado}")

    if "WMO-No. 1203" in fuente and "4.4.1(a)" in fuente:
        detalle.append("  [ok ] el modulo cita el documento y la seccion")
    else:
        ok = False
        detalle.append("  [MAL] el modulo no cita la fuente de sus umbrales")

    if "AVISO DE PROCEDENCIA" in fuente:
        detalle.append("  [ok ] conserva el aviso de que la cita no se leyo del PDF oficial")
    else:
        ok = False
        detalle.append("  [MAL] falta el aviso de procedencia de la cita")

    sin_uso = {MetodoImputacion.MEDIA_MOVIL, MetodoImputacion.CLIMATOLOGIA_MENSUAL}
    usados = {m for m in MetodoImputacion if f"MetodoImputacion.{m.name}" in fuente}
    if not (usados & sin_uso):
        detalle.append(
            "  [ok ] media_movil y climatologia_mensual siguen sin uso:"
            " elegirlos exigiria un corte que ninguna fuente sostiene"
        )
    else:
        ok = False
        detalle.append(
            f"  [MAL] el modulo usa {sorted(m.value for m in usados & sin_uso)} sin fuente"
        )

    return Resultado("CA-8", "Los umbrales son los de la fuente citada", ok, detalle)


def main() -> int:
    print("Verificacion de la regla de imputacion de H1.4 (D-22, D-07)")
    print("=" * 74)

    if not RUTA_PRUEBAS.exists():
        print(f"FALLA: no existe {RUTA_PRUEBAS}")
        return 2

    relativa = RUTA_PRUEBAS.relative_to(RAIZ_REPOSITORIO).as_posix()
    print(f"    $ python -m pytest {relativa} -v")
    corrida = correr_pruebas()

    if corrida.expiro:
        print(f"FALLA: la suite no termino en {TIEMPO_MAXIMO} s.")
        return 2
    if corrida.ejecuciones_ok + corrida.ejecuciones_mal == 0:
        print("FALLA: no se recogio ninguna prueba. Salida de pytest:")
        print(corrida.salida[-2000:])
        return 2

    print(f"  {corrida.resumen()}, sin base de datos: la regla es una funcion pura")

    resultados = [
        apoyado_en(
            corrida,
            "CA-1",
            "Un hueco de 1 a 4 dias se imputa por interpolacion lineal",
            ["test_un_hueco_de_hasta_cuatro_dias_se_imputa", "test_lo_que_no_es_hueco_no_se_toca"],
        ),
        apoyado_en(
            corrida,
            "CA-2",
            "Un hueco de 5 dias o mas no se imputa",
            [
                "test_un_hueco_de_cinco_dias_o_mas_no_se_imputa",
                "test_el_corte_esta_donde_lo_pone_la_omm",
            ],
        ),
        apoyado_en(
            corrida,
            "CA-3",
            "Once faltantes inutilizan el mes aunque los huecos sean cortos",
            [
                "test_once_huecos_de_un_dia_en_el_mismo_mes_no_se_imputan",
                "test_diez_huecos_de_un_dia_si_se_imputan",
            ],
        ),
        apoyado_en(
            corrida,
            "CA-4",
            "Toda imputacion queda marcada",
            ["test_ninguna_fila_sale_con_valor_imputado_y_sin_imputar"],
        ),
        apoyado_en(
            corrida,
            "CA-5",
            "Una serie de eventos no se imputa nunca",
            [
                "test_una_serie_de_eventos_no_se_imputa",
                "test_la_negativa_no_depende_del_largo_del_hueco",
            ],
        ),
        apoyado_en(
            corrida,
            "CA-6",
            "Un cero no es un hueco",
            ["test_una_serie_llena_de_ceros_sale_identica"],
        ),
        apoyado_en(
            corrida,
            "CA-7",
            "No se inventa fuera de los extremos",
            [
                "test_un_hueco_al_principio_no_se_imputa",
                "test_un_hueco_al_final_no_se_imputa",
                "test_extender_el_ultimo_valor_conocido_seria_inventar",
            ],
        ),
        ca8_umbrales_citados(),
    ]

    if corrida.fallaron:
        resultados.append(
            Resultado(
                "CA-0",
                "La suite completa pasa",
                False,
                [f"  [MAL] fallaron: {sorted(corrida.fallaron)}"],
            )
        )

    resultados.sort(key=lambda r: int(r.criterio.split("-")[1]))

    for r in resultados:
        print(f"\n{r.criterio} - {r.titulo} ... {'CUMPLE' if r.cumple else 'NO CUMPLE'}")
        for linea in r.detalle:
            print(linea)

    print("\n" + "=" * 74)
    fallidos = [r for r in resultados if not r.cumple]
    if fallidos:
        print("NO CUMPLEN: " + ", ".join(r.criterio for r in fallidos))
        return 1

    print("Los ocho criterios se cumplen.")
    print("La regla se probo contra huecos INYECTADOS y no observados: las series de")
    print("H1.1 no tienen ninguno. La limitacion la declara D-22 y no se disimula.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
