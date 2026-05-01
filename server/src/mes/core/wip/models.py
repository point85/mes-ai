"""
WIP-TRACK: SQLAlchemy models for work-in-process tracking.

Entities:
- Unit:        A discrete trackable item (identified by serial_number)
- Lot:         A batch of material processed together (identified by lot_number)
- SegmentResponseUnit: Processing record for a unit at a route step
- SegmentResponseLot:  Processing record for a lot at a route step
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mes.framework.db import BaseModel


class Unit(BaseModel):
    """
    A discrete work-in-process unit identified by a serial number.

    Status lifecycle:
        queued       — created and waiting for first step
        in_process   — actively being processed at a step
        completed    — finished all route steps successfully
        scrapped     — removed from production permanently
        on_hold      — temporarily held (e.g. quality issue)
    """

    __tablename__ = "units"

    serial_number: Mapped[str] = mapped_column(
        String(200), unique=True, nullable=False, index=True,
        comment="Unique serial number for the unit",
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("operations_requests.id"),
        nullable=False, index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("product_definitions.id"),
        nullable=False, index=True,
    )
    material_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("material_definitions.id"),
        nullable=True, index=True,
        comment="Output material produced by this unit. Used for dispatch capability matching.",
    )
    current_step_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("process_segments.id"),
        nullable=True, index=True,
        comment="The route step where the unit currently sits (null if completed or not started)",
    )
    current_equipment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("equipment.id"),
        nullable=True, index=True,
        comment="Equipment currently processing the unit (null if queued/completed)",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued",
        comment="Unit status: queued, in_process, completed, scrapped, on_hold",
    )
    scrap_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Free-text reason provided when unit was scrapped",
    )
    scrap_disposition: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="Disposition applied at scrap (e.g. rework, destroy, return)",
    )
    defect_code_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("defect_codes.id"),
        nullable=True, index=True,
        comment="Structured defect code from catalog — enables Pareto analysis",
    )
    scrapped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Timestamp when the unit was scrapped",
    )
    hold_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Reason the unit was placed on hold",
    )

    # ── Relationships ───────────────────────────────────────────────
    order: Mapped["OperationsRequest"] = relationship(  # noqa: F821
        "OperationsRequest", back_populates="units",
    )
    product: Mapped["ProductDefinition"] = relationship(  # noqa: F821
        "ProductDefinition", foreign_keys=[product_id],
    )
    material: Mapped["MaterialDefinition | None"] = relationship(  # noqa: F821
        "MaterialDefinition", foreign_keys=[material_id],
    )
    current_step: Mapped["ProcessSegment | None"] = relationship(  # noqa: F821
        "ProcessSegment", foreign_keys=[current_step_id], lazy="joined",
    )
    history: Mapped[list["SegmentResponseUnit"]] = relationship(
        "SegmentResponseUnit", back_populates="unit", cascade="all, delete-orphan",
        order_by="SegmentResponseUnit.entered_at",
    )

    @property
    def current_step_name(self) -> str | None:
        return self.current_step.name if self.current_step else None

    def __repr__(self) -> str:
        return f"<Unit id={self.id} sn={self.serial_number} status={self.status}>"


class Lot(BaseModel):
    """
    A batch of work-in-process material processed together.
    Uses the same status lifecycle as Unit.
    """

    __tablename__ = "lots"

    lot_number: Mapped[str] = mapped_column(
        String(200), unique=True, nullable=False, index=True,
        comment="Unique lot identifier",
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("operations_requests.id"),
        nullable=False, index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("product_definitions.id"),
        nullable=False, index=True,
    )
    material_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("material_definitions.id"),
        nullable=True, index=True,
        comment="Output material produced by this lot. Used for dispatch capability matching.",
    )
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Total quantity in this lot",
    )
    current_step_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("process_segments.id"),
        nullable=True, index=True,
    )
    current_equipment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("equipment.id"),
        nullable=True, index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued",
        comment="Lot status: queued, in_process, completed, scrapped, on_hold",
    )
    scrap_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Free-text reason provided when lot was scrapped",
    )
    scrap_disposition: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="Disposition applied at scrap (e.g. rework, destroy, return)",
    )
    defect_code_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("defect_codes.id"),
        nullable=True, index=True,
        comment="Structured defect code from catalog — enables Pareto analysis",
    )
    scrapped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Timestamp when the lot was scrapped",
    )
    hold_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Reason the lot was placed on hold",
    )

    # ── Relationships ───────────────────────────────────────────────
    order: Mapped["OperationsRequest"] = relationship(  # noqa: F821
        "OperationsRequest", back_populates="lots",
    )
    product: Mapped["ProductDefinition"] = relationship(  # noqa: F821
        "ProductDefinition", foreign_keys=[product_id],
    )
    material: Mapped["MaterialDefinition | None"] = relationship(  # noqa: F821
        "MaterialDefinition", foreign_keys=[material_id],
    )
    current_step: Mapped["ProcessSegment | None"] = relationship(  # noqa: F821
        "ProcessSegment", foreign_keys=[current_step_id], lazy="joined",
    )
    history: Mapped[list["SegmentResponseLot"]] = relationship(
        "SegmentResponseLot", back_populates="lot", cascade="all, delete-orphan",
        order_by="SegmentResponseLot.entered_at",
    )

    @property
    def current_step_name(self) -> str | None:
        return self.current_step.name if self.current_step else None

    def __repr__(self) -> str:
        return f"<Lot id={self.id} lot_number={self.lot_number} status={self.status}>"


class SegmentResponseUnit(BaseModel):
    """
    A processing record for a unit at a specific route step.
    Created when a unit enters a step; updated with exit time and result when it leaves.
    """

    __tablename__ = "segment_response_units"

    unit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("units.id"),
        nullable=False, index=True,
    )
    step_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("process_segments.id"),
        nullable=False, index=True,
    )
    equipment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("equipment.id"),
        nullable=True, index=True,
    )
    entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Timestamp when the unit entered this step",
    )
    exited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Timestamp when the unit left this step (null if still in-process)",
    )
    result: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="Step result: pass, fail, rework (null if still in-process)",
    )
    operator_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, nullable=True,
        comment="User ID of the operator (from AUTH module)",
    )
    data_snapshot: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="Freeform JSON snapshot of data collected at this step",
    )
    disposition: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Operator-selected disposition label at step completion",
    )
    failure_mode: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        comment="Free-text failure mode description when result=fail",
    )
    defect_code_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("defect_codes.id"),
        nullable=True, index=True,
        comment="Structured defect code — enables Pareto across steps",
    )
    scrap_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Scrap reason if the unit was scrapped at this step",
    )

    # ── UTC Timestamps ──────────────────────────────────────────────
    entered_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
        comment="Timestamp when the unit entered this step (UTC)",
    )
    exited_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
        comment="Timestamp when the unit left this step (UTC)",
    )

    # ── Relationships ───────────────────────────────────────────────
    unit: Mapped["Unit"] = relationship(
        "Unit", back_populates="history",
    )

    def __repr__(self) -> str:
        return (
            f"<SegmentResponseUnit id={self.id} unit_id={self.unit_id} "
            f"step_id={self.step_id} result={self.result}>"
        )


class SegmentResponseLot(BaseModel):
    """
    A processing record for a lot at a specific route step.
    Tracks quantity flow (in, out, scrapped) through each step.
    """

    __tablename__ = "segment_response_lots"

    lot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("lots.id"),
        nullable=False, index=True,
    )
    step_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("process_segments.id"),
        nullable=False, index=True,
    )
    equipment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("equipment.id"),
        nullable=True, index=True,
    )
    entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    exited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    entered_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
        comment="Timestamp when the lot entered this step (UTC)",
    )
    exited_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
        comment="Timestamp when the lot left this step (UTC)",
    )
    quantity_in: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Quantity entering this step",
    )
    quantity_out: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Quantity completing this step successfully",
    )
    quantity_scrapped: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Quantity scrapped at this step",
    )
    operator_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, nullable=True,
    )
    result: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="Step result: pass, fail, rework (null if still in-process)",
    )
    disposition: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Operator-selected disposition label at step completion",
    )
    failure_mode: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
        comment="Free-text failure mode description when result=fail",
    )
    defect_code_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("defect_codes.id"),
        nullable=True, index=True,
        comment="Structured defect code — enables Pareto across steps",
    )
    scrap_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Scrap reason if the lot was scrapped at this step",
    )

    # ── Relationships ───────────────────────────────────────────────
    lot: Mapped["Lot"] = relationship(
        "Lot", back_populates="history",
    )

    def __repr__(self) -> str:
        return (
            f"<SegmentResponseLot id={self.id} lot_id={self.lot_id} "
            f"step_id={self.step_id} qty_in={self.quantity_in}>"
        )



# ─────────────────────────────────────────────────────────────────
# ISA-95 Part 4 Resource Actuals (Phase 6 Step 6 scaffolds)
# ─────────────────────────────────────────────────────────────────
#
# MaterialActual, EquipmentActual, and PersonnelActual record what
# resources were actually used during execution of a process segment.
# Each actual is associated with a single Segment Response — either
# a SegmentResponseUnit or a SegmentResponseLot — via nullable
# foreign keys (exactly one of the two is expected to be set).
#
# Scaffold only — no services / routes / events are wired in Phase 6.
# Consumers land in later phases.


class MaterialActual(BaseModel):
    """
    ISA-95 Part 4 "Material Actual".

    Records material actually consumed or produced while executing a
    Process Segment. One row per (segment response, material lot / def)
    pair. Quantity sign convention: positive values for consumption,
    negative values for production (or use ``direction`` to disambiguate).
    """

    __tablename__ = "material_actuals"

    segment_response_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("segment_response_units.id"),
        nullable=True, index=True,
    )
    segment_response_lot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("segment_response_lots.id"),
        nullable=True, index=True,
    )
    material_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("material_definitions.id"),
        nullable=True, index=True,
        comment="Material definition consumed / produced.",
    )
    material_lot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, nullable=True, index=True,
        comment="Optional reference to a specific inbound MaterialLot (by id).",
    )
    direction: Mapped[str] = mapped_column(
        String(20), nullable=False, default="consumed",
        comment="'consumed' or 'produced'.",
    )
    quantity: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    uom: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="Unit of measure code (e.g. 'EA', 'KG').",
    )
    recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    recorded_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<MaterialActual id={self.id} material_id={self.material_id} "
            f"direction={self.direction} qty={self.quantity}>"
        )


class EquipmentActual(BaseModel):
    """
    ISA-95 Part 4 "Equipment Actual".

    Records which equipment actually executed a Process Segment, along
    with time-in/time-out and (optionally) the equipment state snapshot.
    """

    __tablename__ = "equipment_actuals"

    segment_response_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("segment_response_units.id"),
        nullable=True, index=True,
    )
    segment_response_lot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("segment_response_lots.id"),
        nullable=True, index=True,
    )
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("equipment.id"),
        nullable=False, index=True,
    )
    state: Mapped[str | None] = mapped_column(
        String(32), nullable=True,
        comment="Equipment state during the segment (e.g. 'running', 'idle').",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    started_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
    )
    ended_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<EquipmentActual id={self.id} equipment_id={self.equipment_id} "
            f"state={self.state}>"
        )


class PersonnelActual(BaseModel):
    """
    ISA-95 Part 4 "Personnel Actual".

    Records which operator(s) actually performed a Process Segment.

    The full ISA-95 Personnel entity is deferred (Step 2 skipped), so
    ``person_id`` is a bare UUID string with no FK. It is typically the
    AUTH user id of the operator who signed in at the workstation.
    """

    __tablename__ = "personnel_actuals"

    segment_response_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("segment_response_units.id"),
        nullable=True, index=True,
    )
    segment_response_lot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("segment_response_lots.id"),
        nullable=True, index=True,
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, index=True,
        comment="Operator user id (from AUTH module). No FK — Personnel entity deferred.",
    )
    role: Mapped[str | None] = mapped_column(
        String(64), nullable=True,
        comment="Operational role during the segment (e.g. 'operator', 'inspector').",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    started_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
    )
    ended_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<PersonnelActual id={self.id} person_id={self.person_id} "
            f"role={self.role}>"
        )
