"""store_products + anomaly_alerts (decisiones #7 y #8)

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-11

NOTO: pendiente de aplicar en Railway (deploy) y localmente via tunel SSH.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "store_products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "producto_id",
            sa.Integer(),
            sa.ForeignKey("productos_canonicos.id"),
            nullable=False,
        ),
        sa.Column(
            "tienda_id",
            sa.Integer(),
            sa.ForeignKey("tiendas.id"),
            nullable=False,
        ),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("nombre_crudo", sa.Text(), nullable=False),
        sa.Column("marca_cruda", sa.Text(), nullable=True),
        sa.Column("raw_presentation", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "tienda_id",
            "external_id",
            name="uq_store_product",
        ),
    )

    op.create_table(
        "anomaly_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("alert_type", sa.String(length=40), nullable=False),
        sa.Column(
            "producto_id",
            sa.Integer(),
            sa.ForeignKey("productos_canonicos.id"),
            nullable=True,
        ),
        sa.Column(
            "store_product_id",
            sa.Integer(),
            sa.ForeignKey("store_products.id"),
            nullable=True,
        ),
        sa.Column(
            "tienda_id",
            sa.Integer(),
            sa.ForeignKey("tiendas.id"),
            nullable=True,
        ),
        sa.Column("score", sa.Numeric(8, 4), nullable=True),
        sa.Column(
            "severity",
            sa.String(length=10),
            server_default="medium",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=10),
            server_default="open",
            nullable=False,
        ),
        sa.Column(
            "details",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()),
                "postgresql",
            ),
            server_default="{}",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "alert_type IN ('shrinkflation', 'outpace_devaluation')",
            name="ck_alerts_type",
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high')",
            name="ck_alerts_severity",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'reviewed')",
            name="ck_alerts_status",
        ),
    )
    op.create_index(
        "idx_alerts_status_created",
        "anomaly_alerts",
        ["status", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_alerts_status_created",
        table_name="anomaly_alerts",
    )
    op.drop_table("anomaly_alerts")
    op.drop_table("store_products")
