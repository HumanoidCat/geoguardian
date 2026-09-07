"""Cuenta lo que la ingesta de H1.14 toca, para la evidencia de CA-8.

Imprime, por producto, cuantas filas y hasta que fecha hay en
`crudo.medicion_diaria` (precipitacion) y en `crudo.foco_calor`, y las ultimas
corridas de `control.bitacora_etl`. Se corre antes y despues de cada corrida:
si la segunda corrida no cambio nada, los conteos quedan iguales y la bitacora
la registra con cero filas.

Uso, con la base levantada:
    python docs/herramientas/contar_ingesta.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

sys.path.insert(0, str(Path(__file__).resolve().parent))

from apuntar import ErrorDestino, agregar_argumento, apuntar_a, encabezado  # noqa: E402

from basedatos.conexion import conectar  # noqa: E402

SQL_PRECIPITACION = """
    SELECT fuente_precipitacion, count(*),
           count(*) FILTER (WHERE precipitacion_mm IS NULL),
           min(fecha), max(fecha),
           max(fecha) FILTER (WHERE precipitacion_mm IS NOT NULL)
      FROM crudo.medicion_diaria
     GROUP BY 1 ORDER BY 1
"""
SQL_FOCOS = """
    SELECT producto, count(*), min(fecha), max(fecha),
           count(*) FILTER (WHERE codigo_distrito IS NOT NULL)
      FROM crudo.foco_calor
     GROUP BY 1 ORDER BY 1
"""
SQL_BITACORA = """
    SELECT id, proceso, estado, ventana_desde, ventana_hasta, producto, filas,
           to_char(iniciada_en, 'YYYY-MM-DD HH24:MI:SS'),
           to_char(terminada_en, 'YYYY-MM-DD HH24:MI:SS'),
           left(coalesce(mensaje, ''), 70)
      FROM control.bitacora_etl
     ORDER BY id DESC
     LIMIT 12
"""
SQL_FALLOS = "SELECT corrida_id, count(*) FROM control.fallo GROUP BY 1 ORDER BY 1"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    agregar_argumento(parser)
    opciones = parser.parse_args()
    try:
        apuntar_a(opciones.destino)
    except ErrorDestino as error:
        print(f"\n{error}\n")
        return 1

    conexion = conectar(autocommit=True)
    # Se imprime SIEMPRE, y sale de la conexion abierta, no de las
    # variables de entorno: una salida que no dice a que base le
    # pregunto no sirve como evidencia de que dos puntas coinciden.
    # Ver docs/herramientas/apuntar.py e I-38.
    print(f"\n>> {encabezado(conexion)}")
    try:
        with conexion.cursor() as cursor:
            print("crudo.medicion_diaria, por fuente de precipitacion")
            print("  fuente    filas    nulas   desde        hasta        ultimo con dato")
            cursor.execute(SQL_PRECIPITACION)
            for fuente, filas, nulas, desde, hasta, ultimo in cursor.fetchall():
                print(f"  {fuente:<8} {filas:>8} {nulas:>8}   {desde}   {hasta}   {ultimo}")

            print("\ncrudo.foco_calor, por producto")
            print("  producto         filas   desde        hasta        con distrito")
            cursor.execute(SQL_FOCOS)
            for producto, filas, desde, hasta, dentro in cursor.fetchall():
                print(f"  {producto:<16} {filas:>5}   {desde}   {hasta}   {dentro}")

            print("\ncontrol.bitacora_etl, ultimas corridas")
            cursor.execute(SQL_BITACORA)
            filas_ = cursor.fetchall()
            if not filas_:
                print("  (vacia)")
            for fila in filas_:
                print("  " + " · ".join(str(v) for v in fila))

            cursor.execute(SQL_FALLOS)
            fallos = cursor.fetchall()
            print("\ncontrol.fallo por corrida: " + (str(fallos) if fallos else "sin fallos"))
    finally:
        conexion.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
