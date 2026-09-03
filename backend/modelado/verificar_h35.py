"""Criterios de aceptacion de H3.5: XGBoost dentro de la tabla, y la tabla completa.

QUE COMPRUEBA, Y QUE NO

`backend/modelado/test_xgboost.py` cubre el estimador por dentro. Este guion
cubre el **cableado con el arnes de H3.6** y la **comparabilidad con H3.3 y
H3.4**: que entre en la tabla cuando debe, que no entre cuando no debe, que vea
lo mismo que los demas, que trate los nulos igual **aunque la libreria sepa
tratarlos distinto**, y que con el la tabla quede completa.

Corre sobre series construidas a mano, las mismas de `verificar_h33` y `verificar_h34`. No
necesita la base ni el CSV real: un criterio que solo se puede comprobar con
los datos de una maquina no es un criterio, es una anecdota. Los numeros reales
salen de `python -m backend.modelado.comparar` y van en la evidencia.

Los criterios son los de `docs/evidencias/objetivos/H3.5-criterios-aceptacion.md`,
escritos antes del codigo:

  1. Sin matriz, XGBoost NO entra y sigue listado con el motivo real.
  2. Con matriz entra, y PENDIENTES queda vacio: los tres de D-09 estan.
  3. Ve exactamente los mismos pliegues que los otros dos y las lineas base.
  4. Encuentra la senal que se le puso.
  5. No corre sobre la sequia (D-34); las lineas base si.
  6. Un pliegue de una sola clase se salta con motivo, no tumba la tabla.
  7. No imputa ni usa la rama de ausentes: la fila incompleta sale None.
  8. Invariante a escala: no hay ningun ajuste global escondido.
  9. Reproducible bit a bit, en probabilidades y con ruido.
 10. Las importancias se leen por nombre y suman 1.
 11. Las probabilidades respetan D-21 y coinciden con predecir().
 12. Trata los nulos exactamente igual que la regresion y el bosque.
 13. El peso por fila actua: con y sin pesos predicen distinto, en la direccion declarada.
 14. Con cinco filas, la tabla sigue sin declarar ganador dentro del ruido.

Uso:
    python -m backend.modelado.verificar_h35

Sale con codigo 1 si algun criterio no se cumple.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado.comparar import (  # noqa: E402
    CON_CARACTERISTICAS,
    DISPONIBLES,
    PENDIENTES,
    Observacion,
    comparar,
    estimadores_disponibles,
    pendientes,
    veredicto,
)
from backend.modelado.random_forest import BosqueAleatorio  # noqa: E402
from backend.modelado.regresion_logistica import RegresionLogistica  # noqa: E402
from backend.modelado.verificar_h33 import Resultado, datos_sinteticos  # noqa: E402
from backend.modelado.xgboost_ import XGBoostEstimador  # noqa: E402
from contratos.enums import NivelRiesgo, TipoEvento  # noqa: E402

NOMBRE = "xgboost"


def verificar() -> Resultado:  # noqa: PLR0915 - es una lista de criterios
    r = Resultado()
    print("\nCriterios de aceptacion de H3.5\n")

    filas, caracteristicas = datos_sinteticos(TipoEvento.LLUVIA_INTENSA)

    # ------------------------------------------------------------------ 1
    sin = estimadores_disponibles(False)
    r.comprobar(
        "1. sin matriz, xgboost NO entra en la tabla",
        NOMBRE not in sin and set(sin) == set(DISPONIBLES),
        f"quedo {sorted(sin)}",
    )
    motivo = pendientes(False).get(NOMBRE, "")
    r.comprobar(
        "   y sigue listado con el motivo real, no solo el numero de historia",
        "H3.5" in motivo
        and "caracteristicas.csv" in motivo
        and "generar_caracteristicas" in motivo,
        f"decia: {motivo!r}",
    )

    # ------------------------------------------------------------------ 2
    con = estimadores_disponibles(True)
    r.comprobar(
        "2. con matriz, xgboost entra en la tabla",
        NOMBRE in con and isinstance(con[NOMBRE](), XGBoostEstimador),
        f"quedo {sorted(con)}",
    )
    r.comprobar(
        "   y PENDIENTES queda vacio: los tres de D-09 estan en la tabla",
        not PENDIENTES
        and not pendientes(True)
        and {"regresion logistica", "random forest", "xgboost"} <= set(con),
        f"PENDIENTES={PENDIENTES}, pendientes(True)={pendientes(True)}",
    )

    # ------------------------------------------------------------------ 3 y 4
    resultados = comparar(TipoEvento.LLUVIA_INTENSA, filas, con, caracteristicas)
    largos = {x.nombre: len(x.por_pliegue) for x in resultados}
    r.comprobar(
        "3. ve exactamente los mismos pliegues que los otros dos y las lineas base",
        NOMBRE in largos and len(set(largos.values())) == 1 and largos[NOMBRE] > 0,
        f"largos por estimador: {largos}",
    )
    fila_x = next((x for x in resultados if x.nombre == NOMBRE), None)
    r.comprobar(
        "4. encuentra la senal que se le puso",
        fila_x is not None and fila_x.media > 0.9,
        f"F1-macro {fila_x.media if fila_x else 'sin fila'}; deberia ser casi 1",
    )

    # ------------------------------------------------------------------ 5
    filas_s, caract_s = datos_sinteticos(TipoEvento.SEQUIA)
    nombres = {x.nombre for x in comparar(TipoEvento.SEQUIA, filas_s, con, caract_s)}
    r.comprobar(
        "5. no corre sobre la sequia, que D-34 declara no modelable",
        NOMBRE not in nombres and not (nombres & set(CON_CARACTERISTICAS)),
        f"corrieron {sorted(nombres)}",
    )
    r.comprobar(
        "   y las lineas base si",
        nombres == set(DISPONIBLES),
        f"corrieron {sorted(nombres)}",
    )

    # ------------------------------------------------------------------ 6
    de_una_clase = [(c, f, dict.fromkeys(n, NivelRiesgo.BAJO)) for c, f, n in filas]
    try:
        resultados = comparar(TipoEvento.LLUVIA_INTENSA, de_una_clase, con, caracteristicas)
        sobrevivio = True
    except ValueError:
        sobrevivio = False
    r.comprobar(
        "6. un pliegue de una sola clase no tumba la tabla",
        sobrevivio,
        "la excepcion del estimador se propago y se perdio la comparacion entera",
    )
    if sobrevivio:
        saltados = next((x.saltados for x in resultados if x.nombre == NOMBRE), [])
        r.comprobar(
            "   y queda el motivo por el que se salto",
            bool(saltados) and "una sola clase" in saltados[0],
            f"motivos: {saltados}",
        )

    # ------------------------------------------------------------------ 7
    mitad = len(filas) // 2
    obs = [Observacion(c, f, caracteristicas[(c, f)]) for c, f, _ in filas[:mitad]]
    eti = [n["lluvia_intensa"] for _, _, n in filas[:mitad]]
    modelo = XGBoostEstimador().ajustar(obs, eti)

    incompletas = [Observacion(c, f, {"pp_acum3": 90.0}) for c, f, _ in filas[:50]]
    prediccion = modelo.predecir(incompletas)
    r.comprobar(
        "7. una observacion sin todas sus caracteristicas no se predice, ni por la rama de ausentes",
        all(p is None for p in prediccion),
        f"predijo {sum(1 for p in prediccion if p is not None)} de {len(prediccion)}",
    )
    r.comprobar(
        "   y el estimador lleva la cuenta de cuantas fueron",
        modelo.filas_sin_prediccion == len(incompletas),
        f"conto {modelo.filas_sin_prediccion}, se esperaban {len(incompletas)}",
    )

    # ------------------------------------------------------------------ 8
    por_diez = [
        Observacion(c, f, {k: v * 10 for k, v in o.caracteristicas.items()})
        for (c, f, _), o in zip(filas[:mitad], obs, strict=True)
    ]
    prediccion_a = modelo.predecir(obs)
    prediccion_b = XGBoostEstimador().ajustar(por_diez, eti).predecir(por_diez)
    r.comprobar(
        "8. invariante a escala: no hay ningun ajuste global escondido",
        prediccion_a == prediccion_b and not hasattr(modelo, "_escalador"),
        "la escala cambio alguna prediccion, o hay un escalador que no deberia existir",
    )

    # ------------------------------------------------------------------ 9
    # Se comprueba sobre clases que se solapan y comparando **probabilidades**,
    # por lo que H3.4 aprendio: sobre la senal separable el criterio no podia
    # fallar. Y hay una diferencia con el bosque que importa al sabotear:
    # en XGBoost `random_state=None` NO es aleatorio -la libreria usa semilla 0-
    # y sin submuestreo no hay nada aleatorio que sembrar. Para hacer caer este
    # criterio a proposito hubo que poner una semilla distinta en cada ajuste
    # **y** `subsample=0.5`; con solo quitar la semilla paso 21 de 21. Queda
    # dicho para que nadie crea que ese sabotaje prueba algo aqui.
    import random

    azar = random.Random(7)
    ruidosos = [float(azar.randrange(10)) for _ in range(400)]
    eti_ruido = [
        NivelRiesgo.ALTO if azar.random() < 0.06 * v else NivelRiesgo.BAJO for v in ruidosos
    ]
    obs_ruido = [
        Observacion("50801", f, {"pp_acum3": v, "tmax_media7": v / 3})
        for (_, f, _), v in zip(filas[:400], ruidosos, strict=True)
    ]
    primera = XGBoostEstimador().ajustar(obs_ruido, eti_ruido).probabilidades(obs_ruido)
    segunda = XGBoostEstimador().ajustar(obs_ruido, eti_ruido).probabilidades(obs_ruido)
    r.comprobar(
        "9. dos ajustes con los mismos datos dan las mismas probabilidades, aun con ruido",
        prediccion_a == XGBoostEstimador().ajustar(obs, eti).predecir(obs) and primera == segunda,
        "el estimador no es reproducible: no se puede comparar contra nada",
    )

    # ------------------------------------------------------------------ 10
    importancias = modelo.importancias
    columnas = sorted({k for o in obs for k in o.caracteristicas})
    r.comprobar(
        "10. las importancias se leen por nombre de columna",
        sorted(importancias) == columnas,
        f"claves {sorted(importancias)} contra columnas {columnas}",
    )
    r.comprobar(
        "    y suman 1",
        abs(sum(importancias.values()) - 1.0) < 1e-9,
        f"suman {sum(importancias.values())}",
    )

    # ------------------------------------------------------------------ 11
    mezcla = [*obs[:40], *incompletas[:10]]
    niveles = modelo.predecir(mezcla)
    distribuciones = modelo.probabilidades(mezcla)
    coinciden = all(
        (n is None and d is None) or (n is not None and d is not None and n == max(d, key=d.get))
        for n, d in zip(niveles, distribuciones, strict=True)
    )
    r.comprobar(
        "11. D-21: el nivel es la clase de mayor probabilidad, y None donde no se predice",
        coinciden and any(d is None for d in distribuciones),
        "predecir() y probabilidades() discrepan en alguna fila",
    )
    r.comprobar(
        "    y cada distribucion trae una entrada por clase y suma 1",
        all(
            d is None or (set(d) == set(modelo._clases) and abs(sum(d.values()) - 1) < 1e-6)
            for d in distribuciones
        ),
    )

    # ------------------------------------------------------------------ 12
    con_huecos = [
        Observacion(
            o.codigo_distrito,
            o.fecha,
            {"pp_acum3": o.caracteristicas["pp_acum3"]} if i % 3 == 0 else o.caracteristicas,
        )
        for i, o in enumerate(obs)
    ]
    x = XGBoostEstimador().ajustar(con_huecos, eti)
    b = BosqueAleatorio().ajustar(con_huecos, eti)
    g = RegresionLogistica().ajustar(con_huecos, eti)
    descartadas = {m.filas_descartadas_al_ajustar for m in (x, b, g)}
    huecos = [[p is None for p in m.predecir(con_huecos)] for m in (x, b, g)]
    sin_prediccion = {m.filas_sin_prediccion for m in (x, b, g)}
    r.comprobar(
        "12. trata los nulos exactamente igual que la regresion y el bosque: mismas filas fuera",
        len(descartadas) == 1
        and descartadas != {0}
        and huecos[0] == huecos[1] == huecos[2]
        and len(sin_prediccion) == 1,
        f"ajustar: {[m.filas_descartadas_al_ajustar for m in (x, b, g)]}; "
        f"predecir: {[m.filas_sin_prediccion for m in (x, b, g)]}",
    )

    # ------------------------------------------------------------------ 13
    # Los cajones repetidos de H3.4: una minoria de ALTO que nunca llega a la
    # mitad. Sin pesos nadie predice ALTO; con pesos, los cajones altos si.
    cajones_v = [float(azar.randrange(10)) for _ in range(500)]
    eti_caj = [
        NivelRiesgo.ALTO if azar.random() < 0.04 * v else NivelRiesgo.BAJO for v in cajones_v
    ]
    obs_caj = [
        Observacion("50801", f, {"pp_acum3": v, "tmax_media7": 1.0})
        for (_, f, _), v in zip(filas[:500], cajones_v, strict=True)
    ]
    cajones = [
        Observacion("50801", filas[i][1], {"pp_acum3": float(i), "tmax_media7": 1.0})
        for i in range(10)
    ]
    con_pesos = XGBoostEstimador(balancear=True).ajustar(obs_caj, eti_caj).predecir(cajones)
    sin_pesos = XGBoostEstimador(balancear=False).ajustar(obs_caj, eti_caj).predecir(cajones)
    r.comprobar(
        "13. el peso por fila actua, y en la direccion declarada",
        NivelRiesgo.ALTO not in sin_pesos and NivelRiesgo.ALTO in con_pesos,
        f"sin pesos: {[p.value for p in sin_pesos]}; con pesos: {[p.value for p in con_pesos]}",
    )

    # ------------------------------------------------------------------ 14
    resultados = comparar(TipoEvento.INCENDIO, filas, con, caracteristicas)
    if len(resultados) >= 2:
        primero, segundo = resultados[0], resultados[1]
        dictamen = veredicto(resultados)
        empatan = (primero.media - segundo.media) <= primero.rango
        r.comprobar(
            "14. con todas las filas del registro, sigue sin declarar ganador cuando la ventaja cabe en el ruido",
            len(resultados) == len(con) and ("empate tecnico" in dictamen) == empatan,
            f"{len(resultados)} filas; dictamen: {dictamen}",
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
    print("\nH3.5 cumple sus criterios de aceptacion.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
