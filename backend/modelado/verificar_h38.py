"""
Verificador de H3.8: ajuste de hiperparametros sin mirar los pliegues de prueba.

Criterios en docs/evidencias/objetivos/H3.8-criterios-aceptacion.md.
CA-1 a CA-7 corren **sin base y sin red**: datos sinteticos de H3.3 y rejillas
de juguete, para que la suite no tarde minutos. CA-8 es la corrida real y va en
la evidencia.

    python -m backend.modelado.verificar_h38
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado import afinar  # noqa: E402
from backend.modelado.comparar import NO_MODELABLES, Resultado, elegir_escritor  # noqa: E402
from backend.modelado.particion import particionar  # noqa: E402
from backend.modelado.verificar_h33 import Resultado as Criterios  # noqa: E402
from backend.modelado.verificar_h33 import datos_sinteticos  # noqa: E402
from contratos.enums import TipoEvento  # noqa: E402

MODELABLES = [e for e in TipoEvento if e not in NO_MODELABLES]

#: Rejilla de juguete: dos ejes, cuatro combinaciones. Sirve para comprobar el
#: mecanismo -orden, reproducibilidad, desempate- sin pagar el costo de la real.
REJILLA_JUGUETE = {
    "random forest": {
        "n_estimators": (10, 20),
        "min_samples_leaf": (20, 1),
    }
}


def REJILLA_DE(algoritmo: str) -> dict:
    """La rejilla real del modulo, no la de juguete que instala CA-3."""
    return afinar.REJILLA.get(algoritmo, {})


def candidato(media: float, rango: float, capacidad: int, nombre: str = "x") -> afinar.Candidato:
    """Un candidato armado a mano, para probar la regla de eleccion sin ajustar nada."""
    mitad = rango / 2
    return afinar.Candidato(
        algoritmo="random forest",
        parametros={"nombre": nombre},
        media=media,
        rango=rango,
        por_pliegue=[media - mitad, media + mitad],
        capacidad=capacidad,
    )


def resultado(nombre: str, medias: list[float]) -> Resultado:
    media = sum(medias) / len(medias)
    return Resultado(nombre, medias, media, 0.0, 0)


def verificar() -> Criterios:
    r = Criterios()
    # Foto de lo que el modulo declara. Al final se comprueba que sigue igual:
    # este verificador escribe en `AFINADOS` para probar la tuberia, y un
    # verificador que deja el modulo distinto de como lo encontro es un
    # verificador que puede aprobar algo que ya no existe.
    afinados_declarados = {e: dict(v) for e, v in afinar.AFINADOS.items()}

    print("CA-1 · La rejilla es un dato declarado y acotado")
    total = sum(len(afinar.combinaciones(a)) for a in afinar.afinables())
    r.comprobar("hay rejilla para los tres algoritmos que aprenden", len(afinar.REJILLA) == 3)
    r.comprobar(
        "cada eje tiene al menos dos valores; un eje de uno no es una busqueda",
        all(len(v) >= 2 for ejes in afinar.REJILLA.values() for v in ejes.values()),
    )
    r.comprobar(
        f"la busqueda entera son {total} combinaciones, no una exploracion abierta",
        10 <= total <= 40,
        str(total),
    )
    for algoritmo in afinar.afinables():
        esperadas = 1
        for eje in afinar.REJILLA[algoritmo].values():
            esperadas *= len(eje)
        r.comprobar(
            f"{algoritmo}: el producto cartesiano da {esperadas} y eso es lo que se prueba",
            len(afinar.combinaciones(algoritmo)) == esperadas,
        )
    r.comprobar(
        "las combinaciones no se repiten",
        all(
            len({tuple(sorted(c.items())) for c in afinar.combinaciones(a)})
            == len(afinar.combinaciones(a))
            for a in afinar.afinables()
        ),
    )

    print("CA-2 · Nada se elige mirando los pliegues de prueba")
    for evento in MODELABLES:
        externos = particionar(evento)
        internos = afinar.pliegues_internos(evento)
        prueba_externa = afinar.fechas_de_prueba(externos)
        prueba_interna = afinar.fechas_de_prueba(internos)
        r.comprobar(
            f"{evento.value}: ninguna fecha de prueba interna cae en una de prueba externa",
            not (prueba_interna & prueba_externa),
            f"{len(prueba_interna & prueba_externa)} dias compartidos",
        )
        r.comprobar(
            f"{evento.value}: la ventana interna entera termina antes del primer bloque de prueba",
            internos[-1].prueba[1] < externos[0].prueba[0],
            f"interna hasta {internos[-1].prueba[1]}, prueba externa desde {externos[0].prueba[0]}",
        )
        r.comprobar(
            f"{evento.value}: la interna sale de la ventana de entrenamiento del primer externo",
            internos[0].entrenamiento[0] >= externos[0].entrenamiento[0]
            and internos[-1].prueba[1] <= externos[0].entrenamiento[1],
        )
        r.comprobar(
            f"{evento.value}: la interna tiene mas de un pliegue",
            len(internos) >= 2,
            str(len(internos)),
        )

    print("CA-3 · Los pliegues externos se tocan una sola vez, y por el mismo comparar()")
    evento = TipoEvento.LLUVIA_INTENSA
    filas, caracteristicas = datos_sinteticos(evento)
    original = afinar.REJILLA
    afinar.REJILLA = REJILLA_JUGUETE
    try:
        internos = afinar.pliegues_internos(evento)
        candidatos = afinar.buscar(
            evento, filas, caracteristicas, "random forest", internos, lambda *_: None
        )
        r.comprobar(
            "la busqueda prueba una combinacion por cada punto de la rejilla",
            len(candidatos) == len(afinar.combinaciones("random forest")),
        )
        r.comprobar(
            "y cada candidato trae su F1 por pliegue interno, no un numero suelto",
            all(c.por_pliegue for c in candidatos),
        )
        r.comprobar(
            "los pliegues internos evaluados son los internos, no los cinco de H3.2",
            all(len(c.por_pliegue) <= len(internos) for c in candidatos),
        )

        print("CA-4 · Se afina por evento, y sequia no se afina")
        salida: list[str] = []
        elegidos = afinar.afinar_evento(
            TipoEvento.SEQUIA, filas, caracteristicas, ["random forest"], False, salida.append
        )
        r.comprobar("sequia no devuelve parametros", elegidos == {})
        r.comprobar(
            "y lo dice con el motivo, no en silencio",
            any("no es modelable" in linea for linea in salida),
            " / ".join(salida),
        )

        print("CA-5 · Reproducible")
        otra_vez = afinar.buscar(
            evento, filas, caracteristicas, "random forest", internos, lambda *_: None
        )
        r.comprobar(
            "dos busquedas dan los mismos parametros en el mismo orden",
            [c.parametros for c in candidatos] == [c.parametros for c in otra_vez],
        )
        r.comprobar(
            "y exactamente los mismos puntajes",
            [c.por_pliegue for c in candidatos] == [c.por_pliegue for c in otra_vez],
        )
        r.comprobar(
            "asi que eligen lo mismo",
            afinar.elegir(candidatos)[0].parametros == afinar.elegir(otra_vez)[0].parametros,
        )
    finally:
        afinar.REJILLA = original

    print("CA-6 · El empate se rompe por simplicidad, no por decimales")
    gana_sola = [candidato(0.700, 0.010, 3, "compleja"), candidato(0.600, 0.010, 0, "simple")]
    elegido, motivo = afinar.elegir(gana_sola)
    r.comprobar(
        "si la mejor gana fuera de su ruido, gana la mejor aunque sea la mas compleja",
        elegido.parametros["nombre"] == "compleja",
        motivo,
    )
    empate = [candidato(0.700, 0.050, 3, "compleja"), candidato(0.690, 0.050, 0, "simple")]
    elegido, motivo = afinar.elegir(empate)
    r.comprobar(
        "si la ventaja es menor que el ruido, gana la de menos capacidad",
        elegido.parametros["nombre"] == "simple",
        motivo,
    )
    r.comprobar("y el motivo dice que fue empate tecnico", "empate tecnico" in motivo, motivo)
    empate_igual = [candidato(0.700, 0.050, 2, "b"), candidato(0.700, 0.050, 1, "a")]
    r.comprobar(
        "con la misma media gana la mas simple, sin depender del orden de entrada",
        afinar.elegir(empate_igual)[0].parametros["nombre"] == "a",
    )
    r.comprobar(
        "sin candidatos utiles no se inventa uno",
        afinar.elegir([])[0] is None,
    )
    r.comprobar(
        "la capacidad sale de la posicion en la rejilla declarada",
        afinar.capacidad(
            "random forest", {"n_estimators": 200, "max_depth": 6, "min_samples_leaf": 20}
        )
        == 0
        and afinar.capacidad(
            "random forest", {"n_estimators": 400, "max_depth": None, "min_samples_leaf": 1}
        )
        == 3,
    )

    print("CA-7 · El resultado pasa por D-39 sin excepcion")
    # Con el nombre canonico: es lo que `afinar_evento` pone en la tabla, y el
    # motivo esta escrito en su codigo. Con un nombre nuevo, D-39 lo ignoraria.
    fuera_del_ruido = [
        resultado("xgboost", [0.80, 0.80, 0.80]),
        resultado("climatologica", [0.50, 0.50, 0.50]),
        resultado("trivial", [0.40, 0.40, 0.40]),
    ]
    escritor, motivo = elegir_escritor(fuera_del_ruido)
    r.comprobar(
        "un afinado que gana fuera del ruido pasa a escribir, sin tocar la regla",
        escritor == "xgboost",
        f"{escritor} · {motivo}",
    )
    dentro_del_ruido = [
        resultado("xgboost", [0.55, 0.45, 0.62]),
        resultado("climatologica", [0.52, 0.44, 0.60]),
        resultado("trivial", [0.30, 0.30, 0.30]),
    ]
    escritor, motivo = elegir_escritor(dentro_del_ruido)
    r.comprobar(
        "si gana dentro del ruido, sigue escribiendo la climatologica",
        escritor == "climatologica",
        f"{escritor} · {motivo}",
    )
    fuente_afinar = (RAIZ / "backend" / "modelado" / "afinar.py").read_text(encoding="utf-8")
    r.comprobar(
        "la tabla externa nombra a los afinados con su nombre canonico, o D-39 los ignoraria",
        "estimadores[algoritmo] = fabrica(algoritmo, parametros)" in fuente_afinar
        and 'f"{algoritmo} afinado"' not in fuente_afinar,
    )
    r.comprobar(
        "afinar no agrega ni quita estimadores: la tabla sigue teniendo los cinco de H3.6",
        set(afinar.fabricas(TipoEvento.LLUVIA_INTENSA, True))
        == {"trivial", "climatologica", "regresion logistica", "random forest", "xgboost"},
    )
    # Se guarda lo que hubiera y se restaura al salir. Sin esto, el `pop` del
    # final borraria los afinados REALES para el resto de la corrida, y las
    # comprobaciones que vienen despues mirarian una tuberia sin afinar sin que
    # nadie se entere.
    previo = afinar.AFINADOS.get("lluvia_intensa")
    afinar.AFINADOS["lluvia_intensa"] = {"random forest": {"n_estimators": 7}}
    try:
        construido = afinar.fabricas(TipoEvento.LLUVIA_INTENSA, True)["random forest"]()
        r.comprobar(
            "con afinados, la tuberia construye el estimador con esos parametros",
            construido.parametros == {"n_estimators": 7},
            str(getattr(construido, "parametros", None)),
        )
        sin_caracteristicas = afinar.fabricas(TipoEvento.LLUVIA_INTENSA, False)
        r.comprobar(
            "y sin matriz de caracteristicas siguen quedando solo las lineas base",
            set(sin_caracteristicas) == {"trivial", "climatologica"},
        )
    finally:
        if previo is None:
            afinar.AFINADOS.pop("lluvia_intensa", None)
        else:
            afinar.AFINADOS["lluvia_intensa"] = previo

    r.comprobar(
        "el verificador devolvio AFINADOS como estaba: no deja el modulo tocado",
        afinados_declarados == afinar.AFINADOS,
        f"{sorted(afinar.AFINADOS)} contra {sorted(afinados_declarados)}",
    )
    fuera_de_rejilla = [
        f"{evento}/{algoritmo}: {clave}={valor!r}"
        for evento, por_algoritmo in afinados_declarados.items()
        for algoritmo, parametros in por_algoritmo.items()
        for clave, valor in parametros.items()
        if clave not in REJILLA_DE(algoritmo) or valor not in REJILLA_DE(algoritmo)[clave]
    ]
    r.comprobar(
        "cada valor afinado sale de la rejilla declarada, no de un dedazo al pegarlo",
        not fuera_de_rejilla,
        " / ".join(fuera_de_rejilla),
    )

    fuente = (RAIZ / "backend" / "modelado" / "estimar_riesgo.py").read_text(encoding="utf-8")
    r.comprobar(
        "la tuberia arma la tabla y el escritor por la MISMA puerta: nadie evalua uno y escribe otro",
        fuente.count("fabricas(") >= 2 and "estimadores_disponibles(" not in fuente,
        "estimar_riesgo.py deberia usar afinar.fabricas() en los dos sitios",
    )

    return r


def main() -> int:
    resultado_final = verificar()
    hechos = resultado_final.hechos
    fallos = resultado_final.fallos
    print(f"\n{hechos - len(fallos)} de {hechos} criterios")
    if fallos:
        print("\nNO se cumplen:")
        for fallo in fallos:
            print(f"  - {fallo}")
        print()
        return 1
    print("\nH3.8 cumple CA-1 a CA-7. CA-8 es la corrida real, en la evidencia.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
