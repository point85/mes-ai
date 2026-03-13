"""
ERP Adapter: Domain exceptions.
"""

from mes.framework.api.exceptions import MESException


class ERPConnectionError(MESException):
    """Raised when the adapter cannot connect to the ERP system."""

    status_code = 502
    error_code = "ERP_CONNECTION_ERROR"

    def __init__(self, message: str = "Cannot connect to ERP system", **kwargs):
        super().__init__(message=message, **kwargs)


class ERPSyncError(MESException):
    """Raised when an inbound sync operation fails."""

    status_code = 502
    error_code = "ERP_SYNC_ERROR"

    def __init__(self, message: str = "ERP sync failed", **kwargs):
        super().__init__(message=message, **kwargs)


class ERPOutboundError(MESException):
    """Raised when an outbound report to ERP fails after all retries."""

    status_code = 502
    error_code = "ERP_OUTBOUND_ERROR"

    def __init__(self, message: str = "ERP outbound report failed", **kwargs):
        super().__init__(message=message, **kwargs)
