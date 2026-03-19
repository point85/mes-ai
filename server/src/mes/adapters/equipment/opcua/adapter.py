"""
OPC-UA Equipment Adapter: Concrete EquipmentAdapter implementation.

Maps the abstract EquipmentAdapter interface to OPC-UA operations
via the OPCUAClient wrapper.

Configuration:
    MES_EQUIP_ADAPTER=opcua
    MES_EQUIP_OPCUA_URL=opc.tcp://plc-01:4840

See OPCUASettings for full configuration reference.
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

from .client import OPCUAClient
from .config import OPCUASettings

logger = logging.getLogger("mes.adapters.equipment.opcua")

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


class OPCUAEquipmentAdapter(EquipmentAdapter):
    """
    OPC-UA equipment adapter.

    Connects to a single OPC-UA server endpoint and provides
    tag-based read/write/subscribe operations following the
    EquipmentAdapter interface contract.

    Usage:
        adapter = OPCUAEquipmentAdapter()
        await adapter.connect()
        value = await adapter.read_tag("Temperature")
        await adapter.disconnect()
    """

    def __init__(self, opcua_settings: OPCUASettings | None = None) -> None:
        self._settings = opcua_settings or OPCUASettings()
        self._client = OPCUAClient(self._settings)
        self._subscriptions: dict[str, SubscriptionHandle] = {}

    @property
    def equipment_id(self) -> str:
        return self._settings.EQUIP_OPCUA_EQUIPMENT_ID

    # ──────────────────────────────────────────────────────────────
    # BaseAdapter lifecycle
    # ──────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Connect to the OPC-UA server."""
        await self._client.connect()

    async def disconnect(self) -> None:
        """Disconnect from the OPC-UA server."""
        self._subscriptions.clear()
        await self._client.disconnect()

    async def health_check(self) -> bool:
        """Check OPC-UA session health."""
        return await self._client.health_check()

    # ──────────────────────────────────────────────────────────────
    # EquipmentAdapter interface
    # ──────────────────────────────────────────────────────────────

    async def read_tag(self, tag_name: str) -> TagValue:
        """Read a tag value from the OPC-UA server."""
        value, quality, data_type = await self._client.read_tag(tag_name)
        return TagValue(
            tag_name=tag_name,
            value=value,
            quality=quality,
            data_type=data_type,
        )

    async def write_tag(self, tag_name: str, value: Any) -> None:
        """Write a value to an OPC-UA tag."""
        await self._client.write_tag(tag_name, value)

    async def subscribe_tag(
        self,
        tag_name: str,
        callback: Callable[[TagValue], Any],
        interval_ms: int = 1000,
    ) -> SubscriptionHandle:
        """Subscribe to data changes on an OPC-UA tag."""
        effective_interval = interval_ms or self._settings.EQUIP_OPCUA_SUB_INTERVAL_MS

        handle_id = await self._client.subscribe_tag(tag_name, callback, effective_interval)

        handle = SubscriptionHandle(
            handle_id=handle_id,
            tag_name=tag_name,
            active=True,
        )
        self._subscriptions[handle_id] = handle
        return handle

    async def unsubscribe(self, handle: SubscriptionHandle) -> None:
        """Cancel a tag subscription."""
        handle.active = False
        self._subscriptions.pop(handle.handle_id, None)
        await self._client.unsubscribe_tag(handle.tag_name)

    async def get_equipment_state(self) -> EquipmentState:
        """
        Read equipment state from the configured state tag.

        If no state tag is configured, returns "unknown" state.
        """
        state_value = await self._client.read_state_tag()
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
        """Browse the OPC-UA address space for available tags."""
        raw_tags = await self._client.browse(root)
        return [
            TagInfo(
                tag_name=t["tag_name"],
                data_type=t["data_type"],
                access=t.get("access", "readwrite"),
                description=t.get("description", ""),
            )
            for t in raw_tags
        ]
