"""
Unit tests for REST-API framework module.

Tests cover:
- Response envelope construction (success, list, error)
- Exception hierarchy and HTTP status codes
- Pagination parameter extraction and cursor encoding
"""

from __future__ import annotations

import pytest

from mes.framework.api.exceptions import (
    ConflictException,
    ForbiddenException,
    MESException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)
from mes.framework.api.pagination import decode_cursor, encode_cursor
from mes.framework.api.responses import (
    ErrorResponse,
    ListResponse,
    PaginationMeta,
    SuccessResponse,
    error_response,
    list_response,
    success_response,
)


# --- Response envelope tests ---


class TestResponses:
    def test_success_response(self):
        result = success_response({"id": "abc", "name": "Widget"})
        assert result["data"]["id"] == "abc"
        assert "timestamp" in result["meta"]

    def test_list_response(self):
        items = [{"id": "1"}, {"id": "2"}]
        result = list_response(items, cursor="abc123", limit=50, has_more=True)
        assert len(result["data"]) == 2
        assert result["meta"]["pagination"]["cursor"] == "abc123"
        assert result["meta"]["pagination"]["has_more"] is True

    def test_error_response(self):
        result = error_response(
            code="RESOURCE_NOT_FOUND",
            message="Unit not found",
            details={"id": "xyz"},
        )
        assert result["error"]["code"] == "RESOURCE_NOT_FOUND"
        assert result["error"]["message"] == "Unit not found"
        assert result["error"]["details"]["id"] == "xyz"

    def test_success_response_model(self):
        resp = SuccessResponse[dict](data={"key": "value"})
        assert resp.data == {"key": "value"}
        assert resp.meta.timestamp is not None

    def test_list_response_model(self):
        resp = ListResponse[dict](data=[{"a": 1}, {"b": 2}])
        assert len(resp.data) == 2

    def test_error_response_model(self):
        from mes.framework.api.responses import ErrorDetail

        resp = ErrorResponse(error=ErrorDetail(code="TEST", message="test message"))
        assert resp.error.code == "TEST"


# --- Exception tests ---


class TestExceptions:
    def test_base_exception(self):
        exc = MESException(message="Something went wrong")
        assert exc.status_code == 500
        assert exc.error_code == "INTERNAL_ERROR"
        assert str(exc) == "Something went wrong"

    def test_not_found(self):
        exc = NotFoundException(resource="Unit", resource_id="abc-123")
        assert exc.status_code == 404
        assert exc.error_code == "RESOURCE_NOT_FOUND"
        assert "abc-123" in exc.message

    def test_conflict(self):
        exc = ConflictException(message="Duplicate entry")
        assert exc.status_code == 409

    def test_validation(self):
        exc = ValidationException(message="Invalid quantity")
        assert exc.status_code == 422

    def test_forbidden(self):
        exc = ForbiddenException(message="Access denied")
        assert exc.status_code == 403

    def test_unauthorized(self):
        exc = UnauthorizedException(message="No token")
        assert exc.status_code == 401

    def test_exception_with_details(self):
        exc = NotFoundException(
            resource="Unit",
            resource_id="abc",
            details={"searched_field": "serial_number"},
        )
        assert exc.details["searched_field"] == "serial_number"


# --- Pagination tests ---


class TestPagination:
    def test_cursor_encode_decode(self):
        original = "2026-02-24T10:00:00+00:00"
        encoded = encode_cursor(original)
        assert isinstance(encoded, str)
        decoded = decode_cursor(encoded)
        assert decoded == original

    def test_cursor_encode_uuid(self):
        import uuid

        uid = str(uuid.uuid4())
        encoded = encode_cursor(uid)
        decoded = decode_cursor(encoded)
        assert decoded == uid

    def test_pagination_meta(self):
        meta = PaginationMeta(cursor="abc", limit=25, has_more=True)
        assert meta.cursor == "abc"
        assert meta.limit == 25
        assert meta.has_more is True
