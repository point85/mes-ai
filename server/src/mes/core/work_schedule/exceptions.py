"""
Work Schedule: custom exceptions.
"""

from mes.framework.api.exceptions import MESException


class WorkScheduleNotFoundException(MESException):
    def __init__(self, schedule_id: str) -> None:
        super().__init__(f"Work schedule '{schedule_id}' not found", status_code=404)


class WorkShiftNotFoundException(MESException):
    def __init__(self, shift_id: str) -> None:
        super().__init__(f"Work shift '{shift_id}' not found", status_code=404)


class WorkRotationNotFoundException(MESException):
    def __init__(self, rotation_id: str) -> None:
        super().__init__(f"Work rotation '{rotation_id}' not found", status_code=404)


class WorkTeamNotFoundException(MESException):
    def __init__(self, team_id: str) -> None:
        super().__init__(f"Work team '{team_id}' not found", status_code=404)


class TeamMemberNotFoundException(MESException):
    def __init__(self, member_id: str) -> None:
        super().__init__(f"Team member '{member_id}' not found", status_code=404)


class NonWorkingPeriodNotFoundException(MESException):
    def __init__(self, period_id: str) -> None:
        super().__init__(f"Non-working period '{period_id}' not found", status_code=404)


class DuplicateWorkScheduleNameException(MESException):
    def __init__(self, name: str) -> None:
        super().__init__(f"Work schedule with name '{name}' already exists", status_code=409)
