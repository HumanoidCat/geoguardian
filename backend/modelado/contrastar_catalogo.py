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

**Y LA SEQUIA NECESITA OTRA VENTANA. Esto se descubrio midiendo.**

Con la ventana de siete dias, la sequia dio **0 de 7**. Parecia un fracaso
completo del etiquetado, y no lo era: los siete registros del catalogo llevan la
misma fecha, **2014-09-30**, y el etiquetado marco sequia en esos distritos
**desde enero hasta agosto de 2014**, ocho meses seguidos. La marca mas cercana
esta a **37 dias antes** de la fecha del catalogo, en los ocho distritos.

La explicacion es que **son dos relojes distintos**:

    el catalogo   registra la fecha de la DECLARATORIA administrativa, que se
                  emite despues de evaluar los danos
    el etiquetado marca el mes en que el SPI-3 cae bajo el umbral

Una declaratoria de emergencia por sequia llega **al final** del episodio, no
durante. Y el SPI-3 integra tres meses por construccion, asi que ni siquiera es
un indicador diario.

Contrastar una declaratoria contra una ventana de siete dias **compara dos cosas
que no son comparables**. Por eso la sequia se contrasta ademas con una ventana
de 90 dias, que es el propio periodo de integracion del indice.

**Se reportan las dos.** La de siete dias porque es la unica comparable entre
eventos; la ampliada porque es la que responde la pregunta para la sequia.

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

from backend.modelado.etiquetado import HORIZONTE_DIAS  # noqa: E402
from backend.modelado.evaluar_linea_base import COLUMNA, leer  # noqa: E402
from backend.modelado.linea_base import DISTRITOS_CON_INCENDIO  # noqa: E402
from contratos.enums import NivelRiesgo, TipoEvento  # noqa: E402

CATALOGO = RAIZ / "docs" / "investigacion" / "catalogo-eventos.csv"
ETIQUETAS = RAIZ / "datos" / "procesados" / "etiquetas.csv"

#: Que niveles cuentan como «estaba marcado». BAJO no: es la ausencia de aviso.
MARCA = (NivelRiesgo.MEDIO, NivelRiesgo.ALTO)

#: Dias hacia atras desde la fecha del catalogo. Por evento, y con razon.
#:
#: El SPI-3 integra **tres meses**: no es un indicador diario y una declaratoria
#: administrativa se emite al terminar el episodio, no durante. Los 90 dias son
#: el periodo de integracion del propio indice, no un numero elegido para que el
#: resultado quedara mejor. Ver el encabezado.
VENTANA_AMPLIA = {TipoEvento.SEQUIA: 90}


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


def _distancia_mas_cercana(marcadas: list[date], objetivo: date) -> int | None:
    """Dias con signo hasta la marca mas cercana. Negativo si es anterior.

    Es lo que convierte un fallo en un diagnostico. La sequia de 2014 dio 0 de 7
    con la ventana de siete dias, y lo que explica ese cero es que la marca mas
    cercana estaba a **-37 dias** en los ocho distritos: no faltaba la marca,
    faltaba mirar donde estaba.
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
            f"  {'evento':16}{'ventana':>8}{'catalogo':>9}{'contrast.':>10}{'detecta':>9}"
            f"{'cobertura':>11}{'tasa base':>11}{'realce':>9}"
        )
        for r in resultados:
            if not r.contrastables:
                print(
                    f"  {r.evento:16}{r.ventana:>7}d{r.en_catalogo:>9}{0:>10}{'—':>9}"
                    f"{'—':>11}{r.tasa_base:>10.1%}{'—':>9}"
                )
                continue
            print(
                f"  {r.evento:16}{r.ventana:>7}d{r.en_catalogo:>9}{r.contrastables:>10}"
                f"{r.detectados:>9}{r.cobertura:>10.1%}{r.tasa_base:>11.1%}"
                f"{r.realce:>8.2f}x"
            )
        print()

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
            "VENTANA AMPLIADA. El SPI-3 integra tres meses y una declaratoria se\n"
            "emite al terminar el episodio, no durante:",
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
