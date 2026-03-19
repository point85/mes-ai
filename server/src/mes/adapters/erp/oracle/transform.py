"""
Oracle Cloud ERP: Transform layer.

Maps between Oracle Fusion REST field names and the MES canonical DTOs.

Oracle Cloud ERP uses CamelCase field names in REST responses:
  WorkOrderNumber  → Production order reference
  ItemNumber       → Item/material code
  OrganizationCode → Inventory organization
  WorkCenterName   → Work center
  OperationSequenceNumber → Routing step sequence

This layer normalizes those into MES ProductionOrderDTO, MaterialDefinitionDTO, etc.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from mes.adapters.erp.dtos import (
    BillOfMaterialDTO,
    BOMItemDTO,
    CompletionReport,
    ConsumptionReport,
    MaterialDefinitionDTO,
    ProcessRouteDTO,
    ProductDefinitionDTO,
    ProductionOrderDTO,
    RouteStepDTO,
    WorkCellDTO,
)
from mes.adapters.erp.interfaces import ERPTransformLayer


class OracleTransformLayer(ERPTransformLayer):
    """
    Oracle Cloud ERP (Fusion) field mapping.

    Inbound: Oracle REST JSON → MES DTO
    Outbound: MES report → Oracle-formatted payload
    """

    # ── Inbound transforms ──────────────────────────────────────────

    def to_production_order(self, erp_data: dict[str, Any]) -> ProductionOrderDTO:
        """Map Oracle work order fields to ProductionOrderDTO."""
        return ProductionOrderDTO(
            erp_reference=str(erp_data.get("WorkOrderNumber", "")),
            product_code=erp_data.get("ItemNumber", ""),
            quantity_ordered=int(erp_data.get("PlannedQuantity", erp_data.get("Quantity", 0))),
            planned_start=_parse_oracle_datetime(erp_data.get("PlannedStartDate")),
            planned_end=_parse_oracle_datetime(erp_data.get("PlannedCompletionDate")),
            priority=_map_oracle_priority(erp_data.get("WorkOrderPriority")),
            uom=erp_data.get("UOMCode", "EA"),
            bom_id=erp_data.get("StructureName"),
            routing_id=erp_data.get("RoutingName"),
            metadata={
                "oracle_org_code": erp_data.get("OrganizationCode", ""),
                "oracle_work_order_type": erp_data.get("WorkOrderType", ""),
                "oracle_status": erp_data.get("WorkOrderStatusCode", ""),
                "oracle_work_order_id": erp_data.get("WorkOrderId", ""),
            },
        )

    def to_material(self, erp_data: dict[str, Any]) -> MaterialDefinitionDTO:
        """Map Oracle inventory item fields to MaterialDefinitionDTO."""
        return MaterialDefinitionDTO(
            code=erp_data.get("ItemNumber", ""),
            name=erp_data.get("Description", erp_data.get("ItemDescription", "")),
            material_type=_map_oracle_item_type(
                erp_data.get("ItemType", "STANDARD"),
            ),
            uom=erp_data.get("PrimaryUOMCode", "EA"),
            description=erp_data.get("LongDescription", erp_data.get("Description", "")),
            shelf_life_days=_safe_int(erp_data.get("ShelfLifeDays")),
            metadata={
                "oracle_item_class": erp_data.get("ItemClass", ""),
                "oracle_item_type": erp_data.get("ItemType", ""),
                "oracle_org_code": erp_data.get("OrganizationCode", ""),
                "oracle_item_id": erp_data.get("InventoryItemId", ""),
            },
        )

    def to_product(self, erp_data: dict[str, Any]) -> ProductDefinitionDTO:
        """Map Oracle item as a finished-good to ProductDefinitionDTO."""
        return ProductDefinitionDTO(
            code=erp_data.get("ItemNumber", ""),
            name=erp_data.get("Description", erp_data.get("ItemDescription", "")),
            product_type=_map_oracle_product_type(
                erp_data.get("ItemType", "STANDARD"),
            ),
            version=erp_data.get("RevisionCode", "1.0"),
            description=erp_data.get("LongDescription", erp_data.get("Description", "")),
            metadata={
                "oracle_item_type": erp_data.get("ItemType", ""),
                "oracle_item_status": erp_data.get("ItemStatus", ""),
            },
        )

    def to_bom(self, erp_data: dict[str, Any]) -> BillOfMaterialDTO:
        """Map Oracle item structure (BOM) header + components to BillOfMaterialDTO."""
        items = []
        for idx, component in enumerate(erp_data.get("Component", []), start=1):
            items.append(BOMItemDTO(
                material_code=component.get("ComponentItemNumber", component.get("ComponentItem", "")),
                quantity=float(component.get("ComponentQuantity", component.get("Quantity", 1))),
                uom=component.get("UOMCode", "EA"),
                sequence=int(component.get("ComponentSequenceNumber", idx)),
            ))
        return BillOfMaterialDTO(
            product_code=erp_data.get("ItemNumber", ""),
            version=erp_data.get("AlternateDesignator", "1"),
            items=items,
            metadata={
                "oracle_structure_name": erp_data.get("StructureName", ""),
                "oracle_structure_type": erp_data.get("StructureType", ""),
                "oracle_org_code": erp_data.get("OrganizationCode", ""),
            },
        )

    def to_routing(self, erp_data: dict[str, Any]) -> ProcessRouteDTO:
        """Map Oracle routing/operations to ProcessRouteDTO."""
        steps = []
        for operation in erp_data.get("Operation", []):
            steps.append(RouteStepDTO(
                sequence=int(operation.get("OperationSequenceNumber", operation.get("OperationSequence", 0))),
                name=operation.get("OperationName", operation.get("OperationDescription", "")),
                step_type=_map_oracle_operation_type(
                    operation.get("OperationType", ""),
                ),
                work_center_code=operation.get("WorkCenterName", operation.get("WorkCenter")),
                description=operation.get("OperationDescription", ""),
            ))
        return ProcessRouteDTO(
            product_code=erp_data.get("ItemNumber", ""),
            name=erp_data.get("RoutingName", erp_data.get("WorkOrderNumber", "")),
            version=erp_data.get("AlternateRoutingDesignator", "1"),
            steps=sorted(steps, key=lambda s: s.sequence),
            metadata={
                "oracle_routing_name": erp_data.get("RoutingName", ""),
                "oracle_org_code": erp_data.get("OrganizationCode", ""),
            },
        )

    def to_work_cell(self, erp_data: dict[str, Any]) -> WorkCellDTO:
        """Map Oracle work center to WorkCellDTO."""
        return WorkCellDTO(
            code=erp_data.get("WorkCenterName", erp_data.get("WorkCenter", "")),
            name=erp_data.get("Description", erp_data.get("WorkCenterDescription", "")),
            area_code=erp_data.get("OrganizationCode"),
            capabilities={
                "oracle_work_center_type": erp_data.get("WorkCenterType", ""),
                "oracle_resource_count": erp_data.get("ResourceCount", ""),
            },
        )

    # ── Outbound transforms ──────────────────────────────────────────

    def from_completion(self, report: CompletionReport) -> dict[str, Any]:
        """Transform CompletionReport into Oracle work order completion payload."""
        payload: dict[str, Any] = {
            "WorkOrderNumber": report.erp_reference,
            "OperationSequenceNumber": report.step_id or "10",
            "CompletedQuantity": report.qty_good,
            "RejectedQuantity": report.qty_reject,
            "UOMCode": report.uom,
            "TransactionType": "WIP_COMPLETION",
        }
        if report.completed_at:
            payload["TransactionDate"] = report.completed_at.strftime("%Y-%m-%dT%H:%M:%S")
        return payload

    def from_consumption(self, report: ConsumptionReport) -> dict[str, Any]:
        """Transform ConsumptionReport into Oracle material transaction payload."""
        items = []
        for mat in report.materials:
            items.append({
                "ItemNumber": mat.material_code,
                "TransactionQuantity": mat.quantity,
                "TransactionUOMCode": mat.uom,
                "LotNumber": mat.lot_number or "",
                "TransactionType": "WIP_ISSUE",
            })
        return {
            "WorkOrderNumber": report.erp_reference,
            "MaterialTransactions": items,
        }


# ── Helper functions ──────────────────────────────────────────────


def _parse_oracle_datetime(value: str | None) -> datetime | None:
    """Parse Oracle datetime strings (ISO 8601 format)."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _map_oracle_priority(oracle_priority: Any) -> int:
    """Map Oracle work order priority to MES 0-999 scale."""
    if oracle_priority is None:
        return 500
    mapping = {
        "1": 900,   # Critical
        "2": 700,   # High
        "3": 500,   # Medium (default)
        "4": 300,   # Low
        "5": 100,   # Lowest
    }
    return mapping.get(str(oracle_priority), 500)


def _map_oracle_item_type(oracle_type: str) -> str:
    """Map Oracle item type to MES material_type."""
    mapping = {
        "STANDARD": "raw",
        "RAW_MATERIAL": "raw",
        "SUBASSEMBLY": "semi",
        "FINISHED_GOOD": "finished",
        "PURCHASED": "raw",
        "EXPENSE": "consumable",
        "PHANTOM": "phantom",
    }
    return mapping.get(oracle_type, "raw")


def _map_oracle_product_type(oracle_type: str) -> str:
    """Map Oracle item type to MES product_type for finished goods."""
    mapping = {
        "STANDARD": "discrete",
        "FINISHED_GOOD": "discrete",
        "SUBASSEMBLY": "semi_finished",
        "MODEL": "configurable",
        "PROCESS": "process",
    }
    return mapping.get(oracle_type, "discrete")


def _map_oracle_operation_type(operation_type: str) -> str:
    """Map Oracle operation type to MES step_type."""
    op = operation_type.upper() if operation_type else ""
    if "INSPECTION" in op or "QUALITY" in op:
        return "inspection"
    if "MAINTENANCE" in op:
        return "maintenance"
    return "production"


def _safe_int(value: Any) -> int | None:
    """Safely convert a value to int, returning None on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
