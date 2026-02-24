"""
PHYS-MODEL: Domain exceptions.
"""

from mes.framework.api.exceptions import MESException


class DuplicateCodeException(MESException):
    """Raised when a physical model entity code already exists."""

    status_code = 409
    error_code = "DUPLICATE_CODE"

    def __init__(self, entity: str, code: str) -> None:
        super().__init__(
            message=f"{entity} with code '{code}' already exists",
            details={"entity": entity, "code": code},
        )
