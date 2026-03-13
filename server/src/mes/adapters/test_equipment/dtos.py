"""
Test Equipment Adapter: Data Transfer Objects.

Per ARCHITECTURE.md §9.4.
"""

from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TestResultDTO:
    """Test result received from test/quality equipment."""

    test_id: str
    equipment_id: str
    unit_serial: str | None = None
    lot_number: str | None = None
    result: str = "pass"  # "pass" | "fail" | "inconclusive"
    measured_values: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)
