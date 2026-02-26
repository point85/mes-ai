"""
QUAL-MGMT: Pydantic schemas for the Quality Management REST API.

Create / Read / Update schemas for QualityTest, TestResult, NonConformance.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── Valid constants ──────────────────────────────────────────────────

TEST_TYPES = {"inline", "offline", "destructive"}
TEST_RESULTS = {"pass", "fail"}
NC_TYPES = {"defect", "out_of_spec", "other"}
DISPOSITIONS = {"rework", "scrap", "use_as_is", "return"}
NC_STATUSES = {"open", "investigating", "resolved", "closed"}

# Allowed status transitions for non-conformance workflow
NC_TRANSITIONS: dict[str, set[str]] = {
    "open": {"investigating", "resolved", "closed"},
    "investigating": {"resolved", "closed"},
    "resolved": {"closed"},
    "closed": set(),
}


# ═══════════════════════════════════════════════════════════════════
# QualityTest
# ═══════════════════════════════════════════════════════════════════


class QualityTestCreate(BaseModel):
    """Schema for creating a quality test definition."""

    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    test_type: str = Field("inline", description="inline, offline, destructive")
    step_id: UUID | None = None
    parameters: dict | None = None

    @field_validator("code")
    @classmethod
    def code_no_whitespace(cls, v: str) -> str:
        if " " in v:
            raise ValueError("code must not contain spaces")
        return v

    @field_validator("test_type")
    @classmethod
    def validate_test_type(cls, v: str) -> str:
        if v not in TEST_TYPES:
            raise ValueError(f"test_type must be one of {TEST_TYPES}")
        return v


class QualityTestRead(BaseModel):
    """Schema for returning a quality test definition."""

    id: UUID
    name: str
    code: str
    description: str | None = None
    test_type: str
    step_id: UUID | None = None
    parameters: dict | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QualityTestUpdate(BaseModel):
    """Schema for updating a quality test definition. All fields optional."""

    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = None
    test_type: str | None = None
    step_id: UUID | None = None
    parameters: dict | None = None

    @field_validator("code")
    @classmethod
    def code_no_whitespace(cls, v: str | None) -> str | None:
        if v is not None and " " in v:
            raise ValueError("code must not contain spaces")
        return v

    @field_validator("test_type")
    @classmethod
    def validate_test_type(cls, v: str | None) -> str | None:
        if v is not None and v not in TEST_TYPES:
            raise ValueError(f"test_type must be one of {TEST_TYPES}")
        return v


# ═══════════════════════════════════════════════════════════════════
# TestResult
# ═══════════════════════════════════════════════════════════════════


class RecordResultRequest(BaseModel):
    """Schema for recording a quality test result."""

    test_id: UUID
    unit_id: UUID | None = None
    lot_id: UUID | None = None
    result: str = Field(..., description="pass or fail")
    measured_values: dict | None = None
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
    """Schema for returning a test result."""

    id: UUID
    test_id: UUID
    unit_id: UUID | None = None
    lot_id: UUID | None = None
    result: str
    measured_values: dict | None = None
    operator_id: UUID | None = None
    equipment_id: UUID | None = None
    tested_at: datetime
    notes: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════════
# NonConformance
# ═══════════════════════════════════════════════════════════════════


class NonConformanceCreate(BaseModel):
    """Schema for creating a non-conformance record."""

    unit_id: UUID | None = None
    lot_id: UUID | None = None
    step_id: UUID | None = None
    nc_type: str = Field(..., description="defect, out_of_spec, other")
    description: str = Field(..., min_length=1)

    @field_validator("nc_type")
    @classmethod
    def validate_nc_type(cls, v: str) -> str:
        if v not in NC_TYPES:
            raise ValueError(f"nc_type must be one of {NC_TYPES}")
        return v


class NonConformanceRead(BaseModel):
    """Schema for returning a non-conformance record."""

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

    model_config = {"from_attributes": True}


class NonConformanceUpdate(BaseModel):
    """Schema for updating a non-conformance (resolve / disposition)."""

    status: str | None = None
    disposition: str | None = None
    resolved_by_id: UUID | None = None
    description: str | None = None

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
