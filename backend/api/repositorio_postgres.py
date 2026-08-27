"""
Repositorio contra PostgreSQL. Dueno: Cesar. Historia H6.2, issue #63.

QUE HACE Y QUE NO

Cumple el protocolo `Repositorio` leyendo y escribiendo en la base real, en lugar
del simulado que respondia hasta ahora. Los endpoints de H6.1 no cambian ni una
linea: dependen del protocolo, no de la clase, y `dependencias.py` es el unico
archivo que sabe cual implementacion esta activa.

**SEIS DE LOS DIECISEIS METODOS ESTAN IMPLEMENTADOS.** Los otros diez dependen de
tablas que todavia no existen:

    implementados          tabla                     historia que la trajo
    ---------------------  ------------------------  ---------------------
    listar_distritos       geo.distrito              H1.3
    obtener_distrito       geo.distrito              H1.3
    guardar_mediciones     crudo.medicion_diaria     H1.1
    obtener_mediciones     crudo.medicion_diaria     H1.1
    guardar_focos          crudo.foco_calor          H1.2
    contar_focos           crudo.foco_calor          H1.2

    pendientes             lo que falta              historia que lo va a traer
    ---------------------  ------------------------  --------------------------
    guardar_indices        analitico.indice          H2.5
    obtener_indices        analitico.indice          H2.5
    guardar_riesgos        analitico.riesgo          H3.6
    obtener_riesgo         analitico.riesgo          H3.6
    obtener_riesgos_por_f  analitico.riesgo          H3.6
    listar_eventos         analitico.evento          H4.3
    guardar_reporte_cal    control.reporte_calidad   H1.5
    listar_reportes_cal    control.reporte_calidad   H1.5
    guardar_metricas       analitico.metrica         H3.6
    listar_metricas        analitico.metrica         H3.6

POR QUE LOS PENDIENTES FALLAN EN VEZ DE DEVOLVER VACIO

Devolver una lista vacia diria «no hay ninguno», que es una respuesta legitima y
**falsa**: lo cierto es que la tabla no existe todavia. Es la misma distincion de
D-22 entre un cero y un hueco, y la razon por la que `listar_metricas` del simulado
devuelve vacio pero lo explica en su docstring: alli el vacio es la verdad.

Un metodo que miente en silencio se descubre semanas despues, cuando alguien
grafica una serie de indices que nunca existieron. Uno que falla nombrando la
historia que le falta se descubre en el momento.

POR QUE EL SIMULADO SIGUE SIENDO EL VALOR POR OMISION

`obtener_riesgo` y `obtener_riesgos_por_fecha` son de los pendientes, y las dos
estan expuestas en endpoints que el visor ya consume. Activar esta implementacion
hoy romperia el visor de Avril. H6.2 demuestra que la sustitucion funciona; el dia
que se active es cuando existan las tablas. Ver `dependencias.py`.

SOBRE LAS ESCRITURAS

El protocolo dice que toda escritura ocurre dentro de una transaccion. La conexion
se abre con `autocommit=True` y cada metodo de escritura abre la suya con
`conexion.transaction()`. **Con la conexion en modo transaccion no funcionaria**:
cualquier lectura previa abre una transaccion implicita y el `transaction()`
siguiente se vuelve un punto de retorno dentro de ella. Eso ya paso en
`cargar_mediciones.py` de H1.1 y se detecto porque `descargado_en` tenia un unico
valor para las ocho cargas. Ver la evidencia de H1.1.
"""

from __future__ import annotations

import json
from datetime import date, timedelta

from basedatos.conexion import conectar
from contratos.enums import MetodoImputacion, TipoEvento
from contratos.esquemas import (
    Distrito,
    EventoHistorico,
    FocoCalor,
    IndiceDerivado,
    MedicionDiaria,
    MetricasModelo,
    ReporteCalidad,
    Riesgo,
)

CODIGO_CANTON = 508

# Que historia trae cada tabla que falta. El mensaje de error lo cita para que
# quien se tope con el sepa a que esperar en vez de creer que hay un defecto.
PENDIENTES = {
    "guardar_indices": ("analitico.indice", "H2.5"),
    "obtener_indices": ("analitico.indice", "H2.5"),
    "guardar_riesgos": ("analitico.riesgo", "H3.6"),
    "obtener_riesgo": ("analitico.riesgo", "H3.6"),
    "obtener_riesgos_por_fecha": ("analitico.riesgo", "H3.6"),
    "listar_eventos": ("analitico.evento", "H4.3"),
    "guardar_reporte_calidad": ("control.reporte_calidad", "H1.5"),
    "listar_reportes_calidad": ("control.reporte_calidad", "H1.5"),
    "guardar_metricas": ("analitico.metrica", "H3.6"),
    "listar_metricas": ("analitico.metrica", "H3.6"),
}


