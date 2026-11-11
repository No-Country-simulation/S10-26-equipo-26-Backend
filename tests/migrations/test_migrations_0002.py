"""Integracion: migraciones Alembic contra SQLite (upgrade/downgrade 0002)."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

TABLAS_0001 = {
    "categorias",
    "tiendas",
    "productos_canonicos",
    "precios_historicos",
    "historial_divisas",
}
TABLAS_0002 = {"store_products", "anomaly_alerts"}


def _run_alembic(args: list[str], db_path: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_path.as_posix()}"}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        check=False,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _tables(db_path: Path) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return {row[0] for row in rows}
    finally:
        conn.close()


def _objects(db_path: Path, table: str) -> list[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(f"PRAGMA table_info({table})")
        return [row[1] for row in rows]
    finally:
        conn.close()


@pytest.fixture
def migrated_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "migrations_test.db"
    result = _run_alembic(["upgrade", "head"], db_path)
    assert result.returncode == 0, (
        f"alembic upgrade fallo:\n{result.stdout}\n{result.stderr}"
    )
    return db_path


def test_upgrade_head_crea_las_5_tablas_base_y_las_2_nuevas(
    migrated_db: Path,
) -> None:
    tables = _tables(migrated_db)
    assert TABLAS_0001 <= tables
    assert TABLAS_0002 <= tables


def test_0002_columnas_y_constraints(migrated_db: Path) -> None:
    sp_cols = _objects(migrated_db, "store_products")
    assert {
        "id",
        "producto_id",
        "tienda_id",
        "external_id",
        "source_url",
        "nombre_crudo",
        "marca_cruda",
        "raw_presentation",
        "created_at",
    } <= set(sp_cols)

    alert_cols = _objects(migrated_db, "anomaly_alerts")
    assert {
        "id",
        "alert_type",
        "producto_id",
        "store_product_id",
        "tienda_id",
        "score",
        "severity",
        "status",
        "details",
        "created_at",
        "reviewed_at",
    } <= set(alert_cols)

    conn = sqlite3.connect(migrated_db)
    try:
        # SQLite materializa UNIQUE multi-columna como autoindex con nombre
        # generado: verificamos que exista un indice unico sobre la pareja.
        sp_index_cols = set()
        for row in conn.execute("PRAGMA index_list(store_products)"):
            idx_name, idx_unique = row[1], row[2]
            if idx_unique:
                cols = {
                    col[2]
                    for col in conn.execute(f"PRAGMA index_info({idx_name})")
                }
                sp_index_cols.add(frozenset(cols))
        assert frozenset({"tienda_id", "external_id"}) in sp_index_cols

        alert_indexes = {
            row[1]
            for row in conn.execute("PRAGMA index_list(anomaly_alerts)")
        }
        assert "idx_alerts_status_created" in alert_indexes
    finally:
        conn.close()


def test_0002_constraint_duplicado_efectivo(migrated_db: Path) -> None:
    conn = sqlite3.connect(migrated_db)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(
            "INSERT INTO categorias (nombre) VALUES ('Test')",
        )
        conn.execute(
            "INSERT INTO tiendas (nombre) VALUES ('Coto')",
        )
        conn.execute(
            "INSERT INTO productos_canonicos (nombre_universal, categoria_id) "
            "VALUES ('Prod', 1)",
        )
        conn.execute(
            "INSERT INTO store_products "
            "(producto_id, tienda_id, external_id, nombre_crudo) "
            "VALUES (1, 1, 'EXT-1', 'Crudo')",
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO store_products "
                "(producto_id, tienda_id, external_id, nombre_crudo) "
                "VALUES (1, 1, 'EXT-1', 'Crudo 2')",
            )
        conn.rollback()
    finally:
        conn.close()


def test_downgrade_un_paso_quita_solo_las_tablas_0002(tmp_path: Path) -> None:
    db_path = tmp_path / "downgrade_test.db"
    result = _run_alembic(["upgrade", "head"], db_path)
    assert result.returncode == 0, result.stderr

    result = _run_alembic(["downgrade", "-1"], db_path)
    assert result.returncode == 0, (
        f"alembic downgrade fallo:\n{result.stdout}\n{result.stderr}"
    )

    tables = _tables(db_path)
    assert TABLAS_0001 <= tables
    assert not (TABLAS_0002 & tables)
