"""
WIP-TRACK: Pydantic schemas for the WIP Tracking REST API.

Create / Read schemas for Unit, Lot, UnitHistory, LotHistory,
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
    """Schema for creating a new unit."""

    serial_number: str = Field(..., min_length=1, max_length=200)
    order_id: UUID
    product_id: UUID
    material_id: UUID | None = Field(None, description="Output material for dispatch capability matching")


class UnitRead(BaseModel):
    """Schema for returning a unit."""

    id: UUID
    serial_number: str
    order_id: UUID
    product_id: UUID
    material_id: UUID | None = None
    current_step_id: UUID | None = None
    current_equipment_id: UUID | None = None
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════
# LOT
# ═══════════════════════════════════════════════════════════════════


LOT_STATUSES = {"queued", "in_process", "completed", "scrapped", "on_hold"}


class LotCreate(BaseModel):
    """Schema for creating a new lot."""

    lot_number: str = Field(..., min_length=1, max_length=200)
    order_id: UUID
    product_id: UUID
    quantity: int = Field(..., gt=0)
    material_id: UUID | None = Field(None, description="Output material for dispatch capability matching")


class LotRead(BaseModel):
    """Schema for returning a lot."""

    id: UUID
    lot_number: str
    order_id: UUID
    product_id: UUID
    quantity: int
    material_id: UUID | None = None
    current_step_id: UUID | None = None
    current_equipment_id: UUID | None = None
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

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
    exited_at: datetime | None = None
    result: str | None = None
    operator_id: UUID | None = None
    data_snapshot: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LotHistoryRead(BaseModel):
    """Schema for returning a lot history record."""

    id: UUID
    lot_id: UUID
    step_id: UUID
    equipment_id: UUID | None = None
    entered_at: datetime
    exited_at: datetime | None = None
    quantity_in: int
    quantity_out: int
    quantity_scrapped: int
    operator_id: UUID | None = None
    created_at: datetime

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
    data_snapshot: dict | None = Field(None, description="Optional data collected at step")
    quantity_out: int | None = Field(None, gt=0, description="For lots: quantity completing step")
    quantity_scrapped: int | None = Field(None, ge=0, description="For lots: quantity scrapped at step")


class MoveRequest(BaseModel):
    """Request to move a unit/lot to a specific step (overrides routing engine)."""

    target_step_id: UUID | None = Field(
        None, description="Target step ID (null = use routing engine for next step)",
    )


class HoldRequest(BaseModel):
    """Request to place a unit/lot on hold."""

    reason: str = Field(..., min_length=1, max_length=500)


class ScrapRequest(BaseModel):
    """Request to scrap a unit."""

    reason: str = Field(..., min_length=1, max_length=500)
