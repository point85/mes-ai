"""
OPS-REQUEST / OPS-SCHEDULE / OPS-RESPONSE: SQLAlchemy models for ISA-95 Part 3
Operations Management objects.

Entities:
- OperationsRequest  (was ProductionOrder): ISA-95 Part 3 "Operations Request" —
                     a directive to manufacture a given quantity of a product.
                     Status lifecycle: created → released → in_progress → completed → closed.
- OperationsSchedule (new): ISA-95 Part 3 "Operations Schedule" — groups one or
                     more Operations Requests into a dispatchable schedule
                     window. Scaffolded in Phase 6; consumers land in later
                     phases.
- OperationsResponse (new): ISA-95 Part 3 "Operations Response" — the
                     as-performed aggregate record for a completed Operations
                     Request. Scaffolded in Phase 6; consumers land in later
                     phases.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mes.framework.db import BaseModel


class OperationsRequest(BaseModel):
    """
    A production order — the instruction to manufacture a product quantity.

    Status lifecycle:
        created   — order exists but is not yet released to the floor
        released  — order is available for production (units/lots can be created)
        in_progress — at least one unit/lot has started processing
        completed — all ordered quantity has been produced or scrapped
        closed    — order is finalized and no further changes are allowed
    """

    __tablename__ = "operations_requests"

    order_number: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True,
        comment="Business-visible order number (may come from ERP)",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("product_definitions.id"),
        nullable=False, index=True,
    )
    route_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("operations_definitions.id"),
        nullable=True, index=True,
        comment="Assigned process route; null means use product's default route",
    )

    quantity_ordered: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Total quantity to produce",
    )
    quantity_completed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Quantity successfully completed",
    )
    quantity_scrapped: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Quantity scrapped during production",
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="created",
        comment="Order status: created, released, in_progress, completed, closed",
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Priority (higher = more urgent). 0 = normal.",
    )

    # ── Dates ───────────────────────────────────────────────────────
    planned_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    planned_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    actual_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    actual_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # ── UTC Timestamps ──────────────────────────────────────────────
    planned_start_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
    )
    planned_end_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
    )
    actual_start_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
    )
    actual_end_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
    )

    erp_reference: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="External reference from ERP system",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ───────────────────────────────────────────────
    product: Mapped["ProductDefinition"] = relationship(  # noqa: F821
        "ProductDefinition", foreign_keys=[product_id],
    )
    route: Mapped["OperationsDefinition | None"] = relationship(  # noqa: F821
        "OperationsDefinition", foreign_keys=[route_id],
    )
    units: Mapped[list["Unit"]] = relationship(  # noqa: F821
        "Unit", back_populates="order", cascade="all, delete-orphan",
    )
    lots: Mapped[list["Lot"]] = relationship(  # noqa: F821
        "Lot", back_populates="order", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<OperationsRequest id={self.id} "
            f"order_number={self.order_number} status={self.status}>"
        )


class OperationsSchedule(BaseModel):
    """
    ISA-95 Part 3 "Operations Schedule".

    Groups one or more ``OperationsRequest`` rows into a dispatchable schedule
    window (e.g. a shift, day, or campaign). Scaffold only — no services /
    routes / events are wired in Phase 6. The linkage from Operations Request
    to Schedule will be added as a nullable FK (``schedule_id``) in a later
    phase once consumers exist.
    """

    __tablename__ = "operations_schedules"

    code: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True,
        comment="Business-visible schedule code (e.g. 'SHIFT-2026-04-21-A')",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft",
        comment="Schedule status: draft, released, active, closed",
    )
    planned_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    planned_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    planned_start_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
    )
    planned_end_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
    )

    def __repr__(self) -> str:
        return f"<OperationsSchedule id={self.id} code={self.code} status={self.status}>"


class OperationsResponse(BaseModel):
    """
    ISA-95 Part 3 "Operations Response".

    The as-performed aggregate record for a completed ``OperationsRequest``.
    Composed of the Segment Responses (``SegmentResponseUnit`` /
    ``SegmentResponseLot``) and Resource Actuals (``MaterialActual``,
    ``EquipmentActual``, ``PersonnelActual``) gathered during execution.

    Scaffold only — no services / routes / events are wired in Phase 6.
    A single Operations Response typically corresponds to a single Operations
    Request; this is modeled as a nullable FK so Phase 6 migrations remain
    additive.
    """

    __tablename__ = "operations_responses"

    operations_request_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("operations_requests.id"),
        nullable=True, index=True,
        comment="The Operations Request that this response summarizes.",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open",
        comment="Response status: open, closed",
    )
    quantity_completed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Total good quantity produced across all segment responses.",
    )
    quantity_scrapped: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Total scrapped quantity across all segment responses.",
    )
    actual_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    actual_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    actual_start_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
    )
    actual_end_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    operations_request: Mapped["OperationsRequest | None"] = relationship(
        "OperationsRequest", foreign_keys=[operations_request_id],
    )

    def __repr__(self) -> str:
        return (
            f"<OperationsResponse id={self.id} "
            f"req_id={self.operations_request_id} status={self.status}>"
        )
