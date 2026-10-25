from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    false,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class PrecioHistorico(Base):
    __tablename__ = "precios_historicos"
    __table_args__ = (
        Index(
            "idx_precios_prod_tiempo",
            "producto_id",
            text("timestamp DESC"),
        ),
        Index(
            "idx_precios_tienda_tiempo",
            "tienda_id",
            text("timestamp DESC"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    producto_id: Mapped[int | None] = mapped_column(
        ForeignKey("productos_canonicos.id")
    )
    tienda_id: Mapped[int | None] = mapped_column(ForeignKey("tiendas.id"))
    precio_local: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    precio_tachado: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    en_oferta: Mapped[bool | None] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
    )
    tipo_cambio_usado: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    precio_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2))
