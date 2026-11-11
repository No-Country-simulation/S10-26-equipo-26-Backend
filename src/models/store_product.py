from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class StoreProduct(Base):
    """Vinculo producto canonico <-> fila cruda de cada e-commerce (decision #8)."""

    __tablename__ = "store_products"
    __table_args__ = (
        UniqueConstraint(
            "tienda_id",
            "external_id",
            name="uq_store_product",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(
        ForeignKey("productos_canonicos.id"),
        nullable=False,
    )
    tienda_id: Mapped[int] = mapped_column(
        ForeignKey("tiendas.id"),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    nombre_crudo: Mapped[str] = mapped_column(Text, nullable=False)
    marca_cruda: Mapped[str | None] = mapped_column(Text)
    raw_presentation: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
