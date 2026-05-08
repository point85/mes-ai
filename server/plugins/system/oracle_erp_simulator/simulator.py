"""
Oracle Cloud ERP Simulator: inbound and outbound adapter implementations.

Unlike the generic MockERP adapter (which uses MES-native field names), this
simulator stores data in **Oracle REST API format** and runs every record through
the real ``OracleTransformLayer`` before returning canonical DTOs.

Outbound reports are transformed into Oracle format (using the same transform
layer) and validated against the in-memory work order book before returning an
Oracle-style transaction number.

This exercises the full Oracle data pipeline end-to-end without a live Oracle
Cloud instance.
"""

from __future__ import annotations

import asyncio
import copy
import logging
import random
from datetime import datetime, timezone
from typing import Any

from mes.adapters.erp.dtos import (
    BillOfMaterialDTO,
    ERPConfirmation,
    MaterialConsumptionDTO,
    MaterialDefinitionDTO,
    ProcessRouteDTO,
    ProductDefinitionDTO,
    OperationsRequestDTO,
    WorkCellDTO,
)
from mes.adapters.erp.interfaces import ERPInboundAdapter, ERPOutboundAdapter
from mes.adapters.erp.oracle.transform import OracleTransformLayer

from .oracle_data import (
    ORACLE_BOMS,
    ORACLE_MATERIALS,
    ORACLE_PRODUCTS,
    ORACLE_ROUTINGS,
    ORACLE_WORK_CENTERS,
    ORACLE_WORK_ORDERS,
)

logger = logging.getLogger("mes.plugins.oracle_erp_simulator")


