"""Generic SQLAlchemy driver – connects to PostgreSQL, MySQL, and others.

Usage examples (connection URL):
  postgresql://user:pass@host:5432/dbname
  mysql+pymysql://user:pass@host:3306/dbname
  mssql+pyodbc://user:pass@host/dbname?driver=ODBC+Driver+17+for+SQL+Server
"""
from __future__ import annotations

import time

from .base import DatabaseDriver, QueryResult, TableInfo, ColumnInfo


class SQLAlchemyDriver(DatabaseDriver):

    def __init__(self):
        self._engine = None
        self._conn = None
        self._name: str = "SQLAlchemy"
        self._url: str = ""

    def connect(self, config: dict) -> None:
        from sqlalchemy import create_engine, text, inspect as sa_inspect

        db_type = config.get("db_type", "postgresql")
        url = config.get("url", "")

        if not url:
            # Build URL from individual fields
            host = config.get("host", "localhost")
            port = config.get("port", "")
            user = config.get("user", "")
            password = config.get("password", "")
            database = config.get("database", "")

            driver_map = {
                "postgresql": "postgresql",
                "mysql": "mysql+pymysql",
                "mssql": "mssql+pyodbc",
                "oracle": "oracle+cx_oracle",
                "mariadb": "mysql+pymysql",
                "starrocks": "starrocks",
                "doris": "doris",
                "clickhouse": "clickhousedb",
            }
            scheme = driver_map.get(db_type, db_type)
            auth = f"{user}:{password}@" if user else ""
            port_str = f":{port}" if port else ""
            url = f"{scheme}://{auth}{host}{port_str}/{database}"

        self._url = url
        self._name = config.get("name", f"{db_type} ({config.get('host', 'local')})")
        self._engine = create_engine(url, pool_pre_ping=True, pool_size=2)
        self._conn = self._engine.connect()

    def disconnect(self) -> None:
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
        if self._engine:
            try:
                self._engine.dispose()
            except Exception:
                pass
        self._conn = None
        self._engine = None

    def test_connection(self) -> bool:
        try:
            from sqlalchemy import text
            if self._conn:
                self._conn.execute(text("SELECT 1"))
                return True
        except Exception:
            pass
        return False

    def execute(self, sql: str, params: list | None = None,
                limit: int = 500, offset: int = 0) -> QueryResult:
        if not self._conn:
            return QueryResult(error="Not connected")

        from sqlalchemy import text

        t0 = time.perf_counter()
        try:
            stripped = sql.strip().rstrip(";")
            upper = stripped.upper()

            if upper.startswith(("SELECT", "WITH", "SHOW")):
                # Pagination via subquery
                wrapped = f"SELECT * FROM ({stripped}) AS _q LIMIT {limit} OFFSET {offset}"
                result = self._conn.execute(text(wrapped))
                columns = list(result.keys())
                rows = [list(row) for row in result.fetchall()]

                count_result = self._conn.execute(
                    text(f"SELECT COUNT(*) FROM ({stripped}) AS _q")
                )
                total = count_result.scalar() or 0

                elapsed = (time.perf_counter() - t0) * 1000
                return QueryResult(
                    columns=columns, rows=rows, row_count=total,
                    truncated=total > offset + limit,
                    elapsed_ms=round(elapsed, 2),
                )
            else:
                result = self._conn.execute(text(stripped))
                try:
                    self._conn.commit()
                except Exception:
                    pass
                elapsed = (time.perf_counter() - t0) * 1000
                return QueryResult(
                    affected=result.rowcount if result.rowcount >= 0 else 0,
                    elapsed_ms=round(elapsed, 2),
                )
        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000
            return QueryResult(error=str(e), elapsed_ms=round(elapsed, 2))

    def get_schemas(self) -> list[str]:
        if not self._engine:
            return []
        try:
            from sqlalchemy import inspect as sa_inspect
            insp = sa_inspect(self._engine)
            return sorted(insp.get_schema_names())
        except Exception:
            return ["public"]

    def get_tables(self, schema: str = "public") -> list[TableInfo]:
        if not self._engine:
            return []
        try:
            from sqlalchemy import inspect as sa_inspect
            insp = sa_inspect(self._engine)
            tables = [
                TableInfo(name=t, table_type="TABLE", schema=schema)
                for t in insp.get_table_names(schema=schema)
            ]
            views = [
                TableInfo(name=v, table_type="VIEW", schema=schema)
                for v in insp.get_view_names(schema=schema)
            ]
            return sorted(tables + views, key=lambda t: t.name)
        except Exception:
            return []

    def get_columns(self, table: str, schema: str = "public") -> list[ColumnInfo]:
        if not self._engine:
            return []
        try:
            from sqlalchemy import inspect as sa_inspect
            insp = sa_inspect(self._engine)
            cols = insp.get_columns(table, schema=schema)
            pk_cols = set()
            try:
                pk = insp.get_pk_constraint(table, schema=schema)
                pk_cols = set(pk.get("constrained_columns", []))
            except Exception:
                pass
            return [
                ColumnInfo(
                    name=c["name"],
                    data_type=str(c["type"]),
                    nullable=c.get("nullable", True),
                    primary_key=c["name"] in pk_cols,
                )
                for c in cols
            ]
        except Exception:
            return []

    @property
    def display_name(self) -> str:
        return self._name
