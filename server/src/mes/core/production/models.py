"""
PROD-ORDER: SQLAlchemy model for production orders.

A production order instructs the factory to manufacture a given quantity
of a product.  Orders follow a status lifecycle:
    created → released → in_progress → completed → closed
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mes.framework.db import BaseModel


class ProductionOrder(BaseModel):
    """
    A production order — the instruction to manufacture a product quantity.

    Status lifecycle:
        created   — order exists but is not yet released to the floor
        released  — order is available for production (units/lots can be created)
        in_progress — at least one unit/lot has started processing
        completed — all ordered quantity has been produced or scrapped
        closed    — order is finalized and no further changes are allowed
    """

    __tablename__ = "production_orders"

    order_number: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True,
        comment="Business-visible order number (may come from ERP)",
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("product_definitions.id"),
        nullable=False, index=True,
    )
    route_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("process_routes.id"),
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
    route: Mapped["ProcessRoute | None"] = relationship(  # noqa: F821
        "ProcessRoute", foreign_keys=[route_id],
    )
    units: Mapped[list["Unit"]] = relationship(  # noqa: F821
        "Unit", back_populates="order", cascade="all, delete-orphan",
    )
    lots: Mapped[list["Lot"]] = relationship(  # noqa: F821
        "Lot", back_populates="order", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<ProductionOrder id={self.id} "
            f"order_number={self.order_number} status={self.status}>"
        )
