"""
Forma de los errores de la API. Dueno: Cesar. Historia H6.1, issue #59.

Este es el UNICO modelo propio de la capa de API. Todo lo demas se importa de
contratos/esquemas.py: una copia de un esquema del contrato seria una segunda
definicion que se desincroniza en silencio, y los contratos ya cambiaron dos veces
en dos semanas.

El error no esta en el contrato porque no es un dato del dominio: es como esta API
comunica una falla. Si algun dia el contrato define uno, este se borra.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Error(BaseModel):
    """Respuesta de error. Aparece en OpenAPI para que el consumidor la conozca."""

    model_config = ConfigDict(frozen=True)

    detalle: str = Field(
        description="Que fallo, en lenguaje entendible por quien llama",
        examples=["No existe el distrito 00000"],
    )
