from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.historial_divisa import HistorialDivisaList, HistorialDivisaRead
from src.services import fx_service

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/history", response_model=HistorialDivisaList)
def get_exchange_rate_history(
    db: DbSession,
    start: Annotated[datetime | None, Query()] = None,
    end: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=2000)] = 500,
) -> HistorialDivisaList:
    items = fx_service.get_history(db, start=start, end=end, limit=limit)
    return HistorialDivisaList(
        items=[HistorialDivisaRead.model_validate(i) for i in items],
        total=len(items),
    )


@router.get("/as-of", response_model=HistorialDivisaRead)
def get_exchange_rate_as_of(
    db: DbSession,
    ts: Annotated[datetime, Query(description="Timestamp a consultar (ISO 8601)")],
) -> HistorialDivisaRead:
    registro = fx_service.get_rate_as_of(db, ts)
    return HistorialDivisaRead.model_validate(registro)
