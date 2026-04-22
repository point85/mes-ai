"""
PackML OPC-UA Production Counter Plugin.

Subscribes to OPC-UA PackML PackTag nodes (OPC 30050 companion spec) on
equipment servers to collect production counts in real time.

Standard PackTags used:
    Admin.ProdProcessedCount[n]  — good units produced (per material index)
    Admin.ProdDefectiveCount[n]  — defective/rejected units produced
    Admin.CurMachSpeed           — current machine speed (for future use)

The plugin works with delta detection: it stores the last-known absolute
count for each equipment and only increments the MES production counter
by the difference when a data change notification arrives.

Architecture:
    OPC-UA Server (equipment)
        └─ data change subscription ──► PackMLOpcuaCountersPlugin
                                            └─ ProductionCounterService.increment_counter()
                                                └─ production.counter.updated event
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from mes.framework.plugin.base import MESPlugin

logger = logging.getLogger("mes.plugins.packml_opcua_counters")

# Standard PackML PackTag node paths (OPC 30050)
PACKTAG_GOOD_COUNT = "Admin.ProdProcessedCount"
PACKTAG_DEFECTIVE_COUNT = "Admin.ProdDefectiveCount"
PACKTAG_MACHINE_SPEED = "Admin.CurMachSpeed"

SOURCE_ID = "packml-opcua-counters"


class _EquipmentState:
    """Tracks the last-known absolute counts for delta detection."""

    __slots__ = ("equipment_id", "last_good", "last_reject")

    def __init__(self, equipment_id: UUID) -> None:
        self.equipment_id = equipment_id
        self.last_good: int | None = None
        self.last_reject: int | None = None


class PackMLOpcuaCountersPlugin(MESPlugin):
    """
    Subscribes to OPC-UA PackML PackTag nodes on configured equipment.

    On each data change notification the plugin:
    1. Computes the delta from the last-known value.
    2. Calls ProductionCounterService.increment_counter().
    3. The service emits a production.counter.updated event.

    Configuration (via manifest parameters):
        poll_interval_sec:         Fallback polling interval (default 5 s)
        subscription_interval_ms:  OPC-UA publishing interval (default 1000 ms)

    Equipment OPC-UA endpoints are read from this plugin's ``PluginConfig``
    row under ``config_overrides["equipment_mappings"]``.  Expected shape:

        {
          "equipment_mappings": {
            "<equipment_code>": {
              "opcua_endpoint":   "opc.tcp://10.0.0.1:4840",
              "opcua_namespace":  2,                               # optional
              "opcua_good_node":  "Admin.ProdProcessedCount",      # optional
              "opcua_reject_node": "Admin.ProdDefectiveCount"      # optional
            }
          }
        }
    """

    def __init__(self) -> None:
        self._config: dict[str, Any] = {}
        self._equipment_states: dict[UUID, _EquipmentState] = {}
        self._tasks: list[asyncio.Task[None]] = []
        self._running = False

    async def initialize(self, config: dict[str, Any]) -> None:
        self._config = config
        logger.info(
            "PackML OPC-UA counters plugin initialising "
            "(poll=%ss, sub_interval=%sms)",
            config.get("poll_interval_sec", 5),
            config.get("subscription_interval_ms", 1000),
        )

    async def start(self) -> None:
        """
        Discover equipment with OPC-UA endpoints and start subscriptions.

        Each equipment configured via ``PluginConfig.config_overrides
        ["equipment_mappings"]`` gets a dedicated asyncio task that
        subscribes to the PackTag nodes.
        """
        self._running = True
        equipment_list = await self._discover_opcua_equipment()

        if not equipment_list:
            logger.info("No equipment with OPC-UA endpoints found — plugin idle")
            return

        for equip_id, endpoint, namespace, good_node, reject_node in equipment_list:
            self._equipment_states[equip_id] = _EquipmentState(equip_id)
            task = asyncio.create_task(
                self._subscribe_loop(equip_id, endpoint, namespace, good_node, reject_node),
                name=f"packml-opcua-{equip_id}",
            )
            self._tasks.append(task)

        logger.info(
            "PackML OPC-UA counters started for %d equipment",
            len(equipment_list),
        )

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self._equipment_states.clear()
        logger.info("PackML OPC-UA counters plugin stopped")

    # ── OPC-UA subscription loop ──────────────────────────────────────

    async def _subscribe_loop(
        self,
        equip_id: UUID,
        endpoint: str,
        namespace: int,
        good_node_path: str,
        reject_node_path: str,
    ) -> None:
        """
        Connect to an OPC-UA server and subscribe to PackTag counter nodes.

        Uses asyncua data change subscriptions when available.  Falls back
        to polling at poll_interval_sec if subscription fails.
        """
        poll_interval = self._config.get("poll_interval_sec", 5)
        sub_interval = self._config.get("subscription_interval_ms", 1000)

        try:
            from asyncua import Client as OpcuaClient
        except ImportError:
            logger.error(
                "asyncua not installed — cannot subscribe to OPC-UA. "
                "Install with: pip install mes-ai[opcua]"
            )
            return

        while self._running:
            try:
                async with OpcuaClient(url=endpoint) as client:
                    logger.info("Connected to OPC-UA: %s for equip %s", endpoint, equip_id)

                    ns = namespace
                    good_node = client.get_node(f"ns={ns};s={good_node_path}")
                    reject_node = client.get_node(f"ns={ns};s={reject_node_path}")

                    # Try subscription-based monitoring
                    try:
                        handler = _DataChangeHandler(self, equip_id)
                        subscription = await client.create_subscription(sub_interval, handler)
                        await subscription.subscribe_data_change([good_node, reject_node])
                        logger.info(
                            "Subscribed to PackTag data changes (equip=%s, interval=%dms)",
                            equip_id, sub_interval,
                        )

                        # Keep alive while running
                        while self._running:
                            await asyncio.sleep(poll_interval)

                    except Exception as sub_err:
                        logger.warning(
                            "Subscription failed for %s, falling back to polling: %s",
                            equip_id, sub_err,
                        )
                        # Polling fallback
                        while self._running:
                            try:
                                good_val = await good_node.read_value()
                                reject_val = await reject_node.read_value()
                                await self._process_values(
                                    equip_id,
                                    int(good_val) if good_val is not None else 0,
                                    int(reject_val) if reject_val is not None else 0,
                                )
                            except Exception as read_err:
                                logger.warning("Poll read error (equip=%s): %s", equip_id, read_err)
                            await asyncio.sleep(poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as conn_err:
                logger.error(
                    "OPC-UA connection error (equip=%s, endpoint=%s): %s — retrying in %ds",
                    equip_id, endpoint, conn_err, poll_interval * 2,
                )
                await asyncio.sleep(poll_interval * 2)

    # ── Value processing (delta detection) ────────────────────────────

    async def _process_values(
        self,
        equip_id: UUID,
        good_absolute: int,
        reject_absolute: int,
    ) -> None:
        """
        Compare absolute counts against last-known values.
        If they increased, call increment_counter with the delta.
        """
        state = self._equipment_states.get(equip_id)
        if state is None:
            return

        good_delta = 0
        reject_delta = 0

        if state.last_good is not None and good_absolute > state.last_good:
            good_delta = good_absolute - state.last_good
        if state.last_reject is not None and reject_absolute > state.last_reject:
            reject_delta = reject_absolute - state.last_reject

        state.last_good = good_absolute
        state.last_reject = reject_absolute

        if good_delta > 0 or reject_delta > 0:
            from mes.framework.db import async_session_factory
            from mes.core.performance.service import ProductionCounterService

            async with async_session_factory() as session:
                await ProductionCounterService.increment_counter(
                    session,
                    equipment_id=equip_id,
                    good_delta=good_delta,
                    reject_delta=reject_delta,
                    source_plugin=SOURCE_ID,
                )
                await session.commit()

            logger.debug(
                "Counter update: equip=%s good=+%d reject=+%d (OPC-UA)",
                equip_id, good_delta, reject_delta,
            )

    # ── Equipment discovery ───────────────────────────────────────────

    async def _discover_opcua_equipment(
        self,
    ) -> list[tuple[UUID, str, int, str, str]]:
        """
        Build the list of (equipment_id, endpoint, namespace, good_node, reject_node)
        tuples by joining this plugin's ``PluginConfig.config_overrides
        ["equipment_mappings"]`` against the Equipment table (matched by code).

        Returns:
            List of (equipment_id, endpoint_url, namespace, good_node, reject_node)
        """
        from sqlalchemy import select
        from mes.framework.db import async_session_factory
        from mes.framework.plugin.models import PluginConfig
        from mes.core.physical_model.models import Equipment

        results: list[tuple[UUID, str, int, str, str]] = []

        async with async_session_factory() as session:
            cfg_row = (
                await session.execute(
                    select(PluginConfig).where(PluginConfig.plugin_id == SOURCE_ID)
                )
            ).scalar_one_or_none()

            mappings: dict[str, dict[str, Any]] = {}
            if cfg_row is not None:
                mappings = (cfg_row.config_overrides or {}).get("equipment_mappings", {}) or {}

            if not mappings:
                logger.info(
                    "No equipment_mappings configured in PluginConfig[%s] — nothing to discover",
                    SOURCE_ID,
                )
                return results

            codes = list(mappings.keys())
            eq_rows = (
                await session.execute(
                    select(Equipment).where(
                        Equipment.code.in_(codes),
                        Equipment.is_active.is_(True),
                    )
                )
            ).scalars().all()

            for eq in eq_rows:
                cfg = mappings.get(eq.code) or {}
                endpoint = cfg.get("opcua_endpoint")
                if not endpoint:
                    continue
                namespace = int(cfg.get("opcua_namespace", 2))
                good_node = cfg.get("opcua_good_node", PACKTAG_GOOD_COUNT)
                reject_node = cfg.get("opcua_reject_node", PACKTAG_DEFECTIVE_COUNT)
                results.append((eq.id, endpoint, namespace, good_node, reject_node))

        logger.info("Discovered %d OPC-UA-enabled equipment", len(results))
        return results


class _DataChangeHandler:
    """asyncua subscription handler that dispatches to the plugin."""

    def __init__(self, plugin: PackMLOpcuaCountersPlugin, equip_id: UUID) -> None:
        self._plugin = plugin
        self._equip_id = equip_id
        self._good_value: int = 0
        self._reject_value: int = 0

    def datachange_notification(self, node: Any, val: Any, data: Any) -> None:
        """Called by asyncua on data change.  Schedules async processing."""
        node_id = str(node)
        if PACKTAG_GOOD_COUNT in node_id:
            self._good_value = int(val) if val is not None else 0
        elif PACKTAG_DEFECTIVE_COUNT in node_id:
            self._reject_value = int(val) if val is not None else 0

        # Schedule async processing
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                self._plugin._process_values(
                    self._equip_id,
                    self._good_value,
                    self._reject_value,
                )
            )
        except RuntimeError:
            pass  # No running loop — ignore
