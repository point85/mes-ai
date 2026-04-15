"""
PLUGIN-FW: Pydantic schemas for plugin management API responses and requests.

Plugin lifecycle: available → installed → enabled/disabled → uninstalled
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ─── Parameter schema (mirrors ManifestParameter for API responses) ───


class ParameterSchema(BaseModel):
    """Describes a plugin parameter for the UI install form."""

    name: str
    type: str = "string"
    description: str = ""
    required: bool = False
    default: Any = None
    secret: bool = False
    items: list[ParameterSchema] = Field(default_factory=list)


# ─── Response schemas ──────────────────────────────────────────────────


class PluginSummary(BaseModel):
    """Short plugin description for list responses."""

    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    comment: str = ""
    category: str = "general"
    origin: str = "user"
    installed: bool = False
    enabled: bool = False
    is_loaded: bool = False
    is_running: bool = False
    error: str | None = None
    extension_points: list[str] = Field(default_factory=list)


class CompanionInfo(BaseModel):
    """Companion binding returned in plugin detail responses."""

    id: str
    type: str = "plugin"
    name: str = ""
    path: str = ""
    dev_port: int | None = None
    description: str = ""
    installed: bool = False
    enabled: bool = False


class PluginDetail(PluginSummary):
    """Full plugin information for detail responses."""

    min_mes_version: str = "0.1.0"
    parameters: list[ParameterSchema] = Field(default_factory=list)
    parameter_values: dict[str, Any] = Field(default_factory=dict)
    permissions: list[dict[str, str]] = Field(default_factory=list)
    required_core_permissions: list[str] = Field(default_factory=list)
    event_subscriptions: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    companions: list[CompanionInfo] = Field(default_factory=list)
    config_schema: dict[str, Any] = Field(default_factory=dict)
    config_values: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


# ─── Request schemas ──────────────────────────────────────────────────


class PluginInstallRequest(BaseModel):
    """Request body for installing a plugin (providing parameter values)."""

    parameter_values: dict[str, Any] = Field(
        default_factory=dict,
        description="Values for manifest-declared parameters (required params must be included)",
    )
    notes: str | None = Field(None, description="Optional admin notes")


class PluginConfigUpdate(BaseModel):
    """Request body for updating plugin configuration after installation."""

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
