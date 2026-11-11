from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base


class AnomalyAlert(Base):
    """Alerta de anomalia: reduflacion o superacion de devaluacion (decision #7)."""

    __tablename__ = "anomaly_alerts"
    __table_args__ = (
        CheckConstraint(
            "alert_type IN ('shrinkflation', 'outpace_devaluation')",
            name="ck_alerts_type",
        ),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high')",
            name="ck_alerts_severity",
        ),
        CheckConstraint(
            "status IN ('open', 'reviewed')",
            name="ck_alerts_status",
        ),
        Index(
            "idx_alerts_status_created",
            "status",
            text("created_at DESC"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_type: Mapped[str] = mapped_column(String(40), nullable=False)
    producto_id: Mapped[int | None] = mapped_column(
        ForeignKey("productos_canonicos.id"),
    )
    store_product_id: Mapped[int | None] = mapped_column(
        ForeignKey("store_products.id"),
    )
    tienda_id: Mapped[int | None] = mapped_column(ForeignKey("tiendas.id"))
    score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    severity: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="medium",
        server_default="medium",
    )
    status: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="open",
        server_default="open",
    )
    details: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=False,
        default=dict,
        server_default="{}",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return (
            f"<AnomalyAlert id={self.id} type={self.alert_type} "
            f"status={self.status} severity={self.severity}>"
        )
