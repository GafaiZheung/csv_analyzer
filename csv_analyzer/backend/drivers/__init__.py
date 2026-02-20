"""Database driver registry."""
from .base import DatabaseDriver, QueryResult
from .duckdb_driver import DuckDBDriver
from .sqlite_driver import SQLiteDriver
from .sqlalchemy_driver import SQLAlchemyDriver

DRIVER_REGISTRY: dict[str, type[DatabaseDriver]] = {
    "duckdb": DuckDBDriver,
    "sqlite": SQLiteDriver,
    "postgresql": SQLAlchemyDriver,
    "mysql": SQLAlchemyDriver,
    "sqlalchemy": SQLAlchemyDriver,
}

# Additional database types that use SQLAlchemy with specific Python packages.
# They map to the same SQLAlchemyDriver but require extra pip packages.
EXTRA_SQLALCHEMY_TYPES = {
    "starrocks": {"scheme": "starrocks", "default_port": 9030},
    "doris":     {"scheme": "doris",     "default_port": 9030},
    "clickhouse":{"scheme": "clickhousedb", "default_port": 8123},
    "mssql":     {"scheme": "mssql+pyodbc", "default_port": 1433},
    "oracle":    {"scheme": "oracle+cx_oracle", "default_port": 1521},
    "mariadb":   {"scheme": "mysql+pymysql", "default_port": 3306},
}

# Register all extra types – they all use SQLAlchemyDriver
for _t in EXTRA_SQLALCHEMY_TYPES:
    if _t not in DRIVER_REGISTRY:
        DRIVER_REGISTRY[_t] = SQLAlchemyDriver


def create_driver(db_type: str) -> DatabaseDriver:
    """Factory: create a driver instance by database type name."""
    cls = DRIVER_REGISTRY.get(db_type)
    if cls is None:
        raise ValueError(f"Unsupported database type: {db_type}")
    return cls()
