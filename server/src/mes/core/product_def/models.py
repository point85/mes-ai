"""
PROD-DEF: SQLAlchemy models for the product definition domain.

Entities:
- ProductDefinition: A product that can be manufactured (item master)
- BillOfMaterial:    BOM header — ties a product to its material requirements
- BOMItem:           BOM line item — a single material requirement with quantity
- ProcessRoute:      A manufacturing route (sequence of steps) for a product
- RouteStep:         An individual step/operation within a route
- StepParameter:     A data parameter spec attached to a route step

Route steps reference work cells from PHYS-MODEL and will later
reference MaterialDefinition from MAT-MGMT.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mes.framework.db import BaseModel
from mes.core.uom.models import UnitOfMeasure  # noqa: F401 — needed for relationships


class ProductDefinition(BaseModel):
    """
    A product (item master) that the factory can manufacture.
    Versioned — multiple versions of the same product code may exist.
    """

    __tablename__ = "product_definitions"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    version: Mapped[str] = mapped_column(
        String(50), nullable=False, default="1.0",
        comment="Product version — allows multiple revisions of a product code",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    uom: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("units_of_measure.symbol"),
        nullable=False,
        default="EA",
        comment="Unit of measure — FK to units_of_measure.symbol",
    )
    product_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="discrete",
        comment="Product type: 'discrete' or 'process'",
    )

    # Relationships
    boms: Mapped[list["BillOfMaterial"]] = relationship(
        "BillOfMaterial", back_populates="product", cascade="all, delete-orphan",
    )
    routes: Mapped[list["ProcessRoute"]] = relationship(
        "ProcessRoute", back_populates="product", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ProductDefinition id={self.id} code={self.code} v={self.version}>"


class BillOfMaterial(BaseModel):
    """
    BOM header — links a product to a versioned list of material requirements.
    Supports effectivity dating for engineering change management.
    """

    __tablename__ = "bills_of_material"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_definitions.id"),
        nullable=False, index=True,
    )
    version: Mapped[str] = mapped_column(
        String(50), nullable=False, default="1.0",
        comment="BOM version — allows multiple BOM revisions per product",
    )
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationships
    product: Mapped["ProductDefinition"] = relationship(
        "ProductDefinition", back_populates="boms",
    )
    items: Mapped[list["BOMItem"]] = relationship(
        "BOMItem", back_populates="bom", cascade="all, delete-orphan",
        order_by="BOMItem.position",
    )

    def __repr__(self) -> str:
        return f"<BillOfMaterial id={self.id} product_id={self.product_id} v={self.version}>"


class BOMItem(BaseModel):
    """
    BOM line item — a single material requirement within a BOM.
    References a MaterialDefinition (from MAT-MGMT, to be linked via FK later).
    """

    __tablename__ = "bom_items"

    bom_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bills_of_material.id"),
        nullable=False, index=True,
    )
    material_code: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Material code reference. Will become FK to material_definitions when MAT-MGMT is implemented.",
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    uom: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("units_of_measure.symbol"),
        nullable=False,
        default="EA",
        comment="Unit of measure — FK to units_of_measure.symbol",
    )
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Sort order within the BOM",
    )

    # Relationships
    bom: Mapped["BillOfMaterial"] = relationship(
        "BillOfMaterial", back_populates="items",
    )

    def __repr__(self) -> str:
        return f"<BOMItem id={self.id} bom_id={self.bom_id} material={self.material_code}>"


class ProcessRoute(BaseModel):
    """
    A manufacturing route — an ordered sequence of steps to produce a product.
    Each product may have multiple routes; one is marked as default.
    """

    __tablename__ = "process_routes"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_definitions.id"),
        nullable=False, index=True,
    )
    version: Mapped[str] = mapped_column(
        String(50), nullable=False, default="1.0",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Only one route per product should be marked as default",
    )

    # Relationships
    product: Mapped["ProductDefinition"] = relationship(
        "ProductDefinition", back_populates="routes",
    )
    steps: Mapped[list["RouteStep"]] = relationship(
        "RouteStep", back_populates="route", cascade="all, delete-orphan",
        order_by="RouteStep.sequence",
    )

    def __repr__(self) -> str:
        return f"<ProcessRoute id={self.id} name={self.name} v={self.version}>"


class RouteStep(BaseModel):
    """
    An individual step/operation within a ProcessRoute.
    References a WorkCell from PHYS-MODEL to define where work is performed.
    The sequence field defines step ordering (e.g. 10, 20, 30 for easy insertion).
    """

    __tablename__ = "route_steps"

    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("process_routes.id"),
        nullable=False, index=True,
    )
    sequence: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Step sequence number (10, 20, 30 convention for easy insertion)",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    step_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="production",
        comment="Step type: 'production', 'inspection', or 'rework'",
    )
    work_cell_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_cells.id"),
        nullable=True, index=True,
        comment="Work cell where this step is performed (nullable for unassigned steps)",
    )
    expected_cycle_time_sec: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Expected cycle time in seconds for performance analysis",
    )

    # Relationships
    route: Mapped["ProcessRoute"] = relationship(
        "ProcessRoute", back_populates="steps",
    )
    parameters: Mapped[list["StepParameter"]] = relationship(
        "StepParameter", back_populates="step", cascade="all, delete-orphan",
        order_by="StepParameter.name",
    )

    def __repr__(self) -> str:
        return f"<RouteStep id={self.id} seq={self.sequence} name={self.name}>"


class StepParameter(BaseModel):
    """
    A data parameter specification attached to a RouteStep.
    Defines what data should be collected at this step (data type, limits, target).
    """

    __tablename__ = "step_parameters"

    step_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("route_steps.id"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="numeric",
        comment="Data type: 'numeric', 'string', 'boolean', 'enum'",
    )
    uom: Mapped[str | None] = mapped_column(
        String(20),
        ForeignKey("units_of_measure.symbol"),
        nullable=True,
        comment="Unit of measure — FK to units_of_measure.symbol",
    )
    target_value: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Target/nominal value as string (parsed based on data_type)",
    )
    lower_limit: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Lower control/spec limit",
    )
    upper_limit: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Upper control/spec limit",
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="Whether data collection for this parameter is mandatory",
    )

    # Relationships
    step: Mapped["RouteStep"] = relationship(
        "RouteStep", back_populates="parameters",
    )

    def __repr__(self) -> str:
        return f"<StepParameter id={self.id} step_id={self.step_id} name={self.name}>"
