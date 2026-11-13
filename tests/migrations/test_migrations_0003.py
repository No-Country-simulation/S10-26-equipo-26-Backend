"""Integracion: migracion 0003 (disponible) contra SQLite."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


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


def _columns(db_path: Path, table: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    finally:
        conn.close()


def _tables(db_path: Path) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    finally:
        conn.close()


def test_0003_agrega_disponible_a_precios(tmp_path: Path) -> None:
    db_path = tmp_path / "m0003.db"
    result = _run_alembic(["upgrade", "head"], db_path)
    assert result.returncode == 0, result.stderr
    assert "disponible" in _columns(db_path, "precios_historicos")


def test_0003_nullable_acepta_desconocido(tmp_path: Path) -> None:
    """NULL = desconocido (Coto / registros previos); HU 2.1."""
    db_path = tmp_path / "m0003_null.db"
    assert _run_alembic(["upgrade", "head"], db_path).returncode == 0

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("INSERT INTO categorias (nombre) VALUES ('Test')")
        conn.execute("INSERT INTO tiendas (nombre) VALUES ('Coto')")
        conn.execute(
            "INSERT INTO productos_canonicos (nombre_universal, categoria_id) "
            "VALUES ('Prod', 1)"
        )
        conn.execute(
            "INSERT INTO precios_historicos "
            "(id, producto_id, tienda_id, precio_local, tipo_cambio_usado, precio_usd, "
            " disponible) VALUES (1, 1, 1, 100, 1500, 0.07, NULL)"
        )
        row = conn.execute(
            "SELECT disponible FROM precios_historicos WHERE producto_id = 1"
        ).fetchone()
        assert row == (None,)
        conn.rollback()
    finally:
        conn.close()


def test_downgrade_0003_quita_solo_disponible(tmp_path: Path) -> None:
    db_path = tmp_path / "m0003_down.db"
    assert _run_alembic(["upgrade", "head"], db_path).returncode == 0

    result = _run_alembic(["downgrade", "-1"], db_path)
    assert result.returncode == 0, (
        f"alembic downgrade fallo:\n{result.stdout}\n{result.stderr}"
    )

    cols = _columns(db_path, "precios_historicos")
    assert "disponible" not in cols
    assert "raw_presentation" in cols  # 0002 intacto

    tables = _tables(db_path)
    assert {"store_products", "anomaly_alerts"} <= tables
