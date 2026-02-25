"""
UOM: Pydantic schemas for the Unit of Measure REST API.

Create / Read / Update schemas for UnitOfMeasure, plus a ConversionRequest/Result pair.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ─── UnitOfMeasure CRUD ──────────────────────────────────────────────


class UoMCreate(BaseModel):
    """Schema for creating a new unit of measure."""

    symbol: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    uom_type: str = Field(..., min_length=1, max_length=50)
    multiplier: float = Field(1.0, gt=0, description="Must be > 0")
    offset: float = Field(0.0)

    @field_validator("symbol")
    @classmethod
    def symbol_no_whitespace(cls, v: str) -> str:
        if " " in v:
            raise ValueError("symbol must not contain spaces")
        return v


class UoMRead(BaseModel):
    """Schema for returning a unit of measure."""

    id: UUID
    symbol: str
    name: str
    description: str | None = None
    uom_type: str
    multiplier: float
    offset: float
    is_builtin: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UoMUpdate(BaseModel):
    """Schema for updating a unit of measure. All fields optional."""

    symbol: str | None = Field(None, min_length=1, max_length=20)
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    uom_type: str | None = Field(None, min_length=1, max_length=50)
    multiplier: float | None = Field(None, gt=0)
    offset: float | None = None

    @field_validator("symbol")
    @classmethod
    def symbol_no_whitespace(cls, v: str | None) -> str | None:
        if v is not None and " " in v:
            raise ValueError("symbol must not contain spaces")
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
