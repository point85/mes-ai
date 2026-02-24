"""
PLUGIN-FW: Plugin manifest schema and validation.

The manifest.yaml file in each plugin directory declares:
- Plugin identity (id, name, version, author)
- Minimum MES version compatibility
- Extension points the plugin implements
- Events the plugin subscribes to
- Custom permissions the plugin introduces
- Required core permissions
- Dependencies on other plugins
- Configuration schema (JSON Schema)
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


class PluginManifest(BaseModel):
    """
    Parsed and validated plugin manifest.
    Corresponds to the manifest.yaml file per ARCHITECTURE.md §7.2.
    """

    id: str = Field(..., description="Unique plugin identifier (e.g. 'my-custom-plugin')")
    name: str = Field(..., description="Human-readable plugin name")
    version: str = Field(..., description="Semantic version string")
    description: str = Field("", description="Brief plugin description")
    author: str = Field("", description="Plugin author")
    min_mes_version: str = Field("0.1.0", description="Minimum MES server version required")

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

    # Configuration schema (JSON Schema format)
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
