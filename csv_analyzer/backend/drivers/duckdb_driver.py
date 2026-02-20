"""DuckDB driver – optimised for CSV / Parquet analytics.

Key improvements over v1:
  - File-based databases instead of in-memory to control RAM usage.
  - Configurable memory_limit (default 512 MB).
  - read_csv_auto for direct CSV querying without full import.
"""
from __future__ import annotations

import os
import time
import tempfile
from pathlib import Path

import duckdb

from .base import DatabaseDriver, QueryResult, TableInfo, ColumnInfo


class DuckDBDriver(DatabaseDriver):

    def __init__(self):
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._db_path: str = ""
        self._name: str = "DuckDB"

    # ---- lifecycle ----
    def connect(self, config: dict) -> None:
        db_path = config.get("database", "")
        memory_limit = config.get("memory_limit", "512MB")
        threads = config.get("threads", 4)

        if not db_path or db_path == ":memory:":
            # Use a temp file instead of pure in-memory to cap RAM
            tmp = tempfile.mktemp(suffix=".duckdb")
            db_path = tmp

        self._db_path = db_path
        self._name = config.get("name", f"DuckDB ({Path(db_path).stem})")

        self._conn = duckdb.connect(db_path)
        self._conn.execute(f"SET memory_limit='{memory_limit}'")
        self._conn.execute(f"SET threads={threads}")

    def disconnect(self) -> None:
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def test_connection(self) -> bool:
        try:
            if self._conn:
                self._conn.execute("SELECT 1")
                return True
        except Exception:
            pass
        return False

    # ---- queries ----
    def execute(self, sql: str, params: list | None = None,
                limit: int = 500, offset: int = 0) -> QueryResult:
        if not self._conn:
            return QueryResult(error="Not connected")

        t0 = time.perf_counter()
        try:
            # For SELECT-like statements, wrap with LIMIT/OFFSET
            stripped = sql.strip().rstrip(";")
            upper = stripped.upper()

            if upper.startswith(("SELECT", "WITH", "FROM", "SHOW", "DESCRIBE", "PRAGMA")):
                # Wrap in subquery for pagination
                wrapped = f"SELECT * FROM ({stripped}) AS _q LIMIT {limit} OFFSET {offset}"
                rel = self._conn.execute(wrapped)
                columns = [desc[0] for desc in rel.description]
                rows = [list(row) for row in rel.fetchall()]

                # Get total row count
                count_sql = f"SELECT COUNT(*) FROM ({stripped}) AS _q"
                total = self._conn.execute(count_sql).fetchone()[0]

                elapsed = (time.perf_counter() - t0) * 1000
                return QueryResult(
                    columns=columns,
                    rows=rows,
                    row_count=total,
                    truncated=total > offset + limit,
                    elapsed_ms=round(elapsed, 2),
                )
            else:
                # DDL / DML
                self._conn.execute(stripped)
                elapsed = (time.perf_counter() - t0) * 1000
                return QueryResult(
                    affected=self._conn.execute(
                        "SELECT changes('main')"
                    ).fetchone()[0] if "INSERT" in upper or "UPDATE" in upper or "DELETE" in upper else 0,
                    elapsed_ms=round(elapsed, 2),
                )
        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000
            return QueryResult(error=str(e), elapsed_ms=round(elapsed, 2))

    # ---- metadata ----
    def get_schemas(self) -> list[str]:
        if not self._conn:
            return []
        try:
            rows = self._conn.execute(
                "SELECT schema_name FROM information_schema.schemata ORDER BY schema_name"
            ).fetchall()
            return [r[0] for r in rows]
        except Exception:
            return ["main"]

    def get_tables(self, schema: str = "main") -> list[TableInfo]:
        if not self._conn:
            return []
        try:
            rows = self._conn.execute(
                "SELECT table_name, table_type FROM information_schema.tables "
                "WHERE table_schema = ? ORDER BY table_name",
                [schema],
            ).fetchall()
            return [TableInfo(name=r[0], table_type=r[1], schema=schema) for r in rows]
        except Exception:
            return []

    def get_columns(self, table: str, schema: str = "main") -> list[ColumnInfo]:
        if not self._conn:
            return []
        try:
            rows = self._conn.execute(
                "SELECT column_name, data_type, is_nullable "
                "FROM information_schema.columns "
                "WHERE table_schema = ? AND table_name = ? "
                "ORDER BY ordinal_position",
                [schema, table],
            ).fetchall()
            return [
                ColumnInfo(
                    name=r[0], data_type=r[1],
                    nullable=(r[2] == "YES"),
                )
                for r in rows
            ]
        except Exception:
            return []

    # ---- CSV helpers ----
    def _ensure_utf8(self, csv_path: str) -> str:
        """Detect file encoding; if non-UTF-8, convert to a temp UTF-8 file."""
        try:
            with open(csv_path, 'rb') as f:
                raw = f.read(8192)
            if raw.startswith(b'\xef\xbb\xbf'):
                return csv_path  # UTF-8 BOM – fine as-is
            try:
                raw.decode('utf-8')
                return csv_path
            except (UnicodeDecodeError, ValueError):
                pass
            # Try common non-UTF-8 encodings (Chinese / Japanese / Korean)
            for enc in ('gb18030', 'gbk', 'big5', 'shift_jis', 'euc-kr'):
                try:
                    with open(csv_path, 'r', encoding=enc) as f:
                        content = f.read()
                    fd, tmp = tempfile.mkstemp(suffix='.csv')
                    with os.fdopen(fd, 'w', encoding='utf-8', newline='') as tf:
                        tf.write(content)
                    return tmp
                except (UnicodeDecodeError, ValueError):
                    continue
        except Exception:
            pass
        return csv_path

    def load_csv(self, csv_path: str, table_name: str | None = None) -> str:
        """Import a CSV file as a table. Returns the table name."""
        if not self._conn:
            raise RuntimeError("Not connected")

        path = Path(csv_path)
        if table_name is None:
            table_name = path.stem.replace(" ", "_").replace("-", "_")
            table_name = "".join(c for c in table_name if c.isalnum() or c == "_")
            if not table_name:
                table_name = "imported_csv"

        safe_name = table_name.replace('"', '""')
        actual_path = self._ensure_utf8(csv_path)
        safe_path = Path(actual_path).as_posix().replace("'", "''")

        try:
            self._conn.execute(
                f'CREATE OR REPLACE TABLE "{safe_name}" AS '
                f"SELECT * FROM read_csv_auto('{safe_path}', header=true)"
            )
        finally:
            if actual_path != csv_path:
                try:
                    os.remove(actual_path)
                except Exception:
                    pass

        return table_name

    @property
    def display_name(self) -> str:
        return self._name
