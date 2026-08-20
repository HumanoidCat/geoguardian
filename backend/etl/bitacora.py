"""
Bitacora de las corridas. Dueno: Cesar. Historia H1.1, issue #35.

POR QUE LO HACE EL GUION Y NO LA TERMINAL

Capturar la salida desde PowerShell fallo dos veces en este proyecto:

  - `Start-Transcript` no registra la salida de comandos nativos en la version
    5.1, que es la que trae Windows.
  - Una tuberia con `Tee-Object` dejo un archivo con las lineas de PowerShell y
    ninguna de Python. Cuando la salida va por una tuberia, Python la acumula en
    un bufer en vez de escribirla linea por linea; si el proceso muere, ese bufer
    se pierde entero. La corrida habia durado tres minutos y no quedo rastro de
    por que fallo.

La evidencia de un Pull Request no puede depender de que la tuberia de la
terminal se porte bien. Por eso el guion escribe su propia bitacora, y la vacia
en cada linea para que una corrida interrumpida deje igual lo que alcanzo a
hacer.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager


@contextmanager
def abrir(ruta: str | None) -> Iterator[Callable[..., None]]:
    """
    Devuelve una funcion que imprime en pantalla y, si hay ruta, tambien al archivo.

    El archivo va en UTF-8 explicito: la consola de Windows usa cp1252 por
    omision y los nombres de distrito llevan tilde.
    """
    if not ruta:
        yield print
        return

    with open(ruta, "w", encoding="utf-8") as archivo:

        def registrar(*partes: object) -> None:
            texto = " ".join(str(p) for p in partes)
            print(texto)
            archivo.write(texto + "\n")
            archivo.flush()

        yield registrar
