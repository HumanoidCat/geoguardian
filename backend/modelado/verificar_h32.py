"""Comprueba los criterios de aceptacion de H3.2, la particion temporal.

Criterios en `docs/evidencias/objetivos/H3.2-criterios-aceptacion.md`.

CORRE SIN BASE DE DATOS

Todo lo de aca son propiedades de la **particion**, no del dato cargado. La
distribucion de clases por pliegue -que si necesita la base- la mide
`generar_etiquetas.py`.

INCLUYE UNA PRUEBA NEGATIVA

CA-8 la exige: una particion armada a proposito **con fuga** tiene que salir en
rojo. Un verificador que nunca vio un rojo no prueba que detecte nada. Es el
defecto que tuvo `verificar_h66`, que copiaba la regla en vez de comprobarla y
daba verde con el umbral cambiado.

Uso:
    python -m backend.modelado.verificar_h32

Sale con codigo 1 si algun criterio se rompe.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado.etiquetado import (  # noqa: E402
    COBERTURA_FOCOS,
    HORIZONTE_DIAS,
    VENTANA_ACUMULADO_DIAS,
    etiquetar_distrito,
)
from backend.modelado.particion import (  # noqa: E402
    CARACTERISTICA,
    ESTADISTICOS,
    ETIQUETA,
    PLIEGUES,
    Pliegue,
    cortes_mensuales,
    filas_de_entrenamiento,
    filas_de_prueba,
    fin_de_mes,
    particionar,
    periodo_observado,
    resumen_f1,
    ultima_fecha_que_mira,
)
from contratos.enums import NivelRiesgo, TipoEvento  # noqa: E402

fallos: list[str] = []


def comprobar(descripcion: str, condicion: bool, detalle: str = "") -> None:
    print(f"  {'OK  ' if condicion else 'FALLO'}  {descripcion}")
    if not condicion:
        fallos.append(descripcion)
        if detalle:
            print(f"        {detalle}")


def hay_fuga(evento: TipoEvento, pliegue: Pliegue) -> bool:
    """True si alguna fila de entrenamiento mira dentro de la prueba."""
    t = pliegue.entrenamiento[1]
    return ultima_fecha_que_mira(evento, t) >= pliegue.prueba[0]


def main() -> int:
    print("\nCriterios de aceptacion de H3.2\n")

    particiones = {e: particionar(e) for e in TipoEvento}

    # ---------------------------------------------------------------- CA-1 -- #
    print("CA-1, la particion es una funcion y da lo mismo cada vez:")

    for evento in TipoEvento:
        a, b = particionar(evento), particionar(evento)
        comprobar(f"{evento.value}: dos llamadas dan la misma particion", a == b)

    comprobar(
        "el numero de pliegues es el que declara el modulo",
        all(len(p) == PLIEGUES for p in particiones.values()),
    )

    # ---------------------------------------------------------------- CA-2 -- #
    print("\nCA-2, el embargo se calcula por evento y no hay fuga:")

    # El alcance se comprueba contra `etiquetado.py`, no contra numeros escritos
    # a mano aca. Si el etiquetado cambia su ventana, esto lo detecta.
    t = date(2010, 3, 10)
    comprobar(
        "incendio alcanza t+7, como el horizonte del etiquetado",
        ultima_fecha_que_mira(TipoEvento.INCENDIO, t) == t + timedelta(days=HORIZONTE_DIAS),
    )
    comprobar(
        "lluvia alcanza t+7 y NO t+9: el acumulado se acota para no pasarse",
        ultima_fecha_que_mira(TipoEvento.LLUVIA_INTENSA, t) == t + timedelta(days=HORIZONTE_DIAS),
        f"CA-2 estimo {HORIZONTE_DIAS + VENTANA_ACUMULADO_DIAS - 1} dias. El etiquetado "
        "acota el ultimo acumulado a empezar en t+5, de modo que termine en t+7.",
    )
    comprobar(
        "sequia alcanza el FIN del mes que contiene a t+7",
        ultima_fecha_que_mira(TipoEvento.SEQUIA, t)
        == fin_de_mes(t + timedelta(days=HORIZONTE_DIAS)),
    )

    # El caso que distingue la sequia de los otros dos: `t+7` a principio de mes.
    inicio_de_mes = date(2010, 3, 25)  # t+7 = 2010-04-01
    comprobar(
        "con t+7 al inicio de un mes, la sequia alcanza treinta dias mas",
        (
            ultima_fecha_que_mira(TipoEvento.SEQUIA, inicio_de_mes)
            - ultima_fecha_que_mira(TipoEvento.INCENDIO, inicio_de_mes)
        ).days
        == 29,
        "es la razon por la que el embargo no puede ser una constante unica",
    )

    for evento, pliegues in particiones.items():
        comprobar(
            f"{evento.value}: ninguna fila de entrenamiento mira dentro de la prueba",
            not any(hay_fuga(evento, p) for p in pliegues),
        )
        comprobar(
            f"{evento.value}: todos los pliegues descartan al menos un dia",
            all(p.dias_de_embargo >= 1 for p in pliegues),
            "un embargo de cero dias con horizonte de siete es fuga segura",
        )

    # ---------------------------------------------------------------- CA-3 -- #
    print("\nCA-3, los cortes caen en frontera de mes:")

    for evento, pliegues in particiones.items():
        comprobar(
            f"{evento.value}: toda prueba empieza el dia 1 de un mes",
            all(p.prueba[0].day == 1 for p in pliegues),
        )

    # Y la consecuencia que importa: un episodio de sequia dura mas de dos meses
    # -66,3 filas, medido en H3.0- asi que el corte no puede partirlo por el
    # medio. Con el corte en frontera de mes, la etiqueta del ultimo dia de
    # entrenamiento sale de un mes distinto al del primer dia de prueba.
    for p in particiones[TipoEvento.SEQUIA]:
        mes_entrena = fin_de_mes(p.entrenamiento[1] + timedelta(days=HORIZONTE_DIAS))
        mes_prueba = fin_de_mes(p.prueba[0] + timedelta(days=HORIZONTE_DIAS))
        comprobar(
            f"pliegue {p.indice}: el SPI del borde sale de meses distintos",
            mes_entrena != mes_prueba,
            f"entrenamiento cierra con el mes que termina el {mes_entrena}, "
            f"la prueba abre con el que termina el {mes_prueba}",
        )

    # ---------------------------------------------------------------- CA-4 -- #
    print("\nCA-4, cada evento se parte sobre su propio periodo observado:")

    comprobar(
        "el incendio arranca donde arranca el satelite, no donde la serie climatica",
        periodo_observado(TipoEvento.INCENDIO) == COBERTURA_FOCOS,
        "es I-11: partirlo sobre 1991 pondria cero episodios en el primer bloque",
    )
    comprobar(
        "sequia y lluvia arrancan antes que el incendio",
        periodo_observado(TipoEvento.SEQUIA)[0] < periodo_observado(TipoEvento.INCENDIO)[0],
    )
    comprobar(
        "ninguna particion se sale de su periodo observado",
        all(
            p.entrenamiento[0] >= periodo_observado(e)[0] and p.prueba[1] <= periodo_observado(e)[1]
            for e, ps in particiones.items()
            for p in ps
        ),
    )

    # ---------------------------------------------------------------- CA-5 -- #
    print("\nCA-5, la ventana es expansiva y los bloques no se solapan:")

    for evento, pliegues in particiones.items():
        crece = all(
            pliegues[i].entrenamiento[1] < pliegues[i + 1].entrenamiento[1]
            for i in range(len(pliegues) - 1)
        )
        comprobar(f"{evento.value}: el entrenamiento crece en cada pliegue", crece)
        comprobar(
            f"{evento.value}: todos entrenan desde la misma fecha inicial",
            len({p.entrenamiento[0] for p in pliegues}) == 1,
            "es lo que distingue la ventana expansiva de la deslizante",
        )
        comprobar(
            f"{evento.value}: los bloques de prueba van hacia adelante y no se solapan",
            all(
                pliegues[i].prueba[1] < pliegues[i + 1].prueba[0] for i in range(len(pliegues) - 1)
            ),
        )
        comprobar(
            f"{evento.value}: la prueba siempre es futuro del entrenamiento",
            all(p.entrenamiento[1] < p.prueba[0] for p in pliegues),
        )

    # ---------------------------------------------------------------- CA-6 -- #
    print("\nCA-6, cada estadistico esta clasificado y el corte se pide, no se deriva:")

    comprobar(
        "todo estadistico del pipeline esta clasificado",
        all(v in (ETIQUETA, CARACTERISTICA) for v in ESTADISTICOS.values()),
        "un estadistico sin clasificar es un defecto, no una omision de redaccion",
    )
    comprobar(
        "y la tabla no esta vacia",
        len(ESTADISTICOS) >= 4,
        "si se vacia, esta comprobacion pasa sin comprobar nada",
    )

    # El helper existe para que nadie vuelva a derivar el corte por su cuenta.
    todas = [date(2005, 1, 1) + timedelta(days=d) for d in range(0, 7000, 30)]
    for evento, pliegues in particiones.items():
        p = pliegues[2]
        entrena = filas_de_entrenamiento(p, todas)
        prueba = filas_de_prueba(p, todas)
        comprobar(
            f"{evento.value}: entrenamiento y prueba no comparten ni una fecha",
            not (set(entrena) & set(prueba)),
        )
        comprobar(
            f"{evento.value}: ninguna fila de entrenamiento cae despues del corte",
            all(f < p.prueba[0] for f in entrena),
        )

    # ---------------------------------------------------------------- CA-7 -- #
    print("\nCA-7, el F1-macro se agrega promediando pliegues y con su dispersion:")

    media, desv, valores = resumen_f1([0.60, 0.62, 0.58, 0.61, 0.59])
    comprobar("la media es el promedio simple de los pliegues", abs(media - 0.60) < 1e-9)
    comprobar(
        "devuelve los valores individuales, no solo el resumen",
        valores == [0.60, 0.62, 0.58, 0.61, 0.59],
    )
    comprobar("la desviacion distingue pliegues parejos de dispares", desv < 0.02)

    _, desv_dispar, _ = resumen_f1([0.30, 0.90, 0.35, 0.85, 0.40])
    comprobar(
        "y sube cuando los pliegues no coinciden",
        desv_dispar > 0.2,
        "con clases del 0,87 % un pliegue afortunado mueve el promedio; sin la "
        "dispersion nadie puede notarlo",
    )

    # ---------------------------------------------------------------- CA-8 -- #
    print("\nCA-8, la prueba negativa: una particion con fuga sale en rojo:")

    # Se arma a mano el caso que el embargo evita: entrenamiento pegado a la
    # prueba, sin descartar nada.
    corte = date(2010, 6, 1)
    con_fuga = Pliegue(
        indice=0,
        entrenamiento=(date(2005, 1, 1), corte - timedelta(days=1)),
        prueba=(corte, date(2012, 12, 31)),
        embargo=None,
    )
    for evento in TipoEvento:
        comprobar(
            f"{evento.value}: el detector encuentra la fuga cuando la hay",
            hay_fuga(evento, con_fuga),
            "si esto pasara en verde, el detector no detecta nada",
        )

    # Y que el etiquetado real coincide con lo que el detector supone: un foco
    # puesto justo despues del corte etiqueta una fila anterior al corte.
    plano = {corte + timedelta(days=d): 5.0 for d in range(-40, 40)}
    fila = etiquetar_distrito(
        "50804",
        plano,
        [corte + timedelta(days=1)],
        corte - timedelta(days=1),
        corte - timedelta(days=1),
        cobertura_focos=(date(2001, 1, 1), date(2024, 12, 31)),
    )[0]
    comprobar(
        "y el etiquetado lo confirma: un foco tras el corte marca una fila previa",
        fila.incendio is NivelRiesgo.ALTO,
        "esta es la fuga concreta que el embargo evita, no una abstraccion",
    )

    # ---------------------------------------------------------------- CA-9 -- #
    print("\nCA-9, la particion queda escrita con sus fechas:")

    from backend.modelado.particion import describir

    texto = describir(TipoEvento.SEQUIA, particiones[TipoEvento.SEQUIA])
    comprobar("el artefacto nombra el periodo observado", "1991-01-01" in texto)
    comprobar(
        "y trae una linea por pliegue con sus fechas",
        all(str(p.prueba[0]) in texto for p in particiones[TipoEvento.SEQUIA]),
    )

    # ------------------------------------------------------------ los cortes - #
    print("\nY las piezas de calculo:")

    cortes = cortes_mensuales(date(1991, 1, 1), date(2024, 12, 31), 6)
    comprobar("seis bloques producen cinco cortes", len(cortes) == 5)
    comprobar("todos los cortes son dia 1", all(c.day == 1 for c in cortes))
    comprobar("y van en orden", cortes == sorted(cortes))
    comprobar("fin_de_mes acierta en febrero bisiesto", fin_de_mes(date(2020, 2, 5)).day == 29)
    comprobar("y en febrero comun", fin_de_mes(date(2021, 2, 5)).day == 28)

    try:
        cortes_mensuales(date(2020, 1, 1), date(2020, 3, 31), 6)
        planta = False
    except ValueError:
        planta = True
    comprobar(
        "se planta si el periodo no alcanza para los bloques pedidos",
        planta,
        "tres meses no se pueden partir en seis bloques, y devolver algo seria peor",
    )

    # ----------------------------------------------------------------------- #
    print()
    if fallos:
        print(f"{len(fallos)} criterios fallaron:\n")
        for f in fallos:
            print(f"  - {f}")
        return 1

    print("Los criterios verificables sin base de datos se cumplen.")
    print("La distribucion por pliegue la mide generar_etiquetas.py contra la base.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
