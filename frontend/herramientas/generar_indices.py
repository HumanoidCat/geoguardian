"""Calcula NDVI y NDWI de una escena Sentinel-2 y los deja listos para el visor.

Historia H5.5. Rubrica de Computacion Grafica, criterio CG-3.

===========================================================================
QUE PRODUCE, Y POR QUE ESO
===========================================================================

Un **PNG georreferenciado por indice**, en `frontend/public/indices/`, mas un
`indices.json` con los limites en WGS84 y las cifras de cobertura.

La alternativa era promediar cada indice por distrito y pintarlo como la
coropleta. Se descarto, y el motivo importa porque va en contra de lo que el
proyecto decidio dos veces antes:

  - **D-28/D-30**, el mapa de calor: se objetaba interpolar entre ocho centroides
    porque inventaba valores donde no habia medicion.
  - **I-05**, NASA POWER: se objetaba que los ocho distritos cayeran en la misma
    celda, o sea que el dato no distinguia entre ellos.

**Aca es al reves.** Cada pixel es una medicion de 20 m del satelite. Promediar
sobre un distrito de 70 km2 no evitaria inventar nada: tiraria dato bueno para
parecerse al resto del sistema. Decidido con el PM el 2026-09-03.

La contrapartida se paga en la leyenda, no en el dato: la capa tiene que decir
que es un indice por pixel de una fecha concreta, y no una estimacion de riesgo.

===========================================================================
LAS BANDAS, Y LA QUE TODO EL MUNDO SE EQUIVOCA
===========================================================================

    NDVI = (B8A - B04) / (B8A + B04)      vegetacion
    NDWI = (B03 - B8A) / (B03 + B8A)      agua, McFeeters 1996

**A 20 m el infrarrojo cercano es `B8A`, no `B08`.** La formula del NDVI se
escribe siempre con B08, y en la carpeta `R20m` esa banda no existe: solo esta en
la de 10 m. Lo dejo escrito porque copiar la formula sin mirar el producto es
exactamente como se pierde una hora.

===========================================================================
LA MASCARA, Y POR QUE SE CUENTA LO QUE TAPA
===========================================================================

`SCL` clasifica cada pixel. Se conservan solo vegetacion, suelo desnudo, agua y
sin clasificar; se descartan nube, sombra de nube, cirro, saturado y sin dato.

Un pixel de nube da un NDVI que parece suelo desnudo. Sin mascara la capa
mentiria justo donde el dato falta, que es I-05 otra vez.

**Y el filtro de nubosidad del catalogo es del mosaico entero (T16PGS), no de
Tilaran.** Una escena que el catalogo declara limpia puede tener el canton tapado.
Por eso el guion **cuenta que porcentaje del canton quedo sin dato** y lo imprime:
si es alto, la escena no sirve y hay que probar otra de la temporada. Aviso del PM
al cerrar H1.6.

Uso:

    python frontend/herramientas/generar_indices.py
    python frontend/herramientas/generar_indices.py --escena <carpeta .SAFE>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CRUDOS = RAIZ / "datos" / "crudos" / "sentinel"
DISTRITOS = RAIZ / "frontend" / "public" / "simulados" / "distritos.geojson"
SALIDA = RAIZ / "frontend" / "public" / "indices"

#: Clases de SCL que se conservan. El resto se descarta.
#:
#:   4 vegetacion · 5 suelo desnudo · 6 agua · 7 sin clasificar
#:
#: Se descartan: 0 sin dato, 1 saturado, 2 sombra topografica, 3 sombra de nube,
#: 8 nube probable, 9 nube muy probable, 10 cirro, 11 nieve.
#:
#: El 7 (sin clasificar) se conserva a proposito: es "no se pudo decidir", no
#: "hay nube". Descartarlo agrandaria el hueco sin motivo.
SCL_VALIDAS = {4, 5, 6, 7}

#: Extremos de la rampa de color de cada indice.
#:
#: **EL RANGO SE DECLARA, NO SE CALCULA.** Es la decision que hace que dos escenas
#: se puedan comparar, y merece explicacion porque la alternativa comoda es peor.
#:
#: Estirar al minimo y maximo *de cada escena* daria mas contraste y seria un
#: defecto: el mismo verde significaria cosas distintas segun la imagen. Un
#: potrero identico cambiaria de color el 8 de febrero solo porque cambio el
#: maximo del mosaico, y la capa afirmaria un cambio que no ocurrio. Es la forma
#: de I-04 -el mismo dato diciendo cosas distintas segun donde se mire- aplicada
#: al color.
#:
#: Usar el rango teorico entero, -1 a 1, tampoco sirve: la vegetacion real vive
#: entre 0,2 y 0,9, asi que todo el detalle se apelmaza en un octavo de la escala
#: y un potrero seco se ve igual que un bosque cerrado.
#:
#: Asi que se fijan por razones fisicas, y los numeros van en la leyenda para que
#: el color se pueda leer como cifra:
#:
#:   NDVI  -0,1 a 0,9   por debajo de 0 solo hay agua y sombra; por encima de 0,9
#:                      no ocurre en la practica
#:   NDWI  -0,7 a 0,7   **simetrico a proposito**: el 0 es la frontera fisica
#:                      entre tierra y agua, asi que el color del medio la marca
#:
#: MEDIDO SOBRE LA ESCENA DEL 2025-01-27, y por eso el NDWI llega a 0,7:
#:
#:   NDVI   p25 0,44 · mediana 0,51 · p95 0,60 · maximo 0,72
#:   NDWI   p25 -0,50 · mediana -0,46 · p95 0,13 · minimo **-0,652**
#:
#: Con -0,6 el extremo recortaba. Se corrio a -0,7 para que ningun pixel quede
#: fuera **sin ajustar la escala a esta escena**: -0,7 sigue siendo un numero
#: redondo elegido con margen, no el minimo observado. La diferencia importa: el
#: minimo observado cambiaria en la proxima imagen y la escala con el.
#:
#: Que el NDVI tope en 0,72 y la escala llegue a 0,9 no es desperdicio, es dato:
#: dice que el canton no tiene vegetacion de dosel cerrado. Y que la mitad de los
#: pixeles caigan entre 0,44 y 0,55 dice que es uniforme. Estirar mas fabricaria
#: un contraste que la medicion no sostiene.
RANGOS = {
    "ndvi": (-0.1, 0.9),
    "ndwi": (-0.7, 0.7),
}

#: Tamano del lado del PNG de salida, en pixeles.
#:
#: El canton mide unos 31 km de este a oeste. A 20 m por pixel eso son ~1550
#: pixeles, asi que 1600 conserva la resolucion nativa sin inventar detalle.
#: Subirlo mas seria remuestrear hacia arriba: mas peso y ni un dato nuevo.
LADO = 1600


def _fallar(mensaje: str) -> None:
    print(f"\nERROR: {mensaje}\n", file=sys.stderr)
    raise SystemExit(1)


def buscar_escena(indicada: str | None) -> Path:
    """La carpeta `.SAFE` de la escena, o un error que dice como conseguirla."""
    if indicada:
        carpeta = Path(indicada)
        if not carpeta.is_absolute():
            carpeta = CRUDOS / indicada
        if not carpeta.exists():
            _fallar(f"no existe la carpeta {carpeta}")
        return carpeta

    if not CRUDOS.exists():
        _fallar(
            f"no existe {CRUDOS.relative_to(RAIZ)}.\n"
            "Bajá una escena con:\n"
            "    python -m backend.etl.fuentes.sentinel --descargar --limite 1\n"
            "Hace falta COPERNICUS_USER y COPERNICUS_PASSWORD en el .env."
        )

    # Se busca por `MSIL2A` y **no por `.SAFE`**: el descargador de H1.6 quita esa
    # extension al crear la carpeta -`escena.nombre.replace(".SAFE", "")`- y deja
    # las cuatro bandas planas adentro, sin el arbol GRANULE del producto
    # original. Buscar `.SAFE` no encontraba nada aunque la descarga estuviera
    # completa, que es peor que no encontrar: el error culpa a la descarga.
    escenas = sorted(p for p in CRUDOS.iterdir() if p.is_dir() and "MSIL2A" in p.name)
    if not escenas:
        sueltas = sorted(p.name for p in CRUDOS.iterdir())
        _fallar(
            f"{CRUDOS.relative_to(RAIZ)} existe pero no tiene ninguna escena.\n"
            f"Contiene: {sueltas or 'nada'}\n"
            "Se esperaba una carpeta con MSIL2A en el nombre. Bajá una con:\n"
            "    python -m backend.etl.fuentes.sentinel --descargar --limite 1"
        )
    if len(escenas) > 1:
        print(f"Hay {len(escenas)} escenas; se usa la primera. Con --escena se elige otra.")
    return escenas[0]


def buscar_banda(escena: Path, banda: str) -> Path:
    """La banda a 20 m dentro del producto.

    Se busca por patron y no por ruta armada a mano porque el nombre de las
    subcarpetas de un `.SAFE` lleva marcas de tiempo que cambian por escena.
    """
    encontradas = sorted(escena.rglob(f"*_{banda}_20m.jp2"))
    if not encontradas:
        disponibles = sorted({p.name for p in escena.rglob("*_20m.jp2")})
        _fallar(
            f"no se encontro la banda {banda} a 20 m en {escena.name}.\n"
            f"Hay: {disponibles or 'ninguna banda de 20 m'}\n"
            + ("Ojo: a 20 m el infrarrojo cercano es B8A, no B08." if banda == "B08" else "")
        )
    return encontradas[0]


def geometrias_del_canton() -> list[dict]:
    """Los poligonos de los ocho distritos, para recortar."""
    if not DISTRITOS.exists():
        _fallar(f"no existe {DISTRITOS.relative_to(RAIZ)}")
    coleccion = json.loads(DISTRITOS.read_text(encoding="utf-8"))
    return [rasgo["geometry"] for rasgo in coleccion["features"]]


def limites_del_canton(geometrias: list[dict]) -> tuple[float, float, float, float]:
    """(oeste, sur, este, norte) en WGS84."""
    xs: list[float] = []
    ys: list[float] = []
    for g in geometrias:
        partes = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for parte in partes:
            for x, y in parte[0]:
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument("--escena", help="carpeta .SAFE; por omision, la primera que haya")
    argumentos = analizador.parse_args()

    try:
        import numpy as np
        import rasterio
        from rasterio.features import geometry_mask
        from rasterio.warp import Resampling, calculate_default_transform, reproject
    except ImportError as falta:
        _fallar(
            f"falta una dependencia: {falta.name}.\n"
            "Estan en requirements.txt: activá el entorno virtual."
        )

    escena = buscar_escena(argumentos.escena)
    print(f"\nEscena: {escena.name}")

    # La fecha sale del nombre del producto, que la lleva en la segunda parte:
    # S2C_MSIL2A_20250127T160601_... -> 2025-01-27
    marca = escena.name.split("_")[2]
    fecha = f"{marca[0:4]}-{marca[4:6]}-{marca[6:8]}"
    print(f"Fecha:  {fecha}\n")

    bandas: dict[str, np.ndarray] = {}
    perfil = None
    for nombre in ("B03", "B04", "B8A", "SCL"):
        ruta = buscar_banda(escena, nombre)
        with rasterio.open(ruta) as fuente:
            bandas[nombre] = fuente.read(1)
            if perfil is None:
                perfil = fuente.profile
                crs_origen = fuente.crs
                transformacion_origen = fuente.transform
        print(f"  {nombre}  {bandas[nombre].shape[1]}x{bandas[nombre].shape[0]}  {ruta.name}")

    # --------------------------------------------------------------------- #
    # Los indices                                                            #
    # --------------------------------------------------------------------- #
    #
    # En flotante y con `errstate`: donde el denominador es cero el resultado es
    # NaN, y NaN es exactamente lo que queremos -ausencia- en vez de un cero que
    # se leeria como un valor medido.
    verde = bandas["B03"].astype("float32")
    rojo = bandas["B04"].astype("float32")
    nir = bandas["B8A"].astype("float32")

    with np.errstate(divide="ignore", invalid="ignore"):
        ndvi = (nir - rojo) / (nir + rojo)
        ndwi = (verde - nir) / (verde + nir)

    valido = np.isin(bandas["SCL"], list(SCL_VALIDAS))
    ndvi = np.where(valido, ndvi, np.nan)
    ndwi = np.where(valido, ndwi, np.nan)

    print(f"\nMascara SCL: {valido.mean() * 100:.1f} % de la escena es dato util")

    # --------------------------------------------------------------------- #
    # A WGS84, en la rejilla del canton                                      #
    # --------------------------------------------------------------------- #
    geometrias = geometrias_del_canton()
    oeste, sur, este, norte = limites_del_canton(geometrias)

    destino_transformacion, ancho, alto = calculate_default_transform(
        crs_origen,
        "EPSG:4326",
        bandas["B03"].shape[1],
        bandas["B03"].shape[0],
        *rasterio.transform.array_bounds(
            bandas["B03"].shape[0], bandas["B03"].shape[1], transformacion_origen
        ),
        dst_width=LADO,
        dst_height=LADO,
    )
    # Se reemplaza por la caja del canton: no interesa el mosaico entero.
    destino_transformacion = rasterio.transform.from_bounds(oeste, sur, este, norte, LADO, LADO)

    def a_wgs84(arreglo: np.ndarray) -> np.ndarray:
        salida = np.full((LADO, LADO), np.nan, dtype="float32")
        reproject(
            source=arreglo,
            destination=salida,
            src_transform=transformacion_origen,
            src_crs=crs_origen,
            dst_transform=destino_transformacion,
            dst_crs="EPSG:4326",
            resampling=Resampling.nearest,
            src_nodata=np.nan,
            dst_nodata=np.nan,
        )
        return salida

    # --------------------------------------------------------------------- #
    # Recorte contra los poligonos                                           #
    # --------------------------------------------------------------------- #
    #
    # Fuera del canton no se pinta. Es la misma leccion de D-30: la capa anterior
    # se salia del canton porque su caja venia de los centroides.
    fuera = geometry_mask(
        geometrias,
        out_shape=(LADO, LADO),
        transform=destino_transformacion,
        invert=False,
    )

    SALIDA.mkdir(parents=True, exist_ok=True)
    resumen: dict[str, object] = {
        "escena": escena.name,
        "fecha": fecha,
        "limites": {"oeste": oeste, "sur": sur, "este": este, "norte": norte},
        "lado": LADO,
        "indices": {},
    }

    for nombre, datos, rampa in (
        ("ndvi", ndvi, "vegetacion"),
        ("ndwi", ndwi, "agua"),
    ):
        proyectado = a_wgs84(datos)
        proyectado = np.where(fuera, np.nan, proyectado)

        dentro = ~fuera
        con_dato = dentro & ~np.isnan(proyectado)
        cobertura = con_dato.sum() / max(dentro.sum(), 1) * 100

        png = SALIDA / f"{nombre}.png"
        _escribir_png(proyectado, rampa, png, destino_transformacion, nombre, dentro)

        # El rango viaja al visor: la leyenda tiene que poder escribir los
        # numeros de los extremos. Un color sin su cifra al lado se lee como
        # impresion y no como medicion.
        minimo, maximo = RANGOS[nombre]
        resumen["indices"][nombre] = {
            "archivo": f"indices/{nombre}.png",
            "minimo": minimo,
            "maximo": maximo,
            "cobertura_canton": round(cobertura, 1),
            "sin_dato_canton": round(100 - cobertura, 1),
        }

        print(
            f"  {nombre.upper()}  {png.relative_to(RAIZ)}  "
            f"cobertura del canton: {cobertura:.1f} %"
        )

    (SALIDA / "indices.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"  {(SALIDA / 'indices.json').relative_to(RAIZ)}\n")

    peor = min(v["cobertura_canton"] for v in resumen["indices"].values())
    if peor < 70:
        print(
            f"AVISO: solo el {peor:.1f} % del canton tiene dato.\n"
            "El filtro de nubosidad del catalogo es del mosaico entero, no de\n"
            "Tilaran, asi que una escena declarada limpia puede tener el canton\n"
            "tapado. Conviene probar otra escena de la temporada.\n"
        )
    return 0


def _escribir_png(
    datos,
    rampa: str,
    destino: Path,
    transformacion,
    nombre_indice: str,
    dentro_canton=None,
) -> None:
    """Colorea el indice y lo escribe como PNG.

    Ningun pixel sin dato recibe un color de la escala. Es D-07 aplicado al
    raster: la ausencia se declara, no se rellena con algo plausible.

    Y se declara de dos formas distintas, porque son dos ausencias distintas:

      **dentro del canton, sin dato**   trama diagonal, la misma de "sin
                                        estimacion" en la coropleta
      **fuera del canton**              transparente: ahi no falta el dato, es
                                        que no corresponde

    SE ESCRIBE CON RASTERIO Y NO CON PILLOW, A PROPOSITO.

    Pillow seria una linea mas corta, pero **no esta en `requirements.txt`**, y ese
    archivo exige solicitud de cambio. Pedir una dependencia nueva para colorear
    un arreglo, teniendo `rasterio` ya instalado, seria pagar mantenimiento para
    siempre a cambio de una comodidad de un rato.

    El PNG de GDAL no admite creacion directa -solo copia-, asi que se arma un
    GeoTIFF temporal y se copia. Es el camino documentado, no un rodeo.
    """
    import tempfile

    import numpy as np
    import rasterio
    from rasterio.shutil import copy as copiar_raster

    # A [0, 1] contra el rango **declarado** del indice, no contra el de la
    # escena. Ver RANGOS: es lo que hace que el mismo color signifique lo mismo
    # en cualquier fecha.
    minimo, maximo = RANGOS[nombre_indice]
    normalizado = np.clip((np.nan_to_num(datos, nan=minimo) - minimo) / (maximo - minimo), 0, 1)
    hay = ~np.isnan(datos)

    alto, ancho = datos.shape
    canales = np.zeros((4, alto, ancho), dtype="uint8")

    if rampa == "vegetacion":
        # Marron seco -> verde. La misma direccion que cualquier NDVI publicado.
        crudos = (170 - 130 * normalizado, 110 + 110 * normalizado, 60 + 40 * normalizado)
    else:
        # Ocre -> azul.
        crudos = (200 - 180 * normalizado, 190 - 80 * normalizado, 140 + 100 * normalizado)

    for indice, canal in enumerate(crudos):
        canales[indice] = np.where(hay, canal, 0).astype("uint8")
    canales[3] = np.where(hay, 255, 0).astype("uint8")

    # ----------------------------------------------------------------------- #
    # La ausencia se dibuja, no se deja transparente                            #
    # ----------------------------------------------------------------------- #
    #
    # La primera version dejaba los huecos de nube transparentes. Se vio en el
    # visor y estaba mal: por debajo asoma la coropleta de riesgo, y como la
    # rampa del NDVI pasa por tonos tierra, **el naranja de "Medio" se lee como
    # un valor del indice**. La ausencia se disfrazaba del dato de otra capa.
    #
    # Es D-07: lo que falta se declara. Y el visor ya tiene un lenguaje para
    # eso, la trama de "sin estimacion" de la coropleta, asi que se usa el mismo
    # -misma inclinacion, mismo paso, mismos colores de tokens.css- para que las
    # dos ausencias se lean igual.
    #
    # Solo dentro del canton: fuera se sigue sin pintar nada, porque ahi no es
    # que falte el dato, es que no corresponde.
    if dentro_canton is not None:
        alto_t, ancho_t = datos.shape
        filas, columnas = np.indices((alto_t, ancho_t))
        # Diagonales a 45 grados con paso de 8 px y trazo de 2 px, como el
        # `<pattern>` de MapaCanton.jsx.
        trama = ((filas + columnas) % 8) < 2
        hueco = dentro_canton & ~hay

        # Fondo blanco al 55 %, y la linea gris encima. Los dos colores salen de
        # tokens.css: --sin-dato-fondo y --sin-dato-trama.
        canales[0] = np.where(hueco, np.where(trama, 0x9E, 0xFF), canales[0])
        canales[1] = np.where(hueco, np.where(trama, 0x9E, 0xFF), canales[1])
        canales[2] = np.where(hueco, np.where(trama, 0x9E, 0xFF), canales[2])
        canales[3] = np.where(hueco, np.where(trama, 255, 140), canales[3])

    perfil = {
        "driver": "GTiff",
        "height": alto,
        "width": ancho,
        "count": 4,
        "dtype": "uint8",
        "crs": "EPSG:4326",
        "transform": transformacion,
    }
    # `GDAL_PAM_ENABLED=NO` impide que GDAL escriba un `.aux.xml` con sus
    # estadisticas al lado de cada PNG. Se evita que aparezca en vez de borrarlo
    # despues: un archivo que no se crea no se puede colar en un commit por
    # descuido, y borrarlo depende de tener permiso de escritura en esa carpeta.
    with rasterio.Env(GDAL_PAM_ENABLED="NO"), tempfile.TemporaryDirectory() as carpeta:
        intermedio = Path(carpeta) / "indice.tif"
        with rasterio.open(intermedio, "w", **perfil) as salida:
            salida.write(canales)
        copiar_raster(str(intermedio), str(destino), driver="PNG")


if __name__ == "__main__":
    sys.exit(main())
