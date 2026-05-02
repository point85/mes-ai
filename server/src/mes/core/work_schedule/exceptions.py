"""
Work Schedule: custom exceptions.
"""

from mes.framework.api.exceptions import MESException


class WorkScheduleNotFoundException(MESException):
    status_code = 404
    def __init__(self, schedule_id: str) -> None:
        super().__init__(f"Work schedule '{schedule_id}' not found")


class WorkShiftNotFoundException(MESException):
    status_code = 404
    def __init__(self, shift_id: str) -> None:
        super().__init__(f"Work shift '{shift_id}' not found")


class WorkRotationNotFoundException(MESException):
    status_code = 404
    def __init__(self, rotation_id: str) -> None:
        super().__init__(f"Work rotation '{rotation_id}' not found")


class WorkTeamNotFoundException(MESException):
    status_code = 404
    def __init__(self, team_id: str) -> None:
        super().__init__(f"Work team '{team_id}' not found")


class TeamMemberNotFoundException(MESException):
    status_code = 404
    def __init__(self, member_id: str) -> None:
        super().__init__(f"Team member '{member_id}' not found")


class NonWorkingPeriodNotFoundException(MESException):
    status_code = 404
    def __init__(self, period_id: str) -> None:
        super().__init__(f"Non-working period '{period_id}' not found")


class DuplicateWorkScheduleNameException(MESException):
    status_code = 409
    def __init__(self, name: str) -> None:
        super().__init__(f"Work schedule with name '{name}' already exists")
