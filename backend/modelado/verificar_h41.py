"""
Verificador de H4.1 · Importancia de variables global del mejor modelo.

Dueno: Luna, traspasada desde Alejandro por **D-37**.
Criterios en `docs/evidencias/objetivos/H4.1-criterios-aceptacion.md`.

CORRE SIN BASE Y SIN RED, con un estimador de juguete y pliegues escritos a
mano. Es CA-11, y es la misma forma que `verificar_h34` y `verificar_h35`.

LA COMPROBACION QUE MAS VALE ES LA 10
-------------------------------------

`importancia.py` arma los pliegues con la misma receta que `comparar.comparar`,
porque `comparar` no la expone por separado y esta historia no lo toca. **Dos
implementaciones de la misma medida terminan midiendo cosas distintas**, y ese es
un riesgo real, no teorico.

La comprobacion 10 no confia: corre `comparar()` y `importancia()` sobre los
mismos datos y el mismo estimador, y exige que el F1 de referencia por pliegue
sea **identico, valor por valor**. Si alguien cambia la particion de un lado y no
del otro, sale en rojo el mismo dia.

LOS DOS SABOTAJES DEL FINAL
---------------------------

Un verificador que solo comprueba que las cosas funcionan no dice nada sobre si
comprobaria un fallo. Los dos ultimos rompen algo a proposito y **exigen que se
note**:

 13. Si la permutacion no permuta, todas las caidas tienen que dar CERO exacto.
     Si no dan cero, lo que se esta midiendo incluye el azar del propio modelo, y
     entonces una parte de cada «importancia» no es importancia.
 14. Si la prueba se solapa con el entrenamiento -la fuga que CA-2 prohibe- el F1
     de referencia tiene que SUBIR. Es la demostracion de que la proteccion no es
     decorativa: el error mejora el numero, y por eso no se ve.

Uso:
    python -m backend.modelado.verificar_h41
"""

from __future__ import annotations

import random
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.modelado.comparar import Observacion, comparar  # noqa: E402
from backend.modelado.importancia import (  # noqa: E402
    ImportanciaColumna,
    _permutar,
    columnas_de,
    importancia,
)
from backend.modelado.particion import Pliegue  # noqa: E402
from contratos.enums import NivelRiesgo, TipoEvento  # noqa: E402

INICIO = date(2020, 1, 1)
DIAS = 40


class Resultado:
    def __init__(self) -> None:
        self.fallos: list[str] = []
        self.hechos = 0

    def comprobar(self, nombre: str, condicion: bool, detalle: str = "") -> None:
        self.hechos += 1
        print(f"  {'ok   ' if condicion else 'FALLA'}  {nombre}")
        if not condicion:
            self.fallos.append(f"{nombre}{': ' + detalle if detalle else ''}")
        elif detalle:
            print(f"           {detalle}")


class SoloMiraUna:
    """Predice ALTO si `util` supera 0.5. Ignora todo lo demas, y eso se sabe."""

    nombre = "juguete"

    def __init__(self) -> None:
        self.vistas_al_predecir: list[list[Observacion]] = []

    def ajustar(self, observaciones, etiquetas):
        return self

    def predecir(self, observaciones):
        self.vistas_al_predecir.append(list(observaciones))
        return [
            NivelRiesgo.ALTO if o.caracteristicas.get("util", 0.0) > 0.5 else NivelRiesgo.BAJO
            for o in observaciones
        ]


class SeEquivocaConLaColumna:
    """Usa `util` **al reves**. Permutarla tiene que MEJORAR la metrica.

    Existe para el criterio CA-5: sin un caso asi, «no se recortan los negativos»
    no se puede comprobar, porque ningun modelo razonable produce uno.
    """

    nombre = "al reves"

    def ajustar(self, observaciones, etiquetas):
        return self

    def predecir(self, observaciones):
        return [
            NivelRiesgo.BAJO if o.caracteristicas.get("util", 0.0) > 0.5 else NivelRiesgo.ALTO
            for o in observaciones
        ]


