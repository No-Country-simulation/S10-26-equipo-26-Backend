"""initial schema (5 tablas en espanol — esquema de Railway Postgres)

Revision ID: 0001
Revises:
Create Date: 2026-10-20

NOTO: revision ya aplicada en Railway (alembic_version = 0001). En local se
aplica contra el tunnel SSH (puerto 55432) o contra la BD Docker opcional.
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "categorias",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.UniqueConstraint("nombre", name="categorias_nombre_key"),
    )

    op.create_table(
        "tiendas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("url_base", sa.String(length=255), nullable=True),
        sa.UniqueConstraint("nombre", name="tiendas_nombre_key"),
    )

    op.create_table(
        "productos_canonicos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre_universal", sa.String(length=255), nullable=False),
        sa.Column(
            "categoria_id",
            sa.Integer(),
            sa.ForeignKey("categorias.id"),
            nullable=True,
        ),
        sa.Column("unidad_medida", sa.String(length=50), nullable=True),
        sa.Column("marca", sa.Text(), nullable=True),
    )

    op.create_table(
        "precios_historicos",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "producto_id",
            sa.Integer(),
            sa.ForeignKey("productos_canonicos.id"),
            nullable=True,
        ),
        sa.Column(
            "tienda_id",
            sa.Integer(),
            sa.ForeignKey("tiendas.id"),
            nullable=True,
        ),
        sa.Column("precio_local", sa.Numeric(12, 2), nullable=False),
        sa.Column("precio_tachado", sa.Numeric(12, 2), nullable=True),
        sa.Column(
            "en_oferta",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=True,
        ),
        sa.Column("tipo_cambio_usado", sa.Numeric(12, 4), nullable=False),
        sa.Column("precio_usd", sa.Numeric(12, 2), nullable=False),
    )
    op.create_index(
        "idx_precios_prod_tiempo",
        "precios_historicos",
        ["producto_id", sa.text("timestamp DESC")],
    )
    op.create_index(
        "idx_precios_tienda_tiempo",
        "precios_historicos",
        ["tienda_id", sa.text("timestamp DESC")],
    )

    op.create_table(
        "historial_divisas",
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            primary_key=True,
        ),
        sa.Column("tipo_cambio_oficial", sa.Numeric(12, 4), nullable=False),
        sa.Column("tipo_cambio_paralelo", sa.Numeric(12, 4), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("historial_divisas")

    op.drop_index(
        "idx_precios_tienda_tiempo",
        table_name="precios_historicos",
    )
    op.drop_index(
        "idx_precios_prod_tiempo",
        table_name="precios_historicos",
    )
    op.drop_table("precios_historicos")

    op.drop_table("productos_canonicos")
    op.drop_table("tiendas")
    op.drop_table("categorias")
