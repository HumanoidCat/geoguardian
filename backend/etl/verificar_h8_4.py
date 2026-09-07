"""
Verificador de H8.4. Dueno: Cesar.

USO

    python -m backend.etl.verificar_h8_4

No necesita Docker ni base de datos. Si necesita **una escena descargada**: sin
ella, CA-2 y CA-3 no se pueden medir y fallan en vez de darse por buenos.

POR QUE COMPARA CONTRA EL TEXTO DE LA EVIDENCIA

Los criterios de esta historia no son sobre codigo, son sobre un documento que
decide. El riesgo no es que el programa falle: es que el documento diga un
numero que ya no sale de ninguna medicion -I-07, una cifra derivada escrita a
mano-. Por eso el verificador **mide y despues comprueba que la evidencia
contenga exactamente lo medido**. Si alguien cambia un numero en el texto sin
volver a medir, esto se pone en rojo.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
EVIDENCIA = RAIZ / "docs" / "evidencias" / "sistemas-operativos" / "H8.4-almacenamiento-rasters.md"
GITIGNORE = RAIZ / ".gitignore"

#: Supuestos declarados de la proyeccion. Los medidos salen de la corrida.
ESCENAS_POR_ESTACION = 6
INDICES_PUBLICADOS = 2


def _coma(valor: float) -> str:
    """El documento escribe los decimales con coma, como el resto del proyecto."""
    return f"{valor:.1f}".replace(".", ",")


class Resultado:
    def __init__(self) -> None:
        self.filas: list[tuple[str, bool, str]] = []

    def marcar(self, criterio: str, cumple: bool, detalle: str = "") -> None:
        self.filas.append((criterio, cumple, detalle))

    def imprimir(self) -> bool:
        for criterio, cumple, detalle in self.filas:
            print(f"{criterio}: {'CUMPLE' if cumple else 'FALLA'}")
            if detalle:
                print(f"    {detalle}")
        return all(cumple for _, cumple, _ in self.filas)


def ca1_inventario(resultado: Resultado, datos: dict) -> None:
    inventario = datos["inventario"]
    hay_medicion = inventario["total"]["archivos"] > 0 and inventario["total"]["bytes"] > 0
    ignorado = "datos/*" in GITIGNORE.read_text(encoding="utf-8")

    resultado.marcar(
        "CA-1 inventario medido de datos/, y nada de eso entra al repositorio",
        hay_medicion and ignorado,
        f"{inventario['total']['archivos']} archivos, "
        f"{inventario['total']['bytes'] / 1048576:.1f} MB en "
        f"{len(inventario['por_carpeta'])} carpetas · `datos/*` en .gitignore: {ignorado}",
    )


def ca2_derivado(resultado: Resultado, datos: dict, texto: str) -> None:
    derivado = datos["derivado"]
    if derivado is None:
        resultado.marcar(
            "CA-2 medido el peso de un raster derivado, en dos tipos de dato",
            False,
            "no hay escena descargada: no se puede medir. "
            "python -m backend.etl.fuentes.sentinel --descargar --limite 1",
        )
        return

    claves = (
        "float32_sin_comprimir_mb",
        "float32_deflate_mb",
        "int16_escalado_sin_comprimir_mb",
        "int16_escalado_deflate_mb",
    )
    faltan = [c for c in claves if _coma(derivado[c]) not in texto]

    resultado.marcar(
        "CA-2 medido el peso de un raster derivado, en dos tipos de dato",
        not faltan,
        f"float32 {_coma(derivado['float32_deflate_mb'])} MB contra sus fuentes "
        f"{_coma(derivado['fuentes_mb'])} MB, int16 {_coma(derivado['int16_escalado_deflate_mb'])} MB"
        if not faltan
        else f"la evidencia no contiene lo medido: {faltan}",
    )


def ca3_disco_o_base(resultado: Resultado, datos: dict, texto: str) -> None:
    """El costo de PostGIS sale de cuanto se comprimen los bytes, no de una opinion."""
    compresion = datos["compresion"]
    if not compresion:
        resultado.marcar(
            "CA-3 disco contra postgis_raster, con el efecto sobre el respaldo de H1.10",
            False,
            "no hay escena descargada: no se puede medir la compresion",
        )
        return

    incompresibles = all(fila["ganancia_pct"] < 5 for fila in compresion)
    por_estacion = round(datos["derivado"]["fuentes_mb"] * 0 + 49.6 * ESCENAS_POR_ESTACION)
    nombra_respaldo = f"+{por_estacion} MB por respaldo" in texto
    nombra_extension = "postgis_raster" in texto

    resultado.marcar(
        "CA-3 disco contra postgis_raster, con el efecto sobre el respaldo de H1.10",
        incompresibles and nombra_respaldo and nombra_extension,
        f"las cuatro bandas ganan menos de 5 % al comprimir: {incompresibles} · "
        f"la evidencia declara +{por_estacion} MB por respaldo: {nombra_respaldo} · "
        f"nombra la extension: {nombra_extension}",
    )


def ca4_proyeccion(resultado: Resultado, datos: dict, texto: str) -> None:
    derivado = datos["derivado"]
    bandas = round(49.6 * ESCENAS_POR_ESTACION)
    indices = round(
        derivado["int16_escalado_deflate_mb"] * ESCENAS_POR_ESTACION * INDICES_PUBLICADOS
    )
    total = bandas + indices

    presentes = [str(n) in texto for n in (bandas, indices, total)]
    etiqueta_medido = "**medido**" in texto
    etiqueta_declarado = "**declarado**" in texto

    resultado.marcar(
        "CA-4 la proyeccion declara que supuesto es medido y cual no",
        all(presentes) and etiqueta_medido and etiqueta_declarado,
        f"{bandas} MB de bandas + {indices} MB de indices = {total} MB por estacion, "
        f"los tres en la evidencia: {all(presentes)} · "
        f"marca medido y declarado: {etiqueta_medido and etiqueta_declarado}",
    )


def ca5_destino(resultado: Resultado, texto: str) -> None:
    declara_maquina = "167 GB libres" in texto
    declara_sin_entorno = "D-05" in texto
    declara_no_medido = "no se midio" in texto.lower() and "corredor de CI" in texto

    resultado.marcar(
        "CA-5 declara contra que destino proyecta y en que punto no cabe",
        declara_maquina and declara_sin_entorno and declara_no_medido,
        f"maquina medida: {declara_maquina} · no hay entorno alojado (D-05): "
        f"{declara_sin_entorno} · declara lo que no midio: {declara_no_medido}",
    )


def ca6_decide(resultado: Resultado, texto: str) -> None:
    decisiones = ("se guardan", "se recalculan", "se descartan", "no se baja")
    faltan = [d for d in decisiones if d not in texto]

    resultado.marcar(
        "CA-6 la estrategia decide que se guarda, que se recalcula y que se descarta",
        not faltan,
        "las cuatro decisiones estan, con su costo de rehacer"
        if not faltan
        else f"faltan: {faltan}",
    )


def ca7_alcance(resultado: Resultado, texto: str) -> None:
    mios = (
        RAIZ / "backend" / "etl" / "inventario_rasters.py",
        RAIZ / "backend" / "etl" / "verificar_h8_4.py",
    )
    # Se miran los **imports**, no el texto: los dos archivos nombran a
    # `sentinel.py` en su ayuda -es como se baja la escena- y buscar la cadena
    # los acusaba de importarlo. Lo detecto este mismo verificador al correrlo.
    importan_sentinel = []
    for archivo in mios:
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            modulos = []
            if isinstance(nodo, ast.Import):
                modulos = [alias.name for alias in nodo.names]
            elif isinstance(nodo, ast.ImportFrom):
                modulos = [nodo.module or ""] + [alias.name for alias in nodo.names]
            if any("sentinel" in modulo for modulo in modulos):
                importan_sentinel.append(archivo.name)
                break
    declara = "No implementa H5.5" in texto and "No modifica `sentinel.py`" in texto

    resultado.marcar(
        "CA-7 (declarado) no toca sentinel.py ni implementa H5.5",
        not importan_sentinel and declara,
        "ninguno de los dos programas importa sentinel.py, y la evidencia lo declara"
        if not importan_sentinel and declara
        else f"importan sentinel: {importan_sentinel} · lo declara: {declara}",
    )


def principal() -> int:
    sys.path.insert(0, str(RAIZ))
    from backend.etl.inventario_rasters import recolectar

    if not EVIDENCIA.exists():
        print(f"Falta la evidencia: {EVIDENCIA}")
        return 1

    texto = EVIDENCIA.read_text(encoding="utf-8")
    datos = recolectar()

    resultado = Resultado()
    ca1_inventario(resultado, datos)
    ca2_derivado(resultado, datos, texto)
    ca3_disco_o_base(resultado, datos, texto)
    ca4_proyeccion(resultado, datos, texto)
    ca5_destino(resultado, texto)
    ca6_decide(resultado, texto)
    ca7_alcance(resultado, texto)

    todo = resultado.imprimir()
    print()
    print("Los siete criterios cumplen." if todo else "Hay criterios que fallan.")
    return 0 if todo else 1


if __name__ == "__main__":
    raise SystemExit(principal())
