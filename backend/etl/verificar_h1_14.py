"""
Verificador de H1.14: ingesta reejecutable con cadencia y producto declarados.

Criterios en docs/evidencias/bases-de-datos/H1.14-criterios-aceptacion.md.
CA-1 a CA-7 corren **sin red y sin base**: fuentes falsas registradas en la
fabrica de H6.3 y la conexion falsa de las pruebas del repositorio (H6.2),
que recuerda cada sentencia. Lo que se comprueba es lo que la ingesta le dice
a la base, no lo que la base haria con eso.

Con `--con-base` se agrega lo que solo PostgreSQL puede responder: que la
regla de reemplazo de precipitacion **sabe decir que no** (CA-5) y que una
segunda escritura identica no toca ninguna fila (CA-4). Va dentro de una
transaccion que se revierte, sobre un dia de 1985 que ninguna carga usa.
CA-8 es la corrida real y va en la evidencia, no aqui.

    python -m backend.etl.verificar_h1_14
    python -m backend.etl.verificar_h1_14 --con-base
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from backend.api.test_repositorio_postgres import ConexionFalsa, CursorFalso  # noqa: E402
from backend.etl import ingestar  # noqa: E402
from backend.etl.cargar_focos import HASTA as HASTA_FOCOS  # noqa: E402
from backend.etl.cargar_mediciones import HASTA as HASTA_MEDICIONES  # noqa: E402
from backend.etl.fuentes import fabrica, firms_area  # noqa: E402
from backend.etl.fuentes.chirps import ErrorChirps  # noqa: E402
from backend.etl.fuentes.firms import FocoBruto  # noqa: E402
from backend.etl.fuentes.hibrido import Territorio  # noqa: E402
from backend.modelado.verificar_h33 import Resultado  # noqa: E402
from contratos.esquemas import MedicionDiaria  # noqa: E402

HOY = date(2026, 9, 3)
AYER = HOY - timedelta(days=1)
TERRITORIOS = [
    Territorio(codigo="50801", nombre="Tilaran", geometria={}, longitud=-84.97, latitud=10.47),
    Territorio(
        codigo="50802", nombre="Quebrada Grande", geometria={}, longitud=-84.9, latitud=10.5
    ),
]


def momento(dias_atras: int) -> datetime:
    return datetime.combine(HOY - timedelta(days=dias_atras), datetime.min.time(), UTC)


# --------------------------------------------------------------------------- #
# Dobles                                                                       #
# --------------------------------------------------------------------------- #


class CursorConteo(CursorFalso):
    """Como el de H6.2, pero declara que no sabe contar filas afectadas."""

    rowcount = -1


class ConexionIngesta(ConexionFalsa):
    def cursor(self) -> CursorConteo:
        return CursorConteo(self)


@dataclass
class FuenteClimaFalsa:
    """Cumple ExtractorClima. `nulos_al_final` imita la latencia de la fuente."""

    nombre: str = "clima falsa H1.14"
    valor: float = 1.0
    responde: bool = True
    nulos_al_final: int = 0
    falla: bool = False
    pedidos: list[tuple[str, date, date]] = field(default_factory=list)

    def disponible(self) -> bool:
        return self.responde

    def extraer(self, codigo_distrito: str, desde: date, hasta: date) -> list[MedicionDiaria]:
        if self.falla:
            raise ErrorChirps("ClimateSERV rechazo la peticion (provocado)")
        self.pedidos.append((codigo_distrito, desde, hasta))
        dias = (hasta - desde).days + 1
        return [
            MedicionDiaria(
                codigo_distrito=codigo_distrito,
                fecha=desde + timedelta(days=i),
                temp_max_c=30.0,
                precipitacion_mm=None if i >= dias - self.nulos_al_final else self.valor,
            )
            for i in range(dias)
        ]

    def cerrar(self) -> None:
        pass


@dataclass
class FuenteFocosFalsa:
    """Imita la API por area: dice hasta donde llega cada version y da un foco por dia."""

    fin_final: date
    fin_preliminar: date = AYER
    responde: bool = True
    nombre: str = "focos falsa H1.14"
    productos: tuple[str, ...] = ("modis", "viirs-snpp")
    pedidos: list[tuple[str, bool, date, date]] = field(default_factory=list)

    def disponible(self) -> bool:
        return self.responde

    def disponibilidad(self) -> dict[tuple[str, str], tuple[date, date]]:
        salida = {}
        for base in self.productos:
            salida[(base, "final")] = (date(2000, 1, 1), self.fin_final)
            salida[(base, "preliminar")] = (date(2025, 1, 1), self.fin_preliminar)
        return salida

    def descargar(self, desde, hasta, base, preliminar, registrar=None) -> list[FocoBruto]:
        self.pedidos.append((base, preliminar, desde, hasta))
        codigo = firms_area.codigo_producto(base, preliminar)
        return [
            FocoBruto(
                producto=codigo,
                satelite="N",
                fecha=desde + timedelta(days=i),
                hora_utc=1830,
                latitud=10.47,
                longitud=-84.97,
                confianza="nominal",
                confianza_bruta=None,
                brillo_k=330.0,
                brillo_largo_k=300.0,
                banda_origen="viirs_i4",
                frp_mw=5.0,
                tipo=None,
                dia_noche="D",
            )
            for i in range((hasta - desde).days + 1)
        ]

    def extraer(self, desde, hasta):
        return []

    def cerrar(self) -> None:
        pass


# Registradas en la fabrica de H6.3, como cualquier fuente: la ingesta las
# recibe construidas por `crear_clima` / `crear_focos`.
fabrica.REGISTRO_CLIMA["falsa-h114"] = FuenteClimaFalsa
fabrica.REGISTRO_FOCOS["falsa-h114"] = FuenteFocosFalsa


def ejecutadas(conexion, texto: str) -> list[tuple]:
    return [s for s in conexion.sentencias() if texto in s[1]]


def lotes(conexion) -> list[tuple]:
    return [s for s in conexion.sentencias() if s[0] == "executemany"]


def correr_lluvia(evento: str, fuente, ultima=None, ultimo_dato: date | None = None):
    """
    Una corrida de precipitacion contra la conexion falsa, con sus respuestas en cola.

    La cola sigue el orden de las consultas de `correr`: ultima corrida, ultimo
    dia con dato (solo si toca correr), id de la corrida al abrirla.
    """
    respuestas = [[ultima] if ultima else []]
    if ingestar.toca_correr(evento, ingestar.UltimaCorrida(*ultima) if ultima else None, HOY)[0]:
        respuestas.append([(ultimo_dato,)])
        if evento == "sequia":
            respuestas.append([(None,)])  # ningun dia en preliminar
    respuestas.append([(7,)])
    conexion = ConexionIngesta(resultados=respuestas)
    salida: list[str] = []
    corrida = ingestar.correr(
        conexion, evento, HOY, salida.append, extractor=fuente, territorios=TERRITORIOS
    )
    return conexion, corrida, salida


# --------------------------------------------------------------------------- #
# Criterios                                                                    #
# --------------------------------------------------------------------------- #


def verificar() -> Resultado:
    r = Resultado()

    print("CA-1 · La cadencia es un dato")
    cadencia = ingestar.CADENCIA
    r.comprobar(
        "hay exactamente tres eventos", set(cadencia) == {"incendio", "lluvia_intensa", "sequia"}
    )
    r.comprobar(
        "incendio y lluvia intensa son diarios",
        cadencia["incendio"] == cadencia["lluvia_intensa"] == "diaria",
    )
    r.comprobar("sequia no es diaria: semanal", cadencia["sequia"] == "semanal")
    salida: list[str] = []
    ingestar.encabezado(salida.append, HOY)
    r.comprobar(
        "el guion imprime la cadencia y el producto al arrancar",
        any("Cadencia declarada" in s and "semanal" in s for s in salida)
        and any("Producto por evento" in s and "chirp" in s for s in salida),
    )

    print("CA-2 · La ventana sale de la cadencia y de la ultima corrida")
    hace3 = ingestar.UltimaCorrida(terminada_en=momento(3), ventana_hasta=HOY - timedelta(days=4))
    hace8 = ingestar.UltimaCorrida(terminada_en=momento(8), ventana_hasta=HOY - timedelta(days=9))
    corre, motivo = ingestar.toca_correr("sequia", hace3, HOY)
    r.comprobar(
        "sequia con ultima corrida hace 3 dias no corre, y dice por que",
        not corre and "3 dias" in motivo,
        motivo,
    )
    r.comprobar(
        "sequia con ultima corrida hace 8 dias corre", ingestar.toca_correr("sequia", hace8, HOY)[0]
    )
    r.comprobar(
        "incendio con ultima corrida hace 3 dias corre igual",
        ingestar.toca_correr("incendio", hace3, HOY)[0],
    )
    r.comprobar(
        "incendio: desde el dia siguiente a la ultima ventana, hasta ayer",
        ingestar.ventana_incendio(hace3, HOY) == (HOY - timedelta(days=3), AYER),
    )
    r.comprobar(
        "incendio sin corridas: desde donde termino H1.2",
        ingestar.ventana_incendio(None, HOY) == (HASTA_FOCOS + timedelta(days=1), AYER),
    )
    con = ConexionIngesta(resultados=[[(HOY - timedelta(days=5),)]])
    r.comprobar(
        "lluvia: desde SOLAPE_DIAS antes del ultimo dia con dato, hasta ayer",
        ingestar.ventana_precipitacion(con, "lluvia_intensa", HOY)
        == (HOY - timedelta(days=4 + ingestar.SOLAPE_DIAS), AYER),
    )
    r.comprobar(
        "el solape vuelve a pedir al menos un dia que ya tiene dato", ingestar.SOLAPE_DIAS >= 1
    )
    con = ConexionIngesta(resultados=[[(HOY - timedelta(days=5),)], [(HOY - timedelta(days=40),)]])
    r.comprobar(
        "sequia retrocede hasta el primer dia que sigue en preliminar",
        ingestar.ventana_precipitacion(con, "sequia", HOY) == (HOY - timedelta(days=40), AYER),
    )
    con = ConexionIngesta(resultados=[[(None,)]])
    r.comprobar(
        "lluvia sin datos nuevos: desde donde termino H1.1",
        ingestar.ventana_precipitacion(con, "lluvia_intensa", HOY)
        == (HASTA_MEDICIONES + timedelta(days=1), AYER),
    )
    con = ConexionIngesta(resultados=[[(AYER,)]])
    r.comprobar(
        "lluvia al dia: no hay ventana",
        ingestar.ventana_precipitacion(con, "lluvia_intensa", HOY) is None,
    )
    r.comprobar(
        "la consulta de lluvia pide el ultimo dia CON dato, no la ultima fila",
        "precipitacion_mm IS NOT NULL" in ingestar.SQL_ULTIMO_DIA_LLUVIA,
    )
    _, corrida, salida = correr_lluvia(
        "sequia", fabrica.crear_clima("falsa-h114"), ultima=(momento(3), None)
    )
    r.comprobar(
        "una corrida de sequia fuera de cadencia queda omitida, con el motivo",
        corrida.estado == "omitida" and "3 dias" in corrida.mensaje,
    )

    print("CA-3 · Cada fila declara su producto")
    fuente = fabrica.crear_clima("falsa-h114", valor=4.5)
    con, corrida, _ = correr_lluvia("lluvia_intensa", fuente, ultimo_dato=HOY - timedelta(days=3))
    lote = lotes(con)
    r.comprobar("lluvia intensa escribe un solo lote", len(lote) == 1)
    filas = lote[0][2] if lote else []
    r.comprobar(
        "todas las filas de lluvia intensa declaran fuente_precipitacion = 'chirps' (D-40)",
        bool(filas) and all(f["fuente_precipitacion"] == "chirps" for f in filas),
    )
    esperadas = (2 + ingestar.SOLAPE_DIAS) * 2
    r.comprobar(
        f"son (2 dias nuevos + { ingestar.SOLAPE_DIAS } de solape) x 2 distritos = {esperadas} filas",
        len(filas) == esperadas,
        str(len(filas)),
    )
    apertura = ejecutadas(con, "INSERT INTO control.bitacora_etl")
    r.comprobar(
        "la corrida registra el producto que trajo",
        bool(apertura) and apertura[0][2][3] == "chirps",
    )
    con2, _, _ = correr_lluvia(
        "sequia", fabrica.crear_clima("falsa-h114"), ultimo_dato=HOY - timedelta(days=3)
    )
    filas2 = lotes(con2)[0][2] if lotes(con2) else []
    r.comprobar(
        "sequia declara 'chirps', el final",
        bool(filas2) and all(f["fuente_precipitacion"] == "chirps" for f in filas2),
    )
    r.comprobar(
        "el CHIRP viene del tipo 90 del catalogo y el final del 0",
        ingestar.TIPO_DATO_DE["chirp"] == "90" and ingestar.TIPO_DATO_DE["chirps"] == "0",
    )

    print("CA-4 · Idempotente")
    a, _, _ = correr_lluvia(
        "lluvia_intensa", fabrica.crear_clima("falsa-h114"), ultimo_dato=HOY - timedelta(days=3)
    )
    b, _, _ = correr_lluvia(
        "lluvia_intensa", fabrica.crear_clima("falsa-h114"), ultimo_dato=HOY - timedelta(days=3)
    )
    r.comprobar(
        "dos corridas iguales emiten exactamente las mismas sentencias", lotes(a) == lotes(b)
    )
    sql = ingestar.SQL_ESCRIBIR_MEDICION
    r.comprobar(
        "la escritura es INSERT ... ON CONFLICT (codigo_distrito, fecha) DO UPDATE",
        "ON CONFLICT (codigo_distrito, fecha) DO UPDATE" in sql,
    )
    r.comprobar(
        "el DO UPDATE lleva WHERE: una fila que no cambia no se toca (filas=0 en la segunda corrida)",
        "WHERE medicion_diaria.precipitacion_mm IS DISTINCT FROM" in sql,
    )

    print("CA-5 · El final reemplaza al preliminar, nunca al reves; riesgo no se toca")
    r.comprobar(
        "la regla de reemplazo esta escrita en el SQL de las dos columnas",
        sql.count(ingestar.REEMPLAZA) >= 2,
    )
    r.comprobar(
        "la regla: el preliminar no pisa un valor del final",
        "fuente_precipitacion = 'chirps'" in ingestar.REEMPLAZA
        and "EXCLUDED.fuente_precipitacion <> 'chirps'" in ingestar.REEMPLAZA,
    )
    r.comprobar(
        "la regla: un nulo no pisa un valor",
        ingestar.REEMPLAZA.startswith("EXCLUDED.precipitacion_mm IS NOT NULL"),
    )
    r.comprobar(
        "la ingesta no escribe en analitico.riesgo",
        not any("analitico" in s[1] for s in a.sentencias()),
    )
    focos = fabrica.crear_focos("falsa-h114", fin_final=HOY - timedelta(days=40))
    con = ConexionIngesta(
        resultados=[
            [],  # ultima corrida: ninguna
            [(11,)],  # id de la corrida
            [(HOY - timedelta(days=60), HOY - timedelta(days=20))],  # rango nrt modis
            [(None, None)],  # rango nrt viirs: nada cargado
        ]
    )
    salida = []
    corrida = ingestar.correr(con, "incendio", HOY, salida.append, extractor=focos)
    borrados = ejecutadas(con, "DELETE FROM crudo.foco_calor")
    r.comprobar(
        "incendio: los NRT que el SP ya cubre se borran, solo esos",
        len(borrados) == 1
        and borrados[0][2] == ("modis-nrt", HOY - timedelta(days=60), HOY - timedelta(days=40)),
    )
    sp = [p for (b, prelim, d, h) in focos.pedidos if not prelim for p in [(b, d, h)]]
    r.comprobar(
        "y se piden en SP para el mismo rango",
        (("modis", HOY - timedelta(days=60), HOY - timedelta(days=40)) in sp),
    )
    productos = {f["producto"] for lote_ in lotes(con) for f in lote_[2]}
    r.comprobar(
        "las filas nuevas declaran su version: sp con el codigo base, nrt con -nrt",
        productos == {"modis", "modis-nrt", "viirs-snpp", "viirs-snpp-nrt"},
        str(productos),
    )
    nrt = [(d, h) for (b, prelim, d, h) in focos.pedidos if prelim]
    r.comprobar(
        "el NRT solo se pide para los dias que el SP no cubre",
        bool(nrt) and all(d == HOY - timedelta(days=39) and h == AYER for d, h in nrt),
        str(nrt),
    )
    eventos = con.eventos()
    i_tx = eventos.index("abre_transaccion") if "abre_transaccion" in eventos else -1
    i_del = next(
        (i for i, e in enumerate(con.bitacora) if e[0] == "execute" and "DELETE" in e[1]), -1
    )
    r.comprobar("borrar e insertar van en la misma transaccion", 0 <= i_tx < i_del)

    print("CA-6 · Cada corrida queda registrada")
    fuente = fabrica.crear_clima("falsa-h114")
    con, corrida, _ = correr_lluvia("lluvia_intensa", fuente, ultimo_dato=HOY - timedelta(days=3))
    apertura = ejecutadas(con, "INSERT INTO control.bitacora_etl")
    cierre = ejecutadas(con, "UPDATE control.bitacora_etl")
    r.comprobar(
        "apertura con proceso, ventana y producto",
        bool(apertura)
        and apertura[0][2]
        == (
            "ingesta.lluvia_intensa",
            HOY - timedelta(days=2 + ingestar.SOLAPE_DIAS),
            AYER,
            "chirps",
        ),
        str(apertura[0][2]) if apertura else "sin apertura",
    )
    declara = ejecutadas(con, "set_config('geoguardian.corrida_id'")
    r.comprobar(
        "declara geoguardian.corrida_id con el id de la corrida, dentro de la transaccion",
        bool(declara) and declara[0][2] == ("7",),
    )
    eventos = con.eventos()
    r.comprobar(
        "la declaracion va despues de abrir la transaccion",
        eventos.index("abre_transaccion")
        < next(i for i, e in enumerate(con.bitacora) if e[0] == "execute" and "set_config" in e[1]),
    )
    r.comprobar(
        "cierre exitoso con estado, filas e id",
        bool(cierre)
        and cierre[-1][2][0] == "exitosa"
        and cierre[-1][2][1] == (2 + ingestar.SOLAPE_DIAS) * 2
        and cierre[-1][2][3] == 7,
        str(cierre[-1][2]) if cierre else "sin cierre",
    )
    rota = fabrica.crear_clima("falsa-h114", falla=True)
    con, corrida, _ = correr_lluvia("lluvia_intensa", rota, ultimo_dato=HOY - timedelta(days=3))
    cierre = ejecutadas(con, "UPDATE control.bitacora_etl")
    r.comprobar(
        "una fuente que falla a medio camino queda registrada como fallida, con el motivo",
        corrida.estado == "fallida"
        and bool(cierre)
        and cierre[-1][2][0] == "fallida"
        and "provocado" in (cierre[-1][2][2] or ""),
    )
    r.comprobar("y no escribe ninguna fila", not lotes(con))

    print("CA-7 · Sin red no se inventa nada")
    muda = fabrica.crear_clima("falsa-h114", responde=False)
    con, corrida, _ = correr_lluvia("lluvia_intensa", muda, ultimo_dato=HOY - timedelta(days=3))
    r.comprobar("disponible() = False: cero lotes", not lotes(con))
    cierre = ejecutadas(con, "UPDATE control.bitacora_etl")
    r.comprobar(
        "y la corrida queda fallida con 'no responde'",
        corrida.estado == "fallida"
        and bool(cierre)
        and cierre[-1][2][0] == "fallida"
        and "no responde" in corrida.mensaje,
    )
    muda_focos = fabrica.crear_focos("falsa-h114", fin_final=AYER, responde=False)
    con = ConexionIngesta(resultados=[[], [(3,)]])
    corrida = ingestar.correr(con, "incendio", HOY, lambda *_: None, extractor=muda_focos)
    r.comprobar(
        "lo mismo para focos",
        corrida.estado == "fallida" and not lotes(con) and not muda_focos.pedidos,
    )
    con, corrida, _ = correr_lluvia(
        "lluvia_intensa",
        fabrica.crear_clima("falsa-h114", nulos_al_final=2),
        ultimo_dato=HOY - timedelta(days=5),
    )
    filas = lotes(con)[0][2]
    r.comprobar(
        "los dias que la fuente devuelve sin dato entran nulos, no en cero ni omitidos",
        len(filas) == (4 + ingestar.SOLAPE_DIAS) * 2
        and sum(1 for f in filas if f["precipitacion_mm"] is None) == 4,
    )

    return r


# --------------------------------------------------------------------------- #
# Con base: lo que solo PostgreSQL puede responder                             #
# --------------------------------------------------------------------------- #

DIA_PRUEBA = date(1985, 6, 15)
SQL_UN_DISTRITO = (
    "SELECT codigo FROM geo.distrito WHERE codigo_canton = 508 ORDER BY codigo LIMIT 1"
)
SQL_LEER = "SELECT precipitacion_mm, fuente_precipitacion FROM crudo.medicion_diaria WHERE codigo_distrito = %s AND fecha = %s"


def verificar_con_base(r: Resultado) -> None:
    from basedatos.conexion import conectar

    print("CA-5 y CA-4 contra PostgreSQL, en una transaccion que se revierte")
    with conectar() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(SQL_UN_DISTRITO)
            fila = cursor.fetchone()
        if fila is None:
            r.comprobar("hay un distrito en geo.distrito", False)
            return
        distrito = fila[0]
        try:
            with conexion.cursor() as cursor:
                cursor.execute("SELECT 1 FROM crudo.fuente WHERE codigo = 'chirp'")
                r.comprobar(
                    "la migracion 013 dejo la fuente 'chirp'", cursor.fetchone() is not None
                )
                cursor.execute("SELECT 1 FROM crudo.producto_foco WHERE codigo = 'viirs-snpp-nrt'")
                r.comprobar("y los productos NRT de focos", cursor.fetchone() is not None)
                cursor.execute("SELECT estado FROM control.bitacora_etl LIMIT 0")
                r.comprobar("y control.bitacora_etl", True)

                def escribir(valor, producto):
                    cursor.execute(
                        ingestar.SQL_ESCRIBIR_MEDICION,
                        {
                            "codigo_distrito": distrito,
                            "fecha": DIA_PRUEBA,
                            "temp_max_c": 30.0,
                            "temp_min_c": None,
                            "temp_media_c": None,
                            "humedad_relativa_pct": None,
                            "viento_ms": None,
                            "radiacion_mj_m2": None,
                            "precipitacion_mm": valor,
                            "fuente_precipitacion": producto,
                        },
                    )
                    return cursor.rowcount

                def leer():
                    cursor.execute(SQL_LEER, (distrito, DIA_PRUEBA))
                    return cursor.fetchone()

                cursor.execute(
                    "DELETE FROM crudo.medicion_diaria WHERE codigo_distrito = %s AND fecha = %s",
                    (distrito, DIA_PRUEBA),
                )
                escribir(5.0, "chirp")
                r.comprobar("entra el preliminar en un dia vacio", leer() == (5.0, "chirp"))
                escribir(7.0, "chirps")
                r.comprobar("el final reemplaza al preliminar", leer() == (7.0, "chirps"))
                escribir(9.0, "chirp")
                r.comprobar(
                    "el preliminar NO pisa el valor del final (sabe decir que no)",
                    leer() == (7.0, "chirps"),
                )
                escribir(None, "chirps")
                r.comprobar("un nulo del final no borra el valor", leer() == (7.0, "chirps"))
                cambiadas = escribir(7.0, "chirps")
                r.comprobar(
                    "CA-4: una escritura identica no toca la fila (rowcount 0)",
                    cambiadas == 0,
                    str(cambiadas),
                )
                cursor.execute(
                    "DELETE FROM crudo.medicion_diaria WHERE codigo_distrito = %s AND fecha = %s",
                    (distrito, DIA_PRUEBA),
                )
                escribir(None, "chirps")
                escribir(3.0, "chirp")
                r.comprobar(
                    "un nulo del final si se completa con el preliminar, declarado",
                    leer() == (3.0, "chirp"),
                )
        finally:
            conexion.rollback()
        with conexion.cursor() as cursor:
            cursor.execute(SQL_LEER, (distrito, DIA_PRUEBA))
            r.comprobar(
                "todo se revirtio: el dia de prueba no existe en la tabla",
                cursor.fetchone() is None,
            )


def main() -> int:
    analizador = argparse.ArgumentParser(description="Verifica los criterios de H1.14")
    analizador.add_argument(
        "--con-base", action="store_true", help="Agrega las comprobaciones contra PostgreSQL"
    )
    opciones = analizador.parse_args()

    resultado = verificar()
    if opciones.con_base:
        verificar_con_base(resultado)

    print(f"\n{resultado.hechos - len(resultado.fallos)} de {resultado.hechos} criterios")
    if resultado.fallos:
        print("\nNO se cumplen:")
        for f in resultado.fallos:
            print(f"  - {f}")
        print()
        return 1
    print(
        "\nH1.14 cumple sus criterios de aceptacion (CA-8, la corrida real, va en la evidencia).\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
