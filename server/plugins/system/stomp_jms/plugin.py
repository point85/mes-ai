"""
STOMP JMS Messaging Plugin.

Wraps the STOMPMessagingAdapter as a plugin managed by the MES plugin
framework. Provides bidirectional messaging between the MES event bus
and a STOMP-compatible JMS message broker.

Compatible brokers:
- Apache ActiveMQ / Artemis (port 61613)
- RabbitMQ with STOMP plugin (port 61613)
- Any STOMP 1.2 compatible broker
"""

from __future__ import annotations

from typing import Any

from mes.framework.plugin import MESPlugin


class STOMPJMSPlugin(MESPlugin):
    """Plugin wrapper for the STOMP JMS messaging adapter."""

    def __init__(self) -> None:
        self._adapter: Any = None

    async def initialize(self, config: dict[str, Any]) -> None:
        from mes.adapters.messaging.stomp.adapter import STOMPMessagingAdapter
        from mes.adapters.messaging.stomp.config import STOMPSettings

        # Map plugin config params → STOMPSettings env-style keys
        settings_kwargs: dict[str, Any] = {}
        param_map = {
            "broker_host": "STOMP_BROKER_HOST",
            "broker_port": "STOMP_BROKER_PORT",
            "username": "STOMP_USERNAME",
            "password": "STOMP_PASSWORD",
            "vhost": "STOMP_VHOST",
            "use_ssl": "STOMP_USE_SSL",
            "heartbeat_send_ms": "STOMP_HEARTBEAT_SEND_MS",
            "heartbeat_recv_ms": "STOMP_HEARTBEAT_RECV_MS",
            "reconnect_attempts": "STOMP_RECONNECT_ATTEMPTS",
            "reconnect_delay_sec": "STOMP_RECONNECT_DELAY_SEC",
            "inbound_subscriptions": "STOMP_INBOUND_SUBSCRIPTIONS",
            "outbound_destination": "STOMP_OUTBOUND_DESTINATION",
            "event_subscriptions": "STOMP_EVENT_SUBSCRIPTIONS",
        }
        for param_name, settings_key in param_map.items():
            if param_name in config and config[param_name] is not None:
                settings_kwargs[settings_key] = config[param_name]

        settings = STOMPSettings(_env_file=None, **settings_kwargs)

        # Event bus is injected by the plugin manager if available
        event_bus = config.get("_event_bus")

        self._adapter = STOMPMessagingAdapter(
            settings=settings,
            event_bus=event_bus,
        )

    async def start(self) -> None:
        if self._adapter:
            await self._adapter.connect()

    async def stop(self) -> None:
        if self._adapter:
            await self._adapter.disconnect()

    async def health_check(self) -> bool:
        return await self._adapter.health_check() if self._adapter else False

    def get_adapter(self) -> Any:
        return self._adapter
