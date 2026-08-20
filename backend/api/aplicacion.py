"""
Aplicacion FastAPI. Dueno: Cesar. Historia H6.1, issue #59.

QUE HACE

Arma la aplicacion y su documento OpenAPI. La logica de los endpoints vive en
rutas.py y la resolucion del repositorio en dependencias.py: este archivo solo
compone.

SOBRE LA VERSION

El titulo y la version de los contratos salen de `contratos.VERSION_CONTRATOS` y
no escritos a mano. Los contratos cambiaron dos veces en dos semanas, a v1.2.0 por
los codigos de distrito y a v1.3.0 por el SPI, y una version copiada a mano habria
mentido las dos veces.

USO

    uvicorn backend.api.aplicacion:app --host 0.0.0.0 --port 8000

    documentacion interactiva:  http://localhost:8000/docs
    documento OpenAPI:          http://localhost:8000/openapi.json
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from backend.api.rutas import VERSION_API, router
from contratos import VERSION_CONTRATOS

DESCRIPCION = f"""
Estimacion de riesgo climatico por distrito para el canton de Tilaran.

Contratos **v{VERSION_CONTRATOS}**. Todos los esquemas de respuesta se importan de
`contratos/esquemas.py`: esta API no redefine ninguno.

**Solo lectura.** La ingesta la hace el ETL conectandose a la base con su propio
rol de minimo privilegio, no por HTTP.

**Consulte `/salud` antes de nada.** Si `modo` responde `simulado`, los datos no
son reales y hay que advertirlo a quien los mire.
"""


def crear_aplicacion() -> FastAPI:
    """Compone la aplicacion. Se usa tambien desde el verificador."""
    aplicacion = FastAPI(
        title="GeoGuardian API",
        description=DESCRIPCION,
        version=VERSION_API,
        openapi_tags=[
            {"name": "estado", "description": "Estado de la API y modo de operacion."},
            {"name": "territorio", "description": "Distritos del canton y sus geometrias."},
            {"name": "mediciones", "description": "Series climaticas diarias."},
            {"name": "riesgo", "description": "Estimaciones de riesgo por distrito."},
        ],
    )
    aplicacion.include_router(router)

    # La raiz redirige a la documentacion. Quien abre la direccion a secas se
    # topaba con un 404 sin explicacion.
    #
    # `include_in_schema=False` a proposito: esto es una comodidad, no parte de la
    # interfaz publicada. La superficie que OpenAPI describe sigue siendo la de
    # los seis endpoints acordados, y el criterio CA-4 la comprueba.
    @aplicacion.get("/", include_in_schema=False)
    def raiz() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    return aplicacion


app = crear_aplicacion()
