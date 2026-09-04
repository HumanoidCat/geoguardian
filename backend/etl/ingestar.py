"""
Ingesta reejecutable con cadencia declarada por evento y producto declarado.
Dueno: Alejandro, por D-38 (la historia era de Cesar). Historia H1.14.

QUE HACE

Hasta hoy el sistema era una foto: H1.1 y H1.2 bajaron el historico una vez y
nadie volvia a las fuentes. Este guion trae lo nuevo de cada fuente con la
cadencia que D-26 declaro, deja escrito **que producto** cargo, no duplica
nada si se corre dos veces, y registra cada corrida en `control.bitacora_etl`.

LA CADENCIA ES UN DATO

`CADENCIA` es un diccionario que el guion imprime al arrancar, no un
comentario: incendio y lluvia intensa a diario, sequia semanal como mucho
(D-26: el SPI-3 mira 90 dias, 83 de los cuales ya se conocian ayer).

LA VENTANA NO SE ESCRIBE A MANO

Cada corrida decide su ventana a partir de lo que ya hay:

  - **lluvia intensa** y **sequia** empiezan `SOLAPE_DIAS` antes del **ultimo
    dia con dato** de precipitacion. Con dato, no con fila: la fuente devuelve
    nulos en sus ultimos dias (latencia), y esos dias hay que volver a pedirlos
    hasta que traigan valor. Un nulo no es un dato (D-07). El solape existe
    porque ClimateSERV **no responde a una peticion cuyo rango no tiene ningun
    dato**: en la primera corrida real, sequia pidio 2026-08-01..09-02 con el
    final publicado hasta el 07-31 y el servicio encolo el trabajo y nunca lo
    entrego (120 s; el medidor esperó 450 s con el mismo resultado). Pedir
    desde unos dias antes del ultimo dato hace que la peticion siempre tenga
    algo que devolver; las filas repetidas no cambian nada (CA-4).
  - **incendio** empieza el dia siguiente a la **ventana de la ultima corrida
    exitosa** en la bitacora. Aqui un dia sin filas es un dia sin fuegos, que si
    es un dato, asi que no hace falta volver a pedirlo.
  - Todas terminan **ayer**: el dia en curso esta incompleto en las tres fuentes.

Si nunca hubo una corrida, la ventana arranca donde terminaron H1.1 y H1.2
(sus constantes `HASTA`, importadas, no copiadas).

PRODUCTO DECLARADO, Y EL FINAL REEMPLAZA AL PRELIMINAR

Las dos fuentes sirven cada dato en dos versiones, y no son el mismo dato:

    precipitacion  chirp (sin estaciones)              ->  chirps (final)
    focos          modis-nrt / viirs-snpp-nrt (~3 h)   ->  modis / viirs-snpp (SP)

La regla vive en el SQL: **el preliminar nunca pisa un valor del final, y un
nulo nunca pisa un valor**. Para focos el reemplazo es por dia y producto: se
borran los NRT del dia y entran los SP, en la misma transaccion. Ninguna de
las dos toca `analitico.riesgo`: reemplazar un dato de entrada no reescribe
una estimacion; recalcularla es volver a correr `estimar_riesgo`, que es
idempotente (H3.6).

LO QUE LA MEDICION CAMBIO (D-40)

El plan era cargar el CHIRP (tipo 90 de ClimateSERV) a diario como producto
preliminar y reemplazarlo con el final cada semana. Medido el 2026-09-03: el
CHIRPS final llega hasta el 2026-07-31 (33 dias) y el CHIRP **solo hasta
principios de junio**, y sobre una ventana sin datos el servicio no responde.
Un "preliminar" que llega despues que el final no es un preliminar. Por eso
**lluvia intensa y sequia cargan el final**, `chirps`, y la latencia de lluvia
intensa queda declarada en la que ese producto tiene. El codigo `chirp`, la
regla de reemplazo y su prueba quedan: son lo que hace falta el dia que exista
un preliminar que si llegue antes.

LO QUE NO RESUELVE, Y QUEDA DICHO

Donde se ejecuta. No hay entorno alojado: la programacion queda declarada y
sin destino. Y por D-31 no regenera el manifiesto de H1.7.

USO

    python -m backend.etl.ingestar                      # los tres eventos
    python -m backend.etl.ingestar --evento incendio
    python -m backend.etl.ingestar --sin-escribir       # decide y descarga, no escribe
    python -m backend.etl.ingestar --registro evidencia-h114.txt
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from basedatos.conexion import ErrorConexion, conectar
from contratos.esquemas import MedicionDiaria

from . import bitacora
from .cargar_focos import CODIGO_CANTON, caja_del_canton
from .cargar_focos import HASTA as HASTA_FOCOS
from .cargar_focos import SQL_INSERTAR as SQL_INSERTAR_FOCO
from .cargar_mediciones import HASTA as HASTA_MEDICIONES
from .fuentes import chirps, fabrica, firms_area
from .fuentes.chirps import ErrorChirps
from .fuentes.firms import ErrorFirms, FocoBruto
from .fuentes.hibrido import Territorio, territorios_desde_base
from .fuentes.power import ErrorPower

Registrar = Callable[..., None]

# --------------------------------------------------------------------------- #
# La cadencia y el producto, como datos                                        #
# --------------------------------------------------------------------------- #

CADENCIA: dict[str, str] = {
    "incendio": "diaria",
    "lluvia_intensa": "diaria",
    "sequia": "semanal",
}
DIAS_DE_CADENCIA = {"diaria": 1, "semanal": 7}

# Cuantos dias con dato se vuelven a pedir en cada corrida de precipitacion.
# Ver "LA VENTANA NO SE ESCRIBE A MANO" en la cabecera.
SOLAPE_DIAS = 3

# Que producto trae cada proceso. Para precipitacion es el codigo que va en
# `fuente_precipitacion`; para focos, la version que entra en `producto`.
PRODUCTO: dict[str, str] = {
    "incendio": "nrt, reemplazado por sp donde ya llego",
    # Las dos cargan el final (D-40): el CHIRP medido llega despues que el final.
    "lluvia_intensa": chirps.PRODUCTOS[chirps.TIPO_DATO],  # chirps
    "sequia": chirps.PRODUCTOS[chirps.TIPO_DATO],  # chirps
}
TIPO_DATO_DE = {v: k for k, v in chirps.PRODUCTOS.items()}

EVENTOS = tuple(CADENCIA)
PROCESO = {evento: f"ingesta.{evento}" for evento in EVENTOS}

EN_CURSO, EXITOSA, FALLIDA, OMITIDA = "en_curso", "exitosa", "fallida", "omitida"


class ErrorIngesta(Exception):
    """Falla que impide continuar la corrida. Queda en la bitacora como fallida."""


# --------------------------------------------------------------------------- #
# SQL                                                                          #
# --------------------------------------------------------------------------- #

SQL_ULTIMA_CORRIDA = """
    SELECT terminada_en, ventana_hasta
      FROM control.bitacora_etl
     WHERE proceso = %s AND estado = 'exitosa'
     ORDER BY terminada_en DESC
     LIMIT 1
