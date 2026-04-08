"""
DATA-COLLECT: Pydantic schemas for the Data Collection REST API.

Create / Read / Update schemas for DataDefinition and DataPoint,
plus CollectRequest and CollectBatchRequest action schemas.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── Valid constants ──────────────────────────────────────────────────

DATA_TYPES = {"numeric", "string", "boolean", "enum"}
DATA_SOURCES = {"manual", "equipment", "sensor"}


# ═══════════════════════════════════════════════════════════════════
# DataDefinition
# ═══════════════════════════════════════════════════════════════════


class DataDefinitionCreate(BaseModel):
    """Schema for creating a new data definition."""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    data_type: str = Field("numeric", description="numeric, string, boolean, enum")
    uom: str | None = Field(None, max_length=20)
    step_id: UUID | None = None
    source: str = Field("manual", description="manual, equipment, sensor")
    is_required: bool = False
    enum_values: str | None = Field(None, description="Comma-separated allowed values for enum type")
    lower_limit: float | None = None
    upper_limit: float | None = None

    @field_validator("code")
    @classmethod
    def code_no_whitespace(cls, v: str) -> str:
        if " " in v:
            raise ValueError("code must not contain spaces")
        return v

    @field_validator("data_type")
    @classmethod
    def validate_data_type(cls, v: str) -> str:
        if v not in DATA_TYPES:
            raise ValueError(f"data_type must be one of {DATA_TYPES}")
        return v

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        if v not in DATA_SOURCES:
            raise ValueError(f"source must be one of {DATA_SOURCES}")
        return v


class DataDefinitionRead(BaseModel):
    """Schema for returning a data definition."""

    id: UUID
    name: str
    code: str
    description: str | None = None
    data_type: str
    uom: str | None = None
    step_id: UUID | None = None
    source: str
    is_required: bool
    enum_values: str | None = None
    lower_limit: float | None = None
    upper_limit: float | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DataDefinitionUpdate(BaseModel):
    """Schema for updating a data definition. All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = None
    data_type: str | None = None
    uom: str | None = Field(None, max_length=20)
    step_id: UUID | None = None
    source: str | None = None
    is_required: bool | None = None
    enum_values: str | None = None
    lower_limit: float | None = None
    upper_limit: float | None = None

    @field_validator("code")
    @classmethod
    def code_no_whitespace(cls, v: str | None) -> str | None:
        if v is not None and " " in v:
            raise ValueError("code must not contain spaces")
        return v

    @field_validator("data_type")
    @classmethod
    def validate_data_type(cls, v: str | None) -> str | None:
        if v is not None and v not in DATA_TYPES:
            raise ValueError(f"data_type must be one of {DATA_TYPES}")
        return v

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str | None) -> str | None:
        if v is not None and v not in DATA_SOURCES:
            raise ValueError(f"source must be one of {DATA_SOURCES}")
        return v


# ═══════════════════════════════════════════════════════════════════
# DataPoint — collection
# ═══════════════════════════════════════════════════════════════════


class CollectRequest(BaseModel):
    """Request to collect a single data point."""

    definition_id: UUID
    unit_id: UUID | None = Field(None, description="WIP unit this data belongs to")
    lot_id: UUID | None = Field(None, description="WIP lot this data belongs to")
    value_numeric: float | None = None
    value_string: str | None = None
    value_boolean: bool | None = None
    source_equipment_id: UUID | None = None
    operator_id: UUID | None = None


class CollectBatchRequest(BaseModel):
    """Request to collect multiple data points in a single call."""

    items: list[CollectRequest] = Field(..., min_length=1, max_length=100)


class DataPointRead(BaseModel):
    """Schema for returning a collected data point."""

    id: UUID
    definition_id: UUID
    unit_id: UUID | None = None
    lot_id: UUID | None = None
    value_numeric: float | None = None
    value_string: str | None = None
    value_boolean: bool | None = None
    collected_at: datetime
    collected_at_utc: datetime | None = None
    source_equipment_id: UUID | None = None
    operator_id: UUID | None = None
    is_active: bool
    created_at: datetime
    created_at_utc: datetime | None = None
    updated_at: datetime
    updated_at_utc: datetime | None = None

    model_config = {"from_attributes": True}
