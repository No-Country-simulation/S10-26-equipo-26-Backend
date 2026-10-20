from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PriceObservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    store_product_id: int
    price: Decimal
    price_before: Decimal | None = None
    currency_code: str
    is_promotion: bool
    is_available: bool
    observed_at: datetime
    fetched_at: datetime


class PriceObservationCreate(BaseModel):
    store_product_id: int
    price: Decimal
    price_before: Decimal | None = None
    currency_code: str
    is_promotion: bool = False
    is_available: bool = True
    observed_at: datetime
    fetched_at: datetime
