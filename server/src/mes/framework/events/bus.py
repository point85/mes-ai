"""
EVENT-BUS: In-process async publish/subscribe event bus.

Supports:
- Exact topic matching: "wip.unit.moved"
- Wildcard matching: "wip.unit.*" or "wip.*" or "*"
- Async handlers with error isolation (a failing handler does not affect others)

Future: swap transport to Kafka/NATS/Redis by replacing the _dispatch method
while keeping the same MESEvent schema and handler interface (see ARCHITECTURE.md §8.5).
"""

from __future__ import annotations

import asyncio
import fnmatch
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

from .schema import MESEvent

logger = logging.getLogger("mes.events")

# Type alias for event handler callables
EventHandler = Callable[[MESEvent], Coroutine[Any, Any, None]]


class EventBus:
    """
    In-process async event bus with dot-notation topic matching and wildcard support.

    Usage:
        bus = EventBus()
        bus.subscribe("wip.unit.moved", handler_fn)
        await bus.publish(MESEvent(event_type="wip.unit.moved", source="WIP-TRACK", payload={...}))
    """

    def __init__(self) -> None:
        # topic_pattern -> list of handler callables
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._started: bool = False

    def subscribe(self, topic_pattern: str, handler: EventHandler) -> None:
        """
        Register a handler for a topic pattern.

        Args:
            topic_pattern: Exact topic or wildcard pattern (e.g. "wip.unit.*", "quality.*", "*").
            handler: Async callable accepting a MESEvent.
        """
        self._handlers[topic_pattern].append(handler)
        logger.debug("Subscribed handler %s to topic '%s'", handler.__qualname__, topic_pattern)

    def unsubscribe(self, topic_pattern: str, handler: EventHandler) -> None:
        """Remove a handler from a topic pattern."""
        handlers = self._handlers.get(topic_pattern, [])
        if handler in handlers:
            handlers.remove(handler)
            logger.debug(
                "Unsubscribed handler %s from topic '%s'", handler.__qualname__, topic_pattern
            )

    async def publish(self, event: MESEvent) -> None:
        """
        Publish an event to all matching subscribers.

        Handlers are invoked concurrently via asyncio.gather.
        Individual handler errors are logged and isolated — they do not propagate
        to the publisher or affect other handlers.
        """
        matching_handlers = self._collect_handlers(event.event_type)
        if not matching_handlers:
            logger.debug("No handlers for event type '%s'", event.event_type)
            return

        logger.debug(
            "Publishing event '%s' (id=%s) to %d handler(s)",
            event.event_type,
            event.event_id,
            len(matching_handlers),
        )

        results = await asyncio.gather(
            *(self._safe_invoke(handler, event) for handler in matching_handlers),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                logger.error(
                    "Unhandled exception in event handler for '%s': %s",
                    event.event_type,
                    result,
                    exc_info=result,
                )

    def _collect_handlers(self, event_type: str) -> list[EventHandler]:
        """
        Collect all handlers whose subscription pattern matches the event type.

        Matching rules:
        - Exact match: "wip.unit.moved" matches "wip.unit.moved"
        - Wildcard: "wip.unit.*" matches "wip.unit.moved", "wip.unit.created", etc.
        - Deep wildcard: "wip.*" matches "wip.unit.moved", "wip.lot.created", etc.
        - Global wildcard: "*" matches everything
        """
        matched: list[EventHandler] = []
        for pattern, handlers in self._handlers.items():
            if self._matches(pattern, event_type):
                matched.extend(handlers)
        return matched

    @staticmethod
    def _matches(pattern: str, event_type: str) -> bool:
        """
        Check if a subscription pattern matches an event type.

        Uses fnmatch-style globbing where '*' matches within segments
        and '**' is not needed because we treat '*' at the end as matching
        all remaining segments.
        """
        if pattern == "*":
            return True
        # Convert dot-notation to path-like for fnmatch
        # "wip.unit.*" should match "wip.unit.moved" and "wip.unit.created"
        # "wip.*" should match "wip.unit.moved" (match all descendants)
        pattern_parts = pattern.split(".")
        event_parts = event_type.split(".")

        # If the pattern ends with '*', it matches any number of remaining segments
        if pattern_parts[-1] == "*":
            prefix_parts = pattern_parts[:-1]
            if len(event_parts) < len(prefix_parts):
                return False
            return event_parts[: len(prefix_parts)] == prefix_parts

        # Exact match
        return fnmatch.fnmatch(event_type, pattern)

    @staticmethod
    async def _safe_invoke(handler: EventHandler, event: MESEvent) -> None:
        """Invoke a handler with exception isolation."""
        try:
            await handler(event)
        except Exception as exc:
            logger.error(
                "Handler %s raised %s for event '%s': %s",
                handler.__qualname__,
                type(exc).__name__,
                event.event_type,
                exc,
            )
            raise

    def clear(self) -> None:
        """Remove all subscriptions. Useful for testing."""
        self._handlers.clear()

    @property
    def subscription_count(self) -> int:
        """Total number of active handler registrations."""
        return sum(len(h) for h in self._handlers.values())


# Module-level singleton — the global event bus instance for the application
event_bus = EventBus()