class TablaPendiente(NotImplementedError):
    """
    El metodo existe en el protocolo pero su tabla todavia no.

    Hereda de `NotImplementedError` a proposito: quien capture esa excepcion
    generica tambien atrapa esta, y no hace falta que conozca este modulo.
    """


def _pendiente(metodo: str):
    tabla, historia = PENDIENTES[metodo]
    return TablaPendiente(
        f"`{metodo}` necesita la tabla `{tabla}`, que todavia no existe: la trae la "
        f"historia {historia}. No se devuelve una lista vacia porque diria «no hay "
        f"ninguno», que es distinto de «esto no esta construido». Ver la cabecera de "
        f"backend/api/repositorio_postgres.py."
    )


SQL_DISTRITOS = """
    SELECT codigo, nombre, area_km2, poblacion, ST_AsGeoJSON(geometria)
      FROM geo.distrito
     WHERE codigo_canton = %s
     ORDER BY codigo
"""

SQL_DISTRITO = """
    SELECT codigo, nombre, area_km2, poblacion, ST_AsGeoJSON(geometria)
      FROM geo.distrito
     WHERE codigo = %s
"""

# Una fila por dia del rango, incluidos los que no tienen medicion. El contrato lo
# exige: «el consumidor necesita ver los huecos». Sin el generate_series, un dia
# ausente seria indistinguible de un dia que no existe.
SQL_MEDICIONES = """
    SELECT dia::date,
           m.temp_max_c, m.temp_min_c, m.temp_media_c,
           m.precipitacion_mm, m.humedad_relativa_pct, m.viento_ms, m.radiacion_mj_m2,
           m.imputado, m.metodo_imputacion
      FROM generate_series(%(desde)s::date, %(hasta)s::date, interval '1 day') AS dia
      LEFT JOIN crudo.medicion_diaria m
             ON m.fecha = dia::date AND m.codigo_distrito = %(codigo)s
     ORDER BY dia
"""

SQL_GUARDAR_MEDICION = """
    INSERT INTO crudo.medicion_diaria (
        codigo_distrito, fecha,
        temp_max_c, temp_min_c, temp_media_c,
        humedad_relativa_pct, viento_ms, radiacion_mj_m2, precipitacion_mm,
        fuente_precipitacion, fuente_resto, imputado, metodo_imputacion, descargado_en
    )
    VALUES (
        %(codigo_distrito)s, %(fecha)s,
        %(temp_max_c)s, %(temp_min_c)s, %(temp_media_c)s,
        %(humedad_relativa_pct)s, %(viento_ms)s, %(radiacion_mj_m2)s, %(precipitacion_mm)s,
        'chirps', 'power', %(imputado)s, %(metodo_imputacion)s, now()
    )
    ON CONFLICT (codigo_distrito, fecha) DO UPDATE SET
        temp_max_c           = EXCLUDED.temp_max_c,
        temp_min_c           = EXCLUDED.temp_min_c,
        temp_media_c         = EXCLUDED.temp_media_c,
        humedad_relativa_pct = EXCLUDED.humedad_relativa_pct,
        viento_ms            = EXCLUDED.viento_ms,
        radiacion_mj_m2      = EXCLUDED.radiacion_mj_m2,
        precipitacion_mm     = EXCLUDED.precipitacion_mm,
        imputado             = EXCLUDED.imputado,
        metodo_imputacion    = EXCLUDED.metodo_imputacion,
        descargado_en        = EXCLUDED.descargado_en
"""

# El contrato dice que guardar_focos «asigna cada foco a su distrito por
# interseccion espacial al guardar». Se hace con ST_Contains aqui, que es la capa
# que conoce las geometrias, igual que en cargar_focos.py de H1.2.
SQL_GUARDAR_FOCO = """
    INSERT INTO crudo.foco_calor (
        producto, satelite, fecha, hora_utc, latitud, longitud,
        codigo_distrito, confianza, confianza_bruta,
        brillo_k, banda_origen, descargado_en
    )
    VALUES (
        %(producto)s, %(satelite)s, %(fecha)s, %(hora_utc)s, %(latitud)s, %(longitud)s,
        (SELECT d.codigo
           FROM geo.distrito d
          WHERE d.codigo_canton = %(codigo_canton)s
            AND ST_Contains(d.geometria, ST_SetSRID(ST_MakePoint(%(longitud)s, %(latitud)s), 4326))
          LIMIT 1),
        %(confianza)s, %(confianza_bruta)s,
        %(brillo_k)s, %(banda_origen)s, now()
    )
    ON CONFLICT (producto, satelite, fecha, hora_utc, latitud, longitud) DO UPDATE SET
        codigo_distrito = EXCLUDED.codigo_distrito,
        confianza       = EXCLUDED.confianza,
        confianza_bruta = EXCLUDED.confianza_bruta,
        brillo_k        = EXCLUDED.brillo_k,
        descargado_en   = EXCLUDED.descargado_en
"""

