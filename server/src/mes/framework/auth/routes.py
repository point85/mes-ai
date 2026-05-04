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

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload
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
    RefreshTokenRequest,
    RoleCreate,
    RoleRead,
    TokenResponse,
    UserCreate,
    UserRead,
    UserUpdate,
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
    user.last_login_utc = now.replace(tzinfo=None)
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


# --- Token refresh ---


@router.post("/local/refresh", response_model=TokenResponse)
async def refresh_access_token(
    body: RefreshTokenRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """
    Exchange a valid refresh token for a new access token + refresh token pair.
    The old refresh token is not revoked (stateless); clients should store the new one.
    """
    import jwt

    try:
        payload = AuthService.decode_token(body.refresh_token)
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException(message="Refresh token has expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise UnauthorizedException(message="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise UnauthorizedException(message="Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException(message="Invalid token payload")

    user = await AuthService.get_user_by_id(session, UUID(user_id))
    if user is None:
        raise UnauthorizedException(message="User not found or inactive")

    roles = AuthService.get_user_roles(user)
    permissions = AuthService.get_user_permissions(user)

    return TokenResponse(
        access_token=AuthService.create_access_token(
            user_id=str(user.id),
            username=user.username,
            roles=roles,
            permissions=permissions,
        ),
        refresh_token=AuthService.create_refresh_token(user_id=str(user.id)),
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


@router.get("/users")
async def list_users(
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_permission("auth.user.read")),
):
    """List all active users with their roles (admin only)."""
    result = await session.execute(
        select(User)
        .where(User.is_active.is_(True))
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
        .order_by(User.username)
    )
    users = result.scalars().all()
    return success_response([
        UserRead(
            id=u.id,
            username=u.username,
            email=u.email,
            full_name=u.full_name,
            idp_issuer=u.idp_issuer,
            last_login=u.last_login,
            is_active=u.is_active,
            created_at=u.created_at,
            roles=[ur.role.name for ur in u.user_roles if ur.role.is_active],
        ).model_dump()
        for u in users
    ])


@router.get("/users/{user_id}")
async def get_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_permission("auth.user.read")),
):
    """Get a single user by ID (admin only)."""
    user = await AuthService.get_user_by_id(session, user_id)
    if user is None:
        raise NotFoundException(resource="User", resource_id=str(user_id))
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
            roles=AuthService.get_user_roles(user),
        ).model_dump()
    )


@router.put("/users/{user_id}")
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_permission("auth.user.update")),
):
    """Update a user's profile and optionally reset password (admin only)."""
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise NotFoundException(resource="User", resource_id=str(user_id))

    if body.email is not None:
        user.email = body.email
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password is not None:
        user.hashed_password = AuthService.hash_password(body.password)

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


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(require_permission("auth.user.delete")),
):
    """Soft-delete a user (admin only). Cannot delete your own account."""
    if user_id == current_user.id:
        raise ValidationException(message="Cannot delete your own account")

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise NotFoundException(resource="User", resource_id=str(user_id))

    user.is_active = False
    await session.commit()
    return Response(status_code=204)


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


@router.delete("/roles/{role_id}", status_code=204)
async def delete_role(
    role_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    _admin: User = Depends(require_permission("auth.role.delete")),
):
    """Soft-delete a custom role (admin only). Cannot delete system roles."""
    role = await session.get(Role, role_id)
    if role is None or not role.is_active:
        raise NotFoundException(resource="Role", resource_id=str(role_id))
    if role.is_system:
        raise ValidationException(message="Cannot delete built-in system roles")

    role.is_active = False
    await session.commit()
    return Response(status_code=204)


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
