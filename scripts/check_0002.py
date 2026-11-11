import os

import psycopg

dsn = os.environ["CHECK_DSN"]
c = psycopg.connect(dsn, connect_timeout=10)
print("alembic:", c.execute("SELECT version_num FROM alembic_version").fetchall())
print("store_products:", c.execute("SELECT to_regclass('store_products')").fetchone())
print("anomaly_alerts:", c.execute("SELECT to_regclass('anomaly_alerts')").fetchone())
print(
    "raw_presentation:",
    c.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='precios_historicos' AND column_name='raw_presentation'"
    ).fetchone(),
)
print("productos:", c.execute("SELECT count(*) FROM productos_canonicos").fetchone())
c.close()
