"""
Unit tests for PLUGIN-FW module.

Tests cover:
- Plugin manifest parsing and validation
- Plugin base class interface
- Plugin manager discovery logic (with temp directories)
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from mes.framework.plugin.base import ExtensionPointType, MESPlugin
from mes.framework.plugin.manifest import PluginManifest
from mes.framework.plugin.manager import PluginManager


# --- Manifest tests ---


class TestPluginManifest:
    def test_parse_minimal_manifest(self):
        data = {
            "id": "test-plugin",
            "name": "Test Plugin",
            "version": "1.0.0",
        }
        manifest = PluginManifest.model_validate(data)
        assert manifest.id == "test-plugin"
        assert manifest.name == "Test Plugin"
        assert manifest.version == "1.0.0"
        assert manifest.permissions == []
        assert manifest.extension_points == []

    def test_parse_full_manifest(self):
        data = {
            "id": "advanced-dispatch",
            "name": "Advanced Dispatch",
            "version": "2.0.0",
            "description": "Multi-criteria dispatch optimizer",
            "author": "AI Agent",
            "min_mes_version": "0.1.0",
            "permissions": [
                {"id": "advanced_dispatch.config.read", "description": "View config"},
            ],
            "required_core_permissions": ["dispatch.read", "wip.read"],
            "extension_points": [
                {"type": "dispatch_strategy", "name": "multi_criteria"},
                {"type": "rest_endpoint", "prefix": "/api/v1/custom/optimizer"},
            ],
            "event_subscriptions": ["wip.unit.moved", "equipment.state.changed"],
            "dependencies": [],
            "config_schema": {
                "type": "object",
                "properties": {
                    "weight": {"type": "number", "default": 0.7},
                },
            },
        }
        manifest = PluginManifest.model_validate(data)
        assert len(manifest.permissions) == 1
        assert len(manifest.extension_points) == 2
        assert len(manifest.event_subscriptions) == 2
        assert manifest.config_schema["properties"]["weight"]["default"] == 0.7

    def test_parse_from_yaml_file(self, tmp_path: Path):
        manifest_data = {
            "id": "yaml-test",
            "name": "YAML Test Plugin",
            "version": "0.1.0",
        }
        manifest_file = tmp_path / "manifest.yaml"
        with open(manifest_file, "w") as f:
            yaml.dump(manifest_data, f)

        manifest = PluginManifest.from_yaml(manifest_file)
        assert manifest.id == "yaml-test"

    def test_missing_required_fields_raises(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PluginManifest.model_validate({"name": "No ID"})


# --- MESPlugin base class tests ---


class TestMESPluginBase:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            MESPlugin()

    def test_concrete_plugin_subclass(self):
        class MyPlugin(MESPlugin):
            async def initialize(self, config: dict[str, Any]) -> None:
                self.config = config

            async def start(self) -> None:
                pass

            async def stop(self) -> None:
                pass

        plugin = MyPlugin()
        assert plugin.get_routes() is None
        assert plugin.get_event_handlers() is None


# --- Extension point type tests ---


class TestExtensionPointType:
    def test_all_types_exist(self):
        expected = {
            "dispatch_strategy",
            "operation_hook",
            "rest_endpoint",
            "event_handler",
            "data_processor",
            "report_generator",
            "equipment_driver",
            "equipment_state_model",
        }
        actual = {e.value for e in ExtensionPointType}
        assert actual == expected


# --- Plugin Manager tests (with temp filesystem) ---


class TestPluginManager:
    @pytest.mark.asyncio
    async def test_discover_empty_directory(self, tmp_path: Path, monkeypatch):
        """Plugin manager should handle empty plugin directory gracefully."""
        monkeypatch.setattr("mes.config.settings.PLUGIN_DIR", str(tmp_path))
        monkeypatch.setattr("mes.config.settings.PLUGIN_USER_DIR", str(tmp_path / "user"))
        manager = PluginManager()
        discovered = await manager.discover_all()
        assert discovered == []

    @pytest.mark.asyncio
    async def test_discover_nonexistent_directory(self, monkeypatch):
        """Plugin manager should handle missing plugin directory gracefully."""
        monkeypatch.setattr(
            "mes.config.settings.PLUGIN_DIR", "/nonexistent/path/to/plugins"
        )
        monkeypatch.setattr(
            "mes.config.settings.PLUGIN_USER_DIR", "/nonexistent/path/to/user_plugins"
        )
        manager = PluginManager()
        discovered = await manager.discover_all()
        assert discovered == []

    @pytest.mark.asyncio
    async def test_discover_and_load_plugin(self, tmp_path: Path, monkeypatch):
        """Full lifecycle: discover → load → start → stop a test plugin."""
        monkeypatch.setattr("mes.config.settings.PLUGIN_DIR", str(tmp_path))
        monkeypatch.setattr("mes.config.settings.PLUGIN_USER_DIR", str(tmp_path / "user"))

        # Create a test plugin directory
        plugin_dir = tmp_path / "test_plugin"
        plugin_dir.mkdir()

        # Write manifest.yaml
        manifest = {
            "id": "test-plugin",
            "name": "Test Plugin",
            "version": "1.0.0",
            "config_schema": {
                "type": "object",
                "properties": {
                    "threshold": {"type": "number", "default": 42},
                },
            },
        }
        with open(plugin_dir / "manifest.yaml", "w") as f:
            yaml.dump(manifest, f)

        # Write plugin.py
        plugin_code = '''
from mes.framework.plugin.base import MESPlugin
from typing import Any

class TestMESPlugin(MESPlugin):
    async def initialize(self, config: dict[str, Any]) -> None:
        self.config = config
        self.started = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.started = False
'''
        with open(plugin_dir / "plugin.py", "w") as f:
            f.write(plugin_code)

        manager = PluginManager()
        discovered = await manager.discover_all()
        assert "test-plugin" in discovered

        info = manager.get_plugin("test-plugin")
        assert info is not None
        assert info.manifest.id == "test-plugin"
        assert info.is_loaded is False
        assert info.is_running is False

        # Load and start with this plugin's id in the installed set
        started = await manager.load_and_start({"test-plugin"})
        assert "test-plugin" in started
        assert info.is_loaded is True
        assert info.is_running is True

        await manager.stop_all()
        assert info.is_running is False

    def test_is_loaded(self):
        manager = PluginManager()
        assert manager.is_loaded("nonexistent") is False
