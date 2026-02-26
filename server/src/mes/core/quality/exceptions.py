"""
QUAL-MGMT: Domain exceptions.
"""

from mes.framework.api.exceptions import MESException


class DuplicateTestCodeException(MESException):
    """Raised when a quality test code already exists."""

    status_code = 409
    error_code = "DUPLICATE_TEST_CODE"

    def __init__(self, code: str) -> None:
        super().__init__(
            message=f"Quality test with code '{code}' already exists",
            details={"test_code": code},
        )


class InvalidNCTransitionException(MESException):
    """Raised when a non-conformance status transition is not allowed."""

    status_code = 422
    error_code = "INVALID_NC_TRANSITION"

    def __init__(self, current: str, requested: str) -> None:
        super().__init__(
            message=(
                f"Cannot transition non-conformance from '{current}' "
                f"to '{requested}'"
            ),
            details={
                "current_status": current,
                "requested_status": requested,
            },
        )


class DispositionRequiredException(MESException):
    """Raised when resolving a non-conformance without setting disposition."""

    status_code = 422
    error_code = "DISPOSITION_REQUIRED"

    def __init__(self) -> None:
        super().__init__(
            message="Disposition is required when resolving a non-conformance",
            details={},
        )
