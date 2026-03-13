"""
Equipment Adapter: Data Transfer Objects.

Canonical data types for equipment communication — tag values,
tag metadata, subscription handles, and equipment state.

Per ARCHITECTURE.md §9.3.2.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class TagValue:
    """Value read from an equipment tag/variable."""

    tag_name: str
    value: Any
    quality: str = "good"  # "good" | "bad" | "uncertain"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data_type: str = "float"  # "float" | "int" | "bool" | "string" | "array"


@dataclass
class TagInfo:
    """Metadata about an equipment tag/variable."""

    tag_name: str
    data_type: str
    access: str = "readwrite"  # "read" | "write" | "readwrite"
    description: str = ""


@dataclass
class SubscriptionHandle:
    """Handle returned when subscribing to tag value changes or MOM topics."""

    handle_id: str = field(default_factory=lambda: str(uuid4()))
    tag_name: str = ""
    topic: str = ""
    active: bool = True


@dataclass
class EquipmentState:
    """Current state of a piece of equipment."""

    equipment_id: str
    state: str  # Equipment state (model-dependent, e.g. PackML, SEMI E10)
    sub_state: str = ""
    dispatch_category: str = "available"  # available | busy | unavailable_planned | unavailable_unplanned
    oee_bucket: str = "uptime_value_add"  # uptime_value_add | uptime_non_value | downtime_planned | downtime_unplanned | excluded
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
