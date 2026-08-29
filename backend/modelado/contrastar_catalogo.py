"""Contrasta el etiquetado contra el catalogo de eventos reales. Hacia H4.4.

===========================================================================
QUE PREGUNTA RESPONDE, Y CUAL NO
===========================================================================

**Responde:** cuando en Tilaran ocurrio de verdad un evento con danos
registrados, ¿el etiquetado de H3.0 lo tenia marcado como riesgo?

**No responde:** si el modelo acierta. No hay modelo. Esto valida **la verdad de
terreno**, que es el paso anterior y el que nadie suele comprobar: si las
etiquetas no reconocen los eventos que ocurrieron, ningun modelo entrenado sobre
ellas puede reconocerlos tampoco.

Es la validacion externa que **no necesita participantes**, comprometida en
**D-12** como «caso retrospectivo». El catalogo lo construyo Luna en H4.3 desde
DesInventar Costa Rica.

===========================================================================
TRES LIMITACIONES QUE CAMBIAN COMO SE LEE EL RESULTADO
===========================================================================

**1. El catalogo registra DANOS, no fenomenos.** DesInventar cataloga cuando hubo
perdidas reportadas. Un aguacero igual de intenso sobre un potrero sin
infraestructura no entra. Asi que el catalogo es una muestra **sesgada hacia
donde hay gente y camino**, y eso explica que Tilaran centro tenga 19 de los 46
registros.

**2. La ausencia no es evidencia de ausencia.** Que una fecha no este en el
catalogo **no** significa que no haya pasado nada. Por eso aca se mide
**cobertura** -de los eventos catalogados, cuantos estaban marcados- y **no se
mide precision**. Una marca sin registro en el catalogo no es un falso positivo:
puede ser un evento real que nadie reporto.

Calcular precision contra un catalogo incompleto produce un numero que parece
riguroso y esta mal por construccion.

**3. Una cobertura alta no es buena noticia por si sola.** Si el etiquetado
marcara riesgo el 90 % de los dias, detectaria casi todo y no serviria para nada.
Por eso el numero que importa no es la cobertura sino el **realce**: cuantas
veces mas frecuente es la marca en la ventana de un evento real que en un dia
cualquiera. Un realce de 1,0 significa que el etiquetado no distingue.

===========================================================================
COMO SE ALINEAN LAS FECHAS
===========================================================================

La etiqueta del dia `t` describe la ventana `(t, t+7]`: es una prevision a siete
dias, no una descripcion del dia. Asi que un evento ocurrido el dia `E` estaba
anunciado si alguna etiqueta en `t ∈ [E-7, E-1]` marcaba riesgo.

Buscar la etiqueta **del dia del evento** seria el error facil, y daria una
cobertura mucho mas baja por una razon que no tiene nada que ver con la calidad
del etiquetado.

**LA SEQUIA NECESITA OTRA VENTANA, Y ESA HISTORIA TERMINO EN UN CAMBIO DE ESCALA**

Con SPI-3 y ventana de siete dias, la sequia daba **0 de 7**. Se leyo entonces
como un desajuste de relojes y no como un fallo del indice:

    el catalogo   registra la fecha de la DECLARATORIA administrativa, que se
                  emite despues de evaluar los danos
    el etiquetado marca el mes en que el SPI cae bajo el umbral

Una declaratoria de emergencia por sequia llega **al final** del episodio, no
durante, asi que se agrego una ventana ampliada del tamano del periodo de
integracion del indice, y con ella el SPI-3 recuperaba los siete.

**Esa lectura era incompleta, y `comparar_escalas_spi.py` lo mostro.** Medidas
las tres escalas contra el mismo catalogo, **SPI-6 y SPI-12 detectan los siete
con la ventana estricta de siete dias**, sin ampliar nada. El problema no era
que la pregunta fuera incontestable a siete dias: era que **el SPI-3 sale de
sequia antes de que el dano se declare**. La marca mas cercana quedaba a -37
dias, identica en los ocho distritos, que es la firma de un desajuste
estructural y no de una coincidencia.

**D-32 cambio la escala a SPI-6** por eso, y `VENTANA_AMPLIA` sigue existiendo
porque la ampliada mide otra cosa que igual interesa -cuanto margen tiene el
aviso-, pero **ya no es la que rescata el resultado**.

**Se reportan las dos.** La de siete dias porque es la unica comparable entre
eventos, y ahora ademas porque es la que la sequia aprueba; la ampliada como
diagnostico.

Uso:
    python -m backend.modelado.contrastar_catalogo
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado.etiquetado import HORIZONTE_DIAS, VENTANA_SPI_MESES  # noqa: E402
from backend.modelado.evaluar_linea_base import COLUMNA, leer  # noqa: E402
from backend.modelado.intervalos import (  # noqa: E402
    Intervalo,
    realce_con_intervalo,
    wilson,
)
from backend.modelado.linea_base import DISTRITOS_CON_INCENDIO  # noqa: E402
from contratos.enums import NivelRiesgo, TipoEvento  # noqa: E402

CATALOGO = RAIZ / "docs" / "investigacion" / "catalogo-eventos.csv"
ETIQUETAS = RAIZ / "datos" / "procesados" / "etiquetas.csv"

#: Que niveles cuentan como «estaba marcado». BAJO no: es la ausencia de aviso.
MARCA = (NivelRiesgo.MEDIO, NivelRiesgo.ALTO)

#: Dias hacia atras desde la fecha del catalogo. Por evento, y con razon.
#:
#: Se deriva de la escala del SPI en vez de escribirse a mano. Cuando D-32 la
#: cambio de 3 a 6, un 90 escrito literal habria quedado apuntando a una escala
#: que ya no existe, **sin que nada fallara**: la herramienta habria seguido
#: dando un numero, y el numero habria dejado de ser el periodo de integracion
#: del indice para pasar a ser un valor arbitrario que alguien escribio una vez.
#:
#: Es el mismo criterio que `verificar_h30.py` aplica a los umbrales: leerlos de
#: donde se declaran, no repetirlos.
VENTANA_AMPLIA = {TipoEvento.SEQUIA: VENTANA_SPI_MESES * 30}


@dataclass
class Registro:
    codigo_distrito: str
    tipo: str
    fecha: date
    descripcion: str


@dataclass
class Resultado:
    evento: str
    ventana: int
    en_catalogo: int
    contrastables: int
    detectados: int
    fuera_de_cobertura: list[Registro]
    #: (registro, dias hasta la marca mas cercana; None si el distrito no tiene ninguna)
    fallos: list[tuple[Registro, int | None]]
    tasa_base: float

    #: Denominador de la tasa base, para poder darle intervalo. Sin el, la tasa
    #: base es un float sin `n` y no se puede saber cuanta confianza merece.
    dias_totales: int = 0
    dias_marcados: int = 0

    @property
    def cobertura(self) -> float:
        return self.detectados / self.contrastables if self.contrastables else 0.0

    @property
    def realce(self) -> float:
        """Cuantas veces mas frecuente es la marca ante un evento real.

        Es el numero que importa. La cobertura sola se puede subir marcando
        siempre; el realce no.
        """
        return self.cobertura / self.tasa_base if self.tasa_base else 0.0

    # ----------------------------------------------------------------------- #
    # Las mismas cifras, con su incertidumbre. Agregado por D-32.
    #
    # **Por que hacia falta.** El documento reportaba «64,7 % de cobertura» y
    # «13,7 % de tasa base» como dos puntos, y esos dos numeros salen de
    # muestras de tamano radicalmente distinto: 34 eventos contra 100 000 filas.
    # Sin intervalo, se leen como si tuvieran la misma solidez y no la tienen.
    # ----------------------------------------------------------------------- #
    @property
    def cobertura_ic(self) -> Intervalo | None:
        return wilson(self.detectados, self.contrastables) if self.contrastables else None

    @property
    def tasa_base_ic(self) -> Intervalo | None:
        return wilson(self.dias_marcados, self.dias_totales) if self.dias_totales else None

    @property
    def realce_rango(self) -> tuple[float, float, float] | None:
        """Realce con su rango. **Si el 1,0 cae dentro, el etiquetado no distingue.**"""
        cobertura, base = self.cobertura_ic, self.tasa_base_ic
        if cobertura is None or base is None or base.punto <= 0:
            return None
        return realce_con_intervalo(cobertura, base)


def _distancia_mas_cercana(marcadas: list[date], objetivo: date) -> int | None:
    """Dias con signo hasta la marca mas cercana. Negativo si es anterior.

    Es lo que convierte un fallo en un diagnostico, y en este proyecto ya
    decidio un cambio de escala.

    Con SPI-3, la sequia de 2014 daba 0 de 7 a siete dias. El numero solo dice
    que fallo; **la distancia dice por que**: -37 dias, y el mismo -37 en los
    ocho distritos. Una coincidencia se dispersa entre distritos. Un valor
    identico en los ocho es la firma de algo estructural, y lo era: el indice
    salia de sequia antes de que la declaratoria se emitiera. De ahi D-32.
    """
    if not marcadas:
        return None
    return (min(marcadas, key=lambda d: abs((d - objetivo).days)) - objetivo).days


def leer_catalogo(ruta: Path) -> list[Registro]:
    registros = []
    with ruta.open(encoding="utf-8", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            if not fila.get("fecha_inicio"):
                continue
            registros.append(
                Registro(
                    codigo_distrito=fila["codigo_distrito"].strip(),
                    tipo=fila["tipo_evento"].strip(),
                    fecha=date.fromisoformat(fila["fecha_inicio"].strip()),
                    descripcion=fila.get("descripcion", "")[:70],
                )
            )
    return registros


def contrastar(
    evento: TipoEvento, registros: list[Registro], filas: list, ventana_dias: int
) -> Resultado:
    columna = COLUMNA[evento]

    # Indice (distrito, fecha) -> nivel, solo donde hay etiqueta observada.
    por_dia: dict[tuple[str, date], NivelRiesgo] = {}
    marcados_por_distrito: Counter = Counter()
    dias_por_distrito: Counter = Counter()

    for codigo, fecha, niveles in filas:
        nivel = niveles[columna]
        if nivel is None:
            continue
        por_dia[(codigo, fecha)] = nivel
        dias_por_distrito[codigo] += 1
        if nivel in MARCA:
            marcados_por_distrito[codigo] += 1

    # La tasa base se calcula **sobre los mismos distritos** que el evento
    # admite. Para incendio son tres (D-25); mezclarlo con los ocho bajaria el
    # denominador y regalaria realce.
    admitidos = (
        set(DISTRITOS_CON_INCENDIO) if evento is TipoEvento.INCENDIO else set(dias_por_distrito)
    )
    total_dias = sum(dias_por_distrito[d] for d in admitidos)
    total_marcados = sum(marcados_por_distrito[d] for d in admitidos)
    tasa_base = total_marcados / total_dias if total_dias else 0.0

    # Dias marcados por distrito, para poder medir a que distancia quedo la marca
    # mas cercana cuando un evento no se detecta. Un fallo con la distancia es un
    # diagnostico; un fallo sin ella es solo un numero.
    marcados: dict[str, list[date]] = defaultdict(list)
    for (codigo, fecha), nivel in por_dia.items():
        if nivel in MARCA:
            marcados[codigo].append(fecha)

    del_evento = [r for r in registros if r.tipo == evento.value]

    fuera: list[Registro] = []
    fallos: list[tuple[Registro, int | None]] = []
    detectados = 0

    for registro in del_evento:
        ventana = [registro.fecha - timedelta(days=d) for d in range(1, ventana_dias + 1)]
        disponibles = [
            por_dia[(registro.codigo_distrito, dia)]
            for dia in ventana
            if (registro.codigo_distrito, dia) in por_dia
        ]

        # Sin ninguna etiqueta en la ventana el evento no es contrastable, y hay
        # que decirlo aparte en vez de contarlo como fallo. La mayoria son
        # anteriores a 1991, o de incendio en un distrito que D-25 excluye.
        if not disponibles:
            fuera.append(registro)
            continue

        if any(nivel in MARCA for nivel in disponibles):
            detectados += 1
        else:
            cercanas = marcados.get(registro.codigo_distrito, [])
            fallos.append((registro, _distancia_mas_cercana(cercanas, registro.fecha)))

    return Resultado(
        evento=evento.value,
        ventana=ventana_dias,
        en_catalogo=len(del_evento),
        contrastables=len(del_evento) - len(fuera),
        detectados=detectados,
        fuera_de_cobertura=fuera,
        fallos=fallos,
        tasa_base=tasa_base,
        dias_totales=total_dias,
        dias_marcados=total_marcados,
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--catalogo", type=Path, default=CATALOGO)
    p.add_argument("--etiquetas", type=Path, default=ETIQUETAS)
    p.add_argument("--fallos", action="store_true", help="lista cada evento no detectado")
    args = p.parse_args()

    if not args.etiquetas.exists():
        print(f"\nNo existe {args.etiquetas}. Se genera con la base levantada:\n")
        print("    python -m backend.modelado.generar_etiquetas\n")
        return 1

    registros = leer_catalogo(args.catalogo)
    filas = leer(args.etiquetas)

    print("\nEtiquetado contra el catalogo de eventos reales")
    print(f"  catalogo    {len(registros)} registros con fecha, de DesInventar (H4.3)")
    print(f"  etiquetas   {len(filas)} filas de H3.0\n")

    def tabla(titulo: str, resultados: list[Resultado]) -> None:
        print(titulo)
        print(
            f"  {'evento':16}{'vent.':>6}{'cat.':>6}{'contr.':>7}{'det.':>6}   "
            f"{'cobertura (IC 95 %)':<26}{'tasa base':<12}{'realce (rango)':<22}"
        )
        for r in resultados:
            if not r.contrastables:
                print(
                    f"  {r.evento:16}{r.ventana:>5}d{r.en_catalogo:>6}{0:>7}{'—':>6}   "
                    f"{'sin eventos contrastables':<26}{r.tasa_base:<11.1%} {'—':<22}"
                )
                continue
            rango = r.realce_rango
            # El rango del realce **se declara ausente en vez de rellenarse**: si
            # no hay tasa base no hay realce, y un guion es informacion, un cero
            # seria una mentira con formato de dato.
            texto_realce = (
                f"{rango[0]:.2f}x [{rango[1]:.2f}, {rango[2]:.2f}]" if rango else "—"
            )
            print(
                f"  {r.evento:16}{r.ventana:>5}d{r.en_catalogo:>6}{r.contrastables:>7}"
                f"{r.detectados:>6}   {str(r.cobertura_ic):<26}{r.tasa_base:<11.1%} "
                f"{texto_realce:<22}"
            )
        print()
        # La lectura del rango, junto a la tabla y no en una nota al pie, porque
        # es la unica forma de leerla bien.
        for r in resultados:
            rango = r.realce_rango
            if rango and rango[1] <= 1.0:
                print(
                    f"  ATENCION · {r.evento}: el 1,0 cae dentro del rango de su realce.\n"
                    "  Ante un evento real marca con una frecuencia compatible con la de\n"
                    "  un dia cualquiera: con esta muestra, NO se puede afirmar que\n"
                    "  distingue.\n"
                )

    estrictos = [contrastar(e, registros, filas, HORIZONTE_DIAS) for e in TipoEvento]
    tabla(
        f"VENTANA ESTRICTA, [E-{HORIZONTE_DIAS}, E-1]. La unica comparable entre eventos:",
        estrictos,
    )

    ampliados = [
        contrastar(e, registros, filas, VENTANA_AMPLIA[e])
        for e in TipoEvento
        if e in VENTANA_AMPLIA
    ]
    if ampliados:
        tabla(
            f"VENTANA AMPLIADA. El SPI-{VENTANA_SPI_MESES} integra {VENTANA_SPI_MESES} meses y una\n"
            "declaratoria se emite al terminar el episodio, no durante:",
            ampliados,
        )

    for r in estrictos:
        if r.fuera_de_cobertura:
            print(f"  {r.evento}: {len(r.fuera_de_cobertura)} sin etiqueta en la ventana")
            anios = Counter(x.fecha.year for x in r.fuera_de_cobertura)
            print(f"      anios: {dict(sorted(anios.items()))}")
    print()

    # ----------------------------------------------------------------------- #
    # El analisis de fallos, que es la mitad del valor de esta herramienta
    # ----------------------------------------------------------------------- #
    if args.fallos:
        for r in estrictos:
            if not r.fallos:
                continue
            print(f"\n{r.evento.upper()} · {len(r.fallos)} sin marca en [E-{r.ventana}, E-1]")
            print("  la columna de dias es la distancia a la marca mas cercana\n")
            for registro, distancia in sorted(r.fallos, key=lambda x: x[0].fecha):
                cerca = f"{distancia:+5d} d" if distancia is not None else "  sin marca"
                print(
                    f"  {registro.fecha}  {registro.codigo_distrito}  {cerca}  "
                    f"{registro.descripcion}"
                )

            # Cuantos de los fallos tenian una marca cerca, y de que lado. Es lo
            # que separa «el etiquetado no vio nada» de «el etiquetado lo vio
            # fuera de la ventana», que son dos diagnosticos distintos.
            distancias = [d for _, d in r.fallos if d is not None]
            if distancias:
                dentro_14 = sum(1 for d in distancias if abs(d) <= 14)
                despues = sum(1 for d in distancias if d > 0)
                print(
                    f"\n  de los {len(r.fallos)} fallos, {dentro_14} tenian una marca a "
                    f"14 dias o menos,\n  y en {despues} la marca llego DESPUES del evento"
                )
        print()

    # ----------------------------------------------------------------------- #
    # Lo que se puede y no se puede concluir
    # ----------------------------------------------------------------------- #
    print("Como leer esto\n")
    print("  La COBERTURA sola no dice nada: se sube marcando siempre. El numero")
    print("  que importa es el REALCE, cuantas veces mas frecuente es la marca")
    print("  ante un evento real que en un dia cualquiera. Realce 1,00 significa")
    print("  que el etiquetado no distingue.\n")
    print("  NO se reporta precision. El catalogo registra danos, no fenomenos, y")
    print("  esta incompleto: una marca sin registro puede ser un evento real que")
    print("  nadie reporto. Dividir por marcas totales daria un numero que parece")
    print("  riguroso y esta mal por construccion.\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
