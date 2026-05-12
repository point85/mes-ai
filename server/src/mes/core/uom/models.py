"""
UOM: SQLAlchemy model for units of measure.

Seven physical types (the seven SI base quantities plus 'other' for discrete counts):
    mass, length, time, temperature, electrical, amount_of_substance, luminous_intensity, other

Four classes:
    scalar   — single unit with affine conversion  (y = a·x + b)
    quotient — two scalar units divided            (e.g. kg/s)
    product  — two scalar units multiplied         (e.g. kg·m)
    power    — scalar unit raised to an exponent   (e.g. m³ = m^3)

Affine formula (scalar / left/right components):
    base_value = value * multiplier + offset

Composite UoMs store their components via left_uom_id (numerator/first/base)
and right_uom_id (denominator/second — not used for power).
"""

from __future__ import annotations

import uuid as _uuid

from sqlalchemy import Float, ForeignKey, Integer, String, Text, Boolean, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mes.framework.db import BaseModel

# Valid UoM types and classes
UOM_TYPES = {"mass", "length", "time", "temperature", "electrical", "amount_of_substance", "luminous_intensity", "other"}
UOM_CLASSES = {"scalar", "quotient", "product", "power"}


class UnitOfMeasure(BaseModel):
    """
    A unit of measure.

    The base unit for each scalar type has multiplier=1.0 and offset=0.0:
        mass → kg, time → s, length → m, temperature → K, other → EA

    Composite UoMs reference component units via left_uom_id / right_uom_id.
    Power UoMs also store an integer exponent.
    """

    __tablename__ = "units_of_measure"

    symbol: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True,
        comment="Short symbol, e.g. 'kg', 'lb', 'm³'",
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
        comment="Dimension type of the primary component: mass, length, time, temperature, electrical, amount_of_substance, luminous_intensity, other",
    )
    uom_class: Mapped[str] = mapped_column(
        String(20), nullable=False, default="scalar",
        comment="UoM class: scalar, quotient, product, power",
    )

    # ── Affine conversion parameters (scalar class) ──────────────────
    # base_value = value * multiplier + offset
    multiplier: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0,
        comment="Multiplier relative to the type's base unit (scalar class)",
    )
    offset: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Offset for affine conversions, e.g. temperature (scalar class)",
    )

    # ── Composite UoM components (self-referential) ──────────────────
    # left_uom_id  = numerator (quotient) / first factor (product) / base (power)
    # right_uom_id = denominator (quotient) / second factor (product) / unused (power)
    left_uom_id: Mapped[_uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("units_of_measure.id"),
        nullable=True,
        comment="Left component: numerator (quotient), first factor (product), base (power)",
    )
    right_uom_id: Mapped[_uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("units_of_measure.id"),
        nullable=True,
        comment="Right component: denominator (quotient), second factor (product)",
    )
    exponent: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Integer exponent for power-class UoMs (e.g. 3 for cubic meters)",
    )

    left_uom: Mapped[UnitOfMeasure | None] = relationship(
        "UnitOfMeasure",
        foreign_keys=[left_uom_id],
        remote_side="UnitOfMeasure.id",
        lazy="selectin",
    )
    right_uom: Mapped[UnitOfMeasure | None] = relationship(
        "UnitOfMeasure",
        foreign_keys=[right_uom_id],
        remote_side="UnitOfMeasure.id",
        lazy="selectin",
    )

    # ── Metadata ────────────────────────────────────────────────────
    is_builtin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="True for seed/out-of-the-box units — prevents deletion",
    )

    # ── Convenience properties ───────────────────────────────────────

    @property
    def is_composite(self) -> bool:
        """True for quotient, product, or power classes."""
        return self.uom_class in ("quotient", "product", "power")

    @property
    def left_uom_symbol(self) -> str | None:
        if self.left_uom_id is None:
            return None
        return self.left_uom.symbol if self.left_uom else None

    @property
    def left_uom_type(self) -> str | None:
        if self.left_uom_id is None:
            return None
        return self.left_uom.uom_type if self.left_uom else None

    @property
    def right_uom_symbol(self) -> str | None:
        if self.right_uom_id is None:
            return None
        return self.right_uom.symbol if self.right_uom else None

    @property
    def right_uom_type(self) -> str | None:
        if self.right_uom_id is None:
            return None
        return self.right_uom.uom_type if self.right_uom else None

    def __repr__(self) -> str:
        return f"<UnitOfMeasure symbol={self.symbol} type={self.uom_type} class={self.uom_class}>"
