"""
Verificador del repositorio contra PostgreSQL. Dueno: Cesar. Historia H6.2, issue #63.

Cubre CA-1 a CA-7. La Definition of Done en maquina limpia se verifica por fuera.

POR QUE ESTE VERIFICADOR NO REIMPLEMENTA LAS COMPROBACIONES

Las pruebas viven en `backend/api/test_repositorio_postgres.py`. Este verificador
las EJECUTA en un subproceso y despues comprueba que las que sostienen cada
criterio existieron y pasaron. Reescribir aca la misma comprobacion daria dos
implementaciones del mismo control, y el dia que discrepen no habria forma de
saber cual tiene razon.

Lo que si hace por su cuenta es lo que no es una prueba unitaria: la sustitucion
de la implementacion (CA-5) y correr el verificador de H6.1 (CA-7).

POR QUE LAS PRUEBAS CORREN CON EL PUERTO APUNTANDO A LA NADA

CA-2 dice "sin base de datos". Que las pruebas pasen con la base levantada no
demuestra nada: podrian estar usandola. El subproceso se lanza con
POSTGRES_HOST_LOCAL y POSTGRES_PORT apuntando a un puerto donde no escucha nadie,
asi que cualquier conexion real fallaria o colgaria. Si pasan igual, es que no la
necesitan.

DONDE VIVE LA PRUEBA

En `backend/api/` y no en `backend/tests/`, que es de Luna. Por eso el CI no la
recoge y por eso este verificador la invoca. Ver la evidencia de H6.2.

USO

    python -m backend.api.verificar_h62
    python backend/api/verificar_h62.py
"""

from __future__ import annotations

import inspect
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Ver el mismo bloque en verificar_h61.py: sin esto el modulo no se puede
# invocar por ruta, solo con `python -m`. Deuda de SC-03, saldada en H6.2.
RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
if str(RAIZ_REPOSITORIO) not in sys.path:
    sys.path.insert(0, str(RAIZ_REPOSITORIO))

from backend.api import dependencias  # noqa: E402
from backend.api import repositorio_postgres as modulo  # noqa: E402
from backend.api.repositorio_postgres import PENDIENTES, RepositorioPostgres  # noqa: E402
from backend.api.test_repositorio_postgres import ConexionFalsa  # noqa: E402
from contratos.enums import ModoOperacion  # noqa: E402
from contratos.repositorio import Repositorio  # noqa: E402

RAIZ_API = Path(__file__).resolve().parent
RUTA_PRUEBAS = RAIZ_API / "test_repositorio_postgres.py"
RUTA_VERIFICADOR_H61 = RAIZ_API / "verificar_h61.py"

TIEMPO_MAXIMO = 180

PATRON_PRUEBA = re.compile(r"::(?P<nombre>test_\w+)(?P<parametro>\[[^\]]*\])?\s+(?P<estado>\w+)")


@dataclass
class Resultado:
    criterio: str
    titulo: str
    cumple: bool
    detalle: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Correr la suite una sola vez                                                 #
# --------------------------------------------------------------------------- #


@dataclass
class Corrida:
    """
    Resultado de una corrida de pytest.

    `pasaron` y `fallaron` son conjuntos de NOMBRES de funcion; `ejecuciones` es
    cuantos casos corrieron. Los dos numeros son distintos y se guardan aparte a
    proposito: una prueba parametrizada es un nombre y diez ejecuciones, y
    reportar 18 donde pytest dice 27 subdeclara el trabajo comprobado. La cifra
    va a una evidencia, asi que tiene que decir que cuenta.
    """

    codigo: int
    pasaron: set[str]
    fallaron: set[str]
    ejecuciones_ok: int
    ejecuciones_mal: int
    salida: str
    expiro: bool = False

    @property
    def total(self) -> int:
        return self.ejecuciones_ok + self.ejecuciones_mal

    def resumen(self) -> str:
        return (
            f"{self.ejecuciones_ok} ejecuciones de {len(self.pasaron)} pruebas"
            if not self.fallaron
            else (
                f"{self.ejecuciones_ok} ejecuciones en verde y {self.ejecuciones_mal} en rojo,"
                f" sobre {len(self.pasaron) + len(self.fallaron)} pruebas"
            )
        )


