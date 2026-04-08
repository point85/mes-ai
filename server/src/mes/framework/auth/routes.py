"""
AUTH: REST API routes for authentication and authorization.

Endpoints per ARCHITECTURE.md §6.3 and §11:
- Local login (dev mode)
- Token refresh
- Current user info
- User CRUD (admin)
- Role and permission management (admin)
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mes.config import settings
from mes.framework.api.exceptions import (
    ConflictException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)
from mes.framework.api.responses import success_response
from mes.framework.db import get_db_session

from .dependencies import get_current_user, require_permission
from .models import Permission, Role, User, UserRole
from .schemas import (
    LocalLoginRequest,
    PermissionAssignment,
    RoleCreate,
    RoleRead,
    TokenResponse,
    UserCreate,
    UserRead,
)
from .service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


# --- Local login (dev/fallback mode) ---


@router.post("/local/login", response_model=TokenResponse)
async def local_login(
    body: LocalLoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """
    Authenticate with username/password (local mode only).
    Returns an MES JWT access token and refresh token.
    """
    if settings.AUTH_MODE != "local":
        raise ValidationException(
            message="Local login is disabled. Use OIDC authentication.",
            details={"auth_mode": settings.AUTH_MODE},
        )

    user = await AuthService.get_user_by_username(session, body.username)
    if user is None or user.hashed_password is None:
        raise UnauthorizedException(message="Invalid username or password")

    if not AuthService.verify_password(body.password, user.hashed_password):
        raise UnauthorizedException(message="Invalid username or password")

    # Update last login
    now = datetime.now(timezone.utc)
    user.last_login = now
    user.last_login_utc = now
    await session.commit()

    roles = AuthService.get_user_roles(user)
    permissions = AuthService.get_user_permissions(user)

    access_token = AuthService.create_access_token(
        user_id=str(user.id),
        username=user.username,
        roles=roles,
        permissions=permissions,
    )
    refresh_token = AuthService.create_refresh_token(user_id=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# --- Current user ---


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile and roles."""
    roles = AuthService.get_user_roles(user)
    return success_response(
        UserRead(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            idp_issuer=user.idp_issuer,
            last_login=user.last_login,
            is_active=user.is_active,
            created_at=user.created_at,
            roles=roles,
        ).model_dump()
    )


# --- User admin (admin only) ---


@router.post("/users", status_code=201)
async def create_local_user(
    body: UserCreate,
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_permission("auth.user.create")),
):
    """Create a new local user (admin only, local auth mode)."""
    if settings.AUTH_MODE != "local":
        raise ValidationException(message="Cannot create local users when auth_mode is not 'local'")

    existing = await AuthService.get_user_by_username(session, body.username)
    if existing is not None:
        raise ConflictException(message=f"User '{body.username}' already exists")

    user = User(
        username=body.username,
        email=body.email,
        full_name=body.full_name,
        hashed_password=AuthService.hash_password(body.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    return success_response(
        UserRead(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            created_at=user.created_at,
            roles=[],
        ).model_dump()
    )


# --- Role management (admin only) ---


@router.get("/roles")
async def list_roles(
    session: AsyncSession = Depends(get_db_session),
    _user: User = Depends(require_permission("auth.role.read")),
):
    """List all roles."""
    result = await session.execute(select(Role).where(Role.is_active.is_(True)))
    roles = result.scalars().all()
    role_data = []
    for role in roles:
        perms = await session.execute(
            select(Permission.permission).where(Permission.role_id == role.id)
        )
        role_data.append(
            RoleRead(
                id=role.id,
                name=role.name,
                description=role.description,
                is_system=role.is_system,
                permissions=list(perms.scalars().all()),
            ).model_dump()
        )
    return success_response(role_data)


@router.post("/roles", status_code=201)
async def create_role(
    body: RoleCreate,
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_permission("auth.role.create")),
):
    """Create a new custom role."""
    existing = await session.execute(select(Role).where(Role.name == body.name))
    if existing.scalar_one_or_none() is not None:
        raise ConflictException(message=f"Role '{body.name}' already exists")

    role = Role(name=body.name, description=body.description, is_system=False)
    session.add(role)
    await session.commit()
    await session.refresh(role)

    return success_response(
        RoleRead(
            id=role.id,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            permissions=[],
        ).model_dump()
    )


@router.post("/roles/{role_id}/permissions")
async def update_role_permissions(
    role_id: UUID,
    body: PermissionAssignment,
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_permission("auth.role.update")),
):
    """Add or remove permissions from a role."""
    role = await session.get(Role, role_id)
    if role is None or not role.is_active:
        raise NotFoundException(resource="Role", resource_id=str(role_id))

    # Add permissions
    for perm_str in body.add:
        existing = await session.execute(
            select(Permission).where(
                Permission.role_id == role_id,
                Permission.permission == perm_str,
            )
        )
        if existing.scalar_one_or_none() is None:
            session.add(Permission(role_id=role_id, permission=perm_str))

    # Remove permissions
    for perm_str in body.remove:
        result = await session.execute(
            select(Permission).where(
                Permission.role_id == role_id,
                Permission.permission == perm_str,
            )
        )
        perm = result.scalar_one_or_none()
        if perm is not None:
            await session.delete(perm)

    await session.commit()

    # Return updated permissions
    perms = await session.execute(
        select(Permission.permission).where(Permission.role_id == role_id)
    )
    return success_response({"role_id": str(role_id), "permissions": list(perms.scalars().all())})


# --- User-role assignment (admin only) ---


@router.post("/users/{user_id}/roles/{role_id}", status_code=201)
async def assign_role_to_user(
    user_id: UUID,
    role_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_permission("auth.user.update")),
):
    """Assign a role to a user."""
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise NotFoundException(resource="User", resource_id=str(user_id))

    role = await session.get(Role, role_id)
    if role is None or not role.is_active:
        raise NotFoundException(resource="Role", resource_id=str(role_id))

    existing = await session.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictException(message="User already has this role")

    session.add(UserRole(user_id=user_id, role_id=role_id))
    await session.commit()

    return success_response({"user_id": str(user_id), "role_id": str(role_id)})


@router.delete("/users/{user_id}/roles/{role_id}")
async def remove_role_from_user(
    user_id: UUID,
    role_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_permission("auth.user.update")),
):
    """Remove a role from a user."""
    result = await session.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    )
    user_role = result.scalar_one_or_none()
    if user_role is None:
        raise NotFoundException(resource="UserRole", resource_id=f"{user_id}/{role_id}")

    await session.delete(user_role)
    await session.commit()

    return success_response({"removed": True})
