"""
PHYS-MODEL: Pydantic schemas for the physical asset hierarchy REST API.

Create/Read/Update schemas for Site, Area, ProductionLine, WorkCell, Equipment.
ISA-95 Part 2: EquipmentClass, EquipmentClassProperty, EquipmentCapability, EquipmentCapabilityProperty.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ─── Site ──────────────────────────────────────────────────────────────


class SiteCreate(BaseModel):
    """Schema for creating a new site."""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    timezone: str | None = Field(None, max_length=50)
    address: str | None = None


class SiteRead(BaseModel):
    """Schema for returning site data."""

    id: UUID
    name: str
    code: str
    description: str | None = None
    timezone: str | None = None
    address: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SiteUpdate(BaseModel):
    """Schema for updating a site. All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = None
    timezone: str | None = None
    address: str | None = None


# ─── Area ──────────────────────────────────────────────────────────────


class AreaCreate(BaseModel):
    """Schema for creating a new area within a site."""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None


class AreaRead(BaseModel):
    """Schema for returning area data."""

    id: UUID
    name: str
    code: str
    description: str | None = None
    site_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AreaUpdate(BaseModel):
    """Schema for updating an area."""

    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = None


# ─── ProductionLine ───────────────────────────────────────────────────


class ProductionLineCreate(BaseModel):
    """Schema for creating a production line within an area."""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None


class ProductionLineRead(BaseModel):
    """Schema for returning production line data."""

    id: UUID
    name: str
    code: str
    description: str | None = None
    area_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductionLineUpdate(BaseModel):
    """Schema for updating a production line."""

    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = None


# ─── WorkCell ─────────────────────────────────────────────────────────


class WorkCellCreate(BaseModel):
    """Schema for creating a work cell within a production line."""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None


class WorkCellRead(BaseModel):
    """Schema for returning work cell data."""

    id: UUID
    name: str
    code: str
    description: str | None = None
    line_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkCellUpdate(BaseModel):
    """Schema for updating a work cell."""

    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = None


# ─── Equipment ────────────────────────────────────────────────────────


class EquipmentCreate(BaseModel):
    """Schema for creating equipment within a work cell."""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    equipment_class_id: UUID | None = Field(None, description="ISA-95 Part 2 equipment class ID")
    state_model_id: str | None = Field(None, max_length=50, description="State machine model ID (e.g. 'packml'). Null = 100% available.")
    max_queue_depth: int | None = Field(None, ge=1, description="Max WIP items in input queue. Null = unlimited.")


class EquipmentRead(BaseModel):
    """Schema for returning equipment data."""

    id: UUID
    name: str
    code: str
    description: str | None = None
    work_cell_id: UUID
    equipment_class_id: UUID | None = None
    state_model_id: str | None = None
    max_queue_depth: int | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EquipmentUpdate(BaseModel):
    """Schema for updating equipment."""

    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = None
    equipment_class_id: UUID | None = None
    state_model_id: str | None = None
    max_queue_depth: int | None = Field(None, ge=1, description="Max WIP items in input queue. Null = unlimited.")


# ─── Equipment–Material Setup ────────────────────────────────────────


class EquipmentMaterialCreate(BaseModel):
    """Schema for creating an equipment-material setup."""

    material_id: UUID
    design_speed: float = Field(..., gt=0, description="Nameplate design speed (> 0)")
    design_speed_uom: str = Field(..., min_length=1, max_length=20, description="Rate UoM symbol (e.g. EA/h)")
    reject_uom: str = Field(..., min_length=1, max_length=20, description="UoM symbol for rejects (e.g. EA)")
    target_oee: float = Field(..., ge=0.0, le=100.0, description="Target OEE percentage (0–100)")


class EquipmentMaterialRead(BaseModel):
    """Schema for returning equipment-material setup data."""

    id: UUID
    equipment_id: UUID
    material_id: UUID
    material_name: str | None = None
    material_code: str | None = None
    design_speed: float
    design_speed_uom: str
    reject_uom: str
    target_oee: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EquipmentMaterialUpdate(BaseModel):
    """Schema for updating an equipment-material setup. All fields optional."""

    design_speed: float | None = Field(None, gt=0)
    design_speed_uom: str | None = Field(None, min_length=1, max_length=20)
    reject_uom: str | None = Field(None, min_length=1, max_length=20)
    target_oee: float | None = Field(None, ge=0.0, le=100.0)


# ─── Material Setup (current running material) ──────────────────────


class MaterialSetupRequest(BaseModel):
    """Schema for switching the current material on equipment."""

    equipment_material_id: UUID = Field(..., description="ID of the equipment-material configuration to activate")
    job_number: str | None = Field(None, max_length=64, description="Job / batch identifier")


