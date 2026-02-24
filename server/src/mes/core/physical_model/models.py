"""
PHYS-MODEL: SQLAlchemy models for the ISA-95 physical asset hierarchy.

Entities:
- Site:           Top-level organizational unit (factory / plant)
- Area:           Logical grouping within a site (department / shop)
- ProductionLine: A linear arrangement of work centers within an area
- WorkCenter:     A station where operations are performed (manual or automated)
- Equipment:      An individual machine or device within a work center
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mes.framework.db import BaseModel


class Site(BaseModel):
    """
    ISA-95 Level 2 — Enterprise Site / Plant.
    Top of the physical hierarchy. A single MES instance may manage one or more sites.
    """

    __tablename__ = "sites"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    timezone: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="IANA timezone identifier (e.g. 'America/Chicago')",
    )
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    areas: Mapped[list["Area"]] = relationship(
        "Area", back_populates="site", cascade="all, delete-orphan",
        order_by="Area.name",
    )

    def __repr__(self) -> str:
        return f"<Site id={self.id} code={self.code}>"


class Area(BaseModel):
    """
    ISA-95 — Area within a Site.
    Represents a logical grouping such as a department, shop, or building wing.
    """

    __tablename__ = "areas"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False, index=True,
    )

    # Relationships
    site: Mapped["Site"] = relationship("Site", back_populates="areas")
    production_lines: Mapped[list["ProductionLine"]] = relationship(
        "ProductionLine", back_populates="area", cascade="all, delete-orphan",
        order_by="ProductionLine.name",
    )

    def __repr__(self) -> str:
        return f"<Area id={self.id} code={self.code}>"


class ProductionLine(BaseModel):
    """
    ISA-95 — Production Line within an Area.
    A linear arrangement of work centers that process units sequentially.
    """

    __tablename__ = "production_lines"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    area_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("areas.id"), nullable=False, index=True,
    )

    # Relationships
    area: Mapped["Area"] = relationship("Area", back_populates="production_lines")
    work_centers: Mapped[list["WorkCenter"]] = relationship(
        "WorkCenter", back_populates="production_line", cascade="all, delete-orphan",
        order_by="WorkCenter.name",
    )

    def __repr__(self) -> str:
        return f"<ProductionLine id={self.id} code={self.code}>"


class WorkCenter(BaseModel):
    """
    ISA-95 — Work Center within a Production Line.
    A station where manufacturing operations are performed.
    Can be manual (human-operated) or automated (machine-driven).
    """

    __tablename__ = "work_centers"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("production_lines.id"), nullable=False, index=True,
    )
    wc_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="manual",
        comment="Work center type: 'manual' or 'automated'",
    )

    # Relationships
    production_line: Mapped["ProductionLine"] = relationship(
        "ProductionLine", back_populates="work_centers",
    )
    equipment: Mapped[list["Equipment"]] = relationship(
        "Equipment", back_populates="work_center", cascade="all, delete-orphan",
        order_by="Equipment.name",
    )

    def __repr__(self) -> str:
        return f"<WorkCenter id={self.id} code={self.code}>"


class Equipment(BaseModel):
    """
    ISA-95 — Equipment within a Work Center.
    An individual machine, tool, or device that performs operations on units.
    Status is a simplified dispatch-level status; detailed state machine
    is handled by pluggable equipment_state_model plugins (see D025).
    """

    __tablename__ = "equipment"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    work_center_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("work_centers.id"), nullable=False, index=True,
    )
    equipment_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Free-form equipment type classification",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="idle",
        comment="Operational status: 'up', 'down', 'idle'",
    )
    capabilities: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="Freeform JSON describing equipment capabilities for dispatch matching",
    )

    # Relationships
    work_center: Mapped["WorkCenter"] = relationship(
        "WorkCenter", back_populates="equipment",
    )

    def __repr__(self) -> str:
        return f"<Equipment id={self.id} code={self.code} status={self.status}>"
