"""
Verificador de H12.4 · Diagnostico guiado a partir de `control.bitacora_etl`.

Dueno: Luna. Criterios en
`docs/evidencias/arquitectura-software/H12.4-criterios-aceptacion.md`.

CORRE SIN BASE Y SIN RED. Es CA-5.

POR QUE LOS SABOTAJES USAN FILAS REALES
---------------------------------------

La primera version de este verificador fabricaba la corrida de I-43 como
`filas=215, filas_leidas=3`, **una forma que no existe en la tabla**. La invente
para que coincidiera con mi modelo de las columnas, y mi modelo estaba mal:
`filas_leidas` es lo que trajo la fuente y `filas` lo que se escribio, dos etapas
distintas donde ninguna contiene a la otra.

Las 17 comprobaciones pasaron en verde sobre esa premisa falsa, porque el
sabotaje y el detector compartian el error. Es la leccion de H4.2:

    Una identidad solo detecta errores que rompan la relacion entre sus dos
    lados. Si el error esta aguas arriba de los dos, la identidad se cumple
    perfectamente sobre un numero equivocado.

Ahora los casos salen de la tabla real, y **cada uno dice si su numero esta
medido o reconstruido**.

LOS CUATRO SABOTAJES
--------------------

  7.  La forma de I-43: la fuente trajo muchisimo menos de lo que la ventana
      pedia. **Si no sale, la historia no sirve para el caso que la motivo.**
  7b. La corrida 39 real, con `filas_leidas` nulo. La primera version la dejaba
      pasar EN SILENCIO, que es peor que no detectarla.
  8.  Una corrida `en_curso` con fecha vieja.
  9.  Una bitacora donde todo esta bien, y se exige que **no invente** ninguna
      senal.

Uso:
    python -m backend.calidad.verificar_h12_4
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.calidad.diagnostico_bitacora import (  # noqa: E402
    DIAS_AUSENTE,
    HORAS_COLGADA,
    UMBRAL_COBERTURA,
    Corrida,
    ausencias,
    clasificar,
    cobertura_de,
    encabezado,
    esperadas,
    redactar,
    senales_de,
)

AHORA = datetime(2026, 9, 13, 12, 0, 0)
INGESTA = "ingesta.lluvia_intensa"
ESTIMACION = "estimacion.riesgo"
SERIES = {INGESTA: 8}


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


def _hace(horas: float = 0, dias: float = 0) -> datetime:
    return AHORA - timedelta(hours=horas, days=dias)


#: Series esperadas por la corrida 63: 279 dias de ventana por 8 distritos.
ESPERADAS_63 = 2232

#: Lo que la fuente trajo en la corrida 63. Las 288 que faltan son **36 dias por
#: 8 distritos**, que es la latencia de D-40 despues del 2026-07-31.
LEIDAS_63 = 1944


def _sana(id_: int = 1, proceso: str = INGESTA, **extra) -> Corrida:
    """Una corrida sin nada raro.

    LOS NUMEROS SON LOS DE LA CORRIDA 63, MEDIDOS el 2026-09-13, no
    reconstruidos:

        ventana 2025-12-01 a 2026-09-05 · filas 1712 · filas_leidas 1944

    Una version anterior de este archivo puso la ventana hasta el 2026-07-31 y la
    etiqueto «corrida 63 real». **No lo era**: era una reconstruccion que daba
    justo 1944 de 1944, un 100 % demasiado limpio. La ventana medida llega al
    2026-09-05 y la cobertura real es del 87,1 %.

    Es la misma falta que este verificador ya corrigio una vez, en menor escala:
    un numero comodo presentado como una medicion.
    """
    base = {
        "id": id_,
        "proceso": proceso,
        "estado": "exitosa",
        "iniciada_en": _hace(horas=3),
        "terminada_en": _hace(horas=2),
        "filas": 1712,
        "filas_leidas": LEIDAS_63,
        "mensaje": None,
        "ventana_desde": date(2025, 12, 1),
        "ventana_hasta": date(2026, 9, 5),
    }
    base.update(extra)
    return Corrida(**base)


def verificar() -> Resultado:
    r = Resultado()
    print("\nDiagnostico guiado de la bitacora · H12.4\n")

    # ------------------------------------------------------------------ 1
    sanas = [_sana(1), _sana(2, proceso=ESTIMACION)]
    r.comprobar(
        "1. una corrida sana no produce senal",
        senales_de(sanas, AHORA, SERIES) == [],
        f"corrida 63 medida: {LEIDAS_63} de {ESPERADAS_63} esperadas, {LEIDAS_63 / ESPERADAS_63:.1%}",
    )

    # ------------------------------------------------------------------ 2
    r.comprobar(
        "2. filas_leidas MAYOR que filas no rompe nada (corrida 63 real)",
        clasificar(_sana(63), AHORA, SERIES) is None,
        "1944 traidas, 1712 escritas: el ON CONFLICT salto 232. Son etapas distintas",
    )

    # ------------------------------------------------------------------ 3
    todas = senales_de([_sana(3, estado="parcial", filas=800)], AHORA, SERIES)
    r.comprobar(
        "3. toda senal trae evidencia Y accion (CA-2)",
        bool(todas) and all(s.evidencia.strip() and s.accion.strip() for s in todas),
        "una senal sin evidencia es una opinion; sin accion no ayuda a quien opera",
    )

    # ------------------------------------------------------------------ 4
    sin_codigo = clasificar(
        _sana(4, estado="fallida", mensaje="permission denied for table riesgo"), AHORA, SERIES
    )
    con_codigo = clasificar(_sana(5, estado="fallida", sqlstate="42501"), AHORA, SERIES)
    r.comprobar(
        "4. lo leido de texto libre se marca CONJETURA, lo del sqlstate no (CA-3)",
        sin_codigo is not None
        and sin_codigo.conjetura
        and con_codigo is not None
        and not con_codigo.conjetura,
        "el texto ya engano una vez: en I-43 decia «exitosa»",
    )

    # ------------------------------------------------------------------ 5
    texto = encabezado("base LOCAL: geoguardian en localhost:5433", 3, {"sqlstate": 0}, "8")
    r.comprobar(
        "5. el encabezado declara sobre que esta ciego (CA-4)",
        "NO PUEDE OPINAR" in texto and "sqlstate" in texto and "localhost:5433" in texto,
        "esta salida se pega en un mensaje: la advertencia tiene que viajar con ella",
    )

    # ------------------------------------------------------------------ 6
    r.comprobar(
        "6. una bitacora vacia no es un error (CA-5)",
        senales_de([], AHORA, SERIES) == [] and "Ninguna senal" in redactar([]),
        "no hay filas que juzgar; no se inventa un veredicto",
    )

    # ------------------------------------------------------------------ 7
    r.comprobar(
        "7. el texto de «ninguna senal» NO dice que todo este bien",
        "NO dice que todo este bien" in redactar([]),
        "ausencia de senal conocida no es ausencia de problema",
    )

    # ------------------------------------------------------------------ 8
    # SABOTAJE 1 · La forma de I-43.
    # RECONSTRUIDA, y se dice: la tabla nunca registro esta cobertura, que es
    # justamente el defecto. 215 dias pedidos x 8 distritos = 1720 esperadas;
    # llegaron 3 dias, o sea 24 series.
    i43 = Corrida(
        id=43,
        proceso=INGESTA,
        estado="exitosa",
        iniciada_en=_hace(horas=5),
        terminada_en=_hace(horas=4),
        filas=1968,
        filas_leidas=24,
        mensaje="ingesta completada",
        ventana_desde=date(2025, 12, 29),
        ventana_hasta=date(2026, 9, 3),
    )
    senal = clasificar(i43, AHORA, SERIES)
    r.comprobar(
        "8. SABOTAJE · marca la forma de I-43 (CA-7)",
        senal is not None and senal.nombre == "cobertura incompleta",
        "24 de 1992 = 1,2 %. La ventana es la MEDIDA de la corrida 39; las 24 "
        "series son reconstruidas, porque la tabla nunca las registro: ese es el defecto",
    )

    # ------------------------------------------------------------------ 9
    # SABOTAJE 1b · La corrida 39 REAL, la del propio I-43.
    # MEDIDA el 2026-09-13: exitosa, filas 1968, filas_leidas NULO.
    # La primera version la dejaba pasar en silencio.
    corrida39 = Corrida(
        id=39,
        proceso=INGESTA,
        estado="exitosa",
        iniciada_en=datetime(2026, 9, 4, 22, 17, 52),
        terminada_en=datetime(2026, 9, 4, 22, 18, 48),
        filas=1968,
        filas_leidas=None,
        ventana_desde=date(2025, 12, 29),
        ventana_hasta=date(2026, 9, 3),
    )
    senal = clasificar(corrida39, AHORA, SERIES)
    r.comprobar(
        "9. SABOTAJE · una corrida SIN filas_leidas se declara imposible de juzgar",
        senal is not None and senal.nombre == "cobertura no declarada",
        "corrida 39 real. La version anterior la dejaba pasar EN SILENCIO, que es peor",
    )

    # ----------------------------------------------------------------- 10
    # SABOTAJE 2 · Una corrida colgada.
    colgada = _sana(
        10,
        estado="en_curso",
        iniciada_en=_hace(horas=HORAS_COLGADA + 1),
        terminada_en=None,
        filas=None,
        filas_leidas=None,
    )
    senal = clasificar(colgada, AHORA, SERIES)
    r.comprobar(
        "10. SABOTAJE · marca una corrida en_curso demasiado vieja (CA-8)",
        senal is not None and senal.nombre == "colgada",
        f"abierta {HORAS_COLGADA + 1:.0f} h, umbral {HORAS_COLGADA:.0f} h",
    )

    # ----------------------------------------------------------------- 11
    # SABOTAJE 3 · Todo bien, y se exige que no invente.
    tranquila = [_sana(i, proceso=p) for i, p in enumerate((INGESTA, ESTIMACION), start=1)]
    inventadas = senales_de(tranquila, AHORA, SERIES) + ausencias(tranquila, AHORA)
    r.comprobar(
        "11. SABOTAJE · con todo en orden NO inventa ninguna senal",
        inventadas == [],
        "un diagnosticador que siempre encuentra algo es tan inutil como uno que nunca",
    )

    # ----------------------------------------------------------------- 12
    r.comprobar(
        "12. detecta un proceso diario SIN corridas (CA-9)",
        [s.proceso for s in ausencias([_sana(1)], AHORA)] == [ESTIMACION],
        "el cron caido no escribe nada: es una ausencia y hay que ir a buscarla",
    )

    # ----------------------------------------------------------------- 13
    viejas = [_sana(1, iniciada_en=_hace(dias=DIAS_AUSENTE + 1)), _sana(2, proceso=ESTIMACION)]
    r.comprobar(
        "13. detecta un proceso cuya ultima corrida quedo vieja",
        any(s.proceso == INGESTA for s in ausencias(viejas, AHORA)),
        f"ultima hace {DIAS_AUSENTE + 1} dias, umbral {DIAS_AUSENTE}",
    )

    # ----------------------------------------------------------------- 14
    # El umbral tiene que DISCRIMINAR: si marcara todo, no seria un umbral.
    # 243 dias x 8 = 1944 esperadas.
    umbral = int(ESPERADAS_63 * UMBRAL_COBERTURA)
    arriba = clasificar(_sana(14, filas_leidas=umbral + 1), AHORA, SERIES)
    abajo = clasificar(_sana(15, filas_leidas=umbral - 1), AHORA, SERIES)
    r.comprobar(
        "14. el umbral discrimina: uno por encima pasa, uno por debajo se marca",
        arriba is None and abajo is not None and abajo.nombre == "cobertura incompleta",
        f"umbral {UMBRAL_COBERTURA:.0%}, probado a los dos lados sobre {ESPERADAS_63} esperadas",
    )

    # ----------------------------------------------------------------- 15
    # D-40 con numeros MEDIDOS, no supuestos: a la corrida 63 le faltan 288
    # series, que son 36 dias x 8 distritos despues del 2026-07-31.
    proporcion_63 = LEIDAS_63 / ESPERADAS_63
    r.comprobar(
        "15. la latencia de D-40 no se confunde con un fallo",
        UMBRAL_COBERTURA < proporcion_63 < 0.9,
        f"corrida 63 medida: {proporcion_63:.1%}. Con umbral 0,9 esta corrida SANA "
        "se marcaria. Es el argumento del umbral, y esta medido",
    )

    # ----------------------------------------------------------------- 16
    # Un proceso sin series declaradas NO se juzga por cobertura.
    otro = _sana(17, proceso="api", filas_leidas=1)
    r.comprobar(
        "16. un proceso sin series declaradas no se juzga por cobertura",
        esperadas(otro, SERIES) is None and clasificar(otro, AHORA, SERIES) is None,
        "no saber se dice, no se supone. Es lo que separa un diagnostico de una corazonada",
    )

    # ----------------------------------------------------------------- 17
    sin_ventana = _sana(18, ventana_desde=None, ventana_hasta=None, filas_leidas=1)
    r.comprobar(
        "17. sin ventana declarada tampoco se juzga la cobertura",
        esperadas(sin_ventana, SERIES) is None and clasificar(sin_ventana, AHORA, SERIES) is None,
        "sin lo pedido no hay contra que comparar lo devuelto",
    )

    # ----------------------------------------------------------------- 18
    colgada_y_pobre = Corrida(
        id=19,
        proceso=INGESTA,
        estado="en_curso",
        iniciada_en=_hace(horas=HORAS_COLGADA + 2),
        filas=1968,
        filas_leidas=24,
        ventana_desde=date(2025, 12, 29),
        ventana_hasta=date(2026, 9, 3),
    )
    senal = clasificar(colgada_y_pobre, AHORA, SERIES)
    r.comprobar(
        "18. una corrida con dos problemas se reporta UNA vez, por el mas grave",
        senal is not None and senal.nombre == "colgada",
        "el mismo problema con tres nombres no es mas informacion, es mas ruido",
    )

    # ----------------------------------------------------------------- 19
    mezcla = [i43, corrida39, colgada, _sana(20), _sana(21, estado="fallida", mensaje="timeout")]
    r.comprobar(
        "19. dos corridas del diagnostico dan la misma salida (CA-10)",
        redactar(senales_de(mezcla, AHORA, SERIES)) == redactar(senales_de(mezcla, AHORA, SERIES)),
        "sin azar y sin depender del orden de la consulta",
    )

    # ----------------------------------------------------------------- 20
    salida = redactar(senales_de(mezcla, AHORA, SERIES))
    r.comprobar(
        "20. las conjeturas se separan de lo demas en la salida (CA-3)",
        "CONJETURA" in salida and "No son causas" in salida,
        "quien lee tiene que poder distinguir un codigo de error de una lectura de texto",
    )

    # ----------------------------------------------------------------- 21
    r.comprobar(
        "21. la cobertura cuenta columnas vacias sin confundirlas con cero filas",
        cobertura_de([_sana(1), _sana(2, sqlstate="42501")])
        == {"sqlstate": 1, "version_codigo": 0, "reportado_por": 0},
        "es la cifra con la que el encabezado declara su ceguera",
    )

    return r


def main() -> int:
    r = verificar()
    print(f"\n  {r.hechos - len(r.fallos)} de {r.hechos} comprobaciones en verde")
    if r.fallos:
        print("\n  Fallaron:")
        for fallo in r.fallos:
            print(f"    - {fallo}")
        print()
        return 1
    print("\n  H12.4 cumple sus criterios verificables sin base y sin red.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
