"""Cuenta lo que hay en `analitico.riesgo`, para la evidencia de H3.6.

Imprime filas por evento y algoritmo, el rango de fechas, cuantas filas de
auditoria hay (H1.13), y la ultima `version_modelo`. Es lo que CA-16 pide medir
antes y despues de correr `estimar_riesgo` dos veces: si la segunda corrida no
cambio nada, los conteos y la auditoria quedan iguales.

Uso, con la base levantada:
    python docs/herramientas/contar_riesgo.py
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from basedatos.conexion import conectar  # noqa: E402

SQL_POR_EVENTO = """
    SELECT tipo_evento, coalesce(algoritmo, '(nulo)'), count(*),
           min(fecha), max(fecha),
           count(*) FILTER (WHERE nivel = 'alto'),
           round(avg(probabilidad)::numeric, 4)
      FROM analitico.riesgo
     GROUP BY 1, 2
     ORDER BY 1, 2
"""
SQL_VERSIONES = "SELECT DISTINCT version_modelo FROM analitico.riesgo ORDER BY 1"
SQL_AUDITORIA = "SELECT operacion, count(*) FROM analitico.riesgo_auditoria GROUP BY 1 ORDER BY 1"


def main() -> int:
    conexion = conectar(autocommit=True)
    try:
        with conexion.cursor() as cursor:
            cursor.execute(SQL_POR_EVENTO)
            filas = cursor.fetchall()
            cursor.execute(SQL_VERSIONES)
            versiones = [v for (v,) in cursor.fetchall()]
            cursor.execute(SQL_AUDITORIA)
            auditoria = cursor.fetchall()
    finally:
        conexion.close()

    print("\nanalitico.riesgo\n")
    if not filas:
        print("  (vacia)")
    total = 0
    for evento, algoritmo, n, desde, hasta, altos, p_media in filas:
        total += n
        print(
            f"  {evento:15} {algoritmo:26} {n:7d} filas  {desde} .. {hasta}"
            f"  alto={altos}  P(alto) media={p_media}"
        )
    print(f"\n  total {total} filas")
    print("  version_modelo: " + (", ".join(versiones) if versiones else "(ninguna)"))
    print(
        "  auditoria (H1.13): "
        + (", ".join(f"{op}={n}" for op, n in auditoria) if auditoria else "sin filas")
        + "\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
