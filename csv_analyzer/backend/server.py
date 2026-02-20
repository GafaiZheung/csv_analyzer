"""JSON-RPC server for the Electron frontend.

Reads one JSON object per line from *stdin*, dispatches to the existing
``db_process`` or ``analysis_process`` handler, and writes one JSON
response per line to *stdout*.

Designed to be spawned as a child process by Electron's main process.
"""
from __future__ import annotations

import sys
import json

# Ensure the project root is on sys.path so imports work when
# this file is executed directly by Electron.
from pathlib import Path
_root = str(Path(__file__).resolve().parents[2])
if _root not in sys.path:
    sys.path.insert(0, _root)

from csv_analyzer.core.message import Message
from csv_analyzer.backend.db_process import _handle as db_handle
from csv_analyzer.backend.analysis_process import _handle as analysis_handle


def main() -> None:
    """Event loop: read stdin line by line, write responses to stdout."""
    # Make stderr line-buffered for logging
    sys.stderr.reconfigure(line_buffering=True)
    sys.stderr.write("[server] Python server started, waiting for input...\n")
    sys.stderr.flush()

    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue

        try:
            data: dict = json.loads(line)
        except json.JSONDecodeError as exc:
            sys.stderr.write(f"Invalid JSON from Electron: {exc}\n")
            continue

        action = data.get("action", "")
        if action == "shutdown":
            break

        msg = Message.from_dict(data)
        target = data.get("target", "db")

        if target == "analysis":
            response = analysis_handle(msg)
        else:
            response = db_handle(msg)

        sys.stdout.write(json.dumps(response.to_dict()) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
