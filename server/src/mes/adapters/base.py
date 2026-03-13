"""
Integration Adapters: Base adapter interface.

All integration adapters (ERP, equipment, test equipment) inherit from
BaseAdapter, which provides a common lifecycle contract.

Per ARCHITECTURE.md §9.1.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    """
    Base for all integration adapters.

    Lifecycle: connect() → [operational] → disconnect()
    Use health_check() to verify connectivity at any time.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the external system."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully close the connection."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the adapter can communicate with the external system.

        Returns:
            True if connected and healthy, False otherwise.
        """
        ...
