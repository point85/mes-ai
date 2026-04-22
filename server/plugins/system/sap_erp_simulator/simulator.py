"""
SAP ERP Simulator: inbound and outbound adapter implementations.

Unlike the generic MockERP adapter (which uses MES-native field names), this
simulator stores data in **SAP OData V4 format** and runs every record through
the real ``SAPS4HANATransformLayer`` before returning canonical DTOs.

Outbound reports are transformed into SAP format (using the same transform
layer) and validated against the in-memory order book before returning an
SAP-style confirmation document number.

This exercises the full SAP data pipeline end-to-end without a live SAP
system.
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
from mes.adapters.erp.sap_s4hana.transform import SAPS4HANATransformLayer

from .sap_data import (
    SAP_BOMS,
    SAP_MATERIALS,
    SAP_PRODUCTION_ORDERS,
    SAP_PRODUCTS,
    SAP_ROUTINGS,
    SAP_WORK_CENTERS,
)

logger = logging.getLogger("mes.plugins.sap_erp_simulator")


class SAPSimulatorInboundAdapter(ERPInboundAdapter):
    """
    Simulated SAP S/4HANA inbound adapter.

    Holds SAP-format records in memory and transforms them through
    ``SAPS4HANATransformLayer`` — exactly as the real adapter would after
    fetching OData V4 JSON from SAP.

    Supports ``since`` for incremental sync: production orders whose
    ``MfgOrderPlannedStartDate`` is after ``since`` are returned.
    """

    erp_type: str = "sap"

    def __init__(
        self,
        plant: str = "1000",
        company_code: str = "1000",
        latency_ms: int = 0,
        failure_rate: float = 0.0,
    ) -> None:
        self._plant = plant
        self._company_code = company_code
        self._latency_ms = max(0, latency_ms)
        self._failure_rate = max(0.0, min(1.0, failure_rate))
        self._connected = False
        self._transform = SAPS4HANATransformLayer()

        # Deep-copy mutable data so each simulator instance is independent
        self._materials: list[dict] = copy.deepcopy(SAP_MATERIALS)
        self._products: list[dict] = copy.deepcopy(SAP_PRODUCTS)
        self._orders: list[dict] = copy.deepcopy(SAP_PRODUCTION_ORDERS)
        self._boms: dict[str, list[dict]] = copy.deepcopy(SAP_BOMS)
        self._routings: dict[str, list[dict]] = copy.deepcopy(SAP_ROUTINGS)
        self._work_centers: list[dict] = copy.deepcopy(SAP_WORK_CENTERS)

    # ── Lifecycle ─────────────────────────────────────────────────

    async def connect(self) -> None:
        await self._simulate_latency()
        self._connected = True
        logger.info(
            "SAPSimulatorInbound connected (plant=%s, company=%s, "
            "%d materials, %d orders, %d routings)",
            self._plant, self._company_code,
            len(self._materials), len(self._orders), len(self._routings),
        )

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("SAPSimulatorInbound disconnected")

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
                if (o.get("MfgOrderPlannedStartDate") or "") >= since_iso
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
        sap_boms = self._boms.get(product_id, [])
        return [self._transform.to_bom(b) for b in sap_boms]

    async def sync_routings(self, product_id: str) -> list[ProcessRouteDTO]:
        await self._simulate_latency()
        self._maybe_fail("sync_routings")
        sap_routes = self._routings.get(product_id, [])
        return [self._transform.to_routing(r) for r in sap_routes]

    async def sync_work_cells(self) -> list[WorkCellDTO]:
        await self._simulate_latency()
        self._maybe_fail("sync_work_cells")
        return [self._transform.to_work_cell(wc) for wc in self._work_centers]

    # ── Data mutation helpers (for test setup and simulator GUI) ──

    def add_operations_request(self, sap_order: dict) -> None:
        """Inject an additional SAP-format order into the simulator."""
        self._orders.append(sap_order)

    def add_material(self, sap_material: dict) -> None:
        """Inject an additional SAP-format material into the simulator."""
        self._materials.append(sap_material)

    def update_material(self, code: str, fields: dict) -> dict | None:
        """Update an existing SAP-format material by code. Returns updated record or None."""
        for mat in self._materials:
            if mat["Material"] == code:
                mat.update(fields)
                return mat
        return None

    def delete_material(self, code: str) -> bool:
        """Remove a material by code. Returns True if found and removed."""
        for i, mat in enumerate(self._materials):
            if mat["Material"] == code:
                self._materials.pop(i)
                return True
        return False

    def get_material(self, code: str) -> dict | None:
        """Get a single SAP-format material by code."""
        for mat in self._materials:
            if mat["Material"] == code:
                return mat
        return None

    def add_bom(self, product_code: str, sap_bom: dict) -> None:
        """Inject an additional SAP-format BOM for a product."""
        self._boms.setdefault(product_code, []).append(sap_bom)

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
        """Build a SAP-format material dict from canonical fields."""
        return {
            "Material": code,
            "MaterialName": name,
            "MaterialType": material_type,
            "BaseUnit": uom,
            "MaterialRevisionLevel": revision,
            "MaterialDescription": description,
            "MaximumStoragePeriod": str(shelf_life_days) if shelf_life_days else None,
            "MaterialGroup": "001",
            "Plant": self._plant,
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
        """Build a SAP-format update dict from optional canonical fields."""
        updates: dict = {}
        if name is not None:
            updates["MaterialName"] = name
        if material_type is not None:
            updates["MaterialType"] = material_type
        if uom is not None:
            updates["BaseUnit"] = uom
        if revision is not None:
            updates["MaterialRevisionLevel"] = revision
        if description is not None:
            updates["MaterialDescription"] = description
        if shelf_life_days is not None:
            updates["MaximumStoragePeriod"] = str(shelf_life_days)
        return updates

    @staticmethod
    def material_type_options() -> list[dict[str, str]]:
        """Return SAP-specific material type codes for UI dropdowns."""
        return [
            {"code": "ROH", "label": "Raw Material"},
            {"code": "HALB", "label": "Semi-Finished"},
            {"code": "FERT", "label": "Finished Product"},
            {"code": "VERP", "label": "Packaging"},
        ]

    # ── Internal helpers ──────────────────────────────────────────

    async def _simulate_latency(self) -> None:
        if self._latency_ms > 0:
            await asyncio.sleep(self._latency_ms / 1000.0)

    def _maybe_fail(self, operation: str) -> None:
        if self._failure_rate > 0 and random.random() < self._failure_rate:  # noqa: S311
            from mes.adapters.erp.exceptions import ERPSyncError
            raise ERPSyncError(
                message=f"Simulated SAP OData error on {operation} "
                        f"(CX_SY_OPEN_SQL_DB / HTTP 503)",
            )


class SAPSimulatorOutboundAdapter(ERPOutboundAdapter):
    """
    Simulated SAP S/4HANA outbound adapter.

    Accepts MES outbound reports, transforms them into SAP format via
    ``SAPS4HANATransformLayer``, validates against the in-memory order book,
    and returns SAP-style confirmation document numbers.

    SAP document number patterns:
    - Production order confirmations:  49XXXXXXXX  (10-digit)
    - Material documents (261 mvmt):   49XXXXXXXX
    - Quality notifications:           200XXXXXXX
    """

    def __init__(
        self,
        plant: str = "1000",
        company_code: str = "1000",
        latency_ms: int = 0,
        failure_rate: float = 0.0,
    ) -> None:
        self._plant = plant
        self._company_code = company_code
        self._latency_ms = max(0, latency_ms)
        self._failure_rate = max(0.0, min(1.0, failure_rate))
        self._connected = False
        self._transform = SAPS4HANATransformLayer()

        # Counters for SAP document number series
        self._confirmation_seq = 4900000000
        self._matdoc_seq = 4900000000
        self._qm_seq = 2000000000

        # Known orders for validation (populated from inbound data)
        self._known_orders: set[str] = {
            o["ManufacturingOrder"] for o in SAP_PRODUCTION_ORDERS
        }

        # Stored confirmations for test inspection
        self._confirmations: list[dict[str, Any]] = []

    @property
    def confirmations(self) -> list[dict[str, Any]]:
        """All confirmations recorded by the simulator (for test assertions)."""
        return list(self._confirmations)

    # ── Lifecycle ─────────────────────────────────────────────────

    async def connect(self) -> None:
        await self._simulate_latency()
        self._connected = True
        logger.info(
            "SAPSimulatorOutbound connected (plant=%s, %d known orders)",
            self._plant, len(self._known_orders),
        )

    async def disconnect(self) -> None:
        self._connected = False
        logger.info("SAPSimulatorOutbound disconnected")

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
        """
        Post a production order confirmation to SAP.

        Transforms the report through SAPS4HANATransformLayer.from_completion()
        to validate SAP payload structure, then returns a SAP confirmation
        document number (49-series).
        """
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
        sap_payload = self._transform.from_completion(report)

        self._confirmation_seq += 1
        doc_number = str(self._confirmation_seq)

        record = {
            "type": "confirmation",
            "sap_document": doc_number,
            "sap_payload": sap_payload,
            "order_id": order_id,
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }
        self._confirmations.append(record)

        logger.info(
            "SAP confirmation %s posted for order %s (yield=%d, scrap=%d)",
            doc_number, order_id, qty_good, qty_reject,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=doc_number,
            message=f"SAP confirmation {doc_number} posted",
        )

    async def report_consumption(
        self,
        order_id: str,
        materials: list[MaterialConsumptionDTO],
    ) -> ERPConfirmation:
        """
        Post a goods movement (261 — issue to production order) to SAP.

        Transforms the report through SAPS4HANATransformLayer.from_consumption()
        to validate the GoodsMovementItems structure.
        """
        await self._simulate_latency()
        self._maybe_fail("report_consumption")

        from mes.adapters.erp.dtos import ConsumptionReport
        report = ConsumptionReport(erp_reference=order_id, materials=materials)
        sap_payload = self._transform.from_consumption(report)

        self._matdoc_seq += 1
        doc_number = str(self._matdoc_seq)

        record = {
            "type": "goods_movement_261",
            "sap_document": doc_number,
            "sap_payload": sap_payload,
            "order_id": order_id,
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }
        self._confirmations.append(record)

        logger.info(
            "SAP material document %s posted for order %s (%d line items)",
            doc_number, order_id, len(materials),
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=doc_number,
            message=f"SAP material document {doc_number} posted (mvmt 261)",
        )

    async def report_scrap(
        self,
        order_id: str,
        qty_scrapped: int,
        reason_code: str,
    ) -> ERPConfirmation:
        """Post a scrap confirmation (SAP movement type 531)."""
        await self._simulate_latency()
        self._maybe_fail("report_scrap")

        self._confirmation_seq += 1
        doc_number = str(self._confirmation_seq)

        record = {
            "type": "scrap_531",
            "sap_document": doc_number,
            "sap_payload": {
                "OrderID": order_id,
                "ConfirmationScrapQuantity": str(qty_scrapped),
                "ScrapReasonCode": reason_code,
                "GoodsMovementType": "531",
            },
            "order_id": order_id,
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }
        self._confirmations.append(record)

        logger.info(
            "SAP scrap document %s posted for order %s (qty=%d, reason=%s)",
            doc_number, order_id, qty_scrapped, reason_code,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=doc_number,
            message=f"SAP scrap confirmation {doc_number} posted (mvmt 531)",
        )

    async def report_labor(
        self,
        order_id: str,
        operator_id: str,
        duration_minutes: float,
    ) -> ERPConfirmation:
        """Post a time/labor confirmation to SAP (CATS timesheet)."""
        await self._simulate_latency()
        self._maybe_fail("report_labor")

        self._confirmation_seq += 1
        doc_number = str(self._confirmation_seq)

        record = {
            "type": "time_confirmation",
            "sap_document": doc_number,
            "sap_payload": {
                "OrderID": order_id,
                "PersonnelNumber": operator_id,
                "ActualActivityDuration": str(duration_minutes),
                "ActivityUnit": "MIN",
            },
            "order_id": order_id,
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }
        self._confirmations.append(record)

        logger.info(
            "SAP time confirmation %s posted for order %s (operator=%s, %s min)",
            doc_number, order_id, operator_id, duration_minutes,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=doc_number,
            message=f"SAP time confirmation {doc_number} posted",
        )

    async def report_downtime(
        self,
        equipment_id: str,
        duration_minutes: float,
        reason_code: str,
        started_at: datetime,
    ) -> ERPConfirmation:
        """Post a PM notification for equipment downtime to SAP."""
        await self._simulate_latency()
        self._maybe_fail("report_downtime")

        self._confirmation_seq += 1
        doc_number = str(self._confirmation_seq)

        record = {
            "type": "pm_notification",
            "sap_document": doc_number,
            "sap_payload": {
                "TechnicalObject": equipment_id,
                "NotificationType": "M2",
                "BreakdownDuration": str(duration_minutes),
                "BreakdownDurationUnit": "MIN",
                "DamageCode": reason_code,
                "MalfunctionStartDate": started_at.strftime("%Y-%m-%dT%H:%M:%S"),
            },
            "equipment_id": equipment_id,
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }
        self._confirmations.append(record)

        logger.info(
            "SAP PM notification %s posted for equipment %s (%s min, reason=%s)",
            doc_number, equipment_id, duration_minutes, reason_code,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=doc_number,
            message=f"SAP PM notification {doc_number} posted",
        )

    async def report_quality_result(
        self,
        order_id: str,
        test_id: str,
        result: str,
        details: dict[str, Any],
    ) -> ERPConfirmation:
        """Post a QM results-recording to SAP."""
        await self._simulate_latency()
        self._maybe_fail("report_quality_result")

        self._qm_seq += 1
        doc_number = str(self._qm_seq)

        record = {
            "type": "qm_results_recording",
            "sap_document": doc_number,
            "sap_payload": {
                "InspectionLot": order_id,
                "InspectionCharacteristic": test_id,
                "InspectionResult": result,
                "InspectionResultDetails": details,
            },
            "order_id": order_id,
            "posted_at": datetime.now(timezone.utc).isoformat(),
        }
        self._confirmations.append(record)

        logger.info(
            "SAP QM result %s posted for order %s (test=%s, result=%s)",
            doc_number, order_id, test_id, result,
        )
        return ERPConfirmation(
            success=True,
            erp_doc_number=doc_number,
            message=f"SAP QM results recording {doc_number} posted",
        )

    # ── Internal helpers ──────────────────────────────────────────

    async def _simulate_latency(self) -> None:
        if self._latency_ms > 0:
            await asyncio.sleep(self._latency_ms / 1000.0)

    def _maybe_fail(self, operation: str) -> None:
        if self._failure_rate > 0 and random.random() < self._failure_rate:  # noqa: S311
            from mes.adapters.erp.exceptions import ERPOutboundError
            raise ERPOutboundError(
                message=f"Simulated SAP OData error on {operation} "
                        f"(CX_SY_OPEN_SQL_DB / HTTP 503)",
            )
