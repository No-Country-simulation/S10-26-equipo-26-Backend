from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.precio_historico import PriceHistoryList
from src.services import price_service

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/history", response_model=PriceHistoryList)
def get_price_history(
    db: DbSession,
    producto_id: Annotated[int | None, Query()] = None,
    tienda_id: Annotated[int | None, Query()] = None,
    start: Annotated[datetime | None, Query()] = None,
    end: Annotated[datetime | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 100,
) -> PriceHistoryList:
    return price_service.get_price_history(
        db,
        producto_id=producto_id,
        tienda_id=tienda_id,
        start=start,
        end=end,
        page=page,
        page_size=page_size,
    )
