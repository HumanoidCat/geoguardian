"""
Medidor de la cache de la API. Dueno: Cesar. Historia H8.3, issue #65.

USO

    python -m backend.api.medir_cache

Necesita PostgreSQL levantado y las credenciales en .env, porque la unica
medicion que vale es contra la base real.

QUE MIDE HOY: LA LINEA BASE DE CA-1

Cuantas consultas a la base cuesta cada endpoint **sin cache**, y cuanto tarda.
Ese numero es el que decide que se cachea: lo que no repite trabajo no se
cachea, y la historia tiene que decir cuales quedaron fuera y por que.

COMO SE CUENTAN LAS CONSULTAS, Y POR QUE ASI

`RepositorioPostgres` recibe su conexion por parametro -H6.2 la dejo asi para
poder probarlo sin base-, de modo que alcanza con envolverla: `ConexionContadora`
devuelve cursores que suman uno cada vez que se llama a `execute`. No se parchea
psycopg ni se cuenta llamadas a metodos del repositorio: **se cuenta lo que
efectivamente sale hacia la base**, que es lo que la cache tiene que reducir.

La aplicacion se arma con `crear_aplicacion()` y el repositorio entra por
`dependency_overrides`, la misma costura de inyeccion que usa `dependencias.py`.
Ningun endpoint se entera.

LIMITE DECLARADO

Esto mide el proceso de prueba, no un despliegue: un solo trabajador, sin red de
por medio. Los tiempos sirven para comparar con y sin cache en la misma maquina,
no para prometer latencias de produccion. El techo por proceso y el efecto de
varios trabajadores son CA-8 y CA-9, y se miden aparte.
"""

from __future__ import annotations

import statistics
import sys
import time
from datetime import date, timedelta

REPETICIONES = 7


class CursorContador:
    """Cursor que delega todo y suma uno por cada `execute`."""

    def __init__(self, cursor, contador) -> None:
        self._cursor = cursor
        self._contador = contador

    def __enter__(self):
        self._cursor.__enter__()
        return self

    def __exit__(self, *excepcion):
        return self._cursor.__exit__(*excepcion)

    def execute(self, *argumentos, **nombrados):
        self._contador.consultas += 1
        return self._cursor.execute(*argumentos, **nombrados)

    def executemany(self, *argumentos, **nombrados):
        self._contador.consultas += 1
        return self._cursor.executemany(*argumentos, **nombrados)

    def __getattr__(self, nombre):
        return getattr(self._cursor, nombre)


class ConexionContadora:
    """
    Conexion que delega todo y lleva la cuenta de las consultas emitidas.

    No cambia el comportamiento: `transaction()`, `close()` y lo demas pasan
    tal cual a la conexion real.
    """

    def __init__(self, conexion) -> None:
        self._conexion = conexion
        self.consultas = 0

    def cursor(self, *argumentos, **nombrados):
        return CursorContador(self._conexion.cursor(*argumentos, **nombrados), self)

    def __getattr__(self, nombre):
        return getattr(self._conexion, nombre)


def _casos(repositorio):
    """
    Los seis endpoints con parametros que existen de verdad.

    El distrito sale de la base y el tipo de evento del enum del contrato: no se
    escribe ninguno a mano, para que esto no se rompa el dia que cambien.
    """
    from contratos.enums import TipoEvento

    distritos = repositorio.listar_distritos()
    if not distritos:
        raise SystemExit(
            "geo.distrito esta vacia: sin distritos no hay nada que medir.\n"
            "Corre la carga de H1.3 antes de esto."
        )
    codigo = distritos[0].codigo
    evento = next(iter(TipoEvento)).value

    hasta = date.today()
    desde = hasta - timedelta(days=29)

    return [
        ("/salud", "/salud", {}),
        ("/distritos", "/distritos", {}),
        (f"/distritos/{{codigo}}", f"/distritos/{codigo}", {}),
        (
            f"/distritos/{{codigo}}/mediciones (30 dias)",
            f"/distritos/{codigo}/mediciones",
            {"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        ),
        (
            f"/distritos/{{codigo}}/riesgo",
            f"/distritos/{codigo}/riesgo",
            {"fecha": hasta.isoformat(), "tipo_evento": evento},
        ),
        ("/riesgos", "/riesgos", {"fecha": hasta.isoformat(), "tipo_evento": evento}),
    ]


def _medir(cliente, contador, ruta, parametros):
    """Una llamada de calentamiento que se descarta, y luego las que cuentan."""
    respuesta = cliente.get(ruta, params=parametros)
    estado = respuesta.status_code

    consultas = []
    tiempos = []
    for _ in range(REPETICIONES):
        contador.consultas = 0
        arranque = time.perf_counter()
        respuesta = cliente.get(ruta, params=parametros)
        tiempos.append((time.perf_counter() - arranque) * 1000)
        consultas.append(contador.consultas)
        estado = respuesta.status_code

    return estado, consultas, tiempos


def principal() -> int:
        try:
        from fastapi.testclient import TestClient
    except ImportError as error:
        # El mensaje nombra la causa real. La primera version afirmaba "falta
        # httpx" ante CUALQUIER ImportError, y lo que fallaba era otra cosa: la
        # venv no estaba activa y httpx si estaba instalado. Es el mismo defecto
        # que corrige el PR del CA-4 de H6.3, cometido aqui mismo el mismo dia.
        print(
            f"No se pudo importar TestClient: {error}\n"
            "Si el prompt no empieza con (.venv), la venv no esta activa: "
            ".\\.venv\\Scripts\\Activate.ps1\n"
            "Si de verdad falta httpx: python -m pip install httpx==0.28.1",
            file=sys.stderr,
        )
        return 1

    from backend.api.aplicacion import crear_aplicacion
    from backend.api.dependencias import obtener_repositorio
    from backend.api.repositorio_postgres import RepositorioPostgres
    from basedatos.conexion import conectar

    contador = ConexionContadora(conectar(autocommit=True))
    repositorio = RepositorioPostgres(conexion=contador)

    aplicacion = crear_aplicacion()
    aplicacion.dependency_overrides[obtener_repositorio] = lambda: repositorio
    cliente = TestClient(aplicacion)

    casos = _casos(repositorio)

    print(f"Linea base sin cache · {REPETICIONES} repeticiones · {date.today().isoformat()}")
    print("La primera llamada de cada endpoint se descarta.")
    print()
    print(f"{'endpoint':<40} {'estado':>6} {'consultas':>10} {'mediana ms':>11} {'rango ms':>16}")
    print("-" * 87)

    for nombre, ruta, parametros in casos:
        estado, consultas, tiempos = _medir(cliente, contador, ruta, parametros)

        if len(set(consultas)) == 1:
            columna_consultas = str(consultas[0])
        else:
            # Que varie es informacion, no ruido: significa que el endpoint no
            # hace el mismo trabajo en cada llamada.
            columna_consultas = f"{min(consultas)}-{max(consultas)}"

        print(
            f"{nombre:<40} {estado:>6} {columna_consultas:>10} "
            f"{statistics.median(tiempos):>11.2f} "
            f"{min(tiempos):>7.2f}-{max(tiempos):<8.2f}"
        )

    print()
    print(
        "Consultas es cuantas veces se llamo a execute() contra PostgreSQL en UNA\n"
        "peticion. Un endpoint con dos consultas donde una valida el codigo de\n"
        "distrito esta pagando esa validacion en cada llamada."
    )

    repositorio.cerrar()
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())