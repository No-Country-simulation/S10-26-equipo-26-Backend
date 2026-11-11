from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.exceptions import NotFoundError
from src.models.historial_divisa import HistorialDivisa


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def get_rate_as_of(db: Session, ts: datetime) -> HistorialDivisa:
    """Cotizacion vigente en `ts`: la mas cercana ANTERIOR o igual.

    Si `ts` es anterior al primer registro, devuelve el mas antiguo
    disponible (criterio acordado en DOR HU 3.2).
    """
    momento = _ensure_utc(ts)

    previa = db.scalars(
        select(HistorialDivisa)
        .where(HistorialDivisa.timestamp <= momento)
        .order_by(HistorialDivisa.timestamp.desc())
        .limit(1)
    ).first()
    if previa is not None:
        return previa

    mas_antigua = db.scalars(
        select(HistorialDivisa)
        .order_by(HistorialDivisa.timestamp.asc())
        .limit(1)
    ).first()
    if mas_antigua is None:
        raise NotFoundError("no hay cotizaciones registradas")
    return mas_antigua


def get_history(
    db: Session,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 500,
) -> list[HistorialDivisa]:
    query = select(HistorialDivisa)

    if start is not None:
        query = query.where(HistorialDivisa.timestamp >= _ensure_utc(start))
    if end is not None:
        query = query.where(HistorialDivisa.timestamp <= _ensure_utc(end))

    query = query.order_by(HistorialDivisa.timestamp.asc()).limit(limit)
    return list(db.scalars(query))
