"""
Test Equipment Adapter: Domain exceptions.
"""

from mes.framework.api.exceptions import MESException


class TestEquipmentConnectionError(MESException):
    """Raised when the adapter cannot connect to the test equipment."""

    status_code = 502
    error_code = "TEST_EQUIPMENT_CONNECTION_ERROR"

    def __init__(self, message: str = "Cannot connect to test equipment", **kwargs):
        super().__init__(message=message, **kwargs)


class ResultParsingError(MESException):
    """Raised when a test result file cannot be parsed."""

    status_code = 422
    error_code = "RESULT_PARSING_ERROR"

    def __init__(self, message: str = "Failed to parse test result", **kwargs):
        super().__init__(message=message, **kwargs)
