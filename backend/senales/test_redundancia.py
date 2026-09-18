"""Pruebas de `redundancia.py`. Historia H2.6.

**Ninguna necesita PostgreSQL ni red**, incluidas las de las temperaturas: el
cursor se reemplaza por uno falso que devuelve filas escritas a mano. Es el
CA-12, y es la misma separacion por la que `generar_caracteristicas` vive aparte
de `comparar`.

Las dos pruebas de sabotaje -CA-11- estan marcadas en su nombre. Existen porque
**un detector que siempre encuentra algo y uno que nunca encuentra nada se ven
igual en una sola corrida**: hace falta plantarle una redundancia y exigir que
la vea, y romperla y exigir que deje de verla.
"""

from __future__ import annotations

import csv
import math
import random
from datetime import date

import pytest

from backend.senales.redundancia import (
    TOLERANCIA,
    Fila,
    correlacion,
    correlacion_de_temperaturas,
    escribir_sin,
    filas_completas,
    leer_matriz,
    pares_relacionados,
    relacion_afin,
    variacion_espacial,
)


def csv_de(tmp_path, columnas, filas, formato=".6g"):
    """Escribe un CSV con el MISMO formato que `generar_caracteristicas`."""
    destino = tmp_path / "caracteristicas.csv"
    with destino.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["codigo_distrito", "fecha", *columnas])
        for codigo, fecha, valores in filas:
            escritor.writerow(
                [
                    codigo,
                    fecha,
                    *[
                        "" if valores.get(c) is None else format(valores[c], formato)
                        for c in columnas
                    ],
                ]
            )
    return destino


# ===========================================================================
# LAS DOS COMPROBACIONES
# ===========================================================================


def test_una_copia_exacta_se_detecta():
    """SABOTAJE · CA-11. Se planta una columna identica y tiene que verse."""
    azar = random.Random(1)
    x = [azar.random() * 100 for _ in range(200)]
    vectores = {"a": x, "b": list(x), "c": [i * 0.37 % 5 for i in range(200)]}
    exactos, _altos = pares_relacionados(vectores, ["a", "b", "c"])
    encontrados = {(p.a, p.b) for p in exactos}
    assert ("a", "b") in encontrados


def test_una_relacion_afin_se_detecta():
    """SABOTAJE · CA-11. No solo la copia: `y = a*x + b` tambien es redundante."""
    azar = random.Random(2)
    x = [azar.random() * 100 for _ in range(200)]
    vectores = {"a": x, "b": [3.0 * v + 7.5 for v in x]}
    exactos, _altos = pares_relacionados(vectores, ["a", "b"])
    assert len(exactos) == 1
    par = exactos[0]
    assert par.pendiente == pytest.approx(3.0, rel=1e-9)
    assert par.corte == pytest.approx(7.5, abs=1e-9)


def test_barajar_rompe_la_redundancia():
    """SABOTAJE INVERSO · CA-11. El detector tiene que poder decir que NO.

    Es la mitad que suele faltar. Un detector que devuelve todos los pares como
    redundantes pasaria las dos pruebas de arriba sin problema.
    """
    azar = random.Random(3)
    x = [azar.random() * 100 for _ in range(200)]
    y = [3.0 * v + 7.5 for v in x]
    azar.shuffle(y)
    exactos, altos = pares_relacionados({"a": x, "b": y}, ["a", "b"])
    assert exactos == []
    assert altos == []


def test_una_sola_fila_fuera_de_la_recta_ya_no_es_exacta():
    """La comprobacion es fila por fila, no en promedio.

    Con 199 filas sobre la recta y una sola afuera, el error cuadratico medio
    sigue siendo minusculo y un ajuste por minimos cuadrados declararia la
    relacion. No lo es: una relacion exacta vale en todas las filas.
    """
    x = [float(i) for i in range(200)]
    y = [3.0 * v + 7.5 for v in x]
    y[100] += 50.0
    assert relacion_afin(x, y) is None


def test_la_correlacion_no_alcanza_seno_y_coseno_son_el_contraejemplo():
    """`sen^2 + cos^2 = 1` es dependencia perfecta y correlacion casi nula.

    Es la razon por la que este modulo exige dos comprobaciones. Y tambien es el
    limite declarado: estas dos columnas son redundantes en un sentido que la
    correlacion no ve, y el modulo no las reporta.
    """
    angulos = [2 * math.pi * d / 365.25 for d in range(1, 366)]
    seno = [math.sin(a) for a in angulos]
    coseno = [math.cos(a) for a in angulos]
    exactos, altos = pares_relacionados(
        {"cal_seno": seno, "cal_coseno": coseno}, ["cal_seno", "cal_coseno"]
    )
    assert exactos == []
    assert altos == []
    assert abs(correlacion(seno, coseno)) < 0.1


def test_una_correlacion_negativa_perfecta_tambien_es_redundancia():
    x = [float(i) for i in range(100)]
    exactos, _altos = pares_relacionados({"a": x, "b": [-2.0 * v + 1 for v in x]}, ["a", "b"])
    assert len(exactos) == 1
    assert exactos[0].r == pytest.approx(-1.0)


