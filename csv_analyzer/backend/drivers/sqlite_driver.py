"""SQLite driver."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from .base import DatabaseDriver, QueryResult, TableInfo, ColumnInfo


class SQLiteDriver(DatabaseDriver):

    def __init__(self):
        self._conn: sqlite3.Connection | None = None
        self._db_path: str = ""
        self._name: str = "SQLite"

    def connect(self, config: dict) -> None:
        self._db_path = config.get("database", ":memory:")
        self._name = config.get("name", f"SQLite ({Path(self._db_path).stem})")
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = None

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

    def execute(self, sql: str, params: list | None = None,
                limit: int = 500, offset: int = 0) -> QueryResult:
        if not self._conn:
            return QueryResult(error="Not connected")

        t0 = time.perf_counter()
        try:
            stripped = sql.strip().rstrip(";")
            upper = stripped.upper()
            cur = self._conn.cursor()

            if upper.startswith(("SELECT", "WITH", "PRAGMA")):
                wrapped = f"SELECT * FROM ({stripped}) LIMIT {limit} OFFSET {offset}"
                cur.execute(wrapped, params or [])
                columns = [desc[0] for desc in cur.description] if cur.description else []
                rows = [list(row) for row in cur.fetchall()]

                cur.execute(f"SELECT COUNT(*) FROM ({stripped})", params or [])
                total = cur.fetchone()[0]

                elapsed = (time.perf_counter() - t0) * 1000
                return QueryResult(
                    columns=columns, rows=rows, row_count=total,
                    truncated=total > offset + limit,
                    elapsed_ms=round(elapsed, 2),
                )
            else:
                cur.execute(stripped, params or [])
                self._conn.commit()
                elapsed = (time.perf_counter() - t0) * 1000
                return QueryResult(
                    affected=cur.rowcount,
                    elapsed_ms=round(elapsed, 2),
                )
        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000
            return QueryResult(error=str(e), elapsed_ms=round(elapsed, 2))

    def get_schemas(self) -> list[str]:
        return ["main"]

    def get_tables(self, schema: str = "main") -> list[TableInfo]:
        if not self._conn:
            return []
        try:
            cur = self._conn.execute(
                "SELECT name, type FROM sqlite_master "
                "WHERE type IN ('table','view') ORDER BY name"
            )
            return [
                TableInfo(name=r[0], table_type=r[1].upper(), schema="main")
                for r in cur.fetchall()
            ]
        except Exception:
            return []

    def get_columns(self, table: str, schema: str = "main") -> list[ColumnInfo]:
        if not self._conn:
            return []
        try:
            cur = self._conn.execute(f'PRAGMA table_info("{table}")')
            return [
                ColumnInfo(
                    name=r[1], data_type=r[2] or "TEXT",
                    nullable=(r[3] == 0), primary_key=(r[5] == 1),
                )
                for r in cur.fetchall()
            ]
        except Exception:
            return []

    @property
    def display_name(self) -> str:
        return self._name
