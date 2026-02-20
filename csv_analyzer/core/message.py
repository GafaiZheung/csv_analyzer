"""Unified message protocol for inter-process communication.

All communication between the main process, database process, and analysis
process uses the Message dataclass as the standard envelope.
"""
from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Message:
    """Standard message for all IPC communication.

    Attributes:
        action:  Operation name, e.g. 'connect', 'execute_sql', 'analyze'.
        target:  Destination process – 'db', 'analysis', or 'main'.
        msg_id:  Unique identifier for request/response matching.
        type:    'request', 'response', or 'event'.
        payload: Action-specific data dictionary.
        status:  'pending', 'success', or 'error'.
        error:   Error description when status == 'error'.
    """
    action: str
    target: str = "db"
    msg_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: str = "request"
    payload: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    error: str | None = None
    timestamp: float = field(default_factory=time.time)

    # ---- serialization ----
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)

    # ---- response helpers ----
    def success(self, payload: dict | None = None) -> "Message":
        """Create a success response to this request."""
        return Message(
            action=self.action,
            target="main",
            msg_id=self.msg_id,
            type="response",
            payload=payload or {},
            status="success",
        )

    def fail(self, error: str) -> "Message":
        """Create an error response to this request."""
        return Message(
            action=self.action,
            target="main",
            msg_id=self.msg_id,
            type="response",
            payload={},
            status="error",
            error=error,
        )

    def event(self, action: str, payload: dict | None = None) -> "Message":
        """Create an event message (no request/response matching)."""
        return Message(
            action=action,
            target="main",
            type="event",
            payload=payload or {},
            status="success",
        )
