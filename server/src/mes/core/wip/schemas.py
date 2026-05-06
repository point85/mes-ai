"""
WIP-TRACK: Pydantic schemas for the WIP Tracking REST API.

Create / Read schemas for Unit, Lot, SegmentResponseUnit, SegmentResponseLot,
plus action request schemas for WIP lifecycle operations.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════
# UNIT
# ═══════════════════════════════════════════════════════════════════


UNIT_STATUSES = {"queued", "in_process", "completed", "scrapped", "on_hold"}


class UnitCreate(BaseModel):
    """Schema for creating a new unit. If serial_number is omitted, it is auto-generated."""

    serial_number: str | None = Field(None, min_length=1, max_length=200, description="Omit for auto-generation")
    order_id: UUID
    product_id: UUID
    material_id: UUID | None = Field(None, description="Output material for dispatch capability matching")
    serial_template: str | None = Field(None, max_length=200, description="Template for auto-generation (e.g. 'SN-{order}-{seq:05d}')")


class UnitRead(BaseModel):
    """Schema for returning a unit."""

    id: UUID
    serial_number: str
    order_id: UUID
    product_id: UUID
    material_id: UUID | None = None
    current_step_id: UUID | None = None
    current_step_name: str | None = None
    current_equipment_id: UUID | None = None
    order_number: str | None = None
    status: str
    is_active: bool
    # RCA fields
    scrap_reason: str | None = None
    scrap_disposition: str | None = None

    scrapped_at: datetime | None = None
    hold_reason: str | None = None
    release_reason: str | None = None
    created_at: datetime
    created_at_utc: datetime | None = None
    updated_at: datetime
    updated_at_utc: datetime | None = None

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════
# LOT
# ═══════════════════════════════════════════════════════════════════


LOT_STATUSES = {"queued", "in_process", "completed", "scrapped", "on_hold"}


class LotCreate(BaseModel):
    """Schema for creating a new lot. If lot_number is omitted, it is auto-generated."""

    lot_number: str | None = Field(None, min_length=1, max_length=200, description="Omit for auto-generation")
    order_id: UUID
    product_id: UUID
    quantity: int = Field(..., gt=0)
    material_id: UUID | None = Field(None, description="Output material for dispatch capability matching")
    lot_template: str | None = Field(None, max_length=200, description="Template for auto-generation (e.g. 'LOT-{order}-{seq:04d}')")


class LotRead(BaseModel):
    """Schema for returning a lot."""

    id: UUID
    lot_number: str
    order_id: UUID
    product_id: UUID
    quantity: int
    material_id: UUID | None = None
    current_step_id: UUID | None = None
    current_step_name: str | None = None
    current_equipment_id: UUID | None = None
    order_number: str | None = None
    status: str
    is_active: bool
    uom_symbol: str | None = None
    # RCA fields
    scrap_reason: str | None = None
    scrap_disposition: str | None = None

    scrapped_at: datetime | None = None
    hold_reason: str | None = None
    release_reason: str | None = None
    created_at: datetime
    created_at_utc: datetime | None = None
    updated_at: datetime
    updated_at_utc: datetime | None = None

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════
# HISTORY
# ═══════════════════════════════════════════════════════════════════


class UnitHistoryRead(BaseModel):
    """Schema for returning a unit history record."""

    id: UUID
    unit_id: UUID
    step_id: UUID
    equipment_id: UUID | None = None
    entered_at: datetime
    entered_at_utc: datetime | None = None
    exited_at: datetime | None = None
    exited_at_utc: datetime | None = None
    result: str | None = None
    operator_id: UUID | None = None
    data_snapshot: dict | None = None
    # RCA fields
    disposition: str | None = None
    failure_mode: str | None = None
    scrap_reason: str | None = None
    created_at: datetime
    created_at_utc: datetime | None = None

    model_config = {"from_attributes": True}


class LotHistoryRead(BaseModel):
    """Schema for returning a lot history record."""

    id: UUID
    lot_id: UUID
    step_id: UUID
    equipment_id: UUID | None = None
    entered_at: datetime
    entered_at_utc: datetime | None = None
    exited_at: datetime | None = None
    exited_at_utc: datetime | None = None
    quantity_in: int
    quantity_out: int
    quantity_scrapped: int
    operator_id: UUID | None = None
    # RCA fields
    result: str | None = None
    disposition: str | None = None
    failure_mode: str | None = None
    scrap_reason: str | None = None
    created_at: datetime
    created_at_utc: datetime | None = None

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════
# ACTION REQUESTS
# ═══════════════════════════════════════════════════════════════════


class StartRequest(BaseModel):
    """Request to start processing a unit/lot at its current step."""

    equipment_id: UUID | None = Field(
        None, description="Equipment to process at (optional — uses current_equipment_id if set)",
    )


class CompleteRequest(BaseModel):
    """Request to complete processing at the current step."""

    result: str = Field("pass", description="Step result: pass, fail, rework")
    disposition: str | None = Field(
        None,
        max_length=100,
        description="Disposition name for routing (overrides result-based routing when set)",
    )
    data_snapshot: dict | None = Field(None, description="Optional data collected at step")
    quantity_out: int | None = Field(None, gt=0, description="For lots: quantity completing step")
    quantity_scrapped: int | None = Field(None, ge=0, description="For lots: quantity scrapped at step")
    # RCA fields
    failure_mode: str | None = Field(None, max_length=200, description="Short description of failure mode (for fail results)")


class MoveRequest(BaseModel):
    """Request to move a unit/lot to the next step.

    If target_step_id is set, it overrides the routing engine.
    Otherwise the routing engine evaluates transitions using result/disposition.
    """

    target_step_id: UUID | None = Field(
        None, description="Target step ID (null = use routing engine for next step)",
    )
    result: str | None = Field(
        None,
        pattern=r"^(pass|fail|rework)$",
        description="Step result for conditional routing (auto-read from history if omitted)",
    )
    disposition: str | None = Field(
        None,
        max_length=255,
        description="Operator disposition label for MRB steps (must match a transition label)",
    )


class HoldRequest(BaseModel):
    """Request to place a unit/lot on hold."""

    reason: str = Field(..., min_length=1, max_length=500)


class ReleaseHoldRequest(BaseModel):
    """Request to release a unit/lot from hold."""

    reason: str = Field(..., min_length=1, max_length=500, description="Release disposition / reason selected from the catalog")


class ScrapRequest(BaseModel):
    """Request to scrap a unit or lot."""

    reason: str = Field(..., min_length=1, max_length=500)
    disposition: str | None = Field(None, max_length=100, description="Scrap disposition (e.g. 'rework', 'discard', 'return-to-supplier')")
    failure_mode: str | None = Field(None, max_length=200, description="Short description of the failure mode")