class Memorion:
    """Memoriza el entrenamiento y responde de memoria. Fuera de ella, BAJO.

    Existe solo para el sabotaje 14. Un modelo que **generaliza** -como el
    juguete- da lo mismo con fuga y sin fuga, asi que no sirve para demostrar que
    la fuga infla: hace falta uno que sobreajuste, que es lo que hacen los
    modelos de verdad cuando se les da la oportunidad.
    """

    nombre = "memorion"

    def __init__(self) -> None:
        self._memoria: dict[date, NivelRiesgo] = {}

    def ajustar(self, observaciones, etiquetas):
        self._memoria = {o.fecha: e for o, e in zip(observaciones, etiquetas, strict=True)}
        return self

    def predecir(self, observaciones):
        return [self._memoria.get(o.fecha, NivelRiesgo.BAJO) for o in observaciones]


def datos(n: int = DIAS):
    filas, caracteristicas = [], {}
    for i in range(n):
        fecha = INICIO + timedelta(days=i)
        util = 1.0 if i % 2 == 0 else 0.0
        nivel = NivelRiesgo.ALTO if util else NivelRiesgo.BAJO
        filas.append(("50801", fecha, {"lluvia_intensa": nivel}))
        caracteristicas[("50801", fecha)] = {"util": util, "ruido": float(i % 3)}
    return filas, caracteristicas


