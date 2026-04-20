"""
PROD-DEF: Pydantic schemas for the product definition REST API.

Create/Read/Update schemas for ProductDefinition, BillOfMaterial, BOMItem,
ProcessRoute, RouteStep, StepParameter.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ─── Disposition ──────────────────────────────────────────────────────


class DispositionCreate(BaseModel):
    """Schema for creating a new disposition."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category: str = Field("route", pattern=r"^(route|hold|scrap)$")


class DispositionRead(BaseModel):
    """Schema for returning disposition data."""

    id: UUID
    code: str
    name: str
    description: str | None = None
    category: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DispositionUpdate(BaseModel):
    """Schema for updating a disposition."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = Field(None, pattern=r"^(route|hold|scrap)$")


# ─── ProductDefinition ────────────────────────────────────────────────


class ProductClone(BaseModel):
    """Schema for cloning a product with new identity fields."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    version: str = Field("1.0", max_length=50)
    description: str | None = None


class ProductCreate(BaseModel):
    """Schema for creating a new product definition."""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    version: str = Field("1.0", max_length=50)
    description: str | None = None
    uom: str = Field("EA", max_length=20)
    product_type: str = Field("discrete", pattern=r"^(discrete|process|semi_finished|configurable)$")


class ProductRead(BaseModel):
    """Schema for returning product definition data."""

    id: UUID
    name: str
    code: str
    version: str
    description: str | None = None
    uom: str
    product_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductUpdate(BaseModel):
    """Schema for updating a product definition."""

    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = Field(None, min_length=1, max_length=50)
    version: str | None = Field(None, max_length=50)
    description: str | None = None
    uom: str | None = Field(None, max_length=20)
    product_type: str | None = Field(None, pattern=r"^(discrete|process|semi_finished|configurable)$")


# ─── BillOfMaterial ───────────────────────────────────────────────────


class BOMCreate(BaseModel):
    """Schema for creating a BOM for a product."""

    version: str = Field("1.0", max_length=50)
    effective_date: date | None = None
    expiry_date: date | None = None


class BOMRead(BaseModel):
    """Schema for returning BOM data."""

    id: UUID
    product_id: UUID
    version: str
    effective_date: date | None = None
    expiry_date: date | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BOMUpdate(BaseModel):
    """Schema for updating a BOM."""

    version: str | None = Field(None, max_length=50)
    effective_date: date | None = None
    expiry_date: date | None = None


# ─── BOMItem ──────────────────────────────────────────────────────────


class BOMItemCreate(BaseModel):
    """Schema for creating a BOM item."""

    material_code: str = Field(..., min_length=1, max_length=50)
    quantity: float = Field(..., gt=0)
    uom: str = Field("EA", max_length=20)
    position: int = Field(0, ge=0)
    route_step_id: UUID | None = None


class BOMItemRead(BaseModel):
    """Schema for returning BOM item data."""

    id: UUID
    bom_id: UUID
    material_code: str
    quantity: float
    uom: str
    position: int
    route_step_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BOMItemUpdate(BaseModel):
    """Schema for updating a BOM item."""

    material_code: str | None = Field(None, min_length=1, max_length=50)
    quantity: float | None = Field(None, gt=0)
    uom: str | None = Field(None, max_length=20)
    position: int | None = Field(None, ge=0)
    route_step_id: UUID | None = None


# ─── ProcessRoute ────────────────────────────────────────────────────


class RouteCreate(BaseModel):
    """Schema for creating a process route for a product."""

    name: str = Field(..., min_length=1, max_length=255)
    version: str = Field("1.0", max_length=50)
    description: str | None = None
    is_default: bool = False


class RouteRead(BaseModel):
    """Schema for returning process route data."""

    id: UUID
    product_id: UUID | None = None
    version: str
    name: str
    description: str | None = None
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RouteUpdate(BaseModel):
    """Schema for updating a process route."""

    name: str | None = Field(None, min_length=1, max_length=255)
    version: str | None = Field(None, max_length=50)
    description: str | None = None
    is_default: bool | None = None


# ─── RouteStep ────────────────────────────────────────────────────────


class RouteStepCreate(BaseModel):
    """Schema for creating a route step."""

    sequence: int = Field(..., ge=1)
    name: str = Field(..., min_length=1, max_length=255)
    step_type: str = Field("production", pattern=r"^(production|inspection|rework|mrb)$")
    work_cell_id: UUID | None = None
    equipment_class_id: UUID | None = Field(None, description="ISA-95 equipment class required at this step")
    expected_cycle_time_sec: float | None = Field(None, ge=0)
    erp_operation_number: str | None = Field(None, max_length=50, description="ERP operation number for outbound reporting")
    disposition_id: UUID | None = Field(None, description="FK to the disposition that routes WIP to this step")


