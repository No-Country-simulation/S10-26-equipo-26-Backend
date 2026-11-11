from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


class HistorialDivisaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    tipo_cambio_oficial: Decimal
    tipo_cambio_paralelo: Decimal

    @field_validator("timestamp", mode="after")
    @classmethod
    def _to_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class HistorialDivisaList(BaseModel):
    items: list[HistorialDivisaRead]
    total: int


class HistorialDivisaCreate(BaseModel):
    timestamp: datetime | None = None
    tipo_cambio_oficial: Decimal
    tipo_cambio_paralelo: Decimal
