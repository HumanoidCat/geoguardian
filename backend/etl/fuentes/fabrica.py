"""
Fabrica de extractores. Dueno: Cesar. Historia H6.3, issue #62.

QUE RESUELVE

`cargar_mediciones.py` y `cargar_focos.py` importaban las clases concretas de
`fuentes/` y las instanciaban a mano. Agregar una fuente nueva obligaba a
tocar esos dos archivos, contra lo que `contratos/fuentes.py` ya declaraba:
"agregar una fuente nueva no debe requerir tocar el orquestador: se registra
y listo. Patron Strategy."

QUE ES UNA FUENTE Y QUE NO, QUE NO ES LO QUE PARECIA

Los criterios de esta historia daban por hecho que habia cuatro
implementaciones -chirps, power, hibrido, firms-. Al construir el registro se
comprobo que no:

  - `ExtractorChirps` y `ExtractorPower` tienen `nombre`, `disponible()` y
    `consultar()`, pero **no `extraer()`**. No cumplen `ExtractorClima`:
    `isinstance(ExtractorChirps(), ExtractorClima)` es False. Son clientes de
    dos APIs, no estrategias intercambiables.
  - La unica fuente climatica que cumple el contrato es `ExtractorHibrido`,
    que usa a las otras dos por dentro (D-15: CHIRPS para lluvia, POWER para
    el resto).
  - `ExtractorFirms` si cumple `ExtractorFocosCalor`.

Por eso el registro tiene **dos** fuentes reales hoy, no cuatro, y chirps y
power no figuran: registrarlas seria declarar como intercambiable algo que no
lo es, y `crear_clima` las rechazaria por CA-2.

COMO SE REGISTRA

Cada entrada es un invocable que devuelve algo que cumple el `Protocol`: una
clase, si su constructor alcanza, o una funcion, si hay que armar algo. Los
argumentos se pasan tal cual: `crear_clima("hibrido", territorios=...)`
necesita territorios y `crear_focos("firms", caja=...)` necesita la caja,
porque cada fuente decide los suyos. La fabrica no los conoce y no tiene una
sola rama por nombre: no le importa si lo registrado compone otras piezas por
dentro o no.

QUE NO HACE

No crea el orquestador. `cargar_distritos.py`, `cargar_focos.py` y
`cargar_mediciones.py` siguen siendo tres programas independientes, cada uno
con su propio `main()`. Esta historia construye la fabrica, no el orquestador
que el titulo nombra y que no existe.

No toca `contratos/fuentes.py`. Los dos `Protocol` ya estan y sirven tal como
estan.
"""

from __future__ import annotations

from collections.abc import Callable

from contratos.fuentes import ExtractorClima, ExtractorFocosCalor

from .chirps import ExtractorChirps
from .firms import ExtractorFirms
from .hibrido import ExtractorHibrido, Territorio
from .power import ExtractorPower
from .prueba_fabrica import ExtractorPrueba


class ErrorFuenteDesconocida(Exception):
    """Se pidio un nombre que no esta en el registro correspondiente."""


def construir_hibrido(
    territorios: list[Territorio],
    registrar: Callable[[str], None] | None = None,
) -> ExtractorHibrido:
    """
    Arma la fuente climatica hibrida (D-15): CHIRPS para lluvia, POWER para el resto.

    Instancia sus dos clientes aca adentro en vez de recibirlos hechos: son
    piezas internas de esta fuente, no fuentes registradas -no cumplen
    `ExtractorClima`-, asi que pedirselas a la fabrica seria darles una
    categoria que no tienen. Quien quiera pasarle dobles para probar sin red
    puede construir `ExtractorHibrido` directamente; esta funcion resuelve el
    caso de produccion.
    """
    return ExtractorHibrido(
        territorios,
        power=ExtractorPower(),
        chirps=ExtractorChirps(),
        registrar=registrar,
    )


REGISTRO_CLIMA: dict[str, Callable[..., ExtractorClima]] = {
    "hibrido": construir_hibrido,
    "prueba": ExtractorPrueba,
}

REGISTRO_FOCOS: dict[str, Callable[..., ExtractorFocosCalor]] = {
    "firms": ExtractorFirms,
}


def crear_clima(nombre: str, **argumentos) -> ExtractorClima:
    """
    Devuelve la fuente climatica registrada con ese nombre.

    CA-2: se comprueba que lo construido cumpla `ExtractorClima` antes de
    devolverlo. Un diccionario de nombre a invocable no valida nada por si
    solo, y sin esta comprobacion se podria registrar algo que revienta recien
    cuando alguien lo use. `runtime_checkable` comprueba que los metodos
    existan, no sus firmas ni sus tipos: es una red, no una garantia.
    """
    constructor = REGISTRO_CLIMA.get(nombre)
    if constructor is None:
        disponibles = ", ".join(sorted(REGISTRO_CLIMA)) or "ninguna"
        raise ErrorFuenteDesconocida(
            f"No hay una fuente climatica llamada '{nombre}'. Disponibles: {disponibles}."
        )

    extractor = constructor(**argumentos)
    if not isinstance(extractor, ExtractorClima):
        raise TypeError(
            f"Lo registrado como '{nombre}' en REGISTRO_CLIMA no cumple ExtractorClima: "
            "le falta 'nombre', 'disponible()' o 'extraer()'."
        )
    return extractor


def crear_focos(nombre: str, **argumentos) -> ExtractorFocosCalor:
    """Igual que `crear_clima`, para focos de calor."""
    constructor = REGISTRO_FOCOS.get(nombre)
    if constructor is None:
        disponibles = ", ".join(sorted(REGISTRO_FOCOS)) or "ninguna"
        raise ErrorFuenteDesconocida(
            f"No hay una fuente de focos de calor llamada '{nombre}'. "
            f"Disponibles: {disponibles}."
        )

    extractor = constructor(**argumentos)
    if not isinstance(extractor, ExtractorFocosCalor):
        raise TypeError(
            f"Lo registrado como '{nombre}' en REGISTRO_FOCOS no cumple ExtractorFocosCalor: "
            "le falta 'nombre', 'disponible()' o 'extraer()'."
        )
    return extractor
