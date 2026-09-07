"""
Pruebas de `backend/modelado/importancia.py`. Historia H4.1.

QUE PROTEGEN, Y POR QUE NINGUNA NECESITA UN MODELO DE VERDAD
------------------------------------------------------------

Todas usan un **estimador de juguete** en vez de la regresion, el bosque o
XGBoost. No es por comodidad ni por velocidad: es porque lo que hay que probar
aca **no es el modelo, es el arnes**.

Un estimador de juguete tiene una propiedad que ninguno real tiene: se sabe de
antemano en que columna se apoya. Con eso, «la permutacion de la columna que el
modelo usa tiene que bajar la metrica y la de la columna que ignora no» pasa de
ser una intuicion a ser una asercion.

Si estas pruebas usaran un `RandomForest`, un fallo no distinguiria entre «el
arnes esta roto» y «el bosque decidio otra cosa», que es exactamente la
ambiguedad que hace inutil a una prueba.

Los pliegues se pasan a mano por el parametro `pliegues`, que existe desde H3.8.
Asi no hace falta ni base ni `etiquetas.csv`: es CA-11.
"""

from __future__ import annotations

import random
from datetime import date, timedelta

import pytest

from backend.modelado.comparar import Observacion
from backend.modelado.importancia import (
    ImportanciaColumna,
    ImportanciaEstimador,
    _permutar,
    columnas_de,
    importancia,
)
from backend.modelado.particion import Pliegue
from contratos.enums import NivelRiesgo, TipoEvento

# --------------------------------------------------------------------------- #
# El estimador de juguete                                                       #
# --------------------------------------------------------------------------- #


class SoloMiraUna:
    """Predice ALTO si `columna` supera un umbral, y BAJO si no.

    Ignora por completo el resto de las columnas. `vistas_al_predecir` guarda las
    observaciones de cada llamada, que es lo que permite comprobar **sobre que
    conjunto se permuto** sin mirar el codigo.
    """

    def __init__(self, columna: str = "util", umbral: float = 0.5) -> None:
        self.nombre = "juguete"
        self.columna = columna
        self.umbral = umbral
        self.vistas_al_ajustar: list[list[Observacion]] = []
        self.vistas_al_predecir: list[list[Observacion]] = []

    def ajustar(self, observaciones, etiquetas):
        self.vistas_al_ajustar.append(list(observaciones))
        return self

    def predecir(self, observaciones):
        self.vistas_al_predecir.append(list(observaciones))
        return [
            NivelRiesgo.ALTO
            if o.caracteristicas.get(self.columna, 0.0) > self.umbral
            else NivelRiesgo.BAJO
            for o in observaciones
        ]


def _datos(n: int = 40):
    """`filas` y `caracteristicas` con una columna util y una de puro relleno.

    La etiqueta se construye **desde** `util`, asi que un modelo que la mire
    acierta y uno que mire `ruido` no. La columna `ruido` alterna con un patron
    fijo, sin azar: una prueba que dependa de una semilla propia esconde su
    propia fragilidad.
    """
    filas = []
    caracteristicas = {}
    for i in range(n):
        codigo = "50801"
        fecha = date(2020, 1, 1) + timedelta(days=i)
        util = 1.0 if i % 2 == 0 else 0.0
        nivel = NivelRiesgo.ALTO if util else NivelRiesgo.BAJO
        filas.append((codigo, fecha, {"lluvia_intensa": nivel}))
        caracteristicas[(codigo, fecha)] = {"util": util, "ruido": float(i % 3)}
    return filas, caracteristicas


