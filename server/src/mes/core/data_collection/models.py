"""
DATA-COLLECT: SQLAlchemy models for data collection.

Entities:
- DataDefinition: What data to collect at a route step (template)
- DataPoint:      An actual collected value for a WIP unit or lot
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mes.framework.db import BaseModel
from mes.core.uom.models import UnitOfMeasure  # noqa: F401 — needed for FK


class DataDefinition(BaseModel):
    """
    A definition of data to be collected at a route step.

    Defines the name, code, expected data type, source, and whether the
    collection is mandatory before the step can be completed.

    data_type values:
        numeric  — floating-point measurement (stored in DataPoint.value_numeric)
        string   — free-text value (stored in DataPoint.value_string)
        boolean  — true/false flag (stored in DataPoint.value_boolean)
        enum     — one of a set of allowed values (stored in DataPoint.value_string)

    source values:
        manual    — entered by an operator
        equipment — collected automatically from equipment/PLC
        sensor    — collected from an IoT sensor
    """

    __tablename__ = "data_definitions"

    name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True,
    )
    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True,
        comment="Unique definition code (e.g. TEMP-OVEN-1, TORQUE-BOLT-A)",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="numeric",
        comment="Expected data type: numeric, string, boolean, enum",
    )
    uom: Mapped[str | None] = mapped_column(
        String(20),
        ForeignKey("units_of_measure.symbol"),
        nullable=True,
        comment="Unit of measure — FK to units_of_measure.symbol",
    )
    step_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("route_steps.id"),
        nullable=True, index=True,
        comment="Route step where this data is collected (null = any step)",
    )
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="manual",
        comment="Data source: manual, equipment, sensor",
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="If true, this data point must be collected before step completion",
    )
    enum_values: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Comma-separated allowed values when data_type='enum'",
    )
    lower_limit: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Lower acceptable limit for numeric values",
    )
    upper_limit: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Upper acceptable limit for numeric values",
    )

    # ── Relationships ───────────────────────────────────────────────
    data_points: Mapped[list["DataPoint"]] = relationship(
        "DataPoint", back_populates="definition", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<DataDefinition id={self.id} code={self.code} "
            f"type={self.data_type} source={self.source}>"
        )


class DataPoint(BaseModel):
    """
    An actual data value collected for a WIP unit or lot.

    The value is stored in the column matching the definition's data_type:
    - numeric  → value_numeric
    - string   → value_string
    - boolean  → value_boolean
    - enum     → value_string (validated against DataDefinition.enum_values)
    """

    __tablename__ = "data_points"

    definition_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("data_definitions.id"),
        nullable=False, index=True,
    )
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("units.id"),
        nullable=True, index=True,
        comment="WIP unit this data was collected for (null if lot-based)",
    )
    lot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("lots.id"),
        nullable=True, index=True,
        comment="WIP lot this data was collected for (null if unit-based)",
    )
    value_numeric: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Collected value when data_type='numeric'",
    )
    value_string: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Collected value when data_type='string' or 'enum'",
    )
    value_boolean: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True,
        comment="Collected value when data_type='boolean'",
    )
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Timestamp when the data was collected",
    )
    collected_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
        comment="Timestamp when the data was collected (UTC)",
    )
    source_equipment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("equipment.id"),
        nullable=True, index=True,
        comment="Equipment that produced this data (null if manual entry)",
    )
    operator_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"),
        nullable=True, index=True,
        comment="Operator who entered/confirmed this data",
    )

    # ── Relationships ───────────────────────────────────────────────
    definition: Mapped["DataDefinition"] = relationship(
        "DataDefinition", back_populates="data_points",
    )

    def __repr__(self) -> str:
        val = self.value_numeric or self.value_string or self.value_boolean
        return (
            f"<DataPoint id={self.id} def={self.definition_id} "
            f"value={val}>"
        )
