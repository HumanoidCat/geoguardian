"""
Endpoints de la API. Dueno: Cesar. Historia H6.1, issue #59.

REGLA DE ESTE ARCHIVO

No importa ninguna implementacion concreta de `Repositorio`. Solo el protocolo.
La implementacion llega por inyeccion de dependencias y se decide en
backend/api/dependencias.py. El criterio CA-6 comprueba que aqui no aparezca
`contratos.simulados`.

Todos los modelos de respuesta salen de `contratos/esquemas.py`. La API no
redefine ni uno: el contrato dice de si mismo que define la forma de todo lo que
cruza la frontera del sistema, y una copia se desincroniza en silencio.

SOLO LECTURA

No hay endpoints de escritura. La ingesta la hace el ETL conectandose a la base
con el rol `geoguardian_etl` de H1.8. Un endpoint de escritura seria una segunda
puerta a los mismos datos, con permisos propios que contradirian esos roles.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from backend.api.dependencias import (
    base_conectada,
    modo_de,
    obtener_repositorio,
    ultima_ingesta_de,
)
from backend.api.errores import Error
from contratos import VERSION_CONTRATOS
from contratos.enums import TipoEvento
from contratos.esquemas import Distrito, MedicionDiaria, Riesgo, Salud
from contratos.repositorio import Repositorio

VERSION_API = "0.1.0"

router = APIRouter()

# El repositorio, tipado contra el PROTOCOLO. Este alias es lo que hace que
# cambiar la implementacion no toque ninguna firma de endpoint.
Repo = Annotated[Repositorio, Depends(obtener_repositorio)]

CodigoDistrito = Annotated[
    str,
    Path(
        description="Codigo oficial del distrito, cinco digitos",
        examples=["50801"],
        pattern=r"^\d{5}$",
    ),
]


@router.get(
    "/salud",
    response_model=Salud,
    summary="Estado de la API",
    description=(
        "El frontend lo consulta al arrancar. Cuando `modo` es `simulado` tiene "
        "que mostrar un aviso visible: los datos no son reales."
    ),
    tags=["estado"],
)
def salud(repositorio: Repo) -> Salud:
    # Ninguno de los tres campos se escribe a mano: los tres se le preguntan a la
    # implementacion que efectivamente contesto. `modo` ya era asi desde H6.1; los
    # otros dos eran constantes -`False` y `None`- puestas cuando H6.1 no abria
    # conexion, y ciertas entonces. H6.2 las volvio falsas y sobrevivieron nueve
    # dias porque ningun criterio preguntaba por ellas con el repositorio real.
    # Ver I-41 y el criterio CA-7 de verificar_h61.py, que ahora si pregunta.
    return Salud(
        version_api=VERSION_API,
        version_contratos=VERSION_CONTRATOS,
        modo=modo_de(repositorio),
        base_datos_conectada=base_conectada(repositorio),
        ultima_ingesta=ultima_ingesta_de(repositorio),
    )


@router.get(
    "/distritos",
    response_model=list[Distrito],
    summary="Todos los distritos del canton",
    description="Con su geometria en GeoJSON EPSG:4326, lista para dibujar.",
    tags=["territorio"],
)
def listar_distritos(repositorio: Repo) -> list[Distrito]:
    return repositorio.listar_distritos()


@router.get(
    "/distritos/{codigo}",
    response_model=Distrito,
    responses={404: {"model": Error, "description": "El codigo no corresponde a ningun distrito"}},
    summary="Un distrito por su codigo",
    tags=["territorio"],
)
def obtener_distrito(repositorio: Repo, codigo: CodigoDistrito) -> Distrito:
    distrito = repositorio.obtener_distrito(codigo)
    if distrito is None:
        # 404 y no 500: el contrato dice que la ausencia es un caso valido y por
        # eso `obtener_distrito` devuelve None en vez de lanzar excepcion.
        raise HTTPException(status_code=404, detail=f"No existe el distrito {codigo}")
    return distrito


@router.get(
    "/distritos/{codigo}/mediciones",
    response_model=list[MedicionDiaria],
    responses={404: {"model": Error, "description": "El codigo no corresponde a ningun distrito"}},
    summary="Serie climatica diaria de un distrito",
    description=(
        "Devuelve una fila por cada dia del rango, incluidos los dias sin dato, "
        "con sus campos en `null`. Los huecos no se omiten: un hueco y un dia que "
        "no existe tienen que poder distinguirse."
    ),
    tags=["mediciones"],
)
def obtener_mediciones(
    repositorio: Repo,
    codigo: CodigoDistrito,
    desde: Annotated[date, Query(description="Primer dia del rango, inclusive")],
    hasta: Annotated[date, Query(description="Ultimo dia del rango, inclusive")],
) -> list[MedicionDiaria]:
    if repositorio.obtener_distrito(codigo) is None:
        raise HTTPException(status_code=404, detail=f"No existe el distrito {codigo}")
    if hasta < desde:
        raise HTTPException(status_code=422, detail="El rango termina antes de empezar")
    return repositorio.obtener_mediciones(codigo, desde, hasta)


@router.get(
    "/distritos/{codigo}/riesgo",
    response_model=Riesgo,
    responses={
        404: {
            "model": Error,
            "description": "El distrito no existe, o no hay estimacion para esa combinacion",
        }
    },
    summary="Riesgo estimado de un distrito",
    description=(
        "Mientras no exista un modelo entrenado, `nivel`, `probabilidad` y "
        "`explicacion` viajan en `null`. No se rellenan con un valor plausible."
    ),
    tags=["riesgo"],
)
def obtener_riesgo(
    repositorio: Repo,
    codigo: CodigoDistrito,
    fecha: Annotated[date, Query(description="Fecha de la estimacion")],
    tipo_evento: Annotated[TipoEvento, Query(description="Evento estimado")],
) -> Riesgo:
    if repositorio.obtener_distrito(codigo) is None:
        raise HTTPException(status_code=404, detail=f"No existe el distrito {codigo}")

    riesgo = repositorio.obtener_riesgo(codigo, fecha, tipo_evento)
    if riesgo is None:
        # El contrato: "None si no hay estimacion para esa combinacion. No se
        # inventa una." Devolver un Riesgo con todo en null seria inventar que la
        # estimacion existe y esta vacia, que no es lo mismo que no existir.
        raise HTTPException(
            status_code=404,
            detail=f"No hay estimacion de {tipo_evento.value} para {codigo} el {fecha}",
        )
    return riesgo


@router.get(
    "/riesgos",
    response_model=list[Riesgo],
    summary="Riesgo de todos los distritos en una fecha",
    description="Es lo que consume el visor para pintar las coropletas.",
    tags=["riesgo"],
)
def listar_riesgos(
    repositorio: Repo,
    fecha: Annotated[date, Query(description="Fecha de la estimacion")],
    tipo_evento: Annotated[TipoEvento, Query(description="Evento estimado")],
) -> list[Riesgo]:
    return repositorio.obtener_riesgos_por_fecha(fecha, tipo_evento)
