"""
PERF-ANALYSIS: Pydantic schemas for the Performance Analysis REST API.

Create / Read / Update schemas for Reason, EquipmentStateModel,
EquipmentStateLog, ProductionCounter, plus OEE result schema.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
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
# Reason (hierarchical loss reason codes)
# ═══════════════════════════════════════════════════════════════════


class ReasonCreate(BaseModel):
    """Schema for creating a new reason."""

    code: str = Field(..., min_length=4, max_length=4, description="4-character reason code")
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    oee_bucket: str = Field(..., description="OEE loss bucket for this reason")
    parent_id: UUID | None = Field(None, description="Parent reason ID (null = top-level)")

    @field_validator("oee_bucket")
    @classmethod
    def validate_oee_bucket(cls, v: str) -> str:
        if v not in OEE_BUCKETS:
            raise ValueError(f"oee_bucket must be one of {OEE_BUCKETS}")
        return v


class ReasonUpdate(BaseModel):
    """Schema for updating an existing reason."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    oee_bucket: str | None = None
    parent_id: UUID | None = None

    @field_validator("oee_bucket")
    @classmethod
    def validate_oee_bucket(cls, v: str | None) -> str | None:
        if v is not None and v not in OEE_BUCKETS:
            raise ValueError(f"oee_bucket must be one of {OEE_BUCKETS}")
        return v


class ReasonRead(BaseModel):
    """Schema for reading a reason."""

    id: UUID
    code: str
    name: str
    description: str | None = None
    oee_bucket: str
    parent_id: UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════
# Equipment State Model (state machine definition)
# ═══════════════════════════════════════════════════════════════════


class StateDefinitionSchema(BaseModel):
    """Single state in a state model."""

    name: str = Field(..., min_length=1, max_length=50)
    display_name: str | None = None
    dispatch_category: str
    oee_bucket: str

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


class TransitionDefinitionSchema(BaseModel):
    """Valid transition between two states."""

    from_state: str = Field(..., min_length=1, max_length=50)
    to_state: str = Field(..., min_length=1, max_length=50)
    trigger: str | None = None


class EquipmentStateModelRead(BaseModel):
    """Schema for returning a state model definition."""

    id: UUID
    model_id: str
    name: str
    description: str | None = None
    initial_state: str
    states: list[dict[str, Any]]
    transitions: list[dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EquipmentTransitionRequest(BaseModel):
    """Schema for requesting a state transition on equipment."""

    new_state: str = Field(..., min_length=1, max_length=50)
    reason_code: str | None = None
    notes: str | None = None


class ManualTransitionRequest(BaseModel):
    """Schema for a manual (operator-initiated) state transition with a reason."""

    reason_id: UUID = Field(..., description="Reason code UUID to apply")
    notes: str | None = None


class EquipmentCurrentStateRead(BaseModel):
    """Schema for returning the current state of equipment (or default if no model)."""

    equipment_id: UUID
    state_model: str
    state: str
    dispatch_category: str
    oee_bucket: str
    started_at: datetime | None = None
    valid_transitions: list[dict[str, Any]] = Field(default_factory=list)


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


class CounterIncrementRequest(BaseModel):
    """Schema for atomically incrementing production counters (delta-based)."""

    equipment_id: UUID
    order_id: UUID | None = None
    good_delta: int = Field(0, ge=0, description="Good units to add")
    reject_delta: int = Field(0, ge=0, description="Rejected/defective units to add")
    rework_delta: int = Field(0, ge=0, description="Rework units to add")
    source: str = Field("manual", max_length=50, description="Data source (e.g. packml-opcua, mqtt-counter, manual)")


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
    six_big_losses: dict | None = None
