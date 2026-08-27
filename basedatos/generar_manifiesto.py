"""
Genera el manifiesto del dataset consolidado. Dueno: Cesar. Historia H1.7.

QUE ES ESTO

El repositorio tiene que poder responder "que dato produjo este resultado" sin
guardar el dato. Este programa produce ese documento: version, fecha, filas por
tabla, ventana temporal y sumas de verificacion. El archivo consolidado va como
release asset, fuera del arbol. Lo decide **D-29**.

DOS CLASES DE SUMA, Y NO SON INTERCAMBIABLES

  suma de la fuente     de donde vino     la del SNIT, leida de procedencia-geometrias.md
  suma del contenido    tenemos lo mismo  calculada desde la base, por tabla

La primera es la regla 1 de D-29 y es la que delata que el SNIT republico su capa
-la fuente que ya fallo con I-03 y produjo I-10-. La segunda es la que dos
personas comparan para saber si tienen el mismo dataset.

Hizo falta la segunda porque **los cargadores no guardan los archivos crudos**:
descargan en memoria y cargan. Sin archivo en disco no hay byte que alterar, asi
que la condicion 2 de la seccion Medicion de D-29 solo es comprobable sobre el
contenido.

POR QUE LA SUMA EXCLUYE `descargado_en`

`crudo.medicion_diaria` y `crudo.foco_calor` la declaran
`timestamptz NOT NULL DEFAULT now()`. Si la suma se calculara sobre la fila
completa, **dos personas que cargan exactamente los mismos datos obtendrian sumas
distintas**, porque cada una cargo en otro momento. Eso destruiria el objetivo
entero de D-29.

Las columnas se leen de `information_schema` y se descartan las de
`COLUMNAS_EXCLUIDAS`. El manifiesto imprime la lista que uso, porque **una suma
que nadie puede recalcular no sirve para comparar nada**.

POR QUE NO HAY MARCA DE TIEMPO EN LA SALIDA

Los tres `procedencia-*.md` traen la hora de generacion. Este no puede: la
condicion 1 de la Medicion exige que dos corridas produzcan bytes identicos, y una
marca de tiempo lo impide por construccion. La version y su fecha se pasan
explicitas, que ademas es la regla 3 de D-29: la version se declara, no se infiere.

USO

    python basedatos/generar_manifiesto.py --version v1 --fecha 2026-08-27
    python -m basedatos.generar_manifiesto --version v1 --fecha 2026-08-27 --salida -

`--salida -` escribe a la salida estandar sin tocar el archivo.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[1]
if str(RAIZ_REPOSITORIO) not in sys.path:
    sys.path.insert(0, str(RAIZ_REPOSITORIO))

from basedatos.conexion import conectar  # noqa: E402

RUTA_PROCEDENCIA_GEOMETRIAS = RAIZ_REPOSITORIO / "basedatos" / "ddl" / "procedencia-geometrias.md"
RUTA_SALIDA = RAIZ_REPOSITORIO / "basedatos" / "ddl" / "manifiesto-dataset.md"

# Metadata de carga: describe CUANDO se cargo, no QUE se cargo. Entra en la suma
# solo si se quiere que dos copias identicas del dataset se declaren distintas.
COLUMNAS_EXCLUIDAS = {"descargado_en"}

# Tablas del dataset consolidado, en el orden en que se declaran.
#   (esquema, tabla, columna de fecha o None, procedencia que declara la ventana pedida)
TABLAS = [
    ("geo", "distrito", None, None),
    ("crudo", "medicion_diaria", "fecha", "procedencia-mediciones.md"),
    ("crudo", "foco_calor", "fecha", "procedencia-focos.md"),
]

PATRON_SUMA_SNIT = re.compile(r"^\s*(\w+)\s+sha256\s+([0-9a-f]{64})\s*$", re.M)

# `- Ventana: 2001-01-01 a 2024-12-31` en los procedencia-*.md
PATRON_VENTANA = re.compile(r"Ventana:\s*(\d{4}-\d{2}-\d{2})\s+a\s+(\d{4}-\d{2}-\d{2})")


class ErrorManifiesto(RuntimeError):
    """Falta un insumo. Se para en vez de escribir un manifiesto incompleto."""


# --------------------------------------------------------------------------- #
# Lecturas contra la base                                                      #
# --------------------------------------------------------------------------- #


def columnas_de(cursor, esquema: str, tabla: str) -> list[str]:
    """
    Columnas de dato, en el orden del esquema, sin la metadata de carga.

    Se leen de `information_schema` y no de una lista escrita a mano para que una
    columna nueva entre a la suma sin que nadie se acuerde de agregarla. Que la
    suma cambie ante un cambio de esquema es deliberado: el dataset es el esquema
    mas los datos, y dos bases con columnas distintas no tienen lo mismo.
    """
    cursor.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_schema = %s AND table_name = %s
         ORDER BY ordinal_position
        """,
        (esquema, tabla),
    )
    columnas = [nombre for (nombre,) in cursor.fetchall()]
    if not columnas:
        raise ErrorManifiesto(f"la tabla {esquema}.{tabla} no existe en la base")
    return [c for c in columnas if c not in COLUMNAS_EXCLUIDAS]


