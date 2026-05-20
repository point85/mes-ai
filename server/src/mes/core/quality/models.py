"""
QUAL-MGMT: SQLAlchemy models for quality management.

Entities:
- QualityTest:      A defined quality test (inline, offline, or destructive)
- TestResult:       A recorded result for a quality test against a unit or lot
- NonConformance:   A non-conformance report against a unit or lot
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mes.framework.db import BaseModel


class QualityTest(BaseModel):
    """
    A defined quality test that can be assigned to a route step.

    test_type: inline, offline, or destructive
    """

    __tablename__ = "quality_tests"

    name: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="Human-readable test name",
    )
    code: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True,
        comment="Unique short code for the test (no spaces)",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="inline",
        comment="Test type: inline, offline, or destructive",
    )
    step_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("process_segments.id"),
        nullable=True, index=True,
        comment="Route step this test is assigned to (null = unassigned)",
    )
    parameters: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="Test parameters (tolerances, specifications, etc.)",
    )

    # Relationships
    results: Mapped[list["TestResult"]] = relationship(
        "TestResult", back_populates="test", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<QualityTest id={self.id} code={self.code} test_type={self.test_type}>"


class TestResult(BaseModel):
    """A recorded result for a quality test against a unit or lot."""

    __tablename__ = "test_results"

    test_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("quality_tests.id"),
        nullable=False, index=True,
    )
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, nullable=True, index=True,
        comment="WIP unit tested (null for lot testing)",
    )
    lot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, nullable=True, index=True,
        comment="WIP lot tested (null for unit testing)",
    )
    result: Mapped[str] = mapped_column(
        String(10), nullable=False,
        comment="Test outcome: pass or fail",
    )
    measured_values: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="Measured values recorded during the test",
    )
    operator_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    equipment_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    tested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Timestamp when the test was performed",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    test: Mapped["QualityTest"] = relationship("QualityTest", back_populates="results")

    def __repr__(self) -> str:
        return f"<TestResult id={self.id} test_id={self.test_id} result={self.result}>"


class NonConformance(BaseModel):
    """A non-conformance report against a unit or lot."""

    __tablename__ = "non_conformances"

    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, nullable=True, index=True,
        comment="WIP unit with the non-conformance (null for lot-level NC)",
    )
    lot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, nullable=True, index=True,
        comment="WIP lot with the non-conformance (null for unit-level NC)",
    )
    step_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, nullable=True,
        comment="Route step where the NC was detected",
    )
    nc_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="Non-conformance type: defect, out_of_spec, or other",
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Description of the non-conformance",
    )
    disposition: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="Disposition applied: rework, scrap, use_as_is, or return",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="open",
        comment="NC status: open, investigating, resolved, or closed",
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Timestamp when the NC was resolved",
    )
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    def __repr__(self) -> str:
        return f"<NonConformance id={self.id} nc_type={self.nc_type} status={self.status}>"
