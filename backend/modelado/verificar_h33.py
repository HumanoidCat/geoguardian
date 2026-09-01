"""Criterios de aceptacion de H3.3: la Regresion Logistica dentro de la tabla.

QUE COMPRUEBA, Y QUE NO

Las pruebas de `backend/tests/test_generar_caracteristicas.py` cubren la
**construccion** de la matriz. Este guion cubre el **cableado**: que el estimador
entre en la tabla cuando debe, que no entre cuando no debe, y que la comparacion
siga siendo justa.

Corre sobre series construidas a mano. No necesita la base ni el CSV real: un
criterio que solo se puede comprobar con los datos de una maquina no es un
criterio, es una anecdota.

  1. Sin matriz, la regresion NO entra y sigue listada con el motivo real.
  2. Con matriz, entra en la tabla.
  3. La sequia queda declarada NO MODELABLE por D-34, con su motivo.
  4. Y los estimadores que aprenden no corren sobre ella, aunque se pidan.
  5. Las lineas base SI corren sobre la sequia: no aprenden de episodios.
  6. Todos los estimadores ven **los mismos pliegues**.
  7. Un pliegue que no se puede ajustar se salta con motivo, no tumba la tabla.
  8. CA-6 de H3.2: el escalado se ajusta DENTRO del pliegue.
  9. Y no hay ningun ajuste global escondido: dos pliegues dan escalas distintas.
 10. Una observacion sin todas sus caracteristicas no se predice, y se cuenta.
 11. La tabla no declara ganador cuando la ventaja cabe dentro del ruido.

Uso:
    python -m backend.modelado.verificar_h33

Sale con codigo 1 si algun criterio no se cumple.
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado.comparar import (  # noqa: E402
    CON_CARACTERISTICAS,
    DISPONIBLES,
    NO_MODELABLES,
    Observacion,
    comparar,
    estimadores_disponibles,
    pendientes,
    veredicto,
)
from backend.modelado.particion import particionar  # noqa: E402
from backend.modelado.regresion_logistica import RegresionLogistica  # noqa: E402
from contratos.enums import NivelRiesgo, TipoEvento  # noqa: E402

DISTRITOS = [f"5080{i}" for i in range(1, 9)]


class Resultado:
    def __init__(self) -> None:
        self.fallos: list[str] = []
        self.hechos = 0

    def comprobar(self, nombre: str, condicion: bool, detalle: str = "") -> None:
        self.hechos += 1
        print(f"  {'ok  ' if condicion else 'FALLA'}  {nombre}")
        if not condicion:
            self.fallos.append(f"{nombre}{': ' + detalle if detalle else ''}")


def datos_sinteticos(evento: TipoEvento) -> tuple[list, dict]:
    """Etiquetas y caracteristicas que cubren los pliegues de H3.2.

    La senal es deliberada: `pp_acum3` alto implica ALTO. Un estimador que
    aprende tiene que poder encontrarla, y si la tabla dijera que no la encuentra
    el problema estaria en el cableado y no en los datos.
    """
    pliegues = particionar(evento)
    inicio = pliegues[0].entrenamiento[0]
    fin = pliegues[-1].prueba[1]

    filas, caracteristicas = [], {}
    dia = inicio
    i = 0
    while dia <= fin:
        for codigo in DISTRITOS:
            alto = (i + hash(codigo)) % 7 == 0
            nivel = NivelRiesgo.ALTO if alto else NivelRiesgo.BAJO
            niveles = dict.fromkeys(("sequia", "lluvia_intensa", "incendio"), nivel)
            filas.append((codigo, dia, niveles))
            caracteristicas[(codigo, dia)] = {
                "pp_acum3": 90.0 if alto else 4.0,
                "tmax_media7": 33.0 if alto else 27.0,
            }
        dia += timedelta(days=1)
        i += 1
    return filas, caracteristicas


def verificar() -> Resultado:  # noqa: PLR0915 - es una lista de criterios
    r = Resultado()
    print("\nCriterios de aceptacion de H3.3\n")

    filas, caracteristicas = datos_sinteticos(TipoEvento.LLUVIA_INTENSA)

    # ------------------------------------------------------------------ 1
    sin = estimadores_disponibles(False)
    r.comprobar(
        "1. sin matriz, la regresion NO entra en la tabla",
        "regresion logistica" not in sin and set(sin) == set(DISPONIBLES),
        f"quedo {sorted(sin)}",
    )
    motivo = pendientes(False).get("regresion logistica", "")
    r.comprobar(
        "   y sigue listada con el motivo real, no solo el numero de historia",
        "caracteristicas.csv" in motivo and "generar_caracteristicas" in motivo,
        f"decia: {motivo}",
    )

    # ------------------------------------------------------------------ 2
    con = estimadores_disponibles(True)
    r.comprobar(
        "2. con matriz, la regresion entra en la tabla",
        "regresion logistica" in con,
        f"quedo {sorted(con)}",
    )
    r.comprobar(
        "   y deja de aparecer como pendiente",
        "regresion logistica" not in pendientes(True),
    )

    # ------------------------------------------------------------------ 3
    r.comprobar(
        "3. la sequia esta declarada NO MODELABLE",
        TipoEvento.SEQUIA in NO_MODELABLES,
    )
    texto = NO_MODELABLES.get(TipoEvento.SEQUIA, "")
    r.comprobar(
        "   con el motivo medido, no solo 'no hay datos'",
        "D-34" in texto and "9" in texto and "CA-6" in texto,
        f"decia: {texto}",
    )

    # ------------------------------------------------------------------ 4
    filas_s, caract_s = datos_sinteticos(TipoEvento.SEQUIA)
    resultados = comparar(TipoEvento.SEQUIA, filas_s, con, caract_s)
    nombres = {x.nombre for x in resultados}
    r.comprobar(
        "4. los estimadores que aprenden no corren sobre la sequia",
        not (nombres & set(CON_CARACTERISTICAS)),
        f"corrieron {sorted(nombres)}",
    )

    # ------------------------------------------------------------------ 5
    r.comprobar(
        "5. las lineas base SI corren sobre la sequia",
        nombres == set(DISPONIBLES) and all(x.por_pliegue for x in resultados),
        f"quedo {sorted(nombres)}",
    )

    # ------------------------------------------------------------------ 6
    resultados = comparar(TipoEvento.LLUVIA_INTENSA, filas, con, caracteristicas)
    largos = {x.nombre: len(x.por_pliegue) for x in resultados}
    r.comprobar(
        "6. todos los estimadores ven los mismos pliegues",
        len(set(largos.values())) == 1 and next(iter(largos.values())) > 0,
        f"largos por estimador: {largos}",
    )
    regresion = next(x for x in resultados if x.nombre == "regresion logistica")
    r.comprobar(
        "   y la regresion encuentra la senal que se le puso",
        regresion.media > 0.9,
        f"F1-macro {regresion.media:.3f}; con una senal separable deberia ser casi 1",
    )

    # ------------------------------------------------------------------ 7
    # Un pliegue con una sola clase: no hay nada que aprender. La regresion se
    # niega, y la tabla tiene que sobrevivir a esa negativa.
    de_una_clase = [(c, f, dict.fromkeys(n, NivelRiesgo.BAJO)) for c, f, n in filas]
    try:
        resultados = comparar(TipoEvento.LLUVIA_INTENSA, de_una_clase, con, caracteristicas)
        sobrevivio = True
    except ValueError:
        sobrevivio = False
    r.comprobar(
        "7. un pliegue que no se puede ajustar no tumba la tabla",
        sobrevivio,
        "la excepcion del estimador se propago y se perdio la comparacion entera",
    )
    if sobrevivio:
        saltados = next((x.saltados for x in resultados if x.nombre == "regresion logistica"), [])
        r.comprobar(
            "   y queda el motivo por el que se salto, no un silencio",
            bool(saltados) and "una sola clase" in saltados[0],
            f"motivos: {saltados}",
        )

    # ------------------------------------------------------------------ 8 y 9
    mitad = len(filas) // 2
    obs_a = [Observacion(c, f, caracteristicas[(c, f)]) for c, f, _ in filas[:mitad]]
    eti_a = [n["lluvia_intensa"] for _, _, n in filas[:mitad]]
    modelo_a = RegresionLogistica().ajustar(obs_a, eti_a)

    # Un segundo conjunto con la misma forma y otra escala.
    caract_b = {k: {c: v * 10 for c, v in f.items()} for k, f in caracteristicas.items()}
    obs_b = [Observacion(c, f, caract_b[(c, f)]) for c, f, _ in filas[:mitad]]
    modelo_b = RegresionLogistica().ajustar(obs_b, eti_a)

    media_a = getattr(modelo_a, "_escalador", None)
    media_b = getattr(modelo_b, "_escalador", None)
    r.comprobar(
        "8. CA-6: el escalado se ajusta con los datos que recibe ajustar()",
        media_a is not None and media_b is not None,
        "no hay escalador: el estimador no esta normalizando",
    )
    if media_a is not None and media_b is not None:
        distintas = not (media_a.mean_ == media_b.mean_).all()
        r.comprobar(
            "9. y no hay ajuste global escondido: otra entrada, otra escala",
            distintas,
            "las dos escalas coinciden, asi que se ajusto con algo que no es el pliegue",
        )

    # ------------------------------------------------------------------ 10
    incompletas = [Observacion(c, f, {"pp_acum3": 90.0}) for c, f, _ in filas[:50]]
    prediccion = modelo_a.predecir(incompletas)
    r.comprobar(
        "10. una observacion sin todas sus caracteristicas no se predice",
        all(p is None for p in prediccion),
        f"predijo {sum(1 for p in prediccion if p is not None)} de {len(prediccion)}",
    )
    r.comprobar(
        "    y el estimador lleva la cuenta de cuantas fueron",
        modelo_a.filas_sin_prediccion == len(incompletas),
        f"conto {modelo_a.filas_sin_prediccion}, se esperaban {len(incompletas)}",
    )

    # ------------------------------------------------------------------ 11
    resultados = comparar(TipoEvento.INCENDIO, filas, DISPONIBLES, caracteristicas)
    if len(resultados) >= 2:
        primero, segundo = resultados[0], resultados[1]
        dictamen = veredicto(resultados)
        empatan = (primero.media - segundo.media) <= primero.rango
        r.comprobar(
            "11. no se declara ganador cuando la ventaja cabe en el ruido",
            ("empate tecnico" in dictamen) == empatan,
            f"dictamen: {dictamen}",
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
    print("\nH3.3 cumple sus criterios de aceptacion.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
