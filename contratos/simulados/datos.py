"""Repositorio y extractores simulados. Datos deterministas, reproducibles y falsos."""

from __future__ import annotations

import json
import logging
import random
from datetime import date, timedelta
from pathlib import Path

from .. import VERSION_CONTRATOS
from ..enums import Algoritmo, MetodoImputacion, ModoOperacion, NivelRiesgo, TipoEvento
from ..esquemas import (
    Distrito,
    EventoHistorico,
    FocoCalor,
    IndiceDerivado,
    MedicionDiaria,
    MetricasModelo,
    ReporteCalidad,
    Riesgo,
    Salud,
)

log = logging.getLogger(__name__)

SEMILLA = 20260803

# Los ocho distritos de Tilaran. Codigo, nombre y area.
#
# Los codigos son los oficiales del SNIT: 5 = Guanacaste, 08 = Tilaran, y los dos
# ultimos digitos el distrito. NO son 505xx: ese es el canton de Carrillo. El
# error estuvo en los contratos hasta la version 1.2.0. Ver incidencia I-04.
#
# NI la geometria NI el area estan aca: las trae _distrito_real() del archivo
# que genera docs/herramientas/generar_geometrias_simulado.py desde la capa
# IGN_5_CO:limitedistrital_5k del SNIT. Ver D-13 e I-10.
#
# El area estuvo aca hasta el 24 de agosto, como ocho constantes. Contra la
# geometria oficial fallaban por mucho -Tronadora decia 30,2 km2 y su poligono
# mide 140,0- aunque el total del canton diera casi bien, lo que sugiere que
# estaban asignadas a los codigos equivocados. Se calcula, no se escribe.
_DISTRITOS = [
    ("50801", "Tilaran"),
    ("50802", "Quebrada Grande"),
    ("50803", "Tronadora"),
    ("50804", "Santa Rosa"),
    ("50805", "Libano"),
    ("50806", "Tierras Morenas"),
    ("50807", "Arenal"),
    ("50808", "Cabeceras"),
]


def _sorteo(*partes: object) -> random.Random:
    """
    Generador determinista, sembrado con los argumentos de la consulta.

    Es la pieza que hace reproducible a todo el repositorio simulado. Cada metodo
    que sortea llama a esta funcion con lo que identifica al dato pedido —un
    distrito y una fecha, por ejemplo— y obtiene siempre el mismo generador.

    `random.Random` con una cadena la deriva por SHA-512, que es estable entre
    procesos. `hash()` no lo seria: Python la aleatoriza en cada arranque.

    POR QUE NO SE USA UN GENERADOR COMPARTIDO

    Hasta la version 1.3.1 los metodos sorteaban contra `self._rnd`, un generador
    con estado que avanza en cada llamada. Eso hacia que la misma consulta
    devolviera algo distinto cada vez, y en `obtener_mediciones` producia algo
    peor: **un mismo dia tenia dos temperaturas segun el rango en que se lo
    pidiera**. Ver la incidencia I-08 y las solicitudes SC-03 y SC-04.
    """
    return random.Random("|".join([str(SEMILLA), *(str(p) for p in partes)]))


def _es_hueco(codigo_distrito: str, fecha: date) -> bool:
    """
    Si ese dia viene sin dato. Uno de cada veinte, aproximadamente.

    Se decide desde la FECHA, no desde la posicion dentro del rango pedido. La
    version anterior usaba `i % 20 == 7` sobre el indice del bucle, asi que un
    mismo dia era hueco o no segun donde cayera en la consulta. Lo detecto Cesar
    revisando SC-03.

    Y depende TAMBIEN del distrito. La primera version recibia `codigo_distrito`
    y no lo miraba, con el resultado de que los ocho distritos tenian hueco
    exactamente los mismos dias. Lo detecto Cesar revisando SC-04, y son dos
    problemas: el parametro prometia algo que la funcion no hacia, y no se podia
    escribir una prueba con un distrito con dato y otro sin el. Ese caso es el
    normal cuando una estacion se cae, y es justo lo que H1.4 reconvertida en
    verificacion de completitud tiene que saber detectar.
    """
    return _sorteo(codigo_distrito, fecha.isoformat(), "hueco").random() < 0.05


