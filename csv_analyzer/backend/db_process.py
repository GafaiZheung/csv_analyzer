"""Database connection process.

Runs in a dedicated subprocess.  Manages multiple named connections via the
driver abstraction layer, executes SQL, and streams metadata back to the
main process through the response queue.

Supported actions:
  connect / disconnect / test_connection
  execute_sql
  get_schemas / get_tables / get_columns
  load_csv  (DuckDB only)
  shutdown
"""
from __future__ import annotations

import traceback
from multiprocessing import Queue
from typing import Any

from csv_analyzer.core.message import Message


# ---- connection store (process-local) ----
_connections: dict[str, Any] = {}   # conn_id -> driver instance


def _handle(msg: Message) -> Message:
    """Route a message to the appropriate handler; return a response."""
    action = msg.action
    p = msg.payload

    try:
        if action == "connect":
            return _do_connect(msg, p)
        elif action == "disconnect":
            return _do_disconnect(msg, p)
        elif action == "test_connection":
            return _do_test(msg, p)
        elif action == "execute_sql":
            return _do_execute(msg, p)
        elif action == "get_schemas":
            return _do_get_schemas(msg, p)
        elif action == "get_tables":
            return _do_get_tables(msg, p)
        elif action == "get_columns":
            return _do_get_columns(msg, p)
        elif action == "load_csv":
            return _do_load_csv(msg, p)
        elif action == "list_connections":
            names = {k: _connections[k].display_name for k in _connections}
            return msg.success({"connections": names})
        else:
            return msg.fail(f"Unknown action: {action}")
    except Exception as e:
        return msg.fail(f"{e.__class__.__name__}: {e}\n{traceback.format_exc()}")


# ---- action handlers ----
def _do_connect(msg: Message, p: dict) -> Message:
    from csv_analyzer.backend.drivers import create_driver

    conn_id = p.get("conn_id", "")
    db_type = p.get("db_type", "duckdb")

    if conn_id in _connections:
        try:
            _connections[conn_id].disconnect()
        except Exception:
            pass

    driver = create_driver(db_type)
    driver.connect(p)
    _connections[conn_id] = driver
    return msg.success({"conn_id": conn_id, "name": driver.display_name})


def _do_disconnect(msg: Message, p: dict) -> Message:
    conn_id = p.get("conn_id", "")
    driver = _connections.pop(conn_id, None)
    if driver:
        driver.disconnect()
    return msg.success({"conn_id": conn_id})


def _do_test(msg: Message, p: dict) -> Message:
    conn_id = p.get("conn_id", "")
    driver = _connections.get(conn_id)
    if not driver:
        return msg.fail("Connection not found")
    ok = driver.test_connection()
    return msg.success({"alive": ok})


def _do_execute(msg: Message, p: dict) -> Message:
    conn_id = p.get("conn_id", "")
    sql = p.get("sql", "")
    limit = p.get("limit", 500)
    offset = p.get("offset", 0)

    driver = _connections.get(conn_id)
    if not driver:
        return msg.fail("Connection not found")

    result = driver.execute(sql, limit=limit, offset=offset)
    if result.error:
        return msg.fail(result.error)

    # Sanitize values for serialization (convert non-serializable types)
    clean_rows = []
    for row in result.rows:
        clean_row = []
        for val in row:
            if val is None:
                clean_row.append(None)
            elif isinstance(val, (int, float, str, bool)):
                clean_row.append(val)
            else:
                clean_row.append(str(val))
        clean_rows.append(clean_row)

    return msg.success({
        "columns": result.columns,
        "rows": clean_rows,
        "row_count": result.row_count,
        "truncated": result.truncated,
        "affected": result.affected,
        "elapsed_ms": result.elapsed_ms,
    })


def _do_get_schemas(msg: Message, p: dict) -> Message:
    conn_id = p.get("conn_id", "")
    driver = _connections.get(conn_id)
    if not driver:
        return msg.fail("Connection not found")
    schemas = driver.get_schemas()
    return msg.success({"schemas": schemas})


def _do_get_tables(msg: Message, p: dict) -> Message:
    conn_id = p.get("conn_id", "")
    schema = p.get("schema", "main")
    driver = _connections.get(conn_id)
    if not driver:
        return msg.fail("Connection not found")
    tables = driver.get_tables(schema)
    return msg.success({"tables": [t.to_dict() for t in tables]})


def _do_get_columns(msg: Message, p: dict) -> Message:
    conn_id = p.get("conn_id", "")
    table = p.get("table", "")
    schema = p.get("schema", "main")
    driver = _connections.get(conn_id)
    if not driver:
        return msg.fail("Connection not found")
    columns = driver.get_columns(table, schema)
    return msg.success({"columns": [c.to_dict() for c in columns]})


def _do_load_csv(msg: Message, p: dict) -> Message:
    conn_id = p.get("conn_id", "")
    csv_path = p.get("csv_path", "")
    table_name = p.get("table_name")
    driver = _connections.get(conn_id)
    if not driver:
        return msg.fail("Connection not found")
    if not hasattr(driver, "load_csv"):
        return msg.fail("This driver does not support CSV loading")
    name = driver.load_csv(csv_path, table_name)
    return msg.success({"table_name": name})


# ---- process entry point ----
def db_process_main(in_queue: Queue, out_queue: Queue):
    """Entry point for the database subprocess."""
    while True:
        try:
            data = in_queue.get()
        except Exception:
            continue

        if data is None:
            break

        msg = Message.from_dict(data)
        if msg.action == "shutdown":
            # Disconnect all
            for driver in _connections.values():
                try:
                    driver.disconnect()
                except Exception:
                    pass
            _connections.clear()
            break

        response = _handle(msg)
        out_queue.put(response.to_dict())
