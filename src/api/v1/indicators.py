from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from statistics import median
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.analytics.devaluation import compute_devaluation_gap
from src.analytics.inflation import compute_inflation
from src.analytics.spike_detection import detect_spikes
from src.core.exceptions import NotFoundError
from src.db.session import get_db
from src.models.precio_historico import PrecioHistorico
from src.models.producto_canonico import ProductoCanonico
from src.schemas.indicators import (
    DevaluationGapRead,
    InflationPointRead,
    InflationSeriesRead,
    SpikeListRead,
    SpikeRead,
)

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/inflation", response_model=InflationSeriesRead)
def get_inflation(
    db: DbSession,
    category_id: Annotated[int | None, Query()] = None,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    window_days: Annotated[int, Query(ge=1, le=90)] = 7,
    currency: Literal["local", "usd"] = "local",
) -> InflationSeriesRead:
    resultado = compute_inflation(
        db,
        category_id=category_id,
        start=start_date,
        end=end_date,
        window_days=window_days,
        currency=currency,
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


@router.get("/devaluation-gap", response_model=DevaluationGapRead)
def get_devaluation_gap(
    db: DbSession,
    start_date: date,
    end_date: date,
    category_id: Annotated[int | None, Query()] = None,
    window_days: Annotated[int, Query(ge=1, le=90)] = 7,
) -> DevaluationGapRead:
    resultado = compute_devaluation_gap(
        db,
        start=start_date,
        end=end_date,
        category_id=category_id,
        window_days=window_days,
    )
    return DevaluationGapRead(**vars(resultado))


@router.get("/spikes", response_model=SpikeListRead)
def get_spikes(
    db: DbSession,
    producto_id: int,
    start_date: Annotated[date | None, Query()] = None,
    end_date: Annotated[date | None, Query()] = None,
    window: Annotated[int, Query(ge=2, le=90)] = 5,
    k: Annotated[Decimal, Query(gt=0)] = Decimal(3),
    currency: Literal["local", "usd"] = "local",
) -> SpikeListRead:
    if db.get(ProductoCanonico, producto_id) is None:
        raise NotFoundError(f"producto {producto_id} no encontrado")

    stmt = select(PrecioHistorico).where(
        PrecioHistorico.producto_id == producto_id,
    )
    if start_date is not None:
        stmt = stmt.where(
            PrecioHistorico.timestamp
            >= datetime.combine(start_date, time.min, tzinfo=UTC),
        )
    if end_date is not None:
        stmt = stmt.where(
            PrecioHistorico.timestamp
            < datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=UTC),
        )

    campo = "precio_usd" if currency == "usd" else "precio_local"
    por_dia: dict[date, list[Decimal]] = {}
    for row in db.scalars(stmt.order_by(PrecioHistorico.timestamp.asc())):
        por_dia.setdefault(row.timestamp.date(), []).append(
            getattr(row, campo),
        )

    serie = [
        (dia, Decimal(str(median(valores))))
        for dia, valores in sorted(por_dia.items())
    ]
    picos = detect_spikes(serie, window=window, k=k)

    return SpikeListRead(
        items=[
            SpikeRead(
                date=p.date,
                value=p.value,
                rolling_median=p.rolling_median,
                mad=p.mad,
                score=p.score,
            )
            for p in picos
        ],
        total=len(picos),
        window=window,
        k=k,
    )
