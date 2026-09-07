"""
Que ocupan los rasters, y que costaria guardarlos. Dueno: Cesar. Historia H8.4.

QUE MIDE, Y POR QUE ESTAS TRES COSAS

  1. **Inventario de `datos/`**: cuantos archivos y cuantos bytes hay, por
     carpeta y por extension. Es el punto de partida y se mide, no se estima.
  2. **Cuanto pesa un raster derivado** de las bandas de una escena real, en dos
     tipos de dato. Es el numero que nadie tenia: H1.6 midio la descarga, no lo
     que sale de procesarla, y `datos/procesados/` esta vacio.
  3. **Cuanto se comprimen los bytes de un raster.** De ahi sale, sin discutir,
     que le pasaria al respaldo de H1.10 si los rasters entraran a PostGIS: el
     formato `custom` de `pg_dump` comprime, y si estos bytes no se comprimen,
     cada respaldo crece lo mismo que pesan.

EL DERIVADO SE GENERA PARA PESARLO Y SE BORRA

Es un instrumento de medicion, **no una implementacion de H5.5**, que es de
Avril y todavia no esta escrita. Se calcula la forma que tendria un indice
-mismo tamano, mismo tipo de dato, mismos datos de entrada-, se pesa el archivo
resultante y se descarta. Nada queda en `datos/procesados/`.

USO

    python -m backend.etl.inventario_rasters
    python -m backend.etl.inventario_rasters --json     # para el verificador

Necesita una escena descargada por `sentinel.py` para las mediciones 2 y 3. Sin
ella hace el inventario y declara que lo demas no se pudo medir, en vez de
inventarlo.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import tempfile
import zlib
from collections import defaultdict

RAIZ = pathlib.Path(__file__).resolve().parents[2]
DATOS = RAIZ / "datos"
SENTINEL = DATOS / "crudos" / "sentinel"

MB = 1048576


def inventario(carpeta: pathlib.Path = DATOS) -> dict:
    """Cuenta archivos y bytes por carpeta y por extension. No sigue enlaces."""
    por_carpeta: dict[str, dict] = defaultdict(lambda: {"archivos": 0, "bytes": 0})
    por_extension: dict[str, dict] = defaultdict(lambda: {"archivos": 0, "bytes": 0})
    total = {"archivos": 0, "bytes": 0}

    for ruta in sorted(carpeta.rglob("*")):
        if not ruta.is_file() or ruta.is_symlink():
            continue
        tamano = ruta.stat().st_size
        relativa = ruta.parent.relative_to(RAIZ).as_posix()
        extension = ruta.suffix.lower() or "(sin extension)"
        for destino, clave in ((por_carpeta, relativa), (por_extension, extension)):
            destino[clave]["archivos"] += 1
            destino[clave]["bytes"] += tamano
        total["archivos"] += 1
        total["bytes"] += tamano

    return {"total": total, "por_carpeta": dict(por_carpeta), "por_extension": dict(por_extension)}


def _bandas() -> dict[str, pathlib.Path]:
    """Las bandas de la primera escena descargada, si hay alguna."""
    if not SENTINEL.exists():
        return {}
    encontradas = {}
    for banda in ("B03", "B04", "B8A", "SCL"):
        archivos = sorted(SENTINEL.rglob(f"*_{banda}_20m.jp2"))
        if archivos:
            encontradas[banda] = archivos[0]
    return encontradas


def medir_derivado(bandas: dict[str, pathlib.Path]) -> dict | None:
    """
    Pesa un raster derivado de dos bandas reales, en dos tipos de dato.

    Se escribe en una carpeta temporal del sistema, **fuera de `datos/`**, y se
    borra al salir: lo que interesa es el tamano, no el archivo.
    """
    if not {"B04", "B8A"} <= bandas.keys():
        return None

    import numpy as np
    import rasterio

    with rasterio.open(bandas["B04"]) as rojo_ds, rasterio.open(bandas["B8A"]) as nir_ds:
        perfil = rojo_ds.profile
        rojo = rojo_ds.read(1).astype("float32")
        nir = nir_ds.read(1).astype("float32")

    suma = nir + rojo
    derivado = np.where(suma == 0, 0.0, (nir - rojo) / np.where(suma == 0, 1.0, suma))
    derivado = derivado.astype("float32")

    medidas = {
        "forma": [int(derivado.shape[0]), int(derivado.shape[1])],
        "fuentes_mb": round(sum(bandas[b].stat().st_size for b in ("B04", "B8A")) / MB, 1),
    }

    with tempfile.TemporaryDirectory() as temporal:
        for etiqueta, datos, tipo, compresion in (
            ("float32_sin_comprimir", derivado, "float32", "none"),
            ("float32_deflate", derivado, "float32", "deflate"),
            ("int16_escalado_sin_comprimir", np.round(derivado * 10000), "int16", "none"),
            ("int16_escalado_deflate", np.round(derivado * 10000), "int16", "deflate"),
        ):
            salida = perfil.copy()
            salida.update(driver="GTiff", dtype=tipo, count=1, compress=compresion)
            ruta = pathlib.Path(temporal) / f"{etiqueta}.tif"
            with rasterio.open(ruta, "w", **salida) as destino:
                destino.write(datos.astype(tipo), 1)
            medidas[f"{etiqueta}_mb"] = round(ruta.stat().st_size / MB, 1)

    return medidas


def medir_compresion(bandas: dict[str, pathlib.Path]) -> list[dict]:
    """
    Cuanto se encogen los bytes de cada banda con zlib.

    Es lo que decide el costo de meterlos en PostGIS: `pg_dump -Fc` comprime, y
    lo que no se comprime pesa lo mismo dentro del respaldo que fuera.
    """
    resultado = []
    for banda, ruta in sorted(bandas.items()):
        crudo = ruta.stat().st_size
        comprimido = len(zlib.compress(ruta.read_bytes(), 6))
        resultado.append(
            {
                "banda": banda,
                "disco_mb": round(crudo / MB, 1),
                "comprimido_mb": round(comprimido / MB, 1),
                "ganancia_pct": round(100 * (1 - comprimido / crudo), 1),
            }
        )
    return resultado


def recolectar() -> dict:
    bandas = _bandas()
    return {
        "inventario": inventario(),
        "escena": sorted(p.name for p in bandas.values()) or None,
        "derivado": medir_derivado(bandas),
        "compresion": medir_compresion(bandas),
    }


def _imprimir(datos: dict) -> None:
    inv = datos["inventario"]
    print("\nInventario de datos/\n")
    for carpeta, cuenta in sorted(inv["por_carpeta"].items()):
        print(f"  {carpeta:38s} {cuenta['archivos']:4d} archivos  {cuenta['bytes'] / MB:8.1f} MB")
    print(
        f"  {'TOTAL':38s} {inv['total']['archivos']:4d} archivos  "
        f"{inv['total']['bytes'] / MB:8.1f} MB"
    )

    print("\n  por extension:")
    for extension, cuenta in sorted(inv["por_extension"].items(), key=lambda par: -par[1]["bytes"]):
        print(f"    {extension:10s} {cuenta['archivos']:4d}  {cuenta['bytes'] / MB:8.1f} MB")

    if not datos["escena"]:
        print("\nSin escena descargada: no se midio ni el derivado ni la compresion.")
        print("Se descarga con: python -m backend.etl.fuentes.sentinel --descargar --limite 1")
        return

    d = datos["derivado"]
    print(f"\nRaster derivado de {d['forma'][0]}x{d['forma'][1]}, generado para pesarlo y borrado")
    print(f"  sus dos bandas fuente en disco   {d['fuentes_mb']:7.1f} MB")
    print(f"  float32 sin comprimir            {d['float32_sin_comprimir_mb']:7.1f} MB")
    print(
        f"  float32 deflate                  {d['float32_deflate_mb']:7.1f} MB"
        f"   ({d['float32_deflate_mb'] / d['fuentes_mb']:.1f} veces sus fuentes)"
    )
    print(f"  int16 escalado sin comprimir     {d['int16_escalado_sin_comprimir_mb']:7.1f} MB")
    print(
        f"  int16 escalado deflate           {d['int16_escalado_deflate_mb']:7.1f} MB"
        f"   ({d['int16_escalado_deflate_mb'] / d['fuentes_mb']:.1f} veces sus fuentes)"
    )

    print("\nCuanto se comprimen los bytes de cada banda (lo que decidiria el respaldo)")
    for fila in datos["compresion"]:
        print(
            f"  {fila['banda']:4s} {fila['disco_mb']:6.1f} MB -> {fila['comprimido_mb']:6.1f} MB"
            f"   gana {fila['ganancia_pct']:+.1f} %"
        )


def principal(argumentos: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(description="Inventario y costo de los rasters (H8.4)")
    analizador.add_argument("--json", action="store_true", help="imprime los datos crudos")
    opciones = analizador.parse_args(argumentos)

    datos = recolectar()
    if opciones.json:
        print(json.dumps(datos, indent=2, ensure_ascii=False))
    else:
        _imprimir(datos)
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