def consulta_de_suma(esquema: str, tabla: str, columnas: list[str]) -> str:
    """
    La consulta que produce la suma de una tabla.

    Se arma como texto y se imprime tal cual en el manifiesto: quien lo reciba
    tiene que poder llegar al mismo numero por su cuenta.

    El orden es por el md5 de cada fila y no por la clave primaria, asi que no
    depende de que exista una ni de como este definida. `coalesce` cubre la tabla
    vacia, donde `string_agg` devuelve nulo.
    """
    lista = ", ".join(columnas)
    return (
        "SELECT encode(sha256(coalesce(string_agg(h, '' ORDER BY h), '')::bytea), 'hex')\n"
        f"  FROM (SELECT md5(ROW({lista})::text) AS h FROM {esquema}.{tabla}) s"
    )


def ventana_pedida(procedencia: str | None) -> tuple[str, str] | None:
    """
    La ventana que se PIDIO al descargar, leida de su `procedencia-*.md`.

    No es la misma que la ventana que HAY. Se pidieron los focos de 2001-01-01 a
    2024-12-31 y el primero detectado es del 2 de marzo de 2001: en enero y
    febrero no hubo ninguno. Las dos cifras son ciertas y responden preguntas
    distintas, asi que el manifiesto declara las dos.

    Se lee en vez de escribirse a mano por I-07: una cifra derivada a mano se
    desfasa el dia que alguien recargue con otro rango.
    """
    if procedencia is None:
        return None
    ruta = RAIZ_REPOSITORIO / "basedatos" / "ddl" / procedencia
    if not ruta.exists():
        raise ErrorManifiesto(f"falta {procedencia}, que declara la ventana pedida")
    encontrado = PATRON_VENTANA.search(ruta.read_text(encoding="utf-8"))
    if not encontrado:
        raise ErrorManifiesto(f"{procedencia} no declara una linea `Ventana: ... a ...`")
    return encontrado.group(1), encontrado.group(2)


def medir_tabla(
    cursor, esquema: str, tabla: str, columna_fecha: str | None, procedencia: str | None
) -> dict:
    columnas = columnas_de(cursor, esquema, tabla)

    cursor.execute(f"SELECT count(*) FROM {esquema}.{tabla}")
    (filas,) = cursor.fetchone()

    desde = hasta = None
    if columna_fecha:
        cursor.execute(f"SELECT min({columna_fecha}), max({columna_fecha}) FROM {esquema}.{tabla}")
        desde, hasta = cursor.fetchone()

    cursor.execute(consulta_de_suma(esquema, tabla, columnas))
    (suma,) = cursor.fetchone()

    return {
        "esquema": esquema,
        "tabla": tabla,
        "columnas": columnas,
        "filas": filas,
        "desde": desde,
        "hasta": hasta,
        "suma": suma,
        "consulta": consulta_de_suma(esquema, tabla, columnas),
        "pedida": ventana_pedida(procedencia),
    }


