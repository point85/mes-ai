"""
INVENTORY: Domain exceptions.
"""

from mes.framework.api.exceptions import MESException


class DuplicateLocationCodeException(MESException):
    """Raised when a storage location code already exists."""

    status_code = 409
    error_code = "DUPLICATE_LOCATION_CODE"

    def __init__(self, code: str) -> None:
        super().__init__(
            message=f"Storage location with code '{code}' already exists",
            details={"location_code": code},
        )


class LocationNotFoundException(MESException):
    """Raised when a storage location is not found."""

    status_code = 404
    error_code = "LOCATION_NOT_FOUND"

    def __init__(self, location_id: str) -> None:
        super().__init__(
            message=f"Storage location '{location_id}' not found",
            details={"location_id": location_id},
        )


class InsufficientInventoryException(MESException):
    """Raised when a location does not have enough inventory for the operation."""

    status_code = 422
    error_code = "INSUFFICIENT_INVENTORY"

    def __init__(
        self, location_id: str, requested: float, available: float,
    ) -> None:
        super().__init__(
            message=(
                f"Insufficient inventory at location '{location_id}': "
                f"requested {requested}, available {available}"
            ),
            details={
                "location_id": location_id,
                "requested": requested,
                "available": available,
            },
        )


class InvalidTransactionException(MESException):
    """Raised when an inventory transaction violates business rules."""

    status_code = 422
    error_code = "INVALID_INVENTORY_TRANSACTION"

    def __init__(self, message: str) -> None:
        super().__init__(message=message)