def un_pliegue(n: int = DIAS) -> list[Pliegue]:
    corte = INICIO + timedelta(days=n // 2)
    return [
        Pliegue(
            indice=0,
            entrenamiento=(INICIO, corte - timedelta(days=1)),
            prueba=(corte, INICIO + timedelta(days=n - 1)),
            embargo=None,
        )
    ]


def verificar() -> Resultado:
    r = Resultado()
    filas, caracteristicas = datos()
    pliegues = un_pliegue()

    print("\nImportancia de variables global · H4.1\n")

    # ------------------------------------------------------------------ 1
    obs = [
        Observacion(f"5080{i}", date(2024, 1, 1 + i), {"pp_7": float(i), "tmax_3": float(9 - i)})
        for i in range(6)
    ]
    obs.append(Observacion("50899", date(2024, 2, 1), {"tmax_3": 7.0}))

    permutadas = _permutar(obs, "pp_7", random.Random("H4.1|0|pp_7|0"))
    r.comprobar(
        "1. la permutacion conserva el patron de ausencia",
        "pp_7" not in permutadas[-1].caracteristicas
        and sum("pp_7" in o.caracteristicas for o in permutadas) == 6,
        "rellenar los huecos cambiaria cuantas filas se pueden predecir",
    )

    # ------------------------------------------------------------------ 2
    r.comprobar(
        "2. la permutacion no toca las otras columnas",
        [o.caracteristicas["tmax_3"] for o in permutadas]
        == [o.caracteristicas["tmax_3"] for o in obs],
    )

    # ------------------------------------------------------------------ 3
    r.comprobar(
        "3. reordena sin inventar ni perder valores",
        sorted(o.caracteristicas["pp_7"] for o in permutadas if "pp_7" in o.caracteristicas)
        == sorted(o.caracteristicas["pp_7"] for o in obs if "pp_7" in o.caracteristicas),
    )

    # ------------------------------------------------------------------ 4
    otra = _permutar(obs, "pp_7", random.Random("H4.1|0|pp_7|0"))
    distinta = _permutar(obs, "pp_7", random.Random("H4.1|0|pp_7|1"))
    r.comprobar(
        "4. misma semilla, misma permutacion (CA-3)",
        [o.caracteristicas.get("pp_7") for o in permutadas]
        == [o.caracteristicas.get("pp_7") for o in otra],
        "la semilla se deriva de una cadena; con una tupla cambiaria en cada proceso",
    )
    r.comprobar(
        "   y semillas distintas dan permutaciones distintas",
        [o.caracteristicas.get("pp_7") for o in permutadas]
        != [o.caracteristicas.get("pp_7") for o in distinta],
    )

    # ------------------------------------------------------------------ 5
    r.comprobar("5. las columnas se leen por nombre (CA-6)", columnas_de(obs) == ["pp_7", "tmax_3"])

    # ------------------------------------------------------------------ 6
    resultado = importancia(
        TipoEvento.LLUVIA_INTENSA,
        filas,
        {"juguete": SoloMiraUna},
        caracteristicas,
        pliegues=pliegues,
        repeticiones=5,
    )
    porcolumna = {c.nombre: c for c in resultado[0].permutacion}
    r.comprobar(
        "6. la columna que el modelo usa pesa y la que ignora no",
        porcolumna["util"].media > 0.2 and abs(porcolumna["ruido"].media) < 1e-12,
        f"util {porcolumna['util'].media:.3f}, ruido {porcolumna['ruido'].media:.3f}",
    )

    # ------------------------------------------------------------------ 7
    r.comprobar(
        "7. hay un valor por PLIEGUE, no uno por repeticion (CA-4)",
        all(len(c.por_pliegue) == 1 for c in resultado[0].permutacion),
        "mezclarlos confundiria «varia en el tiempo» con «faltan repeticiones»",
    )

    # ------------------------------------------------------------------ 8
    al_reves = importancia(
        TipoEvento.LLUVIA_INTENSA,
        filas,
        {"al reves": SeEquivocaConLaColumna},
        caracteristicas,
        pliegues=pliegues,
        repeticiones=5,
    )
    caida = {c.nombre: c.media for c in al_reves[0].permutacion}["util"]
    r.comprobar(
        "8. una caida negativa NO se recorta a cero (CA-5)",
        caida < 0,
        f"quedo {caida:.3f}: el modelo usaba la columna en contra, y se ve",
    )

    # ------------------------------------------------------------------ 9
    espia = SoloMiraUna()
    importancia(
        TipoEvento.LLUVIA_INTENSA,
        filas,
        {"juguete": lambda: espia},
        caracteristicas,
        pliegues=pliegues,
        repeticiones=2,
    )
    vistas = {o.fecha for lista in espia.vistas_al_predecir for o in lista}
    pliegue = pliegues[0]
    r.comprobar(
        "9. se permuta sobre PRUEBA y nunca sobre entrenamiento (CA-2)",
        bool(vistas)
        and all(pliegue.prueba[0] <= f <= pliegue.prueba[1] for f in vistas)
        and not any(pliegue.entrenamiento[0] <= f <= pliegue.entrenamiento[1] for f in vistas),
        f"{len(vistas)} fechas, todas dentro de {pliegue.prueba[0]}..{pliegue.prueba[1]}",
    )

    # ------------------------------------------------------------------ 10
    #
    # La que mas vale. Ver el encabezado.
    # Se usa `Memorion` y no el juguete a proposito: el juguete acierta todo y
    # da 1.0 en cualquier particion, asi que una coincidencia entre [1.0] y [1.0]
    # no distinguiria dos particiones distintas. `Memorion` sobreajusta, asi que
    # su F1 **depende** de donde cae el corte y sirve de huella.
    tabla = comparar(
        TipoEvento.LLUVIA_INTENSA,
        filas,
        {"memorion": Memorion},
        caracteristicas,
        pliegues=pliegues,
    )
    de_comparar = next(t.por_pliegue for t in tabla if t.nombre == "memorion")
    de_importancia = importancia(
        TipoEvento.LLUVIA_INTENSA,
        filas,
        {"memorion": Memorion},
        caracteristicas,
        pliegues=pliegues,
        repeticiones=1,
    )[0].referencia_por_pliegue
    r.comprobar(
        "10. los pliegues son LOS MISMOS que los de comparar() (CA-1)",
        de_comparar == de_importancia and de_comparar != [1.0],
        f"{de_comparar} contra {de_importancia}",
    )

    # ------------------------------------------------------------------ 11
    r.comprobar(
        "11. la sequia no produce tabla (CA-9)",
        importancia(
            TipoEvento.SEQUIA,
            filas,
            {"juguete": SoloMiraUna},
            caracteristicas,
            pliegues=pliegues,
        )
        == [],
        "esta en NO_MODELABLES por D-34; inventarle una tabla contradice a H3.0",
    )

    # ------------------------------------------------------------------ 12
    debil = ImportanciaColumna("b", [0.05, -0.02, 0.09])
    fuerte = ImportanciaColumna("a", [0.50, 0.48, 0.52])
    contraria = ImportanciaColumna("c", [-0.40, -0.42, -0.38])
    r.comprobar(
        "12. no se afirma por debajo del ruido propio, y el signo no decide",
        fuerte.distinguible and not debil.distinguible and contraria.distinguible,
        "la regla del veredicto de H3.6, aplicada a una columna",
    )

    # ------------------------------------------------------------------ 12b
    #
    # Que `ninguna_distinguible` mire TODAS las columnas y no solo las que la
    # tabla imprime. La primera corrida real dejo ver el problema al reves: el
    # unico bloque con una columna distinguible era el unico cuyas diez primeras
    # decian `no`, porque esa columna tenia media negativa y quedaba al fondo del
    # orden. La tabla escondia el unico hallazgo.
    lista = [ImportanciaColumna(f"c{i}", [0.001, 0.002]) for i in range(12)]
    lista.append(ImportanciaColumna("escondida", [-0.30, -0.31]))
    est = type(al_reves[0])(
        nombre="x", referencia_por_pliegue=[0.5], permutacion=sorted(lista, key=lambda c: -c.media)
    )
    r.comprobar(
        "12b. una distinguible de media negativa no se pierde al final del orden",
        not est.ninguna_distinguible and est.permutacion[-1].nombre == "escondida",
        "queda ultima al ordenar por media, y aun asi tiene que contarse",
    )

    # ------------------------------------------------------------------ 13
    #
    # SABOTAJE: la permutacion no permuta.
    import backend.modelado.importancia as modulo

    original = modulo._permutar
    modulo._permutar = lambda observaciones, columna, generador: list(observaciones)
    try:
        inmovil = importancia(
            TipoEvento.LLUVIA_INTENSA,
            filas,
            {"juguete": SoloMiraUna},
            caracteristicas,
            pliegues=pliegues,
            repeticiones=3,
        )
    finally:
        modulo._permutar = original

    todas_cero = all(v == 0.0 for c in inmovil[0].permutacion for v in c.por_pliegue)
    r.comprobar(
        "13. SABOTAJE: sin permutar de verdad, toda caida es CERO exacto",
        todas_cero,
        "si no diera cero, parte de cada «importancia» seria el azar del modelo",
    )

    # ------------------------------------------------------------------ 14
    #
    # SABOTAJE: la fuga que CA-2 prohibe. La prueba se solapa con el
    # entrenamiento, y el F1 de referencia sube. **El error mejora el numero**, y
    # por eso no se ve en ninguna metrica.
    con_fuga = [
        Pliegue(
            indice=0,
            entrenamiento=(INICIO, INICIO + timedelta(days=DIAS - 1)),
            prueba=(INICIO, INICIO + timedelta(days=DIAS - 1)),
            embargo=None,
        )
    ]

    def referencia(pliegues_usados):
        salida = importancia(
            TipoEvento.LLUVIA_INTENSA,
            filas,
            {"memorion": Memorion},
            caracteristicas,
            pliegues=pliegues_usados,
            repeticiones=1,
        )
        valores = salida[0].referencia_por_pliegue
        return sum(valores) / len(valores) if valores else 0.0

    limpio = referencia(pliegues)
    sucio = referencia(con_fuga)
    r.comprobar(
        "14. SABOTAJE: con fuga el F1 SUBE, y por eso el error no se ve",
        sucio > limpio,
        f"limpio {limpio:.3f}, con fuga {sucio:.3f}. "
        "Un modelo que sobreajusta premia la fuga; la proteccion de CA-2 no es decorativa",
    )

    return r


def main() -> int:
    resultado = verificar()
    print(f"\n{resultado.hechos - len(resultado.fallos)} de {resultado.hechos} comprobaciones")
    if resultado.fallos:
        print("\nNO se cumplen:")
        for f in resultado.fallos:
            print(f"  - {f}")
        print()
        return 1
    print(
        "\nEl arnes de H4.1 cumple. Lo que NO comprueba este verificador:\n"
        "la corrida real, que necesita etiquetas.csv y caracteristicas.csv.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
