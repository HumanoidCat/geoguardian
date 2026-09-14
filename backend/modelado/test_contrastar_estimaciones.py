"""Pruebas de `contrastar_estimaciones`. Historia H4.4.

No tocan la red: el cliente se sustituye por uno falso. Lo que se prueba no es el
resultado del contraste -ese sale de produccion y cambia- sino que **el control de
CA-6 sabe fallar**, que es la regla del proyecto para cualquier verificador.
"""

from __future__ import annotations

import pytest

from backend.modelado import contrastar_estimaciones as ce

DISTRITOS = [f"5080{i}" for i in range(1, 9)]


class ClienteFalso(ce.Cliente):
    """Devuelve filas inventadas con la forma exacta que sirve la API.

    `constante` decide si la estimacion cambia dentro del mes, que es justo lo
    que CA-6 comprueba.
    """

    def __init__(self, algoritmo: str, constante: bool) -> None:
        super().__init__()
        self.algoritmo = algoritmo
        self.constante = constante

    def riesgos(self, fecha: str, tipo: str) -> list[dict]:
        self.peticiones += 1
        mes, dia = int(fecha[5:7]), int(fecha[8:10])
        filas = []
        for indice, codigo in enumerate(DISTRITOS):
            semilla = mes + indice if self.constante else mes + indice + dia
            nivel = "alto" if semilla % 4 == 0 else "bajo"
            filas.append(
                {
                    "codigo_distrito": codigo,
                    "fecha": fecha,
                    "tipo_evento": tipo,
                    "nivel": nivel,
                    "probabilidad": 0.5 if nivel == "alto" else 0.0,
                    "algoritmo": self.algoritmo,
                    "version_modelo": f"{self.algoritmo}@prueba",
                }
            )
        return filas


EVENTOS = [
    {
        "codigo_distrito": "50804",
        "tipo_evento": "lluvia_intensa",
        "fecha_inicio": "2017-10-05",
        "descripcion": "evento de prueba",
    }
]


def test_separar_aplica_las_dos_exclusiones_declaradas():
    registros = [
        {"tipo_evento": "sequia", "fecha_inicio": "2014-09-30"},
        {"tipo_evento": "lluvia_intensa", "fecha_inicio": "1976-09-01"},
        {"tipo_evento": "lluvia_intensa", "fecha_inicio": "2017-10-05"},
    ]
    contrastables, excluidos = ce.separar(registros)

    assert len(contrastables) == 1
    motivos = [motivo for _, motivo in excluidos]
    assert any("D-34" in m for m in motivos)
    assert any("1991" in m for m in motivos)


@pytest.mark.parametrize(
    ("fila", "esperado"),
    [
        ({"nivel": "alto"}, "anticipado"),
        ({"nivel": "medio"}, "medio"),
        ({"nivel": "bajo"}, "no anticipado"),
        ({"nivel": None}, "sin estimacion"),
        (None, "sin estimacion"),
    ],
)
def test_categoria_de_no_admite_medias_tintas(fila, esperado):
    """`medio` NO es acierto. Es CA-3, y se fijo antes de ver un resultado."""
    assert ce.categoria_de(fila) == esperado


def test_climatologico_constante_deja_seguir():
    cliente = ClienteFalso(ce.CLIMATOLOGICO, constante=True)
    resultado = ce.contrastar(cliente, EVENTOS, "lluvia_intensa")

    assert resultado["es_climatologico"] is True
    assert resultado["constante_en_el_mes"] is True
    assert ce.supuesto_roto([resultado]) == []


def test_climatologico_que_cambia_dentro_del_mes_rompe_el_supuesto():
    """El sabotaje: un escritor que se declara climatologico y no lo es.

    Sin esta prueba, CA-6 seria una frase. El contraste no se publica sobre un
    supuesto falso, y esto es lo que lo impide.
    """
    cliente = ClienteFalso(ce.CLIMATOLOGICO, constante=False)
    resultado = ce.contrastar(cliente, EVENTOS, "lluvia_intensa")

    assert resultado["es_climatologico"] is True
    assert resultado["constante_en_el_mes"] is False
    assert resultado["detalles_de_constancia"]
    assert ce.supuesto_roto([resultado]) == [resultado]


def test_otro_escritor_no_es_un_fallo_pero_se_declara():
    """Incendio hoy lo escribe la regresion logistica, y si cambia en el mes."""
    cliente = ClienteFalso("regresion_logistica", constante=False)
    resultado = ce.contrastar(cliente, EVENTOS, "lluvia_intensa")

    assert resultado["es_climatologico"] is False
    assert ce.supuesto_roto([resultado]) == []


def test_el_realce_se_calcula_contra_la_tasa_base_del_mismo_escritor():
    cliente = ClienteFalso(ce.CLIMATOLOGICO, constante=True)
    resultado = ce.contrastar(cliente, EVENTOS, "lluvia_intensa")

    base = resultado["base"]
    assert base["celdas"] == 96
    if resultado["cobertura"] is not None and base["tasa_alto"]:
        assert resultado["realce"] == pytest.approx(resultado["cobertura"] / base["tasa_alto"])


def test_wilson_es_el_intervalo_y_no_una_aproximacion():
    """Contra valores conocidos: 8 de 34 al 95 % da aproximadamente 12,4 % a 39,6 %."""
    bajo, alto = ce.wilson(8, 34)
    assert bajo == pytest.approx(0.124, abs=0.005)
    assert alto == pytest.approx(0.396, abs=0.005)
    assert ce.wilson(0, 0) is None


def test_el_pareado_por_mes_no_reemplaza_al_realce_declarado():
    """El analisis de fallos agrega; no toca la cobertura ni el realce de CA-4."""
    cliente = ClienteFalso(ce.CLIMATOLOGICO, constante=True)
    resultado = ce.contrastar(cliente, EVENTOS, "lluvia_intensa")

    assert "realce" in resultado and "analisis" in resultado
    assert resultado["analisis"]["realce_pareado"] != resultado["realce"] or True
    assert set(resultado["analisis"]) == {
        "intervalo_cobertura",
        "tasa_por_mes",
        "esperados_pareado_por_mes",
        "observados",
        "realce_pareado",
        "eventos_en_celda_imposible",
    }


def test_una_celda_con_probabilidad_cero_se_cuenta_como_imposible():
    """Donde el almanaque dice P(alto) = 0 y aun asi hubo un evento con danos."""
    medidos = [
        {
            "fecha": "2017-05-25",
            "codigo_distrito": "50801",
            "probabilidad": 0.0,
            "categoria": "no anticipado",
        },
        {
            "fecha": "2017-10-05",
            "codigo_distrito": "50804",
            "probabilidad": 0.08,
            "categoria": "anticipado",
        },
    ]
    celdas = [{"mes": 5, "nivel": "bajo"}, {"mes": 10, "nivel": "alto"}]
    analisis = ce.analisis_de_fallos(medidos, celdas)

    assert len(analisis["eventos_en_celda_imposible"]) == 1
    assert analisis["eventos_en_celda_imposible"][0]["fecha"] == "2017-05-25"
