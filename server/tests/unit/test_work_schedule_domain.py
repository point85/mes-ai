"""
Unit tests for the MES AI work-schedule domain computation layer.

These tests port the PyShift test scenarios (test_pyshift_work_schedule.py and
test_pyshift_snap_schedule.py) to exercise the MES service functions directly
instead of the standalone PyShift library.

All model objects are constructed in-memory (no DB session) because the domain
computation functions operate purely on model attributes.

Adaptation notes vs. PyShift originals:
  - ``datetime.combine(d, time.max) + timedelta(days=N)``
    → ``datetime(d.year, d.month, d.day + N + 1, 0, 0, 0)``
    (PyShift rounds time.max to the next second = midnight; Python does not)
  - Deletion is simulated via ``obj.is_active = False`` rather than list removal.
"""

import unittest
import uuid
from datetime import date, datetime, time, timedelta

from mes.core.work_schedule.models import (
    NonWorkingPeriod,
    RotationSegment,
    WorkRotation,
    WorkSchedule,
    WorkShift,
    WorkTeam,
)
from mes.core.work_schedule.service import (
    _build_period_list,
    _day_in_rotation,
    compute_non_working_time,
    compute_rotation_duration,
    compute_rotation_working_time,
    compute_schedule_rotation_duration,
    compute_schedule_rotation_working_time,
    compute_shift_instances_for_day,
    compute_shift_instances_for_range,
    compute_shift_total_working_time,
    compute_shift_working_time,
    compute_team_average_hours_per_week,
    compute_team_percentage_worked,
    compute_team_working_time,
    compute_working_time,
    is_time_in_shift,
    shift_spans_midnight,
)


# ═══════════════════════════════════════════════════════════════════════════════
# In-memory model factory
# ═══════════════════════════════════════════════════════════════════════════════

class ScheduleBuilder:
    """Build an in-memory WorkSchedule model graph for unit testing (no DB)."""

    def __init__(self, name: str, description: str = "") -> None:
        s = WorkSchedule(name=name, description=description)
        s.id = uuid.uuid4()
        s.is_active = True
        s.shifts = []
        s.rotations = []
        s.teams = []
        s.non_working_periods = []
        self._sched = s

    @property
    def schedule(self) -> WorkSchedule:
        return self._sched

    def shift(
        self, name: str, description: str, start: time, duration: timedelta,
    ) -> WorkShift:
        sh = WorkShift(
            work_schedule_id=self._sched.id,
            name=name,
            description=description,
            start_time=start,
            duration_seconds=int(duration.total_seconds()),
        )
        sh.id = uuid.uuid4()
        sh.is_active = True
        sh.breaks = []
        sh.rotation_segments = []
        self._sched.shifts.append(sh)
        return sh

    def rotation(self, name: str, description: str = "") -> WorkRotation:
        r = WorkRotation(
            work_schedule_id=self._sched.id,
            name=name,
            description=description,
        )
        r.id = uuid.uuid4()
        r.is_active = True
        r.segments = []
        r.teams = []
        self._sched.rotations.append(r)
        return r

    def segment(
        self,
        rot: WorkRotation,
        shift: WorkShift,
        days_on: int,
        days_off: int,
    ) -> RotationSegment:
        seq = len(rot.segments) + 1
        seg = RotationSegment(
            rotation_id=rot.id,
            shift_id=shift.id,
            days_on=days_on,
            days_off=days_off,
            sequence=seq,
        )
        seg.id = uuid.uuid4()
        seg.is_active = True
        seg.shift = shift
        # NOTE: setting `seg.rotation = rot` triggers SQLAlchemy back_populates
        # which already appends `seg` to `rot.segments`. Do NOT also call
        # `rot.segments.append(seg)` -- that would double-count and produce an
        # incorrect `rotation.day_count` / `rotation.working_seconds`.
        seg.rotation = rot
        return seg

    def team(
        self,
        name: str,
        description: str,
        rot: WorkRotation,
        start: date,
    ) -> WorkTeam:
        t = WorkTeam(
            work_schedule_id=self._sched.id,
            name=name,
            description=description,
            rotation_id=rot.id,
            rotation_start=start,
        )
        t.id = uuid.uuid4()
        t.is_active = True
        t.rotation = rot
        t.members = []
        t.member_exceptions = []
        self._sched.teams.append(t)
        return t

    def non_working_period(
        self,
        name: str,
        description: str,
        start_dt: datetime,
        duration: timedelta,
    ) -> NonWorkingPeriod:
        nwp = NonWorkingPeriod(
            work_schedule_id=self._sched.id,
            name=name,
            description=description,
            start_datetime=start_dt,
            duration_seconds=int(duration.total_seconds()),
        )
        nwp.id = uuid.uuid4()
        nwp.is_active = True
        self._sched.non_working_periods.append(nwp)
        return nwp


def _next_midnight(d: date, extra_days: int = 0) -> datetime:
    """Return midnight at the start of ``d + 1 + extra_days``."""
    return datetime(d.year, d.month, d.day) + timedelta(days=1 + extra_days)


# ═══════════════════════════════════════════════════════════════════════════════
# Base test class
# ═══════════════════════════════════════════════════════════════════════════════

class BaseDomainTest(unittest.TestCase):
    """Base class mirroring PyShift's BaseTest, adapted for MES domain functions."""

    REFERENCE_DATE = date(2016, 10, 31)
    LATER_DATE = date(2021, 10, 1)
    LATER_TIME = time(7, 0, 0)

    def setUp(self) -> None:
        self.builder: ScheduleBuilder | None = None

    @property
    def schedule(self) -> WorkSchedule:
        assert self.builder is not None
        return self.builder.schedule

    # ── assertion helpers ───────────────────────────────────────────

    def assert_working_time(
        self, from_dt: datetime, to_dt: datetime, expected_hours: float,
    ) -> None:
        wt = compute_working_time(self.schedule, from_dt, to_dt)
        self.assertAlmostEqual(
            wt.total_seconds(), expected_hours * 3600, places=0,
            msg=f"Working time expected {expected_hours}h got {wt.total_seconds()/3600:.4f}h",
        )

    def assert_non_working_time(
        self, from_dt: datetime, to_dt: datetime, expected_hours: float,
    ) -> None:
        nwt = compute_non_working_time(self.schedule, from_dt, to_dt)
        self.assertAlmostEqual(
            nwt.total_seconds(), expected_hours * 3600, places=0,
            msg=f"Non-working time expected {expected_hours}h got {nwt.total_seconds()/3600:.4f}h",
        )

    # ── port of BaseTest.shiftTests ─────────────────────────────────

    def shift_tests(self) -> None:
        self.assertGreater(len(self.schedule.shifts), 0)
        for shift in self.schedule.shifts:
            total = shift.duration
            start = shift.start_time
            end = shift.end_time

            self.assertGreater(len(shift.name), 0)
            self.assertGreater(total.total_seconds(), 0)
            self.assertIsNotNone(start)
            self.assertIsNotNone(end)

            if shift_spans_midnight(shift):
                worked = compute_shift_total_working_time(shift, start, end, True)
            else:
                worked = compute_shift_working_time(shift, start, end)
            self.assertEqual(worked, total)

            if shift_spans_midnight(shift):
                worked = compute_shift_total_working_time(shift, start, start, True)
            else:
                worked = compute_shift_working_time(shift, start, start)

            if shift.duration_seconds == 86400:
                self.assertEqual(worked.total_seconds(), 86400)
            else:
                self.assertEqual(worked.total_seconds(), 0)

    # ── port of BaseTest.teamTests ──────────────────────────────────

    def team_tests(self, hours_per_rotation: timedelta, rotation_days: timedelta) -> None:
        self.assertGreater(len(self.schedule.teams), 0)
        for team in self.schedule.teams:
            self.assertGreater(len(team.name), 0)
            self.assertEqual(_day_in_rotation(team, team.rotation_start), 1)
            self.assertEqual(compute_rotation_working_time(team.rotation), hours_per_rotation)
            self.assertGreater(compute_team_percentage_worked(team), 0.0)
            self.assertEqual(compute_rotation_duration(team.rotation), rotation_days)
            self.assertIsNotNone(team.rotation_start)
            rotation = team.rotation
            self.assertEqual(compute_rotation_duration(rotation), rotation_days)
            self.assertGreater(len(_build_period_list(rotation)), 0)
            self.assertLessEqual(
                compute_rotation_working_time(rotation).total_seconds(),
                compute_rotation_duration(rotation).total_seconds(),
            )

    # ── port of BaseTest.shiftInstanceTests ────────────────────────

    def shift_instance_tests(self, begin_date: date) -> None:
        rotation = self.schedule.teams[0].rotation
        end_date = begin_date + compute_rotation_duration(rotation)
        day = begin_date
        while day <= end_date:
            instances = compute_shift_instances_for_day(self.schedule, day)
            for inst in instances:
                self.assertLess(inst.start_datetime, inst.end_datetime)
                shift = next(
                    s for s in self.schedule.shifts if s.id == inst.shift_id
                )
                start_t = shift.start_time
                end_t = shift.end_time

                self.assertTrue(is_time_in_shift(shift, start_t))

                start_plus1 = (
                    datetime(1970, 1, 1, start_t.hour, start_t.minute, start_t.second)
                    + timedelta(seconds=1)
                ).time()
                self.assertTrue(is_time_in_shift(shift, start_plus1))

                if shift.duration_seconds != 86400:
                    start_minus1 = (
                        datetime(1970, 1, 1, start_t.hour, start_t.minute, start_t.second)
                        - timedelta(seconds=1)
                    ).time()
                    self.assertFalse(is_time_in_shift(shift, start_minus1))

                self.assertTrue(is_time_in_shift(shift, end_t))

                end_minus1 = (
                    datetime(1970, 1, 1, end_t.hour, end_t.minute, end_t.second)
                    - timedelta(seconds=1)
                ).time()
                self.assertTrue(is_time_in_shift(shift, end_minus1))

                if shift.duration_seconds != 86400:
                    end_plus1 = (
                        datetime(1970, 1, 1, end_t.hour, end_t.minute, end_t.second)
                        + timedelta(seconds=1)
                    ).time()
                    self.assertFalse(is_time_in_shift(shift, end_plus1))

            day += timedelta(days=1)

    # ── combined base test ──────────────────────────────────────────

    def run_base_test(
        self,
        hours_per_rotation: timedelta,
        rotation_days: timedelta,
        starting_date: date | None = None,
    ) -> None:
        begin_date = starting_date if starting_date is not None else self.REFERENCE_DATE
        self.assertGreater(len(self.schedule.name), 0)
        self.assertGreater(len(self.schedule.description), 0)
        self.assertIsNotNone(self.schedule.non_working_periods)
        self.shift_tests()
        self.team_tests(hours_per_rotation, rotation_days)
        self.shift_instance_tests(begin_date)


