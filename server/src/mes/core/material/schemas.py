"""
MAT-MGMT: Pydantic schemas for the Material Management REST API.

Create / Read / Update schemas for MaterialDefinition, MaterialLot,
MaterialConsumption, plus a ConsumeRequest action schema.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── Valid constants ──────────────────────────────────────────────────

MATERIAL_TYPES = {"raw", "intermediate", "finished", "semi", "consumable", "packaging", "spare"}
MATERIAL_LOT_STATUSES = {"available", "reserved", "consumed", "expired"}


# ═══════════════════════════════════════════════════════════════════
# MaterialDefinition
# ═══════════════════════════════════════════════════════════════════


class MaterialCreate(BaseModel):
    """Schema for creating a new material definition."""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    material_type: str = Field("raw", description="raw, intermediate, finished, semi, consumable, packaging, spare")
    uom_id: UUID = Field(..., description="UUID of the unit of measure")
    revision: str | None = Field(None, max_length=20, description="Material revision level")
    shelf_life_days: int | None = Field(None, gt=0)

    @field_validator("code")
    @classmethod
    def code_no_whitespace(cls, v: str) -> str:
        if " " in v:
            raise ValueError("code must not contain spaces")
        return v

    @field_validator("material_type")
    @classmethod
    def validate_material_type(cls, v: str) -> str:
        if v not in MATERIAL_TYPES:
            raise ValueError(f"material_type must be one of {MATERIAL_TYPES}")
        return v


class MaterialRead(BaseModel):
    """Schema for returning a material definition."""

    id: UUID
    name: str
    code: str
    description: str | None = None
    material_type: str
    uom_id: UUID
    uom_symbol: str | None = None
    revision: str | None = None
    shelf_life_days: int | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MaterialUpdate(BaseModel):
    """Schema for updating a material definition. All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = None
    material_type: str | None = None
    uom_id: UUID | None = None
    revision: str | None = Field(None, max_length=20)
    shelf_life_days: int | None = Field(None, gt=0)

    @field_validator("code")
    @classmethod
    def code_no_whitespace(cls, v: str | None) -> str | None:
        if v is not None and " " in v:
            raise ValueError("code must not contain spaces")
        return v

    @field_validator("material_type")
    @classmethod
    def validate_material_type(cls, v: str | None) -> str | None:
        if v is not None and v not in MATERIAL_TYPES:
            raise ValueError(f"material_type must be one of {MATERIAL_TYPES}")
        return v


# ═══════════════════════════════════════════════════════════════════
# MaterialLot
# ═══════════════════════════════════════════════════════════════════


class MaterialLotCreate(BaseModel):
    """Schema for creating a new material lot."""

    material_id: UUID
    lot_number: str = Field(..., min_length=1, max_length=200)
    quantity_on_hand: float = Field(..., ge=0)
    received_date: date | None = None
    expiry_date: date | None = None
    supplier: str | None = Field(None, max_length=255)


class MaterialLotRead(BaseModel):
    """Schema for returning a material lot."""

    id: UUID
    material_id: UUID
    lot_number: str
    quantity_on_hand: float
    quantity_reserved: float
    status: str
    received_date: date | None = None
    expiry_date: date | None = None
    supplier: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MaterialLotUpdate(BaseModel):
    """Schema for updating a material lot. All fields optional."""

    lot_number: str | None = Field(None, min_length=1, max_length=200)
    quantity_on_hand: float | None = Field(None, ge=0)
    received_date: date | None = None
    expiry_date: date | None = None
    supplier: str | None = Field(None, max_length=255)
    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in MATERIAL_LOT_STATUSES:
            raise ValueError(f"status must be one of {MATERIAL_LOT_STATUSES}")
        return v


# ═══════════════════════════════════════════════════════════════════
# MaterialConsumption
# ═══════════════════════════════════════════════════════════════════


class ConsumeRequest(BaseModel):
    """Request to record material consumption against a WIP unit or lot."""

    unit_id: UUID | None = Field(None, description="WIP unit consuming the material")
    lot_id: UUID | None = Field(None, description="WIP lot consuming the material (for batch)")
    step_id: UUID | None = Field(None, description="Route step where consumption occurs")
    quantity_consumed: float = Field(..., gt=0)

    @field_validator("quantity_consumed")
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("quantity_consumed must be positive")
        return v


class ConsumptionRead(BaseModel):
    """Schema for returning a material consumption record."""

    id: UUID
    material_lot_id: UUID
    unit_id: UUID | None = None
    lot_id: UUID | None = None
    step_id: UUID | None = None
    quantity_consumed: float
    consumed_at: datetime
    consumed_at_utc: datetime | None = None
    created_at: datetime
    created_at_utc: datetime | None = None

    model_config = {"from_attributes": True}