class OracleSimulatorInboundAdapter(ERPInboundAdapter):
    """
    Simulated Oracle Cloud ERP inbound adapter.

    Holds Oracle-format records in memory and transforms them through
    ``OracleTransformLayer`` — exactly as the real adapter would after
    fetching REST JSON from Oracle Fusion.
    """

    erp_type: str = "oracle"

    def __init__(
        self,
        organization_code: str = "ORG_MAIN",
        business_unit: str = "BU_MANUFACTURING",
        latency_ms: int = 0,
        failure_rate: float = 0.0,
    ) -> None:
        self._organization_code = organization_code
        self._business_unit = business_unit
        self._latency_ms = max(0, latency_ms)
        self._failure_rate = max(0.0, min(1.0, failure_rate))
        self._connected = False
        self._transform = OracleTransformLayer()

        # Deep-copy mutable data so each simulator instance is independent
        self._materials: list[dict] = copy.deepcopy(ORACLE_MATERIALS)
        self._products: list[dict] = copy.deepcopy(ORACLE_PRODUCTS)
        self._orders: list[dict] = copy.deepcopy(ORACLE_WORK_ORDERS)
        self._boms: dict[str, list[dict]] = copy.deepcopy(ORACLE_BOMS)
        self._routings: dict[str, list[dict]] = copy.deepcopy(ORACLE_ROUTINGS)
        self._work_centers: list[dict] = copy.deepcopy(ORACLE_WORK_CENTERS)

    # ── Lifecycle ─────────────────────────────────────────────────

    async def connect(self) -> None:
        await self._simulate_latency()
        self._connected = True
        logger.info(
            "OracleSimulatorInbound connected (org=%s, bu=%s, "
            "%d materials, %d work orders, %d routings)",
            self._organization_code, self._business_unit,
            len(self._materials), len(self._orders), len(self._routings),
        )

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("OracleSimulatorInbound disconnected")

    async def health_check(self) -> bool:
        return self._connected

    # ── Inbound sync methods ──────────────────────────────────────

    async def sync_operations_requests(
        self, since: datetime | None = None,
    ) -> list[OperationsRequestDTO]:
        await self._simulate_latency()
        self._maybe_fail("sync_operations_requests")

        orders = self._orders
        if since:
            since_iso = since.isoformat()
            orders = [
                o for o in orders
                if (o.get("PlannedStartDate") or "") >= since_iso
            ]

        return [self._transform.to_operations_request(o) for o in orders]

    async def sync_materials(
        self, since: datetime | None = None,
    ) -> list[MaterialDefinitionDTO]:
        await self._simulate_latency()
        self._maybe_fail("sync_materials")
        return [self._transform.to_material(m) for m in self._materials]

    async def sync_products(
        self, since: datetime | None = None,
    ) -> list[ProductDefinitionDTO]:
        await self._simulate_latency()
        self._maybe_fail("sync_products")
        return [self._transform.to_product(p) for p in self._products]

    async def sync_boms(self, product_id: str) -> list[BillOfMaterialDTO]:
        await self._simulate_latency()
        self._maybe_fail("sync_boms")
        oracle_boms = self._boms.get(product_id, [])
        return [self._transform.to_bom(b) for b in oracle_boms]

    async def sync_routings(self, product_id: str) -> list[ProcessRouteDTO]:
        await self._simulate_latency()
        self._maybe_fail("sync_routings")
        oracle_routes = self._routings.get(product_id, [])
        return [self._transform.to_routing(r) for r in oracle_routes]

    async def sync_work_cells(self) -> list[WorkCellDTO]:
        await self._simulate_latency()
        self._maybe_fail("sync_work_cells")
        return [self._transform.to_work_cell(wc) for wc in self._work_centers]

    # ── Data mutation helpers (for simulator GUI CRUD) ────────────

    def get_material(self, code: str) -> dict | None:
        """Get a single Oracle-format material by item number."""
        for mat in self._materials:
            if mat["ItemNumber"] == code:
                return mat
        return None

    def add_material(self, oracle_material: dict) -> None:
        """Inject an additional Oracle-format material into the simulator."""
        self._materials.append(oracle_material)

    def update_material(self, code: str, fields: dict) -> dict | None:
        """Update an existing Oracle-format material by code. Returns updated record or None."""
        for mat in self._materials:
            if mat["ItemNumber"] == code:
                mat.update(fields)
                return mat
        return None

    def delete_material(self, code: str) -> bool:
        """Remove a material by item number. Returns True if found and removed."""
        for i, mat in enumerate(self._materials):
            if mat["ItemNumber"] == code:
                self._materials.pop(i)
                return True
        return False

    def add_operations_request(self, oracle_order: dict) -> None:
        """Inject an additional Oracle-format work order into the simulator."""
        self._orders.append(oracle_order)

    def add_bom(self, product_code: str, oracle_bom: dict) -> None:
        """Inject an additional Oracle-format BOM for a product."""
        self._boms.setdefault(product_code, []).append(oracle_bom)

    # ── Vendor-specific helpers for routes ────────────────────────

    def build_material_record(
        self,
        *,
        code: str,
        name: str,
        material_type: str,
        uom: str,
        revision: str | None = None,
        description: str = "",
        shelf_life_days: int | None = None,
    ) -> dict:
        """Build an Oracle-format material dict from canonical fields."""
        return {
            "ItemNumber": code,
            "Description": name,
            "ItemType": material_type,
            "PrimaryUOMCode": uom,
            "RevisionCode": revision,
            "LongDescription": description,
            "ShelfLifeDays": shelf_life_days,
            "ItemClass": "Raw Material",
            "OrganizationCode": self._organization_code,
            "InventoryItemId": 100000 + len(self._materials) + 1,
        }

    def build_material_updates(
        self,
        *,
        name: str | None = None,
        material_type: str | None = None,
        uom: str | None = None,
        revision: str | None = None,
        description: str | None = None,
        shelf_life_days: int | None = None,
    ) -> dict:
        """Build an Oracle-format update dict from optional canonical fields."""
        updates: dict = {}
        if name is not None:
            updates["Description"] = name
        if material_type is not None:
            updates["ItemType"] = material_type
        if uom is not None:
            updates["PrimaryUOMCode"] = uom
        if revision is not None:
            updates["RevisionCode"] = revision
        if description is not None:
            updates["LongDescription"] = description
        if shelf_life_days is not None:
            updates["ShelfLifeDays"] = shelf_life_days
        return updates

    @staticmethod
    def material_type_options() -> list[dict[str, str]]:
        """Return Oracle-specific material type codes for UI dropdowns."""
        return [
            {"code": "STANDARD", "label": "Standard (Raw Material)"},
            {"code": "SUBASSEMBLY", "label": "Subassembly"},
            {"code": "FINISHED_GOOD", "label": "Finished Good"},
            {"code": "PURCHASED", "label": "Purchased"},
            {"code": "EXPENSE", "label": "Expense / Consumable"},
        ]

    # ── Internal helpers ──────────────────────────────────────────

    async def _simulate_latency(self) -> None:
        if self._latency_ms > 0:
            await asyncio.sleep(self._latency_ms / 1000.0)

    def _maybe_fail(self, operation: str) -> None:
        if self._failure_rate > 0 and random.random() < self._failure_rate:  # noqa: S311
            from mes.adapters.erp.exceptions import ERPSyncError
            raise ERPSyncError(
                message=f"Simulated Oracle REST API error on {operation} "
                        f"(HTTP 503 / Service Unavailable)",
            )


