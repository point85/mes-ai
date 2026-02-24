"""
EVENT-BUS: Event schema for the MES event system.
All events flowing through the bus use this canonical schema.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class MESEvent(BaseModel):
    """
    Canonical event schema for the MES event bus.
    All events — whether emitted by core modules or plugins — use this structure.
    """

    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this event instance",
    )
    event_type: str = Field(
        ...,
        description="Dot-notation topic (e.g. 'wip.unit.moved')",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the event was created",
    )
    source: str = Field(
        ...,
        description="Module or plugin ID that emitted the event",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description="Event-specific data",
    )
    correlation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="ID for tracing related events across a workflow",
    )
