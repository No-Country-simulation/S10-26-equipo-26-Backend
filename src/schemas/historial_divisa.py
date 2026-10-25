from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class HistorialDivisaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    tipo_cambio_oficial: Decimal
    tipo_cambio_paralelo: Decimal


class HistorialDivisaCreate(BaseModel):
    timestamp: datetime | None = None
    tipo_cambio_oficial: Decimal
    tipo_cambio_paralelo: Decimal
