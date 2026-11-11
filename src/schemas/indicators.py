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


class DevaluationGapRead(BaseModel):
    start: date
    end: date
    price_variation: Decimal
    fx_variation: Decimal
    gap: Decimal
    fx_start: Decimal
    fx_end: Decimal


class SpikeRead(BaseModel):
    date: date
    value: Decimal
    rolling_median: Decimal
    mad: Decimal
    score: Decimal


class SpikeListRead(BaseModel):
    items: list[SpikeRead]
    total: int
    window: int
    k: Decimal
