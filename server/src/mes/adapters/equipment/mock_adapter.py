"""
Equipment Adapter: Mock implementation for development, testing, and demo.

In-memory tag store with configurable noise, simulated state changes,
and subscription callbacks.

Per ARCHITECTURE.md §9.3.4.
"""

from __future__ import annotations

import asyncio
import logging
import random
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from .dtos import EquipmentState, SubscriptionHandle, TagInfo, TagValue
from .interfaces import EquipmentAdapter

logger = logging.getLogger("mes.adapters.equipment.mock")


class MockEquipmentAdapter(EquipmentAdapter):
    """
    Mock equipment adapter with an in-memory tag store.

    Config options:
        equipment_id: Identifier for this simulated equipment.
        initial_tags: Dict of tag_name → initial_value.
        noise_stddev: Standard deviation for Gaussian noise on numeric reads (default 0).
        latency_ms: Simulated response latency in milliseconds (default 0).
        failure_rate: Probability [0.0, 1.0) of raising an error (default 0.0).
        initial_state: Starting equipment state (default "idle").
    """

    def __init__(
        self,
        equipment_id: str = "MOCK-EQUIP-01",
        initial_tags: dict[str, Any] | None = None,
        noise_stddev: float = 0.0,
        latency_ms: int = 0,
        failure_rate: float = 0.0,
        initial_state: str = "idle",
    ) -> None:
        self._equipment_id = equipment_id
        self._tag_store: dict[str, Any] = dict(initial_tags or {})
        self._tag_types: dict[str, str] = {}
        self._noise_stddev = max(0.0, noise_stddev)
        self._latency_ms = max(0, latency_ms)
        self._failure_rate = max(0.0, min(1.0, failure_rate))
        self._state = initial_state
        self._connected = False
        self._subscriptions: dict[str, _Subscription] = {}

        # Infer data types from initial values
        for tag_name, value in self._tag_store.items():
            self._tag_types[tag_name] = _infer_type(value)

    @property
    def tag_store(self) -> dict[str, Any]:
        """Direct access to the tag store for test manipulation."""
        return self._tag_store

    async def connect(self) -> None:
        await self._simulate_latency()
        self._connected = True
        logger.info("MockEquipmentAdapter connected: %s", self._equipment_id)

    async def disconnect(self) -> None:
        # Cancel all subscriptions
        for sub in self._subscriptions.values():
            sub.handle.active = False
        self._subscriptions.clear()
        self._connected = False
        logger.info("MockEquipmentAdapter disconnected: %s", self._equipment_id)

    async def health_check(self) -> bool:
        return self._connected

    async def read_tag(self, tag_name: str) -> TagValue:
        await self._simulate_latency()
        self._maybe_fail()
        if tag_name not in self._tag_store:
            from .exceptions import TagNotFoundError
            raise TagNotFoundError(tag_name=tag_name)

        raw_value = self._tag_store[tag_name]
        value = self._apply_noise(raw_value)

        return TagValue(
            tag_name=tag_name,
            value=value,
            quality="good",
            timestamp=datetime.now(timezone.utc),
            data_type=self._tag_types.get(tag_name, "float"),
        )

    async def write_tag(self, tag_name: str, value: Any) -> None:
        await self._simulate_latency()
        self._maybe_fail()
        self._tag_store[tag_name] = value
        self._tag_types[tag_name] = _infer_type(value)

        # Notify subscribers
        if tag_name in self._subscriptions:
            sub = self._subscriptions[tag_name]
            if sub.handle.active:
                tag_value = TagValue(
                    tag_name=tag_name,
                    value=value,
                    quality="good",
                    timestamp=datetime.now(timezone.utc),
                    data_type=self._tag_types[tag_name],
                )
                try:
                    result = sub.callback(tag_value)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:
                    logger.exception("Subscription callback error for tag '%s'", tag_name)

    async def subscribe_tag(
        self,
        tag_name: str,
        callback: Callable[[TagValue], Any],
        interval_ms: int = 1000,
    ) -> SubscriptionHandle:
        await self._simulate_latency()
        handle = SubscriptionHandle(tag_name=tag_name, active=True)
        self._subscriptions[tag_name] = _Subscription(
            handle=handle,
            callback=callback,
            interval_ms=interval_ms,
        )
        logger.debug("Subscribed to tag '%s' (interval=%dms)", tag_name, interval_ms)
        return handle

    async def unsubscribe(self, handle: SubscriptionHandle) -> None:
        handle.active = False
        # Remove from subscriptions by matching handle_id
        to_remove = [
            tag for tag, sub in self._subscriptions.items()
            if sub.handle.handle_id == handle.handle_id
        ]
        for tag in to_remove:
            del self._subscriptions[tag]

    async def get_equipment_state(self) -> EquipmentState:
        await self._simulate_latency()
        return EquipmentState(
            equipment_id=self._equipment_id,
            state=self._state,
            dispatch_category="available" if self._state in ("idle", "running") else "unavailable_unplanned",
        )

    async def browse_tags(self, root: str | None = None) -> list[TagInfo]:
        await self._simulate_latency()
        tags = []
        for tag_name in sorted(self._tag_store.keys()):
            if root and not tag_name.startswith(root):
                continue
            tags.append(TagInfo(
                tag_name=tag_name,
                data_type=self._tag_types.get(tag_name, "float"),
                access="readwrite",
                description=f"Mock tag: {tag_name}",
            ))
        return tags

    def set_state(self, state: str) -> None:
        """Directly change equipment state (for test scenarios)."""
        self._state = state

    def _apply_noise(self, value: Any) -> Any:
        """Add Gaussian noise to numeric values."""
        if self._noise_stddev > 0 and isinstance(value, (int, float)):
            return value + random.gauss(0, self._noise_stddev)  # noqa: S311
        return value

    async def _simulate_latency(self) -> None:
        if self._latency_ms > 0:
            await asyncio.sleep(self._latency_ms / 1000.0)

    def _maybe_fail(self) -> None:
        if self._failure_rate > 0 and random.random() < self._failure_rate:  # noqa: S311
            from .exceptions import CommunicationTimeoutError
            raise CommunicationTimeoutError()


class _Subscription:
    """Internal subscription state."""

    __slots__ = ("handle", "callback", "interval_ms")

    def __init__(
        self,
        handle: SubscriptionHandle,
        callback: Callable[[TagValue], Any],
        interval_ms: int,
    ) -> None:
        self.handle = handle
        self.callback = callback
        self.interval_ms = interval_ms


def _infer_type(value: Any) -> str:
    """Infer tag data type from Python value."""
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (list, tuple)):
        return "array"
    return "string"
