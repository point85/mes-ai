"""
ERP Adapter: Data Transfer Objects.

Canonical DTOs for ERP ↔ MES data exchange. These are ERP-neutral;
the ERPTransformLayer maps between vendor-specific formats and these DTOs.

Per ARCHITECTURE.md §9.2.4 and §9.2.10 (ISA-95 / B2MML alignment).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Inbound DTOs (ERP → MES) ──────────────────────────────────────────────

class ProductionOrderDTO(BaseModel):
    """Production order received from ERP."""

    erp_reference: str = Field(..., description="ERP-native order identifier")
    product_code: str = Field(..., description="Product/material code")
    quantity_ordered: int = Field(..., gt=0)
    planned_start: datetime | None = None
    planned_end: datetime | None = None
    priority: int = Field(default=500, ge=0, le=999)
    uom: str = Field(default="EA", description="Unit of measure symbol")
    bom_id: str | None = None
    routing_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class MaterialDefinitionDTO(BaseModel):
    """Material master record from ERP."""

    code: str
    name: str
    material_type: str = "raw"
    uom: str = "EA"
    description: str = ""
    shelf_life_days: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProductDefinitionDTO(BaseModel):
    """Product/item master from ERP."""

    code: str
    name: str
    product_type: str = "discrete"
    version: str = "1.0"
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class BillOfMaterialDTO(BaseModel):
    """BOM header + items from ERP."""

    product_code: str
    version: str = "1.0"
    items: list[BOMItemDTO] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BOMItemDTO(BaseModel):
    """Single BOM line item."""

    material_code: str
    quantity: float = Field(..., gt=0)
    uom: str = "EA"
    sequence: int = 1


class ProcessRouteDTO(BaseModel):
    """Process route/routing from ERP."""

    product_code: str
    name: str
    version: str = "1.0"
    steps: list[RouteStepDTO] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RouteStepDTO(BaseModel):
    """Single routing step/operation."""

    sequence: int = Field(..., ge=1)
    name: str
    step_type: str = "production"
    work_center_code: str | None = None
    description: str = ""


class WorkCellDTO(BaseModel):
    """Work cell/resource definition from ERP."""

    code: str
    name: str
    area_code: str | None = None
    capabilities: dict[str, Any] = Field(default_factory=dict)


# ── Outbound DTOs (MES → ERP) ─────────────────────────────────────────────

class ERPConfirmation(BaseModel):
    """Response from ERP after an outbound report."""

    success: bool
    erp_doc_number: str | None = None
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompletionReport(BaseModel):
    """Production completion report sent to ERP."""

    erp_reference: str
    qty_good: int = Field(..., ge=0)
    qty_reject: int = Field(default=0, ge=0)
    uom: str = "EA"
    step_id: str | None = None
    completed_at: datetime | None = None


class ConsumptionReport(BaseModel):
    """Material consumption report sent to ERP."""

    erp_reference: str
    materials: list[MaterialConsumptionDTO]


class MaterialConsumptionDTO(BaseModel):
    """Single material consumption line."""

    material_code: str
    quantity: float = Field(..., gt=0)
    uom: str = "EA"
    lot_number: str | None = None


class ScrapReport(BaseModel):
    """Scrap report sent to ERP."""

    erp_reference: str
    qty_scrapped: int = Field(..., gt=0)
    reason_code: str
    uom: str = "EA"


class LaborReport(BaseModel):
    """Labor/time confirmation sent to ERP."""

    erp_reference: str
    operator_id: str
    duration_minutes: float = Field(..., gt=0)
    step_id: str | None = None


class DowntimeReport(BaseModel):
    """Equipment downtime report sent to ERP."""

    equipment_id: str
    duration_minutes: float = Field(..., gt=0)
    reason_code: str
    started_at: datetime


class QualityResultReport(BaseModel):
    """Quality test result sent to ERP."""

    erp_reference: str
    test_id: str
    result: str
    details: dict[str, Any] = Field(default_factory=dict)


# Resolve forward reference for BillOfMaterialDTO.items
BillOfMaterialDTO.model_rebuild()
