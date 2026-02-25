"""
UOM: Domain exceptions.
"""

from mes.framework.api.exceptions import MESException


class DuplicateSymbolException(MESException):
    """Raised when a unit symbol already exists."""

    status_code = 409
    error_code = "DUPLICATE_SYMBOL"

    def __init__(self, symbol: str) -> None:
        super().__init__(
            message=f"Unit with symbol '{symbol}' already exists",
            details={"symbol": symbol},
        )


class IncompatibleUoMTypeException(MESException):
    """Raised when attempting to convert between units of different types."""

    status_code = 422
    error_code = "INCOMPATIBLE_UOM_TYPE"

    def __init__(self, from_symbol: str, from_type: str, to_symbol: str, to_type: str) -> None:
        super().__init__(
            message=(
                f"Cannot convert from '{from_symbol}' ({from_type}) "
                f"to '{to_symbol}' ({to_type}): types must match"
            ),
            details={
                "from_symbol": from_symbol,
                "from_type": from_type,
                "to_symbol": to_symbol,
                "to_type": to_type,
            },
        )


class BuiltinUoMException(MESException):
    """Raised when attempting to delete or modify a protected built-in unit."""

    status_code = 403
    error_code = "BUILTIN_UOM_PROTECTED"

    def __init__(self, symbol: str) -> None:
        super().__init__(
            message=f"Built-in unit '{symbol}' cannot be deleted",
            details={"symbol": symbol},
        )
