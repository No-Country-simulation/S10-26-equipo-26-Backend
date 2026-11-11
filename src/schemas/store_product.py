from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StoreProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int | None = None
    tienda_id: int
    external_id: str
    source_url: str | None = None
    nombre_crudo: str
    marca_cruda: str | None = None
    raw_presentation: str | None = None
    created_at: datetime


class StoreProductCreate(BaseModel):
    producto_id: int | None = Field(default=None, ge=1)
    tienda_id: int = Field(ge=1)
    external_id: str = Field(min_length=1, max_length=255)
    source_url: str | None = None
    nombre_crudo: str = Field(min_length=1)
    marca_cruda: str | None = None
    raw_presentation: str | None = None


class StoreProductUpdate(BaseModel):
    """Asignacion/ajuste del match (flujo humano HU 1.4, paso 4)."""

    producto_id: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _requiere_campo(self):
        if "producto_id" not in self.model_fields_set:
            raise ValueError("producto_id es obligatorio (usa null para desvincular)")
        return self
