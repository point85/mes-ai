"""
PROD-DEF: SQLAlchemy models for the product definition domain.

Entities:
- ProductDefinition: A product that can be manufactured (item master)
- BillOfMaterial:    BOM header — ties a product to its material requirements
- BOMItem:           BOM line item — a single material requirement with quantity
- OperationsDefinition:      A manufacturing route (sequence of steps) for a product
- ProcessSegment:         An individual step/operation within a route
- SegmentParameter:     A data parameter spec attached to a route step
- ProcessSegmentInputDisposition / ProcessSegmentOutputDisposition:
  M:N junction tables that wire dispositions to steps. The route graph is
  fully derived from these lists: an edge exists from step A → step B for
  every disposition `d` that is both an output of A and an input of B.
  Within a single route, a disposition is unique — it appears in at most
  one step's input list AND at most one step's output list. The same
  disposition (Disposition row) may be reused across different routes.

Route steps reference work cells from PHYS-MODEL and will later
reference MaterialDefinition from MAT-MGMT.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Boolean, CheckConstraint, Date, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mes.framework.db import BaseModel
from mes.core.uom.models import UnitOfMeasure  # noqa: F401 — needed for relationships
from mes.core.material.models import MaterialDefinition  # noqa: F401 — needed for OperationsDefinitionMaterialAssignment
from mes.core.physical_model.models import EquipmentClass, Equipment  # noqa: F401 — needed for ProcessSegment relationships


class Disposition(BaseModel):
    """
    A reusable disposition definition — e.g. 'Pass', 'Fail', 'Hold', 'Scrap'.

    Dispositions are top-level entities created independently and then
    referenced by route steps.  When an operator selects a disposition at
    runtime, the routing engine resolves the target step through this FK.
    """

    __tablename__ = "dispositions"
    __table_args__ = (
        Index("ix_dispositions_code", "code", unique=True, postgresql_where=text("is_active = TRUE")),
    )

    code: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Short unique code (e.g. 'PASS', 'QC-FAIL')",
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False,
        comment="Human-readable disposition name",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Optional description of when this disposition applies",
    )
    category: Mapped[str] = mapped_column(
        String(20), nullable=False, default="route",
        comment="Disposition category: 'route', 'hold', 'scrap', or 'release'",
    )

    def __repr__(self) -> str:
        return f"<Disposition id={self.id} code={self.code} category={self.category}>"


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
    uom_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("units_of_measure.id"),
        nullable=False,
        comment="Unit of measure — FK to units_of_measure.id",
    )
    product_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="discrete",
        comment="Product type: discrete, process, semi_finished, or configurable",
    )

    # Relationships
    uom_rel: Mapped["UnitOfMeasure"] = relationship(
        "UnitOfMeasure", foreign_keys=[uom_id], lazy="selectin",
    )
    boms: Mapped[list["BillOfMaterial"]] = relationship(
        "BillOfMaterial", back_populates="product", cascade="all, delete-orphan",
    )
    route_assignments: Mapped[list["OperationsDefinitionProductAssignment"]] = relationship(
        "OperationsDefinitionProductAssignment",
        back_populates="product",
    )

    @property
    def uom_symbol(self) -> str | None:
        return self.uom_rel.symbol if self.uom_rel else None

    def __repr__(self) -> str:
        return f"<ProductDefinition id={self.id} code={self.code} v={self.version}>"


class BillOfMaterial(BaseModel):
    """
    BOM header — links a product to a versioned list of material requirements.
    Supports effectivity dating for engineering change management.
    """

    __tablename__ = "bills_of_material"

    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("product_definitions.id"),
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
        Uuid, ForeignKey("bills_of_material.id"),
        nullable=False, index=True,
    )
    material_code: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="Material code reference. Will become FK to material_definitions when MAT-MGMT is implemented.",
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    uom_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("units_of_measure.id"),
        nullable=False,
        comment="Unit of measure — FK to units_of_measure.id",
    )
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Sort order within the BOM",
    )
    process_segment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("process_segments.id"),
        nullable=True, index=True,
        comment="Optional FK to route step where this material is consumed",
    )

    # Relationships
    bom: Mapped["BillOfMaterial"] = relationship(
        "BillOfMaterial", back_populates="items",
    )
    uom_rel: Mapped["UnitOfMeasure"] = relationship(
        "UnitOfMeasure", foreign_keys=[uom_id], lazy="selectin",
    )

    @property
    def uom_symbol(self) -> str | None:
        return self.uom_rel.symbol if self.uom_rel else None

    def __repr__(self) -> str:
        return f"<BOMItem id={self.id} bom_id={self.bom_id} material={self.material_code}>"


class OperationsDefinition(BaseModel):
    """
    A manufacturing route — an ordered sequence of steps to produce a product.
    Routes are associated with products via the
    ``operations_definition_product_assignments`` junction table (many-to-many).
    """

    __tablename__ = "operations_definitions"

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
    steps: Mapped[list["ProcessSegment"]] = relationship(
        "ProcessSegment", back_populates="route", cascade="all, delete-orphan",
        order_by="ProcessSegment.sequence",
    )
    product_assignments: Mapped[list["OperationsDefinitionProductAssignment"]] = relationship(
        "OperationsDefinitionProductAssignment", back_populates="route", cascade="all, delete-orphan",
    )
    material_assignments: Mapped[list["OperationsDefinitionMaterialAssignment"]] = relationship(
        "OperationsDefinitionMaterialAssignment", back_populates="route", cascade="all, delete-orphan",
    )
    def __repr__(self) -> str:
        return f"<OperationsDefinition id={self.id} name={self.name} v={self.version}>"


class ProcessSegment(BaseModel):
    """
    An individual step/operation within a OperationsDefinition.
    References a WorkCell from PHYS-MODEL to define where work is performed.
    The sequence field defines step ordering (e.g. 10, 20, 30 for easy insertion).
    """

    __tablename__ = "process_segments"

    route_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("operations_definitions.id"),
        nullable=False, index=True,
    )
    sequence: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Step sequence number (10, 20, 30 convention for easy insertion)",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    step_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="production",
        comment="Step type: 'production', 'inspection', 'rework', or 'mrb'",
    )
    equipment_class_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("equipment_classes.id"),
        nullable=True, index=True,
        comment="ISA-95 process segment: what class of equipment is required at this step",
    )
    expected_cycle_time_sec: Mapped[float | None] = mapped_column(
        Float, nullable=True,
        comment="Expected cycle time in seconds for performance analysis",
    )
    erp_operation_number: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="ERP operation/step number for outbound reporting (e.g. '0010', '0020')",
    )
    is_initial_step: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment=(
            "Marks this step as the route's entry point. Exactly one step "
            "per route should be flagged. Used by RoutingEngineService to "
            "resolve the first step for a new lot/unit. The empty-input "
            "rule is a UX hint; this flag is authoritative."
        ),
    )

    # Relationships
    route: Mapped["OperationsDefinition"] = relationship(
        "OperationsDefinition", back_populates="steps",
    )
    equipment_class: Mapped["EquipmentClass | None"] = relationship(
        "EquipmentClass", lazy="joined",
    )
    parameters: Mapped[list["SegmentParameter"]] = relationship(
        "SegmentParameter", back_populates="step", cascade="all, delete-orphan",
        order_by="SegmentParameter.name",
    )
    equipment_requirements: Mapped[list["SegmentEquipmentRequirement"]] = relationship(
        "SegmentEquipmentRequirement", back_populates="step", cascade="all, delete-orphan",
    )
    material_requirements: Mapped[list["SegmentMaterialRequirement"]] = relationship(
        "SegmentMaterialRequirement", back_populates="step", cascade="all, delete-orphan",
        order_by="SegmentMaterialRequirement.position",
    )
    input_dispositions: Mapped[list["ProcessSegmentInputDisposition"]] = relationship(
        "ProcessSegmentInputDisposition",
        back_populates="step",
        cascade="all, delete-orphan",
        order_by="ProcessSegmentInputDisposition.position",
    )
    output_dispositions: Mapped[list["ProcessSegmentOutputDisposition"]] = relationship(
        "ProcessSegmentOutputDisposition",
        back_populates="step",
        cascade="all, delete-orphan",
        order_by="ProcessSegmentOutputDisposition.position",
    )
    def __repr__(self) -> str:
        return f"<ProcessSegment id={self.id} seq={self.sequence} name={self.name}>"


class SegmentParameter(BaseModel):
    """
    A data parameter specification attached to a ProcessSegment.
    Defines what data should be collected at this step (data type, limits, target).
    """

    __tablename__ = "segment_parameters"

    step_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("process_segments.id"),
        nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="numeric",
        comment="Data type: 'numeric', 'string', 'boolean', 'enum'",
    )
    uom_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("units_of_measure.id"),
        nullable=True,
        comment="Unit of measure — FK to units_of_measure.id",
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
    step: Mapped["ProcessSegment"] = relationship(
        "ProcessSegment", back_populates="parameters",
    )
    uom_rel: Mapped["UnitOfMeasure | None"] = relationship(
        "UnitOfMeasure", foreign_keys=[uom_id], lazy="selectin",
    )

    @property
    def uom_symbol(self) -> str | None:
        return self.uom_rel.symbol if self.uom_rel else None

    def __repr__(self) -> str:
        return f"<SegmentParameter id={self.id} step_id={self.step_id} name={self.name}>"


class SegmentEquipmentRequirement(BaseModel):
    """
    ISA-95 Process Segment — Equipment Requirement.

    Specifies that a piece of equipment OR an entire equipment class is
    required / preferred / alternate at a route step.  Exactly one of
    ``equipment_class_id`` and ``equipment_id`` must be set per row.

    This matches ISA-95 Part 2 ``EquipmentSegmentSpecification``, which can
    reference either an abstract ``EquipmentClass`` (e.g. "needs an OVEN")
    or a concrete ``Equipment`` (e.g. "must use RO-500 preferentially").

    The dispatch engine AND-s across all active requirement rows to
    compute the candidate equipment set for the step.

    use_type values:
      - required:  must be satisfied
      - preferred: use if available, otherwise fall back
      - alternate: acceptable substitute
    """

    __tablename__ = "segment_equipment_requirements"
    __table_args__ = (
        UniqueConstraint("step_id", "equipment_id", name="uq_segment_equip_req"),
        UniqueConstraint(
            "step_id", "equipment_class_id",
            name="uq_segment_equip_class_req",
        ),
        CheckConstraint(
            "(equipment_id IS NULL) <> (equipment_class_id IS NULL)",
            name="ck_segment_equip_req_one_target",
        ),
    )

    step_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("process_segments.id"),
        nullable=False, index=True,
    )
    equipment_class_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("equipment_classes.id"),
        nullable=True, index=True,
        comment="Equipment class required at this step (mutually exclusive with equipment_id)",
    )
    equipment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("equipment.id"),
        nullable=True, index=True,
        comment="Specific equipment instance required at this step (mutually exclusive with equipment_class_id)",
    )
    use_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="preferred",
        comment="Use type: required, preferred, alternate",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    step: Mapped["ProcessSegment"] = relationship(
        "ProcessSegment", back_populates="equipment_requirements",
    )
    equipment_class: Mapped["EquipmentClass | None"] = relationship(
        "EquipmentClass", lazy="joined",
    )
    equipment: Mapped["Equipment | None"] = relationship("Equipment", lazy="joined")

    def __repr__(self) -> str:
        target = (
            f"class={self.equipment_class_id}"
            if self.equipment_class_id
            else f"equip={self.equipment_id}"
        )
        return (
            f"<SegmentEquipmentRequirement id={self.id} "
            f"step={self.step_id} {target} use={self.use_type}>"
        )


class SegmentMaterialRequirement(BaseModel):
    """
    ISA-95 Process Segment — Material Requirement.

    Specifies a material consumed or produced at a specific route step,
    with quantity and unit of measure.  This is the step-level BOM —
    linking *what* material is needed *where* in the process.

    material_use values:
      - consumed:  raw material or component used up at this step
      - produced:  intermediate or finished material output at this step
    """

    __tablename__ = "segment_material_requirements"
    __table_args__ = (
        UniqueConstraint("step_id", "material_id", name="uq_segment_mat_req"),
    )

    step_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("process_segments.id"),
        nullable=False, index=True,
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("material_definitions.id"),
        nullable=False, index=True,
        comment="Material definition consumed or produced at this step",
    )
    quantity: Mapped[float] = mapped_column(
        Float, nullable=False,
        comment="Quantity per unit/lot of finished product",
    )
    uom_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("units_of_measure.id"),
        nullable=False,
        comment="Unit of measure — FK to units_of_measure.id",
    )
    material_use: Mapped[str] = mapped_column(
        String(20), nullable=False, default="consumed",
        comment="Material use: consumed, produced",
    )
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Sort order within the step",
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    step: Mapped["ProcessSegment"] = relationship(
        "ProcessSegment", back_populates="material_requirements",
    )
    material: Mapped["MaterialDefinition"] = relationship(
        "MaterialDefinition", lazy="joined",
    )
    uom_rel: Mapped["UnitOfMeasure"] = relationship(
        "UnitOfMeasure", foreign_keys=[uom_id], lazy="selectin",
    )

    @property
    def uom_symbol(self) -> str | None:
        return self.uom_rel.symbol if self.uom_rel else None

    def __repr__(self) -> str:
        return (
            f"<SegmentMaterialRequirement id={self.id} "
            f"step={self.step_id} mat={self.material_id} qty={self.quantity} use={self.material_use}>"
        )


class ProcessSegmentInputDisposition(BaseModel):
    """
    Junction: a disposition that, when raised at the previous step, routes
    a unit/lot INTO this step. The route graph is the join of these rows
    against ``ProcessSegmentOutputDisposition`` on (route_id, disposition_id).

    Within a single route a given Disposition appears in at most one
    step's input list (enforced by validation in the service layer). This
    keeps the destination unambiguous when the routing engine resolves a
    chosen disposition to a next step.

    A step with no rows here is a route entry point (use ``is_initial_step``
    on ProcessSegment to flag the canonical first step).
    """

    __tablename__ = "process_segment_input_dispositions"
    __table_args__ = (
        UniqueConstraint("step_id", "disposition_id", name="uq_psid_step_disp"),
    )

    step_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("process_segments.id"),
        nullable=False, index=True,
    )
    disposition_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("dispositions.id"),
        nullable=False, index=True,
    )
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Sort order within the step's input list (UI hint only)",
    )

    step: Mapped["ProcessSegment"] = relationship(
        "ProcessSegment", back_populates="input_dispositions",
    )
    disposition: Mapped["Disposition"] = relationship(
        "Disposition", lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<ProcessSegmentInputDisposition step={self.step_id} "
            f"disp={self.disposition_id}>"
        )


class ProcessSegmentOutputDisposition(BaseModel):
    """
    Junction: a disposition that the operator (or automation) may select
    when completing this step. Selecting a disposition routes the unit/lot
    to whichever step lists it in ``ProcessSegmentInputDisposition``.

    Within a single route a given Disposition appears in at most one
    step's output list (enforced by validation in the service layer).

    A step with no rows here is a terminal step — completing it ends the
    route and marks the lot/unit as completed.
    """

    __tablename__ = "process_segment_output_dispositions"
    __table_args__ = (
        UniqueConstraint("step_id", "disposition_id", name="uq_psod_step_disp"),
    )

    step_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("process_segments.id"),
        nullable=False, index=True,
    )
    disposition_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("dispositions.id"),
        nullable=False, index=True,
    )
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Sort order within the step's output list (UI hint only)",
    )

    step: Mapped["ProcessSegment"] = relationship(
        "ProcessSegment", back_populates="output_dispositions",
    )
    disposition: Mapped["Disposition"] = relationship(
        "Disposition", lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<ProcessSegmentOutputDisposition step={self.step_id} "
            f"disp={self.disposition_id}>"
        )


class OperationsDefinitionProductAssignment(BaseModel):
    """
    Junction table linking a OperationsDefinition to one or more ProductDefinitions.
    Supports many-to-many: multiple products can share the same manufacturing route.
    """

    __tablename__ = "operations_definition_product_assignments"

    route_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("operations_definitions.id"),
        nullable=False, index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("product_definitions.id"),
        nullable=False, index=True,
    )

    # Relationships
    route: Mapped["OperationsDefinition"] = relationship(
        "OperationsDefinition", back_populates="product_assignments",
    )
    product: Mapped["ProductDefinition"] = relationship(
        "ProductDefinition", back_populates="route_assignments",
    )

    def __repr__(self) -> str:
        return f"<OperationsDefinitionProductAssignment route={self.route_id} product={self.product_id}>"


class OperationsDefinitionMaterialAssignment(BaseModel):
    """
    Junction table linking a OperationsDefinition to one or more MaterialDefinitions.
    Allows any material type (raw, intermediate, finished, etc.) to be assigned
    to a route — e.g. an intermediate material produced by one route and consumed
    by another.
    """

    __tablename__ = "operations_definition_material_assignments"

    route_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("operations_definitions.id"),
        nullable=False, index=True,
    )
    material_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("material_definitions.id"),
        nullable=False, index=True,
    )

    # Relationships
    route: Mapped["OperationsDefinition"] = relationship(
        "OperationsDefinition", back_populates="material_assignments",
    )
    material: Mapped["MaterialDefinition"] = relationship("MaterialDefinition")

    def __repr__(self) -> str:
        return f"<OperationsDefinitionMaterialAssignment route={self.route_id} material={self.material_id}>"



