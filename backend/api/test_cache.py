"""
Pruebas de la cache. Dueno: Cesar. Historia H8.3, issue #65.

USO

    pytest backend/api/test_cache.py

**Sin base y sin red.** El repositorio de adentro es un doble que cuenta cuantas
veces lo llamaron, y el reloj es falso: asi el vencimiento se prueba parando el
tiempo un instante antes y un instante despues del limite, en vez de dormir. Una
prueba con `sleep` es lenta y, peor, se vuelve intermitente en una maquina
cargada.

Cada prueba nombra el criterio que ejercita. Estas cubren CA-1 a CA-7 y CA-12;
lo que necesita PostgreSQL vive en `verificar_h83.py` y `medir_cache.py`.
"""

from __future__ import annotations

import copy
from datetime import date, datetime

import pytest
from pydantic import ValidationError

from backend.api.cache import (
    AUSENTE,
    CacheConVencimiento,
    RepositorioConCache,
    cache_encendida,
    copia_de_lista,
)
from contratos.enums import TipoEvento
from contratos.esquemas import Distrito, MedicionDiaria, Riesgo

EVENTO = next(iter(TipoEvento))
FECHA = date(2026, 9, 14)


class Reloj:
    """Reloj falso. Solo avanza cuando la prueba lo dice."""

    def __init__(self, ahora: float = 1000.0) -> None:
        self.ahora = ahora

    def __call__(self) -> float:
        return self.ahora

    def avanzar(self, segundos: float) -> None:
        self.ahora += segundos


