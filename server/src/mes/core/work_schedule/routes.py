"""
Work Schedule: FastAPI routes.

All endpoints sit under /api/v1/work-schedules/...
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mes.framework.api.responses import list_response, success_response
from mes.framework.auth.dependencies import require_permission
from mes.framework.auth.models import User
from mes.framework.db import get_db_session

from .models import RotationSegment
from .schemas import (
    NonWorkingPeriodCreate,
    NonWorkingPeriodRead,
    NonWorkingPeriodUpdate,
    RotationSegmentCreate,
    RotationSegmentRead,
    ShiftBreakCreate,
    ShiftBreakRead,
    ShiftInstanceResult,
    TeamMemberCreate,
    TeamMemberExceptionCreate,
    TeamMemberExceptionRead,
    TeamMemberRead,
    WorkRotationCreate,
    WorkRotationRead,
    WorkRotationUpdate,
    WorkScheduleCreate,
    WorkScheduleRead,
    WorkScheduleSummary,
    WorkScheduleUpdate,
    WorkShiftCreate,
    WorkShiftRead,
    WorkShiftUpdate,
    WorkTeamCreate,
    WorkTeamRead,
    WorkTeamUpdate,
)
from .service import WorkScheduleService

router = APIRouter(prefix="/api/v1/work-schedules", tags=["Work Schedules"])
svc = WorkScheduleService


# ═══════════════════════════════════════════════════════════════════
# WorkSchedule CRUD
# ═══════════════════════════════════════════════════════════════════

@router.get("", response_model=None)
async def list_schedules(
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.read")),
):
    """List all active work schedules (summary)."""
    items = await svc.list_schedules(session)
    data = [
        WorkScheduleSummary(
            id=s.id, name=s.name, description=s.description,
            is_active=s.is_active,
            shift_count=len(s.shifts),
            team_count=len(s.teams),
            created_at=s.created_at, updated_at=s.updated_at,
        ).model_dump()
        for s in items
    ]
    return list_response(data)


@router.post("", status_code=201)
async def create_schedule(
    body: WorkScheduleCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.create")),
):
    schedule = await svc.create_schedule(session, **body.model_dump())
    await session.commit()
    schedule = await svc.get_schedule(session, schedule.id)
    return success_response(WorkScheduleRead.model_validate(schedule).model_dump())


@router.get("/{schedule_id}")
async def get_schedule(
    schedule_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.read")),
):
    schedule = await svc.get_schedule(session, schedule_id)
    return success_response(WorkScheduleRead.model_validate(schedule).model_dump())


@router.patch("/{schedule_id}")
async def update_schedule(
    schedule_id: UUID,
    body: WorkScheduleUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.update")),
):
    schedule = await svc.update_schedule(session, schedule_id, **body.model_dump(exclude_none=True))
    await session.commit()
    schedule = await svc.get_schedule(session, schedule.id)
    return success_response(WorkScheduleRead.model_validate(schedule).model_dump())


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.delete")),
):
    await svc.delete_schedule(session, schedule_id)
    await session.commit()


# ═══════════════════════════════════════════════════════════════════
# Shifts
# ═══════════════════════════════════════════════════════════════════

@router.get("/{schedule_id}/shifts")
async def list_shifts(
    schedule_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.read")),
):
    items = await svc.list_shifts(session, schedule_id)
    return list_response([WorkShiftRead.model_validate(s).model_dump() for s in items])


@router.post("/{schedule_id}/shifts", status_code=201)
async def create_shift(
    schedule_id: UUID,
    body: WorkShiftCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.create")),
):
    shift = await svc.create_shift(session, schedule_id, **body.model_dump())
    await session.commit()
    shift = await svc.get_shift(session, shift.id)
    return success_response(WorkShiftRead.model_validate(shift).model_dump())


@router.patch("/{schedule_id}/shifts/{shift_id}")
async def update_shift(
    schedule_id: UUID,
    shift_id: UUID,
    body: WorkShiftUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.update")),
):
    shift = await svc.update_shift(session, shift_id, **body.model_dump(exclude_none=True))
    await session.commit()
    shift = await svc.get_shift(session, shift.id)
    return success_response(WorkShiftRead.model_validate(shift).model_dump())


@router.delete("/{schedule_id}/shifts/{shift_id}", status_code=204)
async def delete_shift(
    schedule_id: UUID,
    shift_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.delete")),
):
    await svc.delete_shift(session, shift_id)
    await session.commit()


# ─── Shift Breaks ────────────────────────────────────────────────────────────

@router.post("/{schedule_id}/shifts/{shift_id}/breaks", status_code=201)
async def add_break(
    schedule_id: UUID,
    shift_id: UUID,
    body: ShiftBreakCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.create")),
):
    brk = await svc.add_break(session, shift_id, **body.model_dump())
    await session.commit()
    return success_response(ShiftBreakRead.model_validate(brk).model_dump())


@router.delete("/{schedule_id}/shifts/{shift_id}/breaks/{break_id}", status_code=204)
async def delete_break(
    schedule_id: UUID,
    shift_id: UUID,
    break_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.delete")),
):
    await svc.delete_break(session, break_id)
    await session.commit()


# ═══════════════════════════════════════════════════════════════════
# Rotations
# ═══════════════════════════════════════════════════════════════════

@router.get("/{schedule_id}/rotations")
async def list_rotations(
    schedule_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.read")),
):
    items = await svc.list_rotations(session, schedule_id)
    return list_response([WorkRotationRead.model_validate(r).model_dump() for r in items])


@router.post("/{schedule_id}/rotations", status_code=201)
async def create_rotation(
    schedule_id: UUID,
    body: WorkRotationCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.create")),
):
    rotation = await svc.create_rotation(session, schedule_id, name=body.name, description=body.description)
    # add segments if provided
    for seg in body.segments:
        await svc.add_rotation_segment(
            session, rotation.id,
            shift_id=seg.shift_id, days_on=seg.days_on,
            days_off=seg.days_off, sequence=seg.sequence,
        )
    await session.commit()
    rotation = await svc.get_rotation(session, rotation.id)
    return success_response(WorkRotationRead.model_validate(rotation).model_dump())


@router.patch("/{schedule_id}/rotations/{rotation_id}")
async def update_rotation(
    schedule_id: UUID,
    rotation_id: UUID,
    body: WorkRotationUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.update")),
):
    rotation = await svc.update_rotation(session, rotation_id, **body.model_dump(exclude_none=True))
    await session.commit()
    rotation = await svc.get_rotation(session, rotation.id)
    return success_response(WorkRotationRead.model_validate(rotation).model_dump())


@router.delete("/{schedule_id}/rotations/{rotation_id}", status_code=204)
async def delete_rotation(
    schedule_id: UUID,
    rotation_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.delete")),
):
    await svc.delete_rotation(session, rotation_id)
    await session.commit()


# ─── Rotation Segments ───────────────────────────────────────────────────────

@router.post("/{schedule_id}/rotations/{rotation_id}/segments", status_code=201)
async def add_segment(
    schedule_id: UUID,
    rotation_id: UUID,
    body: RotationSegmentCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.create")),
):
    seg = await svc.add_rotation_segment(
        session, rotation_id,
        shift_id=body.shift_id, days_on=body.days_on,
        days_off=body.days_off, sequence=body.sequence,
    )
    seg_id = seg.id
    await session.commit()
    # Re-fetch after commit to get shift relationship loaded (avoids lazy load in Pydantic)
    result = await session.execute(
        select(RotationSegment)
        .where(RotationSegment.id == seg_id)
        .options(selectinload(RotationSegment.shift))
    )
    seg = result.scalar_one()
    return success_response(RotationSegmentRead.model_validate(seg).model_dump())


@router.delete("/{schedule_id}/rotations/{rotation_id}/segments/{segment_id}", status_code=204)
async def delete_segment(
    schedule_id: UUID,
    rotation_id: UUID,
    segment_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.delete")),
):
    await svc.delete_rotation_segment(session, segment_id)
    await session.commit()


# ═══════════════════════════════════════════════════════════════════
# Teams
# ═══════════════════════════════════════════════════════════════════

@router.get("/{schedule_id}/teams")
async def list_teams(
    schedule_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.read")),
):
    items = await svc.list_teams(session, schedule_id)
    return list_response([WorkTeamRead.model_validate(t).model_dump() for t in items])


@router.post("/{schedule_id}/teams", status_code=201)
async def create_team(
    schedule_id: UUID,
    body: WorkTeamCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.create")),
):
    team = await svc.create_team(session, schedule_id, **body.model_dump())
    await session.commit()
    team = await svc.get_team(session, team.id)
    return success_response(WorkTeamRead.model_validate(team).model_dump())


@router.patch("/{schedule_id}/teams/{team_id}")
async def update_team(
    schedule_id: UUID,
    team_id: UUID,
    body: WorkTeamUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.update")),
):
    team = await svc.update_team(session, team_id, **body.model_dump(exclude_none=True))
    await session.commit()
    team = await svc.get_team(session, team.id)
    return success_response(WorkTeamRead.model_validate(team).model_dump())


@router.delete("/{schedule_id}/teams/{team_id}", status_code=204)
async def delete_team(
    schedule_id: UUID,
    team_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.delete")),
):
    await svc.delete_team(session, team_id)
    await session.commit()


# ─── Team Members ────────────────────────────────────────────────────────────

@router.post("/{schedule_id}/teams/{team_id}/members", status_code=201)
async def add_team_member(
    schedule_id: UUID,
    team_id: UUID,
    body: TeamMemberCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.create")),
):
    member = await svc.add_team_member(session, team_id, **body.model_dump())
    await session.commit()
    return success_response(TeamMemberRead.model_validate(member).model_dump())


@router.delete("/{schedule_id}/teams/{team_id}/members/{member_pk}", status_code=204)
async def delete_team_member(
    schedule_id: UUID,
    team_id: UUID,
    member_pk: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.delete")),
):
    await svc.delete_team_member(session, member_pk)
    await session.commit()


# ─── Team Member Exceptions ──────────────────────────────────────────────────

@router.post("/{schedule_id}/teams/{team_id}/exceptions", status_code=201)
async def add_member_exception(
    schedule_id: UUID,
    team_id: UUID,
    body: TeamMemberExceptionCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.create")),
):
    exc = await svc.add_member_exception(session, team_id, **body.model_dump())
    await session.commit()
    return success_response(TeamMemberExceptionRead.model_validate(exc).model_dump())


@router.delete("/{schedule_id}/teams/{team_id}/exceptions/{exception_id}", status_code=204)
async def delete_member_exception(
    schedule_id: UUID,
    team_id: UUID,
    exception_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.delete")),
):
    await svc.delete_member_exception(session, exception_id)
    await session.commit()


# ═══════════════════════════════════════════════════════════════════
# Non-Working Periods
# ═══════════════════════════════════════════════════════════════════

@router.get("/{schedule_id}/non-working-periods")
async def list_non_working_periods(
    schedule_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.read")),
):
    items = await svc.list_non_working_periods(session, schedule_id)
    return list_response([NonWorkingPeriodRead.model_validate(p).model_dump() for p in items])


@router.post("/{schedule_id}/non-working-periods", status_code=201)
async def create_non_working_period(
    schedule_id: UUID,
    body: NonWorkingPeriodCreate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.create")),
):
    period = await svc.create_non_working_period(session, schedule_id, **body.model_dump())
    await session.commit()
    return success_response(NonWorkingPeriodRead.model_validate(period).model_dump())


@router.patch("/{schedule_id}/non-working-periods/{period_id}")
async def update_non_working_period(
    schedule_id: UUID,
    period_id: UUID,
    body: NonWorkingPeriodUpdate,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.update")),
):
    period = await svc.update_non_working_period(session, period_id, **body.model_dump(exclude_none=True))
    await session.commit()
    return success_response(NonWorkingPeriodRead.model_validate(period).model_dump())


@router.delete("/{schedule_id}/non-working-periods/{period_id}", status_code=204)
async def delete_non_working_period(
    schedule_id: UUID,
    period_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.delete")),
):
    await svc.delete_non_working_period(session, period_id)
    await session.commit()


# ═══════════════════════════════════════════════════════════════════
# Query endpoints
# ═══════════════════════════════════════════════════════════════════

@router.get("/{schedule_id}/shift-instances/day")
async def get_shift_instances_for_day(
    schedule_id: UUID,
    day: date = Query(..., description="Date in YYYY-MM-DD format"),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.read")),
):
    """Get all shift instances across all teams for a specific day."""
    instances = await svc.get_shift_instances_for_day(session, schedule_id, day)
    return list_response([i.model_dump() for i in instances])


@router.get("/{schedule_id}/shift-instances/range")
async def get_shift_instances_for_range(
    schedule_id: UUID,
    from_date: date = Query(...),
    to_date: date = Query(...),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.read")),
):
    """Get all shift instances for a date range (inclusive)."""
    instances = await svc.get_shift_instances_for_range(session, schedule_id, from_date, to_date)
    return list_response([i.model_dump() for i in instances])


@router.get("/{schedule_id}/working-time")
async def get_working_time(
    schedule_id: UUID,
    from_dt: datetime = Query(...),
    to_dt: datetime = Query(...),
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("work_schedule.read")),
):
    """Compute total working seconds across all teams in a datetime range."""
    delta = await svc.get_working_time(session, schedule_id, from_dt, to_dt)
    return success_response({"working_seconds": int(delta.total_seconds())})
