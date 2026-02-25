"""
MAT-MGMT: Domain exceptions.
"""

from mes.framework.api.exceptions import MESException


class DuplicateMaterialCodeException(MESException):
    """Raised when a material code already exists."""

    status_code = 409
    error_code = "DUPLICATE_MATERIAL_CODE"

    def __init__(self, code: str) -> None:
        super().__init__(
            message=f"Material with code '{code}' already exists",
            details={"material_code": code},
        )


class DuplicateLotNumberException(MESException):
    """Raised when a material lot number already exists."""

    status_code = 409
    error_code = "DUPLICATE_LOT_NUMBER"

    def __init__(self, lot_number: str) -> None:
        super().__init__(
            message=f"Material lot with number '{lot_number}' already exists",
            details={"lot_number": lot_number},
        )


class InsufficientQuantityException(MESException):
    """Raised when a material lot does not have enough on-hand quantity."""

    status_code = 422
    error_code = "INSUFFICIENT_QUANTITY"

    def __init__(
        self, lot_number: str, requested: float, available: float,
    ) -> None:
        super().__init__(
            message=(
                f"Material lot '{lot_number}' has insufficient quantity: "
                f"requested {requested}, available {available}"
            ),
            details={
                "lot_number": lot_number,
                "requested": requested,
                "available": available,
            },
        )


class MaterialLotNotAvailableException(MESException):
    """Raised when a material lot is not in 'available' status."""

    status_code = 422
    error_code = "LOT_NOT_AVAILABLE"

    def __init__(self, lot_number: str, current_status: str) -> None:
        super().__init__(
            message=(
                f"Material lot '{lot_number}' is not available for consumption "
                f"(current status: '{current_status}')"
            ),
            details={
                "lot_number": lot_number,
                "current_status": current_status,
            },
        )
