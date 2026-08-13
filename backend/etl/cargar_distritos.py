"""
Carga de geometrias oficiales de distritos. Dueno: Cesar. Historia H1.3, issue #37.

QUE HACE

Descarga del SNIT los ocho distritos del canton de Tilaran y el poligono del
canton, y los carga en el esquema `geo`. Toda la carga ocurre dentro de una sola
transaccion: o entra todo, o no entra nada.

FUENTE

    Servicio:  https://geos.snitcr.go.cr/be/IGN_5_CO/wfs
    Capas:     IGN_5_CO:limitedistrital_5k   (494 entidades a nivel nacional)
               IGN_5_CO:limitecantonal_5k

El listado publicado por el SNIT dice 492 entidades. El servicio devuelve 494:
la division territorial cambio despues de publicarse ese listado. El conteo real
se consulta en cada carga y queda registrado en el archivo de procedencia.

El nodo IGN_5, que es el candidato natural al buscar "cartografia 1:5mil", NO
sirve capas administrativas: publica cultivos, curvas, edificaciones, forestal,
hidrografia, pastos, urbano y vias. Las capas de limites estan en IGN_5_CO.

TRES TRAMPAS DEL SERVICIO, TODAS COMPROBADAS CONTRA EL

1. Los nombres de atributo llevan tilde, y el filtro CQL falla con error de
   analisis si no van entre comillas dobles:

       CQL_FILTER=CÓDIGO_CANTÓN=508      -> Lexical error at line 1, column 5
       CQL_FILTER="CÓDIGO_CANTÓN"=508    -> correcto

2. Las dos capas nombran distinto el codigo de provincia:

       limitedistrital_5k -> CÓDIGO_PROVINCIA
       limitecantonal_5k  -> CÓDIGO_DE_PROVINCIA

3. El atributo `CÓDIGO` NO es el codigo del distrito: vale 160105 en las ocho
   filas y no identifica nada. El codigo oficial es `CÓDIGO_DTA`.

SOBRE EL ORDEN DE LAS COORDENADAS

Pidiendo `srsName=EPSG:4326` con salida GeoJSON, el servicio devuelve longitud
primero y latitud despues, que es lo que PostGIS espera para ese SRID. Verificado
contra el servicio: la primera coordenada de un distrito de Tilaran es
[-85.00072435, 10.45408599]. Si alguna vez viniera al reves, los poligonos
apareceran en Somalia y no en Guanacaste.

SOBRE LAS AREAS

El area no se toma de la fuente ni se calcula en Python: la calcula PostGIS al
insertar, reproyectando a EPSG:8908 (CR-SIRGAS / CRTM05), que es el sistema
nativo de la capa y esta en metros. Calcularla sobre EPSG:4326 daria un numero en
grados cuadrados, que no es una superficie.

Eso ademas evita traer GeoPandas y pyproj a este modulo: la base ya sabe
reproyectar.

USO

    python -m backend.etl.cargar_distritos
    python -m backend.etl.cargar_distritos --solo-descargar   # no toca la base
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from basedatos.conexion import ErrorConexion, conectar

# --------------------------------------------------------------------------- #
# Constantes de la fuente                                                       #
# --------------------------------------------------------------------------- #

WFS = "https://geos.snitcr.go.cr/be/IGN_5_CO/wfs"

CAPA_DISTRITAL = "IGN_5_CO:limitedistrital_5k"
CAPA_CANTONAL = "IGN_5_CO:limitecantonal_5k"

# Tilaran es el canton 08 de la provincia 5 (Guanacaste). El prefijo 505, que es
# el que usaban los simulados antes de la version 1.2.0 de los contratos,
# corresponde a Carrillo.
CODIGO_CANTON = 508
CODIGO_PROVINCIA = 5

# Los ocho codigos oficiales. Si la fuente devuelve un conjunto distinto, la
# carga se detiene: puede ser una reforma territorial real, y eso lo decide una
# persona, no este guion.
CODIGOS_ESPERADOS = frozenset(str(CODIGO_CANTON * 100 + n) for n in range(1, 9))

SRID_ALMACENAMIENTO = 4326  # el que exige el contrato Distrito.geometria
SRID_METRICO = 8908  # CR-SIRGAS / CRTM05, para medir superficies

TIEMPO_LIMITE = 120.0  # segundos; la capa distrital es pesada

RUTA_PROCEDENCIA = (
    Path(__file__).resolve().parents[2] / "basedatos" / "ddl" / "procedencia-geometrias.md"
)


class ErrorCarga(Exception):
    """Falla que impide continuar. Nunca deja la base a medias."""


@dataclass(frozen=True)
class Descarga:
    """Respuesta cruda de una peticion al WFS, con su rastro."""

    capa: str
    url: str
    bytes_crudos: bytes
    contenido: dict[str, Any]
    momento: datetime

    @property
    def suma_sha256(self) -> str:
        return hashlib.sha256(self.bytes_crudos).hexdigest()

    @property
    def entidades(self) -> int:
        return len(self.contenido.get("features", []))


# --------------------------------------------------------------------------- #
# Descarga                                                                      #
# --------------------------------------------------------------------------- #


def _filtro_canton() -> str:
    """
    Filtro CQL por canton, con el nombre del atributo entre comillas dobles.

    Sin las comillas el servicio responde 'Lexical error': no tolera la tilde en
    un identificador desnudo.
    """
    return f'"CÓDIGO_CANTÓN"={CODIGO_CANTON}'


def contar_total_nacional(cliente: httpx.Client) -> int:
    """
    Cuenta las entidades de la capa distrital sin filtrar.

    Se pide con `resultType=hits`, que devuelve solo el conteo y no las
    geometrias. El numero sirve para dejar registrado en la evidencia cuantas
    entidades tiene la capa completa frente a las que se cargaron, que es lo que
    despues permite comprobar que el filtro no se comio ninguna de mas.
    """
    respuesta = cliente.get(
        WFS,
        params={
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": CAPA_DISTRITAL,
            "resultType": "hits",
        },
    )
    respuesta.raise_for_status()

    raiz = ET.fromstring(respuesta.text)
    coincidencias = raiz.attrib.get("numberMatched")
    if coincidencias is None or not coincidencias.isdigit():
        raise ErrorCarga(
            f"El servicio no devolvio un conteo utilizable: {coincidencias!r}"
        )
    return int(coincidencias)


def descargar(cliente: httpx.Client, capa: str) -> Descarga:
    """Descarga una capa filtrada por canton, en EPSG:4326 y formato GeoJSON."""
    parametros = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": capa,
        "outputFormat": "application/json",
        "srsName": f"EPSG:{SRID_ALMACENAMIENTO}",
        "CQL_FILTER": _filtro_canton(),
    }

    respuesta = cliente.get(WFS, params=parametros)
    respuesta.raise_for_status()

    crudo = respuesta.content

    try:
        contenido = json.loads(crudo)
    except json.JSONDecodeError as error:
        # Cuando el filtro esta mal, el servicio responde 200 con un XML de
        # excepcion en vez de GeoJSON. Mostrar el principio del cuerpo ahorra
        # media hora de diagnostico.
        raise ErrorCarga(
            f"La capa {capa} no devolvio GeoJSON. Primeros 400 caracteres de la "
            f"respuesta:\n{crudo[:400].decode('utf-8', errors='replace')}"
        ) from error

    return Descarga(
        capa=capa,
        url=str(respuesta.url),
        bytes_crudos=crudo,
        contenido=contenido,
        momento=datetime.now(UTC),
    )


# --------------------------------------------------------------------------- #
# Validacion, antes de escribir nada                                            #
# --------------------------------------------------------------------------- #


def _texto(propiedades: dict[str, Any], clave: str) -> str:
    """Lee un atributo de texto y le recorta los espacios de los extremos."""
    valor = propiedades.get(clave)
    if valor is None or not str(valor).strip():
        raise ErrorCarga(f"Atributo '{clave}' vacio o ausente en una entidad")
    return str(valor).strip()


def validar_distritos(descarga: Descarga) -> list[dict[str, Any]]:
    """
    Comprueba la coleccion de distritos y devuelve las entidades listas para cargar.

    Todo lo que pueda fallar, falla aqui: antes de abrir la transaccion. Una carga
    que se interrumpe a mitad por un dato malo es peor que una que no empieza.
    """
    entidades = descarga.contenido.get("features", [])

    if len(entidades) != 8:
        raise ErrorCarga(
            f"Se esperaban 8 distritos para el canton {CODIGO_CANTON} y el "
            f"servicio devolvio {len(entidades)}. Revisar el filtro antes de cargar."
        )

    preparadas: list[dict[str, Any]] = []
    codigos_vistos: set[str] = set()

    for entidad in entidades:
        propiedades = entidad.get("properties") or {}

        codigo_dta = propiedades.get("CÓDIGO_DTA")
        if codigo_dta is None:
            raise ErrorCarga(
                "Una entidad no trae CÓDIGO_DTA. Recordar que el atributo "
                "'CÓDIGO' no sirve: vale 160105 en las ocho filas."
            )
        codigo = str(codigo_dta)

        if not codigo.startswith(str(CODIGO_CANTON)):
            raise ErrorCarga(
                f"El distrito {codigo} no pertenece al canton {CODIGO_CANTON}. "
                "El filtro del servicio dejo pasar algo que no corresponde."
            )

        if codigo in codigos_vistos:
            raise ErrorCarga(f"El codigo de distrito {codigo} viene repetido")
        codigos_vistos.add(codigo)

        codigo_canton = int(propiedades["CÓDIGO_CANTÓN"])
        if codigo_canton != CODIGO_CANTON:
            raise ErrorCarga(
                f"El distrito {codigo} declara canton {codigo_canton}, "
                f"se esperaba {CODIGO_CANTON}"
            )

        geometria = entidad.get("geometry")
        if not geometria or geometria.get("type") not in ("Polygon", "MultiPolygon"):
            tipo = (geometria or {}).get("type")
            raise ErrorCarga(
                f"El distrito {codigo} trae una geometria de tipo {tipo!r}, "
                "se esperaba Polygon o MultiPolygon"
            )

        preparadas.append(
            {
                "codigo": codigo,
                "codigo_canton": codigo_canton,
                "codigo_provincia": int(propiedades["CÓDIGO_PROVINCIA"]),
                "nombre": _texto(propiedades, "DISTRITO"),
                "nombre_canton": _texto(propiedades, "CANTÓN"),
                "nombre_provincia": _texto(propiedades, "PROVINCIA"),
                "geojson": json.dumps(geometria),
            }
        )

    faltantes = CODIGOS_ESPERADOS - codigos_vistos
    sobrantes = codigos_vistos - CODIGOS_ESPERADOS
    if faltantes or sobrantes:
        raise ErrorCarga(
            "Los codigos devueltos no coinciden con los ocho oficiales.\n"
            f"  faltan:  {sorted(faltantes) or 'ninguno'}\n"
            f"  sobran:  {sorted(sobrantes) or 'ninguno'}\n"
            "Si el IGN modifico la division territorial, esto lo revisa una "
            "persona antes de cargar."
        )

    return sorted(preparadas, key=lambda d: d["codigo"])


def validar_canton(descarga: Descarga) -> dict[str, Any]:
    """Comprueba que la capa cantonal devolvio exactamente el canton pedido."""
    entidades = descarga.contenido.get("features", [])

    if len(entidades) != 1:
        raise ErrorCarga(
            f"Se esperaba 1 canton y el servicio devolvio {len(entidades)}"
        )

    entidad = entidades[0]
    propiedades = entidad.get("properties") or {}

    codigo = int(propiedades["CÓDIGO_CANTÓN"])
    if codigo != CODIGO_CANTON:
        raise ErrorCarga(f"La capa cantonal devolvio el canton {codigo}")

    geometria = entidad.get("geometry")
    if not geometria or geometria.get("type") not in ("Polygon", "MultiPolygon"):
        raise ErrorCarga("El canton no trae una geometria de poligono utilizable")

    return {
        "codigo": codigo,
        # Ojo: esta capa lo llama CÓDIGO_DE_PROVINCIA, con 'DE'. La distrital lo
        # llama CÓDIGO_PROVINCIA. No son el mismo nombre.
        "codigo_provincia": int(propiedades["CÓDIGO_DE_PROVINCIA"]),
        "nombre": _texto(propiedades, "CANTÓN"),
        "nombre_provincia": _texto(propiedades, "PROVINCIA"),
        "geojson": json.dumps(geometria),
    }


# --------------------------------------------------------------------------- #
# Carga                                                                         #
# --------------------------------------------------------------------------- #

SQL_GEOMETRIA = f"ST_SetSRID(ST_GeomFromGeoJSON(%(geojson)s), {SRID_ALMACENAMIENTO})"

SQL_VALIDEZ = f"SELECT ST_IsValid({SQL_GEOMETRIA})"

SQL_PROVINCIA = """
    INSERT INTO geo.provincia (codigo, nombre)
    VALUES (%(codigo)s, %(nombre)s)
    ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre
