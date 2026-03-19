"""
PLUGIN-FW: Pydantic schemas for plugin management API responses and requests.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ─── Response schemas ──────────────────────────────────────────────────


class PluginSummary(BaseModel):
    """Short plugin description for list responses."""

    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    is_loaded: bool = False
    is_running: bool = False
    enabled: bool = True
    error: str | None = None
    extension_points: list[str] = Field(default_factory=list)


class PluginDetail(PluginSummary):
    """Full plugin information for detail responses."""

    min_mes_version: str = "0.1.0"
    permissions: list[dict[str, str]] = Field(default_factory=list)
    required_core_permissions: list[str] = Field(default_factory=list)
    event_subscriptions: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    config_schema: dict[str, Any] = Field(default_factory=dict)
    config_values: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


# ─── Request schemas ──────────────────────────────────────────────────


class PluginConfigUpdate(BaseModel):
    """Request body for updating plugin configuration."""

    config_overrides: dict[str, Any] = Field(
        ..., description="Configuration key-value pairs to persist"
    )
    notes: str | None = Field(None, description="Optional admin notes")


class PluginEnableRequest(BaseModel):
    """Optional body for enable/disable (allows attaching notes)."""

    notes: str | None = Field(None, description="Optional reason for enabling/disabling")


# ─── Available adapter catalog ─────────────────────────────────────────


class AdapterInfo(BaseModel):
    """Information about an available adapter type."""

    type: str = Field(..., description="Adapter type identifier")
    category: str = Field(..., description="Category: erp, equipment, test_equipment")
    description: str = ""
    install_extra: str | None = Field(
        None, description="pip install extra, e.g. 'pip install mes-ai[sap]'"
    )
    is_installed: bool = Field(False, description="Whether the required package is importable")
