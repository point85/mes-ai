"""
UOM: Pydantic schemas for the Unit of Measure REST API.

Create / Read / Update schemas for UnitOfMeasure, plus a ConversionRequest/Result pair.
Rate UoMs (uom_type="rate") reference a numerator and denominator UoM by symbol.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


# ─── UnitOfMeasure CRUD ──────────────────────────────────────────────


class UoMCreate(BaseModel):
    """Schema for creating a new unit of measure."""

    symbol: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    uom_type: str = Field(..., min_length=1, max_length=50)
    multiplier: float = Field(1.0, gt=0, description="Must be > 0")
    offset: float = Field(0.0)
    numerator_uom_symbol: str | None = Field(
        None, description="For rate UoMs: numerator unit symbol (e.g. EA in EA/h)",
    )
    denominator_uom_symbol: str | None = Field(
        None, description="For rate UoMs: denominator unit symbol (e.g. h in EA/h)",
    )

    @field_validator("symbol")
    @classmethod
    def symbol_no_whitespace(cls, v: str) -> str:
        if " " in v:
            raise ValueError("symbol must not contain spaces")
        return v

    @model_validator(mode="after")
    def rate_requires_both_components(self) -> UoMCreate:
        num = self.numerator_uom_symbol
        den = self.denominator_uom_symbol
        if self.uom_type == "rate":
            if not num or not den:
                raise ValueError("Rate UoMs require both numerator_uom_symbol and denominator_uom_symbol")
        else:
            if num or den:
                raise ValueError("numerator_uom_symbol and denominator_uom_symbol are only valid for rate UoMs (uom_type='rate')")
        return self


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
    numerator_uom_id: UUID | None = None
    denominator_uom_id: UUID | None = None
    numerator_uom_symbol: str | None = None
    denominator_uom_symbol: str | None = None
    numerator_uom_type: str | None = None
    denominator_uom_type: str | None = None
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
    numerator_uom_symbol: str | None = Field(
        None, description="For rate UoMs: numerator unit symbol",
    )
    denominator_uom_symbol: str | None = Field(
        None, description="For rate UoMs: denominator unit symbol",
    )

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
