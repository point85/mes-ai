"""
QUAL-MGMT: SQLAlchemy models for quality management.

Entities:
- QualityTest:   A test definition linked to a route step
- TestResult:    A recorded result of a quality test on a unit or lot
- NonConformance: A defect or out-of-spec condition requiring disposition
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mes.framework.db import BaseModel


class QualityTest(BaseModel):
    """
    A quality test definition that can be executed at a route step.

    test_type values:
        inline      — performed on the production line without removing the unit
        offline     — performed at a separate quality station
        destructive — destroys the tested sample (lot sampling only)
    """

    __tablename__ = "quality_tests"

    name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True,
    )
    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True,
        comment="Unique test code",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="inline",
        comment="Test type: inline, offline, destructive",
    )
    step_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("route_steps.id"),
        nullable=True, index=True,
        comment="Optional route step where this test is performed",
    )
    parameters: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="JSON describing test parameters, criteria, and tolerances",
    )

    # ── Relationships ───────────────────────────────────────────────
    results: Mapped[list["TestResult"]] = relationship(
        "TestResult", back_populates="test", cascade="all, delete-orphan",
        order_by="TestResult.tested_at.desc()",
    )

    def __repr__(self) -> str:
        return (
            f"<QualityTest id={self.id} code={self.code} "
            f"type={self.test_type}>"
        )


class TestResult(BaseModel):
    """
    A recorded result of a quality test execution.

    result values: pass, fail
    """

    __tablename__ = "test_results"

    test_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("quality_tests.id"),
        nullable=False, index=True,
    )
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("units.id"),
        nullable=True, index=True,
        comment="Unit tested (null if lot-level test)",
    )
    lot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("lots.id"),
        nullable=True, index=True,
        comment="Lot tested (null if unit-level test)",
    )
    result: Mapped[str] = mapped_column(
        String(10), nullable=False,
        comment="Test result: pass, fail",
    )
    measured_values: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="JSON of measured values (e.g. {\"dimension_a\": 10.5})",
    )
    operator_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"),
        nullable=True, index=True,
    )
    equipment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("equipment.id"),
        nullable=True, index=True,
        comment="Test equipment used",
    )
    tested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="When the test was performed",
    )
    tested_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
        comment="When the test was performed (UTC)",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ───────────────────────────────────────────────
    test: Mapped["QualityTest"] = relationship(
        "QualityTest", back_populates="results",
    )

    def __repr__(self) -> str:
        return (
            f"<TestResult id={self.id} test_id={self.test_id} "
            f"result={self.result}>"
        )


class NonConformance(BaseModel):
    """
    A non-conformance record for a quality issue on a unit or lot.

    nc_type values:     defect, out_of_spec, other
    disposition values: rework, scrap, use_as_is, return
    status values:      open, investigating, resolved, closed
    """

    __tablename__ = "non_conformances"

    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("units.id"),
        nullable=True, index=True,
    )
    lot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("lots.id"),
        nullable=True, index=True,
    )
    step_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("route_steps.id"),
        nullable=True, index=True,
        comment="Route step where the non-conformance was detected",
    )
    nc_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="Non-conformance type: defect, out_of_spec, other",
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Detailed description of the non-conformance",
    )
    disposition: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="Disposition: rework, scrap, use_as_is, return (null until resolved)",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open",
        comment="Workflow status: open, investigating, resolved, closed",
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )
    resolved_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
    )
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<NonConformance id={self.id} type={self.nc_type} "
            f"status={self.status}>"
        )
