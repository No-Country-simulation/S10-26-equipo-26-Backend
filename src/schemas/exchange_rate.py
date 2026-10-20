from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ExchangeRateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    base_currency: str
    quote_currency: str
    rate: Decimal
    source: str | None = None
    observed_at: datetime
    fetched_at: datetime


class ExchangeRateCreate(BaseModel):
    base_currency: str
    quote_currency: str
    rate: Decimal
    source: str | None = None
    observed_at: datetime
    fetched_at: datetime
