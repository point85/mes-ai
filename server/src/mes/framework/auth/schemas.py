"""
AUTH: Pydantic schemas for authentication and authorization.

These schemas define the API contract for auth endpoints:
- User CRUD
- Role and permission management
- Token responses
- Local login requests
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# --- User schemas ---


class UserCreate(BaseModel):
    """Schema for creating a local user (dev/fallback mode only)."""

    username: str = Field(..., min_length=1, max_length=255)
    email: str | None = None
    full_name: str | None = None
    password: str = Field(..., min_length=8, max_length=128)


class UserRead(BaseModel):
    """Schema for returning user data."""

    id: UUID
    username: str
    email: str | None = None
    full_name: str | None = None
    idp_issuer: str | None = None
    last_login: datetime | None = None
    is_active: bool
    created_at: datetime
    roles: list[str] = Field(default_factory=list, description="List of role names")

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Schema for updating user fields."""

    email: str | None = None
    full_name: str | None = None
    is_active: bool | None = None


# --- Role schemas ---


class RoleCreate(BaseModel):
    """Schema for creating a new role."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class RoleRead(BaseModel):
    """Schema for returning role data."""

    id: UUID
    name: str
    description: str | None = None
    is_system: bool
    permissions: list[str] = Field(default_factory=list, description="List of permission strings")

    model_config = {"from_attributes": True}


class RoleUpdate(BaseModel):
    """Schema for updating a role."""

    description: str | None = None


class PermissionAssignment(BaseModel):
    """Schema for adding/removing permissions from a role."""

    add: list[str] = Field(default_factory=list, description="Permissions to add")
    remove: list[str] = Field(default_factory=list, description="Permissions to remove")


# --- Permission schemas ---


class PermissionRead(BaseModel):
    """Schema for returning a permission entry."""

    id: UUID
    role_id: UUID
    permission: str

    model_config = {"from_attributes": True}


# --- Token schemas ---


class TokenResponse(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token lifetime in seconds")


class LocalLoginRequest(BaseModel):
    """Schema for local authentication login (dev/fallback mode)."""

    username: str
    password: str


# --- IdP Group Mapping schemas ---


class IdPGroupMappingCreate(BaseModel):
    """Schema for creating a group-to-role mapping."""

    idp_group: str = Field(..., min_length=1, max_length=255)
    role_id: UUID


class IdPGroupMappingRead(BaseModel):
    """Schema for returning a group mapping."""

    id: UUID
    idp_group: str
    role_id: UUID

    model_config = {"from_attributes": True}
