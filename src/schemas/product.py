from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    brand: str | None = None
    category: str | None = None
    reference_unit: str | None = None
    created_at: datetime


class ProductCreate(BaseModel):
    name: str
    brand: str | None = None
    category: str | None = None
    reference_unit: str | None = None
