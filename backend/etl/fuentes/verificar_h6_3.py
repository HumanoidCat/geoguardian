"""
Verificador de H6.3. Dueno: Cesar.

USO

    python -m backend.etl.fuentes.verificar_h6_3

No necesita Docker ni red: los criterios son sobre la forma del codigo -que
exista el registro, que nadie importe una clase concreta- y no sobre el
resultado de una descarga.

QUE CAMBIO EL 2026-09-07, Y POR QUE

CA-4 comparaba los cargadores contra un hash congelado el 2026-09-03. Cuando
H1.14 edito `cargar_mediciones.py` por una razon que nada tiene que ver con
agregar fuentes, la comparacion empezo a fallar diciendo "cargadores
cambiados", que no es lo que habia pasado. **Era el mismo defecto de I-29 en mi
propio codigo:** un control que dice la verdad sobre lo que mide -los bytes son
distintos- y miente sobre lo que significa.

CA-4 nunca fue una propiedad que se pueda vigilar: era una **demostracion
fechada**. Contar cuantos archivos se tocan al agregar una fuente solo se puede
responder haciendo el experimento, una vez. Congelarlo dentro de un verificador
que corre para siempre lo convierte en una afirmacion que caduca sola.

El experimento se queda donde pertenece, en la evidencia, con sus hashes y su
fecha. Aca CA-4 comprueba lo que sigue siendo cierto hoy, y CA-3 se amplio a
`ingestar.py`, que desde H1.14 es el mayor consumidor de `fuentes/`.

LIMITE DECLARADO. CA-6 compara el bloque de argparse de cada cargador contra
una copia guardada y comprueba que los dos modulos importan limpio. **No
ejecuta una carga real contra la base**: eso necesita Docker levantado y las
dos APIs respondiendo, y no se hizo aca. Lo que se afirma es que la interfaz
de linea de comandos no cambio, no que la carga corrio.
"""

from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
DIR_ETL = RAIZ / "backend" / "etl"
#: Todo lo que consume `fuentes/` y no debe conocer una clase concreta.
#: `ingestar.py` entro aca el 2026-09-07: lo creo H1.14 con 870 lineas y es hoy
#: el mayor consumidor del paquete. Cuando se escribio este verificador no
#: existia.
CONSUMIDORES = (
    "cargar_distritos.py",
    "cargar_focos.py",
    "cargar_mediciones.py",
    "ingestar.py",
)
CLASES_PROHIBIDAS = {
    "ExtractorChirps",
    "ExtractorPower",
    "ExtractorHibrido",
    "ExtractorFirms",
    "ExtractorFirmsArea",
}

# Argumentos minimos para instanciar cada fuente registrada durante CA-2. Si
# alguien registra una fuente nueva y no la agrega aca, CA-2 falla en vez de
# saltearla en silencio: una comprobacion que se puede omitir sin que nadie se
# entere no comprueba nada.
ARGUMENTOS_DE_PRUEBA = {
    "hibrido": {"territorios": []},
    "prueba": {},
    "firms": {"caja": (-85.0, 10.0, -84.0, 11.0)},
    # La clave va explicita: `ExtractorFirmsArea` se niega a construirse sin
    # FIRMS_MAP_KEY, y esta comprobacion no debe depender de que el entorno la
    # tenga puesta. No sale a la red: solo se instancia y se mira el Protocol.
    "firms-area": {"caja": (-85.0, 10.0, -84.0, 11.0), "clave": "clave-de-prueba"},
}

ARGPARSE_MEDICIONES = """    analizador.add_argument("--desde", default=DESDE.isoformat())
    analizador.add_argument("--hasta", default=HASTA.isoformat())
    analizador.add_argument(
        "--distrito",
        action="append",
        help="Codigo de distrito. Repetible. Por defecto, los ocho.",
    )
    analizador.add_argument(
        "--solo-comprobar",
        action="store_true",
        help="Comprueba que las dos fuentes responden y no escribe nada",
    )
    analizador.add_argument(
        "--registro",
        help="Archivo donde guardar la salida completa, para la evidencia del PR",
    )
    analizador.add_argument(
        "--fallar-en",
        metavar="CODIGO",
        help=(
            "CA-12: aborta al llegar a ese distrito, despues de descargarlo y "
            "antes de confirmar su transaccion. Sirve para comprobar que una "
            "carga interrumpida no deja series parciales."
        ),
    )
"""

