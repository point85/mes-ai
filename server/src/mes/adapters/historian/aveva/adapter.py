"""
AVEVA Historian Adapter: Concrete EquipmentAdapter implementation.

Maps the abstract EquipmentAdapter interface to AVEVA Historian
v2 REST API operations via the AVEVAHistorianClient.

The Historian REST API is primarily read-only (no direct tag writes to
the underlying equipment).  ``write_tag`` raises ``NotImplementedError``
since the Historian stores historical data — equipment writes should
go through OPC-UA or MQTT adapters to the equipment directly.

Subscriptions are poll-based: a background task reads current values
at a configurable interval since the REST API has no push/WebSocket
capability.

Ref: https://docs.aveva.com/bundle/sp-historian/page/338478.html
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from mes.adapters.equipment.dtos import (
    EquipmentState,
    SubscriptionHandle,
    TagInfo,
    TagValue,
)
from mes.adapters.equipment.interfaces import EquipmentAdapter

from .client import AVEVAHistorianClient, _opc_quality_to_str
from .config import AVEVAHistorianSettings

logger = logging.getLogger("mes.adapters.historian.aveva")

# AVEVA TagType codes → canonical data type strings
_TAG_TYPE_MAP: dict[str, str] = {
    "Analog": "float",
    "Discrete": "bool",
    "String": "string",
    "Event": "string",
    "Summary": "float",
}

# Equipment state → dispatch category mapping
_STATE_DISPATCH_MAP: dict[str, str] = {
    "running": "busy",
    "execute": "busy",
    "idle": "available",
    "stopped": "available",
    "fault": "unavailable_unplanned",
    "faulted": "unavailable_unplanned",
    "error": "unavailable_unplanned",
    "aborted": "unavailable_unplanned",
    "maintenance": "unavailable_planned",
    "setup": "unavailable_planned",
    "changeover": "unavailable_planned",
}

# Equipment state → OEE bucket mapping
_STATE_OEE_MAP: dict[str, str] = {
    "running": "uptime_value_add",
    "execute": "uptime_value_add",
    "idle": "uptime_non_value",
    "stopped": "downtime_planned",
    "fault": "downtime_unplanned",
    "faulted": "downtime_unplanned",
    "error": "downtime_unplanned",
    "aborted": "downtime_unplanned",
    "maintenance": "downtime_planned",
    "setup": "uptime_non_value",
    "changeover": "uptime_non_value",
}


class _PollSubscription:
    """Internal: tracks a polling subscription for one tag."""

    __slots__ = ("fqn", "callback", "interval_sec", "handle", "last_value")

    def __init__(
        self,
        fqn: str,
        callback: Callable[[TagValue], Any],
        interval_sec: float,
        handle: SubscriptionHandle,
    ) -> None:
        self.fqn = fqn
        self.callback = callback
        self.interval_sec = interval_sec
        self.handle = handle
        self.last_value: Any = None


class AVEVAHistorianAdapter(EquipmentAdapter):
    """
    AVEVA Historian equipment adapter.

    Connects to an AVEVA Historian REST API v2 endpoint and provides
    tag-based read/subscribe operations following the EquipmentAdapter
    interface contract.

    Extended methods (``get_analog_summary``, ``get_state_summary``,
    ``get_historical``) expose historian-specific capabilities beyond
    the standard EquipmentAdapter interface.

    Usage:
        adapter = AVEVAHistorianAdapter(settings)
        await adapter.connect()
        value = await adapter.read_tag("Baytown.tank_level")
        summary = await adapter.get_analog_summary("Baytown.tank_level", start, end)
        await adapter.disconnect()
    """

    def __init__(
        self,
        settings: AVEVAHistorianSettings | None = None,
    ) -> None:
        self._settings = settings or AVEVAHistorianSettings()
        self._client = AVEVAHistorianClient(self._settings)
        self._subscriptions: dict[str, _PollSubscription] = {}
        self._poll_task: asyncio.Task[None] | None = None

    @property
    def equipment_id(self) -> str:
        return self._settings.AVEVA_EQUIPMENT_ID

    # ── Lifecycle ─────────────────────────────────────────────

    async def connect(self) -> None:
        """Connect to the AVEVA Historian REST API."""
        await self._client.connect()
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info("AVEVA Historian adapter connected")

    async def disconnect(self) -> None:
        """Stop polling and disconnect."""
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None
        self._subscriptions.clear()
        await self._client.disconnect()
        logger.info("AVEVA Historian adapter disconnected")

    async def health_check(self) -> bool:
        """Check REST API connectivity."""
        return await self._client.health_check()

    # ── EquipmentAdapter interface ────────────────────────────

    async def read_tag(self, tag_name: str) -> TagValue:
        """
        Read the current value of a historian tag.

        Args:
            tag_name: Fully qualified name (e.g. "Baytown.tank_level").
        """
        fqn = self._resolve_fqn(tag_name)
        result = await self._client.get_current_value(fqn)
        if result is None:
            return TagValue(
                tag_name=tag_name,
                value=None,
                quality="bad",
                data_type="float",
            )
        return self._vtq_to_tag_value(tag_name, result)

    async def write_tag(self, tag_name: str, value: Any) -> None:
        """
        Not supported: AVEVA Historian REST API is read-only.

        Equipment writes should go through OPC-UA or MQTT adapters.
        """
        raise NotImplementedError(
            "AVEVA Historian REST API does not support writing process "
            "values to equipment. Use an OPC-UA or MQTT equipment adapter "
            "for tag writes."
        )

    async def subscribe_tag(
        self,
        tag_name: str,
        callback: Callable[[TagValue], Any],
        interval_ms: int = 5000,
    ) -> SubscriptionHandle:
        """
        Subscribe to value changes via polling.

        The Historian REST API has no push/WebSocket support, so
        subscriptions are implemented as periodic polls at the
        configured interval.

        Args:
            tag_name: FQN or tag name.
            callback: Invoked when value changes (async or sync).
            interval_ms: Polling interval in milliseconds.
        """
        fqn = self._resolve_fqn(tag_name)
        handle = SubscriptionHandle(tag_name=tag_name, active=True)

        sub = _PollSubscription(
            fqn=fqn,
            callback=callback,
            interval_sec=max(interval_ms / 1000.0, 1.0),
            handle=handle,
        )
        self._subscriptions[handle.handle_id] = sub
        logger.info(
            "Subscribed to %s (poll every %.1fs)", fqn, sub.interval_sec,
        )
        return handle

    async def unsubscribe(self, handle: SubscriptionHandle) -> None:
        """Cancel a polling subscription."""
        handle.active = False
        removed = self._subscriptions.pop(handle.handle_id, None)
        if removed:
            logger.info("Unsubscribed from %s", removed.fqn)

    async def get_equipment_state(self) -> EquipmentState:
        """
        Read equipment state from the configured state tag FQN.

        If no state tag is configured, returns "unknown" state.
        """
        state_fqn = self._settings.AVEVA_STATE_TAG_FQN
        if not state_fqn:
            return EquipmentState(
                equipment_id=self.equipment_id,
                state="unknown",
            )

        result = await self._client.get_current_value(state_fqn)
        if result is None:
            return EquipmentState(
                equipment_id=self.equipment_id,
                state="unknown",
                dispatch_category="unavailable_unplanned",
                oee_bucket="downtime_unplanned",
            )

        # Use Text field for discrete tags (state name), fall back to Value
        state_raw = result.get("Text") or str(result.get("Value", "unknown"))
        state = state_raw.strip().lower()

        return EquipmentState(
            equipment_id=self.equipment_id,
            state=state,
            dispatch_category=_STATE_DISPATCH_MAP.get(state, "available"),
            oee_bucket=_STATE_OEE_MAP.get(state, "uptime_non_value"),
        )

    async def browse_tags(self, root: str | None = None) -> list[TagInfo]:
        """
        Browse available tags from the historian.

        Args:
            root: Data source name or FQN prefix to filter by.
        """
        prefix = root or self._settings.AVEVA_TAG_PREFIX
        if prefix:
            tag_filter = f"startswith(FQN,'{prefix}')"
            raw_tags = await self._client.get_tags(tag_filter=tag_filter)
        else:
            source = self._settings.AVEVA_DATASOURCE or None
            raw_tags = await self._client.get_tags(source=source)

        return [
            TagInfo(
                tag_name=t.get("FQN", t.get("TagName", "")),
                data_type=_TAG_TYPE_MAP.get(t.get("TagType", ""), "float"),
                access="read",  # Historian is read-only for process values
                description=t.get("Description", ""),
            )
            for t in raw_tags
        ]

    # ── Extended: Historian-specific capabilities ─────────────

    async def get_analog_summary(
        self,
        fqn: str,
        start: datetime,
        end: datetime,
        resolution_ms: int | None = None,
        retrieval_mode: str = "Cyclic",
        slice_by: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get analog summary (time-weighted aggregates) for a tag.

        Returns records with: Average, StdDev, Minimum, Maximum,
        First, Last, Integral, PercentGood.

        Ref: https://docs.aveva.com/bundle/sp-historian/page/275756.html
        """
        return await self._client.get_analog_summary(
            fqn=self._resolve_fqn(fqn),
            start=start,
            end=end,
            resolution=resolution_ms,
            retrieval_mode=retrieval_mode,
            slice_by=slice_by,
        )

    async def get_state_summary(
        self,
        fqn: str,
        start: datetime,
        end: datetime,
        resolution_ms: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get state summary (time-in-state durations) for a discrete tag.

        Returns records with: Text (state name), Count, Total,
        Average, Minimum, Maximum.

        Particularly useful for OEE Availability calculation.

        Ref: https://docs.aveva.com/bundle/sp-historian/page/275757.html
        """
        return await self._client.get_state_summary(
            fqn=self._resolve_fqn(fqn),
            start=start,
            end=end,
            resolution=resolution_ms,
        )

    async def get_historical(
        self,
        fqn: str,
        start: datetime,
        end: datetime,
        retrieval_mode: str = "Full",
        resolution_ms: int | None = None,
    ) -> list[TagValue]:
        """
        Get historical process values with full RetrievalMode control.

        Args:
            fqn: Fully qualified name.
            start: Start time.
            end: End time.
            retrieval_mode: Average|Cyclic|Full|Interpolated|BestFit|Delta|
                           Minimum|Maximum|Counter|Integral|Slope
            resolution_ms: Resolution in milliseconds.

        Returns:
            List of TagValue records.
        """
        resolved_fqn = self._resolve_fqn(fqn)
        results = await self._client.get_process_values(
            fqn=resolved_fqn,
            start=start,
            end=end,
            retrieval_mode=retrieval_mode,
            resolution=resolution_ms,
        )
        return [self._vtq_to_tag_value(fqn, r) for r in results]

    # ── Internal helpers ──────────────────────────────────────

    def _resolve_fqn(self, tag_name: str) -> str:
        """
        Resolve a tag name to a fully qualified name.

        If the tag already contains a dot (datasource.tagname), use as-is.
        Otherwise prepend the configured datasource.
        """
        if "." in tag_name:
            return tag_name
        datasource = self._settings.AVEVA_DATASOURCE
        if datasource:
            return f"{datasource}.{tag_name}"
        return tag_name

    @staticmethod
    def _vtq_to_tag_value(tag_name: str, vtq: dict[str, Any]) -> TagValue:
        """Convert an AVEVA ProcessValues VTQ record to a TagValue DTO."""
        opc_quality = vtq.get("OpcQuality", 0)
        value = vtq.get("Value")
        text = vtq.get("Text")

        # For discrete/string tags, prefer Text field
        if value is None and text is not None:
            value = text

        # Infer data type
        if isinstance(value, bool):
            data_type = "bool"
        elif isinstance(value, int):
            data_type = "int"
        elif isinstance(value, float):
            data_type = "float"
        elif isinstance(value, str):
            data_type = "string"
        else:
            data_type = "float"

        # Parse timestamp
        dt_str = vtq.get("DateTime")
        if dt_str:
            try:
                timestamp = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                timestamp = datetime.now(timezone.utc)
        else:
            timestamp = datetime.now(timezone.utc)

        return TagValue(
            tag_name=tag_name,
            value=value,
            quality=_opc_quality_to_str(opc_quality),
            timestamp=timestamp,
            data_type=data_type,
        )

    async def _poll_loop(self) -> None:
        """Background task: poll subscribed tags at their configured intervals."""
        # Track last poll time per subscription
        last_poll: dict[str, float] = {}
        min_sleep = 0.5  # minimum loop sleep to avoid busy-waiting

        while True:
            try:
                now = asyncio.get_event_loop().time()
                next_due = now + 60.0  # fallback: sleep up to 60s if nothing to do

                for sub_id, sub in list(self._subscriptions.items()):
                    if not sub.handle.active:
                        continue

                    due_at = last_poll.get(sub_id, 0) + sub.interval_sec
                    if now >= due_at:
                        # Time to poll this tag
                        last_poll[sub_id] = now
                        try:
                            result = await self._client.get_current_value(sub.fqn)
                            if result is not None:
                                current_value = result.get("Value")
                                if current_value != sub.last_value:
                                    sub.last_value = current_value
                                    tag_value = self._vtq_to_tag_value(
                                        sub.handle.tag_name, result,
                                    )
                                    # Invoke callback (async or sync)
                                    ret = sub.callback(tag_value)
                                    if asyncio.iscoroutine(ret):
                                        await ret
                        except Exception:
                            logger.debug(
                                "Poll failed for %s", sub.fqn, exc_info=True,
                            )
                        due_at = now + sub.interval_sec

                    if due_at < next_due:
                        next_due = due_at

                sleep_time = max(next_due - asyncio.get_event_loop().time(), min_sleep)
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in AVEVA Historian poll loop")
                await asyncio.sleep(5.0)
