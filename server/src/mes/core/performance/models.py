"""
PERF-ANALYSIS: SQLAlchemy models for performance analysis.

Entities:
- Reason:              Hierarchical loss/downtime reason codes
- EquipmentStateModel: State machine definition (e.g. PackML, SEMI E10)
- EquipmentStateLog:   Time-series record of equipment state transitions
- ProductionCounter:   Shift-level production counts for OEE calculation
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from mes.framework.db import BaseModel


class Reason(BaseModel):
    """
    Hierarchical loss / downtime reason code.

    Reasons are organised in a tree (parent_id FK to self).  Each reason
    carries a short 4-character code and an OEE loss bucket so that manual
    state transitions automatically classify time for OEE calculation.

    Example hierarchy:
        1000 Electrical          (downtime_unplanned)
        ├─ 1010 AC Motors        (downtime_unplanned)
        │  └─ 1011 High temp     (downtime_unplanned)
        └─ 1020 DC Drives        (downtime_unplanned)
    """

    __tablename__ = "reasons"

    code: Mapped[str] = mapped_column(
        String(4), unique=True, nullable=False, index=True,
        comment="4-character reason code, e.g. '1000'",
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="Short descriptive name",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    oee_bucket: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="OEE loss bucket: downtime_planned, downtime_unplanned, uptime_non_value, etc.",
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("reasons.id"),
        nullable=True, index=True,
        comment="Parent reason for hierarchical grouping (null = top-level)",
    )

    def __repr__(self) -> str:
        return f"<Reason id={self.id} code={self.code} name={self.name}>"


class EquipmentStateModel(BaseModel):
    """
    A state machine definition that can be assigned to equipment.

    Registered by availability plugins (e.g. PackML, SEMI E10).
    When no state model is assigned, equipment is assumed to be
    100% available and running normally.

    states JSON schema:
        [{"name": "Execute", "display_name": "Executing",
          "dispatch_category": "busy", "oee_bucket": "uptime_value_add"}, ...]

    transitions JSON schema:
        [{"from_state": "Idle", "to_state": "Starting", "trigger": "start"}, ...]
    """

    __tablename__ = "equipment_state_models"

    model_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True,
        comment="Plugin identifier, e.g. 'packml', 'semi_e10'",
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="Human-friendly name, e.g. 'PackML (ISA-TR88)'",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    initial_state: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Name of the initial/default state",
    )
    states: Mapped[list] = mapped_column(
        JSON, nullable=False,
        comment="Array of state definitions with canonical mappings",
    )
    transitions: Mapped[list] = mapped_column(
        JSON, nullable=False,
        comment="Array of valid state transitions",
    )

    def __repr__(self) -> str:
        return f"<EquipmentStateModel id={self.id} model_id={self.model_id}>"


class EquipmentStateLog(BaseModel):
    """
    Time-series record of equipment state transitions.

    Every state (from any state model plugin) is mapped to both a canonical
    dispatch_category and an oee_bucket at write time for fast queries.

    dispatch_category values: available, busy, unavailable_planned, unavailable_unplanned
    oee_bucket values:        uptime_value_add, uptime_non_value, downtime_planned,
                              downtime_unplanned, excluded
    """

    __tablename__ = "equipment_state_logs"

    equipment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("equipment.id"),
        nullable=False, index=True,
    )
    state_model: Mapped[str] = mapped_column(
        String(50), nullable=False, default="default",
        comment="State model plugin ID (e.g. 'packml', 'semi_e10', 'oee_tpm')",
    )
    state: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Plugin-specific state name (e.g. 'Execute', 'Idle')",
    )
    sub_state: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="Optional sub-state within the state",
    )
    dispatch_category: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="Canonical dispatch category: available, busy, unavailable_planned, unavailable_unplanned",
    )
    oee_bucket: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="OEE bucket: uptime_value_add, uptime_non_value, downtime_planned, downtime_unplanned, excluded",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True,
        comment="When this state began",
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When this state ended (null = current state)",
    )
    started_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
        comment="When this state began (UTC)",
    )
    ended_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
        comment="When this state ended (UTC)",
    )
    reason_code: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="Optional reason code for the state change",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<EquipmentStateLog id={self.id} equip={self.equipment_id} "
            f"state={self.state} category={self.dispatch_category}>"
        )


class ProductionCounter(BaseModel):
    """
    Shift-level production counter for OEE Performance and Quality calculations.

    One row per equipment per order per shift_date. Counts are incremented
    as units complete processing at the equipment.
    """

    __tablename__ = "production_counters"

    equipment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("equipment.id"),
        nullable=False, index=True,
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("production_orders.id"),
        nullable=True, index=True,
    )
    shift_date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True,
        comment="The calendar date of the shift",
    )
    good_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    reject_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    rework_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    ideal_cycle_time_sec: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Ideal cycle time in seconds for this product/equipment combo",
    )
    actual_run_time_sec: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Actual productive run time in seconds for the shift",
    )

    def __repr__(self) -> str:
        return (
            f"<ProductionCounter id={self.id} equip={self.equipment_id} "
            f"date={self.shift_date} good={self.good_count}>"
        )
