"""
PERF-ANALYSIS: Domain exceptions.
"""

from mes.framework.api.exceptions import MESException


class NoStateLogDataException(MESException):
    """Raised when there is no state log data for the requested period."""

    status_code = 404
    error_code = "NO_STATE_LOG_DATA"

    def __init__(self, equipment_id: str, period: str) -> None:
        super().__init__(
            message=f"No equipment state log data for equipment '{equipment_id}' in period '{period}'",
            details={
                "equipment_id": equipment_id,
                "period": period,
            },
        )


class NoCounterDataException(MESException):
    """Raised when there is no production counter for OEE Performance/Quality calc."""

    status_code = 404
    error_code = "NO_COUNTER_DATA"

    def __init__(self, equipment_id: str, period: str) -> None:
        super().__init__(
            message=f"No production counter data for equipment '{equipment_id}' in period '{period}'",
            details={
                "equipment_id": equipment_id,
                "period": period,
            },
        )
