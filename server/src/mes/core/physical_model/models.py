"""
PHYS-MODEL: SQLAlchemy models for the ISA-95 physical asset hierarchy.

Entities (Part 1 — Role-Based Equipment Hierarchy):
    Enterprise (implicit) → Site → Area → Work Center → Work Unit

- Site:           A single manufacturing facility. Second level of the ISA-95
                  role-based equipment hierarchy (Enterprise being the first).
- Area:           A logical grouping within a Site (e.g. department, shop).
- ProductionLine: A specialization of ISA-95 "Work Center" for discrete / mixed
                  manufacturing. Contains an ordered set of Work Cells.
- WorkCell:       A specialization of ISA-95 "Work Unit". A station where one or
                  more pieces of equipment perform a specific operation.
- Equipment:      A single machine, tool, or device that resides in a Work Cell.

Entities (Part 2 — Equipment Capability Model):
- EquipmentClass:              Groups equipment by what they can do (e.g. Filler, Labeler)
- EquipmentClassProperty:      Typed property definitions for a class
- EquipmentCapability:         Specific capability declaration for an equipment instance
- EquipmentCapabilityProperty: Actual property values for a capability
- EquipmentMaterial:           Equipment × MaterialDefinition setup record (design speed, UoMs, target OEE)
"""

from __future__ import annotations

import datetime as _dt
import uuid

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mes.framework.db import BaseModel

import datetime as _dt


