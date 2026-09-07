"""
Pruebas del pool acotado de H8.2. Dueno: Alejandro.

No salen a la red ni tocan la base: funciones de juguete con esperas
controladas. Lo que se prueba es el contrato del modulo -orden, fallos,
secuencial de verdad, tope- porque es de lo que depende que la medicion de la
historia signifique algo.

Las esperas son de centesimas de segundo: la suite completa tiene que seguir
corriendo en el CI sin volverse lenta.
"""

from __future__ import annotations

import threading
import time

import pytest

from backend.etl.concurrencia import TRABAJADORES, Medicion, mapear, serializar

ESPERA = 0.05


def dormir(segundos: float) -> float:
    time.sleep(segundos)
    return segundos


def test_el_resultado_sale_en_el_orden_de_entrada_no_en_el_de_terminacion():
    # La primera tarda mas que la ultima: si el orden fuera el de terminacion,
    # esta lista saldria al reves.
    esperas = [4 * ESPERA, 2 * ESPERA, ESPERA]
    resultados, _ = mapear(dormir, esperas, trabajadores=3)
    assert resultados == esperas


def test_con_un_trabajador_no_se_crean_hilos():
    hilos = []
    mapear(lambda _: hilos.append(threading.current_thread().name), range(4), trabajadores=1)
    assert set(hilos) == {threading.current_thread().name}


def test_con_varios_trabajadores_el_trabajo_se_reparte_entre_hilos():
    _, medicion = mapear(dormir, [ESPERA] * 4, trabajadores=4)
    assert len(medicion.hilos) > 1
    assert threading.current_thread().name not in medicion.hilos


def test_el_reloj_es_menor_que_la_suma_de_las_tareas():
    _, medicion = mapear(dormir, [ESPERA] * 4, trabajadores=4)
    assert medicion.segundos < medicion.suma_de_tareas
    assert medicion.aceleracion > 1.0


def test_secuencial_no_acelera_nada_y_lo_dice():
    _, medicion = mapear(dormir, [ESPERA] * 3, trabajadores=1)
    assert medicion.trabajadores == 1
    assert medicion.segundos >= medicion.suma_de_tareas


def test_el_pool_no_abre_mas_hilos_que_el_tope():
    _, medicion = mapear(dormir, [ESPERA] * 12, trabajadores=3)
    assert len(medicion.hilos) <= 3


def test_el_pool_no_abre_mas_hilos_que_tareas():
    _, medicion = mapear(dormir, [ESPERA] * 2, trabajadores=8)
    assert medicion.trabajadores == 2
    assert len(medicion.hilos) <= 2


def test_un_fallo_se_propaga_y_no_devuelve_una_lista_incompleta():
    def falla_en_el_dos(numero: int) -> int:
        if numero == 2:
            raise ValueError("provocado")
        time.sleep(ESPERA)
        return numero

    with pytest.raises(ValueError, match="provocado"):
        mapear(falla_en_el_dos, range(6), trabajadores=3)


def test_se_propaga_el_fallo_de_menor_indice_aunque_otro_falle_antes_por_reloj():
    # El indice 3 falla de inmediato; el 1 falla despues. El error que se ve
    # tiene que ser siempre el mismo, o no se puede reproducir.
    def falla(numero: int) -> int:
        if numero == 1:
            time.sleep(3 * ESPERA)
            raise ValueError("indice 1")
        if numero == 3:
            raise ValueError("indice 3")
        time.sleep(ESPERA)
        return numero

    with pytest.raises(ValueError, match="indice 1"):
        mapear(falla, range(5), trabajadores=5)


def test_tras_un_fallo_las_tareas_que_no_empezaron_no_corren():
    corridas: list[int] = []
    candado = threading.Lock()

    def tarea(numero: int) -> int:
        if numero == 0:
            raise ValueError("provocado")
        time.sleep(ESPERA)
        with candado:
            corridas.append(numero)
        return numero

    with pytest.raises(ValueError):
        mapear(tarea, range(20), trabajadores=2)
    # Con dos trabajadores y veinte tareas, el fallo de la primera tiene que
    # cortar la cola: si corrieran todas, esto seria 19.
    assert len(corridas) < 19


def test_la_medicion_cuenta_una_duracion_por_tarea():
    _, medicion = mapear(dormir, [ESPERA] * 5, trabajadores=2, etiqueta="prueba")
    assert medicion.etiqueta == "prueba"
    assert medicion.tareas == 5
    assert len(medicion.por_tarea) == 5
    assert all(d > 0 for d in medicion.por_tarea)


def test_una_lista_vacia_no_crea_pool_ni_falla():
    resultados, medicion = mapear(dormir, [], trabajadores=4)
    assert resultados == []
    assert medicion.tareas == 0
    assert medicion.aceleracion == 0.0


def test_la_medicion_se_puede_leer_como_texto():
    texto = str(
        Medicion(etiqueta="x", trabajadores=2, tareas=3, segundos=1.0, por_tarea=(1.0, 1.0))
    )
    assert "x" in texto and "2 trabajadores" in texto


def test_el_tope_declarado_es_razonable():
    # No es una preferencia: un tope de 1 haria que la historia no exista, y
    # uno muy alto seria hostigar a dos servicios publicos y gratuitos.
    assert 2 <= TRABAJADORES <= 8


def test_serializar_no_deja_que_dos_hilos_escriban_encimados():
    lineas: list[str] = []

    def registrar_lento(*partes: object) -> None:
        # Imita `bitacora.abrir`: varias operaciones que no son atomicas juntas.
        texto = " ".join(str(p) for p in partes)
        mitad = texto[: len(texto) // 2]
        time.sleep(0.001)
        lineas.append(mitad + texto[len(texto) // 2 :])

    registrar = serializar(registrar_lento)
    mapear(lambda i: registrar(f"linea {i} " + "x" * 20), range(8), trabajadores=4)

    assert len(lineas) == 8
    assert all(linea.endswith("x" * 20) for linea in lineas)
