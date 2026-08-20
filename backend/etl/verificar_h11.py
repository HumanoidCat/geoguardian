"""
Verificador de las series climaticas. Dueno: Cesar. Historia H1.1, issue #35.

Cubre CA-1 a CA-13 del documento de criterios. Cada uno se comprueba ejecutando,
no leyendo: los que hablan de la tabla consultan la tabla, y los que hablan del
protocolo instancian el extractor.

QUE NO CUBRE Y POR QUE

  - **CA-7 (unidades)** no se comprueba aqui sino en el momento de la descarga.
    Es lo correcto: la unidad la declara cada respuesta, asi que verificarla
    despues, sobre la tabla, no probaria nada. `power.py` aborta la carga si no
    coincide, y `--comprobar-unidades` fuerza esa ruta contra el servicio.
  - **CA-10 (migracion dos veces)** y **CA-14 (maquina limpia)** se verifican por
    fuera, corriendo el aplicador dos veces y levantando sobre volumen vacio.
  - **CA-12 (carga interrumpida)** necesita interrumpir una carga a proposito;
    va documentado en la evidencia con el mismo mecanismo determinista de H1.3.

USO

    python -m backend.etl.verificar_h11
    python -m backend.etl.verificar_h11 --comprobar-unidades   # consulta POWER
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import date

from basedatos.conexion import ErrorConexion, conectar
from contratos.esquemas import MedicionDiaria
from contratos.fuentes import ExtractorClima

from . import bitacora
from .cargar_mediciones import DESDE, HASTA
from .fuentes.hibrido import ExtractorHibrido, Territorio, celda_power
from .fuentes.power import UNIDADES, ExtractorPower

CODIGO_CANTON = 508
DIAS_ESPERADOS = (HASTA - DESDE).days + 1
DISTRITOS_ESPERADOS = 8
FILAS_ESPERADAS = DIAS_ESPERADOS * DISTRITOS_ESPERADOS


@dataclass
class Resultado:
    criterio: str
    titulo: str
    cumple: bool
    detalle: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Dobles de prueba                                                              #
# --------------------------------------------------------------------------- #


class _FuenteCaida:
    """Fuente que nunca responde. Para CA-3, sin tocar la red."""

    nombre = "caida"

    def disponible(self) -> bool:
        return False

    def cerrar(self) -> None:
        pass


class _PowerFalso:
    """POWER de prueba con un hueco declarado, para CA-6."""

    nombre = "power falso"

    def __init__(self) -> None:
        self.llamadas = 0

    def disponible(self) -> bool:
        return True

    def cerrar(self) -> None:
        pass

    def consultar(self, longitud, latitud, desde, hasta):
        from .fuentes.power import RespuestaPower

        self.llamadas += 1
        dias = [date.fromordinal(o) for o in range(desde.toordinal(), hasta.toordinal() + 1)]
        # El primer dia va sin dato: es lo que POWER habria mandado como -999.0 y
        # el extractor tiene que haber traducido a None antes de llegar aqui.
        series = {
            parametro: {d: (None if i == 0 else 20.0) for i, d in enumerate(dias)}
            for parametro in UNIDADES
        }
        return RespuestaPower(
            url="prueba", valor_relleno=-999.0, elevacion=550.0, version_api="prueba", series=series
        )


class _ChirpsFalso:
    """CHIRPS de prueba. Devuelve un dia menos que el rango, a proposito."""

    nombre = "chirps falso"

    def disponible(self) -> bool:
        return True

    def cerrar(self) -> None:
        pass

    def consultar(self, geometria, desde, hasta):
        dias = [date.fromordinal(o) for o in range(desde.toordinal(), hasta.toordinal() + 1)]
        # Se omite el ultimo dia: el extractor debe emitirlo igual, con nulo.
        return {d: 3.0 for d in dias[:-1]}


def _territorio_de_prueba() -> Territorio:
    return Territorio(
        codigo="50801",
        nombre="Prueba",
        geometria={
            "type": "Polygon",
            "coordinates": [[[-85.0, 10.4], [-84.9, 10.4], [-84.9, 10.5], [-85.0, 10.4]]],
        },
        longitud=-84.97,
        latitud=10.47,
    )


# --------------------------------------------------------------------------- #
# CA-1, CA-3, CA-4, CA-6 · el extractor, sin base y sin red                     #
# --------------------------------------------------------------------------- #


def ca1_protocolo() -> Resultado:
    extractor = ExtractorHibrido(
        [_territorio_de_prueba()], power=_PowerFalso(), chirps=_ChirpsFalso()
    )
    cumple_isinstance = isinstance(extractor, ExtractorClima)

    # `runtime_checkable` solo comprueba que los metodos existan, no su firma.
    import inspect

    firma = inspect.signature(extractor.extraer)
    esperados = ["codigo_distrito", "desde", "hasta"]
    firma_ok = list(firma.parameters) == esperados

    return Resultado(
        "CA-1",
        "La implementacion cumple el protocolo ExtractorClima",
        cumple_isinstance and firma_ok,
        [
            f"  isinstance(extractor, ExtractorClima): {cumple_isinstance}",
            f"  parametros de extraer: {list(firma.parameters)} (esperado {esperados})",
            f"  nombre: {extractor.nombre}",
        ],
    )


def ca3_disponible() -> Resultado:
    """Con una fuente caida tiene que devolver falso, no lanzar excepcion."""
    detalle = []
    ok = True

    para_probar = [
        ("las dos caidas", _FuenteCaida(), _FuenteCaida(), False),
        ("solo POWER caido", _FuenteCaida(), _ChirpsFalso(), False),
        ("solo CHIRPS caido", _PowerFalso(), _FuenteCaida(), False),
        ("las dos responden", _PowerFalso(), _ChirpsFalso(), True),
    ]

    for titulo, power, chirps, esperado in para_probar:
        extractor = ExtractorHibrido(
            [_territorio_de_prueba()], power=power, chirps=chirps, registrar=lambda _: None
        )
        try:
            obtenido = extractor.disponible()
        except Exception as error:  # noqa: BLE001 - el criterio es que NO lance
            detalle.append(f"  {titulo}: lanzo {type(error).__name__}, deberia devolver falso")
            ok = False
            continue
        marca = "ok" if obtenido == esperado else "MAL"
        detalle.append(f"  {titulo}: devuelve {obtenido}, esperado {esperado} ... {marca}")
        ok = ok and obtenido == esperado

    return Resultado("CA-3", "disponible() comprueba las dos fuentes y no lanza", ok, detalle)


def ca4_ca6_sin_huecos_de_calendario() -> Resultado:
    """
    Un dia que la fuente omite tiene que salir igual, con nulo.

    Es el criterio que el contrato subraya: omitir un dia sin dato lo hace
    indistinguible de un dia que no existe.
    """
    desde, hasta = date(2024, 1, 1), date(2024, 1, 10)
    extractor = ExtractorHibrido(
        [_territorio_de_prueba()],
        power=_PowerFalso(),
        chirps=_ChirpsFalso(),
        registrar=lambda _: None,
    )
    mediciones = extractor.extraer("50801", desde, hasta)

    esperadas = (hasta - desde).days + 1
    fechas = [m.fecha for m in mediciones]
    consecutivas = fechas == [
        date.fromordinal(o) for o in range(desde.toordinal(), hasta.toordinal() + 1)
    ]

    # El primer dia lo omitio POWER; el ultimo lo omitio CHIRPS. Los dos tienen
    # que estar presentes y en nulo, y ninguno en cero.
    primero = mediciones[0]
    ultimo = mediciones[-1]
    hueco_power = primero.temp_media_c is None
    hueco_chirps = ultimo.precipitacion_mm is None
    nada_en_cero = primero.temp_media_c != 0 and ultimo.precipitacion_mm != 0
    tipo_ok = all(isinstance(m, MedicionDiaria) for m in mediciones)

    ok = (
        len(mediciones) == esperadas
        and consecutivas
        and hueco_power
        and hueco_chirps
        and nada_en_cero
        and tipo_ok
    )

    return Resultado(
        "CA-4/CA-6",
        "Una fila por dia; los dias sin dato salen en nulo, nunca en cero",
        ok,
        [
            f"  filas: {len(mediciones)} (esperado {esperadas})",
            f"  fechas consecutivas y sin repetir: {consecutivas}",
            f"  dia omitido por POWER  ({primero.fecha}): temp_media_c = {primero.temp_media_c!r}",
            f"  dia omitido por CHIRPS ({ultimo.fecha}): precipitacion_mm = {ultimo.precipitacion_mm!r}",
            f"  todas son MedicionDiaria del contrato: {tipo_ok}",
        ],
    )


def ca_celda_power() -> Resultado:
    """
    La malla de MERRA-2 ancla centros, no bordes.

    Va aparte porque el error de usar `floor` ya se cometio una vez y produjo un
    numero de celdas plausible pero falso.
    """
    import math

    casos = [
        # (lon, lat, celda esperada). Los dos primeros estan elegidos porque
        # `floor` y `round` dan resultados DISTINTOS: si alguien vuelve a truncar,
        # estos casos lo delatan. El tercero es el origen, que coincide.
        (-84.6, 10.8, (-84.375, 11.0)),
        (-84.97, 10.3, (-85.0, 10.5)),
        (0.0, 0.0, (0.0, 0.0)),
    ]
    detalle = []
    ok = True
    for lon, lat, esperado in casos:
        obtenido = celda_power(lon, lat)
        truncado = (
            math.floor(lon / 0.625) * 0.625,
            math.floor(lat / 0.5) * 0.5,
        )
        coincide = all(abs(a - b) < 1e-9 for a, b in zip(obtenido, esperado, strict=True))
        detalle.append(
            f"  ({lon}, {lat}) -> {obtenido}, esperado {esperado} "
            f"... {'ok' if coincide else 'MAL'}   [truncando daria {truncado}]"
        )
        ok = ok and coincide
    return Resultado("CA-extra", "celda_power redondea al centro, no trunca al borde", ok, detalle)


# --------------------------------------------------------------------------- #
# CA-2 · territorio                                                             #
# --------------------------------------------------------------------------- #


def ca2_puntos_dentro(cursor) -> Resultado:
    cursor.execute(
        """
        SELECT codigo, nombre, ST_Contains(geometria, ST_PointOnSurface(geometria))
          FROM geo.distrito
         WHERE codigo_canton = %s
         ORDER BY codigo
        """,
        (CODIGO_CANTON,),
    )
    filas = cursor.fetchall()
    dentro = [f for f in filas if f[2]]
    ok = len(filas) == DISTRITOS_ESPERADOS and len(dentro) == DISTRITOS_ESPERADOS
    return Resultado(
        "CA-2",
        "Cada distrito tiene geometria y su punto cae dentro",
        ok,
        [f"  {c} {n}: punto dentro = {d}" for c, n, d in filas] or ["  no hay distritos cargados"],
    )


# --------------------------------------------------------------------------- #
# CA-4, CA-5, CA-8, CA-9 · la tabla                                             #
# --------------------------------------------------------------------------- #


def ca4_filas(cursor) -> Resultado:
    cursor.execute(
        """
        SELECT codigo_distrito,
               count(*),
               min(fecha),
               max(fecha),
               (max(fecha) - min(fecha)) + 1 AS dias_de_calendario
          FROM crudo.medicion_diaria
         GROUP BY codigo_distrito
         ORDER BY codigo_distrito
        """
    )
    filas = cursor.fetchall()
    detalle = []
    ok = len(filas) == DISTRITOS_ESPERADOS
    if not filas:
        detalle.append("  la tabla esta vacia: corre primero cargar_mediciones")
        ok = False

    for codigo, cuenta, minima, maxima, calendario in filas:
        completo = cuenta == calendario
        detalle.append(
            f"  {codigo}: {cuenta} filas, {minima} a {maxima}, "
            f"calendario {calendario} ... {'ok' if completo else 'FALTAN DIAS'}"
        )
        ok = ok and completo

    total = sum(f[1] for f in filas)
    detalle.append(f"  total: {total} filas")
    return Resultado("CA-4", "Una fila por dia del rango, sin huecos de calendario", ok, detalle)


def ca5_ventana(cursor) -> Resultado:
    cursor.execute("SELECT min(fecha), max(fecha) FROM crudo.medicion_diaria")
    minima, maxima = cursor.fetchone()
    ok = minima == DESDE and maxima == HASTA
    return Resultado(
        "CA-5",
        "La ventana es la declarada y no se movio",
        ok,
        [
            f"  minima: {minima} (esperado {DESDE})",
            f"  maxima: {maxima} (esperado {HASTA})",
        ],
    )


def ca6_relleno(cursor) -> Resultado:
    """
    Ningun valor de relleno entro como numero.

    El complemento importa igual: si NINGUNA columna tiene nulos en 35 anios, es
    mas sospechoso que una serie con huecos. Se reporta el conteo.
    """
    columnas = [
        "temp_max_c",
        "temp_min_c",
        "temp_media_c",
        "humedad_relativa_pct",
        "viento_ms",
        "radiacion_mj_m2",
        "precipitacion_mm",
    ]
    condicion = " OR ".join(f"{c} <= -900" for c in columnas)
    cursor.execute(f"SELECT count(*) FROM crudo.medicion_diaria WHERE {condicion}")
    (rellenos,) = cursor.fetchone()

    conteos = ", ".join(f"count(*) FILTER (WHERE {c} IS NULL)" for c in columnas)
    cursor.execute(f"SELECT {conteos}, count(*) FROM crudo.medicion_diaria")
    fila = cursor.fetchone()
    nulos = dict(zip(columnas, fila[:-1], strict=True))
    total = fila[-1]

    ok = rellenos == 0
    detalle = [f"  filas con valores <= -900: {rellenos} (esperado 0)", f"  filas totales: {total}"]
    detalle += [f"  nulos en {c}: {n}" for c, n in nulos.items()]
    if total and not any(nulos.values()):
        detalle.append(
            "  AVISO: ninguna columna tiene nulos en toda la serie. Revisar que "
            "el valor de relleno se este traduciendo y no reemplazando."
        )
    return Resultado("CA-6", "Ningun valor de relleno entro como numero", ok, detalle)


def ca8_rangos(cursor) -> Resultado:
    """
    Los rangos ya los impone el DDL, asi que aqui tienen que dar cero.

    Se comprueba igual: un CHECK que nadie verifica es una promesa, no una
    garantia, y si alguien lo quita en una migracion futura esto lo detecta.
    """
    pruebas = {
        "temp_min > temp_max": "temp_min_c > temp_max_c",
        "precipitacion negativa": "precipitacion_mm < 0",
        "humedad fuera de 0-100": "humedad_relativa_pct < 0 OR humedad_relativa_pct > 100",
        "viento negativo": "viento_ms < 0",
        "radiacion negativa": "radiacion_mj_m2 < 0",
        "fecha fuera de ventana": f"fecha < DATE '{DESDE}' OR fecha > DATE '{HASTA}'",
    }
    detalle = []
    ok = True
    for titulo, condicion in pruebas.items():
        cursor.execute(f"SELECT count(*) FROM crudo.medicion_diaria WHERE {condicion}")
        (cuenta,) = cursor.fetchone()
        detalle.append(f"  {titulo}: {cuenta} filas ... {'ok' if cuenta == 0 else 'MAL'}")
        ok = ok and cuenta == 0
    return Resultado("CA-8", "Los rangos son fisicamente posibles", ok, detalle)


def ca9_fuentes(cursor) -> Resultado:
    cursor.execute(
        """
        SELECT fuente_precipitacion, fuente_resto, count(*)
          FROM crudo.medicion_diaria
         GROUP BY 1, 2
         ORDER BY 3 DESC
        """
    )
    filas = cursor.fetchall()
    esperado = {("chirps", "power")}
    vistas = {(p, r) for p, r, _ in filas}
    ok = bool(filas) and vistas == esperado
    return Resultado(
        "CA-9",
        "Cada fila declara de que fuente vino su precipitacion",
        ok,
        [f"  precipitacion={p}, resto={r}: {c} filas" for p, r, c in filas]
        or ["  la tabla esta vacia"],
    )


def ca_d15_distritos_difieren(cursor) -> Resultado:
    """
    La comprobacion que sostiene la decision D-15, ahora con los datos cargados.

    Son dos afirmaciones opuestas y las dos tienen que ser ciertas:

      1. **CHIRPS distingue distritos.** Si diera el mismo valor en los ocho, la
         historia entera no serviria: no se puede estimar riesgo por distrito con
         una serie que es la misma en todos. Es la razon de traer una segunda
         fuente en vez de usar solo POWER.
      2. **POWER no los distingue.** Es la limitacion declarada. Si resultara que
         si los distingue, la caja por celda estaria devolviendo datos de un
         distrito a otro y habria que quitarla.

    Antes de cargar esto se comprobo sobre una semana. Ahora son 35 anios.
    """
    detalle = []

    cursor.execute(
        """
        SELECT count(*) FILTER (WHERE distintos > 1), count(*)
          FROM (
            SELECT fecha, count(DISTINCT precipitacion_mm) AS distintos
              FROM crudo.medicion_diaria
             GROUP BY fecha
          ) AS por_dia
        """
    )
    dias_que_difieren, dias_totales = cursor.fetchone()
    proporcion = dias_que_difieren / dias_totales if dias_totales else 0.0
    detalle.append(
        f"  CHIRPS: {dias_que_difieren} de {dias_totales} dias con al menos dos "
        f"valores distintos entre distritos ({proporcion:.1%})"
    )

    cursor.execute(
        """
        SELECT codigo_distrito, round(sum(precipitacion_mm)::numeric, 1)
          FROM crudo.medicion_diaria
         GROUP BY codigo_distrito
         ORDER BY 2 DESC
        """
    )
    acumulados = cursor.fetchall()
    for codigo, total in acumulados:
        detalle.append(f"    {codigo}: {total} mm acumulados en la ventana")

    if len(acumulados) > 1:
        mayor, menor = float(acumulados[0][1]), float(acumulados[-1][1])
        separacion = (mayor - menor) / menor if menor else 0.0
        detalle.append(f"  separacion entre el mayor y el menor: {separacion:.1%}")

    # POWER: sus seis variables tienen que ser identicas en los ocho distritos.
    cursor.execute(
        """
        SELECT count(*)
          FROM (
            SELECT fecha
              FROM crudo.medicion_diaria
             GROUP BY fecha
            HAVING count(DISTINCT temp_media_c) > 1
                OR count(DISTINCT humedad_relativa_pct) > 1
                OR count(DISTINCT viento_ms) > 1
                OR count(DISTINCT radiacion_mj_m2) > 1
          ) AS por_dia
        """
    )
    (dias_power_distintos,) = cursor.fetchone()
    detalle.append(
        f"  POWER: {dias_power_distintos} dias con valores distintos entre "
        "distritos (esperado 0, es la limitacion declarada)"
    )

    chirps_distingue = dias_que_difieren > 0
    power_no_distingue = dias_power_distintos == 0

    if not chirps_distingue:
        detalle.append(
            "  CHIRPS da el mismo valor en los ocho distritos. Eso invalida la "
            "razon de ser de D-15 y hay que revisar la consulta antes de seguir."
        )
    if not power_no_distingue:
        detalle.append(
            "  POWER distingue distritos, contra lo declarado. Revisar la caja "
            "por celda: puede estar mezclando series."
        )

    return Resultado(
        "CA-D15",
        "CHIRPS distingue distritos y POWER no, como declara la decision",
        chirps_distingue and power_no_distingue,
        detalle,
    )


def ca11_idempotencia(cursor) -> Resultado:
    """
    Comprueba que la clave natural es la que dice el contrato.

    La idempotencia completa se verifica corriendo la carga dos veces y
    comparando conteo y suma; eso va en la evidencia. Aqui se comprueba lo que
    la hace posible: que exista la restriccion sobre la que actua ON CONFLICT.
    """
    cursor.execute(
        """
        SELECT a.attname
          FROM pg_constraint c
          JOIN pg_class t ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
          JOIN unnest(c.conkey) WITH ORDINALITY AS k(attnum, orden) ON true
          JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = k.attnum
         WHERE n.nspname = 'crudo' AND t.relname = 'medicion_diaria' AND c.contype = 'p'
         ORDER BY k.orden
        """
    )
    clave = [f[0] for f in cursor.fetchall()]
    ok = clave == ["codigo_distrito", "fecha"]
    return Resultado(
        "CA-11",
        "La clave natural sostiene la idempotencia",
        ok,
        [f"  clave primaria: {clave} (esperado ['codigo_distrito', 'fecha'])"],
    )


def ca13_procedencia() -> Resultado:
    from .cargar_mediciones import RUTA_PROCEDENCIA

    existe = RUTA_PROCEDENCIA.exists()
    detalle = [f"  {RUTA_PROCEDENCIA}: {'existe' if existe else 'no existe'}"]
    if existe:
        texto = RUTA_PROCEDENCIA.read_text(encoding="utf-8")
        for exigido in ("Fuente:", "Ventana:", "Momento:", "Total de filas"):
            presente = exigido in texto
            detalle.append(f"  contiene {exigido!r}: {presente}")
            existe = existe and presente
    else:
        detalle.append("  se genera al correr cargar_mediciones")
    return Resultado("CA-13", "Queda registrado de donde salio cada serie", existe, detalle)


# --------------------------------------------------------------------------- #
# CA-7 · unidades, contra el servicio                                           #
# --------------------------------------------------------------------------- #


def ca7_unidades() -> Resultado:
    """
    Pide un dia a POWER y compara las unidades declaradas.

    Toca la red, asi que va tras una bandera: el resto del verificador tiene que
    poder correr sin internet.
    """
    extractor = ExtractorPower()
    try:
        respuesta = extractor.consultar(-84.97, 10.47, date(2024, 1, 1), date(2024, 1, 1))
    except Exception as error:  # noqa: BLE001 - cualquier fallo es un no cumple
        return Resultado("CA-7", "Las unidades coinciden con el contrato", False, [f"  {error}"])
    finally:
        extractor.cerrar()

    return Resultado(
        "CA-7",
        "Las unidades coinciden con el contrato",
        True,
        [f"  {p}: {u} (declarada por la fuente y aceptada)" for p, u in UNIDADES.items()]
        + [f"  api {respuesta.version_api}, relleno {respuesta.valor_relleno}"],
    )


# --------------------------------------------------------------------------- #


def main(argumentos: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description="Verifica los criterios de H1.1")
    analizador.add_argument(
        "--comprobar-unidades",
        action="store_true",
        help="CA-7: consulta POWER para comparar las unidades declaradas",
    )
    analizador.add_argument(
        "--registro",
        help="Archivo donde guardar la salida completa, para la evidencia del PR",
    )
    opciones = analizador.parse_args(argumentos)

    with bitacora.abrir(opciones.registro) as registrar:
        return _verificar(opciones, registrar)


def _verificar(opciones, registrar) -> int:
    registrar("Verificacion de las series climaticas de H1.1 (issue #35)")
    registrar("=" * 74)
    registrar(f"Ventana declarada: {DESDE} a {HASTA} = {DIAS_ESPERADOS} dias")
    registrar(f"Filas esperadas con los ocho distritos: {FILAS_ESPERADAS}")

    # Primero lo que no necesita ni base ni red.
    resultados = [
        ca1_protocolo(),
        ca3_disponible(),
        ca4_ca6_sin_huecos_de_calendario(),
        ca_celda_power(),
    ]

    try:
        with conectar(autocommit=True) as conexion, conexion.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM crudo.medicion_diaria")
            (cargadas,) = cursor.fetchone()
            registrar(f"Filas en la tabla: {cargadas}")

            resultados.append(ca2_puntos_dentro(cursor))
            resultados.append(ca11_idempotencia(cursor))
            if cargadas:
                resultados.append(ca4_filas(cursor))
                resultados.append(ca5_ventana(cursor))
                resultados.append(ca6_relleno(cursor))
                resultados.append(ca8_rangos(cursor))
                resultados.append(ca9_fuentes(cursor))
                resultados.append(ca_d15_distritos_difieren(cursor))
            else:
                registrar(
                    "\nAVISO: crudo.medicion_diaria esta vacia. CA-4, CA-5, CA-6, "
                    "CA-8 y CA-9 no se pueden comprobar sin datos cargados."
                )
    except ErrorConexion as error:
        registrar(f"ERROR: {error}")
        return 1

    resultados.append(ca13_procedencia())

    if opciones.comprobar_unidades:
        resultados.append(ca7_unidades())

    for r in resultados:
        registrar(f"\n{r.criterio} · {r.titulo} ... {'CUMPLE' if r.cumple else 'NO CUMPLE'}")
        for linea in r.detalle:
            registrar(linea)

    fallidos = [r for r in resultados if not r.cumple]
    registrar("\n" + "=" * 74)
    if fallidos:
        registrar("NO CUMPLEN: " + ", ".join(r.criterio for r in fallidos))
        return 1
    registrar("Los criterios verificados aqui se cumplen.")
    registrar("Faltan CA-10, CA-12 y CA-14, que se verifican por fuera:")
    registrar("  CA-10  aplicar las migraciones dos veces")
    registrar("  CA-12  interrumpir una carga a proposito y comparar conteo")
    registrar("  CA-14  levantar desde docker compose up sobre volumen vacio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
