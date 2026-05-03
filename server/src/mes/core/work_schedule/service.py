"""
Work Schedule: async CRUD service + domain computation helpers.

Domain logic ported from PyShift without localization.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, with_loader_criteria

from .exceptions import (
    DuplicateWorkScheduleNameException,
    NonWorkingPeriodNotFoundException,
    TeamMemberNotFoundException,
    WorkRotationNotFoundException,
    WorkScheduleNotFoundException,
    WorkShiftNotFoundException,
    WorkTeamNotFoundException,
)
from .models import (
    NonWorkingPeriod,
    RotationSegment,
    ShiftBreak,
    TeamMember,
    TeamMemberException,
    WorkRotation,
    WorkSchedule,
    WorkShift,
    WorkTeam,
)
from .schemas import ShiftInstanceResult


# ═══════════════════════════════════════════════════════════════════
# Load helpers
# ═══════════════════════════════════════════════════════════════════

def _schedule_options():
    """Eager-load all child collections for a WorkSchedule, filtering soft-deleted children."""
    return [
        # Exclude soft-deleted children from every relationship loaded below
        with_loader_criteria(WorkShift, WorkShift.is_active.is_(True), include_aliases=True),
        with_loader_criteria(ShiftBreak, ShiftBreak.is_active.is_(True), include_aliases=True),
        with_loader_criteria(WorkRotation, WorkRotation.is_active.is_(True), include_aliases=True),
        with_loader_criteria(RotationSegment, RotationSegment.is_active.is_(True), include_aliases=True),
        with_loader_criteria(WorkTeam, WorkTeam.is_active.is_(True), include_aliases=True),
        with_loader_criteria(TeamMember, TeamMember.is_active.is_(True), include_aliases=True),
        with_loader_criteria(NonWorkingPeriod, NonWorkingPeriod.is_active.is_(True), include_aliases=True),
        # Relationship load paths
        selectinload(WorkSchedule.shifts).selectinload(WorkShift.breaks),
        selectinload(WorkSchedule.rotations).selectinload(WorkRotation.segments).selectinload(RotationSegment.shift),
        selectinload(WorkSchedule.teams).selectinload(WorkTeam.members),
        selectinload(WorkSchedule.teams).selectinload(WorkTeam.member_exceptions),
        selectinload(WorkSchedule.teams).selectinload(WorkTeam.rotation).selectinload(WorkRotation.segments).selectinload(RotationSegment.shift),
        selectinload(WorkSchedule.non_working_periods),
    ]


# ═══════════════════════════════════════════════════════════════════
# Domain computation (ported from PyShift, no localization)
# ═══════════════════════════════════════════════════════════════════

def _to_epoch_day(d: date) -> int:
    return (d - date(1970, 1, 1)).days


def _day_in_rotation(team: WorkTeam, day: date) -> int:
    """Return the 1-based day index within the team's rotation for *day*."""
    day_to = _to_epoch_day(day)
    start = _to_epoch_day(team.rotation_start)
    delta = day_to - start
    if delta < 0:
        raise ValueError(f"Date {day} is before rotation start {team.rotation_start}")
    rotation_days = team.rotation.day_count
    if rotation_days == 0:
        rotation_days = 1
    return (delta % rotation_days) + 1


def _build_period_list(rotation: WorkRotation) -> list[WorkShift | None]:
    """
    Expand the rotation segments into an ordered list of periods (one entry per
    calendar day).  Working days hold the WorkShift instance; off days hold None.
    """
    periods: list[WorkShift | None] = []
    for seg in sorted(rotation.segments, key=lambda s: s.sequence):
        for _ in range(seg.days_on):
            periods.append(seg.shift)
        for _ in range(seg.days_off):
            periods.append(None)
    return periods


def _get_shift_instance_for_day(
    team: WorkTeam,
    day: date,
    non_working_periods: list[NonWorkingPeriod],
) -> ShiftInstanceResult | None:
    """Return a ShiftInstanceResult if the team is working on *day*, else None."""
    periods = _build_period_list(team.rotation)
    if not periods:
        return None

    idx = _day_in_rotation(team, day) - 1
    shift = periods[idx]
    if shift is None:
        return None

    # Check non-working periods
    for nwp in non_working_periods:
        nwp_start = nwp.start_datetime.date()
        nwp_end = nwp.end_datetime.date()
        if nwp_start <= day <= nwp_end:
            return None

    start_dt = datetime(day.year, day.month, day.day,
                        shift.start_time.hour,
                        shift.start_time.minute,
                        shift.start_time.second)
    end_dt = start_dt + shift.duration

    return ShiftInstanceResult(
        date=day,
        team_id=team.id,
        team_name=team.name,
        shift_id=shift.id,
        shift_name=shift.name,
        start_datetime=start_dt,
        end_datetime=end_dt,
    )


