"""
DISPATCH: Domain exceptions.
"""

from mes.framework.api.exceptions import MESException


class NoEligibleEquipmentException(MESException):
    """Raised when no equipment is available for dispatch."""

    status_code = 422
    error_code = "NO_ELIGIBLE_EQUIPMENT"

    def __init__(self, step_id: str | None = None, reason: str = "") -> None:
        details: dict[str, str | None] = {"step_id": step_id}
        if reason:
            details["reason"] = reason
        super().__init__(
            message=f"No eligible equipment available for dispatch{': ' + reason if reason else ''}",
            details=details,
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


class EquipmentAtCapacityException(MESException):
    """Raised when all candidate equipment queues are full."""

    status_code = 422
    error_code = "EQUIPMENT_AT_CAPACITY"

    def __init__(self, step_id: str | None = None) -> None:
        super().__init__(
            message="All candidate equipment queues are at maximum capacity",
            details={"step_id": step_id},
        )


class MaterialCapabilityException(MESException):
    """Raised when no equipment is set up to process the required material."""

    status_code = 422
    error_code = "MATERIAL_CAPABILITY_MISMATCH"

    def __init__(self, material_id: str, step_id: str | None = None) -> None:
        super().__init__(
            message=f"No equipment is set up to process material '{material_id}'",
            details={"material_id": material_id, "step_id": step_id},
        )