def _un_pliegue(n: int = 40):
    """Un solo pliegue, mitad y mitad, escrito a mano. Sin base y sin H3.2."""
    inicio = date(2020, 1, 1)
    corte = inicio + timedelta(days=n // 2)
    return [
        Pliegue(
            indice=0,
            entrenamiento=(inicio, corte - timedelta(days=1)),
            prueba=(corte, inicio + timedelta(days=n - 1)),
            embargo=None,
        )
    ]


# --------------------------------------------------------------------------- #
# `_permutar`                                                                   #
# --------------------------------------------------------------------------- #


def _observaciones():
    obs = [
        Observacion(f"5080{i}", date(2024, 1, 1 + i), {"pp_7": float(i), "tmax_3": float(10 - i)})
        for i in range(6)
    ]
    # Una fila a la que le falta `pp_7`, que es el caso que importa.
    obs.append(Observacion("50899", date(2024, 2, 1), {"tmax_3": 7.0}))
    return obs


def test_permutar_conserva_el_patron_de_ausencia():
    """
    **La fila que no tenia la columna sigue sin tenerla.**

    Es el detalle que decide si el numero significa algo. Si la permutacion
    rellenara los huecos, cambiaria cuantas filas el estimador puede predecir, y
    entonces la metrica se moveria por una razon que no tiene nada que ver con
    la informacion de la columna. La caida se leeria como importancia y seria
    otra cosa.
    """
    obs = _observaciones()
    salida = _permutar(obs, "pp_7", random.Random("x"))

    assert "pp_7" not in salida[-1].caracteristicas
    assert sum("pp_7" in o.caracteristicas for o in salida) == 6


def test_permutar_no_toca_las_otras_columnas():
    obs = _observaciones()
    salida = _permutar(obs, "pp_7", random.Random("x"))

    assert [o.caracteristicas["tmax_3"] for o in salida] == [
        o.caracteristicas["tmax_3"] for o in obs
    ]


def test_permutar_conserva_el_multiconjunto_de_valores():
    """Barajar reordena; no inventa ni pierde valores."""
    obs = _observaciones()
    salida = _permutar(obs, "pp_7", random.Random("x"))

    antes = sorted(o.caracteristicas["pp_7"] for o in obs if "pp_7" in o.caracteristicas)
    despues = sorted(o.caracteristicas["pp_7"] for o in salida if "pp_7" in o.caracteristicas)
    assert antes == despues


def test_permutar_es_reproducible_con_la_misma_semilla():
    """
    CA-3 y CA-12. La semilla se deriva de una **cadena** y no de una tupla.

    Medido el 2026-09-04: `random.Random(('a', 0))` da un orden distinto en cada
    proceso, porque `hash()` de una cadena se aleatoriza por proceso salvo que se
    fije `PYTHONHASHSEED`. `random.Random('a|0')` no: para cadenas, `seed` usa
    una conversion determinista.

    Un resultado que no se puede repetir no es un resultado, y este defecto no
    haria fallar nada: solo daria numeros distintos cada vez, que es peor.
    """
    obs = _observaciones()
    una = _permutar(obs, "pp_7", random.Random("H4.1|0|pp_7|0"))
    otra = _permutar(obs, "pp_7", random.Random("H4.1|0|pp_7|0"))

    assert [o.caracteristicas.get("pp_7") for o in una] == [
        o.caracteristicas.get("pp_7") for o in otra
    ]


def test_permutar_con_menos_de_dos_filas_no_hace_nada():
    obs = [Observacion("50801", date(2024, 1, 1), {"pp_7": 1.0})]
    assert _permutar(obs, "pp_7", random.Random("x")) == obs


def test_columnas_de_une_y_ordena():
    """CA-6: se leen por nombre, y la union cubre a las filas incompletas."""
    assert columnas_de(_observaciones()) == ["pp_7", "tmax_3"]


# --------------------------------------------------------------------------- #
# La regla de «no se afirma por debajo del ruido propio»                        #
# --------------------------------------------------------------------------- #


def test_una_columna_es_distinguible_solo_si_supera_su_rango():
    """Misma regla que el `veredicto` de H3.6, aplicada a una columna."""
    fuerte = ImportanciaColumna("a", [0.50, 0.48, 0.52])
    debil = ImportanciaColumna("b", [0.05, -0.02, 0.09])

    assert fuerte.distinguible
    assert not debil.distinguible


def test_una_caida_negativa_grande_tambien_es_distinguible():
    """
    CA-5 llevado hasta el final: **el signo no se mira, la magnitud si.**

    Una columna cuya permutacion mejora la metrica de forma consistente esta
    diciendo algo real -el modelo la usaba en contra- y tiene que salir marcada,
    no descartada por ser negativa.
    """
    contraria = ImportanciaColumna("c", [-0.40, -0.42, -0.38])
    assert contraria.distinguible
    assert contraria.media < 0


def test_ninguna_distinguible_es_un_resultado_emitible():
    """CA-10."""
    est = ImportanciaEstimador(
        nombre="x",
        referencia_por_pliegue=[0.3, 0.3],
        permutacion=[ImportanciaColumna("a", [0.01, -0.03]), ImportanciaColumna("b", [0.0, 0.02])],
    )
    assert est.ninguna_distinguible


def test_con_una_columna_distinguible_ya_no_lo_es():
    est = ImportanciaEstimador(
        nombre="x",
        referencia_por_pliegue=[0.3],
        permutacion=[ImportanciaColumna("a", [0.5, 0.49]), ImportanciaColumna("b", [0.0, 0.01])],
    )
    assert not est.ninguna_distinguible


# --------------------------------------------------------------------------- #
# `importancia`, con el estimador de juguete                                    #
# --------------------------------------------------------------------------- #


def test_la_columna_que_el_modelo_usa_pesa_y_la_que_ignora_no():
    """
    La prueba central. `util` construye la etiqueta; `ruido` no la toca.

    Si esto falla, el arnes no esta midiendo importancia: esta midiendo otra cosa
    con el nombre correcto, que es el peor modo de fallar.
    """
    filas, caracteristicas = _datos()
    resultado = importancia(
        TipoEvento.LLUVIA_INTENSA,
        filas,
        {"juguete": SoloMiraUna},
        caracteristicas,
        pliegues=_un_pliegue(),
        repeticiones=3,
    )

    porcolumna = {c.nombre: c for c in resultado[0].permutacion}
    assert porcolumna["util"].media > 0.2
    assert abs(porcolumna["ruido"].media) < 1e-9


def test_la_permutacion_ocurre_sobre_prueba_y_no_sobre_entrenamiento():
    """
    CA-2, comprobado mirando **que observaciones vio el modelo**, no el codigo.

    El estimador de juguete guarda cada lista que recibe. Ninguna de las que
    recibio al predecir puede contener una fecha del bloque de entrenamiento: si
    la contuviera, la importancia estaria midiendo cuanto memorizo el modelo, y
    ese error no se ve en ningun numero. Solo sale una tabla mas nitida.
    """
    filas, caracteristicas = _datos()
    pliegue = _un_pliegue()[0]
    espia = SoloMiraUna()

    importancia(
        TipoEvento.LLUVIA_INTENSA,
        filas,
        {"juguete": lambda: espia},
        caracteristicas,
        pliegues=[pliegue],
        repeticiones=2,
    )

    vistas = {o.fecha for lista in espia.vistas_al_predecir for o in lista}
    assert vistas
    assert all(pliegue.prueba[0] <= f <= pliegue.prueba[1] for f in vistas)
    assert not any(pliegue.entrenamiento[0] <= f <= pliegue.entrenamiento[1] for f in vistas)


def test_dos_corridas_con_la_misma_semilla_dan_lo_mismo():
    """CA-12."""
    filas, caracteristicas = _datos()
    argumentos = (
        TipoEvento.LLUVIA_INTENSA,
        filas,
        {"juguete": SoloMiraUna},
        caracteristicas,
        _un_pliegue(),
        3,
    )
    una = importancia(*argumentos)
    otra = importancia(*argumentos)

    assert [(c.nombre, c.por_pliegue) for c in una[0].permutacion] == [
        (c.nombre, c.por_pliegue) for c in otra[0].permutacion
    ]


def test_la_sequia_no_produce_tabla():
    """CA-9: esta en NO_MODELABLES por D-34, y no se le inventa una."""
    filas, caracteristicas = _datos()
    assert (
        importancia(
            TipoEvento.SEQUIA,
            filas,
            {"juguete": SoloMiraUna},
            caracteristicas,
            pliegues=_un_pliegue(),
        )
        == []
    )


def test_un_estimador_que_no_se_puede_ajustar_no_tumba_la_tabla():
    """Mismo criterio que `comparar`: se salta y se guarda el motivo."""

    class SeNiega:
        nombre = "se niega"

        def ajustar(self, observaciones, etiquetas):
            raise ValueError("una sola clase en el entrenamiento")

        def predecir(self, observaciones):  # pragma: no cover
            raise AssertionError("no deberia llegar aca")

    filas, caracteristicas = _datos()
    resultado = importancia(
        TipoEvento.LLUVIA_INTENSA,
        filas,
        {"se niega": SeNiega, "juguete": SoloMiraUna},
        caracteristicas,
        pliegues=_un_pliegue(),
        repeticiones=2,
    )

    porname = {e.nombre: e for e in resultado}
    assert porname["se niega"].permutacion == []
    assert "una sola clase" in porname["se niega"].saltados[0]
    assert porname["juguete"].permutacion


def test_el_estimador_sin_mdi_ni_coeficientes_los_reporta_como_none():
    """
    Devolver None y decirlo es mas honesto que fabricar un cero.

    La regresion logistica no tiene MDI porque no hay impureza que reducir, y el
    bosque no tiene coeficientes porque no es lineal. **No es una carencia.**
    """
    filas, caracteristicas = _datos()
    resultado = importancia(
        TipoEvento.LLUVIA_INTENSA,
        filas,
        {"juguete": SoloMiraUna},
        caracteristicas,
        pliegues=_un_pliegue(),
        repeticiones=1,
    )
    assert resultado[0].mdi is None
    assert resultado[0].coeficientes is None


def test_las_columnas_salen_ordenadas_por_caida_media():
    filas, caracteristicas = _datos()
    resultado = importancia(
        TipoEvento.LLUVIA_INTENSA,
        filas,
        {"juguete": SoloMiraUna},
        caracteristicas,
        pliegues=_un_pliegue(),
        repeticiones=2,
    )
    medias = [c.media for c in resultado[0].permutacion]
    assert medias == sorted(medias, reverse=True)


@pytest.mark.parametrize("repeticiones", [1, 4])
def test_hay_un_valor_por_pliegue_y_no_uno_por_repeticion(repeticiones):
    """
    CA-4. Las repeticiones se promedian **dentro** del pliegue; lo que se guarda
    es un valor por pliegue.

    Mezclarlos daria una dispersion que no distingue «varia entre pliegues» de
    «varia entre barajadas», y son cosas distintas: la primera dice que la
    importancia no es estable en el tiempo, la segunda solo que hacen falta mas
    repeticiones.
    """
    filas, caracteristicas = _datos()
    resultado = importancia(
        TipoEvento.LLUVIA_INTENSA,
        filas,
        {"juguete": SoloMiraUna},
        caracteristicas,
        pliegues=_un_pliegue(),
        repeticiones=repeticiones,
    )
    assert all(len(c.por_pliegue) == 1 for c in resultado[0].permutacion)
