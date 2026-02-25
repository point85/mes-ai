"""
DATA-COLLECT: Domain exceptions.
"""

from mes.framework.api.exceptions import MESException


class DuplicateDefinitionCodeException(MESException):
    """Raised when a data definition code already exists."""

    status_code = 409
    error_code = "DUPLICATE_DEFINITION_CODE"

    def __init__(self, code: str) -> None:
        super().__init__(
            message=f"Data definition with code '{code}' already exists",
            details={"definition_code": code},
        )


class InvalidDataValueException(MESException):
    """Raised when a collected value doesn't match the definition's expected data_type."""

    status_code = 422
    error_code = "INVALID_DATA_VALUE"

    def __init__(self, code: str, expected_type: str, detail: str) -> None:
        super().__init__(
            message=(
                f"Invalid value for data definition '{code}' "
                f"(expected {expected_type}): {detail}"
            ),
            details={
                "definition_code": code,
                "expected_type": expected_type,
                "detail": detail,
            },
        )


class ValueOutOfLimitsException(MESException):
    """Raised when a numeric value falls outside the definition's lower/upper limits."""

    status_code = 422
    error_code = "VALUE_OUT_OF_LIMITS"

    def __init__(
        self,
        code: str,
        value: float,
        lower_limit: float | None,
        upper_limit: float | None,
    ) -> None:
        limit_desc = ""
        if lower_limit is not None and upper_limit is not None:
            limit_desc = f"[{lower_limit}, {upper_limit}]"
        elif lower_limit is not None:
            limit_desc = f">= {lower_limit}"
        elif upper_limit is not None:
            limit_desc = f"<= {upper_limit}"

        super().__init__(
            message=(
                f"Value {value} for '{code}' is out of limits {limit_desc}"
            ),
            details={
                "definition_code": code,
                "value": value,
                "lower_limit": lower_limit,
                "upper_limit": upper_limit,
            },
        )


class MissingRequiredDataException(MESException):
    """Raised when required data points are missing at step completion."""

    status_code = 422
    error_code = "MISSING_REQUIRED_DATA"

    def __init__(self, missing_codes: list[str]) -> None:
        super().__init__(
            message=(
                f"Required data points not collected: {', '.join(missing_codes)}"
            ),
            details={"missing_codes": missing_codes},
        )


class InvalidEnumValueException(MESException):
    """Raised when a collected enum value is not in the allowed set."""

    status_code = 422
    error_code = "INVALID_ENUM_VALUE"

    def __init__(self, code: str, value: str, allowed: list[str]) -> None:
        super().__init__(
            message=(
                f"Value '{value}' for '{code}' is not in allowed values: "
                f"{', '.join(allowed)}"
            ),
            details={
                "definition_code": code,
                "value": value,
                "allowed_values": allowed,
            },
        )
