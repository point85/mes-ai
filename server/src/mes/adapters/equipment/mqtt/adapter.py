"""
MQTT Equipment Adapter: Concrete EquipmentAdapter implementation.

Maps the abstract EquipmentAdapter interface to MQTT pub/sub operations
via the MQTTClient wrapper.

Configuration:
    MES_EQUIP_ADAPTER=mqtt
    MES_EQUIP_MQTT_BROKER_HOST=mqtt-broker.local
    MES_EQUIP_MQTT_BROKER_PORT=1883
    MES_EQUIP_MQTT_TOPIC_PREFIX=mes/equipment

See MQTTSettings for full configuration reference.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from mes.adapters.equipment.dtos import (
    EquipmentState,
    SubscriptionHandle,
    TagInfo,
    TagValue,
)
from mes.adapters.equipment.interfaces import EquipmentAdapter

from .client import MQTTClient
from .config import MQTTSettings

logger = logging.getLogger("mes.adapters.equipment.mqtt")

# Equipment state → dispatch category mapping
_STATE_DISPATCH_MAP: dict[str, str] = {
    "running": "busy",
    "idle": "available",
    "stopped": "available",
    "fault": "unavailable_unplanned",
    "faulted": "unavailable_unplanned",
    "error": "unavailable_unplanned",
    "maintenance": "unavailable_planned",
    "setup": "unavailable_planned",
    "changeover": "unavailable_planned",
}

# Equipment state → OEE bucket mapping
_STATE_OEE_MAP: dict[str, str] = {
    "running": "uptime_value_add",
    "idle": "uptime_non_value",
    "stopped": "downtime_planned",
    "fault": "downtime_unplanned",
    "faulted": "downtime_unplanned",
    "error": "downtime_unplanned",
    "maintenance": "downtime_planned",
    "setup": "uptime_non_value",
    "changeover": "uptime_non_value",
}


class MQTTEquipmentAdapter(EquipmentAdapter):
    """
    MQTT equipment adapter.

    Connects to an MQTT broker and provides tag-based read/write/subscribe
    operations by mapping tags to MQTT topics under a configurable prefix.

    Tags are cached locally from incoming MQTT messages, so read_tag()
    returns the most recent value without an additional network roundtrip.
    """

    def __init__(self, mqtt_settings: MQTTSettings | None = None) -> None:
        self._settings = mqtt_settings or MQTTSettings()
        self._client = MQTTClient(self._settings)
        self._subscriptions: dict[str, SubscriptionHandle] = {}

    @property
    def equipment_id(self) -> str:
        return self._settings.EQUIP_MQTT_EQUIPMENT_ID

    # ── BaseAdapter lifecycle ──

    async def connect(self) -> None:
        await self._client.connect()

    async def disconnect(self) -> None:
        self._subscriptions.clear()
        await self._client.disconnect()

    async def health_check(self) -> bool:
        return await self._client.health_check()

    # ── EquipmentAdapter interface ──

    async def read_tag(self, tag_name: str) -> TagValue:
        value, quality, data_type = await self._client.read_tag(tag_name)
        return TagValue(
            tag_name=tag_name, value=value, quality=quality, data_type=data_type,
        )

    async def write_tag(self, tag_name: str, value: Any) -> None:
        await self._client.write_tag(tag_name, value)

    async def subscribe_tag(
        self,
        tag_name: str,
        callback: Callable[[TagValue], Any],
        interval_ms: int = 1000,
    ) -> SubscriptionHandle:
        handle_id = await self._client.subscribe_tag(tag_name, callback, interval_ms)
        handle = SubscriptionHandle(handle_id=handle_id, tag_name=tag_name, active=True)
        self._subscriptions[handle_id] = handle
        return handle

    async def unsubscribe(self, handle: SubscriptionHandle) -> None:
        handle.active = False
        self._subscriptions.pop(handle.handle_id, None)
        await self._client.unsubscribe_tag(handle.tag_name)

    async def get_equipment_state(self) -> EquipmentState:
        state_value = await self._client.read_state_topic()
        state = (state_value or "unknown").lower()
        dispatch_category = _STATE_DISPATCH_MAP.get(state, "available")
        oee_bucket = _STATE_OEE_MAP.get(state, "uptime_non_value")
        return EquipmentState(
            equipment_id=self.equipment_id,
            state=state,
            dispatch_category=dispatch_category,
            oee_bucket=oee_bucket,
        )

    async def browse_tags(self, root: str | None = None) -> list[TagInfo]:
        raw_tags = await self._client.browse()
        return [
            TagInfo(
                tag_name=t["tag_name"],
                data_type=t["data_type"],
                access=t.get("access", "readwrite"),
                description=t.get("description", ""),
            )
            for t in raw_tags
        ]
