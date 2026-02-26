"""
PERF-ANALYSIS: Pydantic schemas for the Performance Analysis REST API.

Create / Read / Update schemas for EquipmentStateLog, ProductionCounter,
plus OEE result schema.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── Valid constants ──────────────────────────────────────────────────

DISPATCH_CATEGORIES = {
    "available",
    "busy",
    "unavailable_planned",
    "unavailable_unplanned",
}

OEE_BUCKETS = {
    "uptime_value_add",
    "uptime_non_value",
    "downtime_planned",
    "downtime_unplanned",
    "excluded",
}


# ═══════════════════════════════════════════════════════════════════
# EquipmentStateLog
# ═══════════════════════════════════════════════════════════════════


class StateChangeRequest(BaseModel):
    """Schema for recording an equipment state change."""

    equipment_id: UUID
    state_model: str = Field("default", min_length=1, max_length=50)
    state: str = Field(..., min_length=1, max_length=50)
    sub_state: str | None = None
    dispatch_category: str = Field(..., description="available, busy, unavailable_planned, unavailable_unplanned")
    oee_bucket: str = Field(..., description="uptime_value_add, uptime_non_value, downtime_planned, downtime_unplanned, excluded")
    started_at: datetime
    reason_code: str | None = None
    notes: str | None = None

    @field_validator("dispatch_category")
    @classmethod
    def validate_dispatch_category(cls, v: str) -> str:
        if v not in DISPATCH_CATEGORIES:
            raise ValueError(f"dispatch_category must be one of {DISPATCH_CATEGORIES}")
        return v

    @field_validator("oee_bucket")
    @classmethod
    def validate_oee_bucket(cls, v: str) -> str:
        if v not in OEE_BUCKETS:
            raise ValueError(f"oee_bucket must be one of {OEE_BUCKETS}")
        return v


class EquipmentStateLogRead(BaseModel):
    """Schema for returning an equipment state log entry."""

    id: UUID
    equipment_id: UUID
    state_model: str
    state: str
    sub_state: str | None = None
    dispatch_category: str
    oee_bucket: str
    started_at: datetime
    ended_at: datetime | None = None
    reason_code: str | None = None
    notes: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════
# ProductionCounter
# ═══════════════════════════════════════════════════════════════════


class CounterCreateUpdate(BaseModel):
    """Schema for creating or upserting a production counter."""

    equipment_id: UUID
    order_id: UUID | None = None
    shift_date: date
    good_count: int = Field(0, ge=0)
    reject_count: int = Field(0, ge=0)
    rework_count: int = Field(0, ge=0)
    ideal_cycle_time_sec: float | None = Field(None, gt=0)
    actual_run_time_sec: float | None = Field(None, ge=0)


class ProductionCounterRead(BaseModel):
    """Schema for returning a production counter."""

    id: UUID
    equipment_id: UUID
    order_id: UUID | None = None
    shift_date: date
    good_count: int
    reject_count: int
    rework_count: int
    ideal_cycle_time_sec: float | None = None
    actual_run_time_sec: float | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════
# OEE Result
# ═══════════════════════════════════════════════════════════════════


class OEEResult(BaseModel):
    """Schema for an OEE calculation result."""

    equipment_id: UUID
    period_start: datetime
    period_end: datetime
    availability: float = Field(..., ge=0, le=1, description="0.0 – 1.0")
    performance: float = Field(..., ge=0, description="0.0 – 1.0+")
    quality: float = Field(..., ge=0, le=1, description="0.0 – 1.0")
    oee: float = Field(..., ge=0, description="availability × performance × quality")
    details: dict | None = None
