"""
QUAL-MGMT: Domain exceptions.
"""

from mes.framework.api.exceptions import MESException


class DuplicateTestCodeException(MESException):
    """Raised when a quality test code already exists."""

    status_code = 409
    error_code = "DUPLICATE_TEST_CODE"

    def __init__(self, test_code: str) -> None:
        super().__init__(
            message=f"Quality test with code '{test_code}' already exists",
            details={"test_code": test_code},
        )


class InvalidNCTransitionException(MESException):
    """Raised when a non-conformance status transition is not allowed."""

    status_code = 422
    error_code = "INVALID_NC_TRANSITION"

    def __init__(self, current_status: str, requested_status: str) -> None:
        super().__init__(
            message=(
                f"Cannot transition non-conformance from '{current_status}' "
                f"to '{requested_status}'"
            ),
            details={
                "current_status": current_status,
                "requested_status": requested_status,
            },
        )


class DispositionRequiredException(MESException):
    """Raised when a disposition is required but not provided."""

    status_code = 422
    error_code = "DISPOSITION_REQUIRED"

    def __init__(self) -> None:
        super().__init__(
            message="A disposition is required to resolve this non-conformance",
        )
