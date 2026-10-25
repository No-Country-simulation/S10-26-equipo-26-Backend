from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class HistorialDivisa(Base):
    __tablename__ = "historial_divisas"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        primary_key=True,
        server_default=func.now(),
    )
    tipo_cambio_oficial: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    tipo_cambio_paralelo: Mapped[Decimal] = mapped_column(Numeric(12, 4))
