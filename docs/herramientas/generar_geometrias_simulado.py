"""Trae del SNIT las geometrias reales de los ocho distritos y las deja
utilizables por el simulado de contratos.

POR QUE EXISTE

Hasta el 24 de agosto el simulado dibujaba ocho rectangulos de 0,04 grados
colocados en una grilla de 3x3:

    def _cuadro(i: int) -> dict:
        lon, lat = -84.97 + (i % 3) * 0.09, 10.47 - (i // 3) * 0.07

`i % 3` e `i // 3` son fila y columna. **Nunca fueron ubicaciones**, y por eso
ningun distrito caia donde le toca. Servia para tener algo que dibujar mientras
no habia geometria real, y quedo escrito asi en su docstring.

H1.3 cerro el 13 de agosto y trajo la capa oficial a PostGIS. El simulado siguio
con la grilla, y la grilla llego al sitio publicado. Ver la incidencia **I-10**.

POR QUE NO BASTABA CON LEER LA BASE

El simulado tiene que funcionar **sin base de datos y sin red**: es lo que
sostiene el trabajo en paralelo desde el acuerdo A1.3, y lo que corre en el CI.
Por eso la geometria se congela en un archivo JSON que el simulado lee, y este
programa es lo unico que toca la red.

POR QUE REUSA EL CARGADOR DE CESAR

Importa `descargar` y `validar_distritos` de `backend/etl/cargar_distritos.py`
en vez de repetir la peticion. Ese modulo ya tiene documentadas las tres trampas
del servicio -atributos con tilde, nombres distintos por capa, y que `CODIGO` no
es el codigo del distrito-. Una segunda copia de esa logica seria un segundo
lugar donde equivocarse, que es exactamente el defecto que I-10 registra.

SOBRE LA SIMPLIFICACION

La capa viene a escala 1:5000: Tilaran solo tiene 24.515 vertices. Sin
simplificar, el respaldo estatico pesaria mas que todo el resto del sitio.

`basedatos/consultas/poligonos_simplificados.sql` ya resolvio un problema
parecido, pero **con otro criterio**: ahi la geometria viaja dentro de una URL de
ClimateSERV y el limite son unos 3.000 caracteres. Un mapa web aguanta mucho
mas, asi que reusar aquella tolerancia perderia detalle sin motivo.

El criterio aca es visual: que el contorno se vea correcto a la escala en que se
mira el canton entero. Se usa `simplify(preserve_topology=True)`, que es el
equivalente en Shapely de `ST_SimplifyPreserveTopology`, por la misma razon que
da aquel archivo: el simplificador sin topologia puede producir poligonos
invalidos.

El programa **mide** varias tolerancias y las imprime. La eleccion se toma
mirando esa tabla, no de memoria.

USO

    python docs/herramientas/generar_geometrias_simulado.py --medir
    python docs/herramientas/generar_geometrias_simulado.py --tolerancia 0.0005

Escribe `contratos/simulados/geometrias_tilaran.json`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))

DESTINO = RAIZ / "contratos" / "simulados" / "geometrias_tilaran.json"

# 5 decimales son ~1,1 m en el ecuador. Mas que suficiente para un mapa del
# canton, y cada decimal de mas alarga el archivo sin que se note en pantalla.
DECIMALES = 5

TOLERANCIAS = (0.0, 0.0001, 0.0002, 0.0005, 0.001, 0.002)


def _redondear(geometria: dict, decimales: int) -> dict:
    """Recorta decimales recorriendo la estructura, sin importar la profundidad."""

    def recorrer(nodo):
        if isinstance(nodo, int | float):
            return round(float(nodo), decimales)
        return [recorrer(x) for x in nodo]

    return {"type": geometria["type"], "coordinates": recorrer(geometria["coordinates"])}


def _vertices(geometria: dict) -> int:
    def contar(nodo) -> int:
        if isinstance(nodo, int | float):
            return 0
        if nodo and isinstance(nodo[0], int | float):
            return 1
        return sum(contar(x) for x in nodo)

    return contar(geometria["coordinates"])


def _area_km2(figura) -> float:
    """Superficie en kilometros cuadrados, reproyectando a EPSG:8908.

    POR QUE NO SE MIDE SOBRE EPSG:4326

    Medir sobre grados daria un numero en grados cuadrados, que no es una
    superficie. **EPSG:8908 es CR-SIRGAS / CRTM05**, el sistema nativo de la capa
    del SNIT, y esta en metros.

    Es el mismo calculo que hace `cargar_distritos.py` dejandoselo a PostGIS con
    `ST_Area`. Aca no hay base, asi que lo hace pyproj, pero el sistema y el
    criterio son los mismos a proposito: dos formas distintas de medir lo mismo
    serian dos numeros que no coinciden y nadie sabria cual creer.

    POR QUE SE CALCULA Y NO SE ESCRIBE

    Hasta el 24 de agosto las areas eran ocho constantes escritas a mano en
    `contratos/simulados/datos.py`. Contra la geometria oficial fallaban por
    mucho -Tronadora declaraba 30,2 km2 y su poligono mide 140,0- aunque el
    total del canton diera casi bien, lo que sugiere que estaban asignadas a los
    codigos equivocados.

    El panel del visor muestra ese numero al lado de la forma. Ver **I-10**.
    """
    import pyproj
    from shapely.ops import transform

    a_metros = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:8908", always_xy=True).transform
    return transform(a_metros, figura).area / 1_000_000


def _figura(distrito: dict):
    """Convierte a Shapely lo que devuelve `validar_distritos`.

    La clave es **`geojson`**, y trae el GeoJSON **serializado como texto**: ese
    modulo prepara las entidades para insertarlas en PostGIS con
    `ST_GeomFromGeoJSON`, que recibe una cadena. No hay clave `geometria`.

    Existe esta funcion de una linea para que el nombre del campo aparezca una
    sola vez y no en cada lugar que lo use.
    """
    from shapely.geometry import shape

    return shape(json.loads(distrito["geojson"]))


def _traer() -> list[dict]:
    """Descarga y valida, con el cargador de H1.3. Requiere red."""
    import httpx

    from backend.etl.cargar_distritos import (
        CAPA_DISTRITAL,
        TIEMPO_LIMITE,
        descargar,
        validar_distritos,
    )

    with httpx.Client(timeout=TIEMPO_LIMITE, follow_redirects=True) as cliente:
        print(f"Descargando {CAPA_DISTRITAL} del SNIT...")
        descarga = descargar(cliente, CAPA_DISTRITAL)

    distritos = validar_distritos(descarga)
    print(f"  {len(distritos)} distritos validados\n")
    return distritos


def _medir(distritos: list[dict]) -> None:
    print(f"{'tolerancia':>12}{'vertices':>10}{'KB':>8}   nota")
    print("  " + "-" * 44)
    for tolerancia in TOLERANCIAS:
        total_v = 0
        peso = 0
        for d in distritos:
            g = _figura(d)
            if tolerancia:
                g = g.simplify(tolerancia, preserve_topology=True)
            reducida = _redondear(g.__geo_interface__, DECIMALES)
            total_v += _vertices(reducida)
            peso += len(json.dumps(reducida))
        nota = "sin simplificar" if not tolerancia else f"~{tolerancia * 111_000:.0f} m de desvio"
        print(f"{tolerancia:>12}{total_v:>10}{peso / 1024:>8.1f}   {nota}")
    print()


def _escribir(distritos: list[dict], tolerancia: float) -> int:
    salida: dict[str, dict] = {}
    print(f"{'codigo':<8}{'nombre':<18}{'vertices':>10}{'km2':>10}")
    print("-" * 46)
    total = 0.0
    for d in distritos:
        completo = _figura(d)
        g = completo.simplify(tolerancia, preserve_topology=True) if tolerancia else completo

        if not g.is_valid:
            raise SystemExit(f"El poligono de {d['codigo']} quedo invalido al simplificar.")

        # El area se mide sobre el poligono COMPLETO, no sobre el simplificado:
        # la simplificacion existe para que el mapa pese menos, no para cambiar
        # cuanto mide un distrito.
        area = _area_km2(completo)
        total += area

        reducida = _redondear(g.__geo_interface__, DECIMALES)
        salida[d["codigo"]] = {"geometria": reducida, "area_km2": round(area, 1)}
        print(f"{d['codigo']:<8}{d['nombre']:<18}{_vertices(reducida):>10}{area:>10.1f}")

    print("-" * 46)
    print(f"{'':<36}{total:>10.1f}")

    documento = {
        "procedencia": (
            "Capa IGN_5_CO:limitedistrital_5k del SNIT, filtrada por "
            '"CODIGO_CANTON"=508, en EPSG:4326. Descargada con el cargador de '
            "H1.3 y simplificada por docs/herramientas/generar_geometrias_simulado.py."
        ),
        "tolerancia_grados": tolerancia,
        "decimales": DECIMALES,
        "area_medida_en": "EPSG:8908 (CR-SIRGAS / CRTM05), sobre el poligono sin simplificar",
        "distritos": salida,
    }

    DESTINO.write_text(json.dumps(documento, ensure_ascii=False), encoding="utf-8")
    tamano = DESTINO.stat().st_size / 1024
    print(f"\nEscrito {DESTINO.relative_to(RAIZ)}  ({tamano:.1f} KB)")
    return 0


def _comprobar_dependencias() -> None:
    """Falla antes de descargar nada, y dice el comando exacto.

    Este programa arrastra cuatro paquetes: `httpx`, `shapely` y `pyproj` los usa
    directo, y `psycopg` mas `python-dotenv` entran por el import de
    `cargar_distritos`, que carga la base aunque tenga un modo `--solo-descargar`
    que no la toca.

    Se comprueban todos juntos por una razon concreta: la primera vez, cada uno
    aparecio en un error distinto, despues de esperar la descarga, y hubo que
    correr el programa cuatro veces para enterarse de los cuatro.
    """
    import importlib.util

    faltan = [
        instalar
        for modulo, instalar in (
            ("httpx", "httpx==0.28.1"),
            ("shapely", "shapely==2.0.6"),
            ("pyproj", "pyproj==3.7.0"),
            ("psycopg", '"psycopg[binary]==3.2.3"'),
            ("dotenv", "python-dotenv==1.0.1"),
        )
        if importlib.util.find_spec(modulo) is None
    ]

    if faltan:
        raise SystemExit(
            "\nFaltan dependencias. Todas estan en requirements.txt con esa "
            "misma version:\n\n    pip install " + " ".join(faltan) + "\n"
        )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--medir", action="store_true", help="solo imprime la tabla de tolerancias")
    p.add_argument("--tolerancia", type=float, default=0.0005)
    args = p.parse_args()

    _comprobar_dependencias()
    distritos = _traer()

    if args.medir:
        _medir(distritos)
        print("Elegir mirando la tabla y volver a correr con --tolerancia <valor>.")
        return 0

    return _escribir(distritos, args.tolerancia)


if __name__ == "__main__":
    sys.exit(main())
