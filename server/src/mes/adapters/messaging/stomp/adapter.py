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
from typing import Any

from mes.framework.events.bus import EventBus
from mes.framework.events.schema import MESEvent

from .client import STOMPClient
from .config import STOMPSettings

logger = logging.getLogger("mes.adapters.messaging.stomp")


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
        if not self._event_bus:
            logger.warning("Received broker message but no event bus configured")
            return

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            logger.error(
                "Invalid JSON from %s: %s", destination, body[:200],
            )
            return

        event_type = data.get("event_type")
        if not event_type:
            logger.warning(
                "Message from %s missing 'event_type', skipping: %s",
                destination,
                body[:200],
            )
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
        self._client.send(destination, body, content_type, headers)

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _parse_list(value: str) -> list[str]:
        """Parse a comma-separated string into a list of trimmed values."""
        return [v.strip() for v in value.split(",") if v.strip()]