def _distrito(codigo: str) -> Distrito:
    return Distrito(
        codigo=codigo,
        nombre=f"Distrito {codigo}",
        area_km2=100.0,
        poblacion=1000,
        geometria={"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]]},
    )


class RepositorioFalso:
    """
    Cuenta cuantas veces lo llamaron, por metodo.

    Devuelve objetos nuevos en cada llamada, como haria el de verdad: asi, si la
    cache no guardara nada, la prueba lo veria en el contador y no en el valor.
    """

    def __init__(self, riesgo: Riesgo | None = None) -> None:
        self.llamadas: dict[str, int] = {}
        self._riesgo = riesgo

    def _anotar(self, metodo: str) -> None:
        self.llamadas[metodo] = self.llamadas.get(metodo, 0) + 1

    def listar_distritos(self) -> list[Distrito]:
        self._anotar("listar_distritos")
        return [_distrito("50801"), _distrito("50802")]

    def obtener_distrito(self, codigo: str) -> Distrito | None:
        self._anotar("obtener_distrito")
        return _distrito(codigo)

    def obtener_riesgo(self, codigo_distrito, fecha, tipo_evento) -> Riesgo | None:
        self._anotar("obtener_riesgo")
        return self._riesgo

    def obtener_riesgos_por_fecha(self, fecha, tipo_evento) -> list[Riesgo]:
        self._anotar("obtener_riesgos_por_fecha")
        return []

    def obtener_mediciones(self, codigo_distrito, desde, hasta) -> list[MedicionDiaria]:
        self._anotar("obtener_mediciones")
        return []

    def esta_viva(self) -> bool:
        self._anotar("esta_viva")
        return True

    def ultima_ingesta(self) -> datetime | None:
        self._anotar("ultima_ingesta")
        return None

    def guardar_riesgos(self, riesgos) -> int:
        self._anotar("guardar_riesgos")
        return len(riesgos)


@pytest.fixture
def reloj() -> Reloj:
    return Reloj()


@pytest.fixture
def falso() -> RepositorioFalso:
    return RepositorioFalso()


@pytest.fixture
def repositorio(falso, reloj) -> RepositorioConCache:
    return RepositorioConCache(falso, CacheConVencimiento(ttl=10.0, tope=4, reloj=reloj))


# -- Lo basico -------------------------------------------------------------- #


def test_la_segunda_llamada_no_toca_el_repositorio(repositorio, falso):
    repositorio.listar_distritos()
    repositorio.listar_distritos()
    assert falso.llamadas["listar_distritos"] == 1


def test_el_valor_devuelto_es_el_mismo_contenido(repositorio):
    primera = repositorio.listar_distritos()
    segunda = repositorio.listar_distritos()
    assert [d.codigo for d in primera] == [d.codigo for d in segunda]


def test_claves_distintas_no_se_pisan(repositorio, falso):
    repositorio.obtener_distrito("50801")
    repositorio.obtener_distrito("50802")
    repositorio.obtener_distrito("50801")
    assert falso.llamadas["obtener_distrito"] == 2


# -- CA-4, el vencimiento --------------------------------------------------- #


def test_ca4_un_instante_antes_del_vencimiento_sigue_sirviendo_lo_guardado(
    repositorio, falso, reloj
):
    repositorio.listar_distritos()
    reloj.avanzar(9.9)
    repositorio.listar_distritos()
    assert falso.llamadas["listar_distritos"] == 1


def test_ca4_al_cumplirse_el_vencimiento_vuelve_a_consultar(repositorio, falso, reloj):
    repositorio.listar_distritos()
    reloj.avanzar(10.0)
    repositorio.listar_distritos()
    assert falso.llamadas["listar_distritos"] == 2


def test_ca4_la_entrada_vencida_se_descarta_y_queda_contada(reloj):
    cache = CacheConVencimiento(ttl=10.0, tope=4, reloj=reloj)
    cache.guardar("k", "v")
    reloj.avanzar(10.0)

    assert cache.obtener("k") is AUSENTE
    assert cache.vencidas == 1
    assert len(cache) == 0


# -- CA-5, el tope y el desalojo -------------------------------------------- #


def test_ca5_el_numero_de_entradas_nunca_pasa_del_tope(reloj):
    cache = CacheConVencimiento(ttl=10.0, tope=2, reloj=reloj)
    for i in range(10):
        cache.guardar(f"k{i}", i)
    assert len(cache) == 2


def test_ca5_desaloja_la_menos_usada_recientemente_y_no_otra(reloj):
    """
    Lo que importa no es cuantas quedaron sino CUAL salio.

    Se guardan `a` y `b`, se vuelve a leer `a` -lo que la convierte en la mas
    reciente- y entra `c`. Con LRU tiene que salir `b`. Una cache que desalojara
    por orden de insercion sacaria `a` y esta prueba lo veria.
    """
    cache = CacheConVencimiento(ttl=10.0, tope=2, reloj=reloj)
    cache.guardar("a", 1)
    cache.guardar("b", 2)
    cache.obtener("a")
    cache.guardar("c", 3)

    assert cache.obtener("b") is AUSENTE
    assert cache.obtener("a") == 1
    assert cache.obtener("c") == 3
    assert cache.desalojadas == 1


# -- CA-6, la copia de salida ----------------------------------------------- #


def test_ca6_la_estrategia_por_omision_es_copiar_la_lista(falso, reloj):
    """
    Que la copia por omision sea la de la lista no es un detalle: es la decision
    que CA-10 corrigio. Copiar en profundidad costaba 76 ms contra los 33 ms de
    la consulta que la cache ahorra.
    """
    repositorio = RepositorioConCache(falso, CacheConVencimiento(ttl=10.0, reloj=reloj))
    assert repositorio._copiar is copia_de_lista


def test_ca6_modificar_lo_devuelto_no_corrompe_lo_guardado(repositorio):
    primera = repositorio.listar_distritos()
    primera.clear()

    segunda = repositorio.listar_distritos()
    assert len(segunda) == 2


def test_ca6_los_modelos_del_contrato_son_inmutables(repositorio):
    """
    Hallazgo del 2026-09-15: los esquemas de `contratos/` estan congelados, asi
    que asignarle un campo a un `Distrito` devuelto lanza `ValidationError`.
    Parte de lo que CA-6 queria evitar **ya lo impide el contrato**, no la cache.

    Se deja escrita y no se borra: si alguien descongelara los esquemas, la
    cache pasaria a necesitar mas proteccion de la que hoy tiene, y esto lo
    avisa en vez de dejarlo pasar en silencio.
    """
    distrito = repositorio.listar_distritos()[0]
    with pytest.raises(ValidationError):
        distrito.nombre = "PISADO"


def test_ca6_limite_declarado_el_diccionario_de_geometria_si_se_puede_corromper(repositorio):
    """
    **Esto no es un defecto sin descubrir: es el limite que CA-6 acepta a
    sabiendas, y esta escrito para que se vea.**

    Congelar impide reasignar un atributo, no modificar por dentro lo que ese
    atributo apunta. `geometria` es un diccionario y admite claves nuevas. Con la
    copia de lista, los modelos van compartidos, asi que quien lo modifique
    corrompe lo guardado.

    Evitarlo exige copiar en profundidad, y eso esta medido: 76 ms contra los
    33 ms de la consulta que la cache ahorra. Se paga el limite, no los 76 ms.

    La prueba afirma el comportamiento REAL. Si alguien volviera a la copia
    profunda, esta prueba falla y obliga a volver aqui a leer por que se decidio
    lo contrario.
    """
    primera = repositorio.listar_distritos()
    primera[0].geometria["type"] = "PISADO"

    segunda = repositorio.listar_distritos()
    assert segunda[0].geometria["type"] == "PISADO"


def test_ca6_la_copia_profunda_si_protege_ese_vector(falso, reloj):
    """
    El contraste que le da sentido al limite de arriba: con `deepcopy` el
    diccionario queda protegido. La opcion existe y se descarto por su costo,
    no porque no funcionara.
    """
    profundo = RepositorioConCache(
        falso, CacheConVencimiento(ttl=10.0, tope=4, reloj=reloj), copiar=copy.deepcopy
    )
    profundo.listar_distritos()[0].geometria["type"] = "PISADO"

    assert profundo.listar_distritos()[0].geometria["type"] == "Polygon"


def test_ca6_sin_copia_el_defecto_aparece(falso, reloj):
    """
    El sabotaje de CA-6, escrito como prueba permanente.

    Con `copiar=None` se devuelve la misma lista que quedo guardada, y un
    consumidor la vacia para todas las peticiones siguientes. Si esta prueba
    empezara a fallar significaria que la copia dejo de ser lo que protege, y
    entonces la de mas arriba ya no comprueba lo que dice comprobar.
    """
    sin_copia = RepositorioConCache(
        falso, CacheConVencimiento(ttl=10.0, tope=4, reloj=reloj), copiar=None
    )
    sin_copia.listar_distritos().clear()

    assert sin_copia.listar_distritos() == []


# -- CA-7, la ausencia ------------------------------------------------------ #


def test_ca7_la_ausencia_se_cachea_igual_que_la_presencia(reloj):
    falso = RepositorioFalso(riesgo=None)
    repositorio = RepositorioConCache(falso, CacheConVencimiento(ttl=10.0, tope=4, reloj=reloj))

    assert repositorio.obtener_riesgo("50801", FECHA, EVENTO) is None
    assert repositorio.obtener_riesgo("50801", FECHA, EVENTO) is None
    assert falso.llamadas["obtener_riesgo"] == 1


def test_ca7_ausente_y_none_no_son_lo_mismo(reloj):
    """
    El centinela existe para esto.

    Si `None` hiciera de «no esta», cachear una ausencia no serviria de nada:
    cada lectura la tomaria por un fallo y volveria a la base.
    """
    cache = CacheConVencimiento(ttl=10.0, tope=4, reloj=reloj)
    cache.guardar("k", None)

    assert cache.obtener("k") is None
    assert cache.obtener("otra") is AUSENTE


# -- CA-3, lo que no se cachea ---------------------------------------------- #


def test_ca3_esta_viva_pregunta_siempre(repositorio, falso):
    repositorio.esta_viva()
    repositorio.esta_viva()
    assert falso.llamadas["esta_viva"] == 2


def test_ca3_ultima_ingesta_pregunta_siempre(repositorio, falso):
    repositorio.ultima_ingesta()
    repositorio.ultima_ingesta()
    assert falso.llamadas["ultima_ingesta"] == 2


def test_las_mediciones_no_se_cachean(repositorio, falso):
    repositorio.obtener_mediciones("50801", FECHA, FECHA)
    repositorio.obtener_mediciones("50801", FECHA, FECHA)
    assert falso.llamadas["obtener_mediciones"] == 2


def test_las_escrituras_pasan_sin_tocar(repositorio, falso):
    """Llegan por __getattr__. Cachear una escritura no significa nada."""
    repositorio.guardar_riesgos([])
    repositorio.guardar_riesgos([])
    assert falso.llamadas["guardar_riesgos"] == 2


# -- CA-12, el interruptor -------------------------------------------------- #


def test_ca12_encendida_por_omision(monkeypatch):
    monkeypatch.delenv("GEOGUARDIAN_CACHE", raising=False)
    assert cache_encendida() is True


@pytest.mark.parametrize("valor", ["0", "false", "FALSE", "no", " 0 "])
def test_ca12_se_apaga_por_entorno(monkeypatch, valor):
    monkeypatch.setenv("GEOGUARDIAN_CACHE", valor)
    assert cache_encendida() is False


@pytest.mark.parametrize("valor", ["1", "true", "si", "cualquier cosa"])
def test_ca12_cualquier_otra_cosa_la_deja_encendida(monkeypatch, valor):
    monkeypatch.setenv("GEOGUARDIAN_CACHE", valor)
    assert cache_encendida() is True


# -- Configuracion invalida ------------------------------------------------- #


@pytest.mark.parametrize("ttl", [0, -1])
def test_un_ttl_no_positivo_se_rechaza(ttl):
    with pytest.raises(ValueError):
        CacheConVencimiento(ttl=ttl)


@pytest.mark.parametrize("tope", [0, -1])
def test_un_tope_no_positivo_se_rechaza(tope):
    with pytest.raises(ValueError):
        CacheConVencimiento(tope=tope)
