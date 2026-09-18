"""Comprueba que los PNG de indices versionados se generaron con el token vigente.

POR QUE EXISTE

El #288 arreglo que la trama de ausencia se dibujara con dos grises distintos: la
coropleta con `--sin-dato-trama` y la capa de indices con un `0x9E` escrito en duro
dentro de `generar_indices.py`. El guion ahora lee el token, asi que el valor ya no
esta duplicado.

**Pero los PNG son artefactos en disco.** Si alguien cambia el token y no vuelve a
correr el guion, las imagenes commiteadas siguen con el gris viejo y nada avisa.
Eso quedo dicho en el propio PR:

    Nada comprueba que los PNG commiteados se hayan generado con el token actual.
    Este arreglo cierra la causa -el valor ya no esta duplicado- pero los PNG son
    artefactos en disco: si alguien cambia el token y no vuelve a correr el guion,
    vuelve a pasar.

Y volvio a pasar con otro archivo: el 2026-09-17, `esperado.json` quedo declarando
contratos 1.4.0 despues de que el arbol subiera a 1.5.0. **Mismo patron, artefacto
distinto.**

Este control mira **los pixeles de la imagen**, no un manifiesto que diga con que
se genero. Un archivo que declara como se hizo a si mismo es exactamente la familia
de I-25, I-39 e I-41: una fuente que informa sobre si misma.

SIN DEPENDENCIAS, Y NO ES CAPRICHO

El trabajo `Frontend` del CI no instala nada de Python: `verificar_escala.py` corre
con biblioteca estandar y este tambien tiene que hacerlo. Por eso el PNG se decodifica
a mano con `zlib` y `struct` en vez de con Pillow o numpy.

Uso, desde la raiz del repositorio:

    python frontend/herramientas/verificar_indices.py
"""

from __future__ import annotations

import re
import struct
import sys
import zlib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
TOKENS = RAIZ / "frontend" / "src" / "estilos" / "tokens.css"
INDICES = RAIZ / "frontend" / "public" / "indices"

fallos: list[str] = []


def comprobar(condicion: bool, descripcion: str, detalle: str = "") -> None:
    marca = "OK   " if condicion else "FALLA"
    print(f"  {marca} {descripcion}{('  ' + detalle) if detalle else ''}")
    if not condicion:
        fallos.append(descripcion)


def leer_token(nombre: str) -> str:
    """El valor de una variable CSS, sin valor por omision.

    Se pide sin respaldo a proposito. Un `.get(nombre, '#9e9e9e')` seguiria
    midiendo el gris viejo el dia que el token se renombre, y saldria en verde:
    es el defecto que este mismo control existe para evitar, cometido al medirlo.
    """
    texto = TOKENS.read_text(encoding="utf-8")
    hallazgo = re.search(rf"{re.escape(nombre)}:\s*(#[0-9a-fA-F]{{6}})\s*;", texto)
    if not hallazgo:
        raise SystemExit(f"ERROR: no se encontro {nombre} en {TOKENS.relative_to(RAIZ)}")
    return hallazgo.group(1).lower()


