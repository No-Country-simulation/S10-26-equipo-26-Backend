from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class InflationPointRead(BaseModel):
    date: date
    index: Decimal


class InflationSeriesRead(BaseModel):
    series: list[InflationPointRead]
    base: Decimal
    method: str
    excluded_promos: int
    products_count: int