"""
SQL_ABRIR_CORRIDA = """
    INSERT INTO control.bitacora_etl
        (proceso, iniciada_en, estado, ventana_desde, ventana_hasta, producto)
    VALUES (%s, now(), 'en_curso', %s, %s, %s)
    RETURNING id
"""
SQL_CERRAR_CORRIDA = """
    UPDATE control.bitacora_etl
       SET terminada_en = now(), estado = %s, filas = %s, mensaje = %s
     WHERE id = %s
"""
# `set_config(..., true)` es SET LOCAL con parametros: muere con la transaccion
# y enlaza lo que caiga en control.fallo con esta corrida (migracion 012).
SQL_DECLARAR_CORRIDA = "SELECT set_config('geoguardian.corrida_id', %s, true)"

# Ultimo dia CON DATO de precipitacion, de cualquiera de los dos productos.
SQL_ULTIMO_DIA_LLUVIA = """
    SELECT max(fecha)
      FROM crudo.medicion_diaria
     WHERE precipitacion_mm IS NOT NULL
       AND fuente_precipitacion IN ('chirp', 'chirps')
"""
# Para sequia, ademas: el primer dia que sigue en preliminar, si lo hay. La
# corrida semanal vuelve a pedir desde ahi para que el final lo reemplace.
SQL_PRIMER_PRELIMINAR = """
    SELECT min(fecha)
      FROM crudo.medicion_diaria
     WHERE fuente_precipitacion = 'chirp'
