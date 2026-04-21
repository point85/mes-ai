"""
MAT-MGMT: SQLAlchemy models for material management.

Entities:
- MaterialDefinition: A raw, intermediate, or finished material (item master)
- MaterialLot:        A specific lot/batch of a material with inventory quantity
- MaterialConsumption: A record of material consumed by a WIP unit/lot at a step
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mes.framework.db import BaseModel
from mes.core.uom.models import UnitOfMeasure  # noqa: F401 — needed for relationship


class MaterialDefinition(BaseModel):
    """
    A material that the factory uses, produces, or stores.

    material_type values:
        raw          — purchased raw material from suppliers
        intermediate — produced in-house and consumed downstream
        finished     — final product shipped to customers
        semi         — semi-finished (SAP HALB)
        consumable   — operating supplies (SAP HIBE)
        packaging    — packaging materials (SAP VERP)
        spare        — spare parts (SAP ERSA)
    """

    __tablename__ = "material_definitions"

    name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True,
    )
    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True,
        comment="Unique material code (SKU / part number)",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    material_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="raw",
        comment="Material type: raw, intermediate, finished, semi, consumable, packaging, spare",
    )
    uom: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("units_of_measure.symbol"),
        nullable=False,
        default="EA",
        comment="Default unit of measure — FK to units_of_measure.symbol",
    )
    revision: Mapped[str | None] = mapped_column(
        String(20), nullable=True, default=None,
        comment="Material revision level (e.g. Oracle RevisionCode). Null if ERP has no revisions.",
    )
    shelf_life_days: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Shelf life in days from receipt. Null means no expiry.",
    )

    # ── Relationships ───────────────────────────────────────────────
    unit_of_measure: Mapped["UnitOfMeasure"] = relationship(
        "UnitOfMeasure",
        foreign_keys=[uom],
        lazy="selectin",
    )
    lots: Mapped[list["MaterialLot"]] = relationship(
        "MaterialLot", back_populates="material", cascade="all, delete-orphan",
    )
    equipment_setups: Mapped[list["EquipmentMaterial"]] = relationship(
        "EquipmentMaterial", back_populates="material",
    )

    def __repr__(self) -> str:
        return (
            f"<MaterialDefinition id={self.id} code={self.code} "
            f"type={self.material_type}>"
        )


class MaterialLot(BaseModel):
    """
    A specific lot/batch of a material with tracked inventory.

    Status lifecycle:
        available — lot is in stock and available for consumption
        reserved  — lot is earmarked for a specific order (not yet consumed)
        consumed  — entire lot quantity has been consumed
        expired   — lot has passed its expiry date and is no longer usable
    """

    __tablename__ = "material_lots"

    material_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("material_definitions.id"),
        nullable=False, index=True,
    )
    lot_number: Mapped[str] = mapped_column(
        String(200), unique=True, nullable=False, index=True,
        comment="Unique lot identifier (supplier lot number or internal batch ID)",
    )
    quantity_on_hand: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Current quantity available",
    )
    quantity_reserved: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Quantity reserved for specific orders but not yet consumed",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="available",
        comment="Lot status: available, reserved, consumed, expired",
    )
    received_date: Mapped[date | None] = mapped_column(
        Date, nullable=True,
        comment="Date the lot was received into inventory",
    )
    expiry_date: Mapped[date | None] = mapped_column(
        Date, nullable=True,
        comment="Expiry date (auto-calculated from shelf_life_days if set)",
    )
    supplier: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Supplier name or identifier",
    )

    # ── Relationships ───────────────────────────────────────────────
    material: Mapped["MaterialDefinition"] = relationship(
        "MaterialDefinition", back_populates="lots",
    )
    consumptions: Mapped[list["MaterialConsumption"]] = relationship(
        "MaterialConsumption", back_populates="material_lot",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<MaterialLot id={self.id} lot_number={self.lot_number} "
            f"on_hand={self.quantity_on_hand} status={self.status}>"
        )


class MaterialConsumption(BaseModel):
    """
    A record of material consumed by a WIP unit or lot at a specific route step.
    Links the material lot to the WIP being produced, enabling genealogy/traceability.
    """

    __tablename__ = "material_consumptions"

    material_lot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("material_lots.id"),
        nullable=False, index=True,
    )
    unit_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("units.id"),
        nullable=True, index=True,
        comment="WIP unit that consumed this material (null if lot-based)",
    )
    lot_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("lots.id"),
        nullable=True, index=True,
        comment="WIP lot that consumed this material (null if unit-based)",
    )
    step_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("process_segments.id"),
        nullable=True, index=True,
        comment="Route step at which consumption occurred",
    )
    quantity_consumed: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Quantity of material consumed",
    )
    consumed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Timestamp when consumption was recorded",
    )
    consumed_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
        comment="Timestamp when consumption was recorded (UTC)",
    )

    # ── Relationships ───────────────────────────────────────────────
    material_lot: Mapped["MaterialLot"] = relationship(
        "MaterialLot", back_populates="consumptions",
    )

    def __repr__(self) -> str:
        return (
            f"<MaterialConsumption id={self.id} "
            f"lot={self.material_lot_id} qty={self.quantity_consumed}>"
        )
