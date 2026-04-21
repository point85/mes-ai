"""
PROD-ORDER: Pydantic schemas for the Production Order REST API.

Create / Read / Update schemas for OperationsRequest, plus action schemas
for release and complete transitions.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# ── Valid status values and transitions ──────────────────────────────

ORDER_STATUSES = {"created", "released", "in_progress", "completed", "closed"}

# Allowed transitions: current_status → {allowed next statuses}
ORDER_TRANSITIONS = {
    "created": {"released", "closed"},
    "released": {"in_progress", "closed"},
    "in_progress": {"completed", "closed"},
    "completed": {"closed"},
    "closed": set(),
}


# ── CRUD schemas ─────────────────────────────────────────────────────


class OrderCreate(BaseModel):
    """Schema for creating a new production order."""

    order_number: str = Field(..., min_length=1, max_length=100)
    product_id: UUID
    route_id: UUID | None = None
    quantity_ordered: int = Field(..., gt=0)
    priority: int = Field(0, ge=0)
    planned_start: datetime | None = None
    planned_end: datetime | None = None
    erp_reference: str | None = None
    notes: str | None = None


class OrderRead(BaseModel):
    """Schema for returning a production order."""

    id: UUID
    order_number: str
    product_id: UUID
    route_id: UUID | None = None
    quantity_ordered: int
    quantity_completed: int
    quantity_scrapped: int
    status: str
    priority: int
    planned_start: datetime | None = None
    planned_start_utc: datetime | None = None
    planned_end: datetime | None = None
    planned_end_utc: datetime | None = None
    actual_start: datetime | None = None
    actual_start_utc: datetime | None = None
    actual_end: datetime | None = None
    actual_end_utc: datetime | None = None
    erp_reference: str | None = None
    notes: str | None = None
    is_active: bool
    created_at: datetime
    created_at_utc: datetime | None = None
    updated_at: datetime
    updated_at_utc: datetime | None = None

    model_config = {"from_attributes": True}


class OrderUpdate(BaseModel):
    """Schema for updating a production order. All fields optional."""

    order_number: str | None = Field(None, min_length=1, max_length=100)
    product_id: UUID | None = None
    route_id: UUID | None = None
    quantity_ordered: int | None = Field(None, gt=0)
    priority: int | None = Field(None, ge=0)
    planned_start: datetime | None = None
    planned_end: datetime | None = None
    erp_reference: str | None = None
    notes: str | None = None


# ── Action schemas ───────────────────────────────────────────────────


class OrderReleaseRequest(BaseModel):
    """Optional body when releasing an order."""

    notes: str | None = None


class OrderCompleteRequest(BaseModel):
    """Optional body when completing an order."""

    notes: str | None = None
