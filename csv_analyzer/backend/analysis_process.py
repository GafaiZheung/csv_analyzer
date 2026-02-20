"""Analysis process.

Runs in a dedicated subprocess.  Receives data (as lists of dicts / rows)
from the main process and returns statistical analysis results.

Supported actions:
  column_stats    – per-column descriptive statistics
  data_profile    – full table profiling overview
  missing_values  – null / missing value analysis
  distribution    – histogram / value-frequency data
  correlation     – pairwise correlation matrix (numeric columns)
  shutdown
"""
from __future__ import annotations

import math
import traceback
from collections import Counter
from multiprocessing import Queue
from typing import Any

from csv_analyzer.core.message import Message


def _safe_float(v):
    """Convert to float, return None on failure."""
    if v is None:
        return None
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (ValueError, TypeError):
        return None


def _handle(msg: Message) -> Message:
    action = msg.action
    p = msg.payload

    try:
        if action == "column_stats":
            return _do_column_stats(msg, p)
        elif action == "data_profile":
            return _do_data_profile(msg, p)
        elif action == "missing_values":
            return _do_missing_values(msg, p)
        elif action == "distribution":
            return _do_distribution(msg, p)
        elif action == "correlation":
            return _do_correlation(msg, p)
        else:
            return msg.fail(f"Unknown analysis action: {action}")
    except Exception as e:
        return msg.fail(f"{e.__class__.__name__}: {e}\n{traceback.format_exc()}")


# ---- analysis handlers ----

