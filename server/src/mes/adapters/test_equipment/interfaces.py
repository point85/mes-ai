"""
Test Equipment Adapter: Abstract interfaces for test equipment data collection.

Concrete implementations connect via file drop, REST, OPC-UA, or MOM.

Per ARCHITECTURE.md §9.4.
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable

from mes.adapters.base import BaseAdapter
from mes.adapters.equipment.dtos import SubscriptionHandle

from .dtos import TestResultDTO


class TestEquipmentAdapter(BaseAdapter):
    """Abstract interface for test equipment data collection."""

    @abstractmethod
    async def get_test_result(self, test_id: str) -> TestResultDTO:
        """Retrieve a specific test result by ID."""
        ...

    @abstractmethod
    async def subscribe_results(
        self,
        callback: Callable[[TestResultDTO], None],
    ) -> SubscriptionHandle:
        """Subscribe to incoming test results."""
        ...

    @abstractmethod
    async def get_test_status(self, equipment_id: str) -> str:
        """
        Get current status of a test equipment.

        Returns:
            Status string: "idle" | "testing" | "error" | "offline"
        """
        ...


class FileDropTestAdapter(TestEquipmentAdapter):
    """
    Abstract base for test adapters that watch a directory for result files.

    Concrete implementations parse CSV/XML/JSON files dropped by test equipment
    into the watched directory.
    """

    @abstractmethod
    async def watch_directory(
        self,
        path: str,
        pattern: str = "*.csv",
    ) -> None:
        """
        Start watching a directory for new test result files.

        Args:
            path: Directory path to watch.
            pattern: Glob pattern for result files.
        """
        ...