# ═══════════════════════════════════════════════════════════════════════════════
# Schedule-level tests (porting TestWorkSchedule)
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkScheduleDomain(BaseDomainTest):

    # ── manufacturing shifts ────────────────────────────────────────

    def testManufacturingShifts(self) -> None:
        b = ScheduleBuilder(
            "Manufacturing Company - four twelves",
            "Four 12 hour alternating day/night shifts",
        )
        day = b.shift("Day", "Day shift", time(7, 0, 0), timedelta(hours=12))
        night = b.shift("Night", "Night shift", time(19, 0, 0), timedelta(hours=12))

        day_rot = b.rotation("Day", "Day")
        b.segment(day_rot, day, 7, 7)

        night_rot = b.rotation("Night", "Night")
        b.segment(night_rot, night, 7, 7)

        b.team("A", "A day shift", day_rot, date(2014, 1, 2))
        b.team("B", "B night shift", night_rot, date(2014, 1, 2))
        b.team("C", "C day shift", day_rot, date(2014, 1, 9))
        b.team("D", "D night shift", night_rot, date(2014, 1, 9))
        self.builder = b

        from_dt = datetime.combine(self.LATER_DATE, self.LATER_TIME)
        to_dt = from_dt + timedelta(days=28)

        self.assert_working_time(from_dt, to_dt, 672)
        self.assert_non_working_time(from_dt, to_dt, 0)

        self.assertEqual(
            compute_schedule_rotation_duration(self.schedule).total_seconds(),
            1344 * 3600,
        )
        self.assertEqual(
            compute_schedule_rotation_working_time(self.schedule).total_seconds(),
            336 * 3600,
        )

        for team in self.schedule.teams:
            self.assertEqual(compute_rotation_duration(team.rotation).total_seconds(), 336 * 3600)
            self.assertAlmostEqual(compute_team_percentage_worked(team), 25.00, places=2)
            self.assertEqual(compute_rotation_working_time(team.rotation).total_seconds(), 84 * 3600)
            self.assertAlmostEqual(compute_team_average_hours_per_week(team), 42.0, places=2)

        self.run_base_test(timedelta(hours=84), timedelta(days=14), date(2014, 1, 9))

    # ── firefighter shifts (Kern Co.) ───────────────────────────────

    def testFirefighterShifts1(self) -> None:
        b = ScheduleBuilder("Kern Co.", "Three 24 hour alternating shifts")
        shift = b.shift("24 Hour", "24 hour shift", time(7, 0, 0), timedelta(hours=24))

        rotation = b.rotation("24 Hour", "2 days ON, 2 OFF, 2 ON, 2 OFF, 2 ON, 8 OFF")
        b.segment(rotation, shift, 2, 2)
        b.segment(rotation, shift, 2, 2)
        b.segment(rotation, shift, 2, 8)

        b.team("Red", "A Shift", rotation, date(2017, 1, 8))
        b.team("Black", "B Shift", rotation, date(2017, 2, 1))
        b.team("Green", "C Shift", rotation, date(2017, 1, 2))
        self.builder = b

        from_dt = datetime.combine(self.LATER_DATE, self.LATER_TIME)
        to_dt = from_dt + timedelta(days=28)

        self.assert_working_time(from_dt, to_dt, 672)
        self.assert_non_working_time(from_dt, to_dt, 0)

        self.assertEqual(
            compute_schedule_rotation_duration(self.schedule).total_seconds(), 1296 * 3600,
        )
        self.assertEqual(
            compute_schedule_rotation_working_time(self.schedule).total_seconds(), 432 * 3600,
        )

        for team in self.schedule.teams:
            self.assertEqual(compute_rotation_duration(team.rotation).total_seconds(), 432 * 3600)
            self.assertAlmostEqual(compute_team_percentage_worked(team), 33.33, places=2)
            self.assertEqual(compute_rotation_working_time(team.rotation).total_seconds(), 144 * 3600)
            self.assertAlmostEqual(compute_team_average_hours_per_week(team), 56.0, places=2)

        self.run_base_test(timedelta(hours=144), timedelta(days=18), date(2017, 2, 1))

    # ── firefighter shifts (Seattle) ────────────────────────────────

    def testFirefighterShifts2(self) -> None:
        b = ScheduleBuilder("Seattle", "Four 24 hour alternating shifts")
        shift = b.shift("24 Hours", "24 hour shift", time(7, 0, 0), timedelta(hours=24))

        rotation = b.rotation("24 Hours", "24 Hours")
        b.segment(rotation, shift, 1, 4)
        b.segment(rotation, shift, 1, 2)

        b.team("A", "Platoon1", rotation, date(2014, 2, 2))
        b.team("B", "Platoon2", rotation, date(2014, 2, 4))
        b.team("C", "Platoon3", rotation, date(2014, 1, 31))
        b.team("D", "Platoon4", rotation, date(2014, 1, 29))
        self.builder = b

        from_dt = datetime.combine(self.LATER_DATE, self.LATER_TIME)
        to_dt = from_dt + timedelta(days=28)

        self.assert_working_time(from_dt, to_dt, 672)
        self.assert_non_working_time(from_dt, to_dt, 0)

        self.assertEqual(
            compute_schedule_rotation_duration(self.schedule).total_seconds(), 768 * 3600,
        )
        self.assertEqual(
            compute_schedule_rotation_working_time(self.schedule).total_seconds(), 192 * 3600,
        )

        for team in self.schedule.teams:
            self.assertEqual(compute_rotation_duration(team.rotation).total_seconds(), 192 * 3600)
            self.assertAlmostEqual(compute_team_percentage_worked(team), 25.00, places=2)
            self.assertEqual(compute_rotation_working_time(team.rotation).total_seconds(), 48 * 3600)
            self.assertAlmostEqual(compute_team_average_hours_per_week(team), 42.0, places=2)

        self.run_base_test(timedelta(hours=48), timedelta(days=8))

    # ── nursing ICU ─────────────────────────────────────────────────

    def testNursingICUShifts(self) -> None:
        b = ScheduleBuilder(
            "Nursing ICU",
            "Two 12 hr back-to-back shifts, rotating every 14 days",
        )
        day = b.shift("Day", "Day shift", time(6, 0, 0), timedelta(hours=12))
        night = b.shift("Night", "Night shift", time(18, 0, 0), timedelta(hours=12))

        day_rot = b.rotation("Day", "Day")
        b.segment(day_rot, day, 3, 4)
        b.segment(day_rot, day, 4, 3)

        inv_day_rot = b.rotation("Inverse Day", "Inverse Day")
        b.segment(inv_day_rot, day, 0, 3)
        b.segment(inv_day_rot, day, 4, 4)
        b.segment(inv_day_rot, day, 3, 0)

        night_rot = b.rotation("Night", "Night")
        b.segment(night_rot, night, 4, 3)
        b.segment(night_rot, night, 3, 4)

        inv_night_rot = b.rotation("Inverse Night", "Inverse Night")
        b.segment(inv_night_rot, night, 0, 4)
        b.segment(inv_night_rot, night, 3, 3)
        b.segment(inv_night_rot, night, 4, 0)

        b.team("A", "Day shift", day_rot, self.REFERENCE_DATE)
        b.team("B", "Day inverse shift", inv_day_rot, self.REFERENCE_DATE)
        b.team("C", "Night shift", night_rot, self.REFERENCE_DATE)
        b.team("D", "Night inverse shift", inv_night_rot, self.REFERENCE_DATE)
        self.builder = b

        from_dt = datetime.combine(self.LATER_DATE, self.LATER_TIME)
        to_dt = from_dt + timedelta(days=28)

        self.assert_working_time(from_dt, to_dt, 696)
        self.assert_non_working_time(from_dt, to_dt, 0)

        self.assertEqual(
            compute_schedule_rotation_duration(self.schedule).total_seconds(), 1344 * 3600,
        )
        self.assertEqual(
            compute_schedule_rotation_working_time(self.schedule).total_seconds(), 336 * 3600,
        )

        for team in self.schedule.teams:
            self.assertEqual(compute_rotation_duration(team.rotation).total_seconds(), 336 * 3600)
            self.assertAlmostEqual(compute_team_percentage_worked(team), 25.00, places=2)
            self.assertEqual(compute_rotation_working_time(team.rotation).total_seconds(), 84 * 3600)
            self.assertAlmostEqual(compute_team_average_hours_per_week(team), 42.0, places=2)

        self.run_base_test(timedelta(hours=84), timedelta(days=14))

    # ── postal service ──────────────────────────────────────────────

    def testPostalServiceShifts(self) -> None:
        b = ScheduleBuilder("USPS", "Six 9 hr shifts, rotating every 42 days")
        day = b.shift("Day", "day shift", time(8, 0, 0), timedelta(hours=9))

        rotation = b.rotation("Day", "Day")
        b.segment(rotation, day, 3, 7)
        b.segment(rotation, day, 1, 7)
        b.segment(rotation, day, 1, 7)
        b.segment(rotation, day, 1, 7)
        b.segment(rotation, day, 1, 7)

        b.team("Team A", "A team", rotation, self.REFERENCE_DATE)
        b.team("Team B", "B team", rotation, self.REFERENCE_DATE - timedelta(days=7))
        b.team("Team C", "C team", rotation, self.REFERENCE_DATE - timedelta(days=14))
        b.team("Team D", "D team", rotation, self.REFERENCE_DATE - timedelta(days=21))
        b.team("Team E", "E team", rotation, self.REFERENCE_DATE - timedelta(days=28))
        b.team("Team F", "F team", rotation, self.REFERENCE_DATE - timedelta(days=35))
        self.builder = b

        from_dt = datetime.combine(self.LATER_DATE, self.LATER_TIME)
        to_dt = from_dt + timedelta(days=28)

        self.assert_working_time(from_dt, to_dt, 252)
        self.assert_non_working_time(from_dt, to_dt, 0)

        self.assertEqual(
            compute_schedule_rotation_duration(self.schedule).total_seconds(), 6048 * 3600,
        )
        self.assertEqual(
            compute_schedule_rotation_working_time(self.schedule).total_seconds(), 378 * 3600,
        )

        for team in self.schedule.teams:
            self.assertEqual(compute_rotation_duration(team.rotation).total_seconds(), 1008 * 3600)
            self.assertAlmostEqual(compute_team_percentage_worked(team), 6.25, places=2)
            self.assertEqual(compute_rotation_working_time(team.rotation).total_seconds(), 63 * 3600)
            self.assertAlmostEqual(compute_team_average_hours_per_week(team), 10.50, places=2)

        self.run_base_test(timedelta(hours=63), timedelta(days=42))

    # ── generic 40-hour work week with holidays ─────────────────────

    def testGenericShift(self) -> None:
        b = ScheduleBuilder("Regular 40 hour work week", "9 to 5")

        # holidays (won't overlap with the 21-day test window starting 2016-01-08)
        b.non_working_period("MEMORIAL DAY", "Memorial day",
            datetime.combine(date(2016, 5, 30), time(0, 0, 0)), timedelta(hours=24))
        b.non_working_period("INDEPENDENCE DAY", "Independence day",
            datetime.combine(date(2016, 7, 4), time(0, 0, 0)), timedelta(hours=24))
        b.non_working_period("LABOR DAY", "Labor day",
            datetime.combine(date(2016, 9, 5), time(0, 0, 0)), timedelta(hours=24))
        b.non_working_period("THANKSGIVING", "Thanksgiving day and day after",
            datetime.combine(date(2016, 11, 24), time(0, 0, 0)), timedelta(hours=48))
        b.non_working_period("CHRISTMAS SHUTDOWN", "Christmas week scheduled maintenance",
            datetime.combine(date(2016, 12, 25), time(0, 30, 0)), timedelta(hours=168))

        shift_duration = timedelta(hours=8)
        shift1_start = time(7, 0, 0)
        shift2_start = time(15, 0, 0)

        shift1 = b.shift("Shift1", "Shift #1", shift1_start, shift_duration)
        shift2 = b.shift("Shift2", "Shift #2", shift2_start, shift_duration)

        rotation1 = b.rotation("Shift1", "Shift1")
        b.segment(rotation1, shift1, 5, 2)

        rotation2 = b.rotation("Shift2", "Shift2")
        b.segment(rotation2, shift2, 5, 2)

        start_rotation = date(2016, 1, 1)
        team1 = b.team("Team1", "Team #1", rotation1, start_rotation)
        team2 = b.team("Team2", "Team #2", rotation2, start_rotation)
        self.builder = b
        s = self.schedule

        # 21-day incremental check for team1
        from_dt1 = datetime.combine(start_rotation, shift1_start) + timedelta(days=7)
        d = timedelta()
        total_working = timedelta()
        periods = _build_period_list(rotation1)
        for i in range(21):
            to_dt = from_dt1 + timedelta(days=i)
            total_working = compute_team_working_time(team1, s.non_working_periods, from_dt1, to_dt)
            rotation_day = _day_in_rotation(team1, to_dt.date())
            self.assertEqual(total_working, d,
                msg=f"team1 day {i}: expected {d}, got {total_working}")
            if periods[rotation_day - 1] is not None:
                d += shift_duration

        total_schedule = total_working

        # 21-day incremental check for team2
        from_dt2 = datetime.combine(start_rotation, shift2_start) + timedelta(days=7)
        d = timedelta()
        total_working = timedelta()
        for i in range(21):
            to_dt = from_dt2 + timedelta(days=i)
            total_working = compute_team_working_time(team2, s.non_working_periods, from_dt2, to_dt)
            rotation_day = _day_in_rotation(team2, to_dt.date())
            self.assertEqual(total_working, d,
                msg=f"team2 day {i}: expected {d}, got {total_working}")
            if periods[rotation_day - 1] is not None:
                d += shift_duration

        total_schedule += total_working

        # schedule-level check: working + non-working = per-team sum
        sched_duration = compute_working_time(s, from_dt2, from_dt2 + timedelta(days=21))
        non_working_duration = compute_non_working_time(s, from_dt2, from_dt2 + timedelta(days=21))
        self.assertEqual(sched_duration + non_working_duration, total_schedule)

        self.run_base_test(timedelta(hours=40), timedelta(days=7), date(2016, 1, 1))

    # ── per-team working time (1-on/1-off, non-midnight-crossing) ───

    def testTeamWorkingTime(self) -> None:
        b = ScheduleBuilder("Team Working Time", "Test team working time")
        shift_duration = timedelta(hours=12)
        half_shift = timedelta(hours=6)
        shift_start = time(7, 0, 0)

        shift = b.shift("Team Shift1", "Team shift 1", shift_start, shift_duration)
        rotation = b.rotation("Team", "Rotation")
        b.segment(rotation, shift, 1, 1)

        start_rotation = date(2017, 1, 1)
        team = b.team("Team", "Team", rotation, start_rotation)
        self.builder = b

        base = datetime.combine(start_rotation, shift_start) + timedelta(
            days=rotation.day_count
        )

        # case #1: one day, starting at shift start
        self.assertEqual(
            compute_team_working_time(team, [], base, base + timedelta(days=1)),
            shift_duration,
        )
        # case #2: two days (second day is off)
        self.assertEqual(
            compute_team_working_time(team, [], base, base + timedelta(days=2)),
            shift_duration,
        )
        # case #3: three days (on/off/on)
        self.assertEqual(
            compute_team_working_time(team, [], base, base + timedelta(days=3)),
            shift_duration * 2,
        )
        # case #4: four days (on/off/on/off)
        self.assertEqual(
            compute_team_working_time(team, [], base, base + timedelta(days=4)),
            shift_duration * 2,
        )
        # case #5: start mid-shift
        base5 = base + timedelta(hours=6)
        self.assertEqual(
            compute_team_working_time(team, [], base5, base5 + timedelta(days=1)),
            half_shift,
        )
        # case #6
        self.assertEqual(
            compute_team_working_time(team, [], base5, base5 + timedelta(days=2)),
            shift_duration,
        )
        # case #7
        self.assertEqual(
            compute_team_working_time(team, [], base5, base5 + timedelta(days=3)),
            shift_duration + half_shift,
        )
        # case #8
        self.assertEqual(
            compute_team_working_time(team, [], base5, base5 + timedelta(days=4)),
            shift_duration * 2,
        )

        # ── midnight-crossing shift (18:00 for 12h → ends 06:00) ───
        shift_start2 = time(18, 0, 0)
        shift2 = b.shift("Team Shift2", "Team shift 2", shift_start2, shift_duration)
        rotation2 = b.rotation("Case 8", "Case 8")
        b.segment(rotation2, shift2, 1, 1)
        team2 = b.team("Team2", "Team 2", rotation2, start_rotation)

        base2 = datetime.combine(start_rotation, shift_start2) + timedelta(
            days=rotation.day_count
        )

        # case #1 (night shift, 1 day from shift start)
        self.assertEqual(
            compute_team_working_time(team2, [], base2, base2 + timedelta(days=1)),
            shift_duration,
        )
        # case #2
        self.assertEqual(
            compute_team_working_time(team2, [], base2, base2 + timedelta(days=2)),
            shift_duration,
        )
        # case #3
        self.assertEqual(
            compute_team_working_time(team2, [], base2, base2 + timedelta(days=3)),
            shift_duration * 2,
        )
        # case #4
        self.assertEqual(
            compute_team_working_time(team2, [], base2, base2 + timedelta(days=4)),
            shift_duration * 2,
        )

        # case #5: start at midnight (PyShift: start from time.max on the same day,
        # which rounds to midnight).  Use exact midnight to avoid microsecond drift.
        night_date = base2.date()
        from5 = _next_midnight(night_date)          # next midnight = night_date+1 00:00
        to5 = _next_midnight(night_date, extra_days=1)  # night_date+2 00:00
        self.assertEqual(compute_team_working_time(team2, [], from5, to5), half_shift)

        # case #6
        to6 = _next_midnight(night_date, extra_days=2)
        self.assertEqual(compute_team_working_time(team2, [], from5, to6), shift_duration)

        # case #7
        to7 = _next_midnight(night_date, extra_days=3)
        self.assertEqual(
            compute_team_working_time(team2, [], from5, to7), shift_duration + half_shift,
        )

        # case #8
        to8 = _next_midnight(night_date, extra_days=4)
        self.assertEqual(
            compute_team_working_time(team2, [], from5, to8), shift_duration * 2,
        )

    # ── per-team working time (4-team plan with 14/15.5/14h shifts) ─

    def testTeamWorkingTime2(self) -> None:
        b = ScheduleBuilder("4 Team Plan", "test schedule")
        crossover = b.shift(
            "Crossover", "Day shift #1 cross-over",
            time(7, 0, 0), timedelta(hours=15, minutes=30),
        )
        day = b.shift("Day", "Day shift #2", time(7, 0, 0), timedelta(hours=14))
        night = b.shift("Night", "Night shift", time(22, 0, 0), timedelta(hours=14))

        rotation = b.rotation("4 Team", "4 Team")
        b.segment(rotation, day, 1, 0)
        b.segment(rotation, crossover, 1, 0)
        b.segment(rotation, night, 1, 1)

        team1 = b.team("Team 1", "First team", rotation, self.REFERENCE_DATE)
        self.builder = b

        test_start = self.REFERENCE_DATE + timedelta(days=rotation.day_count)
        am7 = time(7, 0, 0)

        # partial in Day 1
        from_dt = datetime.combine(test_start, am7)
        to_dt = datetime.combine(test_start, time(hour=am7.hour + 1))
        self.assertEqual(
            compute_team_working_time(team1, [], from_dt, to_dt), timedelta(hours=1),
        )

        # full day checks — replace time.max boundary with next midnight
        from_dt = datetime.combine(test_start, time(0, 0, 0))

        # to testStart+1 00:00 (was time.max + 0 days)
        self.assertEqual(
            compute_team_working_time(team1, [], from_dt, _next_midnight(test_start)),
            timedelta(hours=14),
        )
        # to testStart+2 00:00
        self.assertEqual(
            compute_team_working_time(team1, [], from_dt, _next_midnight(test_start, 1)),
            timedelta(hours=29, minutes=30),
        )
        # to testStart+3 00:00 (night shift contributes 2h before midnight)
        self.assertEqual(
            compute_team_working_time(team1, [], from_dt, _next_midnight(test_start, 2)),
            timedelta(hours=31, minutes=30),
        )
        # to testStart+4 00:00 (full night shift now in window)
        self.assertEqual(
            compute_team_working_time(team1, [], from_dt, _next_midnight(test_start, 3)),
            timedelta(hours=43, minutes=30),
        )
        # to testStart+5 00:00 (next day shift)
        self.assertEqual(
            compute_team_working_time(team1, [], from_dt, _next_midnight(test_start, 4)),
            timedelta(hours=57, minutes=30),
        )
        # to testStart+6 00:00
        self.assertEqual(
            compute_team_working_time(team1, [], from_dt, _next_midnight(test_start, 5)),
            timedelta(hours=73),
        )
        # to testStart+7 00:00
        self.assertEqual(
            compute_team_working_time(team1, [], from_dt, _next_midnight(test_start, 6)),
            timedelta(hours=75),
        )
        # to testStart+8 00:00
        self.assertEqual(
            compute_team_working_time(team1, [], from_dt, _next_midnight(test_start, 7)),
            timedelta(hours=87),
        )

        # from the third day in the rotation (night shift day)
        from_dt2 = datetime.combine(test_start + timedelta(days=2), time(0, 0, 0))
        self.assertEqual(
            compute_team_working_time(team1, [], from_dt2, _next_midnight(test_start, 2)),
            timedelta(hours=2),
        )
        self.assertEqual(
            compute_team_working_time(team1, [], from_dt2, _next_midnight(test_start, 3)),
            timedelta(hours=14),
        )
        self.assertEqual(
            compute_team_working_time(team1, [], from_dt2, _next_midnight(test_start, 4)),
            timedelta(hours=28),
        )
        self.assertEqual(
            compute_team_working_time(team1, [], from_dt2, _next_midnight(test_start, 5)),
            timedelta(hours=43, minutes=30),
        )
        self.assertEqual(
            compute_team_working_time(team1, [], from_dt2, _next_midnight(test_start, 6)),
            timedelta(hours=45, minutes=30),
        )

    # ── per-shift working time ──────────────────────────────────────

    def testShiftWorkingTime(self) -> None:
        b = ScheduleBuilder("Working Time1", "Test working time")
        self.builder = b

        # ── 8h day shift (07:00–15:00, non-midnight-crossing) ──────
        shift_duration = timedelta(hours=8)
        shift_start = time(7, 0, 0)
        shift = b.shift("Work Shift1", "Working time shift", shift_start, shift_duration)
        shift_end = shift.end_time

        # case #1: entirely before shift
        self.assertEqual(compute_shift_working_time(shift, time(4, 0, 0), time(5, 0, 0)).total_seconds(), 0)
        self.assertEqual(compute_shift_working_time(shift, time(4, 0, 0), time(4, 0, 0)).total_seconds(), 0)

        # case #2: overlap left edge
        self.assertEqual(compute_shift_working_time(shift, time(6, 0, 0), time(8, 0, 0)).total_seconds(), 3600)

        # case #3: entirely inside
        self.assertEqual(compute_shift_working_time(shift, time(8, 0, 0), time(9, 0, 0)).total_seconds(), 3600)

        # case #4: overlap right edge
        self.assertEqual(compute_shift_working_time(shift, time(14, 0, 0), time(16, 0, 0)).total_seconds(), 3600)

        # case #5: entirely after shift
        self.assertEqual(compute_shift_working_time(shift, time(16, 0, 0), time(17, 0, 0)).total_seconds(), 0)
        self.assertEqual(compute_shift_working_time(shift, time(16, 0, 0), time(16, 0, 0)).total_seconds(), 0)

        # case #6: spans entire shift
        self.assertEqual(
            compute_shift_working_time(shift, time(6, 0, 0), time(16, 0, 0)).total_seconds(),
            shift_duration.total_seconds(),
        )

        # case #7: zero-length inside
        self.assertEqual(compute_shift_working_time(shift, time(8, 0, 0), time(8, 0, 0)).total_seconds(), 0)

        # case #8: start to end
        self.assertEqual(
            compute_shift_working_time(shift, shift_start, shift_end).total_seconds(),
            shift_duration.total_seconds(),
        )

        # case #9: start to start
        self.assertEqual(compute_shift_working_time(shift, shift_start, shift_start).total_seconds(), 0)

        # case #10: end to end
        self.assertEqual(compute_shift_working_time(shift, shift_end, shift_end).total_seconds(), 0)

        # case #11: one second
        self.assertEqual(
            compute_shift_working_time(
                shift, shift_start, time(shift_start.hour, shift_start.minute, shift_start.second + 1),
            ).total_seconds(),
            1,
        )

        # case #12: last hour
        self.assertEqual(
            compute_shift_working_time(shift, time(shift_end.hour - 1, 0, 0), shift_end).total_seconds(),
            3600,
        )

        # ── 8h night shift (22:00–06:00, crosses midnight) ─────────
        shift_start = time(22, 0, 0)
        night = b.shift("Work Shift2", "Working time shift spans midnight", shift_start, shift_duration)
        shift_end = night.end_time

        # case #1
        self.assertEqual(
            compute_shift_total_working_time(night, time(19, 0, 0), time(20, 0, 0), True).total_seconds(), 0,
        )
        self.assertEqual(
            compute_shift_total_working_time(night, time(19, 0, 0), time(19, 0, 0), True).total_seconds(), 0,
        )
        # case #2
        self.assertEqual(
            compute_shift_total_working_time(night, time(21, 0, 0), time(23, 0, 0), True).total_seconds(), 3600,
        )
        # case #3
        self.assertEqual(
            compute_shift_total_working_time(night, time(23, 0, 0), time(0, 0, 0), True).total_seconds(), 3600,
        )
        # case #4 (before_midnight=False — after-midnight portion)
        self.assertEqual(
            compute_shift_total_working_time(night, time(5, 0, 0), time(7, 0, 0), False).total_seconds(), 3600,
        )
        # case #5
        self.assertEqual(
            compute_shift_total_working_time(night, time(7, 0, 0), time(8, 0, 0), True).total_seconds(), 0,
        )
        self.assertEqual(
            compute_shift_total_working_time(night, time(7, 0, 0), time(7, 0, 0), True).total_seconds(), 0,
        )
        # case #6: full span (21:00 to 07:00)
        self.assertEqual(
            compute_shift_total_working_time(night, time(21, 0, 0), time(7, 0, 0), True).total_seconds(),
            shift_duration.total_seconds(),
        )
        # case #7: zero-length inside
        self.assertEqual(
            compute_shift_total_working_time(night, time(23, 0, 0), time(23, 0, 0), True).total_seconds(), 0,
        )
        # case #8: start to end
        self.assertEqual(
            compute_shift_total_working_time(night, shift_start, shift_end, True).total_seconds(),
            shift_duration.total_seconds(),
        )
        # case #9: start to start
        self.assertEqual(
            compute_shift_total_working_time(night, shift_start, shift_start, True).total_seconds(), 0,
        )
        # case #10: end to end
        self.assertEqual(
            compute_shift_total_working_time(night, shift_end, shift_end, True).total_seconds(), 0,
        )
        # case #11: one second from start
        self.assertEqual(
            compute_shift_total_working_time(
                night, shift_start,
                time(shift_start.hour, shift_start.minute, shift_start.second + 1), True,
            ).total_seconds(),
            1,
        )
        # case #12: last hour before end (before_midnight=False)
        self.assertEqual(
            compute_shift_total_working_time(night, time(5, 0, 0), shift_end, False).total_seconds(), 3600,
        )

        # ── 24h shift (07:00 for 24h) ───────────────────────────────
        shift_duration = timedelta(hours=24)
        shift_start = time(7, 0, 0)
        day24 = b.shift("Work Shift3", "Working time shift", shift_start, shift_duration)
        shift_end = day24.end_time  # also time(7, 0, 0) for 24h shift

        # case #1: within 24h shift, before_midnight=False → 1h
        self.assertEqual(
            compute_shift_total_working_time(day24, time(4, 0, 0), time(5, 0, 0), False).total_seconds(), 3600,
        )
        # same range but before_midnight=True → clipped to 0 (before shift start)
        self.assertEqual(
            compute_shift_total_working_time(day24, time(4, 0, 0), time(4, 0, 0), True).total_seconds(), 0,
        )
        # case #2
        self.assertEqual(
            compute_shift_total_working_time(day24, time(6, 0, 0), time(8, 0, 0), True).total_seconds(), 3600,
        )
        # case #3
        self.assertEqual(
            compute_shift_total_working_time(day24, time(8, 0, 0), time(9, 0, 0), True).total_seconds(), 3600,
        )
        # case #4 (end-of-shift boundary; shift_end == shift_start == 07:00 for 24h)
        self.assertEqual(
            compute_shift_total_working_time(day24, time(6, 0, 0), time(8, 0, 0), True).total_seconds(), 3600,
        )
        # case #5
        self.assertEqual(
            compute_shift_total_working_time(day24, time(8, 0, 0), time(9, 0, 0), True).total_seconds(), 3600,
        )
        self.assertEqual(
            compute_shift_total_working_time(day24, time(8, 0, 0), time(8, 0, 0), True).total_seconds(), 0,
        )
        # case #6
        self.assertEqual(
            compute_shift_total_working_time(day24, time(6, 0, 0), time(8, 0, 0), True).total_seconds(), 3600,
        )
        # case #7: zero-length inside
        self.assertEqual(
            compute_shift_total_working_time(day24, time(8, 0, 0), time(8, 0, 0), True).total_seconds(), 0,
        )
        # case #8: full 24h
        self.assertEqual(
            compute_shift_total_working_time(day24, shift_start, shift_end, True).total_seconds(),
            shift_duration.total_seconds(),
        )
        # case #9: start to start (also 24h for 24h shift)
        self.assertEqual(
            compute_shift_total_working_time(day24, shift_start, shift_start, True).total_seconds(),
            shift_duration.total_seconds(),
        )
        # case #10: end to end (also 24h)
        self.assertEqual(
            compute_shift_total_working_time(day24, shift_end, shift_end, True).total_seconds(),
            shift_duration.total_seconds(),
        )
        # case #11: one second from start
        self.assertEqual(
            compute_shift_total_working_time(
                day24, shift_start,
                time(shift_start.hour, shift_start.minute, shift_start.second + 1), True,
            ).total_seconds(),
            1,
        )
        # case #12 (before_midnight=False)
        self.assertEqual(
            compute_shift_total_working_time(day24, time(6, 0, 0), shift_end, False).total_seconds(), 3600,
        )

    # ── non-working time ────────────────────────────────────────────

    def testNonWorkingTime(self) -> None:
        b = ScheduleBuilder("Non Working Time", "Test non working time")
        local_date = date(2017, 1, 1)
        local_time = time(7, 0, 0)

        period1 = b.non_working_period(
            "Day1", "First test day",
            datetime.combine(local_date, time(0, 0, 0)), timedelta(hours=24),
        )
        period2 = b.non_working_period(
            "Day2", "Second test day",
            datetime.combine(local_date, local_time) + timedelta(days=7), timedelta(hours=24),
        )
        self.builder = b
        s = self.schedule

        # case #1: 1h inside period1
        from_dt = datetime.combine(local_date, local_time)
        to_dt = datetime.combine(local_date, time(local_time.hour + 1, 0, 0))
        self.assertEqual(compute_non_working_time(s, from_dt, to_dt), timedelta(hours=1))

        # case #2: spans period1 fully
        from_dt = datetime.combine(local_date, local_time) - timedelta(days=1)
        to_dt = datetime.combine(local_date, local_time) + timedelta(days=1)
        self.assertEqual(compute_non_working_time(s, from_dt, to_dt), timedelta(hours=24))

        # case #3: before period1
        from_dt = datetime.combine(local_date, local_time) - timedelta(days=1)
        to_dt = datetime.combine(local_date, time(local_time.hour + 1, 0, 0)) - timedelta(days=1)
        self.assertEqual(compute_non_working_time(s, from_dt, to_dt), timedelta(hours=0))

        # case #4: after period1
        from_dt = datetime.combine(local_date, local_time) + timedelta(days=1)
        to_dt = datetime.combine(local_date, time(local_time.hour + 1, 0, 0)) + timedelta(days=1)
        self.assertEqual(compute_non_working_time(s, from_dt, to_dt), timedelta(hours=0))

        # case #5: partial before period1 end (7h of 24h period)
        from_dt = datetime.combine(local_date, local_time) - timedelta(days=1)
        to_dt = datetime.combine(local_date, local_time)
        self.assertEqual(compute_non_working_time(s, from_dt, to_dt), timedelta(hours=7))

        # case #6: partial from start into period1 (17h)
        from_dt = datetime.combine(local_date, local_time)
        to_dt = datetime.combine(local_date, local_time) + timedelta(days=1)
        self.assertEqual(compute_non_working_time(s, from_dt, to_dt), timedelta(hours=17))

        # case #7: straddles end of period1, start of period2
        from_dt = datetime.combine(local_date, time(12, 0, 0))
        to_dt = datetime.combine(local_date, time(12, 0, 0)) + timedelta(days=7)
        self.assertEqual(compute_non_working_time(s, from_dt, to_dt), timedelta(hours=17))

        # case #8: spans both periods
        from_dt = datetime.combine(local_date, time(12, 0, 0)) - timedelta(days=1)
        to_dt = datetime.combine(local_date, time(12, 0, 0)) + timedelta(days=8)
        self.assertEqual(compute_non_working_time(s, from_dt, to_dt), timedelta(hours=48))

        # case #9: deactivate both periods → non-working time = 0
        period1.is_active = False
        period2.is_active = False
        from_dt = datetime.combine(local_date, local_time)
        to_dt = datetime.combine(local_date, time(local_time.hour + 1, 0, 0))
        # case #10
        self.assertEqual(compute_non_working_time(s, from_dt, to_dt), timedelta(hours=0))

        # restore and add a shift/team for combined working-time checks
        period1.is_active = True

        shift_duration = timedelta(hours=8)
        shift_start = time(7, 0, 0)
        shift = b.shift("Work Shift1", "Working time shift", shift_start, shift_duration)
        rotation = b.rotation("Case 10", "Case10")
        b.segment(rotation, shift, 1, 1)
        start_rotation = date(2017, 1, 1)
        team = b.team("Team", "Team", rotation, start_rotation)

        mark = local_date + timedelta(days=rotation.day_count)
        # case #11: working time before shift start → 0
        from_dt = datetime.combine(mark, time(local_time.hour - 2, 0, 0))
        to_dt = datetime.combine(mark, time(local_time.hour - 1, 0, 0))
        self.assertEqual(compute_working_time(s, from_dt, to_dt), timedelta(hours=0))

        # case #12: non-working time spanning 8h inside period1
        from_dt = datetime.combine(local_date, shift_start)
        to_dt = datetime.combine(local_date, time(local_time.hour + 8, 0, 0))
        self.assertEqual(compute_non_working_time(s, from_dt, to_dt), timedelta(hours=8))


