"""
UOM: SQLAlchemy model for units of measure.

Each unit belongs to a uom_type (mass, time, length, temperature, volume, count, …).
Conversion to/from the type's base unit uses an affine formula:
    base_value = value * multiplier + offset
"""

from __future__ import annotations

from sqlalchemy import Float, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from mes.framework.db import BaseModel


class UnitOfMeasure(BaseModel):
    """
    A unit of measure with conversion parameters relative to its type's base unit.

    The base unit for each type has multiplier=1.0 and offset=0.0.
    For the four SI fundamental types the base units are:
        mass → kg, time → s, length → m, temperature → K.
    For derived or custom types the user designates one unit as the base.
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
        comment="Dimension type: mass, time, length, temperature, volume, count, …",
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

    # ── Metadata ────────────────────────────────────────────────────
    is_builtin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True for seed/out-of-the-box units — prevents deletion",
    )

    def __repr__(self) -> str:
        return f"<UnitOfMeasure symbol={self.symbol} type={self.uom_type}>"
