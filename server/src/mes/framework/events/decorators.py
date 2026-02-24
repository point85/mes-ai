"""
EVENT-BUS: Decorator for registering event handlers.

Handlers decorated with @event_handler are collected at import time
and registered with the event bus during application startup.
"""

from __future__ import annotations

from typing import Any, Callable, Coroutine

from .schema import MESEvent

# Type alias
EventHandler = Callable[[MESEvent], Coroutine[Any, Any, None]]

# Global registry of decorated handlers: list of (topic_pattern, handler)
_handler_registry: list[tuple[str, EventHandler]] = []


def event_handler(topic_pattern: str) -> Callable[[EventHandler], EventHandler]:
    """
    Decorator to register an async function as an event handler for a topic pattern.

    Usage:
        @event_handler("wip.unit.completed")
        async def on_unit_completed(event: MESEvent) -> None:
            ...

        @event_handler("quality.*")
        async def on_quality_event(event: MESEvent) -> None:
            ...
    """

    def decorator(func: EventHandler) -> EventHandler:
        _handler_registry.append((topic_pattern, func))
        return func

    return decorator


def get_registered_handlers() -> list[tuple[str, EventHandler]]:
    """Return all handlers collected via the @event_handler decorator."""
    return list(_handler_registry)


def clear_handler_registry() -> None:
    """Clear all registered handlers. Useful for testing."""
    _handler_registry.clear()
