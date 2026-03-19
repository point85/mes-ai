"""
MQTT Equipment Adapter: aiomqtt client wrapper.

Manages the MQTT broker connection, topic subscriptions, local tag cache,
publish/subscribe operations, and TLS/auth configuration.

MQTT maps equipment tags to topics:
    {prefix}/{tag_name}  →  e.g. mes/equipment/temperature

The client maintains a local cache of the latest value received on each
topic, so read_tag() returns instantly from cache.  On connect the client
subscribes to {prefix}/# to discover all published tags.

Requires the `aiomqtt` package (optional dependency):
    pip install aiomqtt
"""

from __future__ import annotations

import asyncio
import json
import logging
import ssl
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from mes.adapters.equipment.exceptions import (
    CommunicationTimeoutError,
    EquipmentConnectionError,
    TagNotFoundError,
)

from .config import MQTTSettings

logger = logging.getLogger("mes.adapters.equipment.mqtt")


class MQTTClient:
    """
    Async wrapper around aiomqtt.Client.

    Handles broker connection, TLS, auth, topic subscriptions,
    local tag-value cache, and publish/subscribe operations.
    """

    def __init__(self, mqtt_settings: MQTTSettings | None = None) -> None:
        self._settings = mqtt_settings or MQTTSettings()
        self._client: Any = None  # aiomqtt.Client instance
        self._connected = False
        self._tag_cache: dict[str, _CachedValue] = {}
        self._callbacks: dict[str, Callable] = {}  # topic → user callback
        self._listener_task: asyncio.Task | None = None

    # ── Lifecycle ──

    async def connect(self) -> None:
        """Connect to the MQTT broker and start the message listener."""
        try:
            from aiomqtt import Client as MqttClient  # type: ignore[import-not-found]
        except ImportError as exc:
            raise EquipmentConnectionError(
                message="aiomqtt package not installed. Install with: pip install aiomqtt"
            ) from exc

        s = self._settings
        kwargs: dict[str, Any] = {
            "hostname": s.EQUIP_MQTT_BROKER_HOST,
            "port": s.EQUIP_MQTT_BROKER_PORT,
            "identifier": s.EQUIP_MQTT_CLIENT_ID,
            "keepalive": s.EQUIP_MQTT_KEEPALIVE,
            "timeout": s.EQUIP_MQTT_TIMEOUT,
        }

        if s.EQUIP_MQTT_USERNAME:
            kwargs["username"] = s.EQUIP_MQTT_USERNAME
            kwargs["password"] = s.EQUIP_MQTT_PASSWORD or None

        if s.EQUIP_MQTT_USE_TLS:
            tls_ctx = self._build_tls_context()
            kwargs["tls_context"] = tls_ctx

        try:
            self._client = MqttClient(**kwargs)
            await self._client.__aenter__()
            self._connected = True

            # Subscribe to wildcard topic to discover tags / build cache
            prefix = s.EQUIP_MQTT_TOPIC_PREFIX
            wildcard = f"{prefix}/#"
            await self._client.subscribe(wildcard, qos=s.EQUIP_MQTT_QOS)

            # Also subscribe to state topic if configured
            if s.EQUIP_MQTT_STATE_TOPIC and not s.EQUIP_MQTT_STATE_TOPIC.startswith(prefix):
                await self._client.subscribe(s.EQUIP_MQTT_STATE_TOPIC, qos=s.EQUIP_MQTT_QOS)

            # Start background listener
            self._listener_task = asyncio.create_task(self._listen_loop())

            logger.info(
                "MQTT connected to %s:%d (prefix=%s)",
                s.EQUIP_MQTT_BROKER_HOST, s.EQUIP_MQTT_BROKER_PORT, prefix,
            )
        except EquipmentConnectionError:
            raise
        except Exception as exc:
            self._connected = False
            raise EquipmentConnectionError(
                message=f"MQTT connection failed: {exc}"
            ) from exc

    async def disconnect(self) -> None:
        """Disconnect from the MQTT broker and stop the listener."""
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None

        if self._client and self._connected:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception:
                logger.debug("MQTT disconnect warning (non-fatal)")

        self._connected = False
        self._tag_cache.clear()
        self._callbacks.clear()
        logger.info("MQTT disconnected")

    async def health_check(self) -> bool:
        """Check if the MQTT client is connected."""
        return self._connected and self._client is not None

    # ── Tag Operations ──

    async def read_tag(self, tag_name: str) -> tuple[Any, str, str]:
        """
        Read the latest cached value for a tag.

        Returns (value, quality, data_type).
        Raises TagNotFoundError if no value has been received for this tag.
        """
        cached = self._tag_cache.get(tag_name)
        if cached is None:
            raise TagNotFoundError(tag_name=tag_name)
        return cached.value, cached.quality, cached.data_type

    async def write_tag(self, tag_name: str, value: Any) -> None:
        """Publish a value to the topic corresponding to tag_name."""
        if not self._connected or not self._client:
            raise EquipmentConnectionError(message="MQTT client not connected")

        topic = self._tag_to_topic(tag_name)
        payload = self._encode_payload(value)

        try:
            await asyncio.wait_for(
                self._client.publish(
                    topic, payload=payload,
                    qos=self._settings.EQUIP_MQTT_QOS, retain=True,
                ),
                timeout=self._settings.EQUIP_MQTT_TIMEOUT,
            )
        except asyncio.TimeoutError as exc:
            raise CommunicationTimeoutError(
                message=f"Timeout publishing to '{tag_name}'"
            ) from exc
        except Exception as exc:
            raise CommunicationTimeoutError(
                message=f"Error publishing to '{tag_name}': {exc}"
            ) from exc

    async def subscribe_tag(self, tag_name: str, callback: Callable, interval_ms: int) -> str:
        """
        Register a callback for value changes on a tag's topic.

        The callback is invoked whenever a new message arrives on the topic.
        interval_ms is accepted for interface compatibility but MQTT delivers
        messages as they arrive (event-driven, not polled).

        Returns tag_name as the handle_id.
        """
        self._callbacks[tag_name] = callback
        logger.debug(
            "MQTT subscription registered for '%s' (interval_ms=%d ignored, event-driven)",
            tag_name, interval_ms,
        )
        return tag_name

    async def unsubscribe_tag(self, tag_name: str) -> None:
        """Remove the callback for a tag."""
        self._callbacks.pop(tag_name, None)

    async def browse(self) -> list[dict[str, Any]]:
        """Return metadata for all tags discovered via the wildcard subscription."""
        results = []
        for tag_name, cached in self._tag_cache.items():
            results.append({
                "tag_name": tag_name,
                "data_type": cached.data_type,
                "access": "readwrite",
                "description": f"MQTT topic: {self._tag_to_topic(tag_name)}",
            })
        return results

    async def read_state_topic(self) -> str | None:
        """Read the equipment state from the configured state topic."""
        state_topic = self._settings.EQUIP_MQTT_STATE_TOPIC
        if not state_topic:
            return None
        # The state topic may or may not be under the prefix
        tag_name = self._topic_to_tag(state_topic)
        cached = self._tag_cache.get(tag_name)
        if cached is None:
            return None
        return str(cached.value) if cached.value is not None else None

    # ── Internal helpers ──

    def _tag_to_topic(self, tag_name: str) -> str:
        """Convert a tag name to a full MQTT topic."""
        prefix = self._settings.EQUIP_MQTT_TOPIC_PREFIX
        # If tag_name already looks like a full topic, use as-is
        if tag_name.startswith(prefix + "/"):
            return tag_name
        return f"{prefix}/{tag_name}"

    def _topic_to_tag(self, topic: str) -> str:
        """Extract the tag name from a full MQTT topic."""
        prefix = self._settings.EQUIP_MQTT_TOPIC_PREFIX
        if topic.startswith(prefix + "/"):
            return topic[len(prefix) + 1 :]
        return topic

    @staticmethod
    def _encode_payload(value: Any) -> bytes:
        """Encode a Python value to MQTT payload bytes."""
        if isinstance(value, bytes):
            return value
        if isinstance(value, (dict, list)):
            return json.dumps(value).encode("utf-8")
        return str(value).encode("utf-8")

    @staticmethod
    def _decode_payload(payload: bytes) -> Any:
        """Decode MQTT payload bytes to a Python value."""
        text = payload.decode("utf-8", errors="replace")
        # Try JSON first (for dicts, lists, and typed scalars)
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            pass
        # Try numeric conversion
        try:
            if "." in text:
                return float(text)
            return int(text)
        except ValueError:
            pass
        # Boolean
        if text.lower() in ("true", "false"):
            return text.lower() == "true"
        return text

    def _build_tls_context(self) -> ssl.SSLContext:
        """Build an SSL context for TLS-secured MQTT connections."""
        ctx = ssl.create_default_context()
        s = self._settings
        if s.EQUIP_MQTT_TLS_CA_CERT:
            ctx.load_verify_locations(s.EQUIP_MQTT_TLS_CA_CERT)
        if s.EQUIP_MQTT_TLS_CLIENT_CERT and s.EQUIP_MQTT_TLS_CLIENT_KEY:
            ctx.load_cert_chain(s.EQUIP_MQTT_TLS_CLIENT_CERT, s.EQUIP_MQTT_TLS_CLIENT_KEY)
        return ctx

    async def _listen_loop(self) -> None:
        """Background task: receive messages and dispatch to callbacks."""
        try:
            async for message in self._client.messages:
                topic_str = str(message.topic)
                tag_name = self._topic_to_tag(topic_str)
                value = self._decode_payload(message.payload)
                data_type = _infer_python_type(value)

                # Update cache
                self._tag_cache[tag_name] = _CachedValue(
                    value=value, quality="good", data_type=data_type,
                    timestamp=datetime.now(timezone.utc),
                )

                # Dispatch callback
                callback = self._callbacks.get(tag_name)
                if callback:
                    from mes.adapters.equipment.dtos import TagValue

                    tag_value = TagValue(
                        tag_name=tag_name, value=value, quality="good",
                        timestamp=datetime.now(timezone.utc), data_type=data_type,
                    )
                    try:
                        result = callback(tag_value)
                        if asyncio.iscoroutine(result):
                            asyncio.ensure_future(result)
                    except Exception:
                        logger.exception("MQTT callback error for topic %s", topic_str)
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("MQTT listener loop error")
            self._connected = False


class _CachedValue:
    """Lightweight container for a cached tag value."""

    __slots__ = ("value", "quality", "data_type", "timestamp")

    def __init__(self, value: Any, quality: str, data_type: str, timestamp: datetime) -> None:
        self.value = value
        self.quality = quality
        self.data_type = data_type
        self.timestamp = timestamp


def _infer_python_type(value: Any) -> str:
    """Infer MES data_type string from a Python value."""
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, (list, tuple)):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"