class RouteStepRead(BaseModel):
    """Schema for returning route step data."""

    id: UUID
    route_id: UUID
    sequence: int
    name: str
    step_type: str
    work_cell_id: UUID | None = None
    equipment_class_id: UUID | None = None
    expected_cycle_time_sec: float | None = None
    erp_operation_number: str | None = None
    disposition_id: UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RouteStepUpdate(BaseModel):
    """Schema for updating a route step."""

    sequence: int | None = Field(None, ge=1)
    name: str | None = Field(None, min_length=1, max_length=255)
    step_type: str | None = Field(None, pattern=r"^(production|inspection|rework|mrb)$")
    work_cell_id: UUID | None = None
    equipment_class_id: UUID | None = Field(None, description="ISA-95 equipment class required at this step")
    expected_cycle_time_sec: float | None = Field(None, ge=0)
    erp_operation_number: str | None = Field(None, max_length=50)
    disposition_id: UUID | None = None


# ─── StepParameter ───────────────────────────────────────────────────


class StepParameterCreate(BaseModel):
    """Schema for creating a step parameter."""

    name: str = Field(..., min_length=1, max_length=255)
    data_type: str = Field("numeric", pattern=r"^(numeric|string|boolean|enum)$")
    uom: str | None = Field(None, max_length=20)
    target_value: str | None = None
    lower_limit: str | None = None
    upper_limit: str | None = None
    is_required: bool = False


class StepParameterRead(BaseModel):
    """Schema for returning step parameter data."""

    id: UUID
    step_id: UUID
    name: str
    data_type: str
    uom: str | None = None
    target_value: str | None = None
    lower_limit: str | None = None
    upper_limit: str | None = None
    is_required: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StepParameterUpdate(BaseModel):
    """Schema for updating a step parameter."""

    name: str | None = Field(None, min_length=1, max_length=255)
    data_type: str | None = Field(None, pattern=r"^(numeric|string|boolean|enum)$")
    uom: str | None = None
    target_value: str | None = None
    lower_limit: str | None = None
    upper_limit: str | None = None
    is_required: bool | None = None


# ─── StepTransition ──────────────────────────────────────────────────


class StepTransitionCreate(BaseModel):
    """Schema for creating a step transition (route graph edge)."""

    to_step_id: UUID
    condition: str = Field(
        "always",
        pattern=r"^(always|on_pass|on_fail|on_rework|disposition)$",
    )
    is_default: bool = False
    priority: int = Field(0, ge=0)
    label: str | None = Field(None, max_length=255)


class StepTransitionRead(BaseModel):
    """Schema for returning step transition data."""

    id: UUID
    from_step_id: UUID
    to_step_id: UUID
    condition: str
    is_default: bool
    priority: int
    label: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StepTransitionUpdate(BaseModel):
    """Schema for updating a step transition."""

    to_step_id: UUID | None = None
    condition: str | None = Field(
        None,
        pattern=r"^(always|on_pass|on_fail|on_rework|disposition)$",
    )
    is_default: bool | None = None
    priority: int | None = Field(None, ge=0)
    label: str | None = Field(None, max_length=255)


# ─── Route–Product Assignment ────────────────────────────────────────


class RouteProductAssignmentCreate(BaseModel):
    """Schema for assigning a product to a route."""

    product_id: UUID


class RouteProductAssignmentRead(BaseModel):
    """Schema for returning a route–product assignment."""

    id: UUID
    route_id: UUID
    product_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Route–Material Assignment ───────────────────────────────────────


class RouteMaterialAssignmentCreate(BaseModel):
    """Schema for assigning a material to a route."""

    material_id: UUID


class RouteMaterialAssignmentRead(BaseModel):
    """Schema for returning a route–material assignment."""

    id: UUID
    route_id: UUID
    material_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── Step Equipment Requirement (ISA-95 Process Segment) ─────────────


class StepEquipmentRequirementCreate(BaseModel):
    """Schema for adding an equipment requirement to a route step."""

    equipment_id: UUID
    use_type: str = Field("preferred", pattern=r"^(required|preferred|alternate)$")
    description: str | None = None


class StepEquipmentRequirementRead(BaseModel):
    """Schema for returning a step equipment requirement."""

    id: UUID
    step_id: UUID
    equipment_id: UUID
    use_type: str
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StepEquipmentRequirementUpdate(BaseModel):
    """Schema for updating a step equipment requirement."""

    use_type: str | None = Field(None, pattern=r"^(required|preferred|alternate)$")
    description: str | None = None


# ─── Step Material Requirement (ISA-95 Process Segment) ──────────────


class StepMaterialRequirementCreate(BaseModel):
    """Schema for adding a material requirement to a route step."""

    material_id: UUID
    quantity: float = Field(..., gt=0)
    uom: str = Field("EA", max_length=20)
    material_use: str = Field("consumed", pattern=r"^(consumed|produced)$")
    position: int = Field(0, ge=0)
    description: str | None = None


class StepMaterialRequirementRead(BaseModel):
    """Schema for returning a step material requirement."""

    id: UUID
    step_id: UUID
    material_id: UUID
    quantity: float
    uom: str
    material_use: str
    position: int
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StepMaterialRequirementUpdate(BaseModel):
    """Schema for updating a step material requirement."""

    quantity: float | None = Field(None, gt=0)
    uom: str | None = Field(None, max_length=20)
    material_use: str | None = Field(None, pattern=r"^(consumed|produced)$")
    position: int | None = Field(None, ge=0)
    description: str | None = None
