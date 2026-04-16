"""
PHYS-MODEL: Pydantic schemas for the physical asset hierarchy REST API.

Create/Read/Update schemas for Site, Area, ProductionLine, WorkCell, Equipment.
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
    wc_type: str = Field("manual", pattern=r"^(manual|automated)$")


class WorkCellRead(BaseModel):
    """Schema for returning work cell data."""

    id: UUID
    name: str
    code: str
    description: str | None = None
    line_id: UUID
    wc_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkCellUpdate(BaseModel):
    """Schema for updating a work cell."""

    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = None
    wc_type: str | None = Field(None, pattern=r"^(manual|automated)$")


# ─── Equipment ────────────────────────────────────────────────────────


class EquipmentCreate(BaseModel):
    """Schema for creating equipment within a work cell."""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    equipment_type: str | None = Field(None, max_length=100)
    capabilities: dict[str, Any] | None = None
    state_model_id: str | None = Field(None, max_length=50, description="State machine model ID (e.g. 'packml'). Null = 100% available.")
    max_queue_depth: int | None = Field(None, ge=1, description="Max WIP items in input queue. Null = unlimited.")


class EquipmentRead(BaseModel):
    """Schema for returning equipment data."""

    id: UUID
    name: str
    code: str
    description: str | None = None
    work_cell_id: UUID
    equipment_type: str | None = None
    capabilities: dict[str, Any] | None = None
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
    equipment_type: str | None = None
    capabilities: dict[str, Any] | None = None
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