# ═══════════════════════════════════════════════════════════════════════════════
# Snap-schedule tests (porting TestSnapSchedule)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSnapScheduleDomain(BaseDomainTest):

    def _snap_checks(
        self,
        expected_working_hours: float,
        rotation_duration_hours: float,
        rotation_working_hours: float,
        per_team_duration_hours: float,
        per_team_pct: float,
        per_team_working_hours: float,
        per_team_avg_hrs_per_week: float,
        base_test_hours_per_rot: float,
        base_test_rot_days: int,
        starting_date: date | None = None,
    ) -> None:
        s = self.schedule
        from_dt = datetime.combine(self.LATER_DATE, self.LATER_TIME)
        to_dt = from_dt + timedelta(days=28)

        self.assert_working_time(from_dt, to_dt, expected_working_hours)
        self.assert_non_working_time(from_dt, to_dt, 0)

        self.assertEqual(
            compute_schedule_rotation_duration(s).total_seconds(),
            rotation_duration_hours * 3600,
        )
        self.assertEqual(
            compute_schedule_rotation_working_time(s).total_seconds(),
            rotation_working_hours * 3600,
        )

        for team in s.teams:
            self.assertEqual(
                compute_rotation_duration(team.rotation).total_seconds(),
                per_team_duration_hours * 3600,
            )
            self.assertAlmostEqual(
                compute_team_percentage_worked(team), per_team_pct, places=2,
            )
            self.assertEqual(
                compute_rotation_working_time(team.rotation).total_seconds(),
                per_team_working_hours * 3600,
            )
            self.assertAlmostEqual(
                compute_team_average_hours_per_week(team), per_team_avg_hrs_per_week, places=1,
            )

        self.run_base_test(
            timedelta(hours=base_test_hours_per_rot),
            timedelta(days=base_test_rot_days),
            starting_date,
        )

    # ── Low Night demand ────────────────────────────────────────────

    def testLowNight(self) -> None:
        b = ScheduleBuilder("Low Night Demand Plan", "Low night demand")
        day = b.shift("Day", "Day shift", time(7, 0, 0), timedelta(hours=8))
        swing = b.shift("Swing", "Swing shift", time(15, 0, 0), timedelta(hours=8))
        night = b.shift("Night", "Night shift", time(23, 0, 0), timedelta(hours=8))

        rotation = b.rotation("Low night demand", "Low night demand")
        b.segment(rotation, day, 3, 0)
        b.segment(rotation, swing, 4, 3)
        b.segment(rotation, day, 4, 0)
        b.segment(rotation, swing, 3, 4)
        b.segment(rotation, day, 3, 0)
        b.segment(rotation, night, 4, 3)
        b.segment(rotation, day, 4, 0)
        b.segment(rotation, night, 3, 4)

        for i, offset in enumerate([0, -21, -7, -28, -14, -35]):
            b.team(f"Team{i+1}", f"Team {i+1}", rotation, self.REFERENCE_DATE + timedelta(days=offset))
        self.builder = b

        self._snap_checks(
            expected_working_hours=896,
            rotation_duration_hours=6048,
            rotation_working_hours=1344,
            per_team_duration_hours=1008,
            per_team_pct=22.22,
            per_team_working_hours=224,
            per_team_avg_hrs_per_week=37.33,
            base_test_hours_per_rot=224,
            base_test_rot_days=42,
        )

    # ── 3 Team Fixed 24 ─────────────────────────────────────────────

    def test3TeamFixed24(self) -> None:
        b = ScheduleBuilder("3 Team Fixed 24 Plan", "Fire departments")
        shift = b.shift("24 Hour", "24 hour shift", time(0, 0, 0), timedelta(hours=24))

        rotation = b.rotation("3 Team Fixed 24 Plan", "3 Team Fixed 24 Plan")
        b.segment(rotation, shift, 1, 1)
        b.segment(rotation, shift, 1, 1)
        b.segment(rotation, shift, 1, 4)

        b.team("Team1", "First team", rotation, self.REFERENCE_DATE)
        b.team("Team2", "Second team", rotation, self.REFERENCE_DATE - timedelta(days=3))
        b.team("Team3", "Third team", rotation, self.REFERENCE_DATE - timedelta(days=6))
        self.builder = b

        self._snap_checks(
            expected_working_hours=672,
            rotation_duration_hours=648,
            rotation_working_hours=216,
            per_team_duration_hours=216,
            per_team_pct=33.33,
            per_team_working_hours=72,
            per_team_avg_hrs_per_week=56,
            base_test_hours_per_rot=72,
            base_test_rot_days=9,
        )

    # ── 5/4/9 plan ──────────────────────────────────────────────────

    def test549(self) -> None:
        b = ScheduleBuilder("5/4/9 Plan", "Compressed work workSchedule.")
        day1 = b.shift("Day1", "Day shift #1", time(7, 0, 0), timedelta(hours=9))
        day2 = b.shift("Day2", "Day shift #2", time(7, 0, 0), timedelta(hours=8))

        rotation = b.rotation("5/4/9 ", "5/4/9 ")
        b.segment(rotation, day1, 4, 0)
        b.segment(rotation, day2, 1, 3)
        b.segment(rotation, day1, 4, 3)
        b.segment(rotation, day1, 4, 2)
        b.segment(rotation, day1, 4, 0)
        b.segment(rotation, day2, 1, 2)

        b.team("Team1", "First team", rotation, self.REFERENCE_DATE)
        b.team("Team2", "Second team", rotation, self.REFERENCE_DATE - timedelta(days=14))
        self.builder = b

        self._snap_checks(
            expected_working_hours=320,
            rotation_duration_hours=1344,
            rotation_working_hours=320,
            per_team_duration_hours=672,
            per_team_pct=23.81,
            per_team_working_hours=160,
            per_team_avg_hrs_per_week=40,
            base_test_hours_per_rot=160,
            base_test_rot_days=28,
        )

    # ── 9-to-5 ──────────────────────────────────────────────────────

    def test9to5(self) -> None:
        b = ScheduleBuilder(
            "9 To 5 Plan",
            "Basic 9 to 5 workSchedule plan for office employees.",
        )
        day = b.shift("Day", "Day shift", time(9, 0, 0), timedelta(hours=8))

        rotation = b.rotation("9 To 5 ", "9 To 5 ")
        b.segment(rotation, day, 5, 2)

        b.team("Team", "One team", rotation, self.REFERENCE_DATE)
        self.builder = b

        from_dt = datetime.combine(self.LATER_DATE, self.LATER_TIME)
        to_dt = from_dt + timedelta(days=28)

        self.assert_working_time(from_dt, to_dt, 160)
        self.assert_non_working_time(from_dt, to_dt, 0)

        self.assertEqual(
            compute_schedule_rotation_duration(self.schedule).total_seconds(), 168 * 3600,
        )
        self.assertEqual(
            compute_schedule_rotation_working_time(self.schedule).total_seconds(), 40 * 3600,
        )

        for team in self.schedule.teams:
            self.assertEqual(compute_rotation_duration(team.rotation).total_seconds(), 168 * 3600)
            self.assertAlmostEqual(compute_team_percentage_worked(team), 23.81, places=2)
            self.assertEqual(compute_rotation_working_time(team.rotation).total_seconds(), 40 * 3600)
            self.assertAlmostEqual(compute_team_average_hours_per_week(team), 40, places=1)

        self.run_base_test(timedelta(hours=40), timedelta(days=7))

    # ── 8 Plus 12 ───────────────────────────────────────────────────

    def test8Plus12(self) -> None:
        b = ScheduleBuilder("8 Plus 12 Plan", "Fast rotation plan.")
        day1 = b.shift("Day1", "Day shift #1", time(7, 0, 0), timedelta(hours=12))
        day2 = b.shift("Day2", "Day shift #2", time(7, 0, 0), timedelta(hours=8))
        swing = b.shift("Swing", "Swing shift", time(15, 0, 0), timedelta(hours=8))
        night1 = b.shift("Night1", "Night shift #1", time(19, 0, 0), timedelta(hours=12))
        night2 = b.shift("Night2", "Night shift #2", time(23, 0, 0), timedelta(hours=8))

        rotation = b.rotation("8 Plus 12", "8 Plus 12")
        b.segment(rotation, day2, 5, 0)
        b.segment(rotation, day1, 2, 3)
        b.segment(rotation, night2, 2, 0)
        b.segment(rotation, night1, 2, 0)
        b.segment(rotation, night2, 3, 4)
        b.segment(rotation, swing, 5, 2)

        for i in range(4):
            b.team(f"Team {i+1}", f"Team {i+1}", rotation,
                   self.REFERENCE_DATE - timedelta(days=7 * i))
        self.builder = b

        self._snap_checks(
            expected_working_hours=672,
            rotation_duration_hours=2688,
            rotation_working_hours=672,
            per_team_duration_hours=672,
            per_team_pct=25.00,
            per_team_working_hours=168,
            per_team_avg_hrs_per_week=42,
            base_test_hours_per_rot=168,
            base_test_rot_days=28,
        )

    # ── ICU Interns ─────────────────────────────────────────────────

    def testICUInterns(self) -> None:
        b = ScheduleBuilder("ICU Interns Plan", "ICU intern rotation plan.")
        crossover = b.shift(
            "Crossover", "Day shift #1 cross-over",
            time(7, 0, 0), timedelta(hours=15, minutes=30),
        )
        day = b.shift("Day", "Day shift #2", time(7, 0, 0), timedelta(hours=14))
        night = b.shift("Night", "Night shift", time(22, 0, 0), timedelta(hours=14))

        rotation = b.rotation("ICU", "ICU")
        b.segment(rotation, day, 1, 0)
        b.segment(rotation, crossover, 1, 0)
        b.segment(rotation, night, 1, 1)

        b.team("Team 1", "First team", rotation, self.REFERENCE_DATE)
        b.team("Team 2", "Second team", rotation, self.REFERENCE_DATE - timedelta(days=3))
        b.team("Team 3", "Third team", rotation, self.REFERENCE_DATE - timedelta(days=2))
        b.team("Team 4", "Forth team", rotation, self.REFERENCE_DATE - timedelta(days=1))
        self.builder = b

        from_dt = datetime.combine(self.LATER_DATE, self.LATER_TIME)
        to_dt = from_dt + timedelta(days=28)

        self.assert_working_time(from_dt, to_dt, 1223)
        self.assert_non_working_time(from_dt, to_dt, 0)

        self.assertEqual(
            compute_schedule_rotation_duration(self.schedule).total_seconds(), 384 * 3600,
        )
        self.assertEqual(
            compute_schedule_rotation_working_time(self.schedule).total_seconds(), 174 * 3600,
        )

        for team in self.schedule.teams:
            self.assertEqual(compute_rotation_duration(team.rotation).total_seconds(), 96 * 3600)
            self.assertAlmostEqual(compute_team_percentage_worked(team), 45.31, places=2)
            self.assertEqual(
                compute_rotation_working_time(team.rotation).total_seconds(),
                43 * 3600 + 30 * 60,
            )
            self.assertAlmostEqual(compute_team_average_hours_per_week(team), 76.125, places=1)

        self.run_base_test(timedelta(minutes=2610), timedelta(days=4))

    # ── DuPont 12h rotating ─────────────────────────────────────────

    def testDupont(self) -> None:
        b = ScheduleBuilder("DuPont Schedule", "DuPont 12-hour rotating shift schedule.")
        day = b.shift("Day", "Day shift", time(7, 0, 0), timedelta(hours=12))
        night = b.shift("Night", "Night shift", time(19, 0, 0), timedelta(hours=12))

        rotation = b.rotation("DuPont", "DuPont")
        b.segment(rotation, night, 4, 3)
        b.segment(rotation, day, 3, 1)
        b.segment(rotation, night, 3, 3)
        b.segment(rotation, day, 4, 7)

        for i in range(4):
            b.team(f"Team {i+1}", f"Team {i+1}", rotation,
                   self.REFERENCE_DATE - timedelta(days=7 * i))
        self.builder = b

        self._snap_checks(
            expected_working_hours=672,
            rotation_duration_hours=2688,
            rotation_working_hours=672,
            per_team_duration_hours=672,
            per_team_pct=25.00,
            per_team_working_hours=168,
            per_team_avg_hrs_per_week=42.0,
            base_test_hours_per_rot=168,
            base_test_rot_days=28,
        )

    # ── DNO ─────────────────────────────────────────────────────────

    def testDNO(self) -> None:
        b = ScheduleBuilder("DNO Plan", "Day-Night-Off fast rotation.")
        day = b.shift("Day", "Day shift", time(7, 0, 0), timedelta(hours=12))
        night = b.shift("Night", "Night shift", time(19, 0, 0), timedelta(hours=12))

        rotation = b.rotation("DNO", "DNO")
        b.segment(rotation, day, 1, 0)
        b.segment(rotation, night, 1, 1)

        b.team("Team 1", "First team", rotation, self.REFERENCE_DATE)
        b.team("Team 2", "Second team", rotation, self.REFERENCE_DATE - timedelta(days=1))
        b.team("Team 3", "Third team", rotation, self.REFERENCE_DATE - timedelta(days=2))
        self.builder = b

        self._snap_checks(
            expected_working_hours=672,
            rotation_duration_hours=216,
            rotation_working_hours=72,
            per_team_duration_hours=72,
            per_team_pct=33.33,
            per_team_working_hours=24,
            per_team_avg_hrs_per_week=56.0,
            base_test_hours_per_rot=24,
            base_test_rot_days=3,
        )

    # ── 21 Team Fixed ───────────────────────────────────────────────

    def test21TeamFixed(self) -> None:
        b = ScheduleBuilder("21 Team Fixed 8 6D Plan", "21-team fixed 8-hr shift plan.")
        day = b.shift("Day", "Day shift", time(7, 0, 0), timedelta(hours=8))
        swing = b.shift("Swing", "Swing shift", time(15, 0, 0), timedelta(hours=8))
        night = b.shift("Night", "Night shift", time(23, 0, 0), timedelta(hours=8))

        def make_rot(name: str, sh: WorkShift) -> WorkRotation:
            r = b.rotation(name, name)
            b.segment(r, sh, 6, 3)
            b.segment(r, sh, 5, 3)
            b.segment(r, sh, 6, 2)
            b.segment(r, sh, 6, 2)
            b.segment(r, sh, 6, 2)
            b.segment(r, sh, 6, 2)
            return r

        day_rot = make_rot("Day", day)
        swing_rot = make_rot("Swing", swing)
        night_rot = make_rot("Night", night)

        for i in range(7):
            b.team(f"Team {i+1}", f"{i+1}st day team", day_rot,
                   self.REFERENCE_DATE + timedelta(days=7 * i))
        for i in range(7):
            b.team(f"Team {i+8}", f"{i+1}st swing team", swing_rot,
                   self.REFERENCE_DATE + timedelta(days=7 * i))
        for i in range(7):
            b.team(f"Team {i+15}", f"{i+1}st night team", night_rot,
                   self.REFERENCE_DATE + timedelta(days=7 * i))
        self.builder = b

        from_dt = datetime.combine(self.LATER_DATE, self.LATER_TIME)
        to_dt = from_dt + timedelta(days=28)

        self.assert_working_time(from_dt, to_dt, 3360)
        self.assert_non_working_time(from_dt, to_dt, 0)

        self.assertEqual(
            compute_schedule_rotation_duration(self.schedule).total_seconds(), 24696 * 3600,
        )
        self.assertEqual(
            compute_schedule_rotation_working_time(self.schedule).total_seconds(), 5880 * 3600,
        )

        for team in self.schedule.teams:
            self.assertEqual(compute_rotation_duration(team.rotation).total_seconds(), 1176 * 3600)
            self.assertAlmostEqual(compute_team_percentage_worked(team), 23.81, places=2)
            self.assertEqual(compute_rotation_working_time(team.rotation).total_seconds(), 280 * 3600)
            self.assertAlmostEqual(compute_team_average_hours_per_week(team), 40.0, places=1)

        self.run_base_test(
            timedelta(hours=280),
            timedelta(days=49),
            self.REFERENCE_DATE + timedelta(days=49),
        )

    # ── Two Team Fixed 12 ───────────────────────────────────────────

    def testTwoTeam(self) -> None:
        b = ScheduleBuilder("2 Team Fixed 12 Plan", "Two-team 12-hr fixed schedule.")
        day = b.shift("Day", "Day shift", time(7, 0, 0), timedelta(hours=12))
        night = b.shift("Night", "Night shift", time(19, 0, 0), timedelta(hours=12))

        team1_rot = b.rotation("Team1", "Team1")
        b.segment(team1_rot, day, 1, 0)

        team2_rot = b.rotation("Team2", "Team2")
        b.segment(team2_rot, night, 1, 0)

        b.team("Team 1", "First team", team1_rot, self.REFERENCE_DATE)
        b.team("Team 2", "Second team", team2_rot, self.REFERENCE_DATE)
        self.builder = b

        from_dt = datetime.combine(self.LATER_DATE, self.LATER_TIME)
        to_dt = from_dt + timedelta(days=28)

        self.assert_working_time(from_dt, to_dt, 1320)
        self.assert_non_working_time(from_dt, to_dt, 0)

        self.assertEqual(
            compute_schedule_rotation_duration(self.schedule).total_seconds(), 48 * 3600,
        )
        self.assertEqual(
            compute_schedule_rotation_working_time(self.schedule).total_seconds(), 24 * 3600,
        )

        for team in self.schedule.teams:
            self.assertEqual(compute_rotation_duration(team.rotation).total_seconds(), 24 * 3600)
            self.assertAlmostEqual(compute_team_percentage_worked(team), 50.00, places=2)
            self.assertEqual(compute_rotation_working_time(team.rotation).total_seconds(), 12 * 3600)
            self.assertAlmostEqual(compute_team_average_hours_per_week(team), 84.0, places=1)

        self.run_base_test(timedelta(hours=12), timedelta(days=1))

    # ── Panama ──────────────────────────────────────────────────────

    def testPanama(self) -> None:
        b = ScheduleBuilder("Panama", "Slow rotation 2-2-3 Panama plan.")
        day = b.shift("Day", "Day shift", time(7, 0, 0), timedelta(hours=12))
        night = b.shift("Night", "Night shift", time(19, 0, 0), timedelta(hours=12))

        rotation = b.rotation("Panama", "2 on, 2 off, 3 on, 2 off, 2 on, 3 off")
        # day half
        b.segment(rotation, day, 2, 2)
        b.segment(rotation, day, 3, 2)
        b.segment(rotation, day, 2, 3)
        b.segment(rotation, day, 2, 2)
        b.segment(rotation, day, 3, 2)
        b.segment(rotation, day, 2, 3)
        # night half
        b.segment(rotation, night, 2, 2)
        b.segment(rotation, night, 3, 2)
        b.segment(rotation, night, 2, 3)
        b.segment(rotation, night, 2, 2)
        b.segment(rotation, night, 3, 2)
        b.segment(rotation, night, 2, 3)

        b.team("Team 1", "First team", rotation, self.REFERENCE_DATE)
        b.team("Team 2", "Second team", rotation, self.REFERENCE_DATE - timedelta(days=28))
        b.team("Team 3", "Third team", rotation, self.REFERENCE_DATE - timedelta(days=7))
        b.team("Team 4", "Fourth team", rotation, self.REFERENCE_DATE - timedelta(days=35))
        self.builder = b

        self._snap_checks(
            expected_working_hours=672,
            rotation_duration_hours=5376,
            rotation_working_hours=1344,
            per_team_duration_hours=1344,
            per_team_pct=25.00,
            per_team_working_hours=336,
            per_team_avg_hrs_per_week=42.0,
            base_test_hours_per_rot=336,
            base_test_rot_days=56,
        )


if __name__ == "__main__":
    unittest.main()