class Site(BaseModel):
    """
    ISA-95 Part 1 — Site.

    Second level of the role-based equipment hierarchy (Enterprise → **Site** →
    Area → Work Center → Work Unit). Represents a single manufacturing
    facility / plant. A MES instance may manage one or more Sites.
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
    work_schedule_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("work_schedules.id"), nullable=True, index=True,
        comment="Optional work schedule assigned at the Site level.",
    )

    # Relationships
    areas: Mapped[list["Area"]] = relationship(
        "Area", back_populates="site", cascade="all, delete-orphan",
        order_by="Area.name",
    )

    def __repr__(self) -> str:
        return f"<Site id={self.id} code={self.code}>"


class Area(BaseModel):
    """
    ISA-95 Part 1 — Area.

    Third level of the role-based equipment hierarchy. A logical grouping
    within a Site such as a department, shop, or building wing. Contains one
    or more Work Centers (here represented by ProductionLine).
    """

    __tablename__ = "areas"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    site_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sites.id"), nullable=False, index=True,
    )
    work_schedule_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("work_schedules.id"), nullable=True, index=True,
        comment="Optional work schedule assigned at the Area level.",
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
    ISA-95 Part 1 — Production Line (a specialization of **Work Center**).

    Fourth level of the role-based equipment hierarchy. An ordered arrangement
    of Work Cells that process units sequentially. ISA-95 defines four Work
    Center subtypes (Process Cell, Production Unit, Production Line, Storage
    Zone); this model uses Production Line as the canonical subtype for
    discrete and mixed-mode manufacturing.
    """

    __tablename__ = "production_lines"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    area_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("areas.id"), nullable=False, index=True,
    )
    work_schedule_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("work_schedules.id"), nullable=True, index=True,
        comment="Optional work schedule assigned at the Production Line level.",
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
    ISA-95 Part 1 — Work Cell (a specialization of **Work Unit**).

    Fifth (leaf) level of the role-based equipment hierarchy. A station where
    manufacturing operations are performed by one or more pieces of Equipment.
    ISA-95 defines three Work Unit subtypes (Unit, Work Cell, Storage Unit);
    this model uses Work Cell as the canonical leaf grouping.
    """

    __tablename__ = "work_cells"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    line_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("production_lines.id"), nullable=False, index=True,
    )
    area_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("areas.id"), nullable=False, index=True,
        comment="Denormalized reference to the parent Area (avoids join through ProductionLine).",
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("sites.id"), nullable=False, index=True,
        comment="Denormalized reference to the parent Site (avoids two-level join).",
    )
    work_schedule_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("work_schedules.id"), nullable=True, index=True,
        comment="Optional work schedule assigned at the Work Cell level.",
    )
    # Relationships
    production_line: Mapped["ProductionLine"] = relationship(
        "ProductionLine", back_populates="work_cells",
    )
    area: Mapped["Area"] = relationship("Area", foreign_keys=[area_id])
    site: Mapped["Site"] = relationship("Site", foreign_keys=[site_id])
    equipment: Mapped[list["Equipment"]] = relationship(
        "Equipment", back_populates="work_cell", cascade="all, delete-orphan",
        order_by="Equipment.name",
    )

    def __repr__(self) -> str:
        return f"<WorkCell id={self.id} code={self.code}>"


class Equipment(BaseModel):
    """
    ISA-95 Part 1 — Equipment.

    An individual machine, tool, or device residing in a Work Cell that
    performs operations on units or lots. Classification by function is via
    ``equipment_class_id`` (ISA-95 Part 2 Equipment Class).

    Detailed runtime state is handled by pluggable equipment_state_model
    plugins (see decision D025); this model only carries the dispatch-level
    attributes needed by the core scheduler.
    """

    __tablename__ = "equipment"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    work_cell_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("work_cells.id"), nullable=False, index=True,
    )
    equipment_class_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("equipment_classes.id"), nullable=True, index=True,
        comment="ISA-95 Part 2 equipment class (e.g. Filler, Labeler).",
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
        Uuid,
        ForeignKey(
            "equipment_materials.id",
            use_alter=True,
            name="fk_equipment_current_material_id",
        ),
        nullable=True,
        default=None,
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
    equipment_class: Mapped["EquipmentClass | None"] = relationship(
        "EquipmentClass", back_populates="equipment_members",
    )
    formal_capabilities: Mapped[list["EquipmentCapability"]] = relationship(
        "EquipmentCapability", back_populates="equipment", cascade="all, delete-orphan",
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
    design_speed_uom_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("units_of_measure.id"), nullable=False,
        comment="Rate UoM for design speed — FK to units_of_measure.id",
    )
    reject_uom_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("units_of_measure.id"), nullable=False,
        comment="UoM for rejected / scrap material — FK to units_of_measure.id",
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
        "UnitOfMeasure", foreign_keys=[design_speed_uom_id], lazy="selectin",
    )
    reject_unit: Mapped["UnitOfMeasure"] = relationship(
        "UnitOfMeasure", foreign_keys=[reject_uom_id], lazy="selectin",
    )

    @property
    def design_speed_uom_symbol(self) -> str | None:
        return self.design_speed_unit.symbol if self.design_speed_unit else None

    @property
    def reject_uom_symbol(self) -> str | None:
        return self.reject_unit.symbol if self.reject_unit else None

    def __repr__(self) -> str:
        return (
            f"<EquipmentMaterial id={self.id} "
            f"equip={self.equipment_id} mat={self.material_id} "
            f"speed={self.design_speed} oee={self.target_oee}%>"
        )


# ═══════════════════════════════════════════════════════════════════════
# ISA-95 Part 2 — Equipment Capability Model
# ═══════════════════════════════════════════════════════════════════════


class EquipmentClass(BaseModel):
    """
    ISA-95 Part 2 — Equipment Class.

    Groups equipment by *what they can do* (capability classification),
    independent of where they sit in the physical hierarchy.
    Examples: "Filler", "Labeler", "Oven", "Pick-and-Place".

    An equipment instance references exactly one class via Equipment.equipment_class_id.
    """

    __tablename__ = "equipment_classes"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    properties: Mapped[list["EquipmentClassProperty"]] = relationship(
        "EquipmentClassProperty", back_populates="equipment_class",
        cascade="all, delete-orphan", order_by="EquipmentClassProperty.name",
    )
    equipment_members: Mapped[list["Equipment"]] = relationship(
        "Equipment", back_populates="equipment_class",
    )

    def __repr__(self) -> str:
        return f"<EquipmentClass id={self.id} code={self.code}>"


class EquipmentClassProperty(BaseModel):
    """
    ISA-95 Part 2 — Equipment Class Property.

    Defines a typed property that any equipment in this class should declare.
    For example, class "Filler" may define properties:
      - max_fill_rate (float, bottles/min)
      - min_fill_volume (float, mL)
      - supported_container_types (string)
    """

    __tablename__ = "equipment_class_properties"
    __table_args__ = (
        UniqueConstraint("equipment_class_id", "name", name="uq_ecp_class_name"),
    )

    equipment_class_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("equipment_classes.id"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="Property name (e.g. 'max_fill_rate')",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="string",
        comment="Data type: string, float, int, boolean",
    )
    uom_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("units_of_measure.id"), nullable=True,
        comment="Unit of measure for this property (nullable for dimensionless values)",
    )
    default_value: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Default value (stored as string, interpreted per data_type)",
    )

    # Relationships
    equipment_class: Mapped["EquipmentClass"] = relationship(
        "EquipmentClass", back_populates="properties",
    )
    unit_of_measure: Mapped["UnitOfMeasure | None"] = relationship(
        "UnitOfMeasure", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<EquipmentClassProperty id={self.id} name={self.name} type={self.data_type}>"


class EquipmentCapability(BaseModel):
    """
    ISA-95 Part 2 — Equipment Capability.

    Declares a specific capability of an equipment instance, optionally
    time-bounded. Links to an EquipmentClass to indicate what *kind* of
    operation this equipment can perform.

    capability_type values (per ISA-95):
      - committed:    reserved for a specific job/order
      - available:    currently available for dispatch
      - unattainable: equipment cannot perform this operation right now
    """

    __tablename__ = "equipment_capabilities"

    equipment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("equipment.id"), nullable=False, index=True,
    )
    equipment_class_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("equipment_classes.id"), nullable=True, index=True,
        comment="What class of operation this capability covers",
    )
    capability_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="available",
        comment="ISA-95 capability type: committed, available, unattainable",
    )
    reason: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="Reason for current capability status",
    )
    start_time: Mapped[_dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When this capability becomes valid (null = now)",
    )
    end_time: Mapped[_dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="When this capability expires (null = indefinite)",
    )

    # Relationships
    equipment: Mapped["Equipment"] = relationship(
        "Equipment", back_populates="formal_capabilities",
    )
    equipment_class: Mapped["EquipmentClass | None"] = relationship(
        "EquipmentClass",
    )
    properties: Mapped[list["EquipmentCapabilityProperty"]] = relationship(
        "EquipmentCapabilityProperty", back_populates="capability",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<EquipmentCapability id={self.id} "
            f"equip={self.equipment_id} type={self.capability_type}>"
        )


class EquipmentCapabilityProperty(BaseModel):
    """
    ISA-95 Part 2 — Equipment Capability Property.

    The actual value of a capability property for a specific equipment instance.
    Links back to the class-level property definition for name, data_type, and UoM.
    """

    __tablename__ = "equipment_capability_properties"
    __table_args__ = (
        UniqueConstraint(
            "capability_id", "class_property_id",
            name="uq_ecap_prop",
        ),
    )

    capability_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("equipment_capabilities.id"), nullable=False, index=True,
    )
    class_property_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("equipment_class_properties.id"), nullable=False, index=True,
        comment="Links to the class-level property definition",
    )
    value: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="Property value (stored as string, interpreted per class property data_type)",
    )

    # Relationships
    capability: Mapped["EquipmentCapability"] = relationship(
        "EquipmentCapability", back_populates="properties",
    )
    class_property: Mapped["EquipmentClassProperty"] = relationship(
        "EquipmentClassProperty", lazy="selectin",
    )

    @property
    def property_name(self) -> str | None:
        """Convenience accessor exposing the related class property's name
        (populated via selectin load) so API schemas can surface it without
        requiring callers to resolve the class_property_id separately."""
        return self.class_property.name if self.class_property is not None else None

    @property
    def uom_id(self) -> uuid.UUID | None:
        """Convenience accessor exposing the related class property's UoM id
        (populated via selectin load) so API schemas can surface it."""
        return self.class_property.uom_id if self.class_property is not None else None

    def __repr__(self) -> str:
        return (
            f"<EquipmentCapabilityProperty id={self.id} "
            f"prop={self.class_property_id} value={self.value}>"
        )