def estado_de_imputacion(cursor) -> list[tuple[str, bool, int]]:
    """
    Que se hizo con lo que falta, en `crudo.medicion_diaria`.

    D-22 redujo H1.4 porque las series de H1.1 no tienen un solo faltante en
    12 784 dias: CHIRPS y POWER son productos de malla, completos por
    construccion. Pero **mantuvo la dependencia de H1.7 sobre H1.4** con estas
    palabras: "versionar el dataset consolidado requiere saber que se hizo con lo
    que falta, aunque hoy no falte nada".

    Esto es esa linea. Hoy la respuesta es "nada", y **decirlo explicitamente es
    distinto de no decir nada**: un manifiesto que calla sobre imputacion obliga a
    suponer, y el dia que Sentinel-2 traiga huecos de verdad -H1.6- la diferencia
    entre las dos versiones se va a poder leer.

    El `ORDER BY` no es cosmetico: sin el, dos corridas podrian devolver las filas
    en otro orden y el manifiesto dejaria de ser byte a byte identico.
    """
    cursor.execute(
        """
        SELECT metodo_imputacion, imputado, count(*)
          FROM crudo.medicion_diaria
         GROUP BY metodo_imputacion, imputado
         ORDER BY metodo_imputacion, imputado
        """
    )
    return cursor.fetchall()


def focos_dentro_del_canton(cursor) -> int:
    """
    Los focos con distrito asignado.

    D-29 cita "242 dentro del canton" y la tabla tiene 494 filas: la caja de
    descarga es un rectangulo y el canton no lo es, asi que 252 caen fuera y se
    guardan con `codigo_distrito` nulo. Las dos cifras son ciertas y el manifiesto
    declara las dos, porque una sola invita a creer que la otra esta mal.
    """
    cursor.execute("SELECT count(*) FROM crudo.foco_calor WHERE codigo_distrito IS NOT NULL")
    (cuenta,) = cursor.fetchone()
    return cuenta


# --------------------------------------------------------------------------- #
# La suma de la fuente                                                         #
# --------------------------------------------------------------------------- #


def sumas_del_snit() -> list[tuple[str, str]]:
    """
    Lee las sumas de la descarga desde `procedencia-geometrias.md`.

    No se recalculan: son las de los bytes crudos que trajo `cargar_distritos.py`
    en el momento de la carga, y volver a pedirle la capa al SNIT daria la suma de
    HOY, que es justamente lo que la regla 1 de D-29 quiere poder comparar.
    """
    if not RUTA_PROCEDENCIA_GEOMETRIAS.exists():
        raise ErrorManifiesto(
            f"falta {RUTA_PROCEDENCIA_GEOMETRIAS.name}, que trae las sumas del SNIT. "
            "Lo genera `backend/etl/cargar_distritos.py`."
        )
    texto = RUTA_PROCEDENCIA_GEOMETRIAS.read_text(encoding="utf-8")
    sumas = PATRON_SUMA_SNIT.findall(texto)
    if not sumas:
        raise ErrorManifiesto(
            f"{RUTA_PROCEDENCIA_GEOMETRIAS.name} no declara ninguna suma sha256. "
            "Sin ella el manifiesto no cumple la regla 1 de D-29."
        )
    return sumas


# --------------------------------------------------------------------------- #
# La salida                                                                    #
# --------------------------------------------------------------------------- #


