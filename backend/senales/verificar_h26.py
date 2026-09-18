"""Comprueba los criterios de H2.6 contra la matriz real.

===========================================================================
QUE COMPRUEBA ESTE GUION Y QUE COMPRUEBA `pytest`
===========================================================================

`test_redundancia.py` prueba la **logica** sobre series construidas a mano: no
necesita base, no necesita matriz y corre en decimas de segundo. Es el CA-12.

Este guion prueba los **hallazgos**, y para eso necesita
`datos/procesados/caracteristicas.csv`, que sale de PostgreSQL. Una prueba que
demuestra que el detector funciona no dice nada sobre lo que el detector
encontro; y un hallazgo pegado a mano en un documento no vuelve a comprobarse
nunca.

Por eso los dos sabotajes de aca se plantan sobre **columnas reales** y no
sinteticas: es una comprobacion mas fuerte que la de `pytest`, porque la
distribucion es la de verdad.

    python -m backend.senales.verificar_h26
    python -m backend.senales.verificar_h26 --ca5     # necesita PostgreSQL

Uso en el cierre de la historia: los dos, y la salida va a la evidencia.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.senales.redundancia import (  # noqa: E402
    MATRIZ,
    TOLERANCIA,
    UMBRAL_ALTO,
    como_vectores,
    correlacion,
    correlacion_de_temperaturas,
    filas_completas,
    leer_matriz,
    pares_relacionados,
    variacion_espacial,
)

REDUCIDA = RAIZ / "datos" / "procesados" / "caracteristicas-sin-medias.csv"

#: Los tres pares que la hipotesis declaro ANTES de medir. Se comparan como
#: conjuntos para no depender del orden en que salen del recorrido.
PARES_ESPERADOS = {
    frozenset(("pp_acum3", "pp_media3")),
    frozenset(("pp_acum7", "pp_media7")),
    frozenset(("pp_acum30", "pp_media30")),
}

#: Prefijos que SI distinguen un distrito de otro, y los que no.
#:
#: No es una lista de nombres escrita a mano: es la consecuencia de I-05. La
#: precipitacion viene de CHIRPS, a 0,05 grados, y distingue; las otras tres
#: variables vienen de NASA POWER y los ocho distritos caen en la misma celda.
#: Los estaticos distinguen por construccion y el calendario no, tambien por
#: construccion.
#:
#: SI ESTE CONTROL SE PONE ROJO, NO ES UN DEFECTO: es que la fuente cambio, y
#: eso es un hallazgo que hay que ir a mirar.
DISTINGUEN = ("pp_", "geo_")
NO_DISTINGUEN = ("tmax_", "hr_", "viento_", "cal_")

#: Las que no pueden estar si la matriz salio sin banderas. Los contadores
#: aparecen con `--minimo-observado` y las del indice con `--con-enso`.
PROHIBIDAS = ("_observados", "oni_", "enso_")


class Registro:
    def __init__(self) -> None:
        self.ok = True
        self.lineas: list[str] = []

    def comprobar(self, condicion: bool, criterio: str, titulo: str, detalle: str = "") -> None:
        marca = "ok " if condicion else "MAL"
        if not condicion:
            self.ok = False
        self.lineas.append(f"  [{marca}] {criterio} · {titulo}")
        if detalle:
            for linea in detalle.splitlines():
                self.lineas.append(f"          {linea}")


def verificar(registro: Registro, matriz: Path) -> None:
    columnas, filas = leer_matriz(matriz)
    completas = filas_completas(filas, columnas)

    # --- CA-3: la matriz es la de produccion --------------------------------
    intrusas = sorted(c for c in columnas if any(p in c for p in PROHIBIDAS))
    registro.comprobar(
        not intrusas,
        "CA-3",
        "la matriz salio sin banderas",
        f"columnas {len(columnas)}, filas {len(filas)}"
        + (f"\nintrusas: {', '.join(intrusas)}" if intrusas else ""),
    )

    # --- CA-10: se mide sobre las filas que el modelo usa -------------------
    porcentaje = 100.0 * len(completas) / len(filas) if filas else 0.0
    registro.comprobar(
        bool(completas),
        "CA-10",
        "hay filas completas sobre las que medir",
        f"{len(completas)} de {len(filas)} ({porcentaje:.1f} %)",
    )

    # --- CA-2: la variacion espacial, por prefijo ---------------------------
    espacial = variacion_espacial(filas, columnas)
    fallan_distinguen = sorted(
        c for c in columnas if c.startswith(DISTINGUEN) and espacial.get(c, (0, 0))[0] == 0
    )
    fallan_no = sorted(
        c for c in columnas if c.startswith(NO_DISTINGUEN) and espacial.get(c, (0, 0))[0] > 0
    )
    cuantas_distinguen = sum(1 for c in columnas if espacial.get(c, (0, 0))[0] > 0)
    registro.comprobar(
        not fallan_distinguen and not fallan_no,
        "CA-2",
        "cada columna distingue distritos o no segun su fuente (I-05)",
        f"distinguen {cuantas_distinguen} de {len(columnas)}"
        + (
            f"\nesperaba que distinguieran: {', '.join(fallan_distinguen)}"
            if fallan_distinguen
            else ""
        )
        + (f"\nesperaba que NO distinguieran: {', '.join(fallan_no)}" if fallan_no else ""),
    )

    # --- CA-6 y CA-7: los tres pares exactos --------------------------------
    vectores = como_vectores(completas, columnas)
    exactos, altos = pares_relacionados(vectores, columnas, UMBRAL_ALTO, TOLERANCIA)
    encontrados = {frozenset((p.a, p.b)) for p in exactos}
    registro.comprobar(
        encontrados == PARES_ESPERADOS,
        "CA-6",
        "los tres pares exactos son los declarados en la hipotesis, y solo esos",
        "\n".join(f"{p.relacion()}   residuo {p.residuo:.2e}" for p in exactos)
        or "no se encontro ninguno",
    )
    registro.comprobar(
        all(p.residuo < TOLERANCIA for p in exactos),
        "CA-7",
        "la relacion afin se cumple fila por fila, no en promedio",
        f"peor residuo {max((p.residuo for p in exactos), default=0.0):.2e} "
        f"contra tolerancia {TOLERANCIA:.0e}",
    )

    # --- CA-6: exacto y alto son dos listas, no una -------------------------
    en_altos = {frozenset((p.a, p.b)) for p in altos}
    registro.comprobar(
        not (encontrados & en_altos),
        "CA-6",
        "ningun par exacto se cuenta tambien como alto",
        f"{len(altos)} pares altos con |r| >= {UMBRAL_ALTO}",
    )

    # --- CA-7: el limite declarado del metodo -------------------------------
    calendario = frozenset(("cal_seno", "cal_coseno"))
    registro.comprobar(
        calendario not in encontrados and calendario not in en_altos,
        "CA-7",
        "el par del calendario NO aparece: la correlacion no ve lo no lineal",
        "sen^2 + cos^2 = 1 es dependencia perfecta y su correlacion lineal no lo es. "
        f"r medido: {correlacion(vectores['cal_seno'], vectores['cal_coseno']):+.4f}",
    )

    # --- CA-11: sabotaje sobre una columna REAL -----------------------------
    #
    # Mas fuerte que el de `pytest`, que planta la copia sobre una serie
    # sintetica: aca la distribucion es la de la matriz de verdad.
    testigo = "tmax_rez1"
    acompanantes = [c for c in ("hr_rez1", "geo_lat") if c in columnas]
    plantada = dict(vectores)
    plantada["SABOTAJE_copia"] = list(vectores[testigo])
    sub = [testigo, "SABOTAJE_copia", *acompanantes]
    saboteados, _ = pares_relacionados(plantada, sub, UMBRAL_ALTO, TOLERANCIA)
    registro.comprobar(
        frozenset((testigo, "SABOTAJE_copia")) in {frozenset((p.a, p.b)) for p in saboteados},
        "CA-11",
        f"una copia exacta de `{testigo}` se detecta",
        f"plantada sobre {len(completas)} filas reales",
    )

    # --- CA-11: sabotaje inverso -------------------------------------------
    barajada = list(vectores[testigo])
    random.Random("H2.6").shuffle(barajada)
    rota = dict(vectores)
    rota["SABOTAJE_barajada"] = barajada
    sub_rota = [testigo, "SABOTAJE_barajada", *acompanantes]
    sin_relacion, altos_rota = pares_relacionados(rota, sub_rota, UMBRAL_ALTO, TOLERANCIA)
    par_roto = frozenset((testigo, "SABOTAJE_barajada"))
    registro.comprobar(
        par_roto not in {frozenset((p.a, p.b)) for p in sin_relacion}
        and par_roto not in {frozenset((p.a, p.b)) for p in altos_rota},
        "CA-11",
        "barajada, la misma columna deja de detectarse",
        "un detector que encuentra siempre y uno que no encuentra nunca se ven "
        "igual en una sola corrida",
    )

    # --- CA-8: la matriz reducida existe y es la que se midio ---------------
    if not REDUCIDA.exists():
        registro.comprobar(
            False,
            "CA-8",
            "falta la matriz reducida del antes/despues",
            "python -m backend.senales.redundancia --escribir-sin "
            f"pp_media3,pp_media7,pp_media30 --destino {REDUCIDA}",
        )
        return
    columnas_r, filas_r = leer_matriz(REDUCIDA)
    quitadas = set(columnas) - set(columnas_r)
    registro.comprobar(
        quitadas == {"pp_media3", "pp_media7", "pp_media30"} and len(filas_r) == len(filas),
        "CA-8",
        "la matriz reducida difiere en las tres columnas y en nada mas",
        f"{len(columnas_r)} columnas, {len(filas_r)} filas\n"
        f"quitadas: {', '.join(sorted(quitadas)) or 'ninguna'}",
    )
    exactos_r, _ = pares_relacionados(
        como_vectores(filas_completas(filas_r, columnas_r), columnas_r),
        columnas_r,
        UMBRAL_ALTO,
        TOLERANCIA,
    )
    registro.comprobar(
        not exactos_r,
        "CA-8",
        "en la matriz reducida no queda ninguna redundancia exacta",
        "\n".join(p.relacion() for p in exactos_r) or "ninguna, que es lo que se buscaba",
    )


def verificar_temperaturas(registro: Registro) -> None:
    """CA-5. Lo unico que necesita PostgreSQL: esas columnas no estan en la matriz."""
    try:
        from basedatos.conexion import conectar
    except ImportError as error:
        registro.comprobar(False, "CA-5", "no se pudo importar la conexion", str(error))
        return
    try:
        conexion = conectar()
    except Exception as error:  # noqa: BLE001
        registro.comprobar(
            False, "CA-5", "la base no responde", f"{error}\nse levanta con: docker compose up -d"
        )
        return
    try:
        medida = correlacion_de_temperaturas(conexion.cursor())
    finally:
        conexion.close()

    registro.comprobar(
        medida["una_sola_serie"],
        "CA-5",
        "las tres temperaturas son una sola serie, no ocho (I-05)",
        f"{medida['dias']} dias; desacuerdos entre distritos: {medida['desacuerdos']}",
    )
    if not medida["una_sola_serie"]:
        return
    series = medida["series"]
    r_max_min = correlacion(series["tmax"], series["tmin"])
    detalle = "\n".join(
        f"{a:<8} {b:<8} r = {correlacion(series[a], series[b]):+.6f}"
        for a, b in (("tmax", "tmin"), ("tmax", "tmedia"), ("tmin", "tmedia"))
    )
    # NO se exige un valor: se exige que el numero EXISTA y quede impreso.
    #
    # Poner aca `assert r < 0.5` seria congelar el hallazgo como si fuera un
    # requisito. El criterio era medirlo y escribir lo que diera; si un dia la
    # fuente cambia y la correlacion sube, este control tiene que seguir pasando
    # y el numero nuevo tiene que verse.
    registro.comprobar(
        r_max_min is not None,
        "CA-5",
        "la frase «casi perfectamente correlacionadas» tiene su cifra",
        detalle
        + (
            "\nLa maxima y la minima NO estan correlacionadas: el descarte de "
            "temp_min_c no se sostiene con este argumento."
            if abs(r_max_min) < 0.5
            else "\nLa correlacion subio respecto de la corrida del 2026-09-17: ir a mirar."
        ),
    )


def main() -> int:
    p = argparse.ArgumentParser(description="Criterios de H2.6 contra la matriz real.")
    p.add_argument("--matriz", type=Path, default=MATRIZ)
    p.add_argument("--ca5", action="store_true", help="tambien las temperaturas, contra la base")
    args = p.parse_args()

    if not args.matriz.exists():
        print(f"\nNo encuentro {args.matriz}.")
        print("\n  Se produce con la base levantada:")
        print("    python -m backend.modelado.generar_caracteristicas\n")
        return 1

    registro = Registro()
    print("\nVerificacion de H2.6 · la seleccion de variables, medida\n")
    verificar(registro, args.matriz)
    if args.ca5:
        verificar_temperaturas(registro)

    print("\n".join(registro.lineas))
    print()
    if registro.ok:
        print("  Todas las comprobaciones pasan.")
        if not args.ca5:
            print("  Falta CA-5: corre con --ca5 y la base levantada.")
    else:
        print("  Hay comprobaciones en rojo. El detalle esta arriba.")
    print()
    return 0 if registro.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
