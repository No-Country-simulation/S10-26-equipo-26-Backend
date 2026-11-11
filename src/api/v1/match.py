from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.matching import (
    MatchSuggestionList,
    MatchSuggestionRead,
    MatchSuggestionRequest,
)
from src.schemas.producto_canonico import ProductoCanonicoRead
from src.schemas.store_product import StoreProductRead
from src.services import matching_service

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.post("/suggestions", response_model=MatchSuggestionList)
def get_match_suggestions(
    payload: MatchSuggestionRequest,
    db: DbSession,
) -> MatchSuggestionList:
    sugerencias = matching_service.suggest_matches(
        db,
        tienda_id=payload.tienda_id,
        threshold=payload.threshold,
    )
    items = [
        MatchSuggestionRead(
            store_product=StoreProductRead.model_validate(s.store_product),
            product=ProductoCanonicoRead.model_validate(s.product),
            score=s.score,
            band=s.band,  # type: ignore[arg-type]
        )
        for s in sugerencias
    ]
    auto_count = sum(1 for i in items if i.band == "auto")
    return MatchSuggestionList(
        items=items,
        total=len(items),
        auto_count=auto_count,
        review_count=len(items) - auto_count,
    )