def compute_shift_instances_for_day(
    schedule: WorkSchedule, day: date,
) -> list[ShiftInstanceResult]:
    """Return all shift instances across all teams for the given day."""
    results: list[ShiftInstanceResult] = []
    for team in schedule.teams:
        if not team.is_active:
            continue
        instance = _get_shift_instance_for_day(team, day, schedule.non_working_periods)
        if instance:
            results.append(instance)
    results.sort(key=lambda x: x.start_datetime)
    return results


def compute_shift_instances_for_range(
    schedule: WorkSchedule, from_date: date, to_date: date,
) -> list[ShiftInstanceResult]:
    """Return all shift instances for every day in [from_date, to_date]."""
    results: list[ShiftInstanceResult] = []
    current = from_date
    while current <= to_date:
        results.extend(compute_shift_instances_for_day(schedule, current))
        current += timedelta(days=1)
    return results


def _to_rounded_second(t: time) -> int:
    """Convert a time to seconds of day, rounding up on >=500000 microseconds (matches PyShift)."""
    sec = t.hour * 3600 + t.minute * 60 + t.second
    if t.microsecond >= 500000:
        sec += 1
    return sec


def shift_spans_midnight(shift: WorkShift) -> bool:
    """
    Port of PyShift ``Shift.spansMidnight()``.

    NOTE: This intentionally differs from the model's ``WorkShift.spans_midnight``
    property -- PyShift considers a 24-hour shift to span midnight (because its
    rounded end-of-day second equals its start second), and the working-time
    algorithm depends on that behaviour. Domain code that mirrors PyShift must
    use this helper rather than the model property.
    """
    start_s = _to_rounded_second(shift.start_time)
    end_s = _to_rounded_second(shift.end_time)
    return end_s <= start_s


# Backwards-compatible private alias used internally.
_shift_spans_midnight = shift_spans_midnight


def is_time_in_shift(shift: WorkShift, t: time) -> bool:
    """Return True if *t* falls within the shift's working period (inclusive on both endpoints)."""
    start = _to_rounded_second(shift.start_time)
    end = _to_rounded_second(shift.end_time)
    t_sec = _to_rounded_second(t)

    if start < end:
        return start <= t_sec <= end
    # midnight-crossing or 24-hour shifts
    return t_sec >= start or t_sec <= end


def compute_shift_total_working_time(
    shift: WorkShift,
    from_time: time,
    to_time: time,
    before_midnight: bool = True,
) -> timedelta:
    """
    Port of PyShift ``Shift.calculateTotalWorkingTime()``.

    Returns the overlap of [from_time, to_time] with the shift's working period.
    For midnight-crossing shifts, *before_midnight* picks which side of midnight
    a wrap-around interval belongs to.
    """
    start_s = _to_rounded_second(shift.start_time)
    end_s = _to_rounded_second(shift.end_time)
    from_s = _to_rounded_second(from_time)
    to_s = _to_rounded_second(to_time)

    delta = to_s - from_s

    # Special case: 24-hour shift queried at its own start time
    if delta == 0 and from_s == start_s and shift.duration_seconds == 86400:
        delta = 86400

    if delta < 0:
        delta = 86400 + to_s - from_s

    if _shift_spans_midnight(shift):
        if from_s < start_s and from_s < end_s:
            if not before_midnight:
                from_s += 86400
        to_s = from_s + delta
        end_s += 86400

    # Clip to [start_s, end_s]
    if from_s < start_s:
        from_s = start_s
    if to_s < start_s:
        to_s = start_s
    if from_s > end_s:
        from_s = end_s
    if to_s > end_s:
        to_s = end_s

    return timedelta(seconds=(to_s - from_s))


