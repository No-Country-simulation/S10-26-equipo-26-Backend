"""disponible (stock por observacion) — HU 2.1

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-12

Columna nullable: NULL = desconocido (registro previo o tienda que no
expone stock, ej. Coto). El scraper la llena en cada corrida.
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "precios_historicos",
        sa.Column("disponible", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("precios_historicos", "disponible")
