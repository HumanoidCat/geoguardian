"""
Verificador de los criterios de aceptacion de H1.3. Dueno: Cesar. Issue #37.

Consulta la base y emite un veredicto por criterio, con el valor medido al lado
del umbral. Sale con codigo 1 si alguno no se cumple, para poder encadenarlo.

Cubre CA-2 a CA-8. Los otros criterios se verifican por fuera:

    CA-1   revision del modelo, consulta a information_schema
    CA-9   correr el aplicador de migraciones dos veces
    CA-10  correr el cargador dos veces
    CA-11  basedatos/consultas/verificar_transaccion.sql
    CA-12  archivo basedatos/ddl/procedencia-geometrias.md
    CA-13  secuencia completa desde docker compose up sobre volumen vacio

USO

    python -m basedatos.verificar_h13
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from decimal import Decimal

import psycopg

from basedatos.conexion import ErrorConexion, conectar

CODIGO_CANTON = 508
SRID_ALMACENAMIENTO = 4326
SRID_METRICO = 8908

# Umbrales de CA-7, fijados en el documento de criterios ANTES de ver ningun
# resultado. No se ajustan para que la medicion entre.
TOLERANCIA_INTERNA_PCT = Decimal("0.1")
TOLERANCIA_CANTONAL_PCT = Decimal("2.0")

CODIGOS_ESPERADOS = [str(CODIGO_CANTON * 100 + n) for n in range(1, 9)]

# Nombres con tilde. Si la codificacion se rompe en algun punto del trayecto,
# 'Libano' llega como 'LÃ­bano' y esta comprobacion lo detecta.
NOMBRES_CON_TILDE = ["Tilarán", "Líbano"]


@dataclass
class Resultado:
    criterio: str
    titulo: str
    cumple: bool
    detalle: list[str] = field(default_factory=list)


def _fila(cursor: psycopg.Cursor, sql: str, parametros: dict | None = None):
    cursor.execute(sql, parametros or {})
    return cursor.fetchone()


def ca2_srid(cursor: psycopg.Cursor) -> Resultado:
    """El SRID declarado y el efectivo son 4326."""
    cursor.execute("SELECT DISTINCT ST_SRID(geometria) FROM geo.distrito")
    srids = sorted(f[0] for f in cursor.fetchall())

    tipo = _fila(
        cursor,
        """
        SELECT type, srid, coord_dimension
          FROM geometry_columns
         WHERE f_table_schema = 'geo' AND f_table_name = 'distrito'
        """,
    )

    cumple = srids == [SRID_ALMACENAMIENTO] and tipo is not None and tipo[1] == SRID_ALMACENAMIENTO
    return Resultado(
        "CA-2",
        "Tipo y SRID de la geometria",
        cumple,
        [
            f"SRID presentes en las filas: {srids} (esperado [{SRID_ALMACENAMIENTO}])",
            f"columna declarada: {tipo[0]} SRID {tipo[1]}" if tipo else "columna no declarada",
        ],
    )


def ca3_contrato(cursor: psycopg.Cursor) -> Resultado:
    """Una fila se convierte en contratos.esquemas.Distrito sin que Pydantic falle."""
    detalle: list[str] = []
    try:
        import json

        from contratos.esquemas import Distrito
    except ImportError as error:
        return Resultado("CA-3", "Conversion al contrato", False, [f"no se pudo importar: {error}"])

    fila = _fila(
        cursor,
        """
        SELECT codigo, nombre, area_km2, poblacion, ST_AsGeoJSON(geometria)
          FROM geo.distrito
         ORDER BY codigo
         LIMIT 1
        """,
    )
    if fila is None:
        return Resultado("CA-3", "Conversion al contrato", False, ["la tabla esta vacia"])

    try:
        distrito = Distrito(
            codigo=fila[0],
            nombre=fila[1],
            area_km2=float(fila[2]),
            poblacion=fila[3],
            geometria=json.loads(fila[4]),
        )
    except Exception as error:  # noqa: BLE001 - se reporta cualquier fallo de validacion
        return Resultado("CA-3", "Conversion al contrato", False, [str(error)])

    detalle.append(f"construido Distrito(codigo={distrito.codigo!r}, nombre={distrito.nombre!r})")
    detalle.append(f"geometria: {distrito.geometria.get('type')} en EPSG:{SRID_ALMACENAMIENTO}")
    return Resultado("CA-3", "Conversion al contrato", True, detalle)


def ca4_validez(cursor: psycopg.Cursor) -> Resultado:
    """Ninguna geometria invalida."""
    invalidas = _fila(cursor, "SELECT count(*) FROM geo.distrito WHERE NOT ST_IsValid(geometria)")[
        0
    ]
    return Resultado(
        "CA-4",
        "Validez geometrica",
        invalidas == 0,
        [f"geometrias invalidas: {invalidas} (esperado 0)"],
    )


def ca5_cobertura(cursor: psycopg.Cursor) -> Resultado:
    """Estan los ocho distritos del canton 508 y ninguno mas."""
    total = _fila(cursor, "SELECT count(*) FROM geo.distrito")[0]

    ajenos = _fila(
        cursor,
        "SELECT count(*) FROM geo.distrito WHERE codigo NOT LIKE %(prefijo)s",
        {"prefijo": f"{CODIGO_CANTON}%"},
    )[0]

    cursor.execute("SELECT codigo FROM geo.distrito ORDER BY codigo")
    codigos = [f[0] for f in cursor.fetchall()]

    nombre_canton = _fila(
        cursor,
        """
        SELECT DISTINCT c.nombre
          FROM geo.distrito d
          JOIN geo.canton c ON c.codigo = d.codigo_canton
        """,
    )

    cumple = total == 8 and ajenos == 0 and codigos == CODIGOS_ESPERADOS
    return Resultado(
        "CA-5",
        "Cobertura exacta del canton",
        cumple,
        [
            f"filas: {total} (esperado 8)",
            f"codigos fuera del canton {CODIGO_CANTON}: {ajenos} (esperado 0)",
            f"codigos: {', '.join(codigos)}",
            f"canton: {nombre_canton[0] if nombre_canton else 'ninguno'}",
        ],
    )


def ca6_nombre(cursor: psycopg.Cursor) -> Resultado:
    """El nombre esta presente, sin espacios sobrantes, unico y con las tildes intactas."""
    vacios = _fila(
        cursor,
        "SELECT count(*) FROM geo.distrito WHERE nombre IS NULL OR btrim(nombre) = ''",
    )[0]

    con_espacios = _fila(cursor, "SELECT count(*) FROM geo.distrito WHERE nombre <> btrim(nombre)")[
        0
    ]

    repetidos = _fila(
        cursor,
        """
        SELECT count(*) FROM (
            SELECT nombre FROM geo.distrito GROUP BY nombre HAVING count(*) > 1
        ) AS repetidos
        """,
    )[0]

    con_tilde = _fila(
        cursor,
        "SELECT count(*) FROM geo.distrito WHERE nombre = ANY(%(nombres)s)",
        {"nombres": NOMBRES_CON_TILDE},
    )[0]

    cumple = (
        vacios == 0 and con_espacios == 0 and repetidos == 0 and con_tilde == len(NOMBRES_CON_TILDE)
    )
    return Resultado(
        "CA-6",
        "Nombre presente e integro",
        cumple,
        [
            f"nombres vacios: {vacios} (esperado 0)",
            f"nombres con espacios en los extremos: {con_espacios} (esperado 0)",
            f"nombres repetidos: {repetidos} (esperado 0)",
            f"nombres con tilde intacta {NOMBRES_CON_TILDE}: {con_tilde} "
            f"(esperado {len(NOMBRES_CON_TILDE)})",
        ],
    )


def ca7_area(cursor: psycopg.Cursor) -> Resultado:
    """Consistencia interna del area y contraste contra el poligono cantonal."""
    detalle: list[str] = []

    cursor.execute(
        f"""
        SELECT codigo,
               nombre,
               area_km2,
               ST_Area(ST_Transform(geometria, {SRID_METRICO})) / 1000000.0 AS recalculada
          FROM geo.distrito
         ORDER BY codigo
        """
    )
    filas = cursor.fetchall()

    peor_desvio = Decimal("0")
    for codigo, nombre, guardada, recalculada in filas:
        guardada = Decimal(str(guardada))
        recalculada = Decimal(str(recalculada))
        desvio = abs(guardada - recalculada) / recalculada * 100
        peor_desvio = max(peor_desvio, desvio)
        detalle.append(
            f"  {codigo} {nombre:<18} guardada {guardada:>10.4f}  "
            f"recalculada {recalculada:>10.4f}  desvio {desvio:.6f} %"
        )

    interna_ok = peor_desvio <= TOLERANCIA_INTERNA_PCT

    suma_distritos = Decimal(str(_fila(cursor, "SELECT sum(area_km2) FROM geo.distrito")[0]))

    area_canton_fila = _fila(
        cursor,
        f"""
        SELECT ST_Area(ST_Transform(geometria, {SRID_METRICO})) / 1000000.0
          FROM geo.canton
         WHERE codigo = %(codigo)s AND geometria IS NOT NULL
        """,
        {"codigo": CODIGO_CANTON},
    )

    if area_canton_fila is None:
        detalle.append("  no hay geometria cantonal cargada: no se puede contrastar")
        return Resultado("CA-7", "Coherencia del area", False, detalle)

    area_canton = Decimal(str(area_canton_fila[0]))
    desvio_cantonal = abs(suma_distritos - area_canton) / area_canton * 100
    cantonal_ok = desvio_cantonal <= TOLERANCIA_CANTONAL_PCT

    detalle.append("")
    detalle.append(f"  suma de los ocho distritos : {suma_distritos:>10.4f} km2")
    detalle.append(f"  poligono cantonal oficial  : {area_canton:>10.4f} km2")
    detalle.append(
        f"  desvio {desvio_cantonal:.4f} % (umbral {TOLERANCIA_CANTONAL_PCT} %) -> "
        f"{'dentro' if cantonal_ok else 'FUERA'}"
    )
    detalle.append(
        f"  peor desvio interno {peor_desvio:.6f} % (umbral {TOLERANCIA_INTERNA_PCT} %) -> "
        f"{'dentro' if interna_ok else 'FUERA'}"
    )

    return Resultado("CA-7", "Coherencia del area", interna_ok and cantonal_ok, detalle)


def ca8_poblacion(cursor: psycopg.Cursor) -> Resultado:
    """Poblacion nula, nunca cero de relleno."""
    no_nulos = _fila(cursor, "SELECT count(*) FROM geo.distrito WHERE poblacion IS NOT NULL")[0]
    return Resultado(
        "CA-8",
        "Poblacion nula, no cero",
        no_nulos == 0,
        [f"filas con poblacion no nula: {no_nulos} (esperado 0)"],
    )


COMPROBACIONES = [
    ca2_srid,
    ca3_contrato,
    ca4_validez,
    ca5_cobertura,
    ca6_nombre,
    ca7_area,
    ca8_poblacion,
]


def main() -> int:
    print("Verificacion de criterios de aceptacion de H1.3 (issue #37)")
    print("=" * 70)

    resultados: list[Resultado] = []

    try:
        with conectar() as conexion, conexion.cursor() as cursor:
            for comprobacion in COMPROBACIONES:
                resultados.append(comprobacion(cursor))
    except ErrorConexion as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except psycopg.errors.UndefinedTable:
        print(
            "ERROR: las tablas del esquema geo no existen.\n"
            "Aplica las migraciones primero: python -m basedatos.aplicar_migraciones",
            file=sys.stderr,
        )
        return 1

    for resultado in resultados:
        marca = "CUMPLE" if resultado.cumple else "NO CUMPLE"
        print(f"\n{resultado.criterio} · {resultado.titulo} ... {marca}")
        for linea in resultado.detalle:
            print(f"    {linea}" if not linea.startswith("  ") else linea)

    fallidos = [r for r in resultados if not r.cumple]

    print("\n" + "=" * 70)
    if fallidos:
        print(f"NO CUMPLEN: {', '.join(r.criterio for r in fallidos)}")
        return 1

    print(f"Los {len(resultados)} criterios verificados aqui se cumplen.")
    print("Faltan CA-1, CA-9, CA-10, CA-11, CA-12 y CA-13, que se verifican por fuera.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
