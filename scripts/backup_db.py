"""Backup lógico (solo lectura) de la BD indicada en DATABASE_URL.

Genera un archivo ``.sql`` restaurable: DDL (tablas, constraints, índices),
datos (COPY ... FROM stdin) y ``setval`` de secuencias.

Garantía de solo lectura: todos los SQL se ejecutan dentro de una transacción
``REPEATABLE READ READ ONLY`` — el servidor rechaza cualquier escritura.

Uso (desde la raíz del backend, con el .env apuntando a la BD a respaldar):

    python scripts/backup_db.py
    python scripts/backup_db.py --out backups/mi_backup.sql
    python scripts/backup_db.py --sslmode require
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import psycopg
from sqlalchemy import make_url

from src.core.config import get_settings


def qident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def topo_order(tables: list[str], edges: list[tuple[str, str]]) -> list[str]:
    """Ordena tablas respetando FKs (padres primero)."""
    deps: dict[str, set[str]] = {t: set() for t in tables}
    for child, parent in edges:
        if child in deps and parent in deps:
            deps[child].add(parent)
    ordered: list[str] = []
    pending = dict(deps)
    while pending:
        ready = sorted(t for t, d in pending.items() if not d)
        if not ready:
            ordered.extend(sorted(pending))
            break
        for t in ready:
            ordered.append(t)
            del pending[t]
        for d in pending.values():
            d.difference_update(ready)
    return ordered


def read_copy_text(cur: psycopg.Cursor, sql: str) -> str:
    parts: list[str] = []
    with cur.copy(sql) as copy:
        while True:
            chunk = copy.read()
            if not chunk:
                break
            parts.append(
                chunk if isinstance(chunk, str) else bytes(chunk).decode("utf-8")
            )
    return "".join(parts)


def build_backup(sslmode: str) -> tuple[str, list[tuple[str, int]], str]:
    url = make_url(get_settings().database_url)
    conn = psycopg.connect(
        host=url.host,
        port=url.port or 5432,
        dbname=url.database,
        user=url.username,
        password=url.password,
        sslmode=sslmode,
        connect_timeout=15,
        autocommit=True,
    )
    try:
        cur = conn.cursor()
        cur.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
        cur.execute("SHOW transaction_read_only")
        row = cur.fetchone()
        assert row is not None
        read_only = str(row[0])

        cur.execute(
            """
            SELECT c.relname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relkind = 'r'
            ORDER BY c.relname
            """
        )
        tables = [r[0] for r in cur.fetchall()]
        if not tables:
            raise SystemExit("No hay tablas en el esquema public: nada que respaldar")

        cur.execute(
            """
            SELECT conrelid::regclass::text, confrelid::regclass::text
            FROM pg_constraint
            WHERE contype = 'f' AND connamespace = 'public'::regnamespace
            """
        )
        edges = [(c, p) for c, p in cur.fetchall()]
        order = topo_order(tables, edges)

        columns: dict[str, list[tuple[str, str, bool, str | None, str, str]]] = {}
        for t in order:
            cur.execute(
                """
                SELECT a.attname,
                       format_type(a.atttypid, a.atttypmod),
                       a.attnotnull,
                       pg_get_expr(d.adbin, d.adrelid),
                       a.attidentity,
                       a.attgenerated
                FROM pg_attribute a
                LEFT JOIN pg_attrdef d
                    ON d.adrelid = a.attrelid AND d.adnum = a.attnum
                WHERE a.attrelid = %s::regclass
                  AND a.attnum > 0 AND NOT a.attisdropped
                ORDER BY a.attnum
                """,
                (qident(t),),
            )
            columns[t] = cur.fetchall()

        inline: dict[str, list[tuple[str, str]]] = {}
        for t in order:
            cur.execute(
                """
                SELECT conname, pg_get_constraintdef(oid)
                FROM pg_constraint
                WHERE connamespace = 'public'::regnamespace
                  AND contype IN ('p', 'u', 'c')
                  AND conrelid = %s::regclass
                ORDER BY contype, conname
                """,
                (qident(t),),
            )
            inline[t] = cur.fetchall()

        cur.execute(
            """
            SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE contype = 'f' AND connamespace = 'public'::regnamespace
            ORDER BY conrelid::regclass::text, conname
            """
        )
        fks = cur.fetchall()

        cur.execute(
            """
            SELECT pg_get_indexdef(ix.indexrelid)
            FROM pg_index ix
            JOIN pg_class t ON t.oid = ix.indrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE n.nspname = 'public'
              AND ix.indisvalid
              AND NOT ix.indisprimary
              AND NOT EXISTS (
                  SELECT 1 FROM pg_constraint co WHERE co.conindid = ix.indexrelid
              )
            ORDER BY pg_get_indexdef(ix.indexrelid)
            """
        )
        indexes = [r[0] + ";" for r in cur.fetchall()]

        counts: list[tuple[str, int]] = []
        data_blocks: list[str] = []
        for t in order:
            cur.execute(f"SELECT COUNT(*) FROM {qident(t)}")
            count_row = cur.fetchone()
            assert count_row is not None
            n = count_row[0]
            counts.append((t, n))
            cols = [c[0] for c in columns[t] if c[5] != "s" and c[4] not in ("a", "d")]
            col_list = ", ".join(qident(c) for c in cols)
            payload = read_copy_text(cur, f"COPY {qident(t)} ({col_list}) TO STDOUT")
            data_blocks.append(
                f"COPY {qident(t)} ({col_list}) FROM stdin;\n{payload}\\.\n"
            )

        seq_create: list[str] = []
        seq_owned: list[str] = []
        seq_setval: list[str] = []
        seq_drop: list[str] = []
        cur.execute(
            """
            SELECT pg_get_serial_sequence(
                       format('%I.%I', n.nspname, c.relname), a.attname
                   ) AS seq,
                   format('%I.%I', n.nspname, c.relname) AS tbl,
                   a.attname AS col
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_attribute a
                ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
            WHERE n.nspname = 'public' AND c.relkind = 'r'
              AND a.attgenerated = '' AND a.attidentity = ''
            ORDER BY 1
            """
        )
        for seq, tbl, col in cur.fetchall():
            if not seq:
                continue
            cur.execute(
                """
                SELECT format('%%I.%%I', n.nspname, s.relname),
                       format_type(q.seqtypid, NULL),
                       q.seqstart, q.seqincrement, q.seqmin, q.seqmax,
                       q.seqcache, q.seqcycle
                FROM pg_sequence q
                JOIN pg_class s ON s.oid = q.seqrelid
                JOIN pg_namespace n ON n.oid = s.relnamespace
                WHERE q.seqrelid = %s::regclass
                """,
                (seq,),
            )
            info = cur.fetchone()
            assert info is not None
            qseq, seq_type, start, inc, vmin, vmax, cache, cycle = info
            seq_create.append(
                f"CREATE SEQUENCE {qseq} AS {seq_type} START WITH {start} "
                f"INCREMENT BY {inc} MINVALUE {vmin} MAXVALUE {vmax} "
                f"CACHE {cache}{' CYCLE' if cycle else ''};"
            )
            seq_owned.append(f"ALTER SEQUENCE {qseq} OWNED BY {tbl}.{qident(col)};")
            seq_drop.append(qseq)
            cur.execute(f"SELECT last_value, is_called FROM {qseq}")
            seq_row = cur.fetchone()
            assert seq_row is not None
            last_value, is_called = seq_row[0], seq_row[1]
            seq_lit = qseq.replace("'", "''")
            seq_setval.append(
                f"SELECT setval('{seq_lit}', {last_value}, "
                f"{'true' if is_called else 'false'});"
            )

        cur.execute("COMMIT")

        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines: list[str] = []
        lines.append("-- PriceScope: backup logico (DDL + datos)")
        lines.append(f"-- Fuente: {url.host}:{url.port or 5432}/{url.database}")
        lines.append(f"-- Generado: {now} por scripts/backup_db.py")
        lines.append("-- Snapshot consistente: transaccion REPEATABLE READ READ ONLY")
        lines.append("-- Restaurar: psql -U <user> -d <db> -f este_archivo.sql")
        lines.append("SET check_function_bodies = false;")
        lines.append("SET client_min_messages = warning;")
        lines.append("SET row_security = off;")
        lines.append("SET search_path = public;")
        lines.append("BEGIN;")
        lines.append("")
        lines.append("-- DROP (orden inverso de dependencias)")
        lines.append(
            "DROP TABLE IF EXISTS "
            + ", ".join(qident(t) for t in reversed(order))
            + " CASCADE;"
        )
        if seq_drop:
            lines.append("DROP SEQUENCE IF EXISTS " + ", ".join(seq_drop) + " CASCADE;")
        lines.append("")
        lines.append("-- Secuencias (antes que las tablas que las referencian)")
        lines.extend(seq_create)
        lines.append("")
        lines.append("-- Tablas")
        for t in order:
            lines.append(f"CREATE TABLE {qident(t)} (")
            body: list[str] = []
            for name, coltype, notnull, default, identity, generated in columns[t]:
                col = f"    {qident(name)} {coltype}"
                if generated == "s":
                    col += " GENERATED ALWAYS AS ("
                    col += f"{default}) STORED"
                elif identity == "a":
                    col += " GENERATED ALWAYS AS IDENTITY"
                elif identity == "d":
                    col += " GENERATED BY DEFAULT AS IDENTITY"
                else:
                    if default:
                        col += f" DEFAULT {default}"
                    if notnull:
                        col += " NOT NULL"
                body.append(col)
            for conname, condef in inline[t]:
                body.append(f"    CONSTRAINT {qident(conname)} {condef}")
            lines.append(",\n".join(body))
            lines.append(");")
        if fks:
            lines.append("")
            lines.append("-- Foreign keys")
            for table, conname, condef in fks:
                lines.append(
                    f"ALTER TABLE {qident(table)} "
                    f"ADD CONSTRAINT {qident(conname)} {condef};"
                )
        if indexes:
            lines.append("")
            lines.append("-- Indices")
            lines.extend(indexes)
        lines.append("")
        lines.append("-- Datos")
        lines.extend(data_blocks)
        if seq_owned or seq_setval:
            lines.append("-- Secuencias")
            lines.extend(seq_owned)
            lines.extend(seq_setval)
        lines.append("COMMIT;")
        lines.append("")

        sql_text = "\n".join(lines)
        return sql_text, counts, read_only
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backup logico de la BD")
    parser.add_argument("--out", help="Ruta del archivo .sql de salida")
    parser.add_argument(
        "--sslmode",
        default="prefer",
        choices=["disable", "allow", "prefer", "require", "verify-ca", "verify-full"],
    )
    args = parser.parse_args()

    sql_text, counts, read_only = build_backup(args.sslmode)

    stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out = (
        Path(args.out)
        if args.out
        else Path("backups") / f"pricescope_backup_{stamp}.sql"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(sql_text.encode("utf-8"))

    total = sum(n for _, n in counts)
    print(f"transaction_read_only = {read_only}")
    print(f"Backup escrito: {out} ({out.stat().st_size} bytes)")
    for t, n in counts:
        print(f"  {t}: {n} filas")
    print(f"  TOTAL: {total} filas")


if __name__ == "__main__":
    main()
