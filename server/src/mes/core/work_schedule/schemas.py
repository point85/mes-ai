"""
Work Schedule: Pydantic schemas for REST API.
"""

from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# ShiftBreak
# ─────────────────────────────────────────────────────────────────────────────

class ShiftBreakCreate(BaseModel):
    name: str
    description: str | None = None
    start_time: time
    duration_seconds: int = Field(gt=0, le=86400)


class ShiftBreakRead(BaseModel):
    id: UUID
    shift_id: UUID
    name: str
    description: str | None
    start_time: time
    duration_seconds: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShiftBreakUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    start_time: time | None = None
    duration_seconds: int | None = Field(None, gt=0, le=86400)


# ─────────────────────────────────────────────────────────────────────────────
# WorkShift
# ─────────────────────────────────────────────────────────────────────────────

class WorkShiftCreate(BaseModel):
    name: str
    description: str | None = None
    start_time: time
    duration_seconds: int = Field(gt=0, le=86400)


class WorkShiftRead(BaseModel):
    id: UUID
    work_schedule_id: UUID
    name: str
    description: str | None
    start_time: time
    duration_seconds: int
    breaks: list[ShiftBreakRead] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkShiftUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    start_time: time | None = None
    duration_seconds: int | None = Field(None, gt=0, le=86400)


# ─────────────────────────────────────────────────────────────────────────────
# RotationSegment
# ─────────────────────────────────────────────────────────────────────────────

class RotationSegmentCreate(BaseModel):
    shift_id: UUID
    days_on: int = Field(ge=1)
    days_off: int = Field(ge=0)
    sequence: int = Field(ge=1)


class RotationSegmentRead(BaseModel):
    id: UUID
    rotation_id: UUID
    shift_id: UUID
    shift_name: str | None = None
    days_on: int
    days_off: int
    sequence: int

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def extract_shift_name(cls, data: object) -> object:
        if isinstance(data, dict):
            return data
        # Access shift via __dict__ to avoid triggering SQLAlchemy async lazy load.
        # If the relationship is already loaded it will be in __dict__; if expired
        # it won't be, and shift_name stays None until the caller re-fetches.
        raw_dict = getattr(data, "__dict__", {})
        shift = raw_dict.get("shift")  # type: ignore[union-attr]
        return {
            "id": raw_dict.get("id"),
            "rotation_id": raw_dict.get("rotation_id"),
            "shift_id": raw_dict.get("shift_id"),
            "shift_name": shift.name if shift is not None else None,
            "days_on": raw_dict.get("days_on"),
            "days_off": raw_dict.get("days_off"),
            "sequence": raw_dict.get("sequence"),
            "is_active": raw_dict.get("is_active", True),
        }


class RotationSegmentUpdate(BaseModel):
    shift_id: UUID | None = None
    days_on: int | None = Field(None, ge=1)
    days_off: int | None = Field(None, ge=0)
    sequence: int | None = Field(None, ge=1)


# ─────────────────────────────────────────────────────────────────────────────
# WorkRotation
# ─────────────────────────────────────────────────────────────────────────────

class WorkRotationCreate(BaseModel):
    name: str
    description: str | None = None
    segments: list[RotationSegmentCreate] = []


class WorkRotationRead(BaseModel):
    id: UUID
    work_schedule_id: UUID
    name: str
    description: str | None
    segments: list[RotationSegmentRead] = []
    day_count: int = 0
    working_seconds: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkRotationUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# TeamMember
# ─────────────────────────────────────────────────────────────────────────────

class TeamMemberCreate(BaseModel):
    member_id: str
    name: str
    description: str | None = None


class TeamMemberRead(BaseModel):
    id: UUID
    team_id: UUID
    member_id: str
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TeamMemberUpdate(BaseModel):
    member_id: str | None = None
    name: str | None = None
    description: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# TeamMemberException
# ─────────────────────────────────────────────────────────────────────────────

class TeamMemberExceptionCreate(BaseModel):
    shift_start: datetime
    add_member_id: UUID | None = None
    remove_member_id: UUID | None = None
    reason: str | None = None


class TeamMemberExceptionRead(BaseModel):
    id: UUID
    team_id: UUID
    shift_start: datetime
    add_member_id: UUID | None
    remove_member_id: UUID | None
    reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# WorkTeam
# ─────────────────────────────────────────────────────────────────────────────

class WorkTeamCreate(BaseModel):
    name: str
    description: str | None = None
    rotation_id: UUID
    rotation_start: date


class WorkTeamRead(BaseModel):
    id: UUID
    work_schedule_id: UUID
    name: str
    description: str | None
    rotation_id: UUID
    rotation_start: date
    members: list[TeamMemberRead] = []
    member_exceptions: list[TeamMemberExceptionRead] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkTeamUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    rotation_id: UUID | None = None
    rotation_start: date | None = None


# ─────────────────────────────────────────────────────────────────────────────
# NonWorkingPeriod
# ─────────────────────────────────────────────────────────────────────────────

class NonWorkingPeriodCreate(BaseModel):
    name: str
    description: str | None = None
    start_datetime: datetime
    duration_seconds: int = Field(gt=0)


class NonWorkingPeriodRead(BaseModel):
    id: UUID
    work_schedule_id: UUID
    name: str
    description: str | None
    start_datetime: datetime
    duration_seconds: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NonWorkingPeriodUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    start_datetime: datetime | None = None
    duration_seconds: int | None = Field(None, gt=0)


# ─────────────────────────────────────────────────────────────────────────────
# WorkSchedule
# ─────────────────────────────────────────────────────────────────────────────

class WorkScheduleCreate(BaseModel):
    name: str
    description: str | None = None


class WorkScheduleRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    shifts: list[WorkShiftRead] = []
    rotations: list[WorkRotationRead] = []
    teams: list[WorkTeamRead] = []
    non_working_periods: list[NonWorkingPeriodRead] = []
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkScheduleSummary(BaseModel):
    """Lightweight schedule record for list views."""
    id: UUID
    name: str
    description: str | None
    is_active: bool
    shift_count: int = 0
    team_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkScheduleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Query results
# ─────────────────────────────────────────────────────────────────────────────

class ShiftInstanceResult(BaseModel):
    """Computed shift instance for a given day/datetime."""
    date: date
    team_id: UUID
    team_name: str
    shift_id: UUID
    shift_name: str
    start_datetime: datetime
    end_datetime: datetime
