"""
REST-API: Cursor-based pagination utilities.

Implements cursor-based pagination per ARCHITECTURE.md §6.1.
Cursor is a base64-encoded representation of the last item's sort key.
"""

from __future__ import annotations

import base64
from typing import Any, Sequence
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, asc, desc
from sqlalchemy.ext.asyncio import AsyncSession


class PaginationParams(BaseModel):
    """Query parameters for cursor-based pagination."""

    cursor: str | None = None
    limit: int = 50
    sort: str = "created_at"
    order: str = "desc"  # "asc" | "desc"


def get_pagination_params(
    cursor: str | None = Query(None, description="Pagination cursor from previous response"),
    limit: int = Query(50, ge=1, le=200, description="Number of items to return"),
    sort: str = Query("created_at", description="Field to sort by"),
    order: str = Query("desc", description="Sort order: asc or desc"),
) -> PaginationParams:
    """FastAPI dependency for extracting pagination parameters."""
    return PaginationParams(cursor=cursor, limit=limit, sort=sort, order=order)


def encode_cursor(value: Any) -> str:
    """Encode a value as a pagination cursor (base64)."""
    return base64.urlsafe_b64encode(str(value).encode()).decode()


def decode_cursor(cursor: str) -> str:
    """Decode a pagination cursor back to its original string value."""
    return base64.urlsafe_b64decode(cursor.encode()).decode()


async def paginate_query(
    session: AsyncSession,
    stmt: Select,
    model: Any,
    params: PaginationParams,
) -> tuple[Sequence[Any], str | None, bool]:
    """
    Apply cursor-based pagination to a SQLAlchemy select statement.

    Args:
        session: Async database session.
        stmt: Base SQLAlchemy select statement (before pagination applied).
        model: SQLAlchemy model class (must have the sort column).
        params: Pagination parameters.

    Returns:
        Tuple of (items, next_cursor, has_more).
    """
    sort_column = getattr(model, params.sort, None)
    if sort_column is None:
        sort_column = model.created_at

    # Apply sort direction
    order_func = desc if params.order == "desc" else asc
    stmt = stmt.order_by(order_func(sort_column))

    # Apply cursor filter
    if params.cursor:
        cursor_value = decode_cursor(params.cursor)
        if params.order == "desc":
            stmt = stmt.where(sort_column < cursor_value)
        else:
            stmt = stmt.where(sort_column > cursor_value)

    # Fetch one extra to detect has_more
    stmt = stmt.limit(params.limit + 1)

    result = await session.execute(stmt)
    items = list(result.scalars().all())

    has_more = len(items) > params.limit
    if has_more:
        items = items[: params.limit]

    next_cursor = None
    if has_more and items:
        last_item = items[-1]
        cursor_val = getattr(last_item, params.sort, None)
        if cursor_val is not None:
            next_cursor = encode_cursor(cursor_val)

    return items, next_cursor, has_more
