from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class AlertType(StrEnum):
    SHRINKFLATION = "shrinkflation"
    OUTPACE_DEVALUATION = "outpace_devaluation"


class AlertStatus(StrEnum):
    OPEN = "open"
    REVIEWED = "reviewed"


class AlertSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AnomalyAlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_type: AlertType
    producto_id: int | None = None
    store_product_id: int | None = None
    tienda_id: int | None = None
    score: Decimal | None = None
    severity: AlertSeverity
    status: AlertStatus
    details: dict
    created_at: datetime
    reviewed_at: datetime | None = None


class AnomalyAlertPatch(BaseModel):
    status: AlertStatus
