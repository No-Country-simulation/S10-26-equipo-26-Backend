from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PrecioHistoricoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    producto_id: int | None = None
    tienda_id: int | None = None
    precio_local: Decimal
    precio_tachado: Decimal | None = None
    en_oferta: bool | None = None
    tipo_cambio_usado: Decimal
    precio_usd: Decimal


class PrecioHistoricoCreate(BaseModel):
    producto_id: int | None = None
    tienda_id: int | None = None
    precio_local: Decimal
    precio_tachado: Decimal | None = None
    en_oferta: bool = False
    tipo_cambio_usado: Decimal
    precio_usd: Decimal
    timestamp: datetime | None = None
