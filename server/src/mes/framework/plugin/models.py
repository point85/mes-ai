"""
PLUGIN-FW: Database models for plugin configuration persistence.

Stores per-plugin installed/enabled state and user-provided parameter values
so that they survive server restarts.

Lifecycle:  available → installed (params filled) → enabled → disabled → uninstalled
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from mes.framework.db.base import BaseModel


class PluginConfig(BaseModel):
    """
    Persisted plugin configuration and state.

    One row per plugin_id. Tracks:
    - installed: whether the plugin has been installed (params provided)
    - enabled: whether the plugin should be started on boot
    - parameter_values: user-provided values for manifest-declared parameters
    - config_overrides: additional runtime config overrides
    - notes: admin annotations
    """

    __tablename__ = "plugin_config"

    plugin_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Plugin identifier matching manifest.id",
    )

    installed: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether the plugin has been installed (parameters provided)",
    )

    enabled: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether the plugin should be started on boot",
    )

    parameter_values: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
        comment="User-provided parameter values (filled during install)",
    )

    config_overrides: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        server_default="{}",
        nullable=False,
        comment="Additional runtime config overrides (merged over manifest defaults)",
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        default=None,
        nullable=True,
        comment="Optional admin notes about the plugin configuration",
    )
