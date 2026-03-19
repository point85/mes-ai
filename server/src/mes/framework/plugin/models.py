"""
PLUGIN-FW: Database models for plugin configuration persistence.

Stores per-plugin enabled/disabled state and user-overridden configuration
values so that they survive server restarts.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from mes.framework.db.base import BaseModel


class PluginConfig(BaseModel):
    """
    Persisted plugin configuration and state.

    One row per plugin_id. Tracks whether the plugin is enabled and
    stores user-overridden configuration values (merged on top of
    manifest defaults at resolve time).
    """

    __tablename__ = "plugin_config"

    plugin_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Plugin identifier matching manifest.id",
    )

    enabled: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        comment="Whether the plugin should be started on boot",
    )

    config_overrides: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        server_default="{}",
        nullable=False,
        comment="User-overridden config values (merged over manifest defaults)",
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        default=None,
        nullable=True,
        comment="Optional admin notes about the plugin configuration",
    )
