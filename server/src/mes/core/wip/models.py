"""
WIP-TRACK: SQLAlchemy models for work-in-process tracking.

Entities:
- Unit:        A discrete trackable item (identified by serial_number)
- Lot:         A batch of material processed together (identified by lot_number)
- UnitHistory: Processing record for a unit at a route step
- LotHistory:  Processing record for a lot at a route step
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
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
        UUID(as_uuid=True), ForeignKey("production_orders.id"),
        nullable=False, index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_definitions.id"),
        nullable=False, index=True,
    )
    current_step_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("route_steps.id"),
        nullable=True, index=True,
        comment="The route step where the unit currently sits (null if completed or not started)",
    )
    current_equipment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment.id"),
        nullable=True, index=True,
        comment="Equipment currently processing the unit (null if queued/completed)",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued",
        comment="Unit status: queued, in_process, completed, scrapped, on_hold",
    )

    # ── Relationships ───────────────────────────────────────────────
    order: Mapped["ProductionOrder"] = relationship(  # noqa: F821
        "ProductionOrder", back_populates="units",
    )
    product: Mapped["ProductDefinition"] = relationship(  # noqa: F821
        "ProductDefinition", foreign_keys=[product_id],
    )
    history: Mapped[list["UnitHistory"]] = relationship(
        "UnitHistory", back_populates="unit", cascade="all, delete-orphan",
        order_by="UnitHistory.entered_at",
    )

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
        UUID(as_uuid=True), ForeignKey("production_orders.id"),
        nullable=False, index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_definitions.id"),
        nullable=False, index=True,
    )
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Total quantity in this lot",
    )
    current_step_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("route_steps.id"),
        nullable=True, index=True,
    )
    current_equipment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment.id"),
        nullable=True, index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="queued",
        comment="Lot status: queued, in_process, completed, scrapped, on_hold",
    )

    # ── Relationships ───────────────────────────────────────────────
    order: Mapped["ProductionOrder"] = relationship(  # noqa: F821
        "ProductionOrder", back_populates="lots",
    )
    product: Mapped["ProductDefinition"] = relationship(  # noqa: F821
        "ProductDefinition", foreign_keys=[product_id],
    )
    history: Mapped[list["LotHistory"]] = relationship(
        "LotHistory", back_populates="lot", cascade="all, delete-orphan",
        order_by="LotHistory.entered_at",
    )

    def __repr__(self) -> str:
        return f"<Lot id={self.id} lot_number={self.lot_number} status={self.status}>"


class UnitHistory(BaseModel):
    """
    A processing record for a unit at a specific route step.
    Created when a unit enters a step; updated with exit time and result when it leaves.
    """

    __tablename__ = "unit_history"

    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("units.id"),
        nullable=False, index=True,
    )
    step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("route_steps.id"),
        nullable=False, index=True,
    )
    equipment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment.id"),
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
        UUID(as_uuid=True), nullable=True,
        comment="User ID of the operator (from AUTH module)",
    )
    data_snapshot: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="Freeform JSON snapshot of data collected at this step",
    )

    # ── Relationships ───────────────────────────────────────────────
    unit: Mapped["Unit"] = relationship(
        "Unit", back_populates="history",
    )

    def __repr__(self) -> str:
        return (
            f"<UnitHistory id={self.id} unit_id={self.unit_id} "
            f"step_id={self.step_id} result={self.result}>"
        )


class LotHistory(BaseModel):
    """
    A processing record for a lot at a specific route step.
    Tracks quantity flow (in, out, scrapped) through each step.
    """

    __tablename__ = "lot_history"

    lot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lots.id"),
        nullable=False, index=True,
    )
    step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("route_steps.id"),
        nullable=False, index=True,
    )
    equipment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("equipment.id"),
        nullable=True, index=True,
    )
    entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    exited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
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
        UUID(as_uuid=True), nullable=True,
    )

    # ── Relationships ───────────────────────────────────────────────
    lot: Mapped["Lot"] = relationship(
        "Lot", back_populates="history",
    )

    def __repr__(self) -> str:
        return (
            f"<LotHistory id={self.id} lot_id={self.lot_id} "
            f"step_id={self.step_id} qty_in={self.quantity_in}>"
        )
