"""Compara SPI-3, SPI-6 y SPI-12 contra el catalogo de eventos reales.

===========================================================================
POR QUE EXISTE
===========================================================================

**D-19 fija SPI-3 y nadie lo midio.** Se adopto porque es la escala mas comun
en la literatura de sequia agricola, y eso es un argumento de costumbre, no de
evidencia local.

Al leer completo a Quesada-Hernandez, Hidalgo y Alfaro (2020) -que ya estaba
citado, pero cuya ficha se habia escrito sobre el resumen- aparecio que el
trabajo **evalua SPI-6 y SPI-12, no SPI-3**, contra impactos socio-productivos
reales en tres cantones de Guanacaste, y concluye que esas dos son las que
mejor se asocian con los impactos. Es la referencia local mas cercana que
existe, y **no respalda nuestra escala**: respalda la familia y otras dos
escalas concretas.

Ante eso hay tres salidas. Justificar SPI-3 con otro respaldo, cambiar de
escala, o **medir las tres y decidir con el dato**. Esto es lo tercero.

===========================================================================
QUE MIDE, Y CON QUE SE PUEDE Y NO SE PUEDE CONCLUIR
===========================================================================

Para cada escala se rehace el etiquetado de sequia completo -mismos cortes de
McKee, mismo ajuste gamma por mes calendario de D-19- y se contrasta contra
los registros de sequia del catalogo, igual que `contrastar_catalogo.py`.

Se reportan tres numeros por escala, **todos con intervalo de Wilson al 95 %**:

    cobertura   de los eventos catalogados, cuantos estaban marcados
    tasa base   que fraccion de todos los dias-distrito estan marcados
    realce      cobertura / tasa base

**El realce es el unico que decide.** La cobertura sola se sube marcando
siempre, y una escala larga marca mas dias por construccion: el SPI-12 senala
rachas de un ano donde el SPI-3 senala rachas de un trimestre. Comparar
coberturas sin mirar la tasa base premiaria a la escala mas larga por la razon
equivocada.

**LA MUESTRA ES DIMINUTA Y ESO ES PARTE DEL RESULTADO.** El catalogo tiene
**siete** registros de sequia y los siete llevan la misma fecha, 2014-09-30.
Con n = 7 el intervalo de Wilson sobre la cobertura es enorme -de 0 de 7 el
limite superior queda cerca del 35 %- y por eso **el veredicto puede ser que
no hay veredicto**. Se prefiere decir eso a elegir una escala por una decima.

Es la misma disciplina del «empate tecnico» de `comparar.py`: si los
intervalos se solapan, no se declara ganador.

===========================================================================
DOS VENTANAS POR ESCALA, Y LA SEGUNDA NO ES LA MISMA PARA TODAS
===========================================================================

La ventana estricta de 7 dias es la unica comparable entre eventos, pero para
sequia compara cosas que no son comparables: el catalogo registra la fecha de
la **declaratoria administrativa**, que se emite al terminar el episodio.

Asi que cada escala se contrasta ademas con **su propio periodo de
integracion**: 90 dias para SPI-3, 180 para SPI-6, 360 para SPI-12. No es un
numero elegido para que el resultado quede mejor; es lo que el indice integra.

Y hace falta decirlo con todas las letras: **una ventana mas larga detecta mas
por construccion.** Por eso la comparacion entre escalas se hace con la ventana
estricta, que es igual para las tres, y la ventana propia se reporta al lado
como diagnostico, no como puntaje.

Uso:
    python -m backend.modelado.comparar_escalas_spi
    python -m backend.modelado.comparar_escalas_spi --sintetico
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado.contrastar_catalogo import (  # noqa: E402
    CATALOGO,
    MARCA,
    Registro,
    _distancia_mas_cercana,
    leer_catalogo,
)
from backend.modelado.etiquetado import (  # noqa: E402
    HORIZONTE_DIAS,
    acumulado_mensual,
    nivel_sequia,
)
from backend.modelado.intervalos import Intervalo, realce_con_intervalo, wilson  # noqa: E402
from backend.senales.spi import CalculadorSPI  # noqa: E402
from contratos.enums import NivelRiesgo, TipoEvento  # noqa: E402

#: Las tres escalas en disputa.
#:
#: **3** es la de D-19, adoptada sin medir.
#: **6** y **12** son las que Quesada-Hernandez et al. (2020) hallaron mejor
#: asociadas con impactos reales en Guanacaste, que es la provincia de Tilaran.
ESCALAS = (3, 6, 12)


def ventana_propia(escala: int) -> int:
    """Dias del periodo de integracion de la escala. 90, 180 o 360.

    **No es ajustable por bandera, a proposito.** Lo fija el indice, no quien
    corre la herramienta: un SPI-3 integra tres meses y punto. Si fuera un
    parametro, la tentacion seria moverlo hasta que el resultado quedara bien.
    """
    return escala * 30


@dataclass
class Medicion:
    """Lo medido para una escala en una ventana. Los crudos se conservan."""

    escala: int
    ventana: int
    contrastables: int
    detectados: int
    dias_marcados: int
    dias_totales: int
    #: (registro, dias con signo hasta la marca mas cercana; None si no hay ninguna)
    fallos: list[tuple[Registro, int | None]]
    #: Rachas de meses marcados. Separa «marca mucho» de «marca en muchos episodios».
    episodios: int

    @property
    def cobertura(self) -> Intervalo:
        return wilson(self.detectados, self.contrastables)

    @property
    def tasa_base(self) -> Intervalo:
        return wilson(self.dias_marcados, self.dias_totales)

    @property
    def realce(self) -> tuple[float, float, float]:
        return realce_con_intervalo(self.cobertura, self.tasa_base)

    @property
    def distingue(self) -> bool:
        """Si el 1,0 cae dentro del rango del realce, el etiquetado no distingue."""
        _, menor, _ = self.realce
        return menor > 1.0


def etiquetas_de_sequia(
    precipitacion: dict[str, dict[date, float | None]], escala: int
) -> dict[tuple[str, date], NivelRiesgo]:
    """Rehace el etiquetado de sequia completo para una escala del SPI.

    Se replica la logica de `etiquetar_distrito` en lo que toca a sequia -el
    SPI del mes que contiene a `t + HORIZONTE_DIAS`, con los cortes de McKee-
    en vez de llamarla, porque aquella fija la escala en `VENTANA_SPI_MESES`.

    **El ajuste por mes calendario se conserva.** Sin `meses`, la gamma se
    ajusta una sola vez y el indice sigue la estacionalidad en lugar de la
    anomalia: seria comparar tres escalas todas mal calculadas.
    """
    salida: dict[tuple[str, date], NivelRiesgo] = {}

    for codigo, serie in sorted(precipitacion.items()):
        totales, meses, claves = acumulado_mensual(serie)
        valores = CalculadorSPI().spi(totales, escala, meses)
        por_mes = dict(zip(claves, valores, strict=True))

        fechas = sorted(serie)
        if not fechas:
            continue
        t = min(fechas)
        ultimo = max(fechas) - timedelta(days=HORIZONTE_DIAS)
        while t <= ultimo:
            fin = t + timedelta(days=HORIZONTE_DIAS)
            nivel = nivel_sequia(por_mes.get((fin.year, fin.month)))
            if nivel is not None:
                salida[(codigo, t)] = nivel
            t += timedelta(days=1)

    return salida


def contar_episodios(marcados: dict[str, list[date]]) -> int:
    """Rachas de dias marcados consecutivos, sumadas sobre los distritos.

    **Por que importa y no basta con la tasa base.** Un SPI-12 puede marcar el
    mismo numero de dias que un SPI-3 repartidos en la mitad de episodios: son
    dos comportamientos distintos con la misma tasa. La cuenta de episodios es
    lo que los separa, y es tambien el tamano de muestra efectivo para
    cualquier modelo que se entrene despues.
    """
    total = 0
    for fechas in marcados.values():
        ordenadas = sorted(fechas)
        total += sum(
            1 for i, dia in enumerate(ordenadas) if i == 0 or (dia - ordenadas[i - 1]).days > 1
        )
    return total


def medir(
    etiquetas: dict[tuple[str, date], NivelRiesgo],
    registros: list[Registro],
    escala: int,
    ventana_dias: int,
) -> Medicion:
    marcados: dict[str, list[date]] = defaultdict(list)
    dias_marcados = 0
    for (codigo, fecha), nivel in etiquetas.items():
        if nivel in MARCA:
            marcados[codigo].append(fecha)
            dias_marcados += 1

    del_evento = [r for r in registros if r.tipo == TipoEvento.SEQUIA.value]

    contrastables = 0
    detectados = 0
    fallos: list[tuple[Registro, int | None]] = []

    for registro in del_evento:
        ventana = [registro.fecha - timedelta(days=d) for d in range(1, ventana_dias + 1)]
        disponibles = [
            etiquetas[(registro.codigo_distrito, dia)]
            for dia in ventana
            if (registro.codigo_distrito, dia) in etiquetas
        ]
        if not disponibles:
            continue
        contrastables += 1
        if any(nivel in MARCA for nivel in disponibles):
            detectados += 1
        else:
            cercanas = marcados.get(registro.codigo_distrito, [])
            fallos.append((registro, _distancia_mas_cercana(cercanas, registro.fecha)))

    return Medicion(
        escala=escala,
        ventana=ventana_dias,
        contrastables=contrastables,
        detectados=detectados,
        dias_marcados=dias_marcados,
        dias_totales=len(etiquetas),
        fallos=fallos,
        episodios=contar_episodios(marcados),
    )


def veredicto(mediciones: list[Medicion]) -> str:
    """Que escalas quedan descartadas y cuales quedan empatadas.

    **La primera version preguntaba «¿cual gana?» y esa es la pregunta
    equivocada.** Buscaba la de mayor cobertura, veia que se solapaba con otra
    y devolvia «sin veredicto», con lo cual enterraba el unico resultado
    accionable: que la escala que el proyecto usa habia quedado separada **hacia
    abajo** de las otras dos.

    Descartar es mas facil que coronar, y en muestras chicas es lo unico que se
    puede hacer con honestidad. Una escala queda **descartada** si su intervalo
    de cobertura esta enteramente por debajo del de alguna otra: eso si lo
    sostiene la muestra. Entre las que quedan, si sus intervalos se solapan, no
    se ordenan, y se dice.
    """
    utiles = [m for m in mediciones if m.contrastables > 0]
    if not utiles:
        return (
            "SIN VEREDICTO. Ninguna escala tuvo eventos contrastables: el catalogo\n"
            "  no aporta registros de sequia dentro del periodo con etiqueta."
        )

    descartadas = [
        m for m in utiles if any(otra.cobertura.inferior > m.cobertura.superior for otra in utiles)
    ]
    quedan = [m for m in utiles if m not in descartadas]

    lineas: list[str] = []

    if descartadas:
        for m in descartadas:
            superan = [o for o in utiles if o.cobertura.inferior > m.cobertura.superior]
            lineas.append(
                f"DESCARTADA SPI-{m.escala}. Su intervalo {m.cobertura.inferior:.1%}-"
                f"{m.cobertura.superior:.1%} queda enteramente por debajo del de "
                + ", ".join(f"SPI-{o.escala}" for o in superan)
                + f".\n  Y el 1,0 {'cae dentro' if not m.distingue else 'queda fuera'} "
                "del rango de su realce" + (": no distingue." if not m.distingue else ".")
            )
        lineas.append("")

    if len(quedan) == 1:
        m = quedan[0]
        lineas.append(
            f"QUEDA SPI-{m.escala}, y su realce excluye el 1,0."
            if m.distingue
            else f"QUEDA SPI-{m.escala}, pero el 1,0 cae dentro de su realce: no distingue."
        )
    elif quedan:
        nombres = ", ".join(f"SPI-{m.escala}" for m in quedan)
        lineas.append(
            f"EMPATAN {nombres}. Sus intervalos de cobertura se solapan y la muestra\n"
            "  no las ordena. Elegir entre ellas por la diferencia puntual seria\n"
            "  decidir sobre ruido: hay que decidir por otro criterio y decir cual."
        )
    else:
        lineas.append("No queda ninguna escala en pie, lo que indica un error de lectura.")

    return "\n  ".join(lineas)


def advertencia_de_muestra(mediciones: list[Medicion], registros: list[Registro]) -> str:
    """El aviso que ningun intervalo puede dar por si solo: cuantos eventos hay **de verdad**.

    Los siete registros de sequia son **una fecha en siete distritos**, no siete
    episodios. El intervalo de Wilson los trata como siete extracciones
    independientes y no lo son ni de lejos: el n efectivo esta mas cerca de
    **uno**.

    Por eso este aviso se calcula y se imprime siempre, en vez de confiar en que
    quien lea la tabla se acuerde. Un intervalo optimista sin su advertencia al
    lado es peor que no tener intervalo, porque presta autoridad prestada.
    """
    de_sequia = [r for r in registros if r.tipo == TipoEvento.SEQUIA.value]
    fechas = {r.fecha for r in de_sequia}
    utiles = [m for m in mediciones if m.contrastables > 0]
    n_nominal = max((m.contrastables for m in utiles), default=0)

    if not de_sequia or len(fechas) >= n_nominal:
        return ""

    return (
        f"ATENCION AL TAMANO DE MUESTRA REAL. Los {len(de_sequia)} registros son\n"
        f"  **{len(fechas)} fecha(s) en varios distritos**, no {len(de_sequia)} episodios\n"
        "  independientes. Wilson los cuenta como si lo fueran, asi que los\n"
        f"  intervalos de cobertura estan calculados sobre n = {n_nominal} cuando el n\n"
        f"  efectivo esta mas cerca de {len(fechas)}.\n\n"
        "  Consecuencia para leer el veredicto: una COINCIDENCIA con n efectivo de\n"
        f"  {len(fechas)} no establece nada general. Un FALLO sistematico si dice algo,\n"
        "  porque falsar es mas barato que confirmar: si una escala no marca el\n"
        "  unico episodio que el catalogo permite probar, ese episodio alcanza\n"
        "  para dudar de ella, y no alcanzaria para coronar a las que si lo marcan."
    )


# --------------------------------------------------------------------------- #
# Datos sinteticos, para que el control no se salte en silencio                 #
# --------------------------------------------------------------------------- #
def _sintetico() -> dict[str, dict[date, float | None]]:
    """Precipitacion diaria deterministica, sin dependencias.

    **Por que existe.** La precipitacion vive en la base y `etiquetas.csv` esta
    en el .gitignore. Sin esto, la herramienta no correria en el CI y un fallo
    de importacion o de firma pasaria desapercibido hasta que alguien la
    ejecutara a mano. Es el criterio de **I-06**: un paso que se salta en
    silencio se ve igual que uno que se cumplio.

    **No sirve para concluir nada sobre las escalas.** La estacionalidad es un
    coseno y la variabilidad interanual es una funcion hash: no hay sequias de
    verdad ahi dentro. Solo comprueba que el camino de calculo corre entero.
    """
    import math

    def fnv(texto: str) -> int:
        h = 0x811C9DC5
        for byte in texto.encode():
            h = ((h ^ byte) * 0x01000193) & 0xFFFFFFFF
        return h

    salida: dict[str, dict[date, float | None]] = {}
    for i in range(8):
        # Los codigos reales de los ocho distritos de Tilaran. Con codigos
        # inventados el contraste da cero contrastables y el control **pasa sin
        # medir nada**, que es justo el modo de fallo que este modulo evita.
        codigo = f"5080{i + 1}"
        serie: dict[date, float | None] = {}
        dia = date(1991, 1, 1)
        while dia <= date(2024, 12, 31):
            estacion = max(0.0, math.cos((dia.timetuple().tm_yday - 250) / 58.0))
            ruido = (fnv(f"{codigo}{dia}") % 1000) / 1000.0
            serie[dia] = round(estacion * 22.0 * ruido, 1)
            dia += timedelta(days=1)
        salida[codigo] = serie
    return salida


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--catalogo", type=Path, default=CATALOGO)
    p.add_argument(
        "--sintetico",
        action="store_true",
        help="corre con precipitacion sintetica, sin base. Comprueba el camino, no concluye.",
    )
    p.add_argument("--fallos", action="store_true", help="lista cada evento no detectado")
    args = p.parse_args()

    if args.sintetico:
        precipitacion = _sintetico()
        print("\n  *** DATOS SINTETICOS. Comprueba que el calculo corre. NO concluye. ***")
    else:
        from basedatos.conexion import conectar

        with conectar() as conexion, conexion.cursor() as cursor:
            from backend.modelado.generar_etiquetas import leer_precipitacion

            precipitacion = leer_precipitacion(cursor)

    registros = leer_catalogo(args.catalogo)
    de_sequia = [r for r in registros if r.tipo == TipoEvento.SEQUIA.value]

    print("\nEscalas del SPI contra el catalogo de eventos reales")
    print(f"  distritos   {len(precipitacion)}")
    print(f"  catalogo    {len(de_sequia)} registros de sequia, de {len(registros)} con fecha")
    fechas = {r.fecha for r in de_sequia}
    print(f"  fechas      {len(fechas)} distinta(s): {', '.join(str(f) for f in sorted(fechas))}\n")

    por_escala = {e: etiquetas_de_sequia(precipitacion, e) for e in ESCALAS}

    # ----------------------------------------------------------------------- #
    # Ventana estricta: la unica comparable entre escalas                       #
    # ----------------------------------------------------------------------- #
    estrictas = [medir(por_escala[e], registros, e, HORIZONTE_DIAS) for e in ESCALAS]

    print(f"VENTANA ESTRICTA, [E-{HORIZONTE_DIAS}, E-1]. Igual para las tres:\n")
    print(
        f"  {'escala':8}{'contr.':>7}{'det.':>6}   {'cobertura (IC 95 %)':<26}"
        f"{'tasa base (IC 95 %)':<30}{'realce (rango)':<24}{'episod.':>8}"
    )
    for m in estrictas:
        if not m.contrastables:
            print(
                f"  SPI-{m.escala:<4}{0:>7}{'—':>6}   {'sin eventos contrastables':<26}"
                f"{str(m.tasa_base):<30}{'—':<24}{m.episodios:>8}"
            )
            continue
        punto, menor, mayor = m.realce
        print(
            f"  SPI-{m.escala:<4}{m.contrastables:>7}{m.detectados:>6}   "
            f"{str(m.cobertura):<26}{str(m.tasa_base):<30}"
            f"{f'{punto:.2f}x [{menor:.2f}, {mayor:.2f}]':<24}{m.episodios:>8}"
        )
    print()

    # ----------------------------------------------------------------------- #
    # Ventana propia: diagnostico, NO puntaje                                   #
    # ----------------------------------------------------------------------- #
    propias = [medir(por_escala[e], registros, e, ventana_propia(e)) for e in ESCALAS]

    print("VENTANA PROPIA de cada escala, su periodo de integracion.")
    print("  **No compara**: una ventana mas larga detecta mas por construccion.\n")
    for m in propias:
        if not m.contrastables:
            print(f"  SPI-{m.escala:<6}{m.ventana:>5}d   sin eventos contrastables")
            continue
        print(
            f"  SPI-{m.escala:<6}{m.ventana:>5}d   {m.detectados}/{m.contrastables}   "
            f"{m.cobertura}"
        )
    print()

    # ----------------------------------------------------------------------- #
    # El diagnostico de fallos: donde quedo la marca cuando no estuvo           #
    # ----------------------------------------------------------------------- #
    print("DISTANCIA A LA MARCA MAS CERCANA, ventana estricta.")
    print("  Negativo = la marca fue ANTES del registro del catalogo.\n")
    for m in estrictas:
        distancias = [d for _, d in m.fallos if d is not None]
        if not distancias:
            estado = "sin fallos" if m.contrastables else "no contrastable"
            print(f"  SPI-{m.escala:<6}{estado}")
            continue
        # `min` por valor absoluto, no `max`: se quiere la marca MAS CERCANA.
        # La primera version uso `max` y reportaba la mas lejana bajo el rotulo
        # de la mas cercana, que es peor que no reportarla.
        print(
            f"  SPI-{m.escala:<6}{len(m.fallos)} fallo(s) · "
            f"mas cercana {min(distancias, key=abs):+d} d · "
            f"mediana {sorted(distancias)[len(distancias) // 2]:+d} d"
        )
        if args.fallos:
            for registro, distancia in sorted(m.fallos, key=lambda x: x[0].fecha):
                cerca = f"{distancia:+5d} d" if distancia is not None else "  sin marca"
                print(f"      {registro.fecha}  {registro.codigo_distrito}  {cerca}")
    print()

    # ----------------------------------------------------------------------- #
    aviso = advertencia_de_muestra(estrictas, registros)
    if aviso:
        print(f"  {aviso}\n")

    print("VEREDICTO\n")
    print(f"  {veredicto(estrictas)}\n")

    print("Como leer esto\n")
    print("  Los intervalos son de Wilson al 95 %. Con muestras de este tamano el")
    print("  intervalo es ancho, y esa amplitud **es** el resultado: dice que el")
    print("  catalogo no alcanza para ordenar las escalas, no que las escalas sean")
    print("  equivalentes. Son dos afirmaciones distintas y solo la primera se hace.\n")
    print("  Los intervalos suponen observaciones independientes y no lo son: el SPI")
    print("  de un mes es constante dentro del mes y los distritos comparten celdas")
    print("  de la fuente. Asi que son, si acaso, OPTIMISTAS.\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
