"""
PHYS-MODEL: SQLAlchemy models for the ISA-95 physical asset hierarchy.

Entities:
- Site:           Top-level organizational unit (factory / plant)
- Area:           Logical grouping within a site (department / shop)
- ProductionLine: A linear arrangement of work cells within an area
- WorkCell:       A station where operations are performed (manual or automated)
- Equipment:      An individual machine or device within a work cell
"""

from __future__ import annotations

import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, JSON, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mes.framework.db import BaseModel

import datetime as _dt


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
        Uuid, ForeignKey("sites.id"), nullable=False, index=True,
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
    A linear arrangement of work cells that process units sequentially.
    """

    __tablename__ = "production_lines"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    area_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("areas.id"), nullable=False, index=True,
    )

    # Relationships
    area: Mapped["Area"] = relationship("Area", back_populates="production_lines")
    work_cells: Mapped[list["WorkCell"]] = relationship(
        "WorkCell", back_populates="production_line", cascade="all, delete-orphan",
        order_by="WorkCell.name",
    )

    def __repr__(self) -> str:
        return f"<ProductionLine id={self.id} code={self.code}>"


class WorkCell(BaseModel):
    """
    ISA-95 — Work Cell within a Production Line.
    A station where manufacturing operations are performed.
    Can be manual (human-operated) or automated (machine-driven).
    """

    __tablename__ = "work_cells"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    line_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("production_lines.id"), nullable=False, index=True,
    )
    # Relationships
    production_line: Mapped["ProductionLine"] = relationship(
        "ProductionLine", back_populates="work_cells",
    )
    equipment: Mapped[list["Equipment"]] = relationship(
        "Equipment", back_populates="work_cell", cascade="all, delete-orphan",
        order_by="Equipment.name",
    )

    def __repr__(self) -> str:
        return f"<WorkCell id={self.id} code={self.code}>"


class Equipment(BaseModel):
    """
    ISA-95 — Equipment within a Work Cell.
    An individual machine, tool, or device that performs operations on units.
    Status is a simplified dispatch-level status; detailed state machine
    is handled by pluggable equipment_state_model plugins (see D025).
    """

    __tablename__ = "equipment"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    work_cell_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("work_cells.id"), nullable=False, index=True,
    )
    equipment_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Free-form equipment type classification",
    )
    capabilities: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
        comment="Freeform JSON describing equipment capabilities for dispatch matching",
    )
    state_model_id: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True,
        comment="State machine model ID (e.g. 'packml', 'semi_e10'). Null = 100% available.",
    )
    max_queue_depth: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None,
        comment="Max WIP items (units + lots) allowed in input queue. Null = unlimited.",
    )
    current_material_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("equipment_materials.id"), nullable=True, default=None,
        comment="Currently running equipment-material setup. Null = no material set up.",
    )
    current_job_number: Mapped[str | None] = mapped_column(
        String(64), nullable=True, default=None,
        comment="Job / batch identifier for the current material run.",
    )
    material_setup_at: Mapped[_dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None,
        comment="Local timestamp when the current material was set up.",
    )
    material_setup_at_utc: Mapped[_dt.datetime | None] = mapped_column(
        DateTime(timezone=False), nullable=True, default=None,
        comment="UTC timestamp when the current material was set up.",
    )

    # Relationships
    work_cell: Mapped["WorkCell"] = relationship(
        "WorkCell", back_populates="equipment",
    )
    material_setups: Mapped[list["EquipmentMaterial"]] = relationship(
        "EquipmentMaterial", back_populates="equipment", cascade="all, delete-orphan",
        foreign_keys="EquipmentMaterial.equipment_id",
    )
    active_material_setup: Mapped["EquipmentMaterial | None"] = relationship(
        "EquipmentMaterial", foreign_keys=[current_material_id], lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Equipment id={self.id} code={self.code}>"


class EquipmentMaterial(BaseModel):
    """
    Many-to-many junction between Equipment and MaterialDefinition.

    Stores production-setup data at the intersection:
    - design_speed: nameplate speed for good-output material (e.g. 120 EA/h)
    - design_speed_uom: FK to a rate UoM symbol (must be uom_type='rate')
    - reject_uom: FK to a UoM symbol used for rejected / scrap material
    - target_oee: target OEE percentage (0–100) for this equipment-material pair
    """

    __tablename__ = "equipment_materials"
    __table_args__ = (
        UniqueConstraint("equipment_id", "material_id", name="uq_equip_material"),
    )

    equipment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("equipment.id"), nullable=False, index=True,
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("material_definitions.id"), nullable=False, index=True,
    )
    design_speed: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Nameplate design speed for good produced material",
    )
    design_speed_uom: Mapped[str] = mapped_column(
        String(20), ForeignKey("units_of_measure.symbol"), nullable=False,
        comment="Rate UoM for design speed (e.g. EA/h)",
    )
    reject_uom: Mapped[str] = mapped_column(
        String(20), ForeignKey("units_of_measure.symbol"), nullable=False,
        comment="UoM for rejected / scrap material (e.g. EA, kg)",
    )
    target_oee: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Target OEE percentage (0–100)",
    )

    # Relationships
    equipment: Mapped["Equipment"] = relationship(
        "Equipment", back_populates="material_setups",
        foreign_keys=[equipment_id],
    )
    material: Mapped["MaterialDefinition"] = relationship(
        "MaterialDefinition", back_populates="equipment_setups",
    )
    design_speed_unit: Mapped["UnitOfMeasure"] = relationship(
        "UnitOfMeasure", foreign_keys=[design_speed_uom], lazy="selectin",
    )
    reject_unit: Mapped["UnitOfMeasure"] = relationship(
        "UnitOfMeasure", foreign_keys=[reject_uom], lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<EquipmentMaterial id={self.id} "
            f"equip={self.equipment_id} mat={self.material_id} "
            f"speed={self.design_speed} oee={self.target_oee}%>"
        )