"""

SQL_CANTON = f"""
    INSERT INTO geo.canton (codigo, codigo_provincia, nombre, geometria)
    VALUES (
        %(codigo)s,
        %(codigo_provincia)s,
        %(nombre)s,
        ST_Multi(ST_MakeValid({SQL_GEOMETRIA}))
    )
    ON CONFLICT (codigo) DO UPDATE SET
        codigo_provincia = EXCLUDED.codigo_provincia,
        nombre           = EXCLUDED.nombre,
        geometria        = EXCLUDED.geometria
"""

# El area se calcula aqui, no en Python: ST_Transform lleva la geometria al
# sistema metrico y ST_Area devuelve metros cuadrados.
SQL_DISTRITO = f"""
    INSERT INTO geo.distrito (codigo, codigo_canton, nombre, area_km2, poblacion, geometria)
    VALUES (
        %(codigo)s,
        %(codigo_canton)s,
        %(nombre)s,
        ST_Area(ST_Transform(ST_MakeValid({SQL_GEOMETRIA}), {SRID_METRICO})) / 1000000.0,
        NULL,
        ST_Multi(ST_MakeValid({SQL_GEOMETRIA}))
    )
    ON CONFLICT (codigo) DO UPDATE SET
        codigo_canton = EXCLUDED.codigo_canton,
        nombre        = EXCLUDED.nombre,
        area_km2      = EXCLUDED.area_km2,
        geometria     = EXCLUDED.geometria
    RETURNING area_km2
