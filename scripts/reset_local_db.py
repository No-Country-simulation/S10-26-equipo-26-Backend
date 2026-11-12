"""Reset BD local 5435 + alembic upgrade head + seed."""
import os
import sys

os.environ["DATABASE_URL"] = (
    "postgresql+psycopg://pricescope:pricescope@localhost:5435/pricescope"
)

from sqlalchemy import create_engine, text

DSN = "postgresql+psycopg://pricescope:pricescope@localhost:5435/pricescope"

engine = create_engine(DSN, pool_pre_ping=True)

with engine.begin() as conn:
    conn.execute(text("DROP SCHEMA public CASCADE"))
    conn.execute(text("CREATE SCHEMA public"))
    print("schema reseteado")

# Alembic upgrade
from alembic import command
from alembic.config import Config

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg = Config(os.path.join(root, "alembic.ini"))
cfg.set_main_option("sqlalchemy.url", DSN)
command.upgrade(cfg, "head")
print("alembic upgrade head OK")

# Verificar tablas
with engine.connect() as conn:
    rows = conn.execute(
        text(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname='public' ORDER BY tablename"
        )
    ).fetchall()
    print("TABLAS:", [r[0] for r in rows])
    ver = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    print("alembic_version:", ver)

# Seed
sys.path.insert(0, os.path.dirname(__file__))
from scripts.seed import run_seed

run_seed()
