"""
Equipment Adapter: Abstract interfaces for equipment and MOM communication.

Concrete implementations use OPC-UA (asyncua), MQTT (aiomqtt),
Modbus TCP (pymodbus), HTTP/REST (httpx), or MOM brokers (Kafka, RabbitMQ, etc.).

Per ARCHITECTURE.md §9.3.2.
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Callable
from typing import Any

from mes.adapters.base import BaseAdapter

from .dtos import EquipmentState, SubscriptionHandle, TagInfo, TagValue


class EquipmentAdapter(BaseAdapter):
    """
    Abstract interface for direct equipment communication.

    Supports tag-based read/write/subscribe patterns used by
    OPC-UA, MQTT, Modbus, and REST-based equipment.
    """

    @abstractmethod
    async def read_tag(self, tag_name: str) -> TagValue:
        """Read the current value of an equipment tag."""
        ...

    @abstractmethod
    async def write_tag(self, tag_name: str, value: Any) -> None:
        """Write a value to an equipment tag."""
        ...

    @abstractmethod
    async def subscribe_tag(
        self,
        tag_name: str,
        callback: Callable[[TagValue], Any],
        interval_ms: int = 1000,
    ) -> SubscriptionHandle:
        """
        Subscribe to value changes on a tag.

        Args:
            tag_name: Tag identifier.
            callback: Async or sync callable invoked on each value change.
            interval_ms: Sampling interval in milliseconds.

        Returns:
            Handle for managing the subscription.
        """
        ...

    @abstractmethod
    async def unsubscribe(self, handle: SubscriptionHandle) -> None:
        """Cancel a tag subscription."""
        ...

    @abstractmethod
    async def get_equipment_state(self) -> EquipmentState:
        """Get the current equipment state."""
        ...

    @abstractmethod
    async def browse_tags(self, root: str | None = None) -> list[TagInfo]:
        """
        Browse available tags from the equipment.

        Args:
            root: Optional root node to start browsing from.

        Returns:
            List of available tags.
        """
        ...


class MOMEquipmentAdapter(BaseAdapter):
    """
    Abstract interface for equipment data via message-oriented middleware.

    Used when equipment data flows through Kafka, RabbitMQ, ActiveMQ, etc.
    rather than direct protocol connections.

    Per ARCHITECTURE.md §9.3.2.
    """

    @abstractmethod
    async def subscribe_topic(
        self,
        topic: str,
        callback: Callable[[dict[str, Any]], Any],
    ) -> SubscriptionHandle:
        """Subscribe to a MOM topic for equipment data."""
        ...

    @abstractmethod
    async def publish(self, topic: str, payload: dict[str, Any]) -> None:
        """Publish a message to a MOM topic."""
        ...

    @abstractmethod
    async def consume_queue(
        self,
        queue_name: str,
        callback: Callable[[dict[str, Any]], Any],
    ) -> None:
        """Consume messages from a named queue."""
        ...
