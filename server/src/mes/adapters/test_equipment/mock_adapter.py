"""
Test Equipment Adapter: Mock implementation for development, testing, and demo.

Generates random test results with configurable pass/fail distributions
and measurement ranges.

Per ARCHITECTURE.md §9.4.
"""

from __future__ import annotations

import logging
import random
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from mes.adapters.equipment.dtos import SubscriptionHandle

from .dtos import TestResultDTO
from .interfaces import TestEquipmentAdapter

logger = logging.getLogger("mes.adapters.test_equipment.mock")


class MockTestEquipmentAdapter(TestEquipmentAdapter):
    """
    Mock test equipment that generates random test results.

    Config options:
        equipment_id: Identifier for this simulated test station.
        pass_rate: Probability [0.0, 1.0] of a test passing (default 0.9).
        measurements: Dict defining measurement ranges.
            Key: measurement name, Value: (min, max) tuple.
            Example: {"length": (9.8, 10.2), "weight": (49.5, 50.5)}
        status: Initial equipment status (default "idle").
    """

    def __init__(
        self,
        equipment_id: str = "MOCK-TEST-01",
        pass_rate: float = 0.9,
        measurements: dict[str, tuple[float, float]] | None = None,
        status: str = "idle",
    ) -> None:
        self._equipment_id = equipment_id
        self._pass_rate = max(0.0, min(1.0, pass_rate))
        self._measurements = measurements or {
            "dimension_x": (9.95, 10.05),
            "dimension_y": (4.95, 5.05),
            "weight": (99.0, 101.0),
        }
        self._status = status
        self._connected = False
        self._result_counter = 0
        self._subscribers: list[tuple[SubscriptionHandle, Callable]] = []

    @property
    def result_count(self) -> int:
        """Number of results generated so far."""
        return self._result_counter

    async def connect(self) -> None:
        self._connected = True
        logger.info("MockTestEquipmentAdapter connected: %s", self._equipment_id)

    async def disconnect(self) -> None:
        for handle, _ in self._subscribers:
            handle.active = False
        self._subscribers.clear()
        self._connected = False
        logger.info("MockTestEquipmentAdapter disconnected: %s", self._equipment_id)

    async def health_check(self) -> bool:
        return self._connected

    async def get_test_result(self, test_id: str) -> TestResultDTO:
        """Generate a random test result."""
        return self._generate_result(test_id=test_id)

    async def subscribe_results(
        self,
        callback: Callable[[TestResultDTO], None],
    ) -> SubscriptionHandle:
        handle = SubscriptionHandle(active=True)
        self._subscribers.append((handle, callback))
        return handle

    async def get_test_status(self, equipment_id: str) -> str:
        return self._status

    async def watch_directory(self, path: str, pattern: str = "*.csv") -> None:
        # Mock: no-op — no real filesystem watching
        logger.info("MockTestEquipmentAdapter: watch_directory('%s', '%s') — no-op", path, pattern)

    def generate_and_notify(
        self,
        test_id: str = "auto",
        unit_serial: str | None = None,
        lot_number: str | None = None,
    ) -> TestResultDTO:
        """Generate a result and notify all subscribers (for test scenarios)."""
        result = self._generate_result(
            test_id=test_id,
            unit_serial=unit_serial,
            lot_number=lot_number,
        )
        for handle, callback in self._subscribers:
            if handle.active:
                try:
                    callback(result)
                except Exception:
                    logger.exception("Test result subscriber callback error")
        return result

    def set_status(self, status: str) -> None:
        """Directly change equipment status (for test scenarios)."""
        self._status = status

    def _generate_result(
        self,
        test_id: str = "auto",
        unit_serial: str | None = None,
        lot_number: str | None = None,
    ) -> TestResultDTO:
        """Generate a single random test result."""
        self._result_counter += 1
        passed = random.random() < self._pass_rate  # noqa: S311

        measured_values: dict[str, Any] = {}
        for name, (low, high) in self._measurements.items():
            measured_values[name] = round(random.uniform(low, high), 4)  # noqa: S311

        return TestResultDTO(
            test_id=test_id if test_id != "auto" else f"TEST-{self._result_counter:04d}",
            equipment_id=self._equipment_id,
            unit_serial=unit_serial,
            lot_number=lot_number,
            result="pass" if passed else "fail",
            measured_values=measured_values,
            timestamp=datetime.now(timezone.utc),
        )
