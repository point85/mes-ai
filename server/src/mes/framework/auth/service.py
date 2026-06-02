"""
AUTH: Core authentication and authorization service.

Handles:
- Local login (dev/fallback mode) with bcrypt password hashing
- JWT token creation and validation
- Permission checking with wildcard matching
- User lookup and JIT provisioning support
- Default role/permission seeding
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mes.config import settings

from .models import Permission, Role, User, UserRole

# Serialises concurrent seed_default_roles calls within the same process.
# The second caller waits for the first to commit, then finds all roles
# already present and skips every insert — no database-specific behaviour needed.
_seed_roles_lock = asyncio.Lock()

logger = logging.getLogger("mes.auth")

# Default roles and their permissions per ARCHITECTURE.md §11.3.3
DEFAULT_ROLES: dict[str, dict[str, Any]] = {
    "admin": {
        "description": "System administrator with full access",
        "permissions": ["*"],
    },
    "engineer": {
        "description": "Process/manufacturing engineer",
        "permissions": [
            "physical_model.*",
            "product_def.*",
            "production.order.*",
            "dispatch.*",
            "material.*",
            "data_collect.*",
            "performance.*",
            "wip.read",
            "plugin.read",
        ],
    },
    "operator": {
        "description": "Shop floor operator",
        "permissions": [
            "wip.*",
            "dispatch.read",
            "dispatch.execute",
            "data_collect.read",
            "data_collect.record",
            "material.read",
            "material.consume",
            "performance.read",
            "physical_model.read",
            "product_def.read",
            "production.order.read",
        ],
    },
    "viewer": {
        "description": "Read-only access for management and auditors",
        "permissions": ["*.read"],
    },
}


class AuthService:
    """Service class for authentication and authorization operations."""

    # --- Password hashing (local mode only) ---

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using PBKDF2-SHA256.
        Used only in local auth mode (dev/air-gapped).
        """
        salt = secrets.token_hex(16)
        pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
        return f"{salt}${pw_hash.hex()}"

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its PBKDF2-SHA256 hash."""
        try:
            salt, pw_hash = hashed.split("$")
            expected = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
            return hmac.compare_digest(expected.hex(), pw_hash)
        except (ValueError, AttributeError):
            return False

    # --- JWT token management ---

    @staticmethod
    def create_access_token(
        user_id: str,
        username: str,
        roles: list[str],
        permissions: list[str],
    ) -> str:
        """
        Create a short-lived JWT access token.

        The token carries user identity, roles, and flattened permission list
        so that permission checks do not require a database round-trip.
        """
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        payload = {
            "sub": user_id,
            "username": username,
            "roles": roles,
            "permissions": permissions,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access",
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """Create a long-lived refresh token."""
        expire = datetime.now(timezone.utc) + timedelta(days=7)
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh",
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> dict[str, Any]:
        """
        Decode and validate a JWT token.

        Raises:
            jwt.InvalidTokenError: If token is expired, malformed, or signature invalid.
        """
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

    # --- Permission matching ---

    @staticmethod
    def check_permission(user_permissions: list[str], required: str) -> bool:
        """
        Check if any user permission grants the required permission.

        Supports wildcard matching per ARCHITECTURE.md §11.3.1:
        - '*' grants all permissions
        - 'wip.*' grants all wip.* permissions
        - '*.read' grants all *.read permissions
        """
        for perm in user_permissions:
            if perm == "*":
                return True
            if perm == required:
                return True
            # Wildcard matching
            if "*" in perm:
                perm_parts = perm.split(".")
                req_parts = required.split(".")
                if _wildcard_match(perm_parts, req_parts):
                    return True
        return False

    # --- Database operations ---

    @staticmethod
    async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
        """Fetch a user by username with roles and permissions eagerly loaded."""
        stmt = (
            select(User)
            .where(User.username == username, User.is_active.is_(True))
            .options(
                selectinload(User.user_roles)
                .selectinload(UserRole.role)
                .selectinload(Role.permissions)
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
        """Fetch a user by ID with roles and permissions eagerly loaded."""
        stmt = (
            select(User)
            .where(User.id == user_id, User.is_active.is_(True))
            .options(
                selectinload(User.user_roles)
                .selectinload(UserRole.role)
                .selectinload(Role.permissions)
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def get_user_roles(user: User) -> list[str]:
        """Extract role names from a user's loaded relationships."""
        return [ur.role.name for ur in user.user_roles if ur.role.is_active]

    @staticmethod
    def get_user_permissions(user: User) -> list[str]:
        """Extract flattened permission strings from a user's roles."""
        permissions: set[str] = set()
        for ur in user.user_roles:
            if ur.role.is_active:
                for perm in ur.role.permissions:
                    if perm.is_active:
                        permissions.add(perm.permission)
        return sorted(permissions)

    @staticmethod
    async def seed_admin_user(session: AsyncSession) -> None:
        """
        Create a default admin/admin user if no users exist.
        Called during application startup in local auth mode.
        Safe to run every boot — no-ops if users already exist.
        """
        count_result = await session.execute(select(func.count(User.id)))
        count = count_result.scalar_one()
        if count > 0:
            return

        admin_user = User(
            username="admin",
            email="admin@mes.local",
            full_name="MES Administrator",
            hashed_password=AuthService.hash_password("admin"),
        )
        session.add(admin_user)
        await session.flush()  # get admin_user.id

        admin_role_result = await session.execute(select(Role).where(Role.name == "admin"))
        admin_role = admin_role_result.scalar_one_or_none()
        if admin_role is not None:
            session.add(UserRole(user_id=admin_user.id, role_id=admin_role.id))

        await session.commit()
        logger.info("Seeded default admin user (username=admin, password=admin)")

    @staticmethod
    async def seed_demo_users(session: AsyncSession) -> None:
        """
        Create representative demo users for the CPG and SMT/Electronics lines.
        One user per role per line, plus a cross-site viewer.
        Safe to run multiple times — skips users that already exist by username.

        Credentials (demo only, not for production):
          cpg_engineer   / engineer1  (engineer role)
          cpg_operator1  / operator1  (operator role)
          cpg_operator2  / operator1  (operator role)
          smt_engineer   / engineer1  (engineer role)
          smt_operator1  / operator1  (operator role)
          smt_operator2  / operator1  (operator role)
          plant_manager  / viewer1    (viewer role)
        """
        demo_users = [
            # CPG line
            {
                "username": "cpg_engineer",
                "email": "cpg.engineer@mes.local",
                "full_name": "Emma García",
                "password": "engineer1",
                "roles": ["engineer"],
            },
            {
                "username": "cpg_operator1",
                "email": "cpg.operator1@mes.local",
                "full_name": "Tom Williams",
                "password": "operator1",
                "roles": ["operator"],
            },
            {
                "username": "cpg_operator2",
                "email": "cpg.operator2@mes.local",
                "full_name": "Sara Kim",
                "password": "operator1",
                "roles": ["operator"],
            },
            # SMT / Electronics line
            {
                "username": "smt_engineer",
                "email": "smt.engineer@mes.local",
                "full_name": "David Chen",
                "password": "engineer1",
                "roles": ["engineer"],
            },
            {
                "username": "smt_operator1",
                "email": "smt.operator1@mes.local",
                "full_name": "Maria Rossi",
                "password": "operator1",
                "roles": ["operator"],
            },
            {
                "username": "smt_operator2",
                "email": "smt.operator2@mes.local",
                "full_name": "James Park",
                "password": "operator1",
                "roles": ["operator"],
            },
            # Cross-site management
            {
                "username": "plant_manager",
                "email": "plant.manager@mes.local",
                "full_name": "Alex Johnson",
                "password": "viewer1",
                "roles": ["viewer"],
            },
        ]

        # Load all roles into a name→Role map once
        roles_result = await session.execute(select(Role))
        role_map = {r.name: r for r in roles_result.scalars().all()}

        for spec in demo_users:
            existing = await session.execute(
                select(User).where(User.username == spec["username"])
            )
            if existing.scalar_one_or_none() is not None:
                continue  # idempotent

            user = User(
                username=spec["username"],
                email=spec["email"],
                full_name=spec["full_name"],
                hashed_password=AuthService.hash_password(spec["password"]),
            )
            session.add(user)
            await session.flush()

            for role_name in spec["roles"]:
                role = role_map.get(role_name)
                if role is not None:
                    session.add(UserRole(user_id=user.id, role_id=role.id))

            logger.info("Seeded demo user: %s (%s)", spec["username"], ", ".join(spec["roles"]))

        await session.commit()

    @staticmethod
    async def seed_default_roles(session: AsyncSession) -> None:
        """
        Create default roles and permissions if they don't exist.
        Called during application startup.
        Idempotent and race-safe: the module-level asyncio.Lock serialises
        concurrent calls within the same process so that only one coroutine
        performs inserts at a time.  The second caller waits for the first
        to commit, then finds every role already present and skips cleanly.
        Works identically on PostgreSQL, SQL Server, and Oracle.
        """
        async with _seed_roles_lock:
            for role_name, role_def in DEFAULT_ROLES.items():
                existing = await session.execute(select(Role).where(Role.name == role_name))
                if existing.scalar_one_or_none() is not None:
                    continue

                role = Role(
                    name=role_name,
                    description=role_def["description"],
                    is_system=True,
                )
                session.add(role)
                await session.flush()  # Get role.id

                for perm_str in role_def["permissions"]:
                    perm = Permission(role_id=role.id, permission=perm_str)
                    session.add(perm)

                logger.info("Seeded default role: %s", role_name)

            await session.commit()


def _wildcard_match(pattern_parts: list[str], value_parts: list[str]) -> bool:
    """
    Match permission parts with wildcard support.

    Examples:
        ["wip", "*"] matches ["wip", "unit", "move"] → True (prefix + wildcard)
        ["*", "read"] matches ["wip", "read"] → True
        ["*", "read"] matches ["wip", "unit", "read"] → True (wildcard in first position)
    """
    # Pattern: "module.*" — matches anything starting with "module."
    if len(pattern_parts) == 2 and pattern_parts[1] == "*":
        return value_parts[0] == pattern_parts[0] and len(value_parts) >= 2

    # Pattern: "*.action" — matches any module path ending with "action"
    if len(pattern_parts) == 2 and pattern_parts[0] == "*":
        return len(value_parts) >= 2 and value_parts[-1] == pattern_parts[1]

    # General pattern matching (same length, * matches any single segment)
    if len(pattern_parts) != len(value_parts):
        return False
    return all(p == "*" or p == v for p, v in zip(pattern_parts, value_parts))