def test_un_par_exacto_no_se_cuenta_tambien_como_alto():
    """Son dos decisiones distintas: una se descarta y la otra solo se reporta."""
    x = [float(i) for i in range(100)]
    exactos, altos = pares_relacionados({"a": x, "b": [3.0 * v for v in x]}, ["a", "b"])
    assert len(exactos) == 1
    assert altos == []


# ===========================================================================
# EL REDONDEO DEL CSV
# ===========================================================================


def test_la_relacion_sobrevive_al_formato_del_csv(tmp_path):
    """El caso real: `pp_media{n} = pp_acum{n} / n` despues de pasar por %.6g.

    Si la tolerancia fuera `1e-12` -que es lo que uno escribe sin pensarlo- esta
    prueba fallaria y el informe diria que no hay redundancia donde la hay. Seis
    cifras significativas dejan un error relativo del orden de 1e-06.
    """
    azar = random.Random(4)
    filas = []
    for i in range(300):
        acum = azar.random() * 90
        filas.append(
            ("D1", f"2020-01-{i % 28 + 1:02d}", {"pp_acum3": acum, "pp_media3": acum / 3.0})
        )
    origen = csv_de(tmp_path, ["pp_acum3", "pp_media3"], filas)

    columnas, leidas = leer_matriz(origen)
    vectores = {c: [f.valores[c] for f in leidas] for c in columnas}
    exactos, _altos = pares_relacionados(vectores, columnas)

    assert len(exactos) == 1
    assert exactos[0].pendiente == pytest.approx(1 / 3, rel=1e-4)
    # El residuo es del orden que predice el formato, no cero.
    assert 0 < exactos[0].residuo < TOLERANCIA


def test_una_tolerancia_de_doce_cifras_perderia_la_relacion_real():
    """Congela el porque de la constante, no solo su valor.

    Si alguien baja `TOLERANCIA` a `1e-12` «para ser estrictos», esta prueba
    explica que el efecto no es mas rigor: es dejar de ver una redundancia que
    existe.
    """
    azar = random.Random(5)
    acum = [azar.random() * 90 for _ in range(300)]
    # Se simula el viaje por el CSV: seis cifras significativas de ida.
    redondeado = [float(format(v, ".6g")) for v in acum]
    media = [float(format(v / 3.0, ".6g")) for v in acum]
    assert relacion_afin(redondeado, media, tolerancia=1e-12) is None
    assert relacion_afin(redondeado, media, tolerancia=TOLERANCIA) is not None


def test_la_correlacion_no_se_pasa_de_uno():
    """Regresion numerica. La primera version imprimia `r = 1.0000000172`.

    Pasa con valores grandes y de poca varianza, que es donde la forma corta de
    Pearson resta dos numeros casi iguales. Un coeficiente mayor que 1 no es un
    valor posible y en un informe se lee como un defecto del calculo.
    """
    azar = random.Random(6)
    x = [1_000_000 + azar.random() for _ in range(5000)]
    for y in (list(x), [v * 2.0 for v in x], [-v for v in x]):
        r = correlacion(x, y)
        assert r is not None
        assert -1.0 <= r <= 1.0


def test_una_columna_constante_no_tiene_correlacion_y_no_da_cero():
    """None y no 0.0: un cero se leeria como «no se parecen»."""
    assert correlacion([1.0] * 50, [float(i) for i in range(50)]) is None


# ===========================================================================
# LECTURA Y FILAS COMPLETAS
# ===========================================================================


def test_una_celda_vacia_no_es_un_cero(tmp_path):
    """D-07. Cero milimetros de lluvia es una medicion; ausencia de dato no."""
    origen = csv_de(
        tmp_path,
        ["pp_acum3", "pp_media3"],
        [("D1", "2020-01-01", {"pp_acum3": 0.0, "pp_media3": None})],
    )
    _columnas, filas = leer_matriz(origen)
    assert filas[0].valores["pp_acum3"] == 0.0
    assert "pp_media3" not in filas[0].valores


def test_una_fila_a_la_que_le_falta_una_celda_no_entra(tmp_path):
    """El estimador no imputa: esa fila no se usa ni para ajustar ni para predecir."""
    origen = csv_de(
        tmp_path,
        ["a", "b"],
        [
            ("D1", "2020-01-01", {"a": 1.0, "b": 2.0}),
            ("D1", "2020-01-02", {"a": 1.0, "b": None}),
        ],
    )
    columnas, filas = leer_matriz(origen)
    assert len(filas) == 2
    assert len(filas_completas(filas, columnas)) == 1


# ===========================================================================
# VARIACION ESPACIAL
# ===========================================================================


def test_una_columna_igual_en_todos_los_distritos_no_distingue():
    """El caso de I-05: los ocho distritos en la misma celda de POWER."""
    filas = [
        Fila(f"D{d}", date(2020, 1, dia), {"tmax_rez1": 20.0 + dia})
        for dia in range(1, 11)
        for d in range(8)
    ]
    espacial = variacion_espacial(filas, ["tmax_rez1"])
    distintos, usables = espacial["tmax_rez1"]
    assert usables == 10
    assert distintos == 0


