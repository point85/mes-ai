"""
WIP-TRACK: Domain exceptions.
"""

from mes.framework.api.exceptions import MESException


class DuplicateSerialNumberException(MESException):
    """Raised when a unit serial number already exists."""

    status_code = 409
    error_code = "DUPLICATE_SERIAL_NUMBER"

    def __init__(self, serial_number: str) -> None:
        super().__init__(
            message=f"Unit with serial number '{serial_number}' already exists",
            details={"serial_number": serial_number},
        )


class DuplicateLotNumberException(MESException):
    """Raised when a lot number already exists."""

    status_code = 409
    error_code = "DUPLICATE_LOT_NUMBER"

    def __init__(self, lot_number: str) -> None:
        super().__init__(
            message=f"Lot with lot number '{lot_number}' already exists",
            details={"lot_number": lot_number},
        )


class InvalidWIPTransitionException(MESException):
    """Raised when a WIP status transition is not allowed."""

    status_code = 422
    error_code = "INVALID_WIP_TRANSITION"

    def __init__(self, identifier: str, current: str, action: str) -> None:
        super().__init__(
            message=f"Cannot '{action}' {identifier} — current status is '{current}'",
            details={
                "identifier": identifier,
                "current_status": current,
                "action": action,
            },
        )


class NoRouteAssignedException(MESException):
    """Raised when attempting to move WIP but no route is assigned to the order."""

    status_code = 422
    error_code = "NO_ROUTE_ASSIGNED"

    def __init__(self, order_id: str) -> None:
        super().__init__(
            message=f"Production order '{order_id}' has no route assigned and no default route exists",
            details={"order_id": order_id},
        )


class NoNextStepException(MESException):
    """Raised when there is no next step in the route."""

    status_code = 422
    error_code = "NO_NEXT_STEP"

    def __init__(self, identifier: str, current_step_id: str | None) -> None:
        super().__init__(
            message=f"No next step available for '{identifier}' (current step: {current_step_id})",
            details={
                "identifier": identifier,
                "current_step_id": current_step_id,
            },
        )