def _nivel_desde(probabilidad: float, tipo_evento: TipoEvento) -> NivelRiesgo:
    """
    Deriva el nivel de la probabilidad, en vez de sortearlo aparte.

    INCENDIO NO TIENE NIVEL MEDIO, y esta funcion lo respeta.

    Desde SC-05, `alto` para incendio significa «al menos un foco en la ventana
    de 7 dias». Es binario: o hay foco o no lo hay. El umbral viejo por
    percentiles del conteo tampoco producia tres clases —el P90 vale 0,0 en los
    ocho distritos, medido por Cesar sobre 242 focos en 24 anios— asi que emitir
    MEDIO aqui seria producir un valor que el contrato ya no admite.

    Un doble que emite valores imposibles bajo el contrato no sirve para
    sustituir al original, que es el argumento de SC-03.

    D-21 fijo que `probabilidad` es P(nivel = alto). Sortear las dos cosas por
    separado producia filas imposibles bajo esa definicion: el 20 de agosto, el
    distrito 50802 salio con nivel `bajo` y probabilidad 0,90. Ver SC-03.

    Los cortes en tercios son ARBITRARIOS y se declaran como tales. No son el
    umbral de ningun modelo: cuando H3.4 entrene un clasificador, sera el quien
    decida nivel y probabilidad de forma conjunta y esta funcion desaparece.

    Lo que no es arbitrario es la MONOTONIA: una probabilidad mayor nunca da un
    nivel menor. De esa propiedad dependen el mapa de calor de H5.4, que
    interpola la probabilidad, y el semaforo continuo de H7.1.
    """
    if tipo_evento is TipoEvento.INCENDIO:
        # Binario. El corte en la mitad es tan arbitrario como los tercios y se
        # declara igual: lo unico que el simulado garantiza es la monotonia.
        return NivelRiesgo.ALTO if probabilidad >= 1 / 2 else NivelRiesgo.BAJO

    if probabilidad >= 2 / 3:
        return NivelRiesgo.ALTO
    if probabilidad >= 1 / 3:
        return NivelRiesgo.MEDIO
    return NivelRiesgo.BAJO


_ARCHIVO_GEOMETRIAS = Path(__file__).resolve().parent / "geometrias_tilaran.json"

_territorio: dict[str, dict] | None = None


def _distrito_real(codigo: str) -> dict:
    """Contorno y superficie del distrito, tomados de la capa del SNIT.

    HASTA EL 24 DE AGOSTO ESTO DEVOLVIA UN CUADRADO

    La version anterior generaba ocho rectangulos de 0,04 grados sobre una
    grilla de 3x3, con `i % 3` e `i // 3` como fila y columna. **No eran
    ubicaciones aproximadas: no eran ubicaciones.** Existian para que el visor
    tuviera algo que dibujar antes de que hubiera geometria real, y lo decia su
    docstring.

    H1.3 trajo la capa oficial el 13 de agosto y nada conecto las dos cosas, asi
    que la grilla llego hasta el sitio publicado. Ver la incidencia **I-10**.

    POR QUE SE LEE DE UN ARCHIVO

    El simulado tiene que resolver sin base de datos y sin red -es lo que
    sostiene el trabajo en paralelo del acuerdo A1.3, y lo que corre en el CI-,
    asi que la geometria viene congelada en JSON. La genera
    `docs/herramientas/generar_geometrias_simulado.py` desde el SNIT.

    EL AREA TAMBIEN SALE DE AQUI

    Eran ocho constantes escritas a mano en `_DISTRITOS`. Contra la geometria
    oficial fallaban por mucho: Tronadora declaraba 30,2 km2 y su poligono mide
    140,0. El total del canton daba casi bien, lo que sugiere que los numeros
    estaban asignados a los codigos equivocados.

    El panel del visor muestra esa cifra al lado de la forma, asi que las dos
    tienen que salir de la misma fuente. La calcula el generador sobre
    EPSG:8908, igual que `cargar_distritos.py` se lo deja a PostGIS.

    Sigue siendo un simulado: **el riesgo que se pinta encima es inventado.** Lo
    que deja de ser falso es el territorio.
    """
    global _territorio

    if _territorio is None:
        if not _ARCHIVO_GEOMETRIAS.exists():
            raise FileNotFoundError(
                f"Falta {_ARCHIVO_GEOMETRIAS.name}, que trae los contornos reales del "
                "SNIT. Se genera con:\n\n"
                "    python docs/herramientas/generar_geometrias_simulado.py\n\n"
                "No se vuelve a los cuadrados de marcador de posicion: fue el "
                "defecto I-10."
            )
        documento = json.loads(_ARCHIVO_GEOMETRIAS.read_text(encoding="utf-8"))
        _territorio = documento["distritos"]

    return _territorio[codigo]


