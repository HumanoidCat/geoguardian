"""Criterios de aceptacion del cierre de H3.6: la regla de D-39 y la tuberia.

Los criterios 1 a 7 de H3.6 -el arnes- viven en `verificar_h36.py` y siguen
corriendo en el CI. Este guion cubre lo que faltaba para cerrar la historia:
que la tabla **decida** con una regla fija y que la tuberia **escriba** lo que
la tabla decidio. Son los criterios 8 a 15 de
`docs/evidencias/objetivos/H3.6-criterios-aceptacion.md`; el 16 y el 17 van
contra la base y se documentan en la evidencia.

Todo sin base ni CSV real: la regla se prueba con tablas construidas a mano
para cada rama, y el repositorio con la conexion falsa de las pruebas de H6.2.

   8. Gana el primero cuando gana fuera del ruido.
   9. En empate tecnico, el mas simple dentro del ruido del primero.
  10. La trivial nunca escribe, ni siendo primera.
  11. Nadie escribe bajo el piso; si nadie lo alcanza, None con motivo.
  12. «Fuera del ruido» es ventaja > rango, exactamente: igual cuenta como empate.
  13. Regresion y climatologica entregan probabilidades coherentes con predecir().
  14. La probabilidad de la climatologica es la tasa de ALTO de la celda.
  15. Los tres metodos del repositorio: SQL, transaccion, None sin fila, un Riesgo por distrito.
  15b. El guion produce filas validas con datos sinteticos, sin tocar la base.

Uso:
    python -m backend.modelado.verificar_h36_tuberia
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.api.repositorio_postgres import PENDIENTES, RepositorioPostgres  # noqa: E402
from backend.api.test_repositorio_postgres import ConexionFalsa  # noqa: E402
from backend.modelado.comparar import (  # noqa: E402
    PISO,
    SIMPLICIDAD,
    Observacion,
    Resultado,
    elegir_escritor,
)
from backend.modelado.estimar_riesgo import decidir, filas_a_escribir  # noqa: E402
from backend.modelado.linea_base import LineaBaseClimatologica  # noqa: E402
from backend.modelado.regresion_logistica import RegresionLogistica  # noqa: E402
from backend.modelado.verificar_h33 import Resultado as Criterios  # noqa: E402
from backend.modelado.verificar_h33 import datos_sinteticos  # noqa: E402
from contratos.enums import Algoritmo, NivelRiesgo, TipoEvento  # noqa: E402
from contratos.esquemas import Riesgo  # noqa: E402


def fila(nombre: str, por_pliegue: list[float]) -> Resultado:
    media = sum(por_pliegue) / len(por_pliegue)
    return Resultado(nombre, por_pliegue, media, 0.0, 0)


def tabla(*filas_: Resultado) -> list[Resultado]:
    return sorted(filas_, key=lambda r: -r.media)


def verificar() -> Criterios:  # noqa: PLR0915 - es una lista de criterios
    r = Criterios()
    print("\nCriterios de aceptacion del cierre de H3.6 (D-39 y la tuberia)\n")

    # ------------------------------------------------------------------ 8
    t = tabla(
        fila("xgboost", [0.60, 0.61, 0.59, 0.60, 0.60]),  # media 0.60, rango 0.02
        fila("climatologica", [0.40, 0.41, 0.39, 0.40, 0.40]),
        fila(PISO, [0.30, 0.30, 0.30, 0.30, 0.30]),
    )
    quien, motivo = elegir_escritor(t)
    r.comprobar(
        "8. gana el primero cuando gana fuera del ruido", quien == "xgboost", f"{quien}: {motivo}"
    )
    r.comprobar("   y el motivo lo dice", motivo.startswith("gana fuera del ruido"), motivo)

    # ------------------------------------------------------------------ 9
    t = tabla(
        fila("xgboost", [0.36, 0.36, 0.36, 0.39, 0.38]),  # media 0.37, rango 0.03
        fila("regresion logistica", [0.355, 0.355, 0.355, 0.355, 0.355]),
        fila("climatologica", [0.35, 0.35, 0.35, 0.35, 0.35]),
        fila(PISO, [0.30, 0.30, 0.30, 0.30, 0.30]),
    )
    quien, motivo = elegir_escritor(t)
    r.comprobar(
        "9. en empate tecnico escribe el mas simple dentro del ruido del primero",
        quien == "climatologica",
        f"{quien}: {motivo}",
    )
    t = tabla(
        fila("xgboost", [0.36, 0.36, 0.36, 0.39, 0.38]),
        fila("regresion logistica", [0.355, 0.355, 0.355, 0.355, 0.355]),
        fila("climatologica", [0.32, 0.32, 0.32, 0.32, 0.32]),  # fuera del ruido: 0.32 < 0.34
        fila(PISO, [0.30, 0.30, 0.30, 0.30, 0.30]),
    )
    quien, _ = elegir_escritor(t)
    r.comprobar(
        "   y uno mas simple pero fuera del ruido del primero no cuenta",
        quien == "regresion logistica",
        f"eligio {quien}",
    )

    # ------------------------------------------------------------------ 10
    t = tabla(
        fila(PISO, [0.50, 0.50, 0.50, 0.50, 0.50]),
        fila("random forest", [0.50, 0.50, 0.50, 0.50, 0.50]),
    )
    quien, _ = elegir_escritor(t)
    r.comprobar(
        "10. la trivial nunca escribe, ni siendo primera",
        quien == "random forest",
        f"eligio {quien}",
    )
    r.comprobar("    y no figura en el orden de simplicidad", PISO not in SIMPLICIDAD)

    # ------------------------------------------------------------------ 11
    t = tabla(
        fila(PISO, [0.33, 0.33, 0.33, 0.33, 0.33]),
        fila("climatologica", [0.27, 0.27, 0.27, 0.27, 0.27]),
    )
    quien, motivo = elegir_escritor(t)
    r.comprobar(
        "11. nadie escribe bajo el piso: sequia queda sin fila", quien is None, f"eligio {quien}"
    )
    r.comprobar("    y el motivo nombra el piso", "piso" in motivo and "0.330" in motivo, motivo)

    # ------------------------------------------------------------------ 12
    t = tabla(
        fila("xgboost", [0.38, 0.38, 0.38, 0.40, 0.40]),  # media 0.388, rango 0.02
        fila("climatologica", [0.368, 0.368, 0.368, 0.368, 0.368]),  # ventaja 0.02 = rango
        fila(PISO, [0.30, 0.30, 0.30, 0.30, 0.30]),
    )
    quien, _ = elegir_escritor(t)
    r.comprobar(
        "12. ventaja igual al rango cuenta como empate: es la regla de CA-5, no otra",
        quien == "climatologica",
        f"eligio {quien}",
    )

    # ------------------------------------------------------------------ 13
    filas, caracteristicas = datos_sinteticos(TipoEvento.LLUVIA_INTENSA)
    obs = [Observacion(c, f, caracteristicas[(c, f)]) for c, f, _ in filas[:400]]
    eti = [n["lluvia_intensa"] for _, _, n in filas[:400]]
    incompleta = Observacion("50801", filas[0][1], {"pp_acum3": 90.0})
    regresion = RegresionLogistica().ajustar(obs, eti)
    mezcla = [*obs[:30], incompleta]
    niveles = regresion.predecir(mezcla)
    distribuciones = regresion.probabilidades(mezcla)
    coherente = all(
        (n is None and d is None) or (n is not None and d is not None and n == max(d, key=d.get))
        for n, d in zip(niveles, distribuciones, strict=True)
    )
    r.comprobar(
        "13. la regresion entrega probabilidades coherentes con predecir(), y None donde no predice",
        coherente and distribuciones[-1] is None and niveles[-1] is None,
    )

    # ------------------------------------------------------------------ 14
    entrenamiento = [
        ("50801", date(2020, 3, d), NivelRiesgo.ALTO if d <= 3 else NivelRiesgo.BAJO)
        for d in range(1, 11)
    ]
    entrenamiento += [("50801", date(2020, 4, d), NivelRiesgo.BAJO) for d in range(1, 11)]
    clima = LineaBaseClimatologica().ajustar(entrenamiento)
    marzo = clima.distribucion("50801", date(2021, 3, 15))
    abril = clima.distribucion("50801", date(2021, 4, 15))
    r.comprobar(
        "14. la probabilidad de la climatologica es la tasa de ALTO de la celda",
        marzo is not None
        and abs(marzo[NivelRiesgo.ALTO] - 0.3) < 1e-12
        and abril[NivelRiesgo.ALTO] == 0.0,
        f"marzo {marzo}, abril {abril}",
    )
    r.comprobar(
        "    y una celda sin dato no se inventa",
        clima.distribucion("50801", date(2021, 7, 1)) is None
        and clima.predecir("50801", date(2021, 7, 1)) is None,
    )

    # ------------------------------------------------------------------ 15
    conexion = ConexionFalsa()
    repo = RepositorioPostgres(conexion=conexion)
    riesgo = Riesgo(
        codigo_distrito="50801",
        fecha=date(2025, 1, 1),
        tipo_evento=TipoEvento.INCENDIO,
        nivel=NivelRiesgo.ALTO,
        probabilidad=0.42,
        algoritmo=Algoritmo.LINEA_BASE,
        version_modelo="climatologica@2026-09-03",
    )
    enviadas = repo.guardar_riesgos([riesgo, riesgo])
    sql, params = next(s[1:] for s in conexion.sentencias() if s[0] == "executemany")
    r.comprobar(
        "15. guardar_riesgos: dos filas, dentro de UNA transaccion, con ON CONFLICT sobre la clave natural",
        enviadas == 2
        and conexion.eventos()[:3] == ["abre_transaccion", "abre_cursor", "executemany"]
        and "ON CONFLICT (codigo_distrito, fecha, tipo_evento)" in sql
        and "IS DISTINCT FROM" in sql
        and params[0]["algoritmo"] == "linea_base_climatologica"
        and params[0]["nivel"] == "alto",
        f"eventos {conexion.eventos()}",
    )
    r.comprobar(
        "    y los tres ya no estan en PENDIENTES",
        not ({"guardar_riesgos", "obtener_riesgo", "obtener_riesgos_por_fecha"} & set(PENDIENTES)),
        f"PENDIENTES={sorted(PENDIENTES)}",
    )
    vacio = RepositorioPostgres(conexion=ConexionFalsa(resultados=[[]]))
    r.comprobar(
        "    obtener_riesgo devuelve None sin fila, no un riesgo inventado",
        vacio.obtener_riesgo("50801", date(2025, 1, 1), TipoEvento.INCENDIO) is None,
    )
    con_fila = RepositorioPostgres(
        conexion=ConexionFalsa(
            resultados=[
                [
                    (
                        "50801",
                        date(2025, 1, 1),
                        "incendio",
                        "alto",
                        0.42,
                        "linea_base_climatologica",
                        "v",
                        None,
                    )
                ]
            ]
        )
    )
    leido = con_fila.obtener_riesgo("50801", date(2025, 1, 1), TipoEvento.INCENDIO)
    r.comprobar(
        "    y con fila devuelve un Riesgo del contrato, con probabilidad como float",
        leido is not None
        and leido.nivel is NivelRiesgo.ALTO
        and leido.probabilidad == 0.42
        and leido.algoritmo is Algoritmo.LINEA_BASE,
    )
    ocho = RepositorioPostgres(
        conexion=ConexionFalsa(
            resultados=[
                [
                    (
                        "50801",
                        date(2025, 1, 1),
                        "incendio",
                        "alto",
                        0.42,
                        "linea_base_climatologica",
                        "v",
                        None,
                    ),
                    ("50802", date(2025, 1, 1), "incendio", None, None, None, None, None),
                ]
            ]
        )
    )
    por_fecha = ocho.obtener_riesgos_por_fecha(date(2025, 1, 1), TipoEvento.INCENDIO)
    sql_fecha = next(s[1] for s in ocho._conexion.sentencias() if s[0] == "execute")
    r.comprobar(
        "    obtener_riesgos_por_fecha: un Riesgo por distrito, con nivel None donde no hay fila",
        len(por_fecha) == 2
        and por_fecha[0].nivel is NivelRiesgo.ALTO
        and por_fecha[1].nivel is None
        and por_fecha[1].probabilidad is None
        and "LEFT JOIN analitico.riesgo" in sql_fecha
        and "geo.distrito" in sql_fecha,
        f"{[p.nivel for p in por_fecha]}",
    )

    # ------------------------------------------------------------------ 15b
    hoy = date(2026, 9, 3)
    decision = decidir(TipoEvento.LLUVIA_INTENSA, filas, caracteristicas, hoy)
    producidas = filas_a_escribir(decision, filas, caracteristicas, hoy + timedelta(days=7))
    ultimo = max(f for _, f, _ in filas)
    r.comprobar(
        "15b. con la senal sintetica la tabla elige a un escritor y el guion produce filas",
        decision.escritor is not None and len(producidas) > 0,
        f"escritor {decision.escritor}: {decision.motivo}",
    )
    r.comprobar(
        "     cada fila trae nivel, P(alto) en [0, 1], algoritmo y version_modelo",
        all(
            p.nivel is not None
            and p.probabilidad is not None
            and 0.0 <= p.probabilidad <= 1.0
            and p.algoritmo is not None
            and p.version_modelo
            and p.explicacion is None
            for p in producidas
        ),
    )
    escribe_futuro = any(p.fecha > ultimo for p in producidas)
    necesita = decision.escritor not in ("climatologica",)
    r.comprobar(
        "     y solo un escritor de calendario escribe mas alla del ultimo dia con datos",
        escribe_futuro != necesita,
        f"escritor {decision.escritor}; escribe futuro: {escribe_futuro}",
    )
    r.comprobar(
        "     ninguna fila sale de sequia mientras D-34 siga en pie",
        decidir(TipoEvento.SEQUIA, filas, caracteristicas, hoy).escritor is None
        or not filas_a_escribir(
            decidir(TipoEvento.SEQUIA, filas, caracteristicas, hoy), filas, caracteristicas, hoy
        ),
    )
    return r


def main() -> int:
    resultado = verificar()
    print(f"\n{resultado.hechos - len(resultado.fallos)} de {resultado.hechos} criterios")
    if resultado.fallos:
        print("\nNO se cumplen:")
        for f in resultado.fallos:
            print(f"  - {f}")
        print()
        return 1
    print("\nEl cierre de H3.6 cumple sus criterios de aceptacion.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
