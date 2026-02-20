"""Abstract base class for database drivers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class QueryResult:
    """Standard query result envelope."""
    columns: list[str] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)
    row_count: int = 0
    affected: int = 0
    truncated: bool = False
    error: str | None = None
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "columns": self.columns,
            "rows": self.rows,
            "row_count": self.row_count,
            "affected": self.affected,
            "truncated": self.truncated,
            "error": self.error,
            "elapsed_ms": self.elapsed_ms,
        }


@dataclass
class ColumnInfo:
    """Metadata for a single column."""
    name: str
    data_type: str
    nullable: bool = True
    primary_key: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "data_type": self.data_type,
            "nullable": self.nullable,
            "primary_key": self.primary_key,
        }


@dataclass
class TableInfo:
    """Metadata for a single table/view."""
    name: str
    table_type: str = "TABLE"          # TABLE | VIEW
    schema: str = ""
    row_count: int | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.table_type,
            "schema": self.schema,
            "row_count": self.row_count,
        }


class DatabaseDriver(ABC):
    """Interface every database driver must implement."""

    @abstractmethod
    def connect(self, config: dict) -> None:
        """Establish a connection using the provided config dict."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close the connection and free resources."""

    @abstractmethod
    def execute(self, sql: str, params: list | None = None,
                limit: int = 500, offset: int = 0) -> QueryResult:
        """Execute a SQL statement and return results."""

    @abstractmethod
    def get_tables(self, schema: str = "") -> list[TableInfo]:
        """List tables and views."""

    @abstractmethod
    def get_columns(self, table: str, schema: str = "") -> list[ColumnInfo]:
        """List columns of a table."""

    @abstractmethod
    def get_schemas(self) -> list[str]:
        """List available schemas/databases."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Return True if the connection is alive."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for this connection."""
