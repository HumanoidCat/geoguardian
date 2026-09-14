"""
Diagnostico guiado a partir de `control.bitacora_etl`. Historia H12.4.

Dueno: Luna. Criterios en
`docs/evidencias/arquitectura-software/H12.4-criterios-aceptacion.md`.

EL CASO QUE JUSTIFICA ESTE MODULO
---------------------------------

**I-43.** El ETL pidio 215 dias de precipitacion, llegaron 3, y la corrida quedo
registrada como `exitosa`. Nadie comparo lo pedido contra lo devuelto, y el
defecto vivio meses sin que ninguna alarma sonara: no habia nada mal en la forma
de la respuesta, solo en su tamano.

DONDE ESTA «LO PEDIDO», Y POR QUE LA PRIMERA VERSION NO LO ENCONTRO
-------------------------------------------------------------------

La primera version de este modulo comparaba `filas_leidas` contra `filas`, como
si la primera fuera un subconjunto de la segunda. **Es falso, y lo dice el propio
`ingestar.py`:**

    `filas_leidas` es de la 014 (H12.1): cuantas trajo la FUENTE, aparte de
    cuantas se escribieron.

Son dos etapas distintas. La corrida 63 de la base local trae `filas_leidas =
1944` y `filas = 1712`: la fuente trajo 1944 y se escribieron 1712, porque 232 ya
estaban y las salto el `ON CONFLICT`. La razon daba **1,135**, un valor que bajo
la suposicion equivocada era imposible.

Lo pedido no esta en `filas`: esta en **`ventana_desde` y `ventana_hasta`**.

    dias de la ventana x series por dia  =  lo que se esperaba
    filas_leidas                         =  lo que la fuente trajo

Con eso I-43 es `24 de 1720`, y una corrida sana con la latencia de **D-40** cae
alrededor del 87 %.

Y HAY UNA SENAL QUE LA PRIMERA VERSION SE TRAGABA EN SILENCIO
-------------------------------------------------------------

La corrida **39**, que es la del propio I-43, tiene `filas_leidas = None`: la
columna existia y el ETL todavia no la llenaba. La primera version exigia que no
fuera nula para juzgar, asi que la dejaba pasar **sin decir nada**.

Una corrida que no se puede juzgar **no es una corrida sana**. Ahora sale con su
propio nombre: `cobertura no declarada`.

LO QUE ESTE MODULO NO PUEDE DECIR
---------------------------------

De las cuatro columnas que la migracion 014 creo para diagnosticar, **tres no las
llena nadie**: `sqlstate`, `version_codigo` y `reportado_por`. Quien las llenaria
es `backend/etl/ingestar.py`, que es H1.14 y esta cerrada; el PM decidio el
2026-09-13 que esta historia diagnostica con lo que hay y **declara donde esta
ciega**.

La consecuencia practica es que un fallo solo se puede clasificar leyendo texto
libre, y eso es una **conjetura**, no una causa. Por eso `Senal.conjetura` existe
y la salida las separa: en I-43 el texto decia «exitosa».

La ceguera es **por nivel, no total**: `control.fallo` si guarda `sqlstate`, y
H12.1 le puso la clave foranea hacia esta tabla. Se ven codigos de error de
**filas rechazadas**, no de **corridas**.

Y la de fondo, que ninguna columna arregla:

    El diagnostico solo ve lo que la bitacora registra.
    Un fallo que nunca se escribio no existe para esta herramienta.

Uso:
    python -m backend.calidad.diagnostico_bitacora
    python -m backend.calidad.diagnostico_bitacora --salida diagnostico.txt
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta

# --------------------------------------------------------------------------- #
# Umbrales                                                                      #
# --------------------------------------------------------------------------- #
#
# SE FIJAN AQUI, ANTES DE CORRER CONTRA DATOS REALES, y con su motivo escrito.
# Un umbral elegido despues de ver la tabla es un umbral que eligio la tabla. Es
# la misma regla que CA-6 de H3.0, que dejo a la sequia fuera del modelado sin
# que nadie moviera el numero.

#: Proporcion `filas_leidas / esperadas` por debajo de la cual una corrida
#: cerrada se considera incompleta.
#:
#: Por que 0,5 y no 0,9: **D-40** declara que CHIRPS publica con unos 33 dias de
#: latencia, asi que una corrida legitima que llegue hasta hoy **siempre** trae
#: dias sin dato al final. La corrida 63 de la base local, que es sana, cae
#: alrededor del 87 %; sobre una ventana de tres meses caeria bastante mas abajo.
#: Con 0,9 se marcaria como rota toda corrida reciente y el diagnostico seria
#: ruido, y el ruido se deja de leer.
#:
#: Con 0,5 sigue quedando muy por encima del caso que hay que atrapar: I-43
#: trajo 24 de 1720 series, que es **0,014**.
UMBRAL_COBERTURA = 0.5

#: Horas que una corrida puede estar `en_curso` antes de considerarse colgada.
#: La ingesta completa tarda unos 11 minutos segun el README y la cadena de
#: estimacion unos 4. Seis horas es un orden de magnitud por encima de lo mas
#: lento que se conoce, para no marcar como colgada una corrida lenta.
HORAS_COLGADA = 6.0

#: Dias sin ninguna corrida tras los cuales un proceso diario se da por ausente.
DIAS_AUSENTE = 2

#: Procesos que deberian dejar rastro todos los dias. Se declaran aqui: **una
#: ausencia no se puede detectar buscando en la tabla**, porque lo que falta no
#: esta. Hay que saber de antemano que se esperaba.
PROCESOS_DIARIOS: tuple[str, ...] = ("ingesta.lluvia_intensa", "estimacion.riesgo")

#: Cuantas series deberia traer la fuente por cada dia de ventana, por proceso.
#:
#: **Solo se comprueba la cobertura de los procesos que estan aqui.** Para los
#: demas no se sabe que esperar, y no saber se dice, no se supone.
#:
#: El valor real lo pone `main()` contando `geo.distrito`, no este numero: es la
#: leccion de **I-53**, que una funcion no tenga su propia idea de un valor que
#: pertenece a otro. Esto es solo el respaldo cuando se llama sin base.
SERIES_POR_DIA: dict[str, int] = {"ingesta.lluvia_intensa": 8}

ESTADOS_CERRADOS = frozenset({"exitosa", "fallida", "omitida", "parcial"})


# --------------------------------------------------------------------------- #
# Estructuras                                                                   #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Corrida:
    """Una fila de `control.bitacora_etl`, tal como esta.

    `filas` y `filas_leidas` son de **etapas distintas** y ninguna contiene a la
    otra: la primera es lo que se escribio, la segunda lo que trajo la fuente.
    `filas_leidas` puede ser mayor.
    """

    id: int
    proceso: str
    estado: str
    iniciada_en: datetime
    terminada_en: datetime | None = None
    filas: int | None = None
    filas_leidas: int | None = None
    mensaje: str | None = None
    sqlstate: str | None = None
    version_codigo: str | None = None
    reportado_por: str | None = None
    ventana_desde: date | None = None
    ventana_hasta: date | None = None


@dataclass(frozen=True)
class Senal:
    """Un hallazgo del diagnostico.

    `evidencia` dice **de que dato salio** y `accion` que hacer. Las dos son
    obligatorias: una senal sin evidencia es una opinion, y una sin accion no
    ayuda a quien esta operando a las dos de la manana.

    `conjetura` marca las que salen de leer texto libre. **No son causas.**
    """

    nombre: str
    proceso: str
    evidencia: str
    accion: str
    corrida_id: int | None = None
    conjetura: bool = False


def esperadas(corrida: Corrida, series_por_dia: dict[str, int]) -> int | None:
    """Cuantas series deberia haber traido la fuente, o None si no se sabe.

    **Devolver None es una respuesta, no un fallo.** Un proceso sin ventana
    declarada o sin numero de series conocido no se puede juzgar por cobertura, y
    eso se dice en vez de suponerlo.
    """
    por_dia = series_por_dia.get(corrida.proceso)
    if por_dia is None or corrida.ventana_desde is None or corrida.ventana_hasta is None:
        return None
    dias = (corrida.ventana_hasta - corrida.ventana_desde).days + 1
    return dias * por_dia if dias > 0 else None


# --------------------------------------------------------------------------- #
# Clasificacion                                                                 #
# --------------------------------------------------------------------------- #


def clasificar(
    corrida: Corrida,
    ahora: datetime,
    series_por_dia: dict[str, int] | None = None,
) -> Senal | None:
    """Clasifica UNA corrida, o devuelve None si no tiene senal.

    EL ORDEN DE LAS PRUEBAS ES PARTE DEL CONTRATO y esta fijado de mas grave a
    menos: una corrida colgada se reporta como colgada aunque ademas tenga poca
    cobertura. Devolver la primera que coincida, y no todas, evita que un mismo
    problema aparezca tres veces con tres nombres.
    """
    series = SERIES_POR_DIA if series_por_dia is None else series_por_dia

    if corrida.estado == "en_curso":
        abierta = (ahora - corrida.iniciada_en).total_seconds() / 3600.0
        if abierta > HORAS_COLGADA:
            return Senal(
                nombre="colgada",
                proceso=corrida.proceso,
                corrida_id=corrida.id,
                evidencia=(
                    f"en_curso desde {corrida.iniciada_en:%Y-%m-%d %H:%M}, "
                    f"{abierta:.1f} h abierta, umbral {HORAS_COLGADA:.0f} h"
                ),
                accion=(
                    "El proceso murio sin cerrar su corrida. Revisar si sigue vivo; "
                    "si no, cerrarla a mano con estado 'fallida' y su mensaje."
                ),
            )
        return None

    if corrida.estado not in ESTADOS_CERRADOS:
        return None

    if corrida.estado == "exitosa" and corrida.filas == 0:
        return Senal(
            nombre="exitosa vacia",
            proceso=corrida.proceso,
            corrida_id=corrida.id,
            evidencia="estado exitosa con filas = 0",
            accion="Corrio y no escribio nada. Revisar el rango pedido y la fuente.",
        )

    cuantas = esperadas(corrida, series)
    if cuantas:
        if corrida.filas_leidas is None:
            # LA SENAL QUE LA PRIMERA VERSION SE TRAGABA EN SILENCIO.
            # Es el caso de la corrida 39, la del propio I-43.
            return Senal(
                nombre="cobertura no declarada",
                proceso=corrida.proceso,
                corrida_id=corrida.id,
                evidencia=(
                    f"ventana {corrida.ventana_desde} a {corrida.ventana_hasta} "
                    f"({cuantas} series esperadas), filas_leidas sin valor"
                ),
                accion=(
                    "NO se puede juzgar su cobertura: no hay con que comparar lo pedido. "
                    "No es una corrida sana, es una corrida sin medir. Reejecutar con una "
                    "version del ETL que llene filas_leidas."
                ),
            )
        proporcion = corrida.filas_leidas / cuantas
        if proporcion < UMBRAL_COBERTURA:
            return Senal(
                nombre="cobertura incompleta",
                proceso=corrida.proceso,
                corrida_id=corrida.id,
                evidencia=(
                    f"la fuente trajo {corrida.filas_leidas} de {cuantas} series "
                    f"esperadas ({proporcion:.1%}), umbral {UMBRAL_COBERTURA:.0%}; "
                    f"ventana {corrida.ventana_desde} a {corrida.ventana_hasta}"
                ),
                accion=(
                    "Es la forma de I-43: la fuente devolvio mucho menos de lo pedido y la "
                    "corrida se cerro igual. Reejecutar con --desde y comparar lo pedido "
                    "contra lo devuelto antes de darla por buena."
                ),
            )

    if corrida.estado == "parcial":
        return Senal(
            nombre="parcial",
            proceso=corrida.proceso,
            corrida_id=corrida.id,
            evidencia=f"estado parcial, {corrida.filas} filas escritas",
            accion="Termino a medias. Revisar el mensaje y completar el rango que falta.",
        )

    if corrida.estado == "fallida":
        return Senal(
            nombre="fallida",
            proceso=corrida.proceso,
            corrida_id=corrida.id,
            evidencia=_evidencia_de_fallo(corrida),
            accion=(
                "Cruzar con control.fallo por el id de corrida: ahi SI hay sqlstate "
                "de las filas rechazadas. A nivel de corrida no lo hay."
            ),
            conjetura=corrida.sqlstate is None,
        )

    return None


def _evidencia_de_fallo(corrida: Corrida) -> str:
    """Que se puede decir de un fallo, y con cuanta confianza.

    Con `sqlstate` la evidencia es un codigo, que no cambia con el idioma del
    servidor. Sin el, lo unico que queda es el texto, y **el texto ya engano una
    vez**: en I-43 decia que todo habia salido bien.
    """
    if corrida.sqlstate:
        return f"sqlstate {corrida.sqlstate}"
    if corrida.mensaje:
        recorte = corrida.mensaje.strip().splitlines()[0][:90]
        return f"sin sqlstate; solo el texto: «{recorte}»"
    return "sin sqlstate y sin mensaje: la corrida fallo y no dejo dicho por que"


def senales_de(
    corridas: list[Corrida],
    ahora: datetime,
    series_por_dia: dict[str, int] | None = None,
) -> list[Senal]:
    """Las senales de una lista de corridas, en el orden en que llegan.

    No se ordena por gravedad ni por fecha: el llamador decide. Ordenar aqui
    haria que la salida dependiera de un criterio que nadie declaro.
    """
    encontradas = []
    for corrida in corridas:
        senal = clasificar(corrida, ahora, series_por_dia)
        if senal is not None:
            encontradas.append(senal)
    return encontradas


def ausencias(
    corridas: list[Corrida],
    ahora: datetime,
    procesos: tuple[str, ...] = PROCESOS_DIARIOS,
) -> list[Senal]:
    """Procesos diarios que no dejaron rastro reciente.

    ES LA UNICA SENAL QUE NO SALE DE UNA FILA. Un cron caido no escribe nada, asi
    que buscarlo recorriendo la tabla no lo encuentra nunca: hay que saber de
    antemano que se esperaba y notar que no esta.
    """
    corte = ahora - timedelta(days=DIAS_AUSENTE)
    faltantes = []
    for proceso in procesos:
        ultimas = [c.iniciada_en for c in corridas if c.proceso == proceso]
        if not ultimas:
            faltantes.append(
                Senal(
                    nombre="ausente",
                    proceso=proceso,
                    evidencia="no hay ninguna corrida registrada de este proceso",
                    accion="Revisar si el servicio esta desplegado y si su horario dispara.",
                )
            )
            continue
        ultima = max(ultimas)
        if ultima < corte:
            faltantes.append(
                Senal(
                    nombre="ausente",
                    proceso=proceso,
                    evidencia=(
                        f"ultima corrida {ultima:%Y-%m-%d %H:%M}, "
                        f"hace mas de {DIAS_AUSENTE} dias"
                    ),
                    accion="El proceso deberia correr a diario. Revisar el servicio y sus logs.",
                )
            )
    return faltantes


# --------------------------------------------------------------------------- #
# Salida                                                                        #
# --------------------------------------------------------------------------- #


def encabezado(donde: str, total: int, cobertura: dict[str, int], series: str) -> str:
    """El encabezado que declara sobre que NO se puede opinar.

    Es CA-4, y no es cosmetico: **esta salida se pega en un mensaje**. Si la
    advertencia vive en el documento de criterios y no en el texto, se pierde en
    el primer copiado. Es la misma razon que CA-7 de H4.2.
    """
    lineas = [
        "Diagnostico de control.bitacora_etl · H12.4",
        "",
        f"  {donde}",
        f"  corridas registradas: {total}",
        f"  series por dia esperadas: {series}",
        "",
        "  SOBRE QUE NO PUEDE OPINAR ESTE DIAGNOSTICO",
    ]
    for columna in ("sqlstate", "version_codigo", "reportado_por"):
        con = cobertura.get(columna, 0)
        if con == 0:
            lineas.append(f"    {columna:16} 0 de {total}: nadie la llena todavia")
        else:
            lineas.append(f"    {columna:16} {con} de {total}")
    lineas += [
        "",
        "    Sin sqlstate no se separa un fallo de permisos de uno de datos a",
        "    nivel de corrida: solo queda el texto, y el texto ya engano una vez",
        "    (I-43 decia «exitosa»). Lo que salga de ahi va marcado CONJETURA.",
        "",
        "    control.fallo SI guarda sqlstate, de filas rechazadas. La ceguera es",
        "    por nivel, no total.",
        "",
        "    La cobertura solo se juzga en los procesos con series por dia",
        "    declaradas. En los demas NO se opina, en vez de suponer.",
        "",
        "    Y la de fondo: esto solo ve lo que la bitacora registra. Un fallo",
        "    que nunca se escribio no existe aqui.",
        "",
    ]
    return "\n".join(lineas)


def redactar(senales: list[Senal]) -> str:
    """Las senales en texto, con las conjeturas separadas."""
    if not senales:
        return (
            "  Ninguna senal. Las corridas registradas no muestran ninguno de los\n"
            "  patrones declarados.\n\n"
            "  Eso NO dice que todo este bien: dice que nada de lo que este\n"
            "  diagnostico sabe mirar aparecio. Ver el encabezado.\n"
        )

    ciertas = [s for s in senales if not s.conjetura]
    conjeturas = [s for s in senales if s.conjetura]
    partes = []

    if ciertas:
        partes.append(f"  {len(ciertas)} senal(es) sobre datos estructurados\n")
        for s in ciertas:
            partes.append(_una(s))

    if conjeturas:
        partes.append(
            f"\n  {len(conjeturas)} senal(es) CONJETURA, leidas de texto libre.\n"
            "  No son causas. Confirmar antes de actuar sobre ellas.\n"
        )
        for s in conjeturas:
            partes.append(_una(s))

    return "".join(partes)


def _una(s: Senal) -> str:
    donde = f"corrida {s.corrida_id}" if s.corrida_id is not None else "sin corrida"
    return (
        f"\n  [{s.nombre}] {s.proceso} · {donde}\n"
        f"      evidencia: {s.evidencia}\n"
        f"      accion   : {s.accion}\n"
    )


# --------------------------------------------------------------------------- #
# Lectura de la base                                                            #
# --------------------------------------------------------------------------- #

SQL_CORRIDAS = """
    SELECT id, proceso, estado, iniciada_en, terminada_en,
           filas, filas_leidas, mensaje, sqlstate, version_codigo, reportado_por,
           ventana_desde, ventana_hasta
      FROM control.bitacora_etl
     ORDER BY iniciada_en DESC
     LIMIT %s
