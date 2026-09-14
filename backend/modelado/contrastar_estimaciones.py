"""Contrasta las estimaciones PUBLICADAS contra el catalogo historico. Historia H4.4.

QUE PREGUNTA RESPONDE

Cuando en Tilaran ocurrio de verdad un evento con danos registrados, que decia la
estimacion publicada para ese distrito y esa fecha.

NO responde si el modelo es bueno. Lo que el sitio publica es una linea base
climatologica (D-39), no un modelo entrenado.

POR QUE CONTRA LA API Y NO CONTRA UNA COPIA LOCAL

Porque lo que se defiende es lo que el sitio contesta. Correr el escritor otra vez
en local daria un numero parecido y no seria el mismo hecho: es I-38, donde una
corrida que debia ir contra la nube salio contra la base local y las cifras
coincidian igual.

Cada fila leida se guarda con su `algoritmo` y su `version_modelo`. Si aparece mas
de un escritor, el informe lo declara y no promedia.

EL ESCRITOR NO SE SUPONE, SE LE PREGUNTA

`LineaBaseClimatologica.predecir` indexa por (codigo_distrito, mes): 96 celdas, y
su estimacion es la misma todos los dias de un mes. Sobre un escritor asi, la
ventana de +-7 dias que uso H4.4a contra el etiquetado no mide nada.

Pero incendio lo escribe otro (D-42, y H3.9 lo mueve otra vez), y ese si cambia
dia a dia. Asi que el supuesto se comprueba por evento, leyendo `algoritmo` y
consultando dos fechas del mismo mes:

    climatologico y constante   -> se agrega por celda distrito-mes
    climatologico y NO constante -> se detiene: el metodo no aplica (codigo 1)
    cualquier otro escritor      -> no se agrega, y la tasa base se llama
                                    «muestra declarada de doce fechas»

Es CA-6, y sale de la regla que dejo I-54: antes de explicar una medicion se le
pregunta al sistema si el supuesto se sostiene.

QUE NO HACE

No entrena, no reentrena, no compara algoritmos -D-51 lo acoto y el arnes de H3.9
ya publico esa comparacion-, no escribe una sola fila en `analitico.riesgo`
(D-48) y no toca el catalogo, que es de Luna.

Criterios: docs/evidencias/objetivos/H4.4-criterios-aceptacion.md

    python -m backend.modelado.contrastar_estimaciones
    python -m backend.modelado.contrastar_estimaciones --json informe.json
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

CATALOGO = RAIZ / "docs" / "investigacion" / "catalogo-eventos.csv"
DOMINIO = "https://visor-production-40b5.up.railway.app"

#: La serie climatica empieza en 1991 (H1.1). Antes de eso no hay que contrastar.
PRIMER_ANIO = 1991

#: La sequia no se modela (D-34): sus registros no tienen estimacion que contrastar.
SIN_ESTIMACION_POR_DECISION = {"sequia": "D-34: la sequia no se modela"}

#: El escritor climatologico, el unico para el que vale agregar por celda.
CLIMATOLOGICO = "linea_base_climatologica"

#: Dias del mes con los que se comprueba la constancia dentro del mes (CA-6).
DIAS_DE_PRUEBA = (5, 15, 20)

TIEMPO_LIMITE = 20


# --------------------------------------------------------------------------- #
# Lectura                                                                       #
# --------------------------------------------------------------------------- #


@dataclass
class Cliente:
    """Pide filas a la API publicada y recuerda lo que ya pidio.

    El contador de peticiones no es adorno: el informe lo declara para que
    cualquiera sepa cuanto cuesta repetir la medicion.
    """

    dominio: str = DOMINIO
    peticiones: int = 0
    memoria: dict[tuple[str, str], list[dict]] = field(default_factory=dict)

    def riesgos(self, fecha: str, tipo: str) -> list[dict]:
        clave = (fecha, tipo)
        if clave in self.memoria:
            return self.memoria[clave]

        url = f"{self.dominio}/api/riesgos?fecha={fecha}&tipo_evento={tipo}"
        self.peticiones += 1
        try:
            with urllib.request.urlopen(url, timeout=TIEMPO_LIMITE) as respuesta:
                filas = json.loads(respuesta.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError) as causa:
            raise SystemExit(f"No se pudo consultar {url}\n  {causa}") from causa

        self.memoria[clave] = filas
        return filas


def leer_catalogo(ruta: Path = CATALOGO) -> list[dict]:
    with ruta.open(encoding="utf-8-sig") as archivo:
        return list(csv.DictReader(archivo))


def separar(registros: list[dict]) -> tuple[list[dict], list[tuple[dict, str]]]:
    """Parte el catalogo en contrastables y excluidos, con el motivo de cada exclusion.

    Los motivos se declararon en CA-2 antes de contarlos. Si las cuentas no dan lo
    que ahi se esperaba, manda esta medicion y la diferencia se explica.
    """
    contrastables: list[dict] = []
    excluidos: list[tuple[dict, str]] = []

    for registro in registros:
        tipo = registro["tipo_evento"]
        fecha = registro["fecha_inicio"]

        if tipo in SIN_ESTIMACION_POR_DECISION:
            excluidos.append((registro, SIN_ESTIMACION_POR_DECISION[tipo]))
        elif int(fecha[:4]) < PRIMER_ANIO:
            excluidos.append((registro, f"anterior a {PRIMER_ANIO}, fuera de la serie"))
        else:
            contrastables.append(registro)

    return contrastables, excluidos


# --------------------------------------------------------------------------- #
# El escritor                                                                   #
# --------------------------------------------------------------------------- #


def fila_de(filas: list[dict], codigo: str) -> dict | None:
    for fila in filas:
        if fila["codigo_distrito"] == codigo:
            return fila
    return None


def escritores(filas: list[dict]) -> set[tuple[str, str]]:
    """(algoritmo, version_modelo) de las filas que tienen estimacion."""
    return {(f["algoritmo"], f["version_modelo"]) for f in filas if f.get("nivel") is not None}


def constancia_dentro_del_mes(
    cliente: Cliente, tipo: str, anio: int, meses: list[int]
) -> tuple[bool, list[str]]:
    """Compara varias fechas del mismo mes. Devuelve (es_constante, detalles).

    Comparar `nivel` no alcanza: dos dias pueden coincidir de nivel y diferir de
    probabilidad, y entonces el escritor tampoco es constante.
    """
    detalles: list[str] = []
    constante = True

    for mes in sorted(set(meses)):
        vistas: dict[str, tuple] = {}
        for dia in DIAS_DE_PRUEBA:
            fecha = f"{anio:04d}-{mes:02d}-{dia:02d}"
            filas = cliente.riesgos(fecha, tipo)
            huella = tuple((f["codigo_distrito"], f["nivel"], f["probabilidad"]) for f in filas)
            vistas[fecha] = huella

        distintas = set(vistas.values())
        if len(distintas) > 1:
            constante = False
            fechas = ", ".join(vistas)
            detalles.append(f"mes {mes:02d}: las fechas {fechas} NO dan la misma estimacion")

    return constante, detalles


def tabla_base(cliente: Cliente, tipo: str, anio: int) -> tuple[list[dict], dict]:
    """Las 96 celdas del escritor: doce fechas, ocho distritos cada una.

    El denominador de la tasa son las celdas CON estimacion. Las celdas sin
    estimacion se cuentan aparte y no se rellenan: es D-07, y con incendio son
    cinco distritos de ocho por D-25.
    """
    celdas: list[dict] = []
    for mes in range(1, 13):
        fecha = f"{anio:04d}-{mes:02d}-15"
        for fila in cliente.riesgos(fecha, tipo):
            celdas.append({"mes": mes, **fila})

    con_estimacion = [c for c in celdas if c["nivel"] is not None]
    altos = [c for c in con_estimacion if c["nivel"] == "alto"]
    resumen = {
        "anio_de_referencia": anio,
        "celdas": len(celdas),
        "con_estimacion": len(con_estimacion),
        "sin_estimacion": len(celdas) - len(con_estimacion),
        "altos": len(altos),
        "tasa_alto": len(altos) / len(con_estimacion) if con_estimacion else None,
    }
    return celdas, resumen


def wilson(exitos: int, intentos: int, z: float = 1.96) -> tuple[float, float] | None:
    """Intervalo de Wilson al 95 %. Sin dependencias: son cuatro operaciones.

    Una cobertura sobre 34 eventos sin intervalo invita a leer diferencias que el
    tamano de la muestra no sostiene. El documento tecnico ya usa Wilson en la
    tabla XVI; aqui se usa el mismo.
    """
    if intentos == 0:
        return None
    p = exitos / intentos
    denominador = 1 + z**2 / intentos
    centro = (p + z**2 / (2 * intentos)) / denominador
    radio = z * math.sqrt(p * (1 - p) / intentos + z**2 / (4 * intentos**2)) / denominador
    return (max(0.0, centro - radio), min(1.0, centro + radio))


def tasa_por_mes(celdas: list[dict]) -> dict[int, float]:
    """P(`alto`) de cada mes calendario sobre los distritos que tienen estimacion."""
    tasas: dict[int, float] = {}
    for mes in range(1, 13):
        del_mes = [c for c in celdas if c["mes"] == mes and c["nivel"] is not None]
        if del_mes:
            tasas[mes] = sum(1 for c in del_mes if c["nivel"] == "alto") / len(del_mes)
    return tasas


def analisis_de_fallos(medidos: list[dict], celdas: list[dict]) -> dict:
    """Lo que la cobertura sola no dice. Es la segunda mitad del titulo de H4.4.

    Tres cosas, y ninguna cambia el realce declarado en CA-4:

    1. El intervalo de la cobertura, porque 34 eventos son pocos.
    2. Un denominador **pareado por mes**: los eventos del catalogo se concentran
       en setiembre y octubre, y CA-4 ya lo anticipaba. Comparar contra el
       promedio de los doce meses mezcla esa concentracion con el resultado.
    3. Cuantos eventos cayeron en una celda donde el escritor da P(alto) = 0, o
       sea donde el almanaque dice que eso no pasa y sin embargo paso.
    """
    con_estimacion = [m for m in medidos if m["categoria"] != "sin estimacion"]
    anticipados = sum(1 for m in medidos if m["categoria"] == "anticipado")

    por_mes = tasa_por_mes(celdas)
    esperados = sum(por_mes.get(int(m["fecha"][5:7]), 0.0) for m in con_estimacion)

    imposibles = [m for m in con_estimacion if m["probabilidad"] == 0.0]

    return {
        "intervalo_cobertura": wilson(anticipados, len(con_estimacion)),
        "tasa_por_mes": por_mes,
        "esperados_pareado_por_mes": esperados,
        "observados": anticipados,
        "realce_pareado": (anticipados / esperados) if esperados else None,
        "eventos_en_celda_imposible": [
            {"fecha": m["fecha"], "codigo_distrito": m["codigo_distrito"]} for m in imposibles
        ],
    }


# --------------------------------------------------------------------------- #
# El contraste                                                                  #
# --------------------------------------------------------------------------- #

#: Las categorias se declararon en CA-7 antes de mirar un solo evento.
CATEGORIAS = ("anticipado", "medio", "no anticipado", "sin estimacion")


def categoria_de(fila: dict | None) -> str:
    if fila is None or fila.get("nivel") is None:
        return "sin estimacion"
    if fila["nivel"] == "alto":
        return "anticipado"
    if fila["nivel"] == "medio":
        return "medio"
    return "no anticipado"


def contrastar(cliente: Cliente, registros: list[dict], tipo: str) -> dict:
    eventos = [r for r in registros if r["tipo_evento"] == tipo]
    if not eventos:
        return {"tipo": tipo, "eventos": [], "nota": "sin registros contrastables"}

    medidos = []
    for registro in eventos:
        fecha = registro["fecha_inicio"]
        codigo = registro["codigo_distrito"]
        fila = fila_de(cliente.riesgos(fecha, tipo), codigo)
        medidos.append(
            {
                "fecha": fecha,
                "codigo_distrito": codigo,
                "nivel": None if fila is None else fila["nivel"],
                "probabilidad": None if fila is None else fila["probabilidad"],
                "algoritmo": None if fila is None else fila["algoritmo"],
                "version_modelo": None if fila is None else fila["version_modelo"],
                "categoria": categoria_de(fila),
                "descripcion": registro["descripcion"][:90],
            }
        )

    anio = max(int(m["fecha"][:4]) for m in medidos)
    meses = [int(m["fecha"][5:7]) for m in medidos]

    vistos = {(m["algoritmo"], m["version_modelo"]) for m in medidos if m["algoritmo"]}
    es_climatologico = bool(vistos) and all(a == CLIMATOLOGICO for a, _ in vistos)

    constante, detalles = constancia_dentro_del_mes(cliente, tipo, anio, meses)
    celdas, base = tabla_base(cliente, tipo, anio)

    con_estimacion = [m for m in medidos if m["categoria"] != "sin estimacion"]
    anticipados = [m for m in medidos if m["categoria"] == "anticipado"]
    cobertura = len(anticipados) / len(con_estimacion) if con_estimacion else None
    realce = None
    if cobertura is not None and base["tasa_alto"]:
        realce = cobertura / base["tasa_alto"]

    return {
        "tipo": tipo,
        "eventos": medidos,
        "escritores": sorted(f"{a} · {v}" for a, v in vistos),
        "es_climatologico": es_climatologico,
        "constante_en_el_mes": constante,
        "detalles_de_constancia": detalles,
        "base": base,
        "contrastables": len(medidos),
        "con_estimacion": len(con_estimacion),
        "anticipados": len(anticipados),
        "cobertura": cobertura,
        "realce": realce,
        "conteo": dict(Counter(m["categoria"] for m in medidos)),
        "analisis": analisis_de_fallos(medidos, celdas),
    }


# --------------------------------------------------------------------------- #
# El informe                                                                    #
# --------------------------------------------------------------------------- #


def porcentaje(valor: float | None) -> str:
    return "n/d" if valor is None else f"{valor * 100:.1f} %"


def imprimir(resultado: dict) -> None:
    tipo = resultado["tipo"]
    print()
    print("=" * 78)
    print(f"  {tipo}")
    print("=" * 78)

    if not resultado["eventos"]:
        print(f"  {resultado['nota']}")
        return

    print("\n  Escritor que firma las filas:")
    for escritor in resultado["escritores"] or ["(ninguna fila tiene estimacion)"]:
        print(f"    {escritor}")
    if len(resultado["escritores"]) > 1:
        print("    AVISO: mas de un escritor en la muestra. No se promedia; ver CA-1.")

    print("\n  Supuesto de la celda distrito-mes (CA-6):")
    print(f"    escritor climatologico   {resultado['es_climatologico']}")
    print(f"    constante dentro del mes {resultado['constante_en_el_mes']}")
    for detalle in resultado["detalles_de_constancia"]:
        print(f"      {detalle}")
    if not resultado["es_climatologico"]:
        print("    -> no se agrega por celda; la tasa base es una MUESTRA de doce fechas")

    base = resultado["base"]
    print("\n  Tasa base del mismo escritor (CA-5):")
    print(f"    anio de referencia {base['anio_de_referencia']}")
    print(
        f"    celdas consultadas {base['celdas']}  con estimacion {base['con_estimacion']}"
        f"  sin estimacion {base['sin_estimacion']}"
    )
    print(f"    tasa de `alto`     {porcentaje(base['tasa_alto'])}")

    print("\n  Contraste:")
    print(f"    eventos contrastables {resultado['contrastables']}")
    print(f"    con estimacion        {resultado['con_estimacion']}")
    print(f"    anticipados (`alto`)  {resultado['anticipados']}")
    print(f"    cobertura             {porcentaje(resultado['cobertura'])}")
    realce = resultado["realce"]
    print(f"    REALCE                {'n/d' if realce is None else f'{realce:.2f}x'}")
    print("    (realce 1,00 = la estimacion no distingue un dia con evento de")
    print("     cualquier otro dia del mismo mes)")

    analisis = resultado["analisis"]
    print("\n  Analisis de los fallos:")
    intervalo = analisis["intervalo_cobertura"]
    if intervalo:
        print(
            f"    cobertura con intervalo   {porcentaje(resultado['cobertura'])}"
            f"  (Wilson 95 %: {porcentaje(intervalo[0])} a {porcentaje(intervalo[1])})"
        )
        dentro = intervalo[0] <= base["tasa_alto"] <= intervalo[1]
        veredicto = "DENTRO" if dentro else "FUERA"
        print(f"    la tasa base cae {veredicto} del intervalo de la cobertura")
    print(
        f"    pareado por mes           observados {analisis['observados']}"
        f"  vs esperados {analisis['esperados_pareado_por_mes']:.1f}"
    )
    pareado = analisis["realce_pareado"]
    print(f"    REALCE PAREADO            {'n/d' if pareado is None else f'{pareado:.2f}x'}")
    imposibles = analisis["eventos_en_celda_imposible"]
    print(f"    eventos donde el escritor da P(alto) = 0: {len(imposibles)}")
    for evento in imposibles:
        print(f"      {evento['fecha']}  {evento['codigo_distrito']}")

    print("\n  Evento por evento:")
    print(f"    {'fecha':<12}{'distrito':<10}{'nivel':<14}{'prob':>8}   categoria")
    for evento in sorted(resultado["eventos"], key=lambda e: e["fecha"]):
        probabilidad = evento["probabilidad"]
        texto = "     n/d" if probabilidad is None else f"{probabilidad:8.4f}"
        print(
            f"    {evento['fecha']:<12}{evento['codigo_distrito']:<10}"
            f"{str(evento['nivel']):<14}{texto}   {evento['categoria']}"
        )


def supuesto_roto(resultados: list[dict]) -> list[dict]:
    """Los escritores que se declaran climatologicos y NO son constantes en el mes.

    Vive aparte de `main` a proposito: CA-6 es un control, y un control que nadie
    probo fallando no esta probado. `test_contrastar_estimaciones.py` lo rompe.
    """
    return [r for r in resultados if r.get("es_climatologico") and not r.get("constante_en_el_mes")]


def main() -> int:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("--dominio", default=DOMINIO)
    analizador.add_argument("--json", type=Path, default=None, help="guarda la medicion cruda")
    argumentos = analizador.parse_args()

    cliente = Cliente(dominio=argumentos.dominio)
    registros = leer_catalogo()
    contrastables, excluidos = separar(registros)

    print("Contraste de las estimaciones publicadas contra el catalogo historico")
    print(f"  H4.4 · {date.today().isoformat()}")
    print(f"  catalogo {CATALOGO.relative_to(RAIZ)}: {len(registros)} registros")
    print(f"  dominio  {argumentos.dominio}")

    print(f"\n  Contrastables: {len(contrastables)}")
    print(f"  Excluidos:     {len(excluidos)}")
    for motivo, cuantos in sorted(Counter(m for _, m in excluidos).items()):
        print(f"    {cuantos:>3}  {motivo}")

    tipos = sorted({r["tipo_evento"] for r in contrastables})
    resultados = [contrastar(cliente, contrastables, tipo) for tipo in tipos]
    for resultado in resultados:
        imprimir(resultado)

    print()
    print("=" * 78)
    print(f"  Peticiones a la API: {cliente.peticiones}")
    print("  No se reporta precision: la ausencia en el catalogo no es ausencia de")
    print("  evento, y dividir por las estimaciones daria un numero mal por")
    print("  construccion (CA-9).")

    if supuesto_roto(resultados):
        print("\n  FALLO (CA-6): un escritor declarado climatologico NO es constante")
        print("  dentro del mes. El metodo de este contraste no aplica: no se publica")
        print("  un resultado construido sobre un supuesto falso.")
        return 1

    if argumentos.json:
        argumentos.json.write_text(
            json.dumps(
                {
                    "fecha": date.today().isoformat(),
                    "dominio": argumentos.dominio,
                    "peticiones": cliente.peticiones,
                    "excluidos": [{"registro": r, "motivo": m} for r, m in excluidos],
                    "resultados": resultados,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\n  Medicion cruda en {argumentos.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
