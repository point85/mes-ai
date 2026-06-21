"""
PROD-DEF: Domain exceptions.
"""

from mes.framework.api.exceptions import MESException


class DuplicateProductException(MESException):
    """Raised when a product with the same code+version already exists."""

    status_code = 409
    error_code = "DUPLICATE_PRODUCT"

    def __init__(self, code: str, version: str) -> None:
        super().__init__(
            message=f"Product with code '{code}' version '{version}' already exists",
            details={"code": code, "version": version},
        )


class DuplicateDispositionCodeException(MESException):
    """Raised when a disposition code already exists."""

    status_code = 409
    error_code = "DUPLICATE_DISPOSITION_CODE"

    def __init__(self, code: str) -> None:
        super().__init__(
            message=f"Disposition with code '{code}' already exists",
            details={"code": code},
        )
