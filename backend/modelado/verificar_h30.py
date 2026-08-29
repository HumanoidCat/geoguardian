"""Comprueba los criterios de aceptacion de H3.0, el etiquetado.

Criterios en `docs/evidencias/objetivos/H3.0-criterios-aceptacion.md`.

CORRE SIN BASE DE DATOS

Todo lo que se comprueba aca son propiedades del **etiquetado**, no del dato
cargado. Se ejercita con series construidas a mano, donde la respuesta correcta
se conoce de antemano. Asi puede correr en el CI, que no tiene la base llena.

Lo que si necesita la base es la medicion de la distribucion de clases, y eso lo
hace `generar_etiquetas.py`.

Uso:
    python -m backend.modelado.verificar_h30

Sale con codigo 1 si algun criterio se rompe.
"""

from __future__ import annotations

import random
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado.etiquetado import (  # noqa: E402
    COBERTURA_FOCOS,
    HORIZONTE_DIAS,
    ULTIMO_ANIO,
    acumulado_mensual,
    etiquetar_distrito,
    maximo_acumulado_en_ventana,
    nivel_incendio,
    nivel_lluvia,
    nivel_sequia,
)
from backend.modelado.generar_etiquetas import episodios  # noqa: E402
from backend.senales.percentiles import percentil_acumulado, percentil_dias_humedos  # noqa: E402
from contratos.enums import NivelRiesgo, TipoEvento  # noqa: E402

fallos: list[str] = []


def comprobar(descripcion: str, condicion: bool, detalle: str = "") -> None:
    print(f"  {'OK  ' if condicion else 'FALLO'}  {descripcion}")
    if not condicion:
        fallos.append(descripcion)
        if detalle:
            print(f"        {detalle}")


def serie_estacional(desde: date, hasta: date, semilla: int = 7) -> dict[date, float]:
    """Precipitacion diaria con estacion seca, como el Pacifico Norte."""
    generador = random.Random(semilla)
    salida = {}
    dia = desde
    while dia <= hasta:
        base = 1.0 if dia.month in (1, 2, 3, 4) else 12.0
        salida[dia] = max(0.0, generador.gauss(base, base * 1.2))
        dia += timedelta(days=1)
    return salida


