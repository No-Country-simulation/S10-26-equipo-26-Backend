from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StoreProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    producto_id: int
    tienda_id: int
    external_id: str
    source_url: str | None = None
    nombre_crudo: str
    marca_cruda: str | None = None
    raw_presentation: str | None = None
    created_at: datetime


class StoreProductCreate(BaseModel):
    producto_id: int = Field(ge=1)
    tienda_id: int = Field(ge=1)
    external_id: str = Field(min_length=1, max_length=255)
    source_url: str | None = None
    nombre_crudo: str = Field(min_length=1)
    marca_cruda: str | None = None
    raw_presentation: str | None = None
