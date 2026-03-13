"""
Equipment Adapter: Domain exceptions.
"""

from mes.framework.api.exceptions import MESException


class EquipmentConnectionError(MESException):
    """Raised when the adapter cannot connect to the equipment."""

    status_code = 502
    error_code = "EQUIPMENT_CONNECTION_ERROR"

    def __init__(self, message: str = "Cannot connect to equipment", **kwargs):
        super().__init__(message=message, **kwargs)


class TagNotFoundError(MESException):
    """Raised when a requested tag does not exist on the equipment."""

    status_code = 404
    error_code = "TAG_NOT_FOUND"

    def __init__(self, tag_name: str = "", **kwargs):
        message = f"Tag '{tag_name}' not found on equipment"
        super().__init__(message=message, **kwargs)


class CommunicationTimeoutError(MESException):
    """Raised when equipment communication times out."""

    status_code = 504
    error_code = "EQUIPMENT_TIMEOUT"

    def __init__(self, message: str = "Equipment communication timed out", **kwargs):
        super().__init__(message=message, **kwargs)
