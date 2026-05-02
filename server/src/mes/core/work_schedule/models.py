"""
Work Schedule: SQLAlchemy models.

Ported from PyShift (https://github.com/point85/PyShift) without localization.

Entity hierarchy:
  WorkSchedule
    ├── Shift          (start_time, duration_seconds)
    │    └── ShiftBreak (start_time, duration_seconds)
    ├── Rotation
    │    └── RotationSegment (shift FK, days_on, days_off, sequence)
    ├── Team           (rotation FK, rotation_start date)
    │    ├── TeamMember (member_id str, name, description)
    │    └── TeamMemberException (shift_start datetime, add_member FK, remove_member FK, reason)
    └── NonWorkingPeriod (start_datetime, duration_seconds)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mes.framework.db.base import BaseModel


# ─────────────────────────────────────────────────────────────────────────────
# WorkSchedule  (root aggregate)
# ─────────────────────────────────────────────────────────────────────────────

class WorkSchedule(BaseModel):
    """Root entity — named container for shifts, rotations, teams and holidays."""

    __tablename__ = "work_schedules"

    name: Mapped[str] = mapped_column(
        String(200), unique=True, nullable=False, index=True,
        comment="Unique schedule name",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )

    # ── Relationships ────────────────────────────────────────────────
    shifts: Mapped[list["WorkShift"]] = relationship(
        "WorkShift", back_populates="work_schedule",
        cascade="all, delete-orphan",
    )
    rotations: Mapped[list["WorkRotation"]] = relationship(
        "WorkRotation", back_populates="work_schedule",
        cascade="all, delete-orphan",
    )
    teams: Mapped[list["WorkTeam"]] = relationship(
        "WorkTeam", back_populates="work_schedule",
        cascade="all, delete-orphan",
    )
    non_working_periods: Mapped[list["NonWorkingPeriod"]] = relationship(
        "NonWorkingPeriod", back_populates="work_schedule",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<WorkSchedule id={self.id} name={self.name!r}>"


# ─────────────────────────────────────────────────────────────────────────────
# Shift + ShiftBreak
# ─────────────────────────────────────────────────────────────────────────────

class WorkShift(BaseModel):
    """A named working period with a start time of day and duration."""

    __tablename__ = "work_shifts"

    work_schedule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("work_schedules.id"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[time] = mapped_column(
        Time, nullable=False,
        comment="Time of day when shift starts",
    )
    duration_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Shift length in seconds (max 86400)",
    )

    # ── Relationships ────────────────────────────────────────────────
    work_schedule: Mapped["WorkSchedule"] = relationship(
        "WorkSchedule", back_populates="shifts",
    )
    breaks: Mapped[list["ShiftBreak"]] = relationship(
        "ShiftBreak", back_populates="shift",
        cascade="all, delete-orphan",
    )
    rotation_segments: Mapped[list["RotationSegment"]] = relationship(
        "RotationSegment", back_populates="shift",
    )

    # ── Computed helpers (not persisted) ────────────────────────────
    @property
    def duration(self) -> timedelta:
        return timedelta(seconds=self.duration_seconds)

    @property
    def end_time(self) -> time:
        from datetime import date as _date
        from datetime import datetime as _dt
        dt = _dt.combine(_date.today(), self.start_time) + self.duration
        return dt.time()

    @property
    def spans_midnight(self) -> bool:
        return self.end_time <= self.start_time and self.duration_seconds < 86400

    def __repr__(self) -> str:
        return f"<WorkShift id={self.id} name={self.name!r}>"


class ShiftBreak(BaseModel):
    """A named break period within a shift."""

    __tablename__ = "shift_breaks"

    shift_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("work_shifts.id"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Break length in seconds",
    )

    # ── Relationships ────────────────────────────────────────────────
    shift: Mapped["WorkShift"] = relationship("WorkShift", back_populates="breaks")

    @property
    def duration(self) -> timedelta:
        return timedelta(seconds=self.duration_seconds)

    def __repr__(self) -> str:
        return f"<ShiftBreak id={self.id} name={self.name!r}>"


# ─────────────────────────────────────────────────────────────────────────────
# Rotation + RotationSegment
# ─────────────────────────────────────────────────────────────────────────────

class WorkRotation(BaseModel):
    """Ordered sequence of shift-on / day-off segments that repeat cyclically."""

    __tablename__ = "work_rotations"

    work_schedule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("work_schedules.id"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────────
    work_schedule: Mapped["WorkSchedule"] = relationship(
        "WorkSchedule", back_populates="rotations",
    )
    segments: Mapped[list["RotationSegment"]] = relationship(
        "RotationSegment", back_populates="rotation",
        cascade="all, delete-orphan",
        order_by="RotationSegment.sequence",
    )
    teams: Mapped[list["WorkTeam"]] = relationship(
        "WorkTeam", back_populates="rotation",
    )

    @property
    def day_count(self) -> int:
        return sum(s.days_on + s.days_off for s in self.segments)

    @property
    def working_seconds(self) -> int:
        return sum(s.days_on * (s.shift.duration_seconds if s.shift else 0)
                   for s in self.segments)

    def __repr__(self) -> str:
        return f"<WorkRotation id={self.id} name={self.name!r}>"


class RotationSegment(BaseModel):
    """One on/off block within a rotation (e.g. 7 days on Day-shift, 7 off)."""

    __tablename__ = "rotation_segments"

    rotation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("work_rotations.id"), nullable=False, index=True,
    )
    shift_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("work_shifts.id"), nullable=False, index=True,
    )
    days_on: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    days_off: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sequence: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1,
        comment="1-based position in the rotation",
    )

    # ── Relationships ────────────────────────────────────────────────
    rotation: Mapped["WorkRotation"] = relationship(
        "WorkRotation", back_populates="segments",
    )
    shift: Mapped["WorkShift"] = relationship(
        "WorkShift", back_populates="rotation_segments", lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<RotationSegment rotation={self.rotation_id} "
            f"seq={self.sequence} on={self.days_on} off={self.days_off}>"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Team + TeamMember + TeamMemberException
# ─────────────────────────────────────────────────────────────────────────────

class WorkTeam(BaseModel):
    """A named group of people that works a rotation, starting on a reference date."""

    __tablename__ = "work_teams"

    work_schedule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("work_schedules.id"), nullable=False, index=True,
    )
    rotation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("work_rotations.id"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rotation_start: Mapped[date] = mapped_column(
        Date, nullable=False,
        comment="The calendar date on which day-1 of this team's rotation falls",
    )

    # ── Relationships ────────────────────────────────────────────────
    work_schedule: Mapped["WorkSchedule"] = relationship(
        "WorkSchedule", back_populates="teams",
    )
    rotation: Mapped["WorkRotation"] = relationship(
        "WorkRotation", back_populates="teams", lazy="joined",
    )
    members: Mapped[list["TeamMember"]] = relationship(
        "TeamMember", back_populates="team",
        cascade="all, delete-orphan",
    )
    member_exceptions: Mapped[list["TeamMemberException"]] = relationship(
        "TeamMemberException", back_populates="team",
        cascade="all, delete-orphan",
        foreign_keys="TeamMemberException.team_id",
    )

    def __repr__(self) -> str:
        return f"<WorkTeam id={self.id} name={self.name!r}>"


class TeamMember(BaseModel):
    """A person assigned to a team, identified by an external member ID (e.g. employee ID)."""

    __tablename__ = "team_members"

    team_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("work_teams.id"), nullable=False, index=True,
    )
    member_id: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="External identifier, e.g. employee ID or badge number",
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────────
    team: Mapped["WorkTeam"] = relationship("WorkTeam", back_populates="members")

    def __repr__(self) -> str:
        return f"<TeamMember id={self.id} member_id={self.member_id!r}>"


class TeamMemberException(BaseModel):
    """
    An ad-hoc substitution for one shift instance.

    Records one team member being added and/or one being removed for the
    shift instance that starts at ``shift_start``.
    """

    __tablename__ = "team_member_exceptions"

    team_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("work_teams.id"), nullable=False, index=True,
    )
    shift_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
        comment="Start of the shift instance this exception applies to",
    )
    add_member_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("team_members.id"), nullable=True,
        comment="TeamMember to add for this shift instance",
    )
    remove_member_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("team_members.id"), nullable=True,
        comment="TeamMember to remove for this shift instance",
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ────────────────────────────────────────────────
    team: Mapped["WorkTeam"] = relationship(
        "WorkTeam", back_populates="member_exceptions",
        foreign_keys=[team_id],
    )
    add_member: Mapped["TeamMember | None"] = relationship(
        "TeamMember", foreign_keys=[add_member_id],
    )
    remove_member: Mapped["TeamMember | None"] = relationship(
        "TeamMember", foreign_keys=[remove_member_id],
    )

    def __repr__(self) -> str:
        return f"<TeamMemberException team={self.team_id} shift_start={self.shift_start}>"


# ─────────────────────────────────────────────────────────────────────────────
# NonWorkingPeriod  (holidays, planned shutdowns)
# ─────────────────────────────────────────────────────────────────────────────

class NonWorkingPeriod(BaseModel):
    """A named non-recurring non-working period (holiday, maintenance shutdown, etc.)."""

    __tablename__ = "non_working_periods"

    work_schedule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("work_schedules.id"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_datetime: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    duration_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="Length of the non-working period in seconds",
    )

    # ── Relationships ────────────────────────────────────────────────
    work_schedule: Mapped["WorkSchedule"] = relationship(
        "WorkSchedule", back_populates="non_working_periods",
    )

    @property
    def duration(self) -> timedelta:
        return timedelta(seconds=self.duration_seconds)

    @property
    def end_datetime(self) -> datetime:
        return self.start_datetime + self.duration

    def __repr__(self) -> str:
        return f"<NonWorkingPeriod id={self.id} name={self.name!r}>"
