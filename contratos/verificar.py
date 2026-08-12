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
from datetime import date

logging.basicConfig(level=logging.ERROR)

fallos: list[str] = []


def comprobar(descripcion: str, condicion: bool) -> None:
    estado = "OK  " if condicion else "FALLO"
    print(f"  {estado}  {descripcion}")
    if not condicion:
        fallos.append(descripcion)


def main() -> int:
    from . import VERSION_CONTRATOS
    from .enums import NivelRiesgo, TipoEvento
    from .esquemas import MedicionDiaria, Riesgo
    from .fuentes import ExtractorClima, ExtractorFocosCalor
    from .repositorio import Repositorio
    from .simulados.datos import (
        ExtractorClimaSimulado,
        ExtractorFocosSimulado,
        RepositorioSimulado,
        salud_simulada,
    )

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