"""

SQL_DISTRITOS = "SELECT count(*) FROM geo.distrito"


def leer_corridas(conexion, cuantas: int = 200) -> list[Corrida]:
    """Lee las ultimas corridas. Solo SELECT: este modulo no escribe."""
    with conexion.cursor() as cur:
        cur.execute(SQL_CORRIDAS, (cuantas,))
        return [Corrida(*fila) for fila in cur.fetchall()]


def series_desde_base(conexion) -> dict[str, int]:
    """Cuantas series por dia se esperan, contadas y no supuestas.

    **Es la leccion de I-53**: una funcion no tiene su propia idea de un valor
    que pertenece a otro. El numero de distritos lo manda `geo.distrito`, no una
    constante de este archivo.
    """
    with conexion.cursor() as cur:
        cur.execute(SQL_DISTRITOS)
        fila = cur.fetchone()
    distritos = fila[0] if fila else 0
    if not distritos:
        return {}
    return {"ingesta.lluvia_intensa": distritos}


def cobertura_de(corridas: list[Corrida]) -> dict[str, int]:
    """Cuantas corridas tienen valor en cada columna de diagnostico."""
    return {
        "sqlstate": sum(1 for c in corridas if c.sqlstate),
        "version_codigo": sum(1 for c in corridas if c.version_codigo),
        "reportado_por": sum(1 for c in corridas if c.reportado_por),
    }


def _contra_que_base() -> str:
    """De donde se leyo, dicho en voz alta. Por I-38.

    SE LEE DE `cadena_conexion()`, NO DE LAS VARIABLES DE ENTORNO, y eso es
    **I-53**.

    La version anterior de esta funcion releia `os.getenv("POSTGRES_PORT")` por
    su cuenta, con `"5432"` como valor por defecto. En los guiones que viven
    fuera del repositorio, `load_dotenv()` no encuentra el `.env` del proyecto,
    la variable sale vacia y el defecto se imprime **con el mismo tono que una
    medicion**. El 2026-09-08 eso hizo declarar `localhost:5432` sobre una base
    que estaba en el 5433, y sobre esa declaracion se «corrigio» un documento
    que estaba bien.

    La regla que queda: **una funcion que declara la procedencia no puede tener
    su propia idea de cual es. Le pregunta al mismo codigo que abre la
    conexion.**

    La contrasena no se toca: se descartan todos los campos menos host, port y
    dbname.
    """
    from basedatos.conexion import cadena_conexion

    campos = {}
    for pedazo in cadena_conexion().split():
        clave, _, valor = pedazo.partition("=")
        if clave in ("host", "port", "dbname"):
            campos[clave] = valor

    host = campos.get("host", "?")
    donde = "LOCAL" if host in ("localhost", "127.0.0.1", "::1") else "REMOTA"
    return f"base {donde}: {campos.get('dbname', '?')} en {host}:{campos.get('port', '?')}"


def main(argv: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description="Diagnostico de control.bitacora_etl")
    analizador.add_argument("--salida", help="Archivo donde escribir el informe")
    analizador.add_argument("--cuantas", type=int, default=200, help="Corridas a revisar")
    opciones = analizador.parse_args(argv)

    destino = None
    if opciones.salida:
        destino = open(opciones.salida, "w", encoding="utf-8")  # noqa: SIM115

    def emitir(texto: str = "") -> None:
        print(texto, flush=True)
        if destino:
            destino.write(texto + "\n")
            destino.flush()

    try:
        from basedatos.conexion import conectar
    except ImportError as error:
        print(f"\nCorre esto desde la raiz del repositorio, con el venv activo: {error}\n")
        return 1

    try:
        conexion = conectar()
        try:
            corridas = leer_corridas(conexion, opciones.cuantas)
            series = series_desde_base(conexion)
        finally:
            conexion.close()

        ahora = datetime.now(tz=corridas[0].iniciada_en.tzinfo) if corridas else datetime.now()
        descripcion = (
            ", ".join(f"{k} = {v}" for k, v in sorted(series.items())) if series else "ninguna"
        )

        emitir()
        emitir(encabezado(_contra_que_base(), len(corridas), cobertura_de(corridas), descripcion))

        if not corridas:
            emitir("  La bitacora esta VACIA.")
            emitir()
            emitir("  No es un error: es que todavia no corrio nada, o que corrio")
            emitir("  contra otra base. Ver el encabezado.")
            emitir()
            return 0

        todas = senales_de(corridas, ahora, series) + ausencias(corridas, ahora)
        emitir(redactar(todas))
        return 0
    finally:
        if destino:
            destino.close()


if __name__ == "__main__":
    sys.exit(main())
