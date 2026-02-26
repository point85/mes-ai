"""
DISPATCH: Pydantic schemas for the Dispatching Engine REST API.

Schemas for dispatch evaluation, execution, and strategy listing.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── Valid constants ──────────────────────────────────────────────────

DISPATCH_STRATEGIES = {
    "manual",
    "first_available",
    "shortest_queue",
    "round_robin",
    "capability_match",
}


# ═══════════════════════════════════════════════════════════════════
# Dispatch Request / Response
# ═══════════════════════════════════════════════════════════════════


class DispatchEvaluateRequest(BaseModel):
    """Schema for evaluating dispatch options for a unit or lot."""

    unit_id: UUID | None = None
    lot_id: UUID | None = None
    strategy: str = Field("first_available", description="Dispatch strategy to use")

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        if v not in DISPATCH_STRATEGIES:
            raise ValueError(f"strategy must be one of {DISPATCH_STRATEGIES}")
        return v


class DispatchOption(BaseModel):
    """A single dispatch destination option."""

    equipment_id: UUID
    equipment_code: str
    equipment_name: str
    work_center_id: UUID
    work_center_code: str
    step_id: UUID
    step_name: str | None = None
    queue_depth: int = 0
    score: float = 0.0
    reason: str | None = None


class DispatchEvaluateResponse(BaseModel):
    """Response from dispatch evaluation — list of options ranked by strategy."""

    unit_id: UUID | None = None
    lot_id: UUID | None = None
    strategy: str
    options: list[DispatchOption] = []
    recommended: DispatchOption | None = None


class DispatchExecuteRequest(BaseModel):
    """Schema for executing a dispatch decision."""

    unit_id: UUID | None = None
    lot_id: UUID | None = None
    destination_equipment_id: UUID
    destination_step_id: UUID


class DispatchExecuteResponse(BaseModel):
    """Response from dispatch execution."""

    unit_id: UUID | None = None
    lot_id: UUID | None = None
    destination_equipment_id: UUID
    destination_step_id: UUID
    dispatched_at: datetime


class DispatchStrategyInfo(BaseModel):
    """Information about an available dispatch strategy."""

    name: str
    description: str
    strategy_type: str = "built-in"


class DispatchQueueItem(BaseModel):
    """An item in the dispatch queue for a work center."""

    unit_id: UUID | None = None
    lot_id: UUID | None = None
    serial_number: str | None = None
    lot_number: str | None = None
    order_id: UUID | None = None
    current_step_id: UUID | None = None
    status: str
    equipment_id: UUID | None = None
