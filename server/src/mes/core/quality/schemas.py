"""
QUAL-MGMT: Pydantic schemas for the Quality Management REST API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

# ── Constants ────────────────────────────────────────────────────────

TEST_TYPES: set[str] = {"inline", "offline", "destructive"}
TEST_RESULTS: set[str] = {"pass", "fail"}
NC_TYPES: set[str] = {"defect", "out_of_spec", "other"}
DISPOSITIONS: set[str] = {"rework", "scrap", "use_as_is", "return"}
NC_STATUSES: set[str] = {"open", "investigating", "resolved", "closed"}

NC_TRANSITIONS: dict[str, set[str]] = {
    "open": {"investigating", "resolved", "closed"},
    "investigating": {"resolved", "closed"},
    "resolved": {"closed"},
    "closed": set(),
}


# ═══════════════════════════════════════════════════════════════════
# QualityTest Schemas
# ═══════════════════════════════════════════════════════════════════


class QualityTestCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    test_type: str = Field("inline")
    step_id: UUID | None = None
    parameters: dict[str, Any] | None = None

    @field_validator("test_type")
    @classmethod
    def validate_test_type(cls, v: str) -> str:
        if v not in TEST_TYPES:
            raise ValueError(f"test_type must be one of {TEST_TYPES}")
        return v

    @field_validator("code")
    @classmethod
    def validate_code_no_spaces(cls, v: str) -> str:
        if " " in v:
            raise ValueError("code must not contain spaces")
        return v


class QualityTestRead(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    name: str
    code: str
    description: str | None = None
    test_type: str
    step_id: UUID | None = None
    parameters: dict[str, Any] | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class QualityTestUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = None
    description: str | None = None
    test_type: str | None = None
    step_id: UUID | None = None
    parameters: dict[str, Any] | None = None

    @field_validator("test_type")
    @classmethod
    def validate_test_type(cls, v: str | None) -> str | None:
        if v is not None and v not in TEST_TYPES:
            raise ValueError(f"test_type must be one of {TEST_TYPES}")
        return v


# ═══════════════════════════════════════════════════════════════════
# TestResult Schemas
# ═══════════════════════════════════════════════════════════════════


class RecordResultRequest(BaseModel):
    test_id: UUID
    unit_id: UUID | None = None
    lot_id: UUID | None = None
    result: str = Field(...)
    measured_values: dict[str, Any] | None = None
    operator_id: UUID | None = None
    equipment_id: UUID | None = None
    tested_at: datetime
    notes: str | None = None

    @field_validator("result")
    @classmethod
    def validate_result(cls, v: str) -> str:
        if v not in TEST_RESULTS:
            raise ValueError(f"result must be one of {TEST_RESULTS}")
        return v


class TestResultRead(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    test_id: UUID
    unit_id: UUID | None = None
    lot_id: UUID | None = None
    result: str
    measured_values: dict[str, Any] | None = None
    operator_id: UUID | None = None
    equipment_id: UUID | None = None
    tested_at: datetime
    notes: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ═══════════════════════════════════════════════════════════════════
# NonConformance Schemas
# ═══════════════════════════════════════════════════════════════════


class NonConformanceCreate(BaseModel):
    unit_id: UUID | None = None
    lot_id: UUID | None = None
    step_id: UUID | None = None
    nc_type: str = Field(...)
    description: str = Field(..., min_length=1)

    @field_validator("nc_type")
    @classmethod
    def validate_nc_type(cls, v: str) -> str:
        if v not in NC_TYPES:
            raise ValueError(f"nc_type must be one of {NC_TYPES}")
        return v


class NonConformanceRead(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    unit_id: UUID | None = None
    lot_id: UUID | None = None
    step_id: UUID | None = None
    nc_type: str
    description: str
    disposition: str | None = None
    status: str
    resolved_at: datetime | None = None
    resolved_by_id: UUID | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class NonConformanceUpdate(BaseModel):
    nc_type: str | None = None
    description: str | None = None
    disposition: str | None = None
    status: str | None = None
    resolved_at: datetime | None = None
    resolved_by_id: UUID | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in NC_STATUSES:
            raise ValueError(f"status must be one of {NC_STATUSES}")
        return v

    @field_validator("disposition")
    @classmethod
    def validate_disposition(cls, v: str | None) -> str | None:
        if v is not None and v not in DISPOSITIONS:
            raise ValueError(f"disposition must be one of {DISPOSITIONS}")
        return v