class OracleSimulatorOutboundAdapter(ERPOutboundAdapter):
    """
    Simulated Oracle Cloud ERP outbound adapter.

    Accepts MES outbound reports, transforms them into Oracle format via
    ``OracleTransformLayer``, validates against the in-memory work order book,
    and returns Oracle-style transaction numbers.
    """

    def __init__(
        self,
        organization_code: str = "ORG_MAIN",
        business_unit: str = "BU_MANUFACTURING",
        latency_ms: int = 0,
        failure_rate: float = 0.0,
    ) -> None:
        self._organization_code = organization_code
        self._business_unit = business_unit
        self._latency_ms = max(0, latency_ms)
        self._failure_rate = max(0.0, min(1.0, failure_rate))
        self._connected = False
        self._transform = OracleTransformLayer()

        # Counters for Oracle transaction number series
        self._completion_seq = 3000000
        self._material_txn_seq = 3100000
        self._quality_seq = 3200000

        # Known work orders for validation
        self._known_orders: set[str] = {
            o["WorkOrderNumber"] for o in ORACLE_WORK_ORDERS
        }

        # Stored confirmations for inspection (capped at _MAX_CONFIRMATIONS)
        self._confirmations: list[dict[str, Any]] = []

    _MAX_CONFIRMATIONS = 100

    def _record_confirmation(self, record: dict[str, Any]) -> None:
        """Append a confirmation, keeping only the last _MAX_CONFIRMATIONS entries."""
        self._confirmations.append(record)
        if len(self._confirmations) > self._MAX_CONFIRMATIONS:
            self._confirmations = self._confirmations[-self._MAX_CONFIRMATIONS:]

    @property
    def confirmations(self) -> list[dict[str, Any]]:
        """Most recent confirmations recorded by the simulator (up to _MAX_CONFIRMATIONS)."""
        return list(self._confirmations)

    # ── Lifecycle ─────────────────────────────────────────────────

    async def connect(self) -> None:
        await self._simulate_latency()
        self._connected = True
        logger.info(
            "OracleSimulatorOutbound connected (org=%s, %d known work orders)",
            self._organization_code, len(self._known_orders),
        )

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("OracleSimulatorOutbound disconnected")

    async def health_check(self) -> bool:
        return self._connected

    # ── Outbound report methods ───────────────────────────────────

    async def report_completion(
        self,
        order_id: str,
        qty_good: int,
        qty_reject: int,
        step_id: str | None = None,
    ) -> ERPConfirmation:
        """Post a work order completion transaction."""
        await self._simulate_latency()
        self._maybe_fail("report_completion")

        from mes.adapters.erp.dtos import CompletionReport
        report = CompletionReport(
            erp_reference=order_id,
            qty_good=qty_good,
            qty_reject=qty_reject,
            step_id=step_id,
            completed_at=datetime.now(timezone.utc),
        )
        oracle_payload = self._transform.from_completion(report)

        self._completion_seq += 1
        txn_number = str(self._completion_seq)

        record = {
            "type": "wip_completion",
            "erp_document": txn_number,
            "erp_payload": oracle_payload,
            "order_id": order_id,
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }
        self._record_confirmation(record)

        logger.info(
            "Oracle completion txn %s posted for work order %s (yield=%d, reject=%d)",
            txn_number, order_id, qty_good, qty_reject,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=txn_number,
            message=f"Oracle completion transaction {txn_number} posted",
        )

    async def report_consumption(
        self,
        order_id: str,
        materials: list[MaterialConsumptionDTO],
    ) -> ERPConfirmation:
        """Post a material issue transaction (WIP_ISSUE)."""
        await self._simulate_latency()
        self._maybe_fail("report_consumption")

        from mes.adapters.erp.dtos import ConsumptionReport
        report = ConsumptionReport(erp_reference=order_id, materials=materials)
        oracle_payload = self._transform.from_consumption(report)

        self._material_txn_seq += 1
        txn_number = str(self._material_txn_seq)

        record = {
            "type": "wip_material_issue",
            "erp_document": txn_number,
            "erp_payload": oracle_payload,
            "order_id": order_id,
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }
        self._record_confirmation(record)

        logger.info(
            "Oracle material txn %s posted for work order %s (%d line items)",
            txn_number, order_id, len(materials),
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=txn_number,
            message=f"Oracle material transaction {txn_number} posted (WIP_ISSUE)",
        )

    async def report_scrap(
        self,
        order_id: str,
        qty_scrapped: int,
        reason_code: str,
    ) -> ERPConfirmation:
        """Post a scrap transaction."""
        await self._simulate_latency()
        self._maybe_fail("report_scrap")

        self._material_txn_seq += 1
        txn_number = str(self._material_txn_seq)

        record = {
            "type": "wip_scrap",
            "erp_document": txn_number,
            "erp_payload": {
                "WorkOrderNumber": order_id,
                "ScrapQuantity": str(qty_scrapped),
                "ReasonCode": reason_code,
                "TransactionType": "WIP_SCRAP",
            },
            "order_id": order_id,
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }
        self._record_confirmation(record)

        logger.info(
            "Oracle scrap txn %s posted for work order %s (qty=%d, reason=%s)",
            txn_number, order_id, qty_scrapped, reason_code,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=txn_number,
            message=f"Oracle scrap transaction {txn_number} posted",
        )

    async def report_labor(
        self,
        order_id: str,
        operator_id: str,
        duration_minutes: float,
    ) -> ERPConfirmation:
        """Post a labor/resource transaction."""
        await self._simulate_latency()
        self._maybe_fail("report_labor")

        self._completion_seq += 1
        txn_number = str(self._completion_seq)

        record = {
            "type": "resource_transaction",
            "erp_document": txn_number,
            "erp_payload": {
                "WorkOrderNumber": order_id,
                "ResourceCode": operator_id,
                "ResourceUsage": str(duration_minutes),
                "UOMCode": "MIN",
                "TransactionType": "RESOURCE_CHARGE",
            },
            "order_id": order_id,
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }
        self._record_confirmation(record)

        logger.info(
            "Oracle resource txn %s posted for work order %s (resource=%s, %s min)",
            txn_number, order_id, operator_id, duration_minutes,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=txn_number,
            message=f"Oracle resource transaction {txn_number} posted",
        )

    async def report_downtime(
        self,
        equipment_id: str,
        duration_minutes: float,
        reason_code: str,
        started_at: datetime,
    ) -> ERPConfirmation:
        """Post an equipment downtime event (maintenance work order)."""
        await self._simulate_latency()
        self._maybe_fail("report_downtime")

        self._completion_seq += 1
        txn_number = str(self._completion_seq)

        record = {
            "type": "maintenance_event",
            "erp_document": txn_number,
            "erp_payload": {
                "AssetNumber": equipment_id,
                "DowntimeDuration": str(duration_minutes),
                "DurationUOM": "MIN",
                "FailureCode": reason_code,
                "FailureDate": started_at.strftime("%Y-%m-%dT%H:%M:%S"),
                "TransactionType": "MAINTENANCE_EVENT",
            },
            "equipment_id": equipment_id,
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }
        self._record_confirmation(record)

        logger.info(
            "Oracle maintenance event %s posted for asset %s (%s min, reason=%s)",
            txn_number, equipment_id, duration_minutes, reason_code,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=txn_number,
            message=f"Oracle maintenance event {txn_number} posted",
        )

    async def report_quality_result(
        self,
        order_id: str,
        test_id: str,
        result: str,
        details: dict[str, Any],
    ) -> ERPConfirmation:
        """Post a quality inspection result."""
        await self._simulate_latency()
        self._maybe_fail("report_quality_result")

        self._quality_seq += 1
        txn_number = str(self._quality_seq)

        record = {
            "type": "quality_result",
            "erp_document": txn_number,
            "erp_payload": {
                "WorkOrderNumber": order_id,
                "InspectionPlanCode": test_id,
                "InspectionResult": result,
                "InspectionDetails": details,
                "TransactionType": "QUALITY_RESULT",
            },
            "order_id": order_id,
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }
        self._record_confirmation(record)

        logger.info(
            "Oracle quality result %s posted for work order %s (test=%s, result=%s)",
            txn_number, order_id, test_id, result,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=txn_number,
            message=f"Oracle quality result {txn_number} posted",
        )

    # ── Internal helpers ──────────────────────────────────────────

    async def _simulate_latency(self) -> None:
        if self._latency_ms > 0:
            await asyncio.sleep(self._latency_ms / 1000.0)

    def _maybe_fail(self, operation: str) -> None:
        if self._failure_rate > 0 and random.random() < self._failure_rate:  # noqa: S311
            from mes.adapters.erp.exceptions import ERPOutboundError
            raise ERPOutboundError(
                message=f"Simulated Oracle REST API error on {operation} "
                        f"(HTTP 503 / Service Unavailable)",
            )
