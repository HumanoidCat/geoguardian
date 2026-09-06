"""Escribe `analitico.riesgo` con el estimador que la tabla elige. Historia H3.6, D-39.

===========================================================================
QUE HACE, EN ORDEN
===========================================================================

  1. Corre la tabla comparativa completa de H3.6 -los cinco estimadores, los
     cinco pliegues de H3.2, F1-macro de D-10- sobre las etiquetas y la matriz
     reales. Es la misma funcion que `python -m backend.modelado.comparar`;
     no hay una segunda tabla.
  2. Por evento, **elige al escritor con la regla de D-39** (`elegir_escritor`):
     gana fuera del ruido, o el mas simple dentro del ruido; la trivial nunca;
     nadie bajo el piso. No hay un nombre de algoritmo escrito en este guion.
  3. Ajusta al escritor con **todo** el dato del evento -ya no hay nada que
     evaluar; lo que se escribe es la estimacion que el sistema sirve- y
     predice una fila por distrito y dia: nivel y P(nivel = alto) por D-21.
  4. Las escribe por el repositorio, en lotes, con `ON CONFLICT` sobre la clave
     natural. Correrlo dos veces no cambia ninguna fila.

===========================================================================
QUE FECHAS SE ESCRIBEN
===========================================================================

Las del rango de etiquetas -donde hay dato que respalde la estimacion- y, si el
escritor solo necesita el calendario (la climatologica), tambien hasta
`--hasta`, que por omision es hoy mas siete dias: el horizonte del sistema. Un
escritor que necesita la matriz no puede escribir un dia sin matriz, y por eso
para «hoy» dependeria de la ingesta con cadencia de H1.14.

Sequia no se escribe mientras D-34 siga en pie: la regla lo decide sola, porque
la climatologica queda bajo el piso; si un dia dejara de estarlo, escribiria, y
eso seria una senal para revisar D-34, no un error.

===========================================================================
LO QUE DECLARA CADA FILA
===========================================================================

    algoritmo        el escritor, en el vocabulario del contrato (`Algoritmo`)
    version_modelo   escritor@fecha-de-corrida f1=<media> <veredicto corto>
    probabilidad     P(nivel = alto), D-21; None si el escritor no la tiene
    explicacion      NULL: es H4.2, y la climatologica no tiene que explicar

Uso:
    python -m backend.modelado.estimar_riesgo               escribe
    python -m backend.modelado.estimar_riesgo --sin-escribir   solo decide y cuenta
    python -m backend.modelado.estimar_riesgo --evento incendio
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado.afinar import fabricas  # noqa: E402
from backend.modelado.comparar import (  # noqa: E402
    COLUMNA,
    DISTRITOS_CON_INCENDIO,
    Observacion,
    Resultado,
    comparar,
    elegir_escritor,
    veredicto,
)
from backend.modelado.evaluar_linea_base import leer  # noqa: E402
from contratos.enums import Algoritmo, NivelRiesgo, TipoEvento  # noqa: E402
from contratos.esquemas import Riesgo  # noqa: E402

#: Del nombre en la tabla al vocabulario del contrato. La trivial no esta:
#: D-39 dice que nunca escribe, y si alguien la pidiera aca fallaria con KeyError,
#: que es lo correcto.
ALGORITMO_DE: dict[str, Algoritmo] = {
    "climatologica": Algoritmo.LINEA_BASE,
    "regresion logistica": Algoritmo.REGRESION_LOGISTICA,
    "random forest": Algoritmo.RANDOM_FOREST,
    "xgboost": Algoritmo.XGBOOST,
}

HORIZONTE_DIAS = 7


def retirar_de_otros_escritores(evento: TipoEvento, algoritmo: Algoritmo) -> int:
    """
    Borra las filas del evento que dejo escritas un escritor anterior.

    POR QUE HACE FALTA, Y POR QUE NO HIZO FALTA HASTA HOY

    Las filas se escriben con `ON CONFLICT` sobre la clave natural, asi que
    correr dos veces no cambia nada: el escritor pisa sus propias filas. Pero
    **no pisa las que ya no cubre**. Mientras el escritor de un evento no
    cambiara, eso no se notaba.

    Cambio por primera vez el 2026-09-05, al aplicar D-42: en incendio la
    climatologica quedo fuera de la banda por 0.002 y paso a escribir la
    regresion logistica, que **necesita la matriz** y por lo tanto llega menos
    lejos en el calendario. Resultado medido:

        incendio  linea_base_climatologica   1962 filas  1991-01-01 .. 2026-09-10
        incendio  regresion_logistica       37149 filas  1991-01-30 .. 2024-12-24

    Dos escritores para el mismo evento, y las fechas recientes -incluida hoy,
    que es la que el visor muestra por omision- servidas por un estimador que
    D-39 ya no elige. Es la incidencia I-37.

    El borrado dispara `riesgo_auditoria_tg`, que es `AFTER DELETE OR UPDATE`:
    la historia de H1.13 guarda que estas filas existieron y cuando dejaron de
    existir. Eso es deseable y por eso no se apaga.
    """
    from basedatos.conexion import conectar

    with conectar(autocommit=True) as conexion, conexion.cursor() as cursor:
        cursor.execute(
            "DELETE FROM analitico.riesgo WHERE tipo_evento = %s AND algoritmo <> %s",
            (evento.value, algoritmo.value),
        )
        return cursor.rowcount


def contar_del_evento(evento: TipoEvento) -> int:
    from basedatos.conexion import conectar

    with conectar() as conexion, conexion.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM analitico.riesgo WHERE tipo_evento = %s", (evento.value,)
        )
        return cursor.fetchone()[0]


TAMANIO_LOTE = 5000


@dataclass
class Decision:
    evento: TipoEvento
    escritor: str | None
    motivo: str
    tabla: list[Resultado]
    version: str | None = None


def decidir(evento: TipoEvento, filas: list, caracteristicas: dict, hoy: date) -> Decision:
    """La tabla y la regla de D-39, sin escribir nada."""
    # `fabricas` y no `estimadores_disponibles`: trae los hiperparametros que
    # H3.8 eligio para este evento, si los hay. Con AFINADOS vacio devuelve
    # exactamente lo mismo que antes.
    tabla = comparar(evento, filas, fabricas(evento, bool(caracteristicas)), caracteristicas)
    escritor, motivo = elegir_escritor(tabla)
    version = None
    if escritor is not None:
        fila = next(r for r in tabla if r.nombre == escritor)
        corto = "gana" if motivo.startswith("gana") else "empate-tecnico"
        version = f"{escritor.replace(' ', '-')}@{hoy.isoformat()} f1={fila.media:.3f} {corto}"
    return Decision(evento, escritor, motivo, tabla, version)


def filas_a_escribir(
    decision: Decision,
    filas: list,
    caracteristicas: dict,
    hasta: date,
) -> list[Riesgo]:
    """Ajusta al escritor con todo el dato del evento y produce las filas."""
    if decision.escritor is None:
        return []
    evento = decision.evento
    columna = COLUMNA[evento]
    propias = (
        [f for f in filas if f[0] in DISTRITOS_CON_INCENDIO]
        if evento is TipoEvento.INCENDIO
        else filas
    )
    distritos = sorted({c for c, _, _ in propias})

    def observacion(codigo: str, fecha: date) -> Observacion:
        return Observacion(codigo, fecha, caracteristicas.get((codigo, fecha), {}))

    entrenamiento = [
        (observacion(c, f), n[columna]) for c, f, n in propias if n[columna] is not None
    ]
    # La MISMA puerta que armo la tabla: el que se evaluo y el que escribe no
    # pueden ser dos modelos distintos.
    modelo = fabricas(evento, bool(caracteristicas))[decision.escritor]()
    modelo.ajustar([o for o, _ in entrenamiento], [e for _, e in entrenamiento])

    # Las fechas: las del dato, y hasta `hasta` si el escritor solo mira el calendario.
    fechas = sorted({f for _, f, _ in propias})
    if not getattr(modelo, "necesita_caracteristicas", True) and fechas:
        dia = fechas[-1] + timedelta(days=1)
        while dia <= hasta:
            fechas.append(dia)
            dia += timedelta(days=1)

    objetivo = [observacion(c, f) for c in distritos for f in fechas]
    niveles = modelo.predecir(objetivo)
    distribuciones = modelo.probabilidades(objetivo)

    salida: list[Riesgo] = []
    for o, nivel, d in zip(objetivo, niveles, distribuciones, strict=True):
        if nivel is None:
            continue  # sin estimacion no hay fila: D-07
        salida.append(
            Riesgo(
                codigo_distrito=o.codigo_distrito,
                fecha=o.fecha,
                tipo_evento=evento,
                nivel=nivel,
                probabilidad=(
                    round(float(d.get(NivelRiesgo.ALTO, 0.0)), 4) if d is not None else None
                ),
                algoritmo=ALGORITMO_DE[decision.escritor],
                version_modelo=decision.version,
                explicacion=None,
            )
        )
    return salida


def resumen(riesgos: list[Riesgo]) -> str:
    cuenta = Counter(r.nivel.value for r in riesgos if r.nivel)
    return ", ".join(f"{n}={cuenta[n]}" for n in ("bajo", "medio", "alto") if cuenta[n])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--etiquetas", type=Path, default=RAIZ / "datos" / "procesados" / "etiquetas.csv"
    )
    p.add_argument(
        "--caracteristicas",
        type=Path,
        default=RAIZ / "datos" / "procesados" / "caracteristicas.csv",
    )
    p.add_argument("--evento", choices=[e.value for e in TipoEvento], default=None)
    p.add_argument("--hasta", type=date.fromisoformat, default=None, help="por omision, hoy + 7")
    p.add_argument("--sin-escribir", action="store_true", help="decide y cuenta, no toca la base")
    args = p.parse_args()

    if not args.etiquetas.exists() or not args.caracteristicas.exists():
        print("\nHacen falta las dos: etiquetas.csv y caracteristicas.csv. Con la base levantada:")
        print("    python -m backend.modelado.generar_etiquetas")
        print("    python -m backend.modelado.generar_caracteristicas\n")
        return 1

    from backend.modelado.generar_caracteristicas import leer as leer_caracteristicas

    filas = leer(args.etiquetas)
    caracteristicas = leer_caracteristicas(args.caracteristicas)
    hoy = date.today()
    hasta = args.hasta or hoy + timedelta(days=HORIZONTE_DIAS)
    eventos = [TipoEvento(args.evento)] if args.evento else list(TipoEvento)

    print("\nEstimacion de riesgo · H3.6 · regla de D-39")
    print(
        f"  filas de etiquetas {len(filas)} · matriz {len(caracteristicas)} filas · hasta {hasta}"
    )
    if args.sin_escribir:
        print("  MODO --sin-escribir: no se toca la base\n")

    repositorio = None
    total = 0
    for evento in eventos:
        decision = decidir(evento, filas, caracteristicas, hoy)
        print(f"\n{evento.value.upper()}")
        for r in decision.tabla:
            print(f"  {r.nombre:22} F1-macro {r.media:.3f}  rango {r.rango:.3f}")
        print(f"  veredicto de la tabla   {veredicto(decision.tabla)}")
        print(f"  escribe                 {decision.escritor or 'NADIE'}: {decision.motivo}")
        if decision.escritor is None:
            # NADIE escribe. Las filas viejas NO se borran solas: un borrado
            # masivo disparado por un veredicto que puede moverse con el ruido
            # seria peor que el problema. Se avisa y lo decide una persona.
            if not args.sin_escribir:
                viejas = contar_del_evento(evento)
                if viejas:
                    print(
                        f"  AVISO                   quedan {viejas} filas de una corrida anterior "
                        f"y ningun estimador las respalda hoy. No se borran solas: decidilo a mano."
                    )
            continue
        riesgos = filas_a_escribir(decision, filas, caracteristicas, hasta)
        print(f"  filas                   {len(riesgos)} ({resumen(riesgos)})")
        print(f"  version_modelo          {decision.version}")
        if args.sin_escribir or not riesgos:
            continue
        if repositorio is None:
            from backend.api.repositorio_postgres import RepositorioPostgres

            repositorio = RepositorioPostgres()
        for i in range(0, len(riesgos), TAMANIO_LOTE):
            total += repositorio.guardar_riesgos(riesgos[i : i + TAMANIO_LOTE])
        print(f"  escritas                {len(riesgos)}")

        # Un evento, un escritor. Ver `retirar_de_otros_escritores` e I-37.
        retiradas = retirar_de_otros_escritores(evento, ALGORITMO_DE[decision.escritor])
        if retiradas:
            print(f"  retiradas               {retiradas} de un escritor anterior")

    if repositorio is not None:
        repositorio.cerrar()
    print(f"\n{'Enviadas a la base' if not args.sin_escribir else 'Sin escribir'}: {total} filas\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
