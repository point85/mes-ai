"""
INVENTORY: Pydantic schemas for the Inventory Management REST API.

Create / Read / Update schemas for StorageLocation, InventoryBalance,
InventoryTransaction, plus action schemas for inventory operations.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── Valid constants ──────────────────────────────────────────────────

LOCATION_TYPES = {"receiving", "storage", "rip", "staging", "shipping"}
TRANSACTION_TYPES = {"receive", "putaway", "pick", "move", "consume", "adjust"}
REFERENCE_TYPES = {"operations_request", "unit", "lot"}


# ═══════════════════════════════════════════════════════════════════
# StorageLocation
# ═══════════════════════════════════════════════════════════════════


class StorageLocationCreate(BaseModel):
    """Schema for creating a new storage location."""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    location_type: str = Field("storage", description="receiving, storage, rip, staging, shipping")
    aisle: str | None = Field(None, max_length=20)
    bay: str | None = Field(None, max_length=20)
    tier: str | None = Field(None, max_length=20)
    site_id: UUID | None = None
    capacity: float | None = Field(None, gt=0)

    @field_validator("code")
    @classmethod
    def code_no_whitespace(cls, v: str) -> str:
        if " " in v:
            raise ValueError("code must not contain spaces")
        return v

    @field_validator("location_type")
    @classmethod
    def validate_location_type(cls, v: str) -> str:
        if v not in LOCATION_TYPES:
            raise ValueError(f"location_type must be one of {LOCATION_TYPES}")
        return v


class StorageLocationRead(BaseModel):
    """Schema for returning a storage location."""

    id: UUID
    name: str
    code: str
    description: str | None = None
    location_type: str
    aisle: str | None = None
    bay: str | None = None
    tier: str | None = None
    site_id: UUID | None = None
    capacity: float | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StorageLocationUpdate(BaseModel):
    """Schema for updating a storage location. All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = None
    location_type: str | None = None
    aisle: str | None = Field(None, max_length=20)
    bay: str | None = Field(None, max_length=20)
    tier: str | None = Field(None, max_length=20)
    site_id: UUID | None = None
    capacity: float | None = Field(None, gt=0)

    @field_validator("code")
    @classmethod
    def code_no_whitespace(cls, v: str | None) -> str | None:
        if v is not None and " " in v:
            raise ValueError("code must not contain spaces")
        return v

    @field_validator("location_type")
    @classmethod
    def validate_location_type(cls, v: str | None) -> str | None:
        if v is not None and v not in LOCATION_TYPES:
            raise ValueError(f"location_type must be one of {LOCATION_TYPES}")
        return v


# ═══════════════════════════════════════════════════════════════════
# InventoryBalance
# ═══════════════════════════════════════════════════════════════════


class InventoryBalanceRead(BaseModel):
    """Schema for returning an inventory balance."""

    id: UUID
    material_lot_id: UUID
    location_id: UUID
    quantity_on_hand: float
    quantity_reserved: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════
# InventoryTransaction
# ═══════════════════════════════════════════════════════════════════


class InventoryTransactionRead(BaseModel):
    """Schema for returning an inventory transaction."""

    id: UUID
    transaction_type: str
    material_lot_id: UUID
    from_location_id: UUID | None = None
    to_location_id: UUID | None = None
    quantity: float
    reference_id: UUID | None = None
    reference_type: str | None = None
    reason: str | None = None
    performed_at: datetime
    performed_at_utc: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════
# Action schemas (inventory operations)
# ═══════════════════════════════════════════════════════════════════


class ReceiveRequest(BaseModel):
    """Receive material into a receiving location (creates inventory)."""

    material_lot_id: UUID
    to_location_id: UUID
    quantity: float = Field(..., gt=0)
    reason: str | None = Field(None, max_length=255)
    reference_id: UUID | None = Field(None, description="Production order or PO reference")
    reference_type: str | None = None

    @field_validator("reference_type")
    @classmethod
    def validate_ref(cls, v: str | None) -> str | None:
        if v is not None and v not in REFERENCE_TYPES:
            raise ValueError(f"reference_type must be one of {REFERENCE_TYPES}")
        return v


class PutawayRequest(BaseModel):
    """Move material from receiving to a storage location (aisle/bay/tier)."""

    material_lot_id: UUID
    from_location_id: UUID
    to_location_id: UUID
    quantity: float = Field(..., gt=0)
    reason: str | None = Field(None, max_length=255)


class PickRequest(BaseModel):
    """Pick material from a storage location for production use."""

    material_lot_id: UUID
    from_location_id: UUID
    to_location_id: UUID
    quantity: float = Field(..., gt=0)
    reference_id: UUID | None = Field(None, description="Production order or WIP reference")
    reference_type: str | None = None
    reason: str | None = Field(None, max_length=255)

    @field_validator("reference_type")
    @classmethod
    def validate_ref(cls, v: str | None) -> str | None:
        if v is not None and v not in REFERENCE_TYPES:
            raise ValueError(f"reference_type must be one of {REFERENCE_TYPES}")
        return v


class MoveRequest(BaseModel):
    """Move material between any two locations."""

    material_lot_id: UUID
    from_location_id: UUID
    to_location_id: UUID
    quantity: float = Field(..., gt=0)
    reason: str | None = Field(None, max_length=255)
    reference_id: UUID | None = None
    reference_type: str | None = None

    @field_validator("reference_type")
    @classmethod
    def validate_ref(cls, v: str | None) -> str | None:
        if v is not None and v not in REFERENCE_TYPES:
            raise ValueError(f"reference_type must be one of {REFERENCE_TYPES}")
        return v


class ConsumeInventoryRequest(BaseModel):
    """Consume inventory from a location for WIP."""

    material_lot_id: UUID
    from_location_id: UUID
    quantity: float = Field(..., gt=0)
    reference_id: UUID | None = Field(None, description="WIP unit, lot, or production order reference")
    reference_type: str | None = None
    step_id: UUID | None = Field(None, description="Route step where consumption occurs (for genealogy)")
    reason: str | None = Field(None, max_length=255)

    @field_validator("reference_type")
    @classmethod
    def validate_ref(cls, v: str | None) -> str | None:
        if v is not None and v not in REFERENCE_TYPES:
            raise ValueError(f"reference_type must be one of {REFERENCE_TYPES}")
        return v


class AdjustRequest(BaseModel):
    """Manual inventory adjustment (cycle count correction)."""

    material_lot_id: UUID
    location_id: UUID
    quantity: float = Field(..., description="New absolute quantity (replaces current)")
    reason: str = Field(..., min_length=1, max_length=255, description="Mandatory reason for adjustment")
