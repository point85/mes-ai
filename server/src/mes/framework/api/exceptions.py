"""
REST-API: Domain exception hierarchy and global exception handlers.

All domain exceptions inherit from MESException and carry a machine-readable
error code for consistent API error responses.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .responses import error_response

logger = logging.getLogger(__name__)


class MESException(Exception):
    """Base exception for all MES domain errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str = "An internal error occurred",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundException(MESException):
    """Raised when a requested resource does not exist."""

    status_code = 404
    error_code = "RESOURCE_NOT_FOUND"

    def __init__(
        self,
        resource: str = "Resource",
        resource_id: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        message = f"{resource} with id '{resource_id}' not found"
        super().__init__(message=message, details=details)


class ConflictException(MESException):
    """Raised on uniqueness constraint violations or state conflicts."""

    status_code = 409
    error_code = "CONFLICT"


class ValidationException(MESException):
    """Raised when input data fails business-rule validation."""

    status_code = 422
    error_code = "VALIDATION_ERROR"


class ForbiddenException(MESException):
    """Raised when the user lacks required permissions."""

    status_code = 403
    error_code = "FORBIDDEN"


class UnauthorizedException(MESException):
    """Raised when authentication fails or is missing."""

    status_code = 401
    error_code = "UNAUTHORIZED"


class ServiceUnavailableException(MESException):
    """Raised when a dependency (plugin, adapter, external service) is not available."""

    status_code = 503
    error_code = "SERVICE_UNAVAILABLE"


def _sanitise_pydantic_errors(errors: list[Any]) -> list[Any]:
    """
    Pydantic v2 error dicts can contain a ``ctx`` field whose values are the
    original exception objects (e.g. ``{'error': ValueError(...)}``).
    These are not JSON-serialisable and will crash JSONResponse.  Convert any
    non-primitive ctx value to its string representation before serialising.
    """
    _primitives = (str, int, float, bool, type(None))
    sanitised = []
    for err in errors:
        err = dict(err)
        if isinstance(err.get("ctx"), dict):
            err["ctx"] = {
                k: v if isinstance(v, _primitives) else str(v)
                for k, v in err["ctx"].items()
            }
        sanitised.append(err)
    return sanitised


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers on the FastAPI app.
    Converts MESException subclasses into standard error envelope responses.
    """

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = _sanitise_pydantic_errors(exc.errors())
        logger.warning("Request validation failed: %s", errors)
        return JSONResponse(
            status_code=422,
            content=error_response(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                details={"errors": errors},
            ),
        )

    @app.exception_handler(MESException)
    async def mes_exception_handler(_request: Request, exc: MESException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                code=exc.error_code,
                message=exc.message,
                details=exc.details,
            ),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content=error_response(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred",
                details={"type": type(exc).__name__, "detail": str(exc)},
            ),
        )
