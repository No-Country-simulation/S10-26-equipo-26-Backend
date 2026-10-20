from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnomalyAlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    price_observation_id: int | None = None
    anomaly_type: str
    severity: str
    score: float | None = None
    description: str | None = None
    status: str
    created_at: datetime


class AnomalyAlertUpdate(BaseModel):
    status: str