"""


def cargar(
    distritos: list[dict[str, Any]], canton: dict[str, Any]
) -> tuple[list[tuple[str, str, float]], int]:
    """
    Escribe provincia, canton y distritos en una sola transaccion.

    Devuelve las filas cargadas y cuantas geometrias venian invalidas de origen.

    El orden importa: provincia antes que canton, y canton antes que distritos,
    porque las claves foraneas van en esa direccion.
    """
    filas: list[tuple[str, str, float]] = []
    invalidas = 0

    # Una sola transaccion para todo. Si algo falla en el septimo distrito, los
    # seis anteriores tampoco quedan.
    with (
        conectar() as conexion,
        conexion.transaction(),
        conexion.cursor() as cursor,
    ):
        cursor.execute(
            SQL_PROVINCIA,
            {"codigo": canton["codigo_provincia"], "nombre": canton["nombre_provincia"]},
        )
        cursor.execute(SQL_CANTON, canton)

        for distrito in distritos:
            cursor.execute(SQL_VALIDEZ, {"geojson": distrito["geojson"]})
            resultado = cursor.fetchone()
            if resultado is not None and resultado[0] is False:
                invalidas += 1

            cursor.execute(SQL_DISTRITO, distrito)
            area = cursor.fetchone()
            filas.append(
                (distrito["codigo"], distrito["nombre"], float(area[0]) if area else 0.0)
            )

    return filas, invalidas


# --------------------------------------------------------------------------- #
# Procedencia                                                                   #
# --------------------------------------------------------------------------- #


def escribir_procedencia(
    distrital: Descarga, cantonal: Descarga, total_nacional: int, invalidas: int
) -> None:
    """
    Deja el rastro de que se descargo, cuando y con que filtro.

    Sin esto, dentro de un mes nadie puede decir de donde salieron estas
    geometrias ni si siguen siendo las mismas.

    La suma SHA-256 puede cambiar entre descargas aunque los datos sean los
    mismos, porque el servicio no garantiza el orden de las entidades. Lo estable
    para comparar son el conteo y los codigos.
    """
    momento = distrital.momento.astimezone().strftime("%Y-%m-%d %H:%M:%S %z")

    contenido = f"""# Procedencia de las geometrias territoriales

