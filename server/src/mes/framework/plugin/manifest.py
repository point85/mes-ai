"""
PLUGIN-FW: Plugin manifest schema and validation.

The manifest.yaml file in each plugin directory declares:
- Plugin identity (id, name, version, author, description, comment, category, origin)
- Minimum MES version compatibility
- Extension points the plugin implements
- Events the plugin subscribes to
- Custom permissions the plugin introduces
- Required core permissions
- Dependencies on other plugins
- Parameters: required and optional configuration the end user provides at install time
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class ManifestPermission(BaseModel):
    """A custom permission declared by a plugin."""

    id: str = Field(..., description="Permission string (e.g. 'my_plugin.config.read')")
    description: str = Field("", description="Human-readable description of what this permits")


class ManifestExtensionPoint(BaseModel):
    """An extension point declaration in a plugin manifest."""

    type: str = Field(..., description="Extension point type (e.g. 'dispatch_strategy')")
    name: str | None = Field(None, description="Name of the extension (e.g. strategy name)")
    hook: str | None = Field(None, description="Hook name (for operation_hook type)")
    handler: str | None = Field(None, description="Handler reference (e.g. 'plugin:on_before_move')")
    prefix: str | None = Field(None, description="API prefix (for rest_endpoint type)")


class ManifestParameter(BaseModel):
    """A configuration parameter declared by a plugin author.

    Required parameters must be provided during installation.
    Optional parameters have defaults and can be overridden.
    """

    name: str = Field(..., description="Parameter key (e.g. 'broker_url')")
    type: str = Field("string", description="Data type: string, number, boolean, integer")
    description: str = Field("", description="Human-readable description")
    required: bool = Field(False, description="Must be provided at install time")
    default: Any = Field(None, description="Default value (only for optional parameters)")
    secret: bool = Field(False, description="Whether to mask this value in UI (e.g. passwords)")


class ManifestCompanion(BaseModel):
    """A companion binding declared in a plugin manifest.

    type='plugin': another server-side plugin — cascades install/enable/disable.
    type='client': a web UI app — metadata only (path, dev_port, name).
    """

    id: str = Field(..., description="Companion plugin ID or client identifier")
    type: str = Field("plugin", description="Companion kind: 'plugin' or 'client'")
    name: str = Field("", description="Human-readable label")
    path: str = Field("", description="Relative path to client app (type=client only)")
    dev_port: int | None = Field(None, description="Dev-server port (type=client only)")
    description: str = Field("", description="Brief description of the companion")


class PluginManifest(BaseModel):
    """
    Parsed and validated plugin manifest.
    Corresponds to the manifest.yaml file in each plugin directory.
    """

    # ── Required identity fields ──
    id: str = Field(..., description="Unique plugin identifier (e.g. 'my-custom-plugin')")
    name: str = Field(..., description="Human-readable plugin name")
    version: str = Field(..., description="Semantic version string")
    description: str = Field("", description="Brief plugin description")
    author: str = Field("", description="Plugin author")
    comment: str = Field("", description="Free-form comment from the plugin author")
    category: str = Field("general", description="Plugin category (e.g. erp, equipment, quality, dispatch, general)")
    origin: str = Field("user", description="Origin: 'system' (project contributors) or 'user' (end user)")
    min_mes_version: str = Field("0.1.0", description="Minimum MES server version required")

    # ── Parameters (required + optional config the end user provides at install time) ──
    parameters: list[ManifestParameter] = Field(default_factory=list)

    # Custom permissions this plugin introduces
    permissions: list[ManifestPermission] = Field(default_factory=list)

    # Existing core permissions this plugin requires
    required_core_permissions: list[str] = Field(default_factory=list)

    # Extension points this plugin implements
    extension_points: list[ManifestExtensionPoint] = Field(default_factory=list)

    # Event topics this plugin subscribes to
    event_subscriptions: list[str] = Field(default_factory=list)

    # Other plugins this plugin depends on
    dependencies: list[str] = Field(default_factory=list)

    # Companion bindings — other plugins or client apps bundled with this plugin
    companions: list[ManifestCompanion] = Field(default_factory=list)

    # Pip packages to auto-install when the plugin is installed (e.g. ["stomp-py>=8.1.0"])
    pip_dependencies: list[str] = Field(default_factory=list, description="Python packages to pip-install at plugin install time")

    # Legacy config_schema kept for backward compatibility; prefer `parameters`
    config_schema: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Path) -> "PluginManifest":
        """
        Load and validate a manifest from a YAML file.

        Args:
            path: Path to the manifest.yaml file.

        Returns:
            Validated PluginManifest instance.

        Raises:
            FileNotFoundError: If the manifest file does not exist.
            yaml.YAMLError: If YAML parsing fails.
            pydantic.ValidationError: If the manifest does not match the schema.
        """
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)