def escribir_manifiesto(
    version: str, fecha: date, tablas: list[dict], dentro: int, snit, imputacion
) -> str:
    lineas: list[str] = []
    a = lineas.append

    a("# Manifiesto del dataset consolidado")
    a("")
    a(f"**Version.** {version}")
    a(f"**Fecha de la version.** {fecha.isoformat()}")
    a("**Historia.** H1.7 - **Decide el como.** D-29")
    a("")
    a("Generado por `basedatos/generar_manifiesto.py`. **No editar a mano.**")
    a("")
    a("Este documento **no contiene el dataset**: lo describe. El archivo")
    a("consolidado se publica como *release asset*, fuera del arbol. Lo decide")
    a("D-29, y la razon es que 102 272 filas en cada commit dejan el repositorio")
    a("sin poder revisarse.")
    a("")
    a("**No lleva marca de tiempo de generacion, a proposito.** Dos corridas con")
    a("los mismos argumentos tienen que producir bytes identicos: es la condicion 1")
    a("de la seccion Medicion de D-29, y una hora de generacion la rompe.")
    a("")

    a("## Contenido")
    a("")
    a("**Las dos ventanas no son la misma y las dos son ciertas.** *Pedida* es el")
    a("rango que se solicito al descargar, declarado en el `procedencia-*.md`")
    a("correspondiente. *Observada* es el primer y el ultimo dato que hay en la")
    a("base. Difieren cuando la fuente no tuvo nada que entregar en los extremos")
    a("del rango, que es el caso de los focos de calor: se pidieron doce meses de")
    a("2001 y el primero detectado es de marzo.")
    a("")
    a("| Tabla | Filas | Ventana pedida | Ventana observada |")
    a("|---|---|---|---|")
    for t in tablas:
        if t["desde"]:
            observada = f"{t['desde'].isoformat()} a {t['hasta'].isoformat()}"
        else:
            observada = "sin columna de fecha"
        pedida = f"{t['pedida'][0]} a {t['pedida'][1]}" if t["pedida"] else "no aplica"
        a(f"| `{t['esquema']}.{t['tabla']}` | {t['filas']} | {pedida} | {observada} |")
    a("")
    focos = next(t for t in tablas if t["tabla"] == "foco_calor")
    a(f"De los {focos['filas']} focos de calor, **{dentro} caen dentro del canton** y el")
    a("resto fuera, con `codigo_distrito` nulo: la caja de descarga es un rectangulo")
    a("y el canton no lo es. Las dos cifras son ciertas y D-29 cita la de adentro.")
    a("")

    a("## Que se hizo con lo que falta")
    a("")
    a("D-22 redujo H1.4 al comprobar que las series climaticas no tienen un solo")
    a("faltante en 12 784 dias -CHIRPS y POWER son productos de malla, completos")
    a("por construccion- pero **mantuvo la dependencia de H1.7 sobre H1.4**:")
    a("versionar el dataset requiere saber que se hizo con lo que falta, aunque hoy")
    a("no falte nada. Esta seccion es esa respuesta.")
    a("")
    a("| metodo_imputacion | imputado | Filas |")
    a("|---|---|---|")
    for metodo, imputado, cuenta in imputacion:
        a(f"| `{metodo}` | {str(imputado).lower()} | {cuenta} |")
    a("")
    total_imputadas = sum(c for _, imp, c in imputacion if imp)
    if total_imputadas == 0:
        a("**Ninguna fila fue imputada.** No es que no se haya aplicado la regla: es")
        a("que no hubo sobre que aplicarla. Decirlo explicitamente es distinto de")
        a("callarlo, y el dia que Sentinel-2 traiga huecos reales -H1.6- la")
        a("diferencia entre dos versiones de este manifiesto se va a poder leer.")
    else:
        a(f"**{total_imputadas} filas llevan algun valor imputado.** La regla que se")
        a("aplico la declara H1.4.")
    a("")

    a("## Sumas del contenido cargado")
    a("")
    a("Responden si dos copias del dataset son la misma. Dos personas con el mismo")
    a("dataset llegan al mismo numero; si difieren, sus copias no son iguales.")
    a("")
    a("| Tabla | sha256 |")
    a("|---|---|")
    for t in tablas:
        a(f"| `{t['esquema']}.{t['tabla']}` | `{t['suma']}` |")
    a("")

    a("### Como se calcula, para que se pueda recalcular")
    a("")
    a("**Se excluye la metadata de carga.** `crudo.medicion_diaria` y")
    a("`crudo.foco_calor` declaran `descargado_en timestamptz NOT NULL DEFAULT")
    a("now()`. Incluirla haria que dos personas con datos identicos obtuvieran")
    a("sumas distintas, porque cada una cargo en otro momento.")
    a("")
    a(f"Columnas descartadas: {', '.join(sorted(COLUMNAS_EXCLUIDAS))}.")
    a("")
    for t in tablas:
        a(f"**`{t['esquema']}.{t['tabla']}`**, {len(t['columnas'])} columnas:")
        a("")
        a(f"    {', '.join(t['columnas'])}")
        a("")
        a("```sql")
        for linea in t["consulta"].splitlines():
            a(linea)
        a("```")
        a("")

    a("## Suma de la fuente descargada")
    a("")
    a("Responde de donde vino el dato. Es la regla 1 de D-29: el SNIT es la fuente")
    a("que ya fallo una vez -I-03- y la que produjo I-10. Si republica su capa,")
    a("esta suma cambia y se ve.")
    a("")
    a("Se toma de `basedatos/ddl/procedencia-geometrias.md`, que la calculo sobre")
    a("los bytes crudos en el momento de la descarga. **No se recalcula**: pedirle")
    a("la capa al SNIT hoy daria la suma de hoy, que es justo lo que se quiere")
    a("poder comparar contra esta.")
    a("")
    a("| Capa | sha256 |")
    a("|---|---|")
    for capa, suma in snit:
        a(f"| {capa} | `{suma}` |")
    a("")

    a("## Lo que este manifiesto NO afirma")
    a("")
    a("**Que el dato sea correcto.** Prueba que dos personas tienen lo mismo, no")
    a("que ese algo este bien. La calidad la mide H1.5.")
    a("")
    a("**Que la base siga en este estado.** El manifiesto es una foto. Cuando el")
    a("dataset se recargue hay que regenerarlo, y si alguien recarga y no lo")
    a("regenera, **el manifiesto miente**. Hoy no lo comprueba ninguna maquina:")
    a("D-29 lo deja anotado como deuda y no es parte de H1.7.")
    a("")

    return "\n".join(lineas) + "\n"


