"""
AUTH: FastAPI dependencies for authentication and authorization.

Provides:
- get_current_user: Extracts and validates user from JWT in Authorization header
- require_permission: Factory that returns a dependency requiring a specific permission

Usage in routes:
    @router.get("/units")
    async def list_units(user: User = Depends(get_current_user)):
        ...

    @router.post("/units/{id}/move")
    async def move_unit(user: User = Depends(require_permission("wip.unit.move"))):
        ...
"""

from __future__ import annotations

import logging
from typing import Callable
from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.exceptions import ForbiddenException, UnauthorizedException
from mes.framework.db import get_db_session

from .models import User
from .service import AuthService

logger = logging.getLogger("mes.auth")

# FastAPI security scheme — extracts Bearer token from Authorization header
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """
    FastAPI dependency: Extract and validate the current user from the JWT token.

    Raises:
        UnauthorizedException: If no token, expired token, or user not found.
    """
    if credentials is None:
        raise UnauthorizedException(message="Missing authentication token")

    try:
        payload = AuthService.decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException(message="Token has expired")
    except jwt.InvalidTokenError:
        raise UnauthorizedException(message="Invalid authentication token")

    if payload.get("type") != "access":
        raise UnauthorizedException(message="Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException(message="Invalid token payload")

    user = await AuthService.get_user_by_id(session, UUID(user_id))
    if user is None:
        raise UnauthorizedException(message="User not found or inactive")

    return user


def require_permission(required_permission: str) -> Callable:
    """
    Factory function returning a FastAPI dependency that checks
    the current user has the specified permission.

    Usage:
        @router.post("/units/{id}/move")
        async def move_unit(
            user: User = Depends(require_permission("wip.unit.move"))
        ):
            ...
    """

    async def permission_dependency(
        user: User = Depends(get_current_user),
    ) -> User:
        permissions = AuthService.get_user_permissions(user)
        if not AuthService.check_permission(permissions, required_permission):
            logger.warning(
                "Permission denied: user=%s required=%s",
                user.username,
                required_permission,
            )
            raise ForbiddenException(
                message=f"Permission '{required_permission}' required",
                details={"required_permission": required_permission},
            )
        return user

    return permission_dependency