def test_una_columna_distinta_entre_distritos_si_distingue():
    filas = [
        Fila(f"D{d}", date(2020, 1, dia), {"pp_acum3": dia + d})
        for dia in range(1, 11)
        for d in range(8)
    ]
    distintos, usables = variacion_espacial(filas, ["pp_acum3"])["pp_acum3"]
    assert (distintos, usables) == (10, 10)


def test_la_variacion_espacial_no_depende_de_las_otras_columnas():
    """Se mide sobre todas las filas, no solo sobre las completas.

    No es una correlacion: no hay nada que alinear con otra columna. Restringirla
    a las filas completas contestaria la pregunta sobre un subconjunto elegido
    por el estado de las otras 31 columnas, que no tiene nada que ver.
    """
    fecha = date(2020, 1, 1)
    filas = [
        Fila("D1", fecha, {"a": 1.0, "b": 9.0}),
        Fila("D2", fecha, {"a": 2.0}),  # incompleta: le falta b
    ]
    distintos, usables = variacion_espacial(filas, ["a", "b"])["a"]
    assert (distintos, usables) == (1, 1)


# ===========================================================================
# LAS TEMPERATURAS, SIN BASE
# ===========================================================================


class CursorFalso:
    """Devuelve filas escritas a mano con la forma de la consulta de CA-5."""

    def __init__(self, filas):
        self._filas = filas

    def execute(self, *_a, **_k):
        return None

    def fetchall(self):
        return self._filas


def test_las_temperaturas_se_miden_sobre_los_dias_no_sobre_las_filas():
    """Con I-05 vigente, ocho filas por dia son un dia, no ocho muestras."""
    filas = [
        (f"2020-01-{d:02d}", 30.0 + d, 30.0 + d, 20.0 + d, 20.0 + d, 25.0 + d, 25.0 + d)
        for d in range(1, 21)
    ]
    medida = correlacion_de_temperaturas(CursorFalso(filas))
    assert medida["una_sola_serie"] is True
    assert medida["dias"] == 20
    assert len(medida["series"]["tmax"]) == 20


def test_las_temperaturas_se_niegan_si_los_distritos_no_coinciden():
    """Si I-05 dejara de valer, promediar por lo bajo taparia el hallazgo."""
    filas = [
        ("2020-01-01", 30.0, 31.5, 20.0, 20.0, 25.0, 25.0),  # tmax difiere
        ("2020-01-02", 30.0, 30.0, 20.0, 20.0, 25.0, 25.0),
    ]
    medida = correlacion_de_temperaturas(CursorFalso(filas))
    assert medida["una_sola_serie"] is False
    assert medida["desacuerdos"]["tmax"] == 1
    assert medida["desacuerdos"]["tmin"] == 0


# ===========================================================================
# LA MATRIZ REDUCIDA DEL CA-8
# ===========================================================================


def test_escribir_sin_quita_solo_esas_columnas(tmp_path):
    origen = csv_de(
        tmp_path,
        ["pp_acum3", "pp_media3", "tmax_rez1"],
        [("D1", "2020-01-01", {"pp_acum3": 9.0, "pp_media3": 3.0, "tmax_rez1": 28.0})],
    )
    destino = tmp_path / "reducida.csv"
    quedan, filas = escribir_sin(origen, destino, {"pp_media3"})
    assert quedan == ["pp_acum3", "tmax_rez1"]
    assert filas == 1
    columnas, leidas = leer_matriz(destino)
    assert columnas == ["pp_acum3", "tmax_rez1"]
    assert leidas[0].codigo == "D1"


def test_escribir_sin_copia_las_celdas_tal_cual(tmp_path):
    """El «antes» y el «despues» tienen que diferir en UNA cosa, no en dos.

    Si las celdas se reformatearan al copiarlas, la matriz reducida cambiaria la
    ultima cifra de algunos valores ademas de perder columnas, y la comparacion
    del CA-8 mediria dos efectos a la vez.
    """
    origen = csv_de(
        tmp_path,
        ["a", "b"],
        [("D1", "2020-01-01", {"a": 1 / 3, "b": 2.0})],
    )
    destino = tmp_path / "reducida.csv"
    escribir_sin(origen, destino, {"b"})
    celda_origen = origen.read_text(encoding="utf-8").splitlines()[1].split(",")[2]
    celda_destino = destino.read_text(encoding="utf-8").splitlines()[1].split(",")[2]
    assert celda_origen == celda_destino


def test_escribir_sin_se_niega_ante_un_nombre_que_no_existe(tmp_path):
    """Un nombre mal escrito produciria una copia identica, y el CA-8 mediria
    la misma matriz dos veces sin que nada se queje."""
    origen = csv_de(tmp_path, ["a"], [("D1", "2020-01-01", {"a": 1.0})])
    with pytest.raises(ValueError, match="pp_media3"):
        escribir_sin(origen, tmp_path / "x.csv", {"pp_media3"})