def compute_shift_working_time(
    shift: WorkShift, from_time: time, to_time: time,
) -> timedelta:
    """
    Port of PyShift ``Shift.calculateWorkingTime()``.

    Raises ``ValueError`` for midnight-crossing shifts; callers should use
    :func:`compute_shift_total_working_time` directly when crossing midnight.
    """
    if _shift_spans_midnight(shift):
        raise ValueError(
            f"Shift '{shift.name}' spans midnight; use compute_shift_total_working_time()"
        )
    return compute_shift_total_working_time(shift, from_time, to_time, True)


# ─── Team / schedule working-time computations (port of PyShift) ────────────

# `time.max` rounds up to the next midnight (86400 seconds of day) in PyShift.
# In Python it's 23:59:59.999999. We use this constant where the PyShift
# algorithm semantically means "end of day == 24:00".
_TIME_END_OF_DAY = time(23, 59, 59, 999999)


def compute_team_working_time(
    team: WorkTeam,
    non_working_periods: list[NonWorkingPeriod],
    from_dt: datetime,
    to_dt: datetime,
) -> timedelta:
    """
    Port of PyShift ``Team.calculateWorkingTime()``.

    Walks each calendar day in [from_dt, to_dt], adds today's shift contribution
    (clipped to the window) and adds the after-midnight portion of yesterday's
    midnight-crossing shift, if any.
    """
    if to_dt < from_dt:
        raise ValueError(f"to_dt {to_dt} earlier than from_dt {from_dt}")

    total = timedelta(0)
    this_date = from_dt.date()
    this_time = from_dt.time()
    to_date = to_dt.date()
    to_time_value = to_dt.time()
    day_count = team.rotation.day_count

    # Get yesterday's shift, if any (for after-midnight handling).
    last_shift: WorkShift | None = None
    yesterday = this_date - timedelta(days=1)
    try:
        yesterday_instance = _get_shift_instance_for_day(team, yesterday, non_working_periods)
    except ValueError:
        yesterday_instance = None
    if yesterday_instance is not None:
        # Find the actual WorkShift object that the instance refers to.
        last_shift = next(
            (s for s in team.rotation.work_schedule.shifts
             if s.id == yesterday_instance.shift_id),
            None,
        )

    while this_date <= to_date:
        if last_shift is not None and _shift_spans_midnight(last_shift):
            last_day = this_date == to_date
            if not last_day or (last_day and to_time_value != time.min):
                after_midnight = _to_rounded_second(last_shift.end_time)
                from_second = _to_rounded_second(this_time)
                if after_midnight > from_second:
                    total += timedelta(seconds=(after_midnight - from_second))

        try:
            instance = _get_shift_instance_for_day(team, this_date, non_working_periods)
        except ValueError:
            instance = None

        if instance is not None:
            shift = next(
                (s for s in team.rotation.work_schedule.shifts if s.id == instance.shift_id),
                None,
            )
            if shift is not None:
                last_shift = shift
                if this_date == to_date:
                    duration = compute_shift_total_working_time(
                        shift, this_time, to_time_value, True,
                    )
                else:
                    duration = compute_shift_total_working_time(
                        shift, this_time, _TIME_END_OF_DAY, True,
                    )
                total += duration
        else:
            last_shift = None

        n = 1
        try:
            day_in_rot = _day_in_rotation(team, this_date)
        except ValueError:
            day_in_rot = -1
        if day_in_rot == day_count:
            rotation_end_date = this_date + timedelta(days=day_count)
            if rotation_end_date < to_date:
                n = day_count
                total += timedelta(seconds=team.rotation.working_seconds)

        this_date += timedelta(days=n)
        this_time = time.min

    return total


def compute_non_working_time(
    schedule: WorkSchedule, from_dt: datetime, to_dt: datetime,
) -> timedelta:
    """
    Port of PyShift ``WorkSchedule.calculateNonWorkingTime()``.

    Returns the total time in [from_dt, to_dt] covered by active non-working
    periods (holidays, shutdowns, etc.).
    """
    total = timedelta(0)
    periods = sorted(
        (p for p in schedule.non_working_periods if p.is_active),
        key=lambda p: p.start_datetime,
    )
    for nwp in periods:
        if from_dt >= nwp.end_datetime:
            continue
        if to_dt <= nwp.start_datetime:
            break
        overlap_start = max(nwp.start_datetime, from_dt)
        overlap_end = min(nwp.end_datetime, to_dt)
        if overlap_end > overlap_start:
            total += overlap_end - overlap_start
        if to_dt <= nwp.end_datetime:
            break
    return total


