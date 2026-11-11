from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.analytics.inflation import compute_inflation
from src.db.session import get_db
from src.schemas.indicators import InflationPointRead, InflationSeriesRead

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/inflation", response_model=InflationSeriesRead)
def get_inflation(
    db: DbSession,
    category_id: Annotated[int | None, Query()] = None,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    window_days: Annotated[int, Query(ge=1, le=90)] = 7,
) -> InflationSeriesRead:
    resultado = compute_inflation(
        db,
        category_id=category_id,
        start=start_date,
        end=end_date,
        window_days=window_days,
    )
    return InflationSeriesRead(
        series=[
            InflationPointRead(date=p.date, index=p.index)
            for p in resultado.series
        ],
        base=resultado.base,
        method=resultado.method,
        excluded_promos=resultado.excluded_promos,
        products_count=resultado.products_count,
    )
