"""
AUTH: Database models for authentication and authorization.

Implements RBAC with:
- User (OIDC JIT-provisioned or local dev accounts)
- Role (admin, engineer, operator, viewer + custom)
- Permission (module.resource.action pattern with wildcard support)
- UserRole (M:N join)
- IdPGroupMapping (maps IdP groups to MES roles)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from mes.framework.db import BaseModel


class User(BaseModel):
    """
    MES user account. Created via OIDC JIT provisioning or local registration.
    The MES never stores IdP passwords — only local-mode fallback uses hashed_password.
    """

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # OIDC identity binding
    idp_subject: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True,
        comment="OIDC 'sub' claim — unique user ID at the IdP",
    )
    idp_issuer: Mapped[str | None] = mapped_column(
        String(512), nullable=True,
        comment="OIDC 'iss' claim — identifies which IdP issued the token",
    )

    # Local auth fallback (dev/air-gapped only)
    hashed_password: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="bcrypt hash; only populated when auth_mode=local",
    )

    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username}>"


class Role(BaseModel):
    """
    Authorization role. Default roles: admin, engineer, operator, viewer.
    Custom roles can be created via the admin API.
    """

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
        comment="True for built-in roles that cannot be deleted",
    )

    # Relationships
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan"
    )
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", back_populates="role", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Role id={self.id} name={self.name}>"


class Permission(BaseModel):
    """
    Permission entry assigned to a role.
    Follows module.resource.action pattern (e.g. 'wip.unit.move').
    Wildcards supported: '*', 'wip.*', '*.read'.
    """

    __tablename__ = "permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False, index=True,
    )
    permission: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True,
        comment="Dot-notation permission string (e.g. 'wip.unit.move', 'quality.*')",
    )

    # Relationships
    role: Mapped["Role"] = relationship("Role", back_populates="permissions")

    def __repr__(self) -> str:
        return f"<Permission role_id={self.role_id} permission={self.permission}>"


class UserRole(BaseModel):
    """Join table between User and Role (M:N)."""

    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False, index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="user_roles")
    role: Mapped["Role"] = relationship("Role", back_populates="user_roles")

    def __repr__(self) -> str:
        return f"<UserRole user_id={self.user_id} role_id={self.role_id}>"


class IdPGroupMapping(BaseModel):
    """
    Maps an IdP group name to a MES role.
    Used during OIDC JIT provisioning to auto-assign roles based on IdP group claims.
    """

    __tablename__ = "idp_group_mappings"

    idp_group: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True,
        comment="Group name as it appears in the IdP 'groups' claim",
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False, index=True,
    )

    # Relationships
    role: Mapped["Role"] = relationship("Role")

    def __repr__(self) -> str:
        return f"<IdPGroupMapping idp_group={self.idp_group} role_id={self.role_id}>"