def _do_column_stats(msg: Message, p: dict) -> Message:
    """Compute statistics for a single column."""
    values = p.get("values", [])
    col_name = p.get("column", "")

    total = len(values)
    nulls = sum(1 for v in values if v is None)
    non_null = total - nulls
    unique = len(set(str(v) for v in values if v is not None))

    stats: dict[str, Any] = {
        "column": col_name,
        "total": total,
        "non_null": non_null,
        "null_count": nulls,
        "null_pct": round(nulls / total * 100, 2) if total else 0,
        "unique": unique,
    }

    # Try numeric stats
    nums = [f for v in values if (f := _safe_float(v)) is not None]
    if len(nums) > 0:
        nums.sort()
        n = len(nums)
        mean = sum(nums) / n
        variance = sum((x - mean) ** 2 for x in nums) / n if n > 1 else 0
        std = math.sqrt(variance)

        stats.update({
            "dtype": "numeric",
            "min": nums[0],
            "max": nums[-1],
            "mean": round(mean, 4),
            "std": round(std, 4),
            "median": nums[n // 2],
            "p25": nums[n // 4],
            "p75": nums[3 * n // 4],
        })
    else:
        # String stats
        str_vals = [str(v) for v in values if v is not None]
        if str_vals:
            lengths = [len(s) for s in str_vals]
            stats.update({
                "dtype": "string",
                "min_length": min(lengths),
                "max_length": max(lengths),
                "avg_length": round(sum(lengths) / len(lengths), 2),
            })
        else:
            stats["dtype"] = "empty"

    # Top values
    counter = Counter(str(v) for v in values if v is not None)
    stats["top_values"] = [
        {"value": val, "count": cnt}
        for val, cnt in counter.most_common(10)
    ]

    return msg.success(stats)


def _do_data_profile(msg: Message, p: dict) -> Message:
    """Profile entire dataset: columns, rows, types."""
    columns = p.get("columns", [])
    rows = p.get("rows", [])

    total_rows = len(rows)
    col_profiles = []
    for i, col in enumerate(columns):
        values = [row[i] if i < len(row) else None for row in rows]
        nulls = sum(1 for v in values if v is None)
        unique = len(set(str(v) for v in values if v is not None))
        nums = [f for v in values if (f := _safe_float(v)) is not None]

        profile = {
            "name": col,
            "dtype": "numeric" if len(nums) > total_rows * 0.5 else "string",
            "non_null": total_rows - nulls,
            "null_pct": round(nulls / total_rows * 100, 2) if total_rows else 0,
            "unique": unique,
        }
        col_profiles.append(profile)

    return msg.success({
        "row_count": total_rows,
        "col_count": len(columns),
        "columns": col_profiles,
    })


def _do_missing_values(msg: Message, p: dict) -> Message:
    """Missing value analysis per column."""
    columns = p.get("columns", [])
    rows = p.get("rows", [])
    total = len(rows)

    result = []
    for i, col in enumerate(columns):
        nulls = sum(1 for row in rows if i >= len(row) or row[i] is None)
        result.append({
            "column": col,
            "null_count": nulls,
            "null_pct": round(nulls / total * 100, 2) if total else 0,
            "non_null": total - nulls,
        })

    # Sort by null_pct descending
    result.sort(key=lambda x: x["null_pct"], reverse=True)
    return msg.success({"total_rows": total, "columns": result})


def _do_distribution(msg: Message, p: dict) -> Message:
    """Histogram / value frequency for a column."""
    values = p.get("values", [])
    col_name = p.get("column", "")
    bins = p.get("bins", 20)

    nums = [f for v in values if (f := _safe_float(v)) is not None]

    if len(nums) > 10:
        # Numeric histogram
        lo, hi = min(nums), max(nums)
        if lo == hi:
            histogram = [{"bin": f"{lo}", "count": len(nums)}]
        else:
            step = (hi - lo) / bins
            histogram = []
            for b in range(bins):
                edge_lo = lo + b * step
                edge_hi = lo + (b + 1) * step
                count = sum(1 for x in nums if edge_lo <= x < edge_hi)
                if b == bins - 1:
                    count = sum(1 for x in nums if edge_lo <= x <= edge_hi)
                histogram.append({
                    "bin": f"{round(edge_lo, 2)}–{round(edge_hi, 2)}",
                    "count": count,
                })
        return msg.success({
            "column": col_name,
            "type": "histogram",
            "data": histogram,
        })
    else:
        # Categorical frequency
        counter = Counter(str(v) for v in values if v is not None)
        freq = [{"value": val, "count": cnt} for val, cnt in counter.most_common(30)]
        return msg.success({
            "column": col_name,
            "type": "frequency",
            "data": freq,
        })


def _do_correlation(msg: Message, p: dict) -> Message:
    """Pairwise Pearson correlation for numeric columns."""
    columns = p.get("columns", [])
    rows = p.get("rows", [])

    # Find numeric columns
    numeric_cols = []
    col_data: dict[str, list[float]] = {}

    for i, col in enumerate(columns):
        vals = [_safe_float(row[i]) if i < len(row) else None for row in rows]
        nums = [v for v in vals if v is not None]
        if len(nums) > len(rows) * 0.5:
            numeric_cols.append(col)
            col_data[col] = [v if v is not None else 0.0 for v in vals]

    if len(numeric_cols) < 2:
        return msg.success({"columns": numeric_cols, "matrix": []})

    # Compute correlation matrix
    matrix = []
    for a in numeric_cols:
        row = []
        for b in numeric_cols:
            va, vb = col_data[a], col_data[b]
            n = len(va)
            mean_a = sum(va) / n
            mean_b = sum(vb) / n
            cov = sum((va[i] - mean_a) * (vb[i] - mean_b) for i in range(n)) / n
            std_a = math.sqrt(sum((x - mean_a) ** 2 for x in va) / n)
            std_b = math.sqrt(sum((x - mean_b) ** 2 for x in vb) / n)
            if std_a > 0 and std_b > 0:
                corr = round(cov / (std_a * std_b), 4)
            else:
                corr = 0.0
            row.append(corr)
        matrix.append(row)

    return msg.success({"columns": numeric_cols, "matrix": matrix})


# ---- process entry point ----

def analysis_process_main(in_queue: Queue, out_queue: Queue):
    """Entry point for the analysis subprocess."""
    while True:
        try:
            data = in_queue.get()
        except Exception:
            continue

        if data is None:
            break

        msg = Message.from_dict(data)
        if msg.action == "shutdown":
            break

        response = _handle(msg)
        out_queue.put(response.to_dict())