class MaterialSetupRead(BaseModel):
    """Schema for returning the current material setup on equipment."""

    equipment_material_id: UUID | None = None
    material_id: UUID | None = None
    material_name: str | None = None
    material_code: str | None = None
    design_speed: float | None = None
    design_speed_uom: str | None = None
    job_number: str | None = None
    setup_at: datetime | None = None


# ─── Material Setup simulation requests ─────────────────────────────


class SimulateOpcuaMaterialSetupRequest(BaseModel):
    """Simulate an OPC-UA data-change that triggers a material setup switch."""

    tag: str = Field(
        "ns=2;s=Equipment1/MaterialSetup",
        description="OPC-UA node ID of the material-setup tag",
    )
    material_code: str = Field(
        ..., max_length=50,
        description="Material code to switch to (looked up in equipment-materials)",
    )
    job_number: str | None = Field(None, max_length=64, description="Job / batch identifier")


class SimulateMqttMaterialSetupRequest(BaseModel):
    """Simulate an MQTT JSON message that triggers a material setup switch."""

    topic: str = Field(
        "mes/equipment/{equipment_id}/material-setup",
        description="MQTT topic the message would arrive on",
    )
    material_code: str = Field(
        ..., max_length=50,
        description="Material code to switch to",
    )
    job_number: str | None = Field(None, max_length=64, description="Job / batch identifier")


class SimulateHistorianMaterialSetupRequest(BaseModel):
    """Simulate an AVEVA Historian tag change that triggers a material setup switch."""

    tag_fqn: str = Field(
        ..., max_length=255,
        description="Fully qualified tag name (e.g. 'Baytown.Line1_MaterialSetup')",
    )
    material_code: str = Field(
        ..., max_length=50,
        description="Material code to switch to",
    )
    job_number: str | None = Field(None, max_length=64, description="Job / batch identifier")


# ═══════════════════════════════════════════════════════════════════════
# ISA-95 Part 2 — Equipment Capability Model
# ═══════════════════════════════════════════════════════════════════════


# ─── Equipment Class ─────────────────────────────────────────────────


class EquipmentClassCreate(BaseModel):
    """Schema for creating an equipment class."""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None


class EquipmentClassRead(BaseModel):
    """Schema for returning equipment class data."""

    id: UUID
    name: str
    code: str
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EquipmentClassUpdate(BaseModel):
    """Schema for updating an equipment class."""

    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = None


# ─── Equipment Class Property ───────────────────────────────────────


class EquipmentClassPropertyCreate(BaseModel):
    """Schema for creating a property on an equipment class."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    data_type: str = Field("string", pattern=r"^(string|float|int|boolean)$")
    uom_id: str | None = Field(None, max_length=20, description="UoM symbol (e.g. 'bottles/min')")
    default_value: str | None = Field(None, max_length=255)


class EquipmentClassPropertyRead(BaseModel):
    """Schema for returning an equipment class property."""

    id: UUID
    equipment_class_id: UUID
    name: str
    description: str | None = None
    data_type: str
    uom_id: str | None = None
    default_value: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EquipmentClassPropertyUpdate(BaseModel):
    """Schema for updating an equipment class property."""

    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    data_type: str | None = Field(None, pattern=r"^(string|float|int|boolean)$")
    uom_id: str | None = None
    default_value: str | None = None


class EquipmentClassDetail(EquipmentClassRead):
    """Equipment class with nested properties and member count."""

    properties: list[EquipmentClassPropertyRead] = []
    member_count: int = 0


# ─── Equipment Capability ───────────────────────────────────────────


class EquipmentCapabilityPropertyCreate(BaseModel):
    """Schema for creating a capability property value (inline with capability)."""

    class_property_id: UUID = Field(..., description="ID of the class property definition")
    value: str = Field(..., max_length=255)


class EquipmentCapabilityPropertyRead(BaseModel):
    """Schema for returning a capability property value."""

    id: UUID
    capability_id: UUID
    class_property_id: UUID
    property_name: str | None = None
    value: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EquipmentCapabilityCreate(BaseModel):
    """Schema for creating an equipment capability."""

    equipment_class_id: UUID | None = Field(None, description="Equipment class this capability covers")
    capability_type: str = Field("available", pattern=r"^(committed|available|unattainable)$")
    reason: str | None = Field(None, max_length=255)
    start_time: datetime | None = None
    end_time: datetime | None = None
    properties: list[EquipmentCapabilityPropertyCreate] = []


class EquipmentCapabilityRead(BaseModel):
    """Schema for returning equipment capability data."""

    id: UUID
    equipment_id: UUID
    equipment_class_id: UUID | None = None
    capability_type: str
    reason: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    properties: list[EquipmentCapabilityPropertyRead] = []

    model_config = {"from_attributes": True}


class EquipmentCapabilityUpdate(BaseModel):
    """Schema for updating an equipment capability."""

    equipment_class_id: UUID | None = None
    capability_type: str | None = Field(None, pattern=r"^(committed|available|unattainable)$")
    reason: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