SQL_CONTAR_FOCOS = """
    SELECT count(*)
      FROM crudo.foco_calor
     WHERE codigo_distrito = %s AND fecha BETWEEN %s AND %s
"""


class RepositorioPostgres:
    """
    Cumple el protocolo `Repositorio` contra la base real.

    La conexion se recibe o se abre aqui. Recibirla es lo que permite probar este
    modulo **sin base de datos**, pasandole un doble que registra el SQL emitido:
    es lo que pide el titulo de H6.2 y lo que hace `verificar_h62.py`.
    """

    def __init__(self, conexion=None, codigo_canton: int = CODIGO_CANTON) -> None:
        # autocommit=True a proposito: ver la cabecera del modulo.
        self._conexion = conexion if conexion is not None else conectar(autocommit=True)
        self._codigo_canton = codigo_canton

    def cerrar(self) -> None:
        self._conexion.close()

    # -- Territorio --------------------------------------------------------- #

    def _a_distrito(self, fila) -> Distrito:
        codigo, nombre, area, poblacion, geojson = fila
        return Distrito(
            codigo=codigo,
            nombre=nombre,
            area_km2=float(area) if area is not None else None,
            poblacion=poblacion,
            geometria=json.loads(geojson),
        )

    def listar_distritos(self) -> list[Distrito]:
        with self._conexion.cursor() as cursor:
            cursor.execute(SQL_DISTRITOS, (self._codigo_canton,))
            return [self._a_distrito(f) for f in cursor.fetchall()]

    def obtener_distrito(self, codigo: str) -> Distrito | None:
        """None si no existe. El contrato dice que la ausencia es un caso valido."""
        with self._conexion.cursor() as cursor:
            cursor.execute(SQL_DISTRITO, (codigo,))
            fila = cursor.fetchone()
        return self._a_distrito(fila) if fila else None

    # -- Mediciones --------------------------------------------------------- #

    def guardar_mediciones(self, mediciones: list[MedicionDiaria]) -> int:
        """
        Idempotente por la clave natural. Si falla a mitad revierte todo.

        La transaccion envuelve el `executemany` completo, asi que una carga
        interrumpida no deja filas sueltas, que es lo que el contrato exige.
        """
        if not mediciones:
            return 0

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
                "imputado": m.imputado,
                "metodo_imputacion": m.metodo_imputacion.value,
            }
            for m in mediciones
        ]
        with self._conexion.transaction(), self._conexion.cursor() as cursor:
            cursor.executemany(SQL_GUARDAR_MEDICION, parametros)
        return len(parametros)

    def obtener_mediciones(
        self, codigo_distrito: str, desde: date, hasta: date
    ) -> list[MedicionDiaria]:
        """
        Una fila por dia del rango, con los dias sin dato en None.

        El rango se genera en SQL con `generate_series` y se une por la izquierda:
        asi un dia sin medicion sale igual, con sus campos nulos. Omitirlo haria
        indistinguible un hueco de un dia que no existe.
        """
        with self._conexion.cursor() as cursor:
            cursor.execute(
                SQL_MEDICIONES, {"codigo": codigo_distrito, "desde": desde, "hasta": hasta}
            )
            filas = cursor.fetchall()

        salida = []
        for fila in filas:
            (dia, tmax, tmin, tmed, lluvia, humedad, viento, radiacion, imputado, metodo) = fila
            salida.append(
                MedicionDiaria(
                    codigo_distrito=codigo_distrito,
                    fecha=dia,
                    temp_max_c=tmax,
                    temp_min_c=tmin,
                    temp_media_c=tmed,
                    precipitacion_mm=lluvia,
                    humedad_relativa_pct=humedad,
                    viento_ms=viento,
                    radiacion_mj_m2=radiacion,
                    imputado=bool(imputado),
                    metodo_imputacion=(
                        MetodoImputacion(metodo) if metodo else MetodoImputacion.SIN_IMPUTAR
                    ),
                )
            )
        return salida

    # -- Focos de calor ----------------------------------------------------- #

    def guardar_focos(self, focos: list[FocoCalor]) -> int:
        """
        Asigna cada foco a su distrito por interseccion espacial al guardar.

        Lo pide el contrato con esas palabras. Se resuelve con `ST_Contains` dentro
        del INSERT: PostGIS ya tiene los poligonos y traerlos a Python para repetir
        el calculo seria mover megabytes para llegar al mismo sitio.

        El esquema `FocoCalor` del contrato no trae producto ni banda, asi que se
        guardan con los valores que la tabla exige y que se pueden deducir: el
        satelite distingue el sensor —Terra y Aqua son MODIS, N es VIIRS— y de ahi
        sale la banda. Ver la evidencia de H1.2.
        """
        if not focos:
            return 0

        parametros = []
        for f in focos:
            es_viirs = (f.satelite or "").strip().upper().startswith("N")
            parametros.append(
                {
                    "producto": "viirs-snpp" if es_viirs else "modis",
                    "satelite": f.satelite or "desconocido",
                    "fecha": f.fecha,
                    # El contrato no trae la hora. Se guarda 0 y queda declarado:
                    # inventar una hora plausible seria peor que declarar que no
                    # se sabe.
                    "hora_utc": 0,
                    "latitud": f.latitud,
                    "longitud": f.longitud,
                    "codigo_canton": self._codigo_canton,
                    "confianza": _categoria_desde_entero(f.confianza),
                    "confianza_bruta": None if es_viirs else f.confianza,
                    "brillo_k": f.brillo_k,
                    "banda_origen": "viirs_i4" if es_viirs else "modis_21_22",
                }
            )

        with self._conexion.transaction(), self._conexion.cursor() as cursor:
            cursor.executemany(SQL_GUARDAR_FOCO, parametros)
        return len(parametros)

    def contar_focos(self, codigo_distrito: str, desde: date, hasta: date) -> int:
        """
        Conteo en la ventana. Es la base del etiquetado de incendio.

        Aditivo por construccion, porque cuenta filas: dos ventanas contiguas suman
        la ventana completa. El simulado tuvo que arreglarse para comportarse asi
        en SC-04; aqui sale gratis.
        """
        with self._conexion.cursor() as cursor:
            cursor.execute(SQL_CONTAR_FOCOS, (codigo_distrito, desde, hasta))
            (cuenta,) = cursor.fetchone()
        return int(cuenta)

    # -- Lo que depende de tablas que no existen ---------------------------- #
    #
    # Fallan nombrando la historia que las va a traer. Ver la cabecera del modulo.

    def guardar_indices(self, indices: list[IndiceDerivado]) -> int:
        raise _pendiente("guardar_indices")

    def obtener_indices(
        self, codigo_distrito: str, desde: date, hasta: date
    ) -> list[IndiceDerivado]:
        raise _pendiente("obtener_indices")

    def guardar_riesgos(self, riesgos: list[Riesgo]) -> int:
        raise _pendiente("guardar_riesgos")

    def obtener_riesgo(
        self, codigo_distrito: str, fecha: date, tipo_evento: TipoEvento
    ) -> Riesgo | None:
        raise _pendiente("obtener_riesgo")

    def obtener_riesgos_por_fecha(self, fecha: date, tipo_evento: TipoEvento) -> list[Riesgo]:
        raise _pendiente("obtener_riesgos_por_fecha")

    def listar_eventos(self, tipo_evento: TipoEvento | None = None) -> list[EventoHistorico]:
        raise _pendiente("listar_eventos")

    def guardar_reporte_calidad(self, reporte: ReporteCalidad) -> None:
        raise _pendiente("guardar_reporte_calidad")

    def listar_reportes_calidad(self) -> list[ReporteCalidad]:
        raise _pendiente("listar_reportes_calidad")

    def guardar_metricas(self, metricas: MetricasModelo) -> None:
        raise _pendiente("guardar_metricas")

    def listar_metricas(self) -> list[MetricasModelo]:
        raise _pendiente("listar_metricas")


def _categoria_desde_entero(confianza: int | None) -> str:
    """
    Traduce la confianza entera del contrato a la categoria que la tabla exige.

    Cortes de la Tabla 10 de Giglio, Schroeder, Hall y Justice, MODIS Collection 6
    Active Fire Product User's Guide, Revision C, diciembre de 2020. Los mismos que
    usa `backend/etl/fuentes/firms.py`.

    Un foco sin confianza queda en 'nominal', que es la categoria mayoritaria, y se
    declara aqui: la columna no admite nulo y el contrato si. Es la unica suposicion
    de este modulo.
    """
    if confianza is None:
        return "nominal"
    if confianza < 30:
        return "baja"
    if confianza < 80:
        return "nominal"
    return "alta"


def rango_de_dias(desde: date, hasta: date) -> list[date]:
    """Utilidad para las pruebas: los dias que `obtener_mediciones` debe devolver."""
    return [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]
