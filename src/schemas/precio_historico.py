from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


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

    @field_validator("timestamp", mode="after")
    @classmethod
    def _to_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class PricePoint(PrecioHistoricoRead):
    """Observacion con la clasificacion promo derivada en lectura (HU 2.2)."""

    is_promotion: bool
    price_regular: Decimal
    discount_pct: Decimal


class PriceHistoryList(BaseModel):
    items: list[PricePoint]
    total: int


class PrecioHistoricoCreate(BaseModel):
    producto_id: int | None = None
    tienda_id: int | None = None
    precio_local: Decimal
    precio_tachado: Decimal | None = None
    en_oferta: bool = False
    tipo_cambio_usado: Decimal
    precio_usd: Decimal
    timestamp: datetime | None = None