"""

# La regla de reemplazo, escrita una vez y usada en las dos columnas:
#   - un nulo nunca pisa un valor;
#   - el preliminar nunca pisa un VALOR del final (un nulo del final si se
#     puede completar con el preliminar, y queda declarado como preliminar).
REEMPLAZA = (
    "EXCLUDED.precipitacion_mm IS NOT NULL AND NOT ("
    "medicion_diaria.fuente_precipitacion = 'chirps' "
    "AND medicion_diaria.precipitacion_mm IS NOT NULL "
    "AND EXCLUDED.fuente_precipitacion <> 'chirps')"
)
NUEVA_PRECIPITACION = (
    f"CASE WHEN {REEMPLAZA} THEN EXCLUDED.precipitacion_mm "
    "ELSE medicion_diaria.precipitacion_mm END"
)
NUEVA_FUENTE = (
    f"CASE WHEN {REEMPLAZA} THEN EXCLUDED.fuente_precipitacion "
    "ELSE medicion_diaria.fuente_precipitacion END"
)
RESTO = (
    "temp_max_c",
    "temp_min_c",
    "temp_media_c",
    "humedad_relativa_pct",
    "viento_ms",
    "radiacion_mj_m2",
)
# El resto viene de POWER, que corrige hacia atras: un valor nuevo entra, un
# nulo nuevo no borra el valor que habia.
NUEVO_RESTO = ",\n        ".join(
    f"{c} = coalesce(EXCLUDED.{c}, medicion_diaria.{c})" for c in RESTO
)
# El WHERE hace que una segunda corrida identica no toque la fila: rowcount
# cuenta solo lo que cambio, y `descargado_en` no se mueve en vano.
CAMBIA_ALGO = " OR ".join(
    [f"medicion_diaria.precipitacion_mm IS DISTINCT FROM ({NUEVA_PRECIPITACION})"]
    + [f"medicion_diaria.fuente_precipitacion IS DISTINCT FROM ({NUEVA_FUENTE})"]
    + [
        f"medicion_diaria.{c} IS DISTINCT FROM coalesce(EXCLUDED.{c}, medicion_diaria.{c})"
        for c in RESTO
    ]
)

SQL_ESCRIBIR_MEDICION = f"""
    INSERT INTO crudo.medicion_diaria (
        codigo_distrito, fecha,
        temp_max_c, temp_min_c, temp_media_c,
        humedad_relativa_pct, viento_ms, radiacion_mj_m2,
        precipitacion_mm,
        fuente_precipitacion, fuente_resto,
        descargado_en
    )
    VALUES (
        %(codigo_distrito)s, %(fecha)s,
        %(temp_max_c)s, %(temp_min_c)s, %(temp_media_c)s,
        %(humedad_relativa_pct)s, %(viento_ms)s, %(radiacion_mj_m2)s,
        %(precipitacion_mm)s,
        %(fuente_precipitacion)s, 'power',
        now()
    )
    ON CONFLICT (codigo_distrito, fecha) DO UPDATE SET
        {NUEVO_RESTO},
        precipitacion_mm     = {NUEVA_PRECIPITACION},
        fuente_precipitacion = {NUEVA_FUENTE},
        descargado_en        = EXCLUDED.descargado_en
    WHERE {CAMBIA_ALGO}
"""

# Focos: hasta donde llega la ventana de NRT que ya se cargo, por producto.
SQL_RANGO_NRT = """
    SELECT min(fecha), max(fecha)
      FROM crudo.foco_calor
     WHERE producto = %s
"""
SQL_BORRAR_NRT = """
    DELETE FROM crudo.foco_calor
     WHERE producto = %s AND fecha BETWEEN %s AND %s
