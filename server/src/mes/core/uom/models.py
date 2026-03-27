"""
UOM: SQLAlchemy model for units of measure.

Each unit belongs to a uom_type (mass, time, length, temperature, volume, count, …).
Conversion to/from the type's base unit uses an affine formula:
    base_value = value * multiplier + offset

Rate UoMs (uom_type="rate") are composite: they reference a numerator UoM and
a denominator UoM.  For example "EA/h" (each per hour) references EA (count)
as numerator and h (time) as denominator.  Conversion between rate UoMs is
done by independently converting the numerator and denominator parts.
"""

from __future__ import annotations

import uuid as _uuid

from sqlalchemy import Float, ForeignKey, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mes.framework.db import BaseModel


class UnitOfMeasure(BaseModel):
    """
    A unit of measure with conversion parameters relative to its type's base unit.

    The base unit for each type has multiplier=1.0 and offset=0.0.
    For the four SI fundamental types the base units are:
        mass → kg, time → s, length → m, temperature → K.
    For derived or custom types the user designates one unit as the base.

    Rate UoMs (uom_type="rate") are composite: numerator_uom / denominator_uom.
    """

    __tablename__ = "units_of_measure"

    symbol: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True,
        comment="Short symbol, e.g. 'kg', 'lb', 'case'",
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Human-friendly name, e.g. 'kilogram'",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Optional longer description",
    )
    uom_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="Dimension type: mass, time, length, temperature, volume, count, rate, …",
    )

    # ── Affine conversion parameters ────────────────────────────────
    # base_value = value * multiplier + offset
    multiplier: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0,
        comment="Multiplier relative to the type's base unit",
    )
    offset: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Offset for affine conversions (used by temperature)",
    )

    # ── Rate UoM composition (self-referential) ─────────────────────
    numerator_uom_id: Mapped[_uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units_of_measure.id"),
        nullable=True,
        comment="For rate UoMs: the numerator unit (e.g. EA in EA/h)",
    )
    denominator_uom_id: Mapped[_uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units_of_measure.id"),
        nullable=True,
        comment="For rate UoMs: the denominator unit (e.g. h in EA/h)",
    )

    numerator_uom: Mapped[UnitOfMeasure | None] = relationship(
        "UnitOfMeasure",
        foreign_keys=[numerator_uom_id],
        lazy="joined",
    )
    denominator_uom: Mapped[UnitOfMeasure | None] = relationship(
        "UnitOfMeasure",
        foreign_keys=[denominator_uom_id],
        lazy="joined",
    )

    # ── Metadata ────────────────────────────────────────────────────
    is_builtin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True for seed/out-of-the-box units — prevents deletion",
    )

    @property
    def is_rate(self) -> bool:
        """True when this UoM is a composed rate (numerator / denominator)."""
        return self.numerator_uom_id is not None and self.denominator_uom_id is not None

    @property
    def numerator_uom_symbol(self) -> str | None:
        """Convenience: symbol of the numerator unit, if this is a rate."""
        return self.numerator_uom.symbol if self.numerator_uom else None

    @property
    def denominator_uom_symbol(self) -> str | None:
        """Convenience: symbol of the denominator unit, if this is a rate."""
        return self.denominator_uom.symbol if self.denominator_uom else None

    def __repr__(self) -> str:
        return f"<UnitOfMeasure symbol={self.symbol} type={self.uom_type}>"