def main() -> int:
    print("\nCriterios de aceptacion de H3.0\n")

    desde, hasta = date(1991, 1, 1), date(2024, 12, 31)
    precipitacion = serie_estacional(desde, hasta)
    fechas = sorted(precipitacion)
    serie = [precipitacion[f] for f in fechas]

    # ---------------------------------------------------------------- CA-1 -- #
    print("CA-1, los umbrales son los que declara el contrato:")

    # Se leen del contrato en vez de repetirlos. Si alguien cambia el docstring
    # de NivelRiesgo sin cambiar el codigo, esto no lo detecta; lo que detecta es
    # que el etiquetado use OTROS cortes que los de las funciones del contrato.
    comprobar("SPI de -1.6 es alto", nivel_sequia(-1.6) is NivelRiesgo.ALTO)
    comprobar(
        "SPI de -1.5 es alto, el corte es inclusivo", nivel_sequia(-1.5) is NivelRiesgo.ALTO
    )
    comprobar("SPI de -1.2 es medio", nivel_sequia(-1.2) is NivelRiesgo.MEDIO)
    comprobar(
        "SPI de -1.0 es medio, el corte es inclusivo", nivel_sequia(-1.0) is NivelRiesgo.MEDIO
    )
    comprobar("SPI de -0.9 es bajo", nivel_sequia(-0.9) is NivelRiesgo.BAJO)
    comprobar("un SPI ausente no se convierte en clase", nivel_sequia(None) is None)

    comprobar(
        "lluvia por encima de P99 es alto", nivel_lluvia(100.0, 60.0, 90.0) is NivelRiesgo.ALTO
    )
    comprobar(
        "lluvia entre P95 y P99 es medio", nivel_lluvia(70.0, 60.0, 90.0) is NivelRiesgo.MEDIO
    )
    comprobar(
        "lluvia igual al P95 es bajo, el corte es estricto",
        nivel_lluvia(60.0, 60.0, 90.0) is NivelRiesgo.BAJO,
    )
    comprobar("sin umbral del distrito no hay etiqueta", nivel_lluvia(70.0, None, 90.0) is None)

    # ---------------------------------------------------------------- CA-2 -- #
    print("\nCA-2, lluvia usa el acumulado de 72 h y NO R95p:")

    p95_acumulado = percentil_acumulado(serie, fechas, 95, 3)
    p95_diario = percentil_dias_humedos(serie, fechas, 95)

    comprobar(
        "las dos definiciones dan umbrales distintos",
        p95_acumulado is not None
        and p95_diario is not None
        and abs(p95_acumulado - p95_diario) > 1.0,
        f"acumulado {p95_acumulado}, diario {p95_diario}. Si dieran igual, esta "
        "comprobacion pierde sentido y hay que decirlo.",
    )
    comprobar(
        "el umbral de acumulado es el mayor de los dos",
        p95_acumulado > p95_diario,  # type: ignore[operator]
        "si se invirtiera, usar el equivocado dejaria de inflar las filas en alto "
        "y habria que revisar la medicion de H2.7",
    )

    etiquetas = etiquetar_distrito(
        "50804", precipitacion, [], desde, hasta - timedelta(days=HORIZONTE_DIAS)
    )
    altas_reales = sum(1 for e in etiquetas if e.lluvia_intensa is NivelRiesgo.ALTO)

    # Las mismas etiquetas con el umbral equivocado, para medir el efecto.
    p99_diario = percentil_dias_humedos(serie, fechas, 99)
    altas_con_el_malo = 0
    t = desde
    fin_util = hasta - timedelta(days=HORIZONTE_DIAS)
    while t <= fin_util:
        maximo = maximo_acumulado_en_ventana(
            precipitacion, t + timedelta(days=1), t + timedelta(days=HORIZONTE_DIAS - 2)
        )
        if nivel_lluvia(maximo, p95_diario, p99_diario) is NivelRiesgo.ALTO:
            altas_con_el_malo += 1
        t += timedelta(days=1)

    comprobar(
        "usar R95p inflaria las filas en alto",
        altas_con_el_malo > altas_reales,
        f"con el correcto {altas_reales}, con R95p {altas_con_el_malo} "
        f"({altas_con_el_malo / max(altas_reales, 1):.1f}x)",
    )

    # ---------------------------------------------------------------- CA-3 -- #
    print("\nCA-3, el SPI se pide con el mes calendario:")

    totales, meses, claves = acumulado_mensual(precipitacion)
    comprobar("acumulado_mensual devuelve el mes de cada posicion", len(meses) == len(totales))
    comprobar("los meses van de 1 a 12", set(meses) <= set(range(1, 13)))
    comprobar(
        "el mes declarado coincide con la clave",
        all(mes == clave[1] for mes, clave in zip(meses, claves, strict=True)),
    )

    # ---------------------------------------------------------------- CA-4 -- #
    print("\nCA-4, la ventana es (t, t+7] y no hay fuga:")

    plano = {d: 5.0 for d in precipitacion}
    t = date(2020, 6, 1)

    for desplazamiento, esperado, motivo in (
        (0, NivelRiesgo.BAJO, "un foco en t NO etiqueta la fila de t"),
        (1, NivelRiesgo.ALTO, "un foco en t+1 si la etiqueta"),
        (
            HORIZONTE_DIAS,
            NivelRiesgo.ALTO,
            f"un foco en t+{HORIZONTE_DIAS} entra, el corte es cerrado",
        ),
        (HORIZONTE_DIAS + 1, NivelRiesgo.BAJO, f"un foco en t+{HORIZONTE_DIAS + 1} queda fuera"),
    ):
        fila = etiquetar_distrito("50804", plano, [t + timedelta(days=desplazamiento)], t, t)[0]
        comprobar(motivo, fila.incendio is esperado, f"dio {fila.incendio}")

    # --------------------------------------------------------------- CA-8b -- #
    # Agregado el 2026-08-26, escribiendo los criterios de H3.2. La cuenta de
    # episodios de incendio por pliegue obligo a mirar de donde sale cada uno, y
    # aparecio que la decada de los noventa no tiene satelite detras. Ver I-11.
    print("\nCA-8b, fuera de la cobertura del satelite el incendio es None, no BAJO:")

    inicio_cobertura, fin_cobertura = COBERTURA_FOCOS

    comprobar(
        "sin observacion, cero focos NO es BAJO",
        nivel_incendio(0, ventana_observada=False) is None,
        f"dio {nivel_incendio(0, ventana_observada=False)}",
    )
    comprobar(
        "con observacion, cero focos si es BAJO",
        nivel_incendio(0, ventana_observada=True) is NivelRiesgo.BAJO,
    )

    for t, esperado, motivo in (
        (
            inicio_cobertura - timedelta(days=365),
            None,
            "una fecha muy anterior al satelite sale sin etiqueta",
        ),
        (
            inicio_cobertura - timedelta(days=HORIZONTE_DIAS),
            None,
            "la ventana que asoma un dia por fuera tampoco se etiqueta",
        ),
        (
            inicio_cobertura - timedelta(days=1),
            NivelRiesgo.BAJO,
            "la primera ventana que cae entera adentro si se etiqueta",
        ),
    ):
        fila = etiquetar_distrito("50804", {d: 5.0 for d in precipitacion}, [], t, t)[0]
        comprobar(motivo, fila.incendio is esperado, f"en {t} dio {fila.incendio}")

    # Y que el efecto sea el que se midio: la decada sin satelite es casi un
    # tercio del conjunto. Si esta cuenta cambia, cambio la cobertura.
    sin_observar = sum(1 for e in etiquetas if e.incendio is None)
    comprobar(
        "las filas sin cobertura son ~29 % del distrito, no cero",
        0.25 < sin_observar / len(etiquetas) < 0.33,
        f"{sin_observar} de {len(etiquetas)} = {sin_observar / len(etiquetas):.1%}. "
        f"Cobertura declarada: {inicio_cobertura} a {fin_cobertura}.",
    )

    # ---------------------------------------------------------------- CA-5 -- #
    print("\nCA-5, la sequia no cambia dentro del mes:")

    de_un_mes = [e for e in etiquetas if e.fecha.year == 2015 and e.fecha.month == 7]
    distintos = {e.sequia for e in de_un_mes if e.sequia is not None}
    comprobar(
        "todas las filas de un mes comparten su etiqueta de sequia",
        len(distintos) <= 1,
        f"julio de 2015 tiene {len(distintos)} niveles distintos. La etiqueta sale "
        "del SPI-6 del mes que contiene a t+7, asi que cambia en el borde del mes.",
    )

    # ---------------------------------------------------------------- CA-6 -- #
    print("\nCA-6, los episodios se cuentan y no las filas:")

    focos = [date(2020, 3, 10), date(2020, 3, 11), date(2020, 8, 1)]
    con_focos = etiquetar_distrito("50804", plano, focos, date(2020, 1, 10), date(2020, 12, 20))
    filas_alto = sum(1 for e in con_focos if e.incendio is NivelRiesgo.ALTO)
    cuenta_episodios = episodios(con_focos, TipoEvento.INCENDIO)

    comprobar(
        "un foco marca varias filas seguidas",
        filas_alto > len(focos),
        f"{len(focos)} focos produjeron {filas_alto} filas en alto",
    )
    comprobar(
        "dos focos en dias contiguos son UN episodio",
        cuenta_episodios == 2,
        f"tres focos, dos contiguos, dieron {cuenta_episodios} episodios",
    )
    comprobar("hay menos episodios que filas", cuenta_episodios < filas_alto)

    # ---------------------------------------------------------------- CA-8 -- #
    print("\nCA-8, la ausencia de dato no se convierte en clase:")

    con_hueco = dict(plano)
    hueco = date(2020, 6, 4)
    con_hueco[hueco] = None  # type: ignore[assignment]

    comprobar(
        "un acumulado que toca un hueco devuelve None",
        maximo_acumulado_en_ventana(con_hueco, hueco, hueco) is None,
    )

    mes_con_hueco = {d: v for d, v in con_hueco.items() if d.year == 2020 and d.month == 6}
    totales_hueco, _, _ = acumulado_mensual(mes_con_hueco)
    comprobar("un mes con un dia sin dato sale None", totales_hueco == [None], str(totales_hueco))

    # --------------------------------------------------------------- CA-10 -- #
    print("\nCA-10, la ventana se acota donde termina la fuente mas corta:")

    comprobar(f"el etiquetado declara {ULTIMO_ANIO} como tope", ULTIMO_ANIO == 2024)

    # ---------------------------------------------------------------------- #
    print("\nY el vocabulario del incendio:")

    niveles = {nivel_incendio(n) for n in range(0, 20)}
    comprobar("incendio solo produce alto y bajo", niveles == {NivelRiesgo.ALTO, NivelRiesgo.BAJO})
    comprobar("cero focos es bajo", nivel_incendio(0) is NivelRiesgo.BAJO)
    comprobar("un foco ya es alto", nivel_incendio(1) is NivelRiesgo.ALTO)

    reparto = Counter(e.incendio for e in con_focos)
    comprobar("ninguna fila de incendio sale medio", NivelRiesgo.MEDIO not in reparto)

    if fallos:
        print(f"\n{len(fallos)} criterios fallaron:\n")
        for f in fallos:
            print(f"  - {f}")
        print()
        return 1

    print("\nLos criterios verificables sin base de datos se cumplen.")
    print("La distribucion de clases la mide generar_etiquetas.py contra la base.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
