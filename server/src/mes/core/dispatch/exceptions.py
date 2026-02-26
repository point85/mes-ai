"""
DISPATCH: Domain exceptions.
"""

from mes.framework.api.exceptions import MESException


class NoEligibleEquipmentException(MESException):
    """Raised when no equipment is available for dispatch."""

    status_code = 422
    error_code = "NO_ELIGIBLE_EQUIPMENT"

    def __init__(self, step_id: str | None = None) -> None:
        super().__init__(
            message="No eligible equipment available for dispatch",
            details={"step_id": step_id},
        )


class InvalidDispatchTargetException(MESException):
    """Raised when the selected dispatch destination is not valid."""

    status_code = 422
    error_code = "INVALID_DISPATCH_TARGET"

    def __init__(self, equipment_id: str, reason: str) -> None:
        super().__init__(
            message=f"Invalid dispatch target: equipment '{equipment_id}' — {reason}",
            details={
                "equipment_id": equipment_id,
                "reason": reason,
            },
        )


class NoRouteForDispatchException(MESException):
    """Raised when a unit/lot has no route assigned for dispatch evaluation."""

    status_code = 422
    error_code = "NO_ROUTE_FOR_DISPATCH"

    def __init__(self, identifier: str) -> None:
        super().__init__(
            message=f"No route assigned for dispatch evaluation: '{identifier}'",
            details={"identifier": identifier},
        )
