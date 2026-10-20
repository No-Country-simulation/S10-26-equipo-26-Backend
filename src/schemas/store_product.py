from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StoreProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    store_id: int
    external_id: str
    source_url: str | None = None
    source_name: str | None = None
    created_at: datetime


class StoreProductCreate(BaseModel):
    product_id: int
    store_id: int
    external_id: str
    source_url: str | None = None
    source_name: str | None = None
