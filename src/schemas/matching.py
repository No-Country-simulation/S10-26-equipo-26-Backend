from typing import Literal

from pydantic import BaseModel, Field

from src.schemas.producto_canonico import ProductoCanonicoRead
from src.schemas.store_product import StoreProductRead


class MatchSuggestionRequest(BaseModel):
    tienda_id: int = Field(ge=1)
    threshold: float = Field(default=0.75, ge=0.0, le=1.0)


class MatchSuggestionRead(BaseModel):
    store_product: StoreProductRead
    product: ProductoCanonicoRead
    score: float
    band: Literal["auto", "review"]


class MatchSuggestionList(BaseModel):
    items: list[MatchSuggestionRead]
    total: int
    auto_count: int
    review_count: int
