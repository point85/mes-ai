"""
INVENTORY: SQLAlchemy models for inventory management.

Entities:
- StorageLocation:      A warehouse location identified by aisle, bay, and tier
- InventoryBalance:     Current quantity of a material lot at a storage location
- InventoryTransaction: Audit trail for all inventory movements
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, Uuid, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mes.framework.db import BaseModel
from mes.core.physical_model.models import Site  # noqa: F401 — needed for relationship
from mes.core.material.models import MaterialLot  # noqa: F401 — needed for relationship
from mes.core.uom.models import UnitOfMeasure  # noqa: F401 — needed for relationship


class StorageLocation(BaseModel):
    """
    A physical warehouse location where material can be stored.

    location_type values:
        receiving  — inbound dock where goods are received
        storage    — warehouse racking identified by aisle/bay/tier
        rip        — raw and in-process staging near production
        staging    — general staging / marshalling area
        shipping   — outbound dock for finished goods
    """

    __tablename__ = "storage_locations"
    __table_args__ = (
        Index("ix_storage_locations_code", "code", unique=True, postgresql_where=text("is_active = TRUE")),
    )

    name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True,
    )
    code: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Unique location code (e.g. RECV-01, A-03-B-02)",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="storage",
        comment="Location type: receiving, storage, rip, staging, shipping",
    )
    aisle: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="Aisle identifier (for storage locations)",
    )
    bay: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="Bay identifier within the aisle",
    )
    tier: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="Tier/shelf level within the bay",
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("sites.id"),
        nullable=True, index=True,
        comment="Site this location belongs to",
    )
    capacity: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Maximum storage capacity (in base UoM of stored material)",
    )
    capacity_uom_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("units_of_measure.id"),
        nullable=True,
        comment="Unit of measure for the capacity value",
    )

    # ── Relationships ───────────────────────────────────────────────
    site: Mapped["Site | None"] = relationship(
        "Site", lazy="selectin",
    )
    capacity_uom_rel: Mapped["UnitOfMeasure | None"] = relationship(
        "UnitOfMeasure", foreign_keys=[capacity_uom_id], lazy="selectin",
    )

    @property
    def capacity_uom_symbol(self) -> str | None:
        return self.capacity_uom_rel.symbol if self.capacity_uom_rel else None
    balances: Mapped[list["InventoryBalance"]] = relationship(
        "InventoryBalance", back_populates="location",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<StorageLocation id={self.id} code={self.code} "
            f"type={self.location_type}>"
        )


class InventoryBalance(BaseModel):
    """
    Current quantity of a material lot at a specific storage location.

    This is the denormalised view of inventory — the sum of all transactions
    for this (lot, location) pair should equal quantity_on_hand.  The balance
    is updated transactionally by the InventoryService on every movement.
    """

    __tablename__ = "inventory_balances"
    __table_args__ = (
        UniqueConstraint(
            "material_lot_id", "location_id",
            name="uq_inventory_balance_lot_location",
        ),
    )

    material_lot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("material_lots.id"),
        nullable=False, index=True,
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("storage_locations.id"),
        nullable=False, index=True,
    )
    quantity_on_hand: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Current quantity at this location",
    )
    quantity_reserved: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
        comment="Quantity reserved for picking / orders",
    )

    # ── Relationships ───────────────────────────────────────────────
    material_lot: Mapped["MaterialLot"] = relationship(
        "MaterialLot", lazy="selectin",
    )
    location: Mapped["StorageLocation"] = relationship(
        "StorageLocation", back_populates="balances", lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<InventoryBalance lot={self.material_lot_id} "
            f"location={self.location_id} qty={self.quantity_on_hand}>"
        )


class InventoryTransaction(BaseModel):
    """
    An immutable audit record of an inventory movement.

    transaction_type values:
        receive   — goods received from supplier into a receiving location
        putaway   — moved from receiving to a storage location (aisle/bay/tier)
        pick      — removed from storage for production use
        move      — transferred between locations (e.g. storage → RIP)
        consume   — consumed by WIP (links to MaterialConsumption)
        adjust    — manual inventory adjustment (count correction)
    """

    __tablename__ = "inventory_transactions"

    transaction_type: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True,
        comment="Transaction type: receive, putaway, pick, move, consume, adjust",
    )
    material_lot_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("material_lots.id"),
        nullable=False, index=True,
    )
    from_location_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("storage_locations.id"),
        nullable=True, index=True,
        comment="Source location (null for receives)",
    )
    to_location_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("storage_locations.id"),
        nullable=True, index=True,
        comment="Destination location (null for consumes)",
    )
    quantity: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Quantity moved (positive = into to_location)",
    )
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, nullable=True,
        comment="Optional FK to operations_request, unit, or lot for traceability",
    )
    reference_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True,
        comment="Type of reference: operations_request, unit, lot",
    )
    reason: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Reason or note for the transaction",
    )
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="When the transaction was performed",
    )
    performed_at_utc: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True,
        comment="When the transaction was performed (UTC naive)",
    )

    # ── Relationships ───────────────────────────────────────────────
    material_lot: Mapped["MaterialLot"] = relationship(
        "MaterialLot", lazy="selectin",
    )
    from_location: Mapped["StorageLocation | None"] = relationship(
        "StorageLocation", foreign_keys=[from_location_id], lazy="selectin",
    )
    to_location: Mapped["StorageLocation | None"] = relationship(
        "StorageLocation", foreign_keys=[to_location_id], lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<InventoryTransaction id={self.id} type={self.transaction_type} "
            f"lot={self.material_lot_id} qty={self.quantity}>"
        )
