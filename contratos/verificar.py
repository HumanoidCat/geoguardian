"""
Verifica que los simulados sigan cumpliendo los contratos congelados.

Lo corre el CI en cada push. Es la red de seguridad mas importante del proyecto:
si alguien cambia un contrato sin actualizar su simulado, tres personas quedan
bloqueadas sin saber por que. Esto lo detecta en el momento.

Uso:  python -m contratos.verificar
"""

from __future__ import annotations

import logging
import sys
from datetime import date, timedelta

logging.basicConfig(level=logging.ERROR)

fallos: list[str] = []


def comprobar(descripcion: str, condicion: bool) -> None:
    estado = "OK  " if condicion else "FALLO"
    print(f"  {estado}  {descripcion}")
    if not condicion:
        fallos.append(descripcion)


def main() -> int:
    from . import VERSION_CONTRATOS
    from .enums import Algoritmo, NivelRiesgo, TipoEvento
    from .esquemas import MedicionDiaria, MetricasModelo, Riesgo
    from .fuentes import ExtractorClima, ExtractorFocosCalor
    from .modelado import Estimador, Evaluador
    from .repositorio import Repositorio
    from .senales import ProcesadorSenales
    from .simulados.datos import (
        ExtractorClimaSimulado,
        ExtractorFocosSimulado,
        RepositorioSimulado,
        salud_simulada,
    )
    from .simulados.modelado import EstimadorSimulado, EvaluadorSimulado
    from .simulados.senales import ProcesadorSenalesSimulado

    print(f"\nContratos version {VERSION_CONTRATOS}\n")

    print("Los simulados cumplen los protocolos:")
    repo = RepositorioSimulado()
    clima = ExtractorClimaSimulado()
    focos = ExtractorFocosSimulado()
    comprobar("RepositorioSimulado cumple Repositorio", isinstance(repo, Repositorio))
    comprobar("ExtractorClimaSimulado cumple ExtractorClima", isinstance(clima, ExtractorClima))
    comprobar(
        "ExtractorFocosSimulado cumple ExtractorFocosCalor", isinstance(focos, ExtractorFocosCalor)
    )
    senales = ProcesadorSenalesSimulado()
    estimador = EstimadorSimulado(Algoritmo.RANDOM_FOREST, TipoEvento.SEQUIA)
    linea_base = EstimadorSimulado(Algoritmo.LINEA_BASE, TipoEvento.SEQUIA)
    evaluador = EvaluadorSimulado()
    comprobar(
        "ProcesadorSenalesSimulado cumple ProcesadorSenales",
        isinstance(senales, ProcesadorSenales),
    )
    comprobar("EstimadorSimulado cumple Estimador", isinstance(estimador, Estimador))
    comprobar("EvaluadorSimulado cumple Evaluador", isinstance(evaluador, Evaluador))

    print("\nLos datos faltantes son representables:")
    m = MedicionDiaria(codigo_distrito="50801", fecha=date(2026, 1, 1), precipitacion_mm=0.0)
    comprobar("cero milimetros de lluvia se conserva como 0.0", m.precipitacion_mm == 0.0)
    comprobar("una variable sin dato queda en None", m.temp_max_c is None)
    serie = repo.obtener_mediciones("50801", date(2026, 1, 1), date(2026, 1, 31))
    comprobar("la serie devuelve un registro por dia, huecos incluidos", len(serie) == 31)
    comprobar("hay huecos representados como None", any(x.temp_max_c is None for x in serie))

    print("\nLo que aun no existe se reporta vacio, no inventado:")
    r = Riesgo(codigo_distrito="50801", fecha=date(2026, 1, 1), tipo_evento=TipoEvento.SEQUIA)
    comprobar("un riesgo sin modelo tiene nivel None", r.nivel is None)
    comprobar("un riesgo sin modelo tiene probabilidad None", r.probabilidad is None)
    comprobar("sin modelos entrenados no hay metricas", repo.listar_metricas() == [])
    comprobar(
        "la salud simulada no declara ingesta previa", salud_simulada().ultima_ingesta is None
    )

    print("\nEl procesamiento de senales no rellena huecos:")
    con_hueco: list[float | None] = [1.0, None, 3.0, 4.0, None, 6.0]
    filtrada = senales.filtrar_ruido(con_hueco, 3)
    comprobar(
        "un hueco que entra al filtro sale como hueco",
        [i for i, v in enumerate(filtrada) if v is None] == [1, 4],
    )
    try:
        senales.espectro(con_hueco, 1.0)
        espectro_rechaza = False
    except ValueError:
        espectro_rechaza = True
    comprobar("el espectro rechaza una serie con huecos", espectro_rechaza)
    indice = senales.spi([float(i % 30) for i in range(60)], 3)
    comprobar("el SPI deja en None lo que no puede calcular", indice[:3] == [None, None, None])
    comprobar(
        "una ventana mayoritariamente vacia no se promedia",
        senales.remuestrear([1.0, None, None, None], 4, "media") == [None],
    )

    print("\nNo hay estimacion sin modelo detras:")
    comprobar("un estimador recien creado no esta entrenado", estimador.entrenado() is False)
    try:
        estimador.predecir([{"lluvia": 1.0}])
        sin_entrenar_falla = False
    except RuntimeError:
        sin_entrenar_falla = True
    comprobar("predecir sin entrenar lanza RuntimeError", sin_entrenar_falla)

    caracteristicas = [
        {"mes": float((i % 12) + 1), "lluvia": float(i % 7), "temp": 20.0 + i % 5}
        for i in range(120)
    ]
    etiquetas = [[NivelRiesgo.BAJO, NivelRiesgo.MEDIO, NivelRiesgo.ALTO][i % 3] for i in range(120)]
    fechas = [date(2020, 1, 1) + timedelta(days=i) for i in range(120)]

    linea_base.entrenar(caracteristicas, etiquetas)
    estimador.entrenar(caracteristicas, etiquetas)
    comprobar(
        "la linea base ignora las caracteristicas y solo mira el mes",
        linea_base.predecir([{"mes": 3.0, "lluvia": 0.0, "temp": 15.0}])
        == linea_base.predecir([{"mes": 3.0, "lluvia": 999.0, "temp": 99.0}]),
    )
    comprobar(
        "la linea base declara que no explica, con None",
        linea_base.explicar({"mes": 3.0, "lluvia": 1.0}) is None,
    )

    print("\nLa validacion temporal no admite fuga:")
    metricas = evaluador.validar_ventana_expansiva(estimador, caracteristicas, etiquetas, fechas, 3)
    comprobar("la ventana expansiva produce metricas", metricas.f1_macro is not None)
    desordenadas = fechas[60:] + fechas[:60]
    try:
        evaluador.validar_ventana_expansiva(estimador, caracteristicas, etiquetas, desordenadas, 3)
        rechaza_desorden = False
    except ValueError:
        rechaza_desorden = True
    comprobar("una particion fuera de orden temporal es rechazada", rechaza_desorden)

    peor = MetricasModelo(
        algoritmo=Algoritmo.RANDOM_FOREST, tipo_evento=TipoEvento.SEQUIA, version="x", f1_macro=0.20
    )
    mejor = MetricasModelo(
        algoritmo=Algoritmo.LINEA_BASE, tipo_evento=TipoEvento.SEQUIA, version="x", f1_macro=0.55
    )
    supera, _ = evaluador.comparar_con_linea_base(peor, mejor)
    comprobar("no superar la linea base es un resultado, no una excepcion", supera is False)

    print("\nEl modo simulado es visible:")
    comprobar("la API expone modo simulado", salud_simulada().modo.value == "simulado")

    print("\nEl vocabulario del dominio esta cerrado:")
    comprobar("tres niveles de riesgo", len(list(NivelRiesgo)) == 3)
    comprobar("tres tipos de evento", len(list(TipoEvento)) == 3)

    distritos = repo.listar_distritos()
    comprobar("ocho distritos cargados", len(distritos) == 8)

    # Incidencia I-04: hasta la version 1.2.0 los simulados usaban 50501-50508,
    # que es el canton de Carrillo. Tilaran es 5 = Guanacaste, 08 = Tilaran.
    # El error no lo detecto nadie porque el resto de las comprobaciones miran
    # estructura, no si el valor existe en el mundo. Esta si lo mira.
    codigos = sorted(d.codigo for d in distritos)
    comprobar(
        "los codigos son del canton de Tilaran (508xx)",
        all(c.startswith("508") for c in codigos),
    )
    comprobar(
        "los ocho codigos son 50801 a 50808 y no se repiten",
        codigos == [f"508{n:02d}" for n in range(1, 9)],
    )

    if fallos:
        print(f"\n{len(fallos)} verificaciones fallaron:")
        for f in fallos:
            print(f"  - {f}")
        return 1
    print("\nTodas las verificaciones pasaron.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