# --------------------------------------------------------------------------- #


def main(argumentos=None) -> int:
    analizador = argparse.ArgumentParser(
        description="Genera el manifiesto del dataset consolidado (H1.7, D-29).",
    )
    analizador.add_argument(
        "--version",
        required=True,
        help="Version declarada del dataset, por ejemplo v1. D-29 regla 3: se declara, no se infiere.",
    )
    analizador.add_argument(
        "--fecha",
        required=True,
        type=date.fromisoformat,
        help="Fecha de la version, AAAA-MM-DD. No es la hora de generacion.",
    )
    analizador.add_argument(
        "--salida",
        default=str(RUTA_SALIDA),
        help="Ruta del manifiesto. Un guion escribe a la salida estandar.",
    )
    opciones = analizador.parse_args(argumentos)

    try:
        with conectar() as conexion, conexion.cursor() as cursor:
            tablas = [medir_tabla(cursor, e, t, f, p) for e, t, f, p in TABLAS]
            dentro = focos_dentro_del_canton(cursor)
            imputacion = estado_de_imputacion(cursor)
        contenido = escribir_manifiesto(
            opciones.version, opciones.fecha, tablas, dentro, sumas_del_snit(), imputacion
        )
    except ErrorManifiesto as error:
        print(f"FALLA: {error}", file=sys.stderr)
        return 2

    if opciones.salida == "-":
        sys.stdout.write(contenido)
        return 0

    destino = Path(opciones.salida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(contenido, encoding="utf-8", newline="\n")
    print(f"Manifiesto {opciones.version} escrito en {destino}")
    for t in tablas:
        print(
            f"  {t['esquema']}.{t['tabla']:<16} {t['filas']:>7} filas  sha256 {t['suma'][:16]}..."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
