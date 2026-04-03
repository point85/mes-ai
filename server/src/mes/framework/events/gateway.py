"""
EVENT-BUS: WebSocket gateway for real-time event streaming to browser clients.

Subscribes to the in-process event bus with a wildcard handler and forwards
every MESEvent to all connected WebSocket clients as JSON.  Clients can
optionally send a JSON subscribe message to filter by topic patterns:

    {"action": "subscribe", "topics": ["wip.unit.*", "dispatch.*"]}

If no subscribe message is sent, the client receives ALL events.
"""

from __future__ import annotations

import asyncio
import fnmatch
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .bus import event_bus
from .schema import MESEvent

logger = logging.getLogger("mes.events.gateway")

router = APIRouter(tags=["Real-Time Events"])

# ── Connection Manager ───────────────────────────────────────────────


class _ConnectionManager:
    """Track active WebSocket connections and their topic filters."""

    def __init__(self) -> None:
        # ws -> set of topic patterns (empty set = all events)
        self._connections: dict[WebSocket, set[str]] = {}
        self._registered: bool = False

    @property
    def active_count(self) -> int:
        return len(self._connections)

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections[ws] = set()
        self._ensure_bus_subscription()
        logger.info("WebSocket client connected (%d active)", self.active_count)

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.pop(ws, None)
        logger.info("WebSocket client disconnected (%d active)", self.active_count)

    def set_topics(self, ws: WebSocket, topics: set[str]) -> None:
        if ws in self._connections:
            self._connections[ws] = topics

    async def broadcast(self, event: MESEvent) -> None:
        """Send event to all connected clients whose filters match."""
        payload = event.model_dump(mode="json")
        dead: list[WebSocket] = []
        for ws, topics in self._connections.items():
            if topics and not self._matches_any(topics, event.event_type):
                continue
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.pop(ws, None)

    def _ensure_bus_subscription(self) -> None:
        """Subscribe to the event bus exactly once."""
        if not self._registered:
            event_bus.subscribe("*", self._on_event)
            self._registered = True

    async def _on_event(self, event: MESEvent) -> None:
        await self.broadcast(event)

    @staticmethod
    def _matches_any(patterns: set[str], event_type: str) -> bool:
        for p in patterns:
            if p == "*":
                return True
            parts = p.split(".")
            event_parts = event_type.split(".")
            if parts[-1] == "*":
                prefix = parts[:-1]
                if len(event_parts) >= len(prefix) and event_parts[: len(prefix)] == prefix:
                    return True
            elif fnmatch.fnmatch(event_type, p):
                return True
        return False


_manager = _ConnectionManager()


def get_connection_manager() -> _ConnectionManager:
    """Return the module-level connection manager (for health/status)."""
    return _manager


# ── WebSocket Endpoint ───────────────────────────────────────────────


@router.websocket("/api/v1/events/ws")
async def event_stream(ws: WebSocket) -> None:
    """
    WebSocket endpoint for real-time MES event streaming.

    After connecting, clients may send:
        {"action": "subscribe", "topics": ["wip.*", "dispatch.*"]}
    to filter events.  Without a subscribe message, all events are forwarded.

    The server sends MESEvent JSON payloads whenever an event is published
    on the in-process event bus.
    """
    await _manager.connect(ws)
    try:
        while True:
            data: dict[str, Any] = await ws.receive_json()
            action = data.get("action")
            if action == "subscribe":
                topics = set(data.get("topics", []))
                _manager.set_topics(ws, topics)
                await ws.send_json({"status": "subscribed", "topics": list(topics)})
            elif action == "ping":
                await ws.send_json({"status": "pong"})
    except WebSocketDisconnect:
        _manager.disconnect(ws)
    except Exception:
        _manager.disconnect(ws)
