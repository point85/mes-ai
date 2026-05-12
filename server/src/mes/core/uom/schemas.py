"""
UOM: Pydantic schemas for the Unit of Measure REST API.

Five types: mass, length, time, temperature, other
Four classes:
    scalar   — affine conversion (y = a·x + b)
    quotient — left / right   (e.g. kg/s)
    product  — left × right   (e.g. kg·m)
    power    — left ^ exponent (e.g. m³)
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

UOM_TYPES = {"mass", "length", "time", "temperature", "electrical", "force", "amount_of_substance", "luminous_intensity", "other"}
UOM_CLASSES = {"scalar", "quotient", "product", "power"}


# ─── UnitOfMeasure CRUD ──────────────────────────────────────────────


class UoMCreate(BaseModel):
    """Schema for creating a new unit of measure."""

    symbol: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    uom_type: str = Field(..., min_length=1, max_length=50,
                          description="Primary dimension type: mass, length, time, temperature, other")
    uom_class: Literal["scalar", "quotient", "product", "power"] = "scalar"
    # Scalar fields
    multiplier: float = Field(1.0, gt=0, description="Affine multiplier (scalar class)")
    offset: float = Field(0.0, description="Affine offset (scalar class)")
    # Composite component fields
    left_uom_symbol: str | None = Field(
        None, description="Left component: numerator (quotient), first factor (product), base (power)",
    )
    right_uom_symbol: str | None = Field(
        None, description="Right component: denominator (quotient), second factor (product)",
    )
    exponent: int | None = Field(None, ge=2, description="Integer exponent (power class only)")

    @field_validator("symbol")
    @classmethod
    def symbol_no_whitespace(cls, v: str) -> str:
        if " " in v:
            raise ValueError("symbol must not contain spaces")
        return v

    @field_validator("uom_type")
    @classmethod
    def valid_uom_type(cls, v: str) -> str:
        if v not in UOM_TYPES:
            raise ValueError(f"uom_type must be one of {sorted(UOM_TYPES)}")
        return v

    @model_validator(mode="after")
    def validate_class_fields(self) -> UoMCreate:
        cls_ = self.uom_class
        left = self.left_uom_symbol
        right = self.right_uom_symbol
        exp = self.exponent
        if cls_ == "scalar":
            if left or right or exp is not None:
                raise ValueError("scalar UoMs must not set left/right/exponent")
        elif cls_ == "quotient":
            if not left or not right:
                raise ValueError("quotient UoMs require both left_uom_symbol and right_uom_symbol")
            if exp is not None:
                raise ValueError("exponent is only valid for power UoMs")
        elif cls_ == "product":
            if not left or not right:
                raise ValueError("product UoMs require both left_uom_symbol and right_uom_symbol")
            if exp is not None:
                raise ValueError("exponent is only valid for power UoMs")
        elif cls_ == "power":
            if not left:
                raise ValueError("power UoMs require left_uom_symbol (the base unit)")
            if right:
                raise ValueError("power UoMs must not set right_uom_symbol")
            if exp is None:
                raise ValueError("power UoMs require an exponent (>= 2)")
        return self


class UoMRead(BaseModel):
    """Schema for returning a unit of measure."""

    id: UUID
    symbol: str
    name: str
    description: str | None = None
    uom_type: str
    uom_class: str
    multiplier: float
    offset: float
    is_builtin: bool
    is_active: bool
    left_uom_id: UUID | None = None
    right_uom_id: UUID | None = None
    left_uom_symbol: str | None = None
    right_uom_symbol: str | None = None
    left_uom_type: str | None = None
    right_uom_type: str | None = None
    exponent: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UoMUpdate(BaseModel):
    """Schema for updating a unit of measure. All fields optional."""

    symbol: str | None = Field(None, min_length=1, max_length=20)
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    uom_type: str | None = Field(None, min_length=1, max_length=50)
    uom_class: Literal["scalar", "quotient", "product", "power"] | None = None
    multiplier: float | None = Field(None, gt=0)
    offset: float | None = None
    left_uom_symbol: str | None = None
    right_uom_symbol: str | None = None
    exponent: int | None = Field(None, ge=2)

    @field_validator("symbol")
    @classmethod
    def symbol_no_whitespace(cls, v: str | None) -> str | None:
        if v is not None and " " in v:
            raise ValueError("symbol must not contain spaces")
        return v

    @field_validator("uom_type")
    @classmethod
    def valid_uom_type(cls, v: str | None) -> str | None:
        if v is not None and v not in UOM_TYPES:
            raise ValueError(f"uom_type must be one of {sorted(UOM_TYPES)}")
        return v


# ─── Conversion ──────────────────────────────────────────────────────


class ConversionRequest(BaseModel):
    """Request to convert a value between two units."""

    value: float
    from_symbol: str = Field(..., min_length=1)
    to_symbol: str = Field(..., min_length=1)


class ConversionResult(BaseModel):
    """Result of a unit conversion."""

    original_value: float
    from_symbol: str
    from_name: str
    converted_value: float
    to_symbol: str
    to_name: str
