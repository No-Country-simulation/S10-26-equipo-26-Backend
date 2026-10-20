"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-20

"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("brand", sa.String(length=255), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("reference_unit", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "stores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("currency_code", sa.String(length=3), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "store_products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id"),
            nullable=False,
        ),
        sa.Column(
            "store_id",
            sa.Integer(),
            sa.ForeignKey("stores.id"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("source_name", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "store_id",
            "external_id",
            name="uq_store_products_store_external",
        ),
    )
    op.create_index(
        "ix_store_products_product_id",
        "store_products",
        ["product_id"],
    )
    op.create_index(
        "ix_store_products_store_id",
        "store_products",
        ["store_id"],
    )

    op.create_table(
        "price_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "store_product_id",
            sa.Integer(),
            sa.ForeignKey("store_products.id"),
            nullable=False,
        ),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("price_before", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("is_promotion", sa.Boolean(), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_price_observations_store_product_id",
        "price_observations",
        ["store_product_id"],
    )
    op.create_index(
        "ix_price_observations_observed_at",
        "price_observations",
        ["observed_at"],
    )

    op.create_table(
        "exchange_rates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("quote_currency", sa.String(length=3), nullable=False),
        sa.Column("rate", sa.Numeric(18, 6), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_exchange_rates_observed_pair",
        "exchange_rates",
        ["observed_at", "base_currency", "quote_currency"],
    )

    op.create_table(
        "anomaly_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "price_observation_id",
            sa.Integer(),
            sa.ForeignKey("price_observations.id"),
            nullable=True,
        ),
        sa.Column("anomaly_type", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_anomaly_alerts_price_observation_id",
        "anomaly_alerts",
        ["price_observation_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_anomaly_alerts_price_observation_id",
        table_name="anomaly_alerts",
    )
    op.drop_table("anomaly_alerts")

    op.drop_index(
        "ix_exchange_rates_observed_pair",
        table_name="exchange_rates",
    )
    op.drop_table("exchange_rates")

    op.drop_index(
        "ix_price_observations_observed_at",
        table_name="price_observations",
    )
    op.drop_index(
        "ix_price_observations_store_product_id",
        table_name="price_observations",
    )
    op.drop_table("price_observations")

    op.drop_index(
        "ix_store_products_store_id",
        table_name="store_products",
    )
    op.drop_index(
        "ix_store_products_product_id",
        table_name="store_products",
    )
    op.drop_table("store_products")

    op.drop_table("stores")
    op.drop_table("products")
