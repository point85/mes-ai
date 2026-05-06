"""
ADMIN: REST API for reading and writing the server .env configuration file.

GET  /api/v1/admin/config        — return all editable settings (secrets masked)
PATCH /api/v1/admin/config       — update one or more settings and rewrite .env

Excluded (read-only, cannot be changed via UI):
    MES_DATABASE_URL, MES_DB_POOL_SIZE, MES_DB_MAX_OVERFLOW, MES_DB_ECHO

Secret fields are returned as masked ("••••••") and a PATCH payload that
contains the mask value is ignored (no-op), so existing secrets are never
accidentally overwritten.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from mes.config import settings
from mes.framework.api.responses import success_response
from mes.framework.auth.dependencies import require_permission

logger = logging.getLogger("mes.admin.config")

router = APIRouter(prefix="/api/v1/admin/config", tags=["Admin – Config"])

# Absolute path to the .env file (one directory up from this file's package root)
_ENV_FILE = Path(__file__).resolve().parents[4] / ".env"

_MASK = "••••••"

# Fields that must never be exposed or modified through the API.
_EXCLUDED: frozenset[str] = frozenset(
    [
        "MES_DATABASE_URL",
        "MES_DB_POOL_SIZE",
        "MES_DB_MAX_OVERFLOW",
        "MES_DB_ECHO",
    ]
)

# Fields whose values are masked on GET; a PATCH with the mask value is ignored.
_SECRET_FIELDS: frozenset[str] = frozenset(
    [
        "MES_SECRET_KEY",
        "MES_OIDC_CLIENT_SECRET",
    ]
)

# Metadata for each editable key: label, description, input type, options.
_META: dict[str, dict[str, Any]] = {
    "MES_AUTH_MODE": {
        "label": "Authentication Mode",
        "description": "none = dev (no login); local = username/password; oidc = enterprise SSO",
        "type": "select",
        "options": ["none", "local", "oidc"],
    },
    "MES_SECRET_KEY": {
        "label": "JWT Secret Key",
        "description": "Secret used to sign JWTs. Change in production.",
        "type": "password",
        "options": [],
    },
    "MES_ALGORITHM": {
        "label": "JWT Algorithm",
        "description": "Algorithm for JWT signing.",
        "type": "select",
        "options": ["HS256", "HS384", "HS512", "RS256"],
    },
    "MES_ACCESS_TOKEN_EXPIRE_MINUTES": {
        "label": "Access Token Expiry (minutes)",
        "description": "How long access tokens remain valid.",
        "type": "number",
        "options": [],
    },
    "MES_REFRESH_TOKEN_EXPIRE_DAYS": {
        "label": "Refresh Token Expiry (days)",
        "description": "How long refresh tokens remain valid.",
        "type": "number",
        "options": [],
    },
    "MES_OIDC_ISSUER": {
        "label": "OIDC Issuer URL",
        "description": "OIDC provider URL (required when AUTH_MODE=oidc).",
        "type": "text",
        "options": [],
    },
    "MES_OIDC_CLIENT_ID": {
        "label": "OIDC Client ID",
        "description": "Client ID registered with the OIDC provider.",
        "type": "text",
        "options": [],
    },
    "MES_OIDC_CLIENT_SECRET": {
        "label": "OIDC Client Secret",
        "description": "Client secret for the OIDC provider. Write-only once saved.",
        "type": "password",
        "options": [],
    },
    "MES_OIDC_SCOPES": {
        "label": "OIDC Scopes",
        "description": "Comma-separated OIDC scopes.",
        "type": "text",
        "options": [],
    },
    "MES_OIDC_ROLE_CLAIM": {
        "label": "OIDC Role Claim",
        "description": "JWT claim name that carries the user's roles/groups.",
        "type": "text",
        "options": [],
    },
    "MES_OIDC_REDIRECT_URI": {
        "label": "OIDC Redirect URI",
        "description": "OAuth callback URL registered with the provider.",
        "type": "text",
        "options": [],
    },
    "MES_EVENT_BUS_TYPE": {
        "label": "Event Bus Type",
        "description": "memory = in-process; redis = distributed via Redis.",
        "type": "select",
        "options": ["memory", "redis"],
    },
    "MES_REDIS_URL": {
        "label": "Redis URL",
        "description": "Redis connection URL (used when EVENT_BUS_TYPE=redis).",
        "type": "text",
        "options": [],
    },
    "MES_LOG_LEVEL": {
        "label": "Log Level",
        "description": "Server log verbosity.",
        "type": "select",
        "options": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    },
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _read_env_file() -> dict[str, str]:
    """Parse the .env file into a key→value dict (skips comments and blanks)."""
    result: dict[str, str] = {}
    if not _ENV_FILE.exists():
        return result
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped:
            key, _, value = stripped.partition("=")
            result[key.strip()] = value.strip()
    return result


def _write_env_file(updates: dict[str, str]) -> None:
    """
    Rewrite .env preserving comments/structure, updating or appending keys.
    Only keys present in `updates` are changed.
    """
    if not _ENV_FILE.exists():
        raise FileNotFoundError(f".env file not found at {_ENV_FILE}")

    lines = _ENV_FILE.read_text(encoding="utf-8").splitlines()
    written: set[str] = set()
    new_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.partition("=")[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                written.add(key)
                continue
        new_lines.append(line)

    # Append any keys not already in the file
    for key, value in updates.items():
        if key not in written:
            new_lines.append(f"{key}={value}")

    _ENV_FILE.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _current_values() -> dict[str, str]:
    """Return live values from settings (not the .env file on disk)."""
    return {
        "MES_AUTH_MODE": settings.AUTH_MODE,
        "MES_SECRET_KEY": settings.SECRET_KEY,
        "MES_ALGORITHM": settings.ALGORITHM,
        "MES_ACCESS_TOKEN_EXPIRE_MINUTES": str(settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "MES_REFRESH_TOKEN_EXPIRE_DAYS": str(settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "MES_OIDC_ISSUER": settings.OIDC_ISSUER,
        "MES_OIDC_CLIENT_ID": settings.OIDC_CLIENT_ID,
        "MES_OIDC_CLIENT_SECRET": settings.OIDC_CLIENT_SECRET,
        "MES_OIDC_SCOPES": settings.OIDC_SCOPES,
        "MES_OIDC_ROLE_CLAIM": settings.OIDC_ROLE_CLAIM,
        "MES_OIDC_REDIRECT_URI": settings.OIDC_REDIRECT_URI,
        "MES_EVENT_BUS_TYPE": settings.EVENT_BUS_TYPE,
        "MES_REDIS_URL": settings.REDIS_URL,
        "MES_LOG_LEVEL": settings.LOG_LEVEL,
    }


# ── Response models ───────────────────────────────────────────────────────────

class ConfigEntry(BaseModel):
    key: str
    value: str
    label: str
    description: str
    type: str          # "text" | "password" | "select" | "number"
    options: list[str]
    readonly: bool = False
    masked: bool = False


class ConfigPatchRequest(BaseModel):
    updates: dict[str, str]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", summary="Get editable server configuration")
async def get_config(
    _user=Depends(require_permission("admin.config.read")),
):
    """Return all editable configuration entries with current values."""
    live = _current_values()
    entries: list[ConfigEntry] = []

    for key, meta in _META.items():
        raw_value = live.get(key, "")
        is_secret = key in _SECRET_FIELDS
        display_value = _MASK if (is_secret and raw_value) else raw_value

        entries.append(
            ConfigEntry(
                key=key,
                value=display_value,
                label=meta["label"],
                description=meta["description"],
                type=meta["type"],
                options=meta["options"],
                masked=is_secret,
            )
        )

    return success_response({"entries": [e.model_dump() for e in entries]})


@router.patch("", summary="Update server configuration")
async def patch_config(
    body: ConfigPatchRequest,
    _user=Depends(require_permission("admin.config.write")),
):
    """
    Write one or more settings to the .env file.

    - Excluded keys (DATABASE_URL, DB pool settings) are silently ignored.
    - Secret fields submitted with the mask value are ignored (no-op).
    - A server restart is required for changes to take effect.
    """
    filtered: dict[str, str] = {}

    for key, value in body.updates.items():
        if key in _EXCLUDED:
            logger.warning("Attempt to edit excluded config key %s — ignored", key)
            continue
        if key not in _META:
            logger.warning("Unknown config key %s — ignored", key)
            continue
        if key in _SECRET_FIELDS and value == _MASK:
            continue  # User left the masked placeholder — don't overwrite
        filtered[key] = value

    if filtered:
        _write_env_file(filtered)
        logger.info("Config updated by admin: %s", list(filtered.keys()))

    return success_response(
        {
            "updated_keys": list(filtered.keys()),
            "restart_required": True,
        }
    )
