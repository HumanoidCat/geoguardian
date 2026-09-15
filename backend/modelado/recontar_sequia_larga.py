"""
Recuento de episodios de sequia sobre la serie larga del canton. Historia H3.11.

QUE PREGUNTA CONTESTA

**D-34** cerro la sequia con **13 episodios en 34 anos** contra los 30 que pide el
CA-6 de H3.0, y con el minimo por pliegue muy por debajo de 10. H1.16 trajo
**76 anos**. La pregunta es si la sequia sigue sin ser modelable con la serie
larga, o si solo lo parecia porque la serie era corta.

POR QUE ESTE GUION EXISTE Y NO SE CORRE `generar_etiquetas.py`

El CA-1 de H3.11 pedia correr **el mismo guion** sobre la serie larga. No se
puede, y no por comodidad:

  * `generar_etiquetas.py` lee `crudo.medicion_diaria`, que esta **por distrito**,
    y `crudo.serie_canton` **no tiene `codigo_distrito`** porque el CA-9 de H1.16
    y D-47 lo prohiben;
  * y ademas es el guion que produjo el 13 de D-34: **tiene que seguir
    produciendolo**, asi que tampoco se modifica.

Lo que ese criterio pide de verdad -que los dos numeros signifiquen lo mismo- se
cumple **importando** las funciones que deciden que es un episodio, sin copiar ni
una linea: `nivel_sequia`, `acumulado_mensual`, `CalculadorSPI`,
`VENTANA_SPI_MESES`, `HORIZONTE_DIAS`, `Etiqueta`, `rachas_del_canton`,
`episodios`, `particionar`. Si alguien cambia manana la definicion de episodio,
este recuento cambia con ella.

LAS DOS DIFERENCIAS DE METODO QUE SE MIDEN POR SEPARADO

**1. El SPI no tiene periodo de referencia fijo.** `backend/senales/spi.py` ajusta
la gamma **sobre los acumulados que recibe**. Correr la serie larga cambia la vara
al mismo tiempo que cambia la muestra. Por eso la base del SPI y la ventana que se
etiqueta son **dos parametros distintos** de `etiquetar_canton`.

**2. El orden de agregacion es otro.** D-34 hace SPI por distrito, nivel por
distrito y union de los ocho. Aca hay una sola serie: SPI del canton, nivel,
rachas. El SPI de la lluvia promediada no es la union de los SPI. El control de
CA-7 -misma ventana que D-34, con esta serie- es lo unico que dice si los dos
metodos hablan del mismo fenomeno.

LA COMBINACION QUE CUENTA, FIJADA ANTES DE VER NINGUN NUMERO

Hay dos palancas y cuatro combinaciones. **CA-8** dice cual se compara contra el
umbral: **serie completa con base completa**. Las otras tres son control y no
candidatas. Este guion las imprime todas, en ese orden, y marca cual es cual.

    python -m backend.modelado.recontar_sequia_larga
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado.etiquetado import (  # noqa: E402
    HORIZONTE_DIAS,
    VENTANA_SPI_MESES,
    CalculadorSPI,
    Etiqueta,
    acumulado_mensual,
    nivel_sequia,
)
from backend.modelado.generar_etiquetas import (  # noqa: E402
    episodios,
    episodios_por_pliegue,
    rachas_del_canton,
)
from backend.modelado.particion import particionar  # noqa: E402
from contratos.enums import TipoEvento  # noqa: E402

#: Umbrales de CA-6 de H3.0, fijados antes de mirar el dato. No se tocan.
MINIMO_TOTAL = 30
MINIMO_POR_PLIEGUE = 10

#: La serie es del canton: un solo "distrito" con un codigo que no existe en
#: `geo.distrito`, justamente para que nadie lo confunda con uno real.
CANTON = "canton"

SQL_SERIE = """
    SELECT fecha, precipitacion_mm
      FROM crudo.serie_canton
     ORDER BY fecha
"""

#: La ventana de D-34 no se escribe a mano: se pregunta. D-34 conto sobre lo que
#: habia en `crudo.medicion_diaria`, asi que esa tabla es la que dice cual fue.
SQL_VENTANA_CHIRPS = """
    SELECT min(fecha), max(fecha) FROM crudo.medicion_diaria
