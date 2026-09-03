"""Descarga imagenes Sentinel-2 de estacion seca sobre Tilaran. Historia H1.6.

=============================================================================
SOBRE LA PROPIEDAD DE ESTE ARCHIVO
=============================================================================

`backend/etl/` es de Cesar. H1.6 paso a Alejandro el 2026-08-31 por **D-33** y la
excepcion se movio con la historia, declarada en `docs/07-propiedad-archivos.md`.

=============================================================================
POR QUE NO CUMPLE NINGUN PROTOCOLO DE `contratos/fuentes.py`
=============================================================================

`ExtractorClima` y `ExtractorFocosCalor` devuelven **filas**: una medicion por dia
o un foco por deteccion. Esta fuente devuelve **archivos de imagen de 15 MB**.

Forzarla dentro de `ExtractorClima` obligaria a inventar un `extraer()` que
devuelve una lista de `MedicionDiaria` que no existe, o a ensanchar un contrato
congelado para acomodar una fuente que no se parece. Las dos son peores que tener
una clase con su propia forma.

**No es una violacion del contrato: es una fuente de otra especie.** Lo que si se
mantiene es la interfaz de uso -`disponible()` antes de una descarga larga- porque
esa parte si es comun y ya esta probada.

=============================================================================
QUE SE DESCARGA, Y POR QUE NO EL PRODUCTO ENTERO
=============================================================================

Un producto L2A completo pesa **entre 0,6 y 1 GB**. Medido contra el catalogo el
2026-09-03: las seis escenas de la estacion seca 2024-25 suman unos **4,4 GB**.

De todo eso, lo que H5.5 necesita para NDVI y NDWI son **tres bandas**. Bajando
solo esas mas la mascara de nubes:

    B03  verde          15,7 MB    NDWI
    B04  rojo           15,5 MB    NDVI
    B8A  infrarrojo     17,4 MB    las dos
    SCL  clasificacion   1,0 MB    mascara de nubes por pixel
                        --------
                        49,6 MB por escena, ~298 MB las seis

**Quince veces menos.** Y esto no es una optimizacion: 4,4 GB no caben con
comodidad en la maquina de un estudiante, asi que la diferencia es entre una
historia que corre y una que no.

**A 20 metros la banda infrarroja es `B8A`, no `B08`.** `B08` solo existe en la
carpeta de 10 m. Se descubrio listando el producto, no leyendo: el NDVI clasico se
escribe con B08 y copiarlo sin mirar habria pedido un archivo que no esta ahi.
B8A es la banda estrecha del mismo infrarrojo cercano y es la correcta a 20 m.

**Por que 20 m y no 10 m.** El proyecto estima riesgo **por distrito**, y el mas
pequenio del canton tiene varios kilometros de lado. A 10 m cada banda pasa de
16 MB a mas de 100 MB para una resolucion que despues se promedia sobre poligonos
enormes. Ver D-33 y la evidencia de H1.6.

=============================================================================
LA BUSQUEDA NO NECESITA CREDENCIALES; LA DESCARGA SI
=============================================================================

Comprobado contra el servicio: el catalogo OData responde sin autenticacion y solo
`$value` exige el token. Por eso `buscar()` se puede correr -y verificar- sin que
nadie tenga cuenta, y `descargar_bandas()` es lo unico que la pide.

Es lo que permite que el verificador de H1.6 compruebe los filtros en cualquier
maquina, incluida la integracion continua, sin poner un secreto en el CI.

Uso:
    python -m backend.etl.fuentes.sentinel --buscar
    python -m backend.etl.fuentes.sentinel --descargar --limite 1
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[3]

# EL .env SE CARGA AQUI, Y ES LO QUE FALTABA EN LA PRIMERA VERSION.
#
# `os.environ` no trae el `.env`: alguien tiene que leerlo. La primera version
# suponia que si, asi que `--buscar` funcionaba -no necesita credenciales- y
# `--descargar` moria diciendo que faltaban variables **que estaban puestas**.
#
# Peor que el olvido: `comprobar_copernicus.py` leia el `.env` con un parser
# escrito a mano, de modo que el comprobador decia SIRVE y el extractor decia que
# faltaban las credenciales, **por la misma cuenta**. Dos formas de leer lo mismo,
# y solo una funcionaba. Es la forma de I-27.
#
# `load_dotenv()` es la forma que el proyecto ya usaba en `basedatos/conexion.py`
# y que esta en `requirements.txt`. Ahora es la unica.
load_dotenv()

CATALOGO = "https://catalogue.dataspace.copernicus.eu/odata/v1"
DESCARGA = "https://download.dataspace.copernicus.eu/odata/v1"
IDENTIDAD = (
    "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
)
CLIENTE_OIDC = "cdse-public"

COLECCION = "SENTINEL-2"

# L2A y no L1C: viene con correccion atmosferica y con la mascara de nubes por
# pixel (SCL). Calcular NDVI sobre reflectancia de tope de atmosfera mezcla la
# senal de la vegetacion con la del aire, y la comparacion entre fechas -que es
# justamente para lo que sirve la serie- deja de ser valida.
TIPO_PRODUCTO = "S2MSI2A"

# Contorno del canton de Tilaran, redondeado hacia afuera desde
# `frontend/public/simulados/distritos.geojson`, que trae los limites del SNIT.
CAJA = (-85.0468, 10.32082, -84.76609, 10.65175)

#: Meses de estacion seca en la vertiente pacifica de Guanacaste.
#:
#: Diciembre a abril. No es una eleccion nuestra: es el criterio de la historia
#: -«imagenes de estacion seca»- y coincide con el regimen del Pacifico Norte de
#: Costa Rica. Se declara aqui porque un rango de fechas escrito suelto en una
#: llamada es un numero magico que nadie puede discutir despues.
ESTACION_SECA = (12, 1, 2, 3, 4)

NUBOSIDAD_MAXIMA = 20.0

#: Banda -> para que sirve. El orden es el de descarga.
BANDAS = {
    "B03": "verde, para NDWI",
    "B04": "rojo, para NDVI",
    "B8A": "infrarrojo cercano a 20 m, para las dos",
    "SCL": "clasificacion de escena, mascara de nubes por pixel",
}

RESOLUCION = "R20m"

TIEMPO_LIMITE = 120.0
TIEMPO_LIMITE_DESCARGA = 900.0

DESTINO = RAIZ / "datos" / "crudos" / "sentinel"


class ErrorSentinel(Exception):
    """Algo de Copernicus no salio como el contrato de esta clase promete."""


@dataclass(frozen=True)
class EscenaSentinel:
    """Una escena del catalogo. Metadatos, todavia sin descargar nada."""

    id: str
    nombre: str
    fecha: date
    bytes: int

    @property
    def mosaico(self) -> str:
        """El identificador de mosaico, `T16PGS` para Tilaran."""
        for parte in self.nombre.split("_"):
            if parte.startswith("T") and len(parte) == 6:
                return parte
        return "?"


def _rango_de_estacion_seca(anio: int) -> tuple[str, str]:
    """La estacion seca de un anio, que **cruza el cambio de anio**.

    Diciembre pertenece a la temporada del anio siguiente. Pedir «diciembre a
    abril del mismo anio» devolveria cero resultados sin fallar, que es la peor
    forma de equivocarse: un filtro vacio se ve igual que un cielo nublado.
    """
    return f"{anio - 1}-12-01T00:00:00.000Z", f"{anio}-05-01T00:00:00.000Z"


def _filtro(desde: str, hasta: str, nubosidad: float) -> str:
    x0, y0, x1, y1 = CAJA
    poligono = f"POLYGON(({x0} {y0},{x1} {y0},{x1} {y1},{x0} {y1},{x0} {y0}))"
    return (
        f"Collection/Name eq '{COLECCION}'"
        " and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType'"
        f" and att/OData.CSC.StringAttribute/Value eq '{TIPO_PRODUCTO}')"
        f" and OData.CSC.Intersects(area=geography'SRID=4326;{poligono}')"
        f" and ContentDate/Start gt {desde}"
        f" and ContentDate/Start lt {hasta}"
        " and Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover'"
        f" and att/OData.CSC.DoubleAttribute/Value le {nubosidad})"
    )


class ExtractorSentinel:
    """Busca y descarga escenas Sentinel-2 sobre el canton de Tilaran."""

    nombre = "Copernicus Sentinel-2 L2A"

    def __init__(
        self,
        usuario: str | None = None,
        clave: str | None = None,
        cliente: httpx.Client | None = None,
    ) -> None:
        self._usuario = usuario if usuario is not None else os.environ.get("COPERNICUS_USER", "")
        self._clave = clave if clave is not None else os.environ.get("COPERNICUS_PASSWORD", "")
        self._propio = cliente is None
        self._cliente = cliente or httpx.Client(timeout=TIEMPO_LIMITE, follow_redirects=True)
        self._token: str | None = None
        self._token_vence = 0.0

    def cerrar(self) -> None:
        if self._propio:
            self._cliente.close()

    # -- Autenticacion ------------------------------------------------------ #

    def _pedir_token(self) -> str:
        """Token nuevo. Vive 1800 s, comprobado contra el servicio.

        Se renueva con **60 segundos de margen**: una descarga de 50 MB puede
        arrancar con el token vivo y terminar con el vencido, y ese fallo llega
        como un 401 a mitad de archivo, que se lee como red rota.
        """
        if not self._usuario or not self._clave:
            raise ErrorSentinel(
                "Faltan COPERNICUS_USER o COPERNICUS_PASSWORD.\n"
                "Comproba la cuenta con:\n"
                "    python docs/herramientas/comprobar_copernicus.py"
            )

        respuesta = self._cliente.post(
            IDENTIDAD,
            data={
                "client_id": CLIENTE_OIDC,
                "username": self._usuario,
                "password": self._clave,
                "grant_type": "password",
            },
            timeout=60.0,
        )
        if respuesta.status_code != 200:
            raise ErrorSentinel(
                f"Copernicus rechazo las credenciales ({respuesta.status_code}). "
                "Corre docs/herramientas/comprobar_copernicus.py para ver por que."
            )

        cuerpo = respuesta.json()
        self._token = cuerpo["access_token"]
        self._token_vence = time.time() + float(cuerpo.get("expires_in", 1800)) - 60
        return self._token

    def _autorizacion(self) -> dict[str, str]:
        if not self._token or time.time() >= self._token_vence:
            self._pedir_token()
        return {"Authorization": f"Bearer {self._token}"}

    def disponible(self) -> bool:
        """Se puede autenticar. Devuelve falso, no lanza: se llama para fallar temprano."""
        try:
            self._pedir_token()
        except (ErrorSentinel, httpx.HTTPError):
            return False
        return True

    # -- Busqueda, sin credenciales ----------------------------------------- #

    def buscar(
        self,
        anio: int,
        nubosidad_maxima: float = NUBOSIDAD_MAXIMA,
    ) -> list[EscenaSentinel]:
        """Escenas de la estacion seca de `anio` con nubosidad bajo el umbral.

        `anio` es el anio en que **termina** la temporada: `buscar(2025)` cubre
        diciembre de 2024 a abril de 2025.
        """
        desde, hasta = _rango_de_estacion_seca(anio)
        parametros = {
            "$filter": _filtro(desde, hasta, nubosidad_maxima),
            "$orderby": "ContentDate/Start asc",
            "$top": "100",
            "$count": "true",
        }

        respuesta = self._cliente.get(f"{CATALOGO}/Products", params=parametros)
        if respuesta.status_code != 200:
            raise ErrorSentinel(
                f"El catalogo respondio {respuesta.status_code}. " f"Cuerpo: {respuesta.text[:200]}"
            )

        cuerpo = respuesta.json()
        escenas = []
        for fila in cuerpo.get("value", []):
            inicio = fila.get("ContentDate", {}).get("Start", "")
            escenas.append(
                EscenaSentinel(
                    id=fila["Id"],
                    nombre=fila["Name"],
                    fecha=datetime.fromisoformat(inicio.replace("Z", "+00:00")).date(),
                    bytes=int(fila.get("ContentLength") or 0),
                )
            )

        # SE COMPRUEBA QUE EL FILTRO DE MES HIZO ALGO.
        #
        # El rango de fechas se arma con cadenas; una mal formada no falla, filtra
        # de menos. Si apareciera una escena de julio, el filtro no esta haciendo
        # lo que dice y las «imagenes de estacion seca» serian imagenes de
        # cualquier epoca.
        fuera = [e for e in escenas if e.fecha.month not in ESTACION_SECA]
        if fuera:
            raise ErrorSentinel(
                f"El catalogo devolvio {len(fuera)} escenas fuera de la estacion "
                f"seca, la primera del {fuera[0].fecha}. El filtro de fechas no "
                f"esta haciendo lo que dice."
            )

        return escenas

    # -- Descarga, con credenciales ----------------------------------------- #

    def _granulo(self, escena: EscenaSentinel) -> str:
        """El identificador del granulo, que **hay que preguntar**.

        Lleva la hora de sensado y el numero de orbita absoluta, y no se puede
        derivar del nombre del producto. Deducirlo era la alternativa y habria
        funcionado hasta la primera escena con otra convencion.
        """
        ruta = f"{DESCARGA}/Products({escena.id})/Nodes({escena.nombre})/Nodes(GRANULE)/Nodes"
        respuesta = self._cliente.get(ruta, headers=self._autorizacion())
        if respuesta.status_code != 200:
            raise ErrorSentinel(f"No se pudo listar el granulo ({respuesta.status_code}).")

        nodos = respuesta.json().get("result", [])
        if len(nodos) != 1:
            raise ErrorSentinel(f"Se esperaba un granulo y hay {len(nodos)}: {escena.nombre}")
        return nodos[0]["Name"]

    def descargar_bandas(
        self,
        escena: EscenaSentinel,
        destino: Path = DESTINO,
        bandas: tuple[str, ...] = tuple(BANDAS),
    ) -> list[Path]:
        """Baja las bandas de una escena. Idempotente: no rebaja lo que ya esta."""
        carpeta = destino / escena.nombre.replace(".SAFE", "")
        carpeta.mkdir(parents=True, exist_ok=True)

        granulo = self._granulo(escena)
        base = (
            f"{DESCARGA}/Products({escena.id})/Nodes({escena.nombre})"
            f"/Nodes(GRANULE)/Nodes({granulo})/Nodes(IMG_DATA)/Nodes({RESOLUCION})/Nodes"
        )

        listado = self._cliente.get(base, headers=self._autorizacion())
        if listado.status_code != 200:
            raise ErrorSentinel(f"No se pudo listar {RESOLUCION} ({listado.status_code}).")
        disponibles = {
            n["Name"]: int(n.get("ContentLength") or 0) for n in listado.json()["result"]
        }

        escritos = []
        for banda in bandas:
            archivo = next((n for n in disponibles if f"_{banda}_" in n), None)
            if archivo is None:
                raise ErrorSentinel(
                    f"La banda {banda} no esta en {RESOLUCION} de {escena.nombre}.\n"
                    f"Hay: {sorted(disponibles)}\n"
                    "A 20 m el infrarrojo cercano se llama B8A, no B08."
                )

            salida = carpeta / archivo
            esperado = disponibles[archivo]

            # IDEMPOTENTE, Y SE COMPRUEBA POR TAMANIO, NO POR EXISTENCIA.
            #
            # Un archivo a medias de una descarga interrumpida existe y esta mal.
            # Comparar contra el tamanio que declara el catalogo distingue las dos
            # cosas; `if salida.exists()` las confunde.
            if salida.exists() and salida.stat().st_size == esperado:
                print(f"    {archivo}  ya estaba")
                escritos.append(salida)
                continue

            print(f"    {archivo}  {esperado / 1048576:.1f} MB")
            parcial = salida.with_suffix(salida.suffix + ".parcial")
            with self._cliente.stream(
                "GET",
                f"{base}({archivo})/$value",
                headers=self._autorizacion(),
                timeout=TIEMPO_LIMITE_DESCARGA,
            ) as flujo:
                if flujo.status_code != 200:
                    raise ErrorSentinel(f"{archivo}: el servidor respondio {flujo.status_code}")
                with parcial.open("wb") as f:
                    for trozo in flujo.iter_bytes(chunk_size=1 << 20):
                        f.write(trozo)

            real = parcial.stat().st_size
            if esperado and real != esperado:
                parcial.unlink()
                raise ErrorSentinel(
                    f"{archivo}: se esperaban {esperado} bytes y llegaron {real}. "
                    "Se borro el parcial en vez de dejar un archivo truncado que "
                    "se ve como una imagen valida."
                )

            # El renombrado va AL FINAL: hasta aqui el archivo bueno no existe con
            # su nombre, asi que una interrupcion nunca deja algo que la proxima
            # corrida confunda con una descarga completa.
            parcial.replace(salida)
            escritos.append(salida)

        return escritos


def main() -> int:
    p = argparse.ArgumentParser(description="Sentinel-2 de estacion seca sobre Tilaran. H1.6.")
    p.add_argument("--buscar", action="store_true", help="solo consulta el catalogo")
    p.add_argument("--descargar", action="store_true", help="baja las bandas")
    p.add_argument("--anio", type=int, default=2025, help="anio en que TERMINA la temporada")
    p.add_argument("--nubosidad", type=float, default=NUBOSIDAD_MAXIMA)
    p.add_argument("--limite", type=int, default=0, help="cuantas escenas bajar, 0 = todas")
    argumentos = p.parse_args()

    extractor = ExtractorSentinel()
    try:
        escenas = extractor.buscar(argumentos.anio, argumentos.nubosidad)

        print(
            f"\nEstacion seca {argumentos.anio - 1}-{argumentos.anio}, "
            f"nubosidad menor o igual a {argumentos.nubosidad:.0f} %\n"
        )
        if not escenas:
            print("  No hay ninguna escena que cumpla. No es un error: es el cielo.\n")
            return 0

        for e in escenas:
            print(f"  {e.fecha}  {e.mosaico}  {e.bytes / 1048576:>7.0f} MB  {e.nombre}")
        print(
            f"\n  {len(escenas)} escenas, {sum(e.bytes for e in escenas) / 1073741824:.1f} GB enteras"
        )
        print(f"  Bajando solo {', '.join(BANDAS)}: unos {len(escenas) * 49.6:.0f} MB\n")

        if not argumentos.descargar:
            return 0

        elegidas = escenas[: argumentos.limite] if argumentos.limite else escenas
        print(f"Descargando {len(elegidas)} escenas a {DESTINO.relative_to(RAIZ)}\n")
        for e in elegidas:
            print(f"  {e.fecha}  {e.nombre}")
            extractor.descargar_bandas(e)
        print("\nListo.\n")
        return 0

    except ErrorSentinel as error:
        print(f"\nERROR: {error}\n", file=sys.stderr)
        return 1
    finally:
        extractor.cerrar()


if __name__ == "__main__":
    raise SystemExit(main())
