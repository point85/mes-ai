"""
STOMP JMS Adapter: High-level messaging adapter.

Provides a bidirectional bridge between:
- Inbound: broker queues/topics → MES internal event bus
- Outbound: MES event bus → broker destinations

Inbound messages are expected to be JSON with at least an 'event_type' field.
Outbound messages are serialized MESEvent payloads published as JSON.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from mes.adapters.equipment.dtos import EquipmentState, SubscriptionHandle, TagInfo, TagValue
from mes.adapters.equipment.exceptions import TagNotFoundError
from mes.adapters.equipment.interfaces import EquipmentAdapter
from mes.framework.events.bus import EventBus
from mes.framework.events.schema import MESEvent

from .client import STOMPClient
from .config import STOMPSettings

logger = logging.getLogger("mes.adapters.messaging.stomp")

_STATE_DISPATCH_MAP: dict[str, str] = {
    "running": "busy",
    "execute": "busy",
    "idle": "available",
    "stopped": "available",
    "fault": "unavailable_unplanned",
    "faulted": "unavailable_unplanned",
    "error": "unavailable_unplanned",
    "maintenance": "unavailable_planned",
    "setup": "unavailable_planned",
    "changeover": "unavailable_planned",
}

_STATE_OEE_MAP: dict[str, str] = {
    "running": "uptime_value_add",
    "execute": "uptime_value_add",
    "idle": "uptime_non_value",
    "stopped": "downtime_planned",
    "fault": "downtime_unplanned",
    "faulted": "downtime_unplanned",
    "error": "downtime_unplanned",
    "maintenance": "downtime_planned",
    "setup": "uptime_non_value",
    "changeover": "uptime_non_value",
}


class STOMPMessagingAdapter:
    """
    Bidirectional STOMP↔MES event bridge.

    Inbound flow:
        broker destination → STOMPClient → on_broker_message → EventBus.publish()

    Outbound flow:
        EventBus → on_mes_event → STOMPClient.send() → broker destination
    """

    def __init__(
        self,
        settings: STOMPSettings | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._settings = settings or STOMPSettings()
        self._event_bus = event_bus
        self._client = STOMPClient(
            self._settings,
            on_message=self._on_broker_message,
            on_error=self._on_broker_error,
        )
        self._subscription_ids: list[str] = []
        self._connected = False

    # ── Lifecycle ──────────────────────────────────────────────────

    async def connect(self) -> None:
        """Connect to broker, subscribe to inbound destinations and MES events."""
        try:
            await self._client.connect()
        except Exception:
            logger.warning(
                "STOMP broker not reachable at %s:%d — plugin will remain inactive. "
                "Disable the stomp-jms plugin or start a broker, then restart.",
                self._settings.STOMP_BROKER_HOST,
                self._settings.STOMP_BROKER_PORT,
            )
            return
        self._connected = True

        # Subscribe to inbound broker destinations
        inbound = self._parse_list(self._settings.STOMP_INBOUND_SUBSCRIPTIONS)
        for dest in inbound:
            sub_id = self._client.subscribe(dest)
            self._subscription_ids.append(sub_id)

        # Subscribe to MES event bus for outbound forwarding
        if self._event_bus:
            event_topics = self._parse_list(self._settings.STOMP_EVENT_SUBSCRIPTIONS)
            for topic in event_topics:
                self._event_bus.subscribe(topic, self._on_mes_event)
            logger.info(
                "STOMP outbound bridge active for MES topics: %s", event_topics,
            )

    async def disconnect(self) -> None:
        """Unsubscribe and disconnect from broker."""
        for sub_id in self._subscription_ids:
            self._client.unsubscribe(sub_id)
        self._subscription_ids.clear()

        # Unsubscribe from event bus
        if self._event_bus:
            event_topics = self._parse_list(self._settings.STOMP_EVENT_SUBSCRIPTIONS)
            for topic in event_topics:
                self._event_bus.unsubscribe(topic, self._on_mes_event)

        await self._client.disconnect()
        self._connected = False

    async def health_check(self) -> bool:
        """Check if the broker connection is healthy."""
        return await self._client.health_check()

    # ── Inbound: broker → MES ─────────────────────────────────────

    async def _on_broker_message(
        self,
        destination: str,
        headers: dict[str, str],
        body: str,
    ) -> None:
        """
        Handle an incoming message from the broker.

        Expects JSON body with at least 'event_type'. Optional fields:
        'source', 'payload', 'correlation_id'.
        """
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            logger.error(
                "Invalid JSON from %s: %s", destination, body[:200],
            )
            return

        handled = False
        if isinstance(data, dict):
            handled = await self._handle_inbound_payload(destination, headers, data)

        if not isinstance(data, dict):
            if not handled:
                logger.warning("Message from %s is not a JSON object", destination)
            return

        event_type = data.get("event_type")
        if not event_type:
            if not handled:
                logger.warning(
                    "Message from %s missing 'event_type', skipping: %s",
                    destination,
                    body[:200],
                )
            return

        if not self._event_bus:
            logger.warning("Received broker message but no event bus configured")
            return

        event = MESEvent(
            event_type=event_type,
            source=data.get("source", f"stomp:{destination}"),
            payload=data.get("payload", {}),
            correlation_id=data.get("correlation_id", ""),
        )
        await self._event_bus.publish(event)
        logger.debug(
            "Inbound STOMP → MES event: %s from %s", event_type, destination,
        )

    async def _handle_inbound_payload(
        self,
        destination: str,
        headers: dict[str, str],
        data: dict[str, Any],
    ) -> bool:
        """Hook for subclasses that consume non-event STOMP messages."""
        del destination, headers, data
        return False

    async def _on_broker_error(
        self,
        headers: dict[str, str],
        body: str,
    ) -> None:
        """Log broker error frames."""
        logger.error("STOMP broker error: %s — %s", headers, body[:500])

    # ── Outbound: MES → broker ────────────────────────────────────

    async def _on_mes_event(self, event: MESEvent) -> None:
        """
        Forward an MES event to the broker outbound destination.

        Serializes the event as JSON and sends it to the configured
        outbound destination (queue or topic).
        """
        if not self._connected or not self._client.is_connected:
            logger.warning(
                "Cannot forward event %s — STOMP not connected", event.event_type,
            )
            return

        message = json.dumps(
            {
                "event_id": event.event_id,
                "event_type": event.event_type,
                "timestamp": event.timestamp.isoformat(),
                "source": event.source,
                "payload": event.payload,
                "correlation_id": event.correlation_id,
            },
        )
        self._client.send(
            destination=self._settings.STOMP_OUTBOUND_DESTINATION,
            body=message,
            headers={"mes-event-type": event.event_type},
        )
        logger.debug(
            "Outbound MES → STOMP: %s → %s",
            event.event_type,
            self._settings.STOMP_OUTBOUND_DESTINATION,
        )

    # ── Public send API ───────────────────────────────────────────

    def send(
        self,
        destination: str,
        body: str,
        content_type: str = "application/json",
        headers: dict[str, str] | None = None,
    ) -> None:
        """
        Send a message to an arbitrary broker destination.

        This is the programmatic API for plugin consumers who want to
        publish messages to specific queues/topics beyond the automatic
        event bridge.
        """
        self._client.send(
            destination=destination,
            body=body,
            content_type=content_type,
            headers=headers,
        )

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _parse_list(value: str) -> list[str]:
        """Parse a comma-separated string into a list of trimmed values."""
        return [v.strip() for v in value.split(",") if v.strip()]


class STOMPEquipmentAdapter(STOMPMessagingAdapter, EquipmentAdapter):
    """STOMP-backed equipment adapter using JSON messages and a local tag cache."""

    def __init__(
        self,
        settings: STOMPSettings | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        super().__init__(settings=settings, event_bus=event_bus)
        self._tag_cache: dict[str, TagValue] = {}
        self._subscriptions: dict[str, tuple[SubscriptionHandle, str | None]] = {}
        self._callbacks: dict[str, Callable[[TagValue], Any]] = {}

    async def read_tag(self, tag_name: str) -> TagValue:
        value = self._tag_cache.get(tag_name)
        if value is None:
            raise TagNotFoundError(tag_name=tag_name)
        return value

    async def write_tag(self, tag_name: str, value: Any) -> None:
        destination = self._tag_to_destination(tag_name)
        payload = json.dumps({"tag_name": tag_name, "value": value})
        self.send(destination=destination, body=payload)

    async def subscribe_tag(
        self,
        tag_name: str,
        callback: Callable[[TagValue], Any],
        interval_ms: int = 1000,
    ) -> SubscriptionHandle:
        del interval_ms
        destination = self._tag_to_destination(tag_name)
        sub_id: str | None = None
        if self._client.is_connected:
            sub_id = self._client.subscribe(destination)
        handle = SubscriptionHandle(tag_name=tag_name, topic=destination, active=True)
        self._callbacks[tag_name] = callback
        self._subscriptions[handle.handle_id] = (handle, sub_id)
        return handle

    async def unsubscribe(self, handle: SubscriptionHandle) -> None:
        handle.active = False
        stored = self._subscriptions.pop(handle.handle_id, None)
        self._callbacks.pop(handle.tag_name, None)
        if stored and stored[1]:
            self._client.unsubscribe(stored[1])

    async def get_equipment_state(self) -> EquipmentState:
        state_value = self._tag_cache.get(self._settings.STOMP_STATE_TAG)
        equipment_value = self._tag_cache.get(self._settings.STOMP_EQUIPMENT_ID_TAG)
        state = str(state_value.value).lower() if state_value else "unknown"
        return EquipmentState(
            equipment_id=str(equipment_value.value) if equipment_value else "",
            state=state,
            dispatch_category=_STATE_DISPATCH_MAP.get(state, "available"),
            oee_bucket=_STATE_OEE_MAP.get(state, "uptime_non_value"),
        )

    async def browse_tags(self, root: str | None = None) -> list[TagInfo]:
        return [
            TagInfo(
                tag_name=tag_name,
                data_type=value.data_type,
                access="readwrite",
                description=f"STOMP tag cached from {value.tag_name}",
            )
            for tag_name, value in sorted(self._tag_cache.items())
            if root is None or tag_name.startswith(root)
        ]

    async def _handle_inbound_payload(
        self,
        destination: str,
        headers: dict[str, str],
        data: dict[str, Any],
    ) -> bool:
        del headers
        tag_name = data.get("tag_name") if isinstance(data.get("tag_name"), str) else self._destination_to_tag(destination)
        if not tag_name or "value" not in data:
            return False

        value = data.get("value")
        data_type = str(data.get("data_type") or self._infer_data_type(value))
        quality = str(data.get("quality") or "good")
        tag_value = TagValue(tag_name=tag_name, value=value, quality=quality, data_type=data_type)
        self._tag_cache[tag_name] = tag_value

        callback = self._callbacks.get(tag_name)
        if callback:
            result = callback(tag_value)
            if hasattr(result, "__await__"):
                await result
        return True

    def _tag_to_destination(self, tag_name: str) -> str:
        if tag_name.startswith("/"):
            return tag_name
        return f"{self._settings.STOMP_TOPIC_PREFIX.rstrip('/')}/{tag_name}"

    def _destination_to_tag(self, destination: str) -> str | None:
        prefix = self._settings.STOMP_TOPIC_PREFIX.rstrip("/")
        if destination.startswith(prefix + "/"):
            return destination[len(prefix) + 1 :]
        return None

    @staticmethod
    def _infer_data_type(value: Any) -> str:
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        if isinstance(value, list):
            return "array"
        if isinstance(value, dict):
            return "object"
        return "string"