"""


# --------------------------------------------------------------------------- #
# Bitacora de corridas (control.bitacora_etl, H12.1 / migracion 013)          #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class UltimaCorrida:
    terminada_en: datetime
    ventana_hasta: date | None


@dataclass
class Corrida:
    """Lo que la bitacora sabe de una corrida. Es lo que devuelve `correr`."""

    proceso: str
    producto: str
    estado: str
    ventana: tuple[date, date] | None = None
    filas: int = 0
    mensaje: str = ""
    id: int | None = None


class Bitacora:
    """Escribe en `control.bitacora_etl`. Cada metodo es una sentencia."""

    def __init__(self, conexion) -> None:
        self._conexion = conexion

    def ultima(self, proceso: str) -> UltimaCorrida | None:
        with self._conexion.cursor() as cursor:
            cursor.execute(SQL_ULTIMA_CORRIDA, (proceso,))
            fila = cursor.fetchone()
        if fila is None:
            return None
        return UltimaCorrida(terminada_en=fila[0], ventana_hasta=fila[1])

    def abrir(self, corrida: Corrida) -> int:
        desde, hasta = corrida.ventana if corrida.ventana else (None, None)
        with self._conexion.cursor() as cursor:
            cursor.execute(SQL_ABRIR_CORRIDA, (corrida.proceso, desde, hasta, corrida.producto))
            fila = cursor.fetchone()
        if fila is None:
            raise ErrorIngesta("La bitacora no devolvio el id de la corrida")
        corrida.id = int(fila[0])
        return corrida.id

    def cerrar(self, corrida: Corrida) -> None:
        with self._conexion.cursor() as cursor:
            cursor.execute(
                SQL_CERRAR_CORRIDA,
                (corrida.estado, corrida.filas, corrida.mensaje or None, corrida.id),
            )

    def declarar(self, cursor, corrida: Corrida) -> None:
        """Dentro de la transaccion: enlaza control.fallo con esta corrida."""
        cursor.execute(SQL_DECLARAR_CORRIDA, (str(corrida.id),))


# --------------------------------------------------------------------------- #
# Decidir la ventana                                                           #
# --------------------------------------------------------------------------- #


def toca_correr(evento: str, ultima: UltimaCorrida | None, hoy: date) -> tuple[bool, str]:
    """
    CA-2: sequia solo corre si pasaron 7 dias o mas desde su ultima corrida
    exitosa. Las diarias corren siempre; si estan al dia, la ventana lo dira.
    """
    cada = DIAS_DE_CADENCIA[CADENCIA[evento]]
    if ultima is None or cada == 1:
        return True, "primera corrida" if ultima is None else "cadencia diaria"
    hace = (hoy - ultima.terminada_en.date()).days
    if hace < cada:
        return False, f"ultima corrida hace {hace} dias; cadencia {CADENCIA[evento]} ({cada})"
    return True, f"ultima corrida hace {hace} dias; toca ({CADENCIA[evento]})"


def _fecha(valor) -> date | None:
    if valor is None:
        return None
    return valor.date() if isinstance(valor, datetime) else valor


def ventana_precipitacion(conexion, evento: str, hoy: date) -> tuple[date, date] | None:
    """
    Desde SOLAPE_DIAS antes del ultimo dia con dato hasta ayer; None si esta al dia.

    Sequia ademas retrocede hasta el primer dia que siga en preliminar, si
    lo hay, para que el final lo reemplace.
    """
    hasta = hoy - timedelta(days=1)
    with conexion.cursor() as cursor:
        cursor.execute(SQL_ULTIMO_DIA_LLUVIA)
        fila = cursor.fetchone()
    ultimo = _fecha(fila[0]) if fila else None
    if ultimo is None:
        desde = HASTA_MEDICIONES + timedelta(days=1)
    elif ultimo >= hasta:
        return None
    else:
        desde = ultimo + timedelta(days=1 - SOLAPE_DIAS)

    if evento == "sequia":
        with conexion.cursor() as cursor:
            cursor.execute(SQL_PRIMER_PRELIMINAR)
            fila = cursor.fetchone()
        primero = _fecha(fila[0]) if fila else None
        if primero is not None:
            desde = min(desde, primero)
    return (desde, hasta) if desde <= hasta else None


def ventana_incendio(ultima: UltimaCorrida | None, hoy: date) -> tuple[date, date] | None:
    """Desde el dia siguiente a la ventana de la ultima corrida exitosa, hasta ayer."""
    base = ultima.ventana_hasta if ultima and ultima.ventana_hasta else HASTA_FOCOS
    desde = base + timedelta(days=1)
    hasta = hoy - timedelta(days=1)
    return (desde, hasta) if desde <= hasta else None


# --------------------------------------------------------------------------- #
# Escribir                                                                     #
# --------------------------------------------------------------------------- #


def _filas_afectadas(cursor, enviadas: int) -> int:
    """rowcount tras executemany es la suma en psycopg 3; -1 es «no se sabe»."""
    conteo = getattr(cursor, "rowcount", -1)
    return enviadas if conteo is None or conteo < 0 else int(conteo)


def escribir_mediciones(
    conexion, corrida: Corrida, mediciones: list[MedicionDiaria], producto: str
) -> int:
    """Un lote por corrida, con la corrida declarada en la sesion. Devuelve filas que cambiaron."""
    parametros = [
        {
            "codigo_distrito": m.codigo_distrito,
            "fecha": m.fecha,
            "temp_max_c": m.temp_max_c,
            "temp_min_c": m.temp_min_c,
            "temp_media_c": m.temp_media_c,
            "humedad_relativa_pct": m.humedad_relativa_pct,
            "viento_ms": m.viento_ms,
            "radiacion_mj_m2": m.radiacion_mj_m2,
            "precipitacion_mm": m.precipitacion_mm,
            "fuente_precipitacion": producto,
        }
        for m in mediciones
    ]
    if not parametros:
        return 0
    with conexion.transaction(), conexion.cursor() as cursor:
        Bitacora(conexion).declarar(cursor, corrida)
        cursor.executemany(SQL_ESCRIBIR_MEDICION, parametros)
        return _filas_afectadas(cursor, len(parametros))


def _parametros_foco(f: FocoBruto) -> dict:
    return {
        "producto": f.producto,
        "satelite": f.satelite,
        "fecha": f.fecha,
        "hora_utc": f.hora_utc,
        "latitud": f.latitud,
        "longitud": f.longitud,
        "codigo_canton": CODIGO_CANTON,
        "confianza": f.confianza,
        "confianza_bruta": f.confianza_bruta,
        "brillo_k": f.brillo_k,
        "brillo_largo_k": f.brillo_largo_k,
        "banda_origen": f.banda_origen,
        "frp_mw": f.frp_mw,
        "tipo": f.tipo,
        "dia_noche": f.dia_noche,
    }


@dataclass(frozen=True)
class Reemplazo:
    """Dias de NRT de un producto que el SP ya cubre: se borran y entran los SP."""

    base: str
    desde: date
    hasta: date


def planear_incendio(
    conexion, extractor, ventana: tuple[date, date] | None
) -> tuple[list[tuple[str, bool, date, date]], list[Reemplazo], list[str]]:
    """
    Que pedir y en que version, segun `data_availability`.

    Devuelve los tramos nuevos (producto, preliminar, desde, hasta), los
    reemplazos pendientes y los avisos: dias que ninguna version cubre. Todo
    sale del servicio y de la tabla, no de fechas escritas a mano. Un hueco no
    detiene la corrida, pero queda en la bitacora: se puede continuar, nunca
    callar (H1.9).
    """
    disponibilidad = extractor.disponibilidad()
    tramos: list[tuple[str, bool, date, date]] = []
    reemplazos: list[Reemplazo] = []
    avisos: list[str] = []

    for base in extractor.productos:
        final = disponibilidad.get((base, "final"))
        preliminar = disponibilidad.get((base, "preliminar"))
        fin_final = final[1] if final else None

        if ventana:
            desde, hasta = ventana
            if fin_final and desde <= fin_final:
                tramos.append((base, False, desde, min(hasta, fin_final)))
                desde = fin_final + timedelta(days=1)
            if desde <= hasta:
                if preliminar is None:
                    raise ErrorIngesta(f"FIRMS no lista la version preliminar de {base}")
                if desde < preliminar[0]:
                    avisos.append(
                        f"{base}: ni SP ni NRT cubren {desde}..{preliminar[0] - timedelta(days=1)}"
                    )
                    desde = preliminar[0]
                if desde <= hasta:
                    tramos.append((base, True, desde, min(hasta, preliminar[1])))

        if fin_final:
            codigo = firms_area.codigo_producto(base, preliminar=True)
            with conexion.cursor() as cursor:
                cursor.execute(SQL_RANGO_NRT, (codigo,))
                fila = cursor.fetchone()
            primero, ultimo = (_fecha(fila[0]), _fecha(fila[1])) if fila else (None, None)
            if primero and ultimo and primero <= fin_final:
                reemplazos.append(Reemplazo(base, primero, min(ultimo, fin_final)))

    return tramos, reemplazos, avisos


def escribir_focos(conexion, corrida: Corrida, extractor, tramos, reemplazos, registrar) -> int:
    """Descarga y escribe todo en una transaccion: o entra completo o no entra."""
    with conexion.transaction(), conexion.cursor() as cursor:
        Bitacora(conexion).declarar(cursor, corrida)
        total = 0
        for r in reemplazos:
            codigo = firms_area.codigo_producto(r.base, preliminar=True)
            cursor.execute(SQL_BORRAR_NRT, (codigo, r.desde, r.hasta))
            borradas = _filas_afectadas(cursor, 0)
            focos = extractor.descargar(
                r.desde, r.hasta, r.base, preliminar=False, registrar=registrar
            )
            if focos:
                cursor.executemany(SQL_INSERTAR_FOCO, [_parametros_foco(f) for f in focos])
            registrar(
                f"  reemplazo {r.base} {r.desde}..{r.hasta}: "
                f"{borradas} nrt borrados, {len(focos)} sp escritos"
            )
            total += len(focos)
        for base, preliminar, desde, hasta in tramos:
            focos = extractor.descargar(desde, hasta, base, preliminar, registrar=registrar)
            if focos:
                cursor.executemany(SQL_INSERTAR_FOCO, [_parametros_foco(f) for f in focos])
            total += len(focos)
        return total


# --------------------------------------------------------------------------- #
# Una corrida                                                                  #
# --------------------------------------------------------------------------- #


def construir_extractor(evento: str, conexion, territorios: list[Territorio] | None, registrar):
    """Por la fabrica de H6.3. Para precipitacion, con el producto del evento."""
    if evento == "incendio":
        return fabrica.crear_focos("firms-area", caja=caja_del_canton(conexion))
    if territorios is None:
        territorios = territorios_desde_base(conexion, CODIGO_CANTON)
    return fabrica.crear_clima(
        "hibrido",
        territorios=territorios,
        registrar=registrar,
        tipo_dato_chirps=TIPO_DATO_DE[PRODUCTO[evento]],
    )


def correr(
    conexion,
    evento: str,
    hoy: date,
    registrar: Registrar = print,
    extractor=None,
    territorios: list[Territorio] | None = None,
    escribir: bool = True,
) -> Corrida:
    """
    Una corrida de un evento, de principio a fin, registrada.

    `extractor` y `territorios` se inyectan para probar sin red ni base; en
    produccion salen de la fabrica y de `geo.distrito`. Con `escribir=False`
    decide y descarga pero no escribe ni registra.
    """
    if evento not in CADENCIA:
        raise ErrorIngesta(f"Evento {evento!r} desconocido; conocidos: {EVENTOS}")

    corrida = Corrida(proceso=PROCESO[evento], producto=PRODUCTO[evento], estado=EN_CURSO)
    libro = Bitacora(conexion)
    ultima = libro.ultima(corrida.proceso)

    corre, motivo = toca_correr(evento, ultima, hoy)
    registrar(
        f"{corrida.proceso}: cadencia {CADENCIA[evento]}, producto {corrida.producto}; {motivo}"
    )
    if not corre:
        return _omitir(libro, corrida, motivo, registrar, escribir)

    if evento == "incendio":
        corrida.ventana = ventana_incendio(ultima, hoy)
    else:
        corrida.ventana = ventana_precipitacion(conexion, evento, hoy)
    if corrida.ventana is None:
        return _omitir(libro, corrida, "al dia: no hay dias nuevos que pedir", registrar, escribir)

    desde, hasta = corrida.ventana
    registrar(f"  ventana {desde} a {hasta} ({(hasta - desde).days + 1} dias)")
    if escribir:
        libro.abrir(corrida)

    propio = extractor is None
    try:
        if extractor is None:
            extractor = construir_extractor(evento, conexion, territorios, registrar)
        if not extractor.disponible():
            raise ErrorIngesta(f"{extractor.nombre} no responde; no se escribe nada")

        if evento == "incendio":
            tramos, reemplazos, avisos = planear_incendio(conexion, extractor, corrida.ventana)
            for base, preliminar, d, h in tramos:
                registrar(f"  pedir {firms_area.codigo_producto(base, preliminar)} {d}..{h}")
            for r in reemplazos:
                registrar(f"  reemplazar {r.base}-nrt por sp en {r.desde}..{r.hasta}")
            for aviso in avisos:
                registrar(f"  AVISO {aviso}")
            corrida.mensaje = "; ".join(avisos)
            if escribir:
                corrida.filas = escribir_focos(
                    conexion, corrida, extractor, tramos, reemplazos, registrar
                )
            else:
                for base, preliminar, d, h in tramos:
                    corrida.filas += len(
                        extractor.descargar(d, h, base, preliminar, registrar=registrar)
                    )
        else:
            if territorios is None:
                territorios = territorios_desde_base(conexion, CODIGO_CANTON)
            mediciones: list[MedicionDiaria] = []
            for territorio in territorios:
                mediciones += extractor.extraer(territorio.codigo, desde, hasta)
            sin_dato = sum(1 for m in mediciones if m.precipitacion_mm is None)
            registrar(f"  {len(mediciones)} mediciones, {sin_dato} sin precipitacion")
            if escribir:
                corrida.filas = escribir_mediciones(conexion, corrida, mediciones, corrida.producto)
            else:
                corrida.filas = len(mediciones)

        corrida.estado = EXITOSA
    except (ErrorIngesta, ErrorChirps, ErrorPower, ErrorFirms, ErrorConexion) as error:
        corrida.estado = FALLIDA
        corrida.mensaje = f"{type(error).__name__}: {error}"
    finally:
        if propio and extractor is not None and hasattr(extractor, "cerrar"):
            extractor.cerrar()

    if escribir:
        libro.cerrar(corrida)
    registrar(
        f"  {corrida.estado}: {corrida.filas} filas{' · ' + corrida.mensaje if corrida.mensaje else ''}"
    )
    return corrida


def _omitir(libro: Bitacora, corrida: Corrida, motivo: str, registrar, escribir: bool) -> Corrida:
    corrida.estado = OMITIDA
    corrida.mensaje = motivo
    if escribir:
        libro.abrir(corrida)
        libro.cerrar(corrida)
    registrar(f"  omitida: {motivo}")
    return corrida


# --------------------------------------------------------------------------- #
# Programa                                                                     #
# --------------------------------------------------------------------------- #


def principal(argumentos: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        description="Trae lo nuevo de cada fuente con la cadencia declarada por evento"
    )
    analizador.add_argument("--evento", action="append", choices=EVENTOS, help="Repetible")
    analizador.add_argument(
        "--sin-escribir", action="store_true", help="Decide y descarga, no escribe"
    )
    analizador.add_argument("--registro", help="Archivo donde guardar la salida completa")
    opciones = analizador.parse_args(argumentos)

    with bitacora.abrir(opciones.registro) as registrar:
        return _principal(opciones, registrar)


def encabezado(registrar: Registrar, hoy: date) -> None:
    """CA-1: la cadencia y el producto se imprimen al arrancar, como datos."""
    registrar(f"Cadencia declarada: {CADENCIA}")
    registrar(f"Producto por evento: {PRODUCTO}")
    registrar(f"Hoy: {hoy} · inicio {datetime.now().astimezone().isoformat(timespec='seconds')}")


def _principal(opciones, registrar) -> int:
    hoy = date.today()
    eventos = opciones.evento or list(EVENTOS)
    encabezado(registrar, hoy)
    if opciones.sin_escribir:
        registrar("Modo --sin-escribir: no se escribe ni se registra nada")

    arranque = time.monotonic()
    fallidas = 0
    try:
        # autocommit: la apertura de la corrida se confirma sola, y la escritura
        # de datos va en su propia transaccion. Es lo que aprendio cargar_focos.
        with conectar(autocommit=True) as conexion:
            for evento in eventos:
                registrar("")
                corrida = correr(
                    conexion, evento, hoy, registrar, escribir=not opciones.sin_escribir
                )
                fallidas += corrida.estado == FALLIDA
    except ErrorConexion as error:
        registrar(f"\nFALLO: {error}")
        return 1
    except Exception:
        registrar("\nFALLO INESPERADO:\n" + traceback.format_exc())
        raise

    registrar(
        f"\n{len(eventos)} procesos en {time.monotonic() - arranque:.1f} s; fallidos: {fallidas}"
    )
    return 1 if fallidas else 0


if __name__ == "__main__":
    sys.exit(principal())