class RepositorioSimulado:
    """Cumple el protocolo Repositorio. No toca ninguna base de datos."""

    def __init__(self) -> None:
        # No hay generador compartido, y es a proposito: cada metodo siembra el
        # suyo con `_sorteo`. Dejar uno aqui sin usar seria una invitacion a que
        # alguien vuelva a sortear contra el, que es el defecto de I-08. Lo
        # senalo Cesar al revisar SC-04.
        log.warning("RepositorioSimulado en uso: los datos NO son reales")

    # -- Territorio --------------------------------------------------------- #

    def listar_distritos(self) -> list[Distrito]:
        return [
            Distrito(
                codigo=codigo,
                nombre=nombre,
                area_km2=_distrito_real(codigo)["area_km2"],
                poblacion=None,
                geometria=_distrito_real(codigo)["geometria"],
            )
            for codigo, nombre in _DISTRITOS
        ]

    def obtener_distrito(self, codigo: str) -> Distrito | None:
        return next((d for d in self.listar_distritos() if d.codigo == codigo), None)

    # -- Mediciones --------------------------------------------------------- #

    def guardar_mediciones(self, mediciones: list[MedicionDiaria]) -> int:
        return len(mediciones)

    def obtener_mediciones(
        self, codigo_distrito: str, desde: date, hasta: date
    ) -> list[MedicionDiaria]:
        """
        Serie diaria, DETERMINISTA por distrito y fecha.

        Incluye huecos a proposito: una de cada veinte fechas viene sin dato.

        **Una serie no se puede pedir en tandas.** Cada dia se sortea con su propia
        semilla, de modo que pedir del 1 al 5 y del 3 al 7 devuelve exactamente los
        mismos valores para el 3, el 4 y el 5. Antes no: el mismo dia tenia dos
        temperaturas distintas segun el rango. Le pegaba a cualquier calculo sobre
        ventanas moviles, como H2.5. Ver SC-04.
        """
        salida, actual = [], desde
        while actual <= hasta:
            sorteo = _sorteo(codigo_distrito, actual.isoformat())
            hueco = _es_hueco(codigo_distrito, actual)
            salida.append(
                MedicionDiaria(
                    codigo_distrito=codigo_distrito,
                    fecha=actual,
                    temp_max_c=None if hueco else round(sorteo.uniform(27, 34), 1),
                    temp_min_c=None if hueco else round(sorteo.uniform(17, 22), 1),
                    temp_media_c=None if hueco else round(sorteo.uniform(22, 27), 1),
                    precipitacion_mm=None if hueco else round(max(0.0, sorteo.gauss(4, 9)), 1),
                    humedad_relativa_pct=None if hueco else round(sorteo.uniform(60, 95), 1),
                    viento_ms=None if hueco else round(sorteo.uniform(1, 11), 1),
                    radiacion_mj_m2=None if hueco else round(sorteo.uniform(12, 24), 1),
                    imputado=False,
                    metodo_imputacion=MetodoImputacion.SIN_IMPUTAR,
                )
            )
            actual += timedelta(days=1)
        return salida

    # -- Focos de calor ----------------------------------------------------- #

    def guardar_focos(self, focos: list[FocoCalor]) -> int:
        return len(focos)

    def contar_focos(self, codigo_distrito: str, desde: date, hasta: date) -> int:
        """
        Focos de calor en el rango. Determinista y ADITIVO.

        Se cuenta dia por dia y se suma, en vez de sortear un numero para el rango
        entero. Asi contar dos ventanas contiguas da lo mismo que contar la ventana
        completa, que es como se comporta una consulta real sobre filas.

        Importa para H3.0: el etiquetado de incendio usa ventanas de 7 dias, y con
        un sorteo por rango dos ventanas solapadas se contradirian.
        """
        total, actual = 0, desde
        while actual <= hasta:
            # Un dia sin deteccion es un CERO, no un hueco. Es la distincion de
            # D-22: FIRMS informa ausencia de focos, no ausencia de dato.
            # De 0 a 3 y no de 0 a 1. Con un solo foco por dia como maximo, una
            # ventana de 7 dias tenia un techo duro de 7, que en FIRMS no existe:
            # un distrito puede tener varias detecciones el mismo dia. Lo midio
            # Cesar sobre 400 dias al revisar SC-04.
            total += _sorteo(codigo_distrito, actual.isoformat(), "focos").randint(0, 3)
            actual += timedelta(days=1)
        return total

    # -- Derivados y riesgo ------------------------------------------------- #

    def guardar_indices(self, indices: list[IndiceDerivado]) -> int:
        return len(indices)

    def obtener_indices(
        self, codigo_distrito: str, desde: date, hasta: date
    ) -> list[IndiceDerivado]:
        """Un punto cada siete dias, con los valores sembrados por fecha."""
        salida, actual = [], desde
        while actual <= hasta:
            sorteo = _sorteo(codigo_distrito, actual.isoformat(), "indices")
            salida.append(
                IndiceDerivado(
                    codigo_distrito=codigo_distrito,
                    fecha=actual,
                    spi_1m=round(sorteo.gauss(0, 1), 2),
                    spi_3m=round(sorteo.gauss(0, 1), 2),
                    anomalia_temp_c=round(sorteo.gauss(0, 1.5), 2),
                    dias_sin_lluvia=sorteo.randint(0, 20),
                )
            )
            actual += timedelta(days=7)
        return salida

    def guardar_riesgos(self, riesgos: list[Riesgo]) -> int:
        return len(riesgos)

    def obtener_riesgo(
        self, codigo_distrito: str, fecha: date, tipo_evento: TipoEvento
    ) -> Riesgo | None:
        """
        Riesgo simulado, DETERMINISTA en sus tres argumentos.

        No usa `self._rnd`. Ese generador tiene estado y avanza en cada llamada,
        asi que la misma consulta devolvia un valor distinto cada vez. Medido el
        20 de agosto sobre `GET /riesgos`, tres peticiones identicas dieron tres
        respuestas distintas. Ver SC-03 e incidencia I-08.

        POR QUE IMPORTA, Y POR QUE **NO** ES POR HTTP

        La primera version de este comentario decia que "un GET es idempotente por
        definicion". Es falso, y lo corrigio Cesar al revisar SC-03: la
        idempotencia de HTTP restringe el **efecto sobre el servidor**, no la
        representacion devuelta. Un `GET /hora-actual` es idempotente y responde
        algo distinto cada vez. El simulado viejo no violaba ninguna regla de HTTP.

        La razon correcta es la **sustituibilidad**: el repositorio de H6.2 va a
        ser determinista porque lee filas guardadas, y eso es propiedad del
        repositorio, no del metodo HTTP. Un doble que no cumple la propiedad por
        la que se lo puede poner en lugar del original no sirve para sustituirlo.
        """
        sorteo = _sorteo(codigo_distrito, fecha.isoformat(), tipo_evento.value)

        # El rango arranca en 0,05 y no en 0,3 para que los tres niveles sean
        # alcanzables. Con el minimo en 0,3 la probabilidad casi siempre caia por
        # encima del corte de un tercio y el nivel `bajo` no aparecia nunca.
        probabilidad = round(sorteo.uniform(0.05, 0.95), 2)

        return Riesgo(
            codigo_distrito=codigo_distrito,
            fecha=fecha,
            tipo_evento=tipo_evento,
            nivel=_nivel_desde(probabilidad, tipo_evento),
            probabilidad=probabilidad,
            algoritmo=Algoritmo.XGBOOST,
            version_modelo="simulado-0.0.0",
            explicacion=None,
        )

    def obtener_riesgos_por_fecha(self, fecha: date, tipo_evento: TipoEvento) -> list[Riesgo]:
        return [
            self.obtener_riesgo(d.codigo, fecha, tipo_evento)  # type: ignore[misc]
            for d in self.listar_distritos()
        ]

    # -- Eventos, calidad y modelos ----------------------------------------- #

    def listar_eventos(self, tipo_evento: TipoEvento | None = None) -> list[EventoHistorico]:
        base = [
            EventoHistorico(
                codigo_distrito="50801",
                tipo_evento=TipoEvento.LLUVIA_INTENSA,
                fecha_inicio=date(2021, 7, 20),
                fecha_fin=date(2021, 7, 23),
                severidad=NivelRiesgo.ALTO,
                fuente="SIMULADO: reemplazar con catalogo real de la historia H4.3",
                descripcion=None,
            ),
            EventoHistorico(
                codigo_distrito="50806",
                tipo_evento=TipoEvento.SEQUIA,
                fecha_inicio=date(2019, 2, 1),
                fecha_fin=date(2019, 5, 15),
                severidad=NivelRiesgo.ALTO,
                fuente="SIMULADO: reemplazar con catalogo real de la historia H4.3",
                descripcion=None,
            ),
            EventoHistorico(
                codigo_distrito="50807",
                tipo_evento=TipoEvento.INCENDIO,
                fecha_inicio=date(2020, 3, 10),
                fecha_fin=date(2020, 3, 14),
                severidad=NivelRiesgo.MEDIO,
                fuente="SIMULADO: reemplazar con catalogo real de la historia H4.3",
                descripcion=None,
            ),
        ]
        return [e for e in base if tipo_evento is None or e.tipo_evento == tipo_evento]

    def guardar_reporte_calidad(self, reporte: ReporteCalidad) -> None:
        return None

    def listar_reportes_calidad(self) -> list[ReporteCalidad]:
        return []

    def guardar_metricas(self, metricas: MetricasModelo) -> None:
        return None

    def listar_metricas(self) -> list[MetricasModelo]:
        """
        Vacio a proposito. Todavia no se entreno ningun modelo, asi que no hay
        metricas que reportar. Devolver numeros aqui seria inventar resultados.
        """
        return []


