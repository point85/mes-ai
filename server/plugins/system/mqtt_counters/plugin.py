"""
MQTT Production Counter Plugin.

Subscribes to an MQTT topic pattern where equipment publishes production
count events.  Each incoming message contains deltas (good, reject,
rework) which are forwarded to ProductionCounterService.increment_counter().

Default topic layout:
    mes/equipment/{equipment_id}/counters

Expected JSON payload:
    {
        "good_delta": <int>,        # required, >= 0
        "reject_delta": <int>,      # optional, default 0
        "rework_delta": <int>,      # optional, default 0
        "order_id": "<uuid>"        # optional
    }

The equipment_id is extracted from the topic path, so the publishing
device only needs to know its own ID (embedded in the topic).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any
from uuid import UUID

from mes.framework.plugin.base import MESPlugin

logger = logging.getLogger("mes.plugins.mqtt_counters")

SOURCE_ID = "mqtt-counters"


class MQTTCountersPlugin(MESPlugin):
    """
    Subscribes to MQTT counter topics and forwards deltas to the
    production counter service.

    Configuration (via manifest parameters):
        broker_host:     MQTT broker hostname (default "localhost")
        broker_port:     MQTT broker port     (default 1883)
        topic_pattern:   topic with '+' wildcard for equipment_id
        username/password: optional broker auth
        qos:             subscription QoS     (default 1)
    """

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}
        self._task: asyncio.Task[None] | None = None
        self._running = False

    async def initialize(self, config: dict[str, Any]) -> None:
        self._config = config
        logger.info(
            "MQTT counters plugin initialising (broker=%s:%s, topic=%s)",
            config.get("broker_host", "localhost"),
            config.get("broker_port", 1883),
            config.get("topic_pattern", "mes/equipment/+/counters"),
        )

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(
            self._subscribe_loop(), name="mqtt-counters-subscriber"
        )
        logger.info("MQTT counters plugin started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("MQTT counters plugin stopped")

    async def health_check(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    # ── MQTT subscription loop ────────────────────────────────────────

    async def _subscribe_loop(self) -> None:
        """
        Connect to the MQTT broker, subscribe to the counter topic,
        and process incoming messages indefinitely.
        """
        broker = self._config.get("broker_host", "localhost")
        port = int(self._config.get("broker_port", 1883))
        topic = self._config.get("topic_pattern", "mes/equipment/+/counters")
        username = self._config.get("username") or None
        password = self._config.get("password") or None
        qos = int(self._config.get("qos", 1))

        try:
            import aiomqtt
        except ImportError:
            logger.error(
                "aiomqtt not installed — cannot subscribe to MQTT. "
                "Install with: pip install mes-ai[mqtt]"
            )
            return

        while self._running:
            try:
                async with aiomqtt.Client(
                    hostname=broker,
                    port=port,
                    username=username,
                    password=password,
                ) as client:
                    await client.subscribe(topic, qos=qos)
                    logger.info("Subscribed to MQTT topic: %s", topic)

                    async for message in client.messages:
                        if not self._running:
                            break
                        try:
                            await self._handle_message(message)
                        except Exception as e:
                            logger.warning("Error handling MQTT message: %s", e)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    "MQTT connection error (broker=%s:%d): %s — reconnecting in 5s",
                    broker, port, e,
                )
                await asyncio.sleep(5)

    # ── Message handling ──────────────────────────────────────────────

    async def _handle_message(self, message: Any) -> None:
        """
        Parse an MQTT message, extract equipment_id from the topic,
        and forward the counter delta to ProductionCounterService.
        """
        topic_str = str(message.topic)
        equipment_id = self._extract_equipment_id(topic_str)
        if equipment_id is None:
            logger.warning("Could not extract equipment_id from topic: %s", topic_str)
            return

        payload = self._parse_payload(message.payload)
        if payload is None:
            return

        good_delta = max(0, int(payload.get("good_delta", 0)))
        reject_delta = max(0, int(payload.get("reject_delta", 0)))
        rework_delta = max(0, int(payload.get("rework_delta", 0)))
        order_id_str = payload.get("order_id")
        order_id = UUID(order_id_str) if order_id_str else None

        if good_delta == 0 and reject_delta == 0 and rework_delta == 0:
            return  # Nothing to process

        from mes.framework.db import async_session_factory
        from mes.core.performance.service import ProductionCounterService

        async with async_session_factory() as session:
            await ProductionCounterService.increment_counter(
                session,
                equipment_id=equipment_id,
                good_delta=good_delta,
                reject_delta=reject_delta,
                rework_delta=rework_delta,
                order_id=order_id,
                source_plugin=SOURCE_ID,
            )
            await session.commit()

        logger.debug(
            "Counter update: equip=%s good=+%d reject=+%d rework=+%d (MQTT)",
            equipment_id, good_delta, reject_delta, rework_delta,
        )

    @staticmethod
    def _extract_equipment_id(topic: str) -> UUID | None:
        """
        Extract equipment_id from the configured topic pattern.

        Supports the default pattern mes/equipment/{uuid}/counters.
        Returns None if the topic structure doesn't match or the extracted UUID is invalid.
        """
        parts = topic.split("/")
        if len(parts) != 4 or parts[3] != "counters":
            return None
        try:
            return UUID(parts[2])
        except ValueError:
            return None

    @staticmethod
    def _compile_topic_pattern(topic_pattern: str) -> re.Pattern[str]:
        escaped = re.escape(topic_pattern)
        if "{equipment_id}" in topic_pattern:
            escaped = escaped.replace(re.escape("{equipment_id}"), r"(?P<equipment_id>[^/]+)")
        else:
            escaped = escaped.replace(r"\+", r"(?P<equipment_id>[^/]+)", 1)
            escaped = escaped.replace(r"\+", r"[^/]+")
        escaped = escaped.replace(r"\#", r".*")
        return re.compile(escaped)

    @staticmethod
    def _parse_payload(raw: bytes | bytearray | str) -> dict[str, Any] | None:
        """Parse a JSON payload, returning None on failure."""
        try:
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8")
            data = json.loads(raw)
            if not isinstance(data, dict):
                logger.warning("MQTT payload is not a JSON object")
                return None
            return data
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning("Invalid MQTT payload: %s", e)
            return None