Generado por `backend/etl/cargar_distritos.py`. Historia H1.3, issue #37.
No editar a mano: se reescribe en cada carga.

## Descarga

| Dato | Valor |
|---|---|
| Fecha y hora | {momento} |
| Servicio | {WFS} |
| Capa distrital | `{CAPA_DISTRITAL}` |
| Capa cantonal | `{CAPA_CANTONAL}` |
| Filtro | `{_filtro_canton()}` |
| Sistema de coordenadas pedido | EPSG:{SRID_ALMACENAMIENTO} |

## Cobertura

| Dato | Valor |
|---|---|
| Entidades de la capa distrital a nivel nacional | {total_nacional} |
| Entidades traidas por el filtro | {distrital.entidades} |
| Entidades de la capa cantonal traidas | {cantonal.entidades} |
| Geometrias invalidas de origen, corregidas con ST_MakeValid | {invalidas} |

El filtro reduce {total_nacional} distritos del pais a los {distrital.entidades}
del canton {CODIGO_CANTON} (Tilaran). La reduccion ocurre en el servidor: no se
descargan las {total_nacional} para descartar despues.

## Sumas de verificacion

    distrital  sha256  {distrital.suma_sha256}
    cantonal   sha256  {cantonal.suma_sha256}

## Peticiones exactas

    {distrital.url}

    {cantonal.url}
