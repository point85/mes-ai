"""
REST-API: Standard response envelope schemas.

All API responses are wrapped in a consistent envelope per ARCHITECTURE.md §6.2:
- Success single: {"data": {...}, "meta": {"timestamp": ...}}
- Success list:   {"data": [...], "meta": {"timestamp": ..., "pagination": {...}}}
- Error:          {"error": {"code": ..., "message": ..., "details": ...}, "meta": {"timestamp": ...}}
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Cursor-based pagination metadata."""

    cursor: str | None = Field(None, description="Cursor for the next page")
    limit: int = Field(50, description="Page size")
    has_more: bool = Field(False, description="Whether more results exist beyond this page")


class ResponseMeta(BaseModel):
    """Metadata included in every response."""

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the response",
    )
    pagination: PaginationMeta | None = None


class SuccessResponse(BaseModel, Generic[T]):
    """Envelope for a single-resource success response."""

    data: T
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


class ListResponse(BaseModel, Generic[T]):
    """Envelope for a list success response with pagination."""

    data: list[T]
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


class ErrorDetail(BaseModel):
    """Structured error information."""

    code: str = Field(..., description="Machine-readable error code (e.g. RESOURCE_NOT_FOUND)")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(None, description="Additional error context")


class ErrorResponse(BaseModel):
    """Envelope for error responses."""

    error: ErrorDetail
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


# --- Helper functions for constructing responses ---


def success_response(data: Any) -> dict[str, Any]:
    """Build a single-resource success response dict."""
    return {
        "data": data,
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat()},
    }


def list_response(
    data: list[Any],
    cursor: str | None = None,
    limit: int = 50,
    has_more: bool = False,
) -> dict[str, Any]:
    """Build a list success response dict with pagination metadata."""
    return {
        "data": data,
        "meta": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pagination": {
                "cursor": cursor,
                "limit": limit,
                "has_more": has_more,
            },
        },
    }


def error_response(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an error response dict."""
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
        "meta": {"timestamp": datetime.now(timezone.utc).isoformat()},
    }