def compute_working_time(
    schedule: WorkSchedule, from_dt: datetime, to_dt: datetime,
) -> timedelta:
    """
    Port of PyShift ``WorkSchedule.calculateWorkingTime()``.

    Sums each team's working time, then subtracts non-working periods.
    """
    if to_dt <= from_dt:
        return timedelta(0)

    total = timedelta(0)
    for team in schedule.teams:
        if not team.is_active:
            continue
        total += compute_team_working_time(team, schedule.non_working_periods, from_dt, to_dt)

    total -= compute_non_working_time(schedule, from_dt, to_dt)
    if total.total_seconds() < 0:
        total = timedelta(0)
    return total


# ─── Rotation / team statistics (port of PyShift) ──────────────────────────


def compute_rotation_duration(rotation: WorkRotation) -> timedelta:
    """Duration of one full rotation cycle."""
    return timedelta(days=rotation.day_count)


def compute_rotation_working_time(rotation: WorkRotation) -> timedelta:
    """Total working time within one full rotation cycle."""
    return timedelta(seconds=rotation.working_seconds)


def compute_schedule_rotation_duration(schedule: WorkSchedule) -> timedelta:
    """Sum of all active teams' rotation durations (PyShift ``getRotationDuration``)."""
    return timedelta(days=sum(
        team.rotation.day_count for team in schedule.teams if team.is_active
    ))


def compute_schedule_rotation_working_time(schedule: WorkSchedule) -> timedelta:
    """Sum of all active teams' rotation working times (PyShift ``getRotationWorkingTime``)."""
    return timedelta(seconds=sum(
        team.rotation.working_seconds for team in schedule.teams if team.is_active
    ))


def compute_team_percentage_worked(team: WorkTeam) -> float:
    """Percentage of the rotation cycle that is scheduled working time."""
    total_secs = team.rotation.day_count * 86400
    if total_secs == 0:
        return 0.0
    return team.rotation.working_seconds / total_secs * 100.0


def compute_team_average_hours_per_week(team: WorkTeam) -> float:
    """Average hours worked per week based on the rotation."""
    rotation = team.rotation
    if rotation.day_count == 0:
        return 0.0
    return (rotation.working_seconds / 3600.0) * 7.0 / rotation.day_count


# ═══════════════════════════════════════════════════════════════════
# WorkScheduleService
# ═══════════════════════════════════════════════════════════════════