"""

    RUTA_PROCEDENCIA.parent.mkdir(parents=True, exist_ok=True)
    RUTA_PROCEDENCIA.write_text(contenido, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Punto de entrada                                                              #
# --------------------------------------------------------------------------- #


def ejecutar(solo_descargar: bool = False) -> int:
    with httpx.Client(timeout=TIEMPO_LIMITE, follow_redirects=True) as cliente:
        print(f"Consultando {WFS}")
        total_nacional = contar_total_nacional(cliente)
        print(f"  capa distrital, total nacional: {total_nacional} entidades")

        print(f"  filtro: {_filtro_canton()}")
        distrital = descargar(cliente, CAPA_DISTRITAL)
        cantonal = descargar(cliente, CAPA_CANTONAL)
        print(f"  distritos traidos: {distrital.entidades}")
        print(f"  cantones traidos:  {cantonal.entidades}")

    distritos = validar_distritos(distrital)
    canton = validar_canton(cantonal)
    print(f"\nValidacion superada: {len(distritos)} distritos de {canton['nombre']}")

    if solo_descargar:
        print("\nModo solo descarga: no se escribio en la base.")
        for distrito in distritos:
            print(f"  {distrito['codigo']}  {distrito['nombre']}")
        return 0

    filas, invalidas = cargar(distritos, canton)

    print("\nCargado en geo.distrito:\n")
    print(f"  {'codigo':<8} {'nombre':<18} {'area_km2':>10}")
    print(f"  {'-' * 8} {'-' * 18} {'-' * 10}")
    for codigo, nombre, area in filas:
        print(f"  {codigo:<8} {nombre:<18} {area:>10.4f}")
    print(f"  {'-' * 8} {'-' * 18} {'-' * 10}")
    print(f"  {'':<8} {'suma':<18} {sum(f[2] for f in filas):>10.4f}")

    if invalidas:
        print(f"\nGeometrias invalidas de origen, corregidas: {invalidas}")
    else:
        print("\nNinguna geometria venia invalida de origen.")

    escribir_procedencia(distrital, cantonal, total_nacional, invalidas)
    print(f"Procedencia escrita en {RUTA_PROCEDENCIA}")

    return 0


def main() -> int:
    analizador = argparse.ArgumentParser(
        description="Carga las geometrias oficiales de los distritos de Tilaran."
    )
    analizador.add_argument(
        "--solo-descargar",
        action="store_true",
        help="Descarga y valida sin escribir en la base de datos.",
    )
    argumentos = analizador.parse_args()

    try:
        return ejecutar(solo_descargar=argumentos.solo_descargar)
    except (ErrorCarga, ErrorConexion) as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        return 1
    except httpx.HTTPError as error:
        print(f"\nERROR: fallo la consulta al SNIT.\n{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