class ExtractorClimaSimulado:
    """Cumple el protocolo ExtractorClima. No hace peticiones de red."""

    nombre = "SIMULADO-clima"

    def __init__(self) -> None:
        log.warning("ExtractorClimaSimulado en uso: los datos NO son reales")
        self._repo = RepositorioSimulado()

    def disponible(self) -> bool:
        return True

    def extraer(self, codigo_distrito: str, desde: date, hasta: date) -> list[MedicionDiaria]:
        return self._repo.obtener_mediciones(codigo_distrito, desde, hasta)


class ExtractorFocosSimulado:
    """Cumple el protocolo ExtractorFocosCalor."""

    nombre = "SIMULADO-focos"

    def __init__(self) -> None:
        log.warning("ExtractorFocosSimulado en uso: los datos NO son reales")

    def disponible(self) -> bool:
        return True

    def extraer(self, desde: date, hasta: date) -> list[FocoCalor]:
        """
        Doce focos simulados en el rango, DETERMINISTAS.

        Este era el quinto sitio que sorteaba contra un generador con estado, y
        SC-04 no lo cubrio porque busque solo dentro de `RepositorioSimulado`. Lo
        encontro Cesar: el archivo tiene otra clase.

        Importa para H1.2, que implementa `ExtractorFocosCalor` de verdad: si el
        doble contra el que se compara no es reproducible, la prueba no prueba
        nada.
        """
        dias = max(0, (hasta - desde).days)
        focos = []
        for i in range(12):
            sorteo = _sorteo(desde.isoformat(), hasta.isoformat(), "foco", i)
            focos.append(
                FocoCalor(
                    fecha=desde + timedelta(days=sorteo.randint(0, dias)),
                    latitud=round(sorteo.uniform(10.40, 10.55), 4),
                    longitud=round(sorteo.uniform(-85.05, -84.85), 4),
                    confianza=sorteo.randint(30, 100),
                    brillo_k=round(sorteo.uniform(300, 360), 1),
                    satelite="SIMULADO",
                    codigo_distrito=None,
                )
            )
        return focos


def salud_simulada() -> Salud:
    """Estado que la API expone mientras corre con simulados."""
    return Salud(
        version_api="0.1.0",
        version_contratos=VERSION_CONTRATOS,
        modo=ModoOperacion.SIMULADO,
        base_datos_conectada=False,
        ultima_ingesta=None,
    )
