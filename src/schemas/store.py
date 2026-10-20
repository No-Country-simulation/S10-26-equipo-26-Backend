from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    base_url: str
    country_code: str | None = None
    currency_code: str | None = None
    created_at: datetime