"""


def etiquetar_canton(
    serie: dict[date, float | None],
    base: tuple[date, date],
    ventana: tuple[date, date],
) -> list[Etiqueta]:
    """Etiqueta la sequia del canton, con la base del SPI y la ventana separadas.

    `base` es el periodo sobre el que se ajusta la gamma; `ventana` es el rango de
    fechas `t` que se etiqueta. Separarlos es lo que permite medir el efecto de la
    base sin mezclarlo con el de tener mas anos.

    El nivel sale de `nivel_sequia` y el SPI de `CalculadorSPI`, los dos
    importados: la definicion de sequia es la de H3.0 y no una copia.
    """
    recorte = {f: v for f, v in serie.items() if base[0] <= f <= base[1]}
    totales, meses, claves = acumulado_mensual(recorte)
    valores = CalculadorSPI().spi(totales, VENTANA_SPI_MESES, meses)
    spi_por_mes = dict(zip(claves, valores, strict=True))

    etiquetas: list[Etiqueta] = []
    t = ventana[0]
    while t <= ventana[1]:
        # El SPI-6 del mes que contiene al final del horizonte, igual que
        # `etiquetar_distrito`. La prueba de equivalencia lo comprueba.
        fin = t + timedelta(days=HORIZONTE_DIAS)
        etiquetas.append(
            Etiqueta(
                codigo_distrito=CANTON,
                fecha=t,
                sequia=nivel_sequia(spi_por_mes.get((fin.year, fin.month))),
                lluvia_intensa=None,
                incendio=None,
            )
        )
        t += timedelta(days=1)
    return etiquetas


def meses_sin_spi(serie: dict[date, float | None], base: tuple[date, date]) -> list[str]:
    """CA-9: que meses no tienen SPI, y por que. No es lo mismo cero que nada.

    Dos motivos distintos y los dos se declaran:
      * el arranque del SPI-6, que no existe hasta el sexto mes;
      * un mes con algun dia sin dato, que `acumulado_mensual` deja en None por
        D-07 -y esta bien: un total al que le faltan dias es menor por
        construccion y entraria como sequia.
    """
    recorte = {f: v for f, v in serie.items() if base[0] <= f <= base[1]}
    totales, _, claves = acumulado_mensual(recorte)

    salida = []
    for i, (clave, total) in enumerate(zip(claves, totales, strict=True)):
        etiqueta = f"{clave[0]}-{clave[1]:02d}"
        if i < VENTANA_SPI_MESES - 1:
            salida.append(f"{etiqueta} (arranque del SPI-{VENTANA_SPI_MESES})")
        elif total is None:
            salida.append(f"{etiqueta} (algun dia sin dato, D-07)")
    return salida


def por_pliegue(
    etiquetas: list[Etiqueta],
    ventana: tuple[date, date],
    con_la_particion_de_h30: bool = False,
) -> list[int] | None:
    """Episodios de entrenamiento por pliegue.

    Con `con_la_particion_de_h30` se usa **`episodios_por_pliegue` tal cual**, que
    parte sobre el periodo observado del evento -1991 a 2024-. Es lo que hizo
    D-34, asi que es lo que corresponde para el control de CA-7.

    Para la serie larga esa funcion no sirve: llama a `particionar(evento)` sin
    ventana y partiria 1991-2024 aunque se le pasen etiquetas desde 1950. Ahi se
    le pasa la ventana a `particionar` -parametro que ya tiene- y se cuenta con
    **la misma expresion** que usa esa funcion, sobre las mismas rachas.
    """
    if con_la_particion_de_h30:
        return episodios_por_pliegue({CANTON: etiquetas}, TipoEvento.SEQUIA)

    try:
        pliegues = particionar(TipoEvento.SEQUIA, desde=ventana[0], hasta=ventana[1])
    except Exception:  # noqa: BLE001 - periodo insuficiente u otro motivo declarado
        return None

    canton = rachas_del_canton({CANTON: etiquetas}, TipoEvento.SEQUIA)
    return [
        sum(1 for i, f in canton if i >= desde and f <= hasta)
        for desde, hasta in (p.entrenamiento for p in pliegues)
    ]


def contar(
    serie: dict[date, float | None],
    base: tuple[date, date],
    ventana: tuple[date, date],
    con_la_particion_de_h30: bool = False,
) -> dict:
    etiquetas = etiquetar_canton(serie, base, ventana)
    rachas = rachas_del_canton({CANTON: etiquetas}, TipoEvento.SEQUIA)
    pliegues = por_pliegue(etiquetas, ventana, con_la_particion_de_h30)
    return {
        "base": base,
        "ventana": ventana,
        "episodios": episodios(etiquetas, TipoEvento.SEQUIA),
        "rachas": rachas,
        "pliegues": pliegues,
        "minimo_pliegue": min(pliegues) if pliegues else None,
        "anios": (ventana[1] - ventana[0]).days / 365.25,
    }


def imprimir(titulo: str, r: dict, nota: str = "") -> None:
    b, v = r["base"], r["ventana"]
    print(f"\n{titulo}")
    print(f"  ventana etiquetada  {v[0]} a {v[1]}   ({r['anios']:.1f} anios)")
    print(f"  base del SPI        {b[0]} a {b[1]}")
    print(f"  episodios           {r['episodios']}")
    if r["pliegues"] is None:
        print("  por pliegue         no se pudo particionar (periodo insuficiente)")
    else:
        print(f"  por pliegue         {r['pliegues']}   minimo {r['minimo_pliegue']}")
    if nota:
        print(f"  {nota}")


def main() -> int:
    # Adentro de `main` y no arriba, igual que `generar_etiquetas.py`: asi el
    # modulo se puede importar -y probar- sin el controlador de la base.
    from basedatos.conexion import ErrorConexion, conectar

    print("Recuento de sequias sobre la serie larga · H3.11 · D-34")

    try:
        with conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(SQL_SERIE)
            serie = {f: (None if v is None else float(v)) for f, v in cursor.fetchall()}
            cursor.execute(SQL_VENTANA_CHIRPS)
            chirps_desde, chirps_hasta = cursor.fetchone()
    except ErrorConexion as causa:
        print(f"FALLO de conexion: {causa}", file=sys.stderr)
        return 1

    if not serie:
        print("crudo.serie_canton esta vacia. Correr cargar_serie_canton primero.")
        return 1

    fechas = sorted(serie)
    larga = (fechas[0], fechas[-1] - timedelta(days=HORIZONTE_DIAS))
    corta = (chirps_desde, chirps_hasta - timedelta(days=HORIZONTE_DIAS))

    sin_dato = [f for f, v in serie.items() if v is None]
    con_dato = len(serie) - len(sin_dato)
    print(f"\n  serie      {len(serie)} dias, {fechas[0]} a {fechas[-1]}, {con_dato} con dato")
    if sin_dato:
        # CA-9: un dia sin dato no es un dia con cero. Se nombra, porque arrastra
        # su mes entero a None en `acumulado_mensual` (D-07) y hay que saber cual.
        print(f"  sin dato   {', '.join(str(f) for f in sin_dato[:10])}")
    print(f"  ventana de D-34   {chirps_desde} a {chirps_hasta}  (de crudo.medicion_diaria)")

    faltantes = meses_sin_spi(serie, larga)
    print(f"\nCA-9 · meses sin SPI sobre la serie completa: {len(faltantes)}")
    for m in faltantes:
        print(f"    {m}")

    # -- CA-7: el control. Va PRIMERO, y contra los 13 de D-34. --------------- #
    control = contar(serie, base=corta, ventana=corta, con_la_particion_de_h30=True)
    imprimir(
        "CA-7 · CONTROL · ventana de D-34, base de D-34 (efecto del orden de agregacion)",
        control,
        f"D-34 conto 13 con los ocho distritos. Diferencia: {control['episodios'] - 13:+d}",
    )

    # -- CA-6: el efecto de la base, con la ventana fija. --------------------- #
    base_larga = contar(serie, base=larga, ventana=corta, con_la_particion_de_h30=True)
    imprimir(
        "CA-6 · CONTROL · ventana de D-34, base completa (efecto de la vara)",
        base_larga,
        f"Contra el control: {base_larga['episodios'] - control['episodios']:+d}",
    )

    # -- la cuarta celda, por completitud. ----------------------------------- #
    cruzada = contar(serie, base=corta, ventana=larga)
    imprimir("CONTROL · ventana completa, base de D-34 (no es candidata)", cruzada)

    # -- CA-8: la que se compara contra el umbral. --------------------------- #
    headline = contar(serie, base=larga, ventana=larga)
    imprimir("CA-8 · EL RECUENTO · ventana completa, base completa", headline)

    print("\nCA-3 · los dos umbrales de CA-6 de H3.0, por separado:")
    total_ok = headline["episodios"] >= MINIMO_TOTAL
    minimo = headline["minimo_pliegue"]
    pliegue_ok = minimo is not None and minimo >= MINIMO_POR_PLIEGUE
    print(
        f"  total          {headline['episodios']:>3} contra {MINIMO_TOTAL:>3}   "
        f"{'alcanza' if total_ok else 'NO alcanza'}"
    )
    print(
        f"  peor pliegue   {str(minimo):>3} contra {MINIMO_POR_PLIEGUE:>3}   "
        f"{'alcanza' if pliegue_ok else 'NO alcanza'}"
    )

    print("\nVEREDICTO")
    if total_ok and pliegue_ok:
        print("  La sequia pasa los dos umbrales sobre la serie larga.")
        print("  CA-5: pasar el umbral abre la puerta, no la cruza. Modelar es otra")
        print("  historia, con su propia medicion.")
    else:
        print("  La sequia NO es modelable tampoco sobre la serie larga.")
        print("  D-34 se sostiene, y ahora con mas evidencia en vez de con menos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