ARGPARSE_FOCOS = """    analizador.add_argument("--desde", default=DESDE.isoformat())
    analizador.add_argument("--hasta", default=HASTA.isoformat())
    analizador.add_argument(
        "--solo-comprobar",
        action="store_true",
        help="Comprueba que la fuente responde y no escribe nada",
    )
    analizador.add_argument(
        "--registro",
        help="Archivo donde guardar la salida completa, para la evidencia del PR",
    )
"""


class Resultado:
    def __init__(self) -> None:
        self.filas: list[tuple[str, bool, str]] = []

    def marcar(self, criterio: str, cumple: bool, detalle: str = "") -> None:
        self.filas.append((criterio, cumple, detalle))

    def imprimir(self) -> bool:
        for criterio, cumple, detalle in self.filas:
            print(f"{criterio}: {'CUMPLE' if cumple else 'FALLA'}")
            if detalle:
                print(f"    {detalle}")
        return all(cumple for _, cumple, _ in self.filas)


def ca1_registro(resultado: Resultado, fabrica) -> None:
    """
    Las fuentes que cumplen un Protocol estan en el registro.

    Son dos, no cuatro: chirps y power no implementan `ExtractorClima` -no
    tienen `extraer()`- y no son fuentes registrables. Esta correccion se
    hizo al construir el registro; el criterio escrito antes del codigo decia
    cuatro.
    """
    clima = set(fabrica.REGISTRO_CLIMA)
    focos = set(fabrica.REGISTRO_FOCOS)
    faltan = {"hibrido"} - clima | {"firms"} - focos
    resultado.marcar(
        "CA-1 el registro asocia nombre a implementacion y trae las fuentes reales",
        not faltan,
        f"clima: {sorted(clima)} · focos: {sorted(focos)}"
        + (f" · faltan: {sorted(faltan)}" if faltan else ""),
    )


def ca2_protocolo(resultado: Resultado, fabrica) -> None:
    from contratos.fuentes import ExtractorClima, ExtractorFocosCalor

    fallos = []
    comprobadas = []
    for nombre in fabrica.REGISTRO_CLIMA:
        if nombre not in ARGUMENTOS_DE_PRUEBA:
            fallos.append(f"{nombre} (sin argumentos declarados en el verificador)")
            continue
        if isinstance(fabrica.crear_clima(nombre, **ARGUMENTOS_DE_PRUEBA[nombre]), ExtractorClima):
            comprobadas.append(nombre)
        else:
            fallos.append(nombre)

    for nombre in fabrica.REGISTRO_FOCOS:
        if nombre not in ARGUMENTOS_DE_PRUEBA:
            fallos.append(f"{nombre} (sin argumentos declarados en el verificador)")
            continue
        instancia = fabrica.crear_focos(nombre, **ARGUMENTOS_DE_PRUEBA[nombre])
        if isinstance(instancia, ExtractorFocosCalor):
            comprobadas.append(nombre)
        else:
            fallos.append(nombre)

    resultado.marcar(
        "CA-2 cada fuente registrada cumple su Protocol",
        not fallos,
        f"fallaron: {fallos}"
        if fallos
        else f"comprobadas: {comprobadas} (runtime_checkable "
        "mira que los metodos existan, no sus firmas)",
    )


def ca3_sin_import_concreto(resultado: Resultado) -> None:
    ofensores = {}
    for nombre in CONSUMIDORES:
        arbol = ast.parse((DIR_ETL / nombre).read_text(encoding="utf-8"))
        importados = set()
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom):
                importados.update(alias.name for alias in nodo.names)
        if importados & CLASES_PROHIBIDAS:
            ofensores[nombre] = sorted(importados & CLASES_PROHIBIDAS)

    resultado.marcar(
        "CA-3 nadie que consuma fuentes/ importa una clase concreta",
        not ofensores,
        str(ofensores)
        if ofensores
        else f"limpios: {', '.join(CONSUMIDORES)}; siguen importando tipos de error y de "
        "dato (ErrorChirps, ErrorPower, ErrorFirms, FocoBruto) y constantes de producto, "
        "que no son extractores",
    )


