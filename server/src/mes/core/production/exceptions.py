"""
PROD-ORDER: Domain exceptions.
"""

from mes.framework.api.exceptions import MESException


class DuplicateOrderNumberException(MESException):
    """Raised when an order number already exists."""

    status_code = 409
    error_code = "DUPLICATE_ORDER_NUMBER"

    def __init__(self, order_number: str) -> None:
        super().__init__(
            message=f"Production order with number '{order_number}' already exists",
            details={"order_number": order_number},
        )


class InvalidOrderTransitionException(MESException):
    """Raised when an order status transition is not allowed."""

    status_code = 422
    error_code = "INVALID_ORDER_TRANSITION"

    def __init__(self, order_number: str, current: str, requested: str) -> None:
        super().__init__(
            message=(
                f"Cannot transition order '{order_number}' "
                f"from '{current}' to '{requested}'"
            ),
            details={
                "order_number": order_number,
                "current_status": current,
                "requested_status": requested,
            },
        )


class OrderNotReleasedException(MESException):
    """Raised when an operation requires the order to be released or in-progress."""

    status_code = 422
    error_code = "ORDER_NOT_RELEASED"

    def __init__(self, order_number: str, current_status: str) -> None:
        super().__init__(
            message=(
                f"Order '{order_number}' must be 'released' or 'in_progress' "
                f"but is '{current_status}'"
            ),
            details={
                "order_number": order_number,
                "current_status": current_status,
            },
        )