class WorkScheduleService:

    # ─── WorkSchedule ────────────────────────────────────────────────

    @staticmethod
    async def list_schedules(session: AsyncSession) -> Sequence[WorkSchedule]:
        stmt = (
            select(WorkSchedule)
            .where(WorkSchedule.is_active.is_(True))
            .order_by(WorkSchedule.name)
            .options(
                selectinload(WorkSchedule.shifts),
                selectinload(WorkSchedule.teams),
            )
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_schedule(session: AsyncSession, schedule_id: UUID) -> WorkSchedule:
        stmt = (
            select(WorkSchedule)
            .where(WorkSchedule.id == schedule_id, WorkSchedule.is_active.is_(True))
            .options(*_schedule_options())
        )
        result = await session.execute(stmt)
        schedule = result.scalar_one_or_none()
        if schedule is None:
            raise WorkScheduleNotFoundException(str(schedule_id))
        return schedule

    @staticmethod
    async def create_schedule(session: AsyncSession, name: str, description: str | None) -> WorkSchedule:
        existing = await session.execute(
            select(WorkSchedule).where(WorkSchedule.name == name, WorkSchedule.is_active.is_(True))
        )
        if existing.scalar_one_or_none() is not None:
            raise DuplicateWorkScheduleNameException(name)
        schedule = WorkSchedule(name=name, description=description)
        session.add(schedule)
        await session.flush()
        return schedule

    @staticmethod
    async def update_schedule(
        session: AsyncSession, schedule_id: UUID, **kwargs: Any
    ) -> WorkSchedule:
        schedule = await WorkScheduleService.get_schedule(session, schedule_id)
        for k, v in kwargs.items():
            if v is not None:
                setattr(schedule, k, v)
        await session.flush()
        return schedule

    @staticmethod
    async def delete_schedule(session: AsyncSession, schedule_id: UUID) -> None:
        schedule = await WorkScheduleService.get_schedule(session, schedule_id)
        schedule.is_active = False
        await session.flush()

    # ─── Shift ───────────────────────────────────────────────────────

    @staticmethod
    async def get_shift(session: AsyncSession, shift_id: UUID) -> WorkShift:
        stmt = (
            select(WorkShift)
            .where(WorkShift.id == shift_id, WorkShift.is_active.is_(True))
            .options(selectinload(WorkShift.breaks))
        )
        result = await session.execute(stmt)
        shift = result.scalar_one_or_none()
        if shift is None:
            raise WorkShiftNotFoundException(str(shift_id))
        return shift

    @staticmethod
    async def list_shifts(session: AsyncSession, schedule_id: UUID) -> Sequence[WorkShift]:
        stmt = (
            select(WorkShift)
            .where(WorkShift.work_schedule_id == schedule_id, WorkShift.is_active.is_(True))
            .options(selectinload(WorkShift.breaks))
            .order_by(WorkShift.name)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def create_shift(
        session: AsyncSession, schedule_id: UUID,
        name: str, description: str | None,
        start_time: time, duration_seconds: int,
    ) -> WorkShift:
        # verify schedule exists
        await WorkScheduleService.get_schedule(session, schedule_id)
        shift = WorkShift(
            work_schedule_id=schedule_id, name=name,
            description=description, start_time=start_time,
            duration_seconds=duration_seconds,
        )
        session.add(shift)
        await session.flush()
        return shift

    @staticmethod
    async def update_shift(session: AsyncSession, shift_id: UUID, **kwargs: Any) -> WorkShift:
        shift = await WorkScheduleService.get_shift(session, shift_id)
        for k, v in kwargs.items():
            if v is not None:
                setattr(shift, k, v)
        await session.flush()
        return shift

    @staticmethod
    async def delete_shift(session: AsyncSession, shift_id: UUID) -> None:
        shift = await WorkScheduleService.get_shift(session, shift_id)
        shift.is_active = False
        await session.flush()

    # ─── Break ───────────────────────────────────────────────────────

    @staticmethod
    async def add_break(
        session: AsyncSession, shift_id: UUID,
        name: str, description: str | None,
        start_time: time, duration_seconds: int,
    ) -> ShiftBreak:
        await WorkScheduleService.get_shift(session, shift_id)
        brk = ShiftBreak(
            shift_id=shift_id, name=name, description=description,
            start_time=start_time, duration_seconds=duration_seconds,
        )
        session.add(brk)
        await session.flush()
        return brk

    @staticmethod
    async def delete_break(session: AsyncSession, break_id: UUID) -> None:
        stmt = select(ShiftBreak).where(ShiftBreak.id == break_id)
        result = await session.execute(stmt)
        brk = result.scalar_one_or_none()
        if brk is not None:
            brk.is_active = False
        await session.flush()

    # ─── Rotation ────────────────────────────────────────────────────

    @staticmethod
    async def get_rotation(session: AsyncSession, rotation_id: UUID) -> WorkRotation:
        stmt = (
            select(WorkRotation)
            .where(WorkRotation.id == rotation_id, WorkRotation.is_active.is_(True))
            .options(
                selectinload(WorkRotation.segments).selectinload(RotationSegment.shift),
            )
        )
        result = await session.execute(stmt)
        rotation = result.scalar_one_or_none()
        if rotation is None:
            raise WorkRotationNotFoundException(str(rotation_id))
        return rotation

    @staticmethod
    async def list_rotations(session: AsyncSession, schedule_id: UUID) -> Sequence[WorkRotation]:
        stmt = (
            select(WorkRotation)
            .where(WorkRotation.work_schedule_id == schedule_id, WorkRotation.is_active.is_(True))
            .options(selectinload(WorkRotation.segments).selectinload(RotationSegment.shift))
            .order_by(WorkRotation.name)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def create_rotation(
        session: AsyncSession, schedule_id: UUID,
        name: str, description: str | None,
    ) -> WorkRotation:
        await WorkScheduleService.get_schedule(session, schedule_id)
        rotation = WorkRotation(work_schedule_id=schedule_id, name=name, description=description)
        session.add(rotation)
        await session.flush()
        return rotation

    @staticmethod
    async def update_rotation(session: AsyncSession, rotation_id: UUID, **kwargs: Any) -> WorkRotation:
        rotation = await WorkScheduleService.get_rotation(session, rotation_id)
        for k, v in kwargs.items():
            if v is not None:
                setattr(rotation, k, v)
        await session.flush()
        return rotation

    @staticmethod
    async def delete_rotation(session: AsyncSession, rotation_id: UUID) -> None:
        rotation = await WorkScheduleService.get_rotation(session, rotation_id)
        rotation.is_active = False
        await session.flush()

    @staticmethod
    async def add_rotation_segment(
        session: AsyncSession, rotation_id: UUID,
        shift_id: UUID, days_on: int, days_off: int, sequence: int,
    ) -> RotationSegment:
        await WorkScheduleService.get_rotation(session, rotation_id)
        await WorkScheduleService.get_shift(session, shift_id)
        seg = RotationSegment(
            rotation_id=rotation_id, shift_id=shift_id,
            days_on=days_on, days_off=days_off, sequence=sequence,
        )
        session.add(seg)
        await session.flush()
        return seg

    @staticmethod
    async def delete_rotation_segment(session: AsyncSession, segment_id: UUID) -> None:
        stmt = select(RotationSegment).where(RotationSegment.id == segment_id)
        result = await session.execute(stmt)
        seg = result.scalar_one_or_none()
        if seg is not None:
            seg.is_active = False
        await session.flush()

    # ─── Team ─────────────────────────────────────────────────────────

    @staticmethod
    async def get_team(session: AsyncSession, team_id: UUID) -> WorkTeam:
        stmt = (
            select(WorkTeam)
            .where(WorkTeam.id == team_id, WorkTeam.is_active.is_(True))
            .options(
                selectinload(WorkTeam.members),
                selectinload(WorkTeam.member_exceptions),
                selectinload(WorkTeam.rotation).selectinload(WorkRotation.segments).selectinload(RotationSegment.shift),
            )
        )
        result = await session.execute(stmt)
        team = result.scalar_one_or_none()
        if team is None:
            raise WorkTeamNotFoundException(str(team_id))
        return team

    @staticmethod
    async def list_teams(session: AsyncSession, schedule_id: UUID) -> Sequence[WorkTeam]:
        stmt = (
            select(WorkTeam)
            .where(WorkTeam.work_schedule_id == schedule_id, WorkTeam.is_active.is_(True))
            .options(
                selectinload(WorkTeam.members),
                selectinload(WorkTeam.rotation),
            )
            .order_by(WorkTeam.name)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def create_team(
        session: AsyncSession, schedule_id: UUID,
        name: str, description: str | None,
        rotation_id: UUID, rotation_start: date,
    ) -> WorkTeam:
        await WorkScheduleService.get_schedule(session, schedule_id)
        await WorkScheduleService.get_rotation(session, rotation_id)
        team = WorkTeam(
            work_schedule_id=schedule_id, name=name,
            description=description, rotation_id=rotation_id,
            rotation_start=rotation_start,
        )
        session.add(team)
        await session.flush()
        return team

    @staticmethod
    async def update_team(session: AsyncSession, team_id: UUID, **kwargs: Any) -> WorkTeam:
        team = await WorkScheduleService.get_team(session, team_id)
        for k, v in kwargs.items():
            if v is not None:
                setattr(team, k, v)
        await session.flush()
        return team

    @staticmethod
    async def delete_team(session: AsyncSession, team_id: UUID) -> None:
        team = await WorkScheduleService.get_team(session, team_id)
        team.is_active = False
        await session.flush()

    # ─── TeamMember ──────────────────────────────────────────────────

    @staticmethod
    async def get_team_member(session: AsyncSession, member_id: UUID) -> TeamMember:
        stmt = select(TeamMember).where(
            TeamMember.id == member_id, TeamMember.is_active.is_(True)
        )
        result = await session.execute(stmt)
        member = result.scalar_one_or_none()
        if member is None:
            raise TeamMemberNotFoundException(str(member_id))
        return member

    @staticmethod
    async def add_team_member(
        session: AsyncSession, team_id: UUID,
        member_id: str, name: str, description: str | None,
    ) -> TeamMember:
        await WorkScheduleService.get_team(session, team_id)
        member = TeamMember(
            team_id=team_id, member_id=member_id,
            name=name, description=description,
        )
        session.add(member)
        await session.flush()
        return member

    @staticmethod
    async def delete_team_member(session: AsyncSession, member_pk: UUID) -> None:
        member = await WorkScheduleService.get_team_member(session, member_pk)
        member.is_active = False
        await session.flush()

    # ─── TeamMemberException ─────────────────────────────────────────

    @staticmethod
    async def add_member_exception(
        session: AsyncSession, team_id: UUID,
        shift_start: datetime,
        add_member_id: UUID | None,
        remove_member_id: UUID | None,
        reason: str | None,
    ) -> TeamMemberException:
        await WorkScheduleService.get_team(session, team_id)
        exc = TeamMemberException(
            team_id=team_id, shift_start=shift_start,
            add_member_id=add_member_id,
            remove_member_id=remove_member_id,
            reason=reason,
        )
        session.add(exc)
        await session.flush()
        return exc

    @staticmethod
    async def delete_member_exception(session: AsyncSession, exception_id: UUID) -> None:
        stmt = select(TeamMemberException).where(TeamMemberException.id == exception_id)
        result = await session.execute(stmt)
        exc = result.scalar_one_or_none()
        if exc is not None:
            exc.is_active = False
        await session.flush()

    # ─── NonWorkingPeriod ─────────────────────────────────────────────

    @staticmethod
    async def get_non_working_period(session: AsyncSession, period_id: UUID) -> NonWorkingPeriod:
        stmt = select(NonWorkingPeriod).where(
            NonWorkingPeriod.id == period_id, NonWorkingPeriod.is_active.is_(True)
        )
        result = await session.execute(stmt)
        period = result.scalar_one_or_none()
        if period is None:
            raise NonWorkingPeriodNotFoundException(str(period_id))
        return period

    @staticmethod
    async def list_non_working_periods(
        session: AsyncSession, schedule_id: UUID,
    ) -> Sequence[NonWorkingPeriod]:
        stmt = (
            select(NonWorkingPeriod)
            .where(
                NonWorkingPeriod.work_schedule_id == schedule_id,
                NonWorkingPeriod.is_active.is_(True),
            )
            .order_by(NonWorkingPeriod.start_datetime)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def create_non_working_period(
        session: AsyncSession, schedule_id: UUID,
        name: str, description: str | None,
        start_datetime: datetime, duration_seconds: int,
    ) -> NonWorkingPeriod:
        await WorkScheduleService.get_schedule(session, schedule_id)
        period = NonWorkingPeriod(
            work_schedule_id=schedule_id, name=name,
            description=description, start_datetime=start_datetime,
            duration_seconds=duration_seconds,
        )
        session.add(period)
        await session.flush()
        return period

    @staticmethod
    async def update_non_working_period(
        session: AsyncSession, period_id: UUID, **kwargs: Any
    ) -> NonWorkingPeriod:
        period = await WorkScheduleService.get_non_working_period(session, period_id)
        for k, v in kwargs.items():
            if v is not None:
                setattr(period, k, v)
        await session.flush()
        return period

    @staticmethod
    async def delete_non_working_period(session: AsyncSession, period_id: UUID) -> None:
        period = await WorkScheduleService.get_non_working_period(session, period_id)
        period.is_active = False
        await session.flush()

    # ─── Query helpers ────────────────────────────────────────────────

    @staticmethod
    async def get_shift_instances_for_day(
        session: AsyncSession, schedule_id: UUID, day: date,
    ) -> list[ShiftInstanceResult]:
        schedule = await WorkScheduleService.get_schedule(session, schedule_id)
        return compute_shift_instances_for_day(schedule, day)

    @staticmethod
    async def get_shift_instances_for_range(
        session: AsyncSession, schedule_id: UUID,
        from_date: date, to_date: date,
    ) -> list[ShiftInstanceResult]:
        schedule = await WorkScheduleService.get_schedule(session, schedule_id)
        return compute_shift_instances_for_range(schedule, from_date, to_date)

    @staticmethod
    async def get_working_time(
        session: AsyncSession, schedule_id: UUID,
        from_dt: datetime, to_dt: datetime,
    ) -> timedelta:
        schedule = await WorkScheduleService.get_schedule(session, schedule_id)
        return compute_working_time(schedule, from_dt, to_dt)
