"""
Example plugin: priority-weighted dispatch strategy.

Demonstrates:
- Subclassing MESPlugin with full lifecycle
- Declaring a ``dispatch_strategy`` extension point
- Subscribing to events via ``get_event_handlers``
- Exposing a custom REST endpoint via ``get_routes``
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from mes.framework.plugin.base import MESPlugin

logger = logging.getLogger("mes.plugins.example_dispatch")

router = APIRouter(prefix="/api/v1/plugins/example-dispatch", tags=["plugins"])


class ExampleDispatchPlugin(MESPlugin):
    """A sample plugin that registers a priority-weighted dispatch strategy."""

    def __init__(self) -> None:
        self._priority_weight: float = 0.6
        self._queue_weight: float = 0.4
        self._events_received: int = 0

    # ── Lifecycle ────────────────────────────────────────────

    async def initialize(self, config: dict[str, Any]) -> None:
        self._priority_weight = float(config.get("priority_weight", 0.6))
        self._queue_weight = float(config.get("queue_weight", 0.4))
        logger.info(
            "ExampleDispatchPlugin initialised  "
            "priority_weight=%.2f  queue_weight=%.2f",
            self._priority_weight,
            self._queue_weight,
        )

    async def start(self) -> None:
        logger.info("ExampleDispatchPlugin started")

    async def stop(self) -> None:
        logger.info(
            "ExampleDispatchPlugin stopped  events_received=%d",
            self._events_received,
        )

    # ── Extension points ─────────────────────────────────────

    def get_routes(self) -> list[APIRouter]:
        return [router]

    def get_event_handlers(self) -> dict[str, Any]:
        return {
            "wip.unit.moved": self._on_unit_moved,
        }

    # ── Event handler ────────────────────────────────────────

    async def _on_unit_moved(self, event: dict[str, Any]) -> None:
        self._events_received += 1
        logger.debug("priority_weighted saw wip.unit.moved: %s", event.get("unit_id"))

    # ── Strategy logic (callable from dispatch service) ──────

    def score(
        self,
        order_priority: int,
        queue_length: int,
        max_priority: int = 10,
        max_queue: int = 50,
    ) -> float:
        """Return a 0-1 score combining order priority and queue length.

        Higher is better (prefer high priority, short queue).
        """
        priority_norm = min(order_priority / max_priority, 1.0) if max_priority else 0.0
        queue_norm = 1.0 - min(queue_length / max_queue, 1.0) if max_queue else 1.0
        return self._priority_weight * priority_norm + self._queue_weight * queue_norm


# ── Custom endpoint ──────────────────────────────────────────

@router.get("/status")
async def plugin_status() -> dict[str, Any]:
    """Health-check / info endpoint for the example plugin."""
    return {"plugin": "example-dispatch", "status": "ok"}
