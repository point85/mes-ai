"""
SAP S/4HANA: Transform layer.

Maps between SAP-specific field names and the MES canonical DTOs.

SAP uses German-origin abbreviations for many fields:
  AUFNR → Manufacturing Order Number
  MATNR → Material Number
  WERKS → Plant
  LGORT → Storage Location
  ARBPL → Work Center
  VORNR → Operation/Activity Number
  STLNR → BOM Number

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
from mes.adapters.erp.uom_mapping import normalize_erp_uom


class SAPS4HANATransformLayer(ERPTransformLayer):
    """
    SAP S/4HANA field mapping.

    Inbound: SAP JSON → MES DTO
    Outbound: MES report → SAP-formatted payload
    """

    # ── Inbound transforms ──────────────────────────────────────────

    def to_production_order(self, erp_data: dict[str, Any]) -> ProductionOrderDTO:
        """Map SAP production order fields to ProductionOrderDTO."""
        return ProductionOrderDTO(
            erp_reference=erp_data.get("ManufacturingOrder", erp_data.get("AUFNR", "")),
            product_code=erp_data.get("Material", erp_data.get("MATNR", "")),
            quantity_ordered=int(erp_data.get("TotalQuantity", erp_data.get("GAMNG", 0))),
            planned_start=_parse_sap_datetime(
                erp_data.get("MfgOrderPlannedStartDate", erp_data.get("GSTRP")),
            ),
            planned_end=_parse_sap_datetime(
                erp_data.get("MfgOrderPlannedEndDate", erp_data.get("GLTRP")),
            ),
            priority=_map_sap_priority(erp_data.get("MfgOrderPriority", "2")),
            uom=normalize_erp_uom(erp_data.get("ProductionUnit", erp_data.get("GMEIN", "EA"))),
            bom_id=erp_data.get("BillOfMaterial", erp_data.get("STLNR")),
            routing_id=erp_data.get("ProductionRouting", erp_data.get("PLNNR")),
            metadata={
                "sap_plant": erp_data.get("ProductionPlant", erp_data.get("WERKS", "")),
                "sap_order_type": erp_data.get("ManufacturingOrderType", erp_data.get("AUART", "")),
                "sap_status": erp_data.get("MfgOrderStatus", ""),
                "sap_mrp_controller": erp_data.get("MRPController", ""),
            },
        )

    def to_material(self, erp_data: dict[str, Any]) -> MaterialDefinitionDTO:
        """Map SAP material master fields to MaterialDefinitionDTO."""
        return MaterialDefinitionDTO(
            code=erp_data.get("Material", erp_data.get("MATNR", "")),
            name=erp_data.get("MaterialName", erp_data.get("MAKTX", "")),
            material_type=_map_sap_material_type(
                erp_data.get("MaterialType", erp_data.get("MTART", "ROH")),
            ),
            uom=normalize_erp_uom(
                erp_data.get("BaseUnit", erp_data.get("MEINS", "EA")),
            ),
            revision=erp_data.get("MaterialRevisionLevel"),
            description=erp_data.get("MaterialDescription", erp_data.get("MAKTX", "")),
            shelf_life_days=_safe_int(erp_data.get("MaximumStoragePeriod")),
            metadata={
                "sap_material_group": erp_data.get("MaterialGroup", erp_data.get("MATKL", "")),
                "sap_material_type": erp_data.get("MaterialType", erp_data.get("MTART", "")),
                "sap_plant": erp_data.get("Plant", erp_data.get("WERKS", "")),
            },
        )

    def to_product(self, erp_data: dict[str, Any]) -> ProductDefinitionDTO:
        """Map SAP product/material as a finished-good to ProductDefinitionDTO."""
        return ProductDefinitionDTO(
            code=erp_data.get("Product", erp_data.get("MATNR", "")),
            name=erp_data.get("ProductDescription", erp_data.get("MAKTX", "")),
            product_type=_map_sap_product_type(
                erp_data.get("MaterialType", erp_data.get("MTART", "FERT")),
            ),
            version=erp_data.get("MaterialRevisionLevel", "1.0"),
            description=erp_data.get("ProductDescription", erp_data.get("MAKTX", "")),
            metadata={
                "sap_material_type": erp_data.get("MaterialType", erp_data.get("MTART", "")),
                "sap_industry_sector": erp_data.get("IndustrySector", ""),
            },
        )

    def to_bom(self, erp_data: dict[str, Any]) -> BillOfMaterialDTO:
        """Map SAP BOM header + items to BillOfMaterialDTO."""
        items = []
        for idx, sap_item in enumerate(erp_data.get("to_BOMItem", []), start=1):
            items.append(BOMItemDTO(
                material_code=sap_item.get("BillOfMaterialComponent", sap_item.get("IDNRK", "")),
                quantity=float(sap_item.get("BillOfMaterialItemQuantity", sap_item.get("MENGE", 1))),
                uom=normalize_erp_uom(sap_item.get("BillOfMaterialItemUnit", sap_item.get("MEINS", "EA"))),
                sequence=int(sap_item.get("BillOfMaterialItemNumber", idx)),
            ))
        return BillOfMaterialDTO(
            product_code=erp_data.get("Material", erp_data.get("MATNR", "")),
            version=erp_data.get("BillOfMaterialVariant", "1"),
            items=items,
            metadata={
                "sap_bom_number": erp_data.get("BillOfMaterial", erp_data.get("STLNR", "")),
                "sap_bom_usage": erp_data.get("BillOfMaterialVariantUsage", ""),
            },
        )

    def to_routing(self, erp_data: dict[str, Any]) -> ProcessRouteDTO:
        """Map SAP routing header + operations to ProcessRouteDTO."""
        steps = []
        for sap_op in erp_data.get("to_Operation", []):
            steps.append(RouteStepDTO(
                sequence=int(sap_op.get("OperationNumber", sap_op.get("VORNR", 0))),
                name=sap_op.get("OperationText", sap_op.get("LTXA1", "")),
                step_type=_map_sap_activity_type(
                    sap_op.get("OperationControlProfile", ""),
                ),
                work_center_code=sap_op.get("WorkCenter", sap_op.get("ARBPL")),
                description=sap_op.get("OperationText", ""),
            ))
        return ProcessRouteDTO(
            product_code=erp_data.get("Material", erp_data.get("MATNR", "")),
            name=erp_data.get("ProductionRoutingGroup", erp_data.get("PLNNR", "")),
            version=erp_data.get("ProductionRoutingGroupCounter", "1"),
            steps=sorted(steps, key=lambda s: s.sequence),
            metadata={
                "sap_routing_number": erp_data.get("ProductionRoutingGroup", ""),
                "sap_plant": erp_data.get("Plant", ""),
            },
        )

    def to_work_cell(self, erp_data: dict[str, Any]) -> WorkCellDTO:
        """Map SAP work center to WorkCellDTO."""
        return WorkCellDTO(
            code=erp_data.get("WorkCenter", erp_data.get("ARBPL", "")),
            name=erp_data.get("WorkCenterText", erp_data.get("KTEXT", "")),
            area_code=erp_data.get("Plant", erp_data.get("WERKS")),
            capabilities={
                "sap_category": erp_data.get("WorkCenterCategoryCode", ""),
                "sap_capacity": erp_data.get("Capacity", ""),
            },
        )

    # ── Outbound transforms ──────────────────────────────────────────

    def from_completion(self, report: CompletionReport) -> dict[str, Any]:
        """Transform CompletionReport into SAP confirmation payload."""
        payload: dict[str, Any] = {
            "OrderID": report.erp_reference,
            "OrderOperation": report.step_id or "0010",
            "ConfirmationYieldQuantity": str(report.qty_good),
            "ConfirmationScrapQuantity": str(report.qty_reject),
            "ConfirmationUnit": report.uom,
            "IsFinalConfirmation": False,
        }
        if report.completed_at:
            payload["PostingDate"] = report.completed_at.strftime("%Y-%m-%dT%H:%M:%S")
        return payload

    def from_consumption(self, report: ConsumptionReport) -> dict[str, Any]:
        """Transform ConsumptionReport into SAP goods movement payload."""
        items = []
        for mat in report.materials:
            items.append({
                "Material": mat.material_code,
                "Quantity": str(mat.quantity),
                "EntryUnit": mat.uom,
                "Batch": mat.lot_number or "",
                "GoodsMovementType": "261",  # SAP: goods issue for production order
            })
        return {
            "OrderID": report.erp_reference,
            "GoodsMovementItems": items,
        }


# ── Helper functions ──────────────────────────────────────────────


def _parse_sap_datetime(value: str | None) -> datetime | None:
    """Parse SAP datetime strings (ISO 8601 or /Date(epoch)/ format)."""
    if not value:
        return None
    # OData V4 uses ISO 8601
    if "T" in str(value):
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    # Legacy /Date(1234567890000)/ format
    if "/Date(" in str(value):
        try:
            ms = int(str(value).split("(")[1].split(")")[0].split("+")[0].split("-")[0])
            return datetime.fromtimestamp(ms / 1000.0)  # noqa: DTZ006
        except (ValueError, IndexError):
            return None
    return None


def _map_sap_priority(sap_priority: str) -> int:
    """Map SAP priority code to MES 0-999 scale."""
    mapping = {
        "1": 900,  # Very high
        "2": 700,  # High
        "3": 500,  # Medium (default)
        "4": 300,  # Low
        "5": 100,  # Very low
    }
    return mapping.get(str(sap_priority), 500)


def _map_sap_material_type(sap_type: str) -> str:
    """Map SAP material type (MTART) to MES material_type."""
    mapping = {
        "ROH": "raw",        # Raw material
        "HALB": "semi",      # Semi-finished
        "FERT": "finished",  # Finished product
        "HIBE": "consumable",  # Operating supplies
        "VERP": "packaging",   # Packaging
        "ERSA": "spare",       # Spare parts
    }
    return mapping.get(sap_type, "raw")


def _map_sap_product_type(sap_type: str) -> str:
    """Map SAP material type to MES product_type for finished goods."""
    mapping = {
        "FERT": "discrete",
        "HALB": "semi_finished",
        "KMAT": "configurable",
        "PROC": "process",
    }
    return mapping.get(sap_type, "discrete")


def _map_sap_activity_type(control_profile: str) -> str:
    """Map SAP operation control profile to MES step_type."""
    # Simplified mapping — SAP has many control profiles
    if control_profile.startswith("PP"):
        return "production"
    if control_profile.startswith("QM"):
        return "inspection"
    if control_profile.startswith("PM"):
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
