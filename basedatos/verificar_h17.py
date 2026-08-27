"""
Verificador del manifiesto del dataset. Dueno: Cesar. Historia H1.7.

Cubre CA-1 a CA-6. Los cinco primeros son las cuatro condiciones de la seccion
**Medicion** de D-29 convertidas en algo que una maquina pueda decidir.

ESTE VERIFICADOR MODIFICA LA BASE, Y LA DEJA COMO ESTABA

CA-2 exige demostrar que una suma se mueve cuando el dato cambia. No hay forma de
demostrarlo sin cambiar un dato. Se hace dentro de una transaccion que se revierte
a proposito -levantando una excepcion dentro del `with`, que es como psycopg3
revierte- y despues **se vuelve a calcular la suma y se compara contra la
original**. Si no coincide, el criterio sale en rojo: preferimos avisar que la base
quedo tocada antes que callarlo.

No se usa `docker compose down -v` en ninguna parte, por I-05.

POR QUE CA-2 TIENE DOS MITADES

Que la suma cambie cuando el dato cambia es lo minimo. **Que NO cambie cuando solo
cambia `descargado_en` es lo que hace comparable el manifiesto entre dos personas**,
y es exactamente lo que esa columna habria roto si entrara en la suma.

USO

    python basedatos/verificar_h17.py
    python -m basedatos.verificar_h17
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[1]
if str(RAIZ_REPOSITORIO) not in sys.path:
    sys.path.insert(0, str(RAIZ_REPOSITORIO))

from basedatos.conexion import conectar  # noqa: E402
from basedatos.generar_manifiesto import (  # noqa: E402
    RUTA_SALIDA,
    TABLAS,
    columnas_de,
    consulta_de_suma,
    sumas_del_snit,
)

RUTA_GENERADOR = RAIZ_REPOSITORIO / "basedatos" / "generar_manifiesto.py"

VERSION = "v1"
FECHA = "2026-08-27"

TIEMPO_MAXIMO = 300

# `| `crudo.medicion_diaria` | 102272 | 1991-01-01 a 2025-12-31 | ... |`
PATRON_FILA = re.compile(
    r"^\|\s*`(?P<tabla>[\w.]+)`\s*\|\s*(?P<filas>\d+)\s*\|"
    r"\s*(?P<pedida>[^|]+?)\s*\|\s*(?P<observada>[^|]+?)\s*\|\s*$",
    re.M,
)
PATRON_SUMA_TABLA = re.compile(
    r"^\|\s*`(?P<tabla>[\w.]+)`\s*\|\s*`(?P<suma>[0-9a-f]{64})`\s*\|", re.M
)
PATRON_SUMA_CAPA = re.compile(r"^\|\s*(?P<capa>\w+)\s*\|\s*`(?P<suma>[0-9a-f]{64})`\s*\|", re.M)


@dataclass
class Resultado:
    criterio: str
    titulo: str
    cumple: bool
    detalle: list[str] = field(default_factory=list)


class Revertir(Exception):
    """Se levanta a proposito para que psycopg3 revierta la transaccion."""


def generar(destino: str, extra: list[str] | None = None) -> subprocess.CompletedProcess:
    """
    Corre el generador. `extra` sustituye a los argumentos por omision.

    La comparacion es `extra is None` y NO `extra or ...`: una lista vacia es
    falsa en Python, asi que `[] or [...]` devuelve los argumentos por omision y
    la comprobacion de "sin argumentos" terminaria corriendo con argumentos. Paso
    exactamente eso en la primera corrida de este verificador.
    """
    por_omision = ["--version", VERSION, "--fecha", FECHA]
    orden = [sys.executable, str(RUTA_GENERADOR), *(por_omision if extra is None else extra)]
    if destino:
        orden += ["--salida", destino]
    return subprocess.run(
        orden,
        cwd=str(RAIZ_REPOSITORIO),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=TIEMPO_MAXIMO,
        check=False,
    )


# --------------------------------------------------------------------------- #
# CA-1 - dos corridas, bytes identicos                                         #
# --------------------------------------------------------------------------- #


def ca1_reproducible() -> Resultado:
    detalle: list[str] = []
    with tempfile.TemporaryDirectory() as carpeta:
        primero = Path(carpeta) / "uno.md"
        segundo = Path(carpeta) / "dos.md"

        for destino in (primero, segundo):
            proceso = generar(str(destino))
            if proceso.returncode != 0:
                return Resultado(
                    "CA-1",
                    "Dos corridas producen bytes identicos",
                    False,
                    [
                        f"  [MAL] el generador salio con codigo {proceso.returncode}",
                        f"  {proceso.stderr.strip()}",
                    ],
                )

        uno = primero.read_bytes()
        dos = segundo.read_bytes()

    if uno != dos:
        primera_diferencia = next(
            (i for i, (a, b) in enumerate(zip(uno, dos, strict=False)) if a != b),
            min(len(uno), len(dos)),
        )
        return Resultado(
            "CA-1",
            "Dos corridas producen bytes identicos",
            False,
            [
                f"  [MAL] difieren: {len(uno)} y {len(dos)} bytes, primera diferencia en {primera_diferencia}",
                "  Hay algo escrito a mano o una marca de tiempo en el contenido versionado.",
            ],
        )

    detalle.append(f"  [ok ] dos corridas del generador dieron los mismos {len(uno)} bytes")
    detalle.append("  o sea que no hay marca de tiempo ni nada escrito a mano en la salida")
    return Resultado("CA-1", "Dos corridas producen bytes identicos", True, detalle)


# --------------------------------------------------------------------------- #
# CA-2 - la suma se mueve con el dato y no con el momento de carga             #
# --------------------------------------------------------------------------- #


def suma_de(cursor, esquema: str, tabla: str) -> str:
    cursor.execute(consulta_de_suma(esquema, tabla, columnas_de(cursor, esquema, tabla)))
    (suma,) = cursor.fetchone()
    return suma


def ca2_sensibilidad() -> Resultado:
    detalle: list[str] = []
    ok = True
    esquema, tabla = "crudo", "medicion_diaria"

    # autocommit=True para que `transaction()` abra una transaccion de verdad y no
    # un punto de retorno dentro de otra. Es la trampa de psycopg3 que produjo el
    # defecto de H1.1.
    with conectar(autocommit=True) as conexion, conexion.cursor() as cursor:
        original = suma_de(cursor, esquema, tabla)
        detalle.append(f"  suma original de {esquema}.{tabla}: {original[:16]}...")

        cursor.execute(
            f"SELECT codigo_distrito, fecha FROM {esquema}.{tabla} ORDER BY codigo_distrito, fecha LIMIT 1"
        )
        clave = cursor.fetchone()
        if clave is None:
            return Resultado(
                "CA-2", "La suma distingue dato de metadata", False, ["  [MAL] la tabla esta vacia"]
            )

        # -- mitad 1: cambiar un DATO tiene que mover la suma -------------------
        try:
            with conexion.transaction():
                cursor.execute(
                    f"UPDATE {esquema}.{tabla} SET temp_max_c = coalesce(temp_max_c, 0) + 1"
                    " WHERE codigo_distrito = %s AND fecha = %s",
                    clave,
                )
                alterada = suma_de(cursor, esquema, tabla)
                raise Revertir
        except Revertir:
            pass

        if alterada == original:
            ok = False
            detalle.append("  [MAL] cambiar temp_max_c de una fila NO movio la suma")
        else:
            detalle.append(
                f"  [ok ] cambiar temp_max_c de una fila movio la suma a {alterada[:16]}..."
            )

        # -- mitad 2: cambiar el MOMENTO DE CARGA no tiene que moverla ----------
        try:
            with conexion.transaction():
                cursor.execute(
                    f"UPDATE {esquema}.{tabla} SET descargado_en = descargado_en + interval '1 day'"
                )
                con_otra_carga = suma_de(cursor, esquema, tabla)
                raise Revertir
        except Revertir:
            pass

        if con_otra_carga != original:
            ok = False
            detalle.append(
                "  [MAL] mover descargado_en de TODAS las filas cambio la suma;"
                " dos personas con los mismos datos no podrian compararla"
            )
        else:
            detalle.append(
                "  [ok ] mover descargado_en de las 102 272 filas dejo la suma igual:"
                " la metadata de carga esta fuera"
            )

        # -- la base tiene que haber quedado como estaba -----------------------
        final = suma_de(cursor, esquema, tabla)
        if final != original:
            ok = False
            detalle.append(f"  [MAL] LA BASE QUEDO TOCADA: la suma final es {final[:16]}...")
        else:
            detalle.append("  [ok ] las dos transacciones revirtieron: la base quedo como estaba")

    return Resultado("CA-2", "La suma distingue el dato de la metadata de carga", ok, detalle)


# --------------------------------------------------------------------------- #
# CA-3 - lo que el manifiesto declara coincide con la base                     #
# --------------------------------------------------------------------------- #


def ca3_coincide_con_la_base(manifiesto: str) -> Resultado:
    detalle: list[str] = []
    ok = True

    declarado = {m.group("tabla"): m for m in PATRON_FILA.finditer(manifiesto)}
    sumas = {m.group("tabla"): m.group("suma") for m in PATRON_SUMA_TABLA.finditer(manifiesto)}

    with conectar() as conexion, conexion.cursor() as cursor:
        for esquema, tabla, columna_fecha, _ in TABLAS:
            nombre = f"{esquema}.{tabla}"
            fila = declarado.get(nombre)
            if fila is None:
                ok = False
                detalle.append(f"  [MAL] {nombre} no aparece en el manifiesto")
                continue

            cursor.execute(f"SELECT count(*) FROM {esquema}.{tabla}")
            (filas,) = cursor.fetchone()
            if int(fila.group("filas")) != filas:
                ok = False
                detalle.append(
                    f"  [MAL] {nombre}: declara {fila.group('filas')} y la base tiene {filas}"
                )
            else:
                detalle.append(f"  [ok ] {nombre}: {filas} filas")

            if columna_fecha:
                cursor.execute(
                    f"SELECT min({columna_fecha}), max({columna_fecha}) FROM {esquema}.{tabla}"
                )
                desde, hasta = cursor.fetchone()
                esperado = f"{desde.isoformat()} a {hasta.isoformat()}"
                if fila.group("observada") != esperado:
                    ok = False
                    detalle.append(
                        f"  [MAL] {nombre}: ventana observada declara"
                        f" '{fila.group('observada')}' y la base dice '{esperado}'"
                    )
                else:
                    detalle.append(f"  [ok ] {nombre}: ventana observada {esperado}")

            real = suma_de(cursor, esquema, tabla)
            if sumas.get(nombre) != real:
                ok = False
                detalle.append(f"  [MAL] {nombre}: la suma declarada no es la de la base")
            else:
                detalle.append(f"  [ok ] {nombre}: sha256 {real[:16]}... coincide")

    return Resultado("CA-3", "Los conteos, ventanas y sumas coinciden con la base", ok, detalle)


# --------------------------------------------------------------------------- #
# CA-4, CA-5 y CA-6                                                            #
# --------------------------------------------------------------------------- #


def ca4_suma_del_snit(manifiesto: str) -> Resultado:
    detalle: list[str] = []
    ok = True
    en_procedencia = dict(sumas_del_snit())
    en_manifiesto = {
        m.group("capa"): m.group("suma") for m in PATRON_SUMA_CAPA.finditer(manifiesto)
    }

    for capa, suma in en_procedencia.items():
        if en_manifiesto.get(capa) == suma:
            detalle.append(f"  [ok ] capa {capa}: {suma[:16]}... viaja en el manifiesto")
        else:
            ok = False
            detalle.append(
                f"  [MAL] capa {capa}: la suma del manifiesto no es la de la procedencia"
            )

    if not en_procedencia:
        ok = False
        detalle.append("  [MAL] procedencia-geometrias.md no declara ninguna suma")

    return Resultado("CA-4", "La suma del SNIT viaja dentro del manifiesto", ok, detalle)


def ca5_version_declarada() -> Resultado:
    """Sin `--version` y `--fecha` el generador tiene que fallar, no inventar."""
    detalle: list[str] = []
    ok = True

    sin_nada = generar("-", extra=[])
    if sin_nada.returncode == 0:
        ok = False
        detalle.append("  [MAL] sin argumentos el generador produjo un manifiesto igual")
    else:
        detalle.append(f"  [ok ] sin argumentos falla con codigo {sin_nada.returncode}")

    solo_version = generar("-", extra=["--version", VERSION])
    if solo_version.returncode == 0:
        ok = False
        detalle.append("  [MAL] sin --fecha el generador produjo un manifiesto igual")
    else:
        detalle.append("  [ok ] con --version pero sin --fecha tambien falla")

    return Resultado("CA-5", "La version se declara, no se infiere", ok, detalle)


def ca6_se_puede_recalcular(manifiesto: str) -> Resultado:
    detalle: list[str] = []
    ok = True

    consultas = manifiesto.count("```sql")
    if consultas < len(TABLAS):
        ok = False
        detalle.append(f"  [MAL] {consultas} consultas para {len(TABLAS)} tablas")
    else:
        detalle.append(f"  [ok ] el manifiesto trae las {consultas} consultas de suma")

    with conectar() as conexion, conexion.cursor() as cursor:
        for esquema, tabla, _, _ in TABLAS:
            columnas = columnas_de(cursor, esquema, tabla)
            if ", ".join(columnas) in manifiesto:
                detalle.append(
                    f"  [ok ] {esquema}.{tabla}: sus {len(columnas)} columnas estan listadas"
                )
            else:
                ok = False
                detalle.append(f"  [MAL] {esquema}.{tabla}: la lista de columnas no coincide")

    if "descargado_en" in manifiesto:
        detalle.append("  [ok ] declara que descargado_en queda fuera de la suma")
    else:
        ok = False
        detalle.append("  [MAL] no declara que columnas quedan fuera")

    return Resultado("CA-6", "El manifiesto dice como se calcula cada suma", ok, detalle)


# --------------------------------------------------------------------------- #


def main() -> int:
    print("Verificacion del manifiesto del dataset de H1.7 (D-29)")
    print("=" * 74)

    if not RUTA_SALIDA.exists():
        print(f"FALLA: no existe {RUTA_SALIDA}. Generalo primero.")
        return 2

    manifiesto = RUTA_SALIDA.read_text(encoding="utf-8")
    print(
        f"Manifiesto: {RUTA_SALIDA.relative_to(RAIZ_REPOSITORIO).as_posix()}, {len(manifiesto)} caracteres"
    )
    print("CA-2 modifica la base dentro de transacciones que se revierten.")

    resultados = [
        ca1_reproducible(),
        ca2_sensibilidad(),
        ca3_coincide_con_la_base(manifiesto),
        ca4_suma_del_snit(manifiesto),
        ca5_version_declarada(),
        ca6_se_puede_recalcular(manifiesto),
    ]

    for r in resultados:
        print(f"\n{r.criterio} - {r.titulo} ... {'CUMPLE' if r.cumple else 'NO CUMPLE'}")
        for linea in r.detalle:
            print(linea)

    fallidos = [r for r in resultados if not r.cumple]
    print("\n" + "=" * 74)
    if fallidos:
        print("NO CUMPLEN: " + ", ".join(r.criterio for r in fallidos))
        return 1
    print("Los seis criterios se cumplen.")
    print("Falta publicar el consolidado como release asset: D-29 lo incluye en el")
    print("alcance de H1.7 y esta entrega no lo cubre. Declarado, no omitido.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
