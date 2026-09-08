"""
Verificador de H3.7. Dueno: Cesar.

USO

    docker compose up -d db
    python -m basedatos.aplicar_migraciones
    python -m basedatos.verificar_h3_7

**Necesita PostgreSQL**: los criterios son sobre lo que la tabla conserva en la
ida y la vuelta, y eso no se puede comprobar sin base. Lo que si se comprueba sin
ella -que los metodos salieron del registro de pendientes, que la bandera de
`comparar.py` es opcional- se comprueba igual y se dice cual es cual.

LAS FILAS DE PRUEBA SE BORRAN

Se escriben con la version `verificacion-h3.7`, que nadie mas usa, y se borran al
terminar aunque algun criterio falle. Una verificacion que deja basura en la
tabla que verifica no es una verificacion.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from basedatos.conexion import conectar  # noqa: E402
from contratos.enums import Algoritmo, TipoEvento  # noqa: E402
from contratos.esquemas import MetricasModelo  # noqa: E402

VERSION_PRUEBA = "verificacion-h3.7"

COLUMNAS_ESPERADAS = {
    "algoritmo",
    "tipo_evento",
    "version",
    "entrenado_en",
    "f1_macro",
    "precision_macro",
    "exhaustividad_macro",
    "matriz_confusion",
    "registrado_en",
    "supera_linea_base",
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


def _metricas(**cambios) -> MetricasModelo:
    base = {
        "algoritmo": Algoritmo.XGBOOST,
        "tipo_evento": TipoEvento.INCENDIO,
        "version": VERSION_PRUEBA,
        "entrenado_en": datetime.now().astimezone(),
        "f1_macro": 0.5,
        "precision_macro": 0.4,
        "exhaustividad_macro": 0.6,
        "matriz_confusion": [[10, 2], [3, 4]],
        "supera_linea_base": True,
    }
    return MetricasModelo(**{**base, **cambios})


def _de_prueba(repositorio) -> list[MetricasModelo]:
    return [m for m in repositorio.listar_metricas() if m.version == VERSION_PRUEBA]


def ca1_la_tabla_existe(resultado: Resultado, conexion) -> None:
    with conexion.cursor() as cursor:
        cursor.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'analitico' AND table_name = 'metrica'"
        )
        columnas = {fila[0] for fila in cursor.fetchall()}

    faltan = COLUMNAS_ESPERADAS - columnas
    resultado.marcar(
        "CA-1 la migracion 018 crea analitico.metrica con los campos del contrato",
        bool(columnas) and not faltan,
        f"{len(columnas)} columnas" + (f" · faltan {sorted(faltan)}" if faltan else ""),
    )


def ca2_idempotente(resultado: Resultado, repositorio) -> None:
    repositorio.guardar_metricas(_metricas(f1_macro=0.5))
    repositorio.guardar_metricas(_metricas(f1_macro=0.7))
    filas = [m for m in _de_prueba(repositorio) if m.algoritmo == Algoritmo.XGBOOST]

    correcto = len(filas) == 1 and filas[0].f1_macro == 0.7
    resultado.marcar(
        "CA-2 guardar dos veces la misma version actualiza, no duplica",
        correcto,
        f"{len(filas)} fila(s), f1_macro = {filas[0].f1_macro if filas else 'n/d'} "
        "tras guardar 0.5 y despues 0.7",
    )


def ca3_tres_estados(resultado: Resultado, repositorio) -> None:
    esperado = {
        Algoritmo.XGBOOST: True,
        Algoritmo.RANDOM_FOREST: False,
        Algoritmo.REGRESION_LOGISTICA: None,
    }
    for algoritmo, valor in esperado.items():
        repositorio.guardar_metricas(_metricas(algoritmo=algoritmo, supera_linea_base=valor))

    vuelto = {m.algoritmo: m.supera_linea_base for m in _de_prueba(repositorio)}
    errores = {a: (v, vuelto.get(a)) for a, v in esperado.items() if vuelto.get(a) is not v}

    resultado.marcar(
        "CA-3 supera_linea_base distingue nulo, falso y verdadero",
        not errores,
        "los tres vuelven como se guardaron; None sigue siendo None y no false"
        if not errores
        else f"cambiaron: {errores}",
    )


def ca4_no_calculada_no_es_cero(resultado: Resultado, repositorio) -> None:
    repositorio.guardar_metricas(
        _metricas(
            algoritmo=Algoritmo.LINEA_BASE,
            f1_macro=None,
            precision_macro=None,
            exhaustividad_macro=None,
            entrenado_en=None,
        )
    )
    fila = next(m for m in _de_prueba(repositorio) if m.algoritmo == Algoritmo.LINEA_BASE)
    vacios = (fila.f1_macro, fila.precision_macro, fila.exhaustividad_macro, fila.entrenado_en)

    resultado.marcar(
        "CA-4 una metrica no calculada vuelve None, no cero",
        all(v is None for v in vacios),
        f"f1, precision, exhaustividad y entrenado_en vuelven {vacios}",
    )


def ca5_matriz(resultado: Resultado, repositorio) -> None:
    matriz = [[10, 2], [3, 4]]
    repositorio.guardar_metricas(_metricas(algoritmo=Algoritmo.XGBOOST, matriz_confusion=matriz))
    fila = next(m for m in _de_prueba(repositorio) if m.algoritmo == Algoritmo.XGBOOST)

    igual = fila.matriz_confusion == matriz and all(
        isinstance(v, int) for renglon in (fila.matriz_confusion or []) for v in renglon
    )
    resultado.marcar(
        "CA-5 matriz_confusion vuelve con la misma forma y los mismos enteros",
        igual,
        f"se guardo {matriz} y volvio {fila.matriz_confusion}",
    )


def ca6_bandera_opcional(resultado: Resultado) -> None:
    fuente = (RAIZ / "backend" / "modelado" / "comparar.py").read_text(encoding="utf-8")
    opcional = '"--guardar",\n        action="store_true"' in fuente
    encerrado = "if args.guardar:" in fuente
    no_importa_arriba = (
        "from backend.api.repositorio_postgres import" not in fuente.split("def guardar(")[0]
    )

    resultado.marcar(
        "CA-6 comparar.py --guardar es opcional y sin ella se comporta igual",
        opcional and encerrado and no_importa_arriba,
        f"bandera opcional: {opcional} · persistencia encerrada en el if: {encerrado} · "
        f"el repositorio se importa dentro de la funcion, no al cargar el modulo: "
        f"{no_importa_arriba}",
    )


def ca7_fuera_de_pendientes(resultado: Resultado) -> None:
    from backend.api.repositorio_postgres import PENDIENTES
    from backend.api.test_repositorio_postgres import LLAMADAS_PENDIENTES

    salieron = "guardar_metricas" not in PENDIENTES and "listar_metricas" not in PENDIENTES
    coinciden = set(LLAMADAS_PENDIENTES) == set(PENDIENTES)

    resultado.marcar(
        "CA-7 los dos metodos salen de PENDIENTES y la prueba los deja de esperar rotos",
        salieron and coinciden,
        f"quedan pendientes: {sorted(PENDIENTES)} · el mapa de la prueba coincide: {coinciden}",
    )


def limpiar(conexion) -> int:
    with conexion.cursor() as cursor:
        cursor.execute("DELETE FROM analitico.metrica WHERE version = %s", (VERSION_PRUEBA,))
        return cursor.rowcount


def principal() -> int:
    from backend.api.repositorio_postgres import RepositorioPostgres

    resultado = Resultado()
    ca6_bandera_opcional(resultado)
    ca7_fuera_de_pendientes(resultado)

    conexion = conectar(autocommit=True)
    repositorio = RepositorioPostgres(conexion=conexion)
    try:
        ca1_la_tabla_existe(resultado, conexion)
        ca2_idempotente(resultado, repositorio)
        ca3_tres_estados(resultado, repositorio)
        ca4_no_calculada_no_es_cero(resultado, repositorio)
        ca5_matriz(resultado, repositorio)
    finally:
        borradas = limpiar(conexion)
        conexion.close()

    todo = resultado.imprimir()
    print(f"\nFilas de prueba borradas: {borradas}")
    print("Los siete criterios cumplen." if todo else "Hay criterios que fallan.")
    print("CA-8 se declara: esta historia no decide que estimador escribe analitico.riesgo.")
    return 0 if todo else 1


if __name__ == "__main__":
    raise SystemExit(principal())