def correr_pruebas_sin_base() -> Corrida:
    entorno = dict(os.environ)
    # Puerto 1: privilegiado y sin nadie escuchando. Si alguna prueba abriera una
    # conexion real, no la conseguiria.
    entorno["POSTGRES_HOST_LOCAL"] = "127.0.0.1"
    entorno["POSTGRES_PORT"] = "1"

    try:
        proceso = subprocess.run(
            [sys.executable, "-m", "pytest", str(RUTA_PRUEBAS), "-v"],
            cwd=str(RAIZ_REPOSITORIO),
            env=entorno,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIEMPO_MAXIMO,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return Corrida(
            codigo=-1,
            pasaron=set(),
            fallaron=set(),
            ejecuciones_ok=0,
            ejecuciones_mal=0,
            salida="",
            expiro=True,
        )

    salida = (proceso.stdout or "") + (proceso.stderr or "")
    pasaron: set[str] = set()
    fallaron: set[str] = set()
    ejecuciones_ok = 0
    ejecuciones_mal = 0
    for linea in salida.splitlines():
        encontrado = PATRON_PRUEBA.search(linea)
        if not encontrado:
            continue
        nombre = encontrado.group("nombre")
        if encontrado.group("estado") == "PASSED":
            pasaron.add(nombre)
            ejecuciones_ok += 1
        elif encontrado.group("estado") in ("FAILED", "ERROR"):
            fallaron.add(nombre)
            ejecuciones_mal += 1

    return Corrida(
        codigo=proceso.returncode,
        pasaron=pasaron,
        fallaron=fallaron,
        ejecuciones_ok=ejecuciones_ok,
        ejecuciones_mal=ejecuciones_mal,
        salida=salida,
    )


def apoyado_en(corrida: Corrida, criterio: str, titulo: str, nombres: list[str]) -> Resultado:
    """
    Un criterio se cumple si TODAS sus pruebas existieron y pasaron.

    Que una prueba no aparezca es tan malo como que falle: significa que el
    criterio quedo sin cubrir, y un verificador que no distinga esas dos cosas
    da por bueno un criterio que nadie comprobo.
    """
    detalle: list[str] = []
    ok = True
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


# --------------------------------------------------------------------------- #
# CA-2 - las pruebas corren sin base de datos                                  #
# --------------------------------------------------------------------------- #


def ca2_sin_base(corrida: Corrida) -> Resultado:
    """
    La evidencia fuerte no es que una prueba pase: es DONDE corrio toda la suite.

    Se apoya en tres cosas, y la primera es la que vale: las 27 pruebas pasaron
    con POSTGRES_PORT=1, un puerto donde no escucha nadie. Cualquier conexion
    real habria fallado o habria colgado en el reintento de `conectar`, que es
    justamente lo que el tiempo maximo de este verificador detecta.
    """
    base = apoyado_en(
        corrida,
        "CA-2",
        "Las pruebas corren sin base de datos",
        ["test_construir_con_un_doble_no_llama_a_conectar"],
    )

    detalle = [
        f"  [ok ] {corrida.resumen()}, con POSTGRES_HOST_LOCAL=127.0.0.1 y"
        " POSTGRES_PORT=1, donde no escucha nadie",
        *base.detalle,
    ]

    fuente = RUTA_PRUEBAS.read_text(encoding="utf-8")
    if re.search(r"^from basedatos|^import basedatos", fuente, re.M):
        base.cumple = False
        detalle.append("  [MAL] la prueba importa basedatos directamente")
    else:
        detalle.append("  [ok ] la prueba no importa `basedatos`: la conexion entra por el doble")

    base.detalle = detalle
    return base


# --------------------------------------------------------------------------- #
# CA-5 - sustituir la implementacion no toca ningun endpoint                   #
# --------------------------------------------------------------------------- #


def ca5_sustitucion() -> Resultado:
    """
    Se comprueba en el proceso, con la conexion falsa.

    `_repositorio_postgres()` construye un `RepositorioPostgres()` sin argumentos,
    que abriria una conexion real. Se sustituye `conectar` por una que devuelve el
    doble: asi se comprueba la eleccion de implementacion, que es lo que el
    criterio pide, sin necesitar la base.
    """
    detalle: list[str] = []
    ok = True

    original_conectar = modulo.conectar
    original_variable = os.environ.get(dependencias.VARIABLE_REPOSITORIO)

    try:
        modulo.conectar = lambda *_a, **_k: ConexionFalsa()
        dependencias._repositorio_postgres.cache_clear()
        dependencias._repositorio_simulado.cache_clear()

        os.environ[dependencias.VARIABLE_REPOSITORIO] = "postgres"
        elegido = dependencias.obtener_repositorio()
        if isinstance(elegido, RepositorioPostgres):
            detalle.append("  [ok ] GEOGUARDIAN_REPOSITORIO=postgres elige RepositorioPostgres")
        else:
            ok = False
            detalle.append(f"  [MAL] con postgres devolvio {type(elegido).__name__}")

        modo = dependencias.modo_de(elegido)
        if modo is ModoOperacion.REAL:
            detalle.append("  [ok ] /salud declararia modo real, deducido de la implementacion")
        else:
            ok = False
            detalle.append(f"  [MAL] el modo deducido fue {modo}")

        dependencias._repositorio_postgres.cache_clear()
        os.environ[dependencias.VARIABLE_REPOSITORIO] = ""
        por_omision = dependencias.obtener_repositorio()
        if isinstance(por_omision, RepositorioPostgres):
            ok = False
            detalle.append("  [MAL] el valor por omision ya no es el simulado; rompe el visor")
        else:
            detalle.append(
                f"  [ok ] sin la variable sigue el simulado ({type(por_omision).__name__}),"
                " que es deliberado hasta que existan las tablas que faltan"
            )
    finally:
        modulo.conectar = original_conectar
        dependencias._repositorio_postgres.cache_clear()
        dependencias._repositorio_simulado.cache_clear()
        if original_variable is None:
            os.environ.pop(dependencias.VARIABLE_REPOSITORIO, None)
        else:
            os.environ[dependencias.VARIABLE_REPOSITORIO] = original_variable

    fuente_rutas = (RAIZ_API / "rutas.py").read_text(encoding="utf-8")
    if "RepositorioPostgres" in fuente_rutas:
        ok = False
        detalle.append("  [MAL] rutas.py nombra la implementacion concreta")
    else:
        detalle.append("  [ok ] rutas.py no nombra RepositorioPostgres: no se toco ningun endpoint")

    return Resultado("CA-5", "Sustituir la implementacion no toca ningun endpoint", ok, detalle)


# --------------------------------------------------------------------------- #
# CA-7 - las dos deudas de SC-03                                               #
# --------------------------------------------------------------------------- #


def ca7_deudas_sc03() -> Resultado:
    """Corre el verificador de H6.1 POR RUTA, que es la mitad de la deuda."""
    detalle: list[str] = []
    ok = True

    try:
        proceso = subprocess.run(
            [sys.executable, str(RUTA_VERIFICADOR_H61)],
            cwd=str(RAIZ_REPOSITORIO),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIEMPO_MAXIMO,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return Resultado(
            "CA-7",
            "Las dos deudas de SC-03 quedan saldadas",
            False,
            [f"  [MAL] verificar_h61.py no termino en {TIEMPO_MAXIMO} s"],
        )

    salida = (proceso.stdout or "") + (proceso.stderr or "")

    if "No module named" in salida:
        ok = False
        detalle.append("  [MAL] invocado por ruta falla al importar: el arreglo del path no esta")
    elif proceso.returncode == 0:
        detalle.append("  [ok ] verificar_h61.py corre invocado por ruta y sale con codigo 0")
    else:
        ok = False
        detalle.append(f"  [MAL] verificar_h61.py salio con codigo {proceso.returncode}")

    for criterio, que_comprueba in (("CA-12", "idempotencia"), ("CA-13", "monotonia")):
        if f"{criterio} " in salida and "NO CUMPLE" not in salida:
            detalle.append(f"  [ok ] {criterio} presente y en verde: {que_comprueba}")
        else:
            ok = False
            detalle.append(f"  [MAL] {criterio} ausente o en rojo: {que_comprueba}")

    return Resultado("CA-7", "Las dos deudas de SC-03 quedan saldadas", ok, detalle)


# --------------------------------------------------------------------------- #


def main() -> int:
    print("Verificacion del repositorio PostgreSQL de H6.2 (issue #63)")
    print("=" * 74)

    if not RUTA_PRUEBAS.exists():
        print(f"FALLA: no existe {RUTA_PRUEBAS}")
        return 2

    print("Corriendo la suite con el puerto de la base apuntando a la nada.")
    relativa = RUTA_PRUEBAS.relative_to(RAIZ_REPOSITORIO).as_posix()
    # La ruta relativa a la raiz y no el nombre suelto: esta linea se pega en la
    # evidencia y tiene que ser el comando que de verdad corre desde ahi.
    print(f"    $ python -m pytest {relativa} -v")
    corrida = correr_pruebas_sin_base()

    if corrida.expiro:
        print(f"\nFALLA: la suite no termino en {TIEMPO_MAXIMO} s.")
        print("Una prueba esta intentando conectarse a la base y esperando el reintento.")
        return 2
    if corrida.total == 0:
        print("\nFALLA: no se recogio ninguna prueba. Salida de pytest:")
        print(corrida.salida[-2000:])
        return 2

    print(f"  {corrida.resumen()}")

    resultados = [
        apoyado_en(
            corrida,
            "CA-1",
            "RepositorioPostgres cumple el protocolo completo",
            [
                "test_implementa_los_dieciseis_metodos_del_protocolo",
                "test_las_firmas_coinciden_con_las_del_protocolo",
            ],
        ),
        ca2_sin_base(corrida),
        apoyado_en(
            corrida,
            "CA-3",
            "Los pendientes fallan nombrando la tabla y la historia",
            [
                "test_la_tabla_de_pendientes_cubre_exactamente_los_metodos_que_fallan",
                "test_un_pendiente_falla_en_vez_de_devolver_vacio",
                "test_los_pendientes_los_atrapa_un_except_generico",
            ],
        ),
        apoyado_en(
            corrida,
            "CA-4",
            "Cada escritura ocurre dentro de su propia transaccion",
            [
                "test_guardar_mediciones_escribe_dentro_de_la_transaccion",
                "test_guardar_focos_escribe_dentro_de_la_transaccion",
                "test_dos_guardados_abren_dos_transacciones",
                "test_guardar_una_lista_vacia_no_abre_ninguna_transaccion",
                "test_las_lecturas_no_abren_transaccion",
            ],
        ),
        ca5_sustitucion(),
        apoyado_en(
            corrida,
            "CA-6",
            "Los dias sin dato vuelven como nulos, no ausentes",
            [
                "test_los_dias_sin_medicion_vuelven_con_nulos_y_no_ausentes",
                "test_el_sql_de_mediciones_genera_el_rango_y_une_por_la_izquierda",
            ],
        ),
        ca7_deudas_sc03(),
    ]

    # La suite entera tiene que estar en verde, no solo las pruebas citadas: una
    # prueba que falla y que ningun criterio cita sigue siendo un defecto.
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
    print(f"Metodos pendientes declarados: {len(PENDIENTES)} de {len(_metodos_del_protocolo())}")

    fallidos = [r for r in resultados if not r.cumple]
    if fallidos:
        print("NO CUMPLEN: " + ", ".join(r.criterio for r in fallidos))
        return 1

    print("Los siete criterios se cumplen.")
    print("Falta la Definition of Done en maquina limpia, que verifica otra persona.")
    return 0


def _metodos_del_protocolo() -> list[str]:
    return [
        nombre
        for nombre, _ in inspect.getmembers(Repositorio, inspect.isfunction)
        if not nombre.startswith("_")
    ]


if __name__ == "__main__":
    raise SystemExit(main())