def ca4_fuente_de_juguete(resultado: Resultado, fabrica) -> None:
    """
    Una fuente se agrega con su archivo y una entrada del registro.

    **Esto ya no compara hashes.** La demostracion de que agregar una fuente no
    toca ningun cargador se hizo el 2026-09-03, con los tres archivos comparados
    byte por byte antes y despues, y esta contada en la evidencia con sus sumas.
    Un experimento fechado no se puede repetir desde aca: los cargadores cambian
    por otras historias, y comparar contra el hash de aquel dia produce una falla
    que dice "cambiaron los cargadores" cuando lo que paso fue otra cosa.

    Lo que si sigue siendo comprobable es lo de abajo, y lo confirma ademas un
    hecho posterior que vale mas que cualquier hash: H1.14 agrego la fuente
    `firms-area` el 2026-09-05 **sin tocar ningun cargador**, y `ingestar.py` la
    pide por nombre a la fabrica.
    """
    archivo_nuevo = (DIR_ETL / "fuentes" / "prueba_fabrica.py").exists()
    registrada = "prueba" in fabrica.REGISTRO_CLIMA
    agregada_despues = "firms-area" in fabrica.REGISTRO_FOCOS

    resultado.marcar(
        "CA-4 una fuente se agrega con su archivo y una entrada del registro",
        archivo_nuevo and registrada,
        f"la de juguete: archivo propio {archivo_nuevo}, en el registro {registrada} · "
        f"y una real agregada despues por H1.14 sin tocar cargadores: {agregada_despues} · "
        "la comparacion byte por byte del 2026-09-03 esta en la evidencia, fechada",
    )


def ca5_error_nombrado(resultado: Resultado, fabrica) -> None:
    detalles = []
    ok = True

    try:
        fabrica.crear_clima("no-existe")
        ok = False
        detalles.append("crear_clima('no-existe') no lanzo nada")
    except fabrica.ErrorFuenteDesconocida as error:
        if "hibrido" not in str(error):
            ok = False
            detalles.append(f"no nombra las disponibles: {error}")
    except Exception as error:
        ok = False
        detalles.append(f"lanzo {type(error).__name__}, no ErrorFuenteDesconocida")

    try:
        fabrica.crear_focos("no-existe")
        ok = False
        detalles.append("crear_focos('no-existe') no lanzo nada")
    except fabrica.ErrorFuenteDesconocida as error:
        if "firms" not in str(error):
            ok = False
            detalles.append(f"no nombra las disponibles: {error}")
    except Exception as error:
        ok = False
        detalles.append(f"lanzo {type(error).__name__}, no ErrorFuenteDesconocida")

    resultado.marcar(
        "CA-5 pedir una fuente inexistente falla nombrando las disponibles",
        ok,
        "; ".join(detalles)
        if detalles
        else "ErrorFuenteDesconocida en los dos registros, "
        "con los nombres disponibles en el mensaje; nunca KeyError",
    )


def ca6_opciones_de_linea_de_comandos(resultado: Resultado) -> None:
    try:
        importlib.import_module("backend.etl.cargar_mediciones")
        importlib.import_module("backend.etl.cargar_focos")
    except Exception as error:
        resultado.marcar(
            "CA-6 las opciones de linea de comandos no cambiaron", False, f"import fallo: {error}"
        )
        return

    faltan = []
    if ARGPARSE_MEDICIONES not in (DIR_ETL / "cargar_mediciones.py").read_text(encoding="utf-8"):
        faltan.append("cargar_mediciones.py")
    if ARGPARSE_FOCOS not in (DIR_ETL / "cargar_focos.py").read_text(encoding="utf-8"):
        faltan.append("cargar_focos.py")

    resultado.marcar(
        "CA-6 las opciones de linea de comandos no cambiaron",
        not faltan,
        "los dos modulos importan limpio y su bloque de argparse esta byte por byte igual; "
        "no se corrio una carga real contra la base"
        if not faltan
        else f"bloque de argparse distinto en: {faltan}",
    )


def ca7_no_crea_orquestador(resultado: Resultado) -> None:
    resultado.marcar(
        "CA-7 (declarado) esta historia no crea el orquestador",
        True,
        "declarado en la cabecera de fabrica.py y en la evidencia; se declara, no se mide",
    )


def principal() -> int:
    sys.path.insert(0, str(RAIZ))
    from backend.etl.fuentes import fabrica

    resultado = Resultado()
    ca1_registro(resultado, fabrica)
    ca2_protocolo(resultado, fabrica)
    ca3_sin_import_concreto(resultado)
    ca4_fuente_de_juguete(resultado, fabrica)
    ca5_error_nombrado(resultado, fabrica)
    ca6_opciones_de_linea_de_comandos(resultado)
    ca7_no_crea_orquestador(resultado)

    todo_cumple = resultado.imprimir()
    print()
    print("Los siete criterios cumplen." if todo_cumple else "Hay criterios que fallan.")
    return 0 if todo_cumple else 1


if __name__ == "__main__":
    raise SystemExit(principal())
