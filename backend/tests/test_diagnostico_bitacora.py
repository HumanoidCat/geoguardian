"""
Pruebas de `backend/calidad/diagnostico_bitacora.py`. Historia H12.4.

POR QUE EXISTEN, SI YA HAY UN VERIFICADOR CON 21 COMPROBACIONES
---------------------------------------------------------------

**Porque el verificador no corre en el CI.** `.github/workflows/ci.yml` invoca
los verificadores uno por uno, a mano, y ahi solo estan `verificar_h61`, `h30`,
`h31`, `h32`, `h36`, `h62` y `h14`. No estan `h41`, `h42`, `h12_1`, `h3_7`,
`h12_3` ni `h12_4`.

Un control que solo corre cuando alguien se acuerda **no protege nada**, y es la
misma forma de I-52: el codigo existe y nadie lo ejecuta.

El CI si corre `python -m pytest backend`, asi que lo que viva aqui se ejecuta en
cada empuje sin que nadie tenga que agregarlo a ningun archivo ajeno.

QUE PROTEGEN
------------

Las decisiones que un cambio distraido puede romper sin que se note:

  * que `filas_leidas` y `filas` **no se comparen entre si**, que fue el defecto
    original de este modulo;
  * que una corrida sin `filas_leidas` **no pase en silencio**;
  * que no se opine de lo que no se puede juzgar;
  * y que la salida no diga que todo esta bien cuando solo dice que no vio nada.

Los numeros salen de la tabla real, medidos el 2026-09-13, y cada uno dice si
esta medido o reconstruido.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from backend.calidad.diagnostico_bitacora import (
    HORAS_COLGADA,
    UMBRAL_COBERTURA,
    Corrida,
    ausencias,
    clasificar,
    encabezado,
    esperadas,
    redactar,
    senales_de,
)

AHORA = datetime(2026, 9, 13, 12, 0, 0)
INGESTA = "ingesta.lluvia_intensa"
ESTIMACION = "estimacion.riesgo"
SERIES = {INGESTA: 8}

#: Corrida 63, MEDIDA: ventana 2025-12-01 a 2026-09-05 (279 dias x 8 = 2232),
#: la fuente trajo 1944 y se escribieron 1712.
ESPERADAS_63 = 2232
LEIDAS_63 = 1944


def _corrida(id_: int = 1, proceso: str = INGESTA, **extra) -> Corrida:
    base = {
        "id": id_,
        "proceso": proceso,
        "estado": "exitosa",
        "iniciada_en": AHORA - timedelta(hours=3),
        "terminada_en": AHORA - timedelta(hours=2),
        "filas": 1712,
        "filas_leidas": LEIDAS_63,
        "ventana_desde": date(2025, 12, 1),
        "ventana_hasta": date(2026, 9, 5),
    }
    base.update(extra)
    return Corrida(**base)


# --------------------------------------------------------------------------- #
# Lo pedido sale de la ventana, no de `filas`                                   #
# --------------------------------------------------------------------------- #


def test_lo_esperado_sale_de_la_ventana_y_no_de_las_filas_escritas():
    """
    **Es la prueba que sostiene el modulo entero.**

    La primera version comparaba `filas_leidas` contra `filas` como si una
    contuviera a la otra. Son etapas distintas: lo que trajo la fuente y lo que
    se escribio. Si alguien vuelve a cruzarlas, esta prueba lo detiene.
    """
    assert esperadas(_corrida(), SERIES) == ESPERADAS_63


def test_filas_leidas_mayor_que_filas_no_es_un_error():
    """Corrida 63 medida: 1944 traidas y 1712 escritas, porque el `ON CONFLICT`
    salto 232 que ya estaban. Bajo la suposicion vieja esto era imposible."""
    corrida = _corrida()
    assert corrida.filas_leidas > corrida.filas
    assert clasificar(corrida, AHORA, SERIES) is None


def test_la_latencia_de_d40_no_se_confunde_con_un_fallo():
    """
    A la corrida 63 le faltan 288 series, que son **36 dias por 8 distritos**
    despues del 2026-07-31: exactamente la latencia que declara D-40.

    Con un umbral de 0,9 esta corrida **sana** se marcaria. El argumento del
    umbral esta medido, no supuesto.
    """
    proporcion = LEIDAS_63 / ESPERADAS_63
    assert UMBRAL_COBERTURA < proporcion < 0.9


# --------------------------------------------------------------------------- #
# Las senales                                                                   #
# --------------------------------------------------------------------------- #


def test_marca_la_forma_de_i43():
    """
    24 series de 1992, sobre la ventana **medida** de la corrida 39.

    Las 24 son reconstruidas: la tabla nunca las registro, y ese es el defecto
    que esta historia existe para atrapar.
    """
    i43 = _corrida(
        43,
        filas=1968,
        filas_leidas=24,
        ventana_desde=date(2025, 12, 29),
        ventana_hasta=date(2026, 9, 3),
    )
    senal = clasificar(i43, AHORA, SERIES)

    assert senal is not None
    assert senal.nombre == "cobertura incompleta"


def test_una_corrida_sin_filas_leidas_no_pasa_en_silencio():
    """
    CA-14. Es la corrida 39 real, la del propio I-43.

    La primera version exigia que `filas_leidas` no fuera nulo para juzgar, asi
    que la dejaba pasar **sin decir nada**. Una corrida que no se puede juzgar no
    es una corrida sana: es una corrida sin medir.
    """
    corrida39 = _corrida(
        39,
        filas=1968,
        filas_leidas=None,
        ventana_desde=date(2025, 12, 29),
        ventana_hasta=date(2026, 9, 3),
    )
    senal = clasificar(corrida39, AHORA, SERIES)

    assert senal is not None
    assert senal.nombre == "cobertura no declarada"


def test_marca_una_corrida_en_curso_demasiado_vieja():
    colgada = _corrida(
        62,
        estado="en_curso",
        iniciada_en=AHORA - timedelta(hours=HORAS_COLGADA + 1),
        terminada_en=None,
        filas=None,
        filas_leidas=None,
    )
    senal = clasificar(colgada, AHORA, SERIES)

    assert senal is not None
    assert senal.nombre == "colgada"


def test_con_todo_en_orden_no_inventa_ninguna_senal():
    """
    Un diagnosticador que siempre encuentra algo es tan inutil como uno que nunca
    encuentra nada, y es el modo de fallo mas comodo de no ver: nadie se queja de
    una herramienta que avisa de mas hasta que deja de leerla.
    """
    tranquila = [_corrida(1), _corrida(2, proceso=ESTIMACION)]

    assert senales_de(tranquila, AHORA, SERIES) == []
    assert ausencias(tranquila, AHORA) == []


def test_una_corrida_con_dos_problemas_se_reporta_una_vez():
    """El orden de clasificacion es contrato: gana lo mas grave. El mismo
    problema con tres nombres no es mas informacion, es mas ruido."""
    corrida = _corrida(
        19,
        estado="en_curso",
        iniciada_en=AHORA - timedelta(hours=HORAS_COLGADA + 2),
        terminada_en=None,
        filas_leidas=24,
    )
    senal = clasificar(corrida, AHORA, SERIES)

    assert senal is not None
    assert senal.nombre == "colgada"


# --------------------------------------------------------------------------- #
# No opinar de lo que no se puede juzgar                                        #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "cambios",
    [
        pytest.param({"proceso": "api"}, id="proceso sin series declaradas"),
        pytest.param(
            {"ventana_desde": None, "ventana_hasta": None},
            id="corrida sin ventana declarada",
        ),
    ],
)
def test_no_se_juzga_la_cobertura_de_lo_que_no_se_sabe_que_esperar(cambios):
    """
    **No saber se dice, no se supone.** Es lo que separa un diagnostico de una
    corazonada, y es la misma regla que D-07 aplica a los datos.
    """
    corrida = _corrida(17, filas_leidas=1, **cambios)

    assert esperadas(corrida, SERIES) is None
    assert clasificar(corrida, AHORA, SERIES) is None


def test_la_ausencia_se_busca_porque_no_esta_en_la_tabla():
    """
    ES LA UNICA SENAL QUE NO SALE DE UNA FILA. Un cron caido no escribe nada, asi
    que recorrer la tabla no lo encuentra nunca.

    Es la senal que diagnostico la causa de I-52.
    """
    faltantes = ausencias([_corrida(1, proceso=INGESTA)], AHORA)

    assert [s.proceso for s in faltantes] == [ESTIMACION]


# --------------------------------------------------------------------------- #
# La salida                                                                     #
# --------------------------------------------------------------------------- #


def test_sin_senales_no_se_dice_que_todo_este_bien():
    """Ausencia de senal conocida no es ausencia de problema, y la salida tiene
    que decirlo con esas palabras."""
    texto = redactar([])

    assert "Ninguna senal" in texto
    assert "NO dice que todo este bien" in texto


def test_lo_leido_de_texto_libre_se_marca_como_conjetura():
    """El texto ya engano una vez: en I-43 el mensaje decia «exitosa»."""
    sin_codigo = clasificar(
        _corrida(4, estado="fallida", mensaje="permission denied"), AHORA, SERIES
    )
    con_codigo = clasificar(_corrida(5, estado="fallida", sqlstate="42501"), AHORA, SERIES)

    assert sin_codigo is not None and sin_codigo.conjetura
    assert con_codigo is not None and not con_codigo.conjetura
    assert "CONJETURA" in redactar([sin_codigo])


def test_el_encabezado_lleva_la_declaracion_de_ceguera_pegada():
    """
    CA-4, y no es cosmetico: **esta salida se pega en un mensaje**. Si la
    advertencia vive en el documento de criterios se pierde en el primer copiado.
    Es la misma razon que CA-7 de H4.2.
    """
    texto = encabezado("base LOCAL: geoguardian en localhost:5433", 3, {"sqlstate": 0}, "8")

    assert "NO PUEDE OPINAR" in texto
    assert "sqlstate" in texto
    assert "localhost:5433" in texto


def test_dos_corridas_dan_la_misma_salida():
    """Sin azar y sin depender del orden de la consulta."""
    mezcla = [_corrida(1), _corrida(2, filas_leidas=24), _corrida(3, estado="parcial")]

    assert redactar(senales_de(mezcla, AHORA, SERIES)) == redactar(
        senales_de(mezcla, AHORA, SERIES)
    )


def test_toda_senal_trae_evidencia_y_accion():
    """Una senal sin evidencia es una opinion; una sin accion no le sirve a quien
    esta operando a las dos de la manana."""
    senales = senales_de([_corrida(3, estado="parcial", filas=800)], AHORA, SERIES)

    assert senales
    assert all(s.evidencia.strip() and s.accion.strip() for s in senales)