def leer_png(ruta: Path) -> tuple[int, int, bytearray]:
    """Decodifica un PNG RGBA de 8 bits, sin entrelazar. Devuelve los pixeles.

    Solo el subconjunto que produce `generar_indices.py`. Si el archivo no encaja
    en ese subconjunto **se falla en vez de adivinar**: un decodificador que
    interpreta mal un formato inesperado devuelve colores que no estan ahi, y este
    control se usa justamente para creerle a los colores.
    """
    datos = ruta.read_bytes()
    if datos[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"ERROR: {ruta.name} no es un PNG")

    ancho = alto = profundidad = tipo = entrelazado = None
    comprimido = bytearray()
    posicion = 8

    while posicion < len(datos):
        largo = struct.unpack(">I", datos[posicion : posicion + 4])[0]
        etiqueta = datos[posicion + 4 : posicion + 8]
        cuerpo = datos[posicion + 8 : posicion + 8 + largo]
        posicion += 12 + largo  # 4 largo + 4 etiqueta + cuerpo + 4 CRC

        if etiqueta == b"IHDR":
            ancho, alto, profundidad, tipo, _, _, entrelazado = struct.unpack(">IIBBBBB", cuerpo)
        elif etiqueta == b"IDAT":
            comprimido += cuerpo
        elif etiqueta == b"IEND":
            break

    if (profundidad, tipo, entrelazado) != (8, 6, 0):
        raise SystemExit(
            f"ERROR: {ruta.name} no es RGBA de 8 bits sin entrelazar "
            f"(profundidad={profundidad}, tipo={tipo}, entrelazado={entrelazado}).\n"
            "Este control solo entiende lo que genera generar_indices.py. Si el "
            "formato cambio, hay que actualizarlo en vez de dejarlo adivinar."
        )

    crudo = zlib.decompress(bytes(comprimido))
    canales = 4
    por_linea = ancho * canales
    pixeles = bytearray(alto * por_linea)
    anterior = bytearray(por_linea)

    for fila in range(alto):
        inicio = fila * (por_linea + 1)
        filtro = crudo[inicio]
        linea = bytearray(crudo[inicio + 1 : inicio + 1 + por_linea])

        if filtro == 1:  # Sub
            for i in range(canales, por_linea):
                linea[i] = (linea[i] + linea[i - canales]) & 0xFF
        elif filtro == 2:  # Up
            for i in range(por_linea):
                linea[i] = (linea[i] + anterior[i]) & 0xFF
        elif filtro == 3:  # Average
            for i in range(por_linea):
                izq = linea[i - canales] if i >= canales else 0
                linea[i] = (linea[i] + ((izq + anterior[i]) >> 1)) & 0xFF
        elif filtro == 4:  # Paeth
            for i in range(por_linea):
                izq = linea[i - canales] if i >= canales else 0
                arriba = anterior[i]
                diagonal = anterior[i - canales] if i >= canales else 0
                p = izq + arriba - diagonal
                pa, pb, pc = abs(p - izq), abs(p - arriba), abs(p - diagonal)
                if pa <= pb and pa <= pc:
                    predicho = izq
                elif pb <= pc:
                    predicho = arriba
                else:
                    predicho = diagonal
                linea[i] = (linea[i] + predicho) & 0xFF
        elif filtro != 0:
            raise SystemExit(f"ERROR: filtro PNG desconocido ({filtro}) en {ruta.name}")

        pixeles[fila * por_linea : (fila + 1) * por_linea] = linea
        anterior = linea

    return ancho, alto, pixeles


def grises_de_la_trama(pixeles: bytearray) -> dict[int, int]:
    """Cuenta los grises opacos y neutros, que es donde vive la trama.

    La trama se dibuja con alfa 255 y con los tres canales iguales. El dato del
    indice tambien es opaco, pero sus colores vienen de una rampa que pasa por
    tonos tierra y agua: los grises puros son practicamente solo la trama.
    """
    cuenta: dict[int, int] = {}
    for i in range(0, len(pixeles), 4):
        r, g, b, a = pixeles[i], pixeles[i + 1], pixeles[i + 2], pixeles[i + 3]
        if a == 255 and r == g == b:
            cuenta[r] = cuenta.get(r, 0) + 1
    return cuenta


def main() -> None:
    if not INDICES.exists():
        print(f"No existe {INDICES.relative_to(RAIZ)}: no hay indices que comprobar.")
        print("Se generan con python frontend/herramientas/generar_indices.py")
        return

    png = sorted(INDICES.glob("*.png"))
    if not png:
        print(f"No hay ningun PNG en {INDICES.relative_to(RAIZ)}.")
        return

    trama = leer_token("--sin-dato-trama")
    esperado = int(trama.lstrip("#")[0:2], 16)
    print(f"Token vigente: --sin-dato-trama = {trama}  ->  {esperado} (0x{esperado:02X})")
    print(f"Leido de {TOKENS.relative_to(RAIZ)}\n")

    for ruta in png:
        ancho, alto, pixeles = leer_png(ruta)
        cuenta = grises_de_la_trama(pixeles)

        print(f"{ruta.name}  {ancho}x{alto}")

        if not cuenta:
            # Sin trama no hay nada que comprobar, y eso puede ser correcto: una
            # escena sin nubes dentro del canton no deja huecos. Se dice.
            print("  nota  no hay ningun gris opaco: esta escena no tiene trama de ausencia\n")
            continue

        dominante = max(cuenta, key=cuenta.get)
        comprobar(
            dominante == esperado,
            f"el gris de la trama es el del token ({trama})",
            f"encontrado {dominante} (0x{dominante:02X}) en {cuenta[dominante]} pixeles",
        )

        viejos = {v: n for v, n in cuenta.items() if v != esperado and n > 1000}
        comprobar(
            not viejos,
            "no queda ningun gris de una generacion anterior",
            ""
            if not viejos
            else "encontrados: "
            + ", ".join(f"0x{v:02X} en {n} px" for v, n in sorted(viejos.items())),
        )
        print()

    if fallos:
        print(f"{len(fallos)} comprobaciones fallaron.\n")
        print("Los PNG commiteados NO se generaron con el token vigente.")
        print("Se arregla corriendo:  python frontend/herramientas/generar_indices.py")
        sys.exit(1)

    print("Los PNG de indices se generaron con el token vigente.")


if __name__ == "__main__":
    main()
