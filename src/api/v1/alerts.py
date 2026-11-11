from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.exceptions import NotFoundError
from src.db.session import get_db
from src.models.anomaly_alert import AnomalyAlert
from src.schemas.anomaly_alert import AnomalyAlertPatch, AnomalyAlertRead
from src.services import alert_engine

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "/evaluate",
    response_model=list[AnomalyAlertRead],
    status_code=status.HTTP_201_CREATED,
)
def evaluate_alerts(
    start_date: date,
    end_date: date,
    db: DbSession,
    window_days: Annotated[int, Query(ge=1, le=90)] = 1,
    threshold: Annotated[Decimal, Query(ge=0)] = Decimal(0),
) -> list[AnomalyAlertRead]:
    """Job de evaluacion (HU 3.5): genera alertas outpace_devaluation."""
    alertas = alert_engine.evaluate_outpace_devaluation(
        db,
        start=start_date,
        end=end_date,
        window_days=window_days,
        threshold=threshold,
    )
    return [AnomalyAlertRead.model_validate(a) for a in alertas]


@router.get("", response_model=list[AnomalyAlertRead])
def list_alerts(
    db: DbSession,
    alert_status: Annotated[Literal["open", "reviewed"] | None, Query(alias="status")] = None,
    severity: Annotated[Literal["low", "medium", "high"] | None, Query()] = None,
    alert_type: Annotated[
        Literal["shrinkflation", "outpace_devaluation"] | None,
        Query(alias="type"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[AnomalyAlertRead]:
    query = select(AnomalyAlert)
    if alert_status is not None:
        query = query.where(AnomalyAlert.status == alert_status)
    if severity is not None:
        query = query.where(AnomalyAlert.severity == severity)
    if alert_type is not None:
        query = query.where(AnomalyAlert.alert_type == alert_type)

    query = query.order_by(AnomalyAlert.created_at.desc()).limit(limit)
    items = list(db.scalars(query))
    return [AnomalyAlertRead.model_validate(a) for a in items]


@router.patch("/{alert_id}", response_model=AnomalyAlertRead)
def update_alert_status(
    alert_id: int,
    payload: AnomalyAlertPatch,
    db: DbSession,
) -> AnomalyAlertRead:
    alerta = db.get(AnomalyAlert, alert_id)
    if alerta is None:
        raise NotFoundError(f"alerta {alert_id} no encontrada")

    alerta.status = payload.status.value
    if payload.status.value == "reviewed":
        alerta.reviewed_at = datetime.now(UTC)
    elif alerta.reviewed_at is not None:
        alerta.reviewed_at = None

    db.commit()
    db.refresh(alerta)
    return AnomalyAlertRead.model_validate(alerta)
