"""
Unit tests for Plugin Management: REST API, CLI, config resolution, adapter bridge.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from mes.framework.plugin.base import MESPlugin, ExtensionPointType
from mes.framework.plugin.manager import PluginManager, PluginInfo
from mes.framework.plugin.manifest import PluginManifest
from mes.framework.plugin.schemas import (
    AdapterInfo,
    ParameterSchema,
    PluginConfigUpdate,
    PluginDetail,
    PluginInstallRequest,
    PluginSummary,
)


# ─── Helpers ───────────────────────────────────────────────────────────


def _make_manifest(**overrides: Any) -> PluginManifest:
    data = {
        "id": "test-plugin",
        "name": "Test Plugin",
        "version": "1.0.0",
        "description": "A test plugin",
        "author": "Test",
        "config_schema": {
            "type": "object",
            "properties": {
                "weight": {"type": "number", "default": 0.5},
                "mode": {"type": "string", "default": "auto"},
            },
        },
        "extension_points": [{"type": "dispatch_strategy", "name": "test-dispatch"}],
    }
    data.update(overrides)
    return PluginManifest.model_validate(data)


class DummyPlugin(MESPlugin):
    async def initialize(self, config: dict[str, Any]) -> None:
        self.config = config

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass


# ─── Config Resolution Tests ──────────────────────────────────────────


class TestConfigResolution:
    def test_resolve_defaults_from_manifest(self):
        manager = PluginManager()
        manifest = _make_manifest()
        config = manager._resolve_config(manifest)
        assert config == {"weight": 0.5, "mode": "auto"}

    def test_resolve_empty_config_schema(self):
        manager = PluginManager()
        manifest = _make_manifest(config_schema={})
        config = manager._resolve_config(manifest)
        assert config == {}

    @pytest.mark.asyncio
    async def test_resolve_with_overrides(self):
        manager = PluginManager()
        manifest = _make_manifest()
        param_values = {"weight": 0.9, "custom_key": "value"}
        result = await manager.resolve_config_with_overrides(manifest, param_values)
        assert result["weight"] == 0.9
        assert result["mode"] == "auto"
        assert result["custom_key"] == "value"


# ─── PluginSummary / PluginDetail Schema Tests ────────────────────────


class TestPluginSchemas:
    def test_plugin_summary(self):
        s = PluginSummary(
            id="test-plugin",
            name="Test",
            version="1.0.0",
            is_loaded=True,
            is_running=True,
            enabled=True,
            installed=True,
            extension_points=["dispatch_strategy"],
        )
        d = s.model_dump()
        assert d["id"] == "test-plugin"
        assert d["is_running"] is True
        assert d["installed"] is True

    def test_plugin_summary_defaults(self):
        s = PluginSummary(
            id="test-plugin",
            name="Test",
            version="1.0.0",
            is_loaded=False,
            is_running=False,
            enabled=False,
            installed=False,
            extension_points=[],
        )
        d = s.model_dump()
        assert d["comment"] == ""
        assert d["category"] == "general"
        assert d["origin"] == "user"

    def test_plugin_detail_extends_summary(self):
        d = PluginDetail(
            id="test-plugin",
            name="Test",
            version="1.0.0",
            is_loaded=True,
            is_running=False,
            enabled=True,
            installed=True,
            config_schema={"properties": {"x": {"type": "number"}}},
            config_values={"x": 42},
        )
        dump = d.model_dump()
        assert dump["config_values"]["x"] == 42
        assert dump["parameters"] == []
        assert dump["parameter_values"] == {}

    def test_adapter_info(self):
        a = AdapterInfo(
            type="opcua",
            category="equipment",
            description="OPC-UA adapter",
            install_extra="opcua",
            is_installed=False,
        )
        assert a.is_installed is False

    def test_plugin_install_request(self):
        r = PluginInstallRequest(parameter_values={"key": "value"}, notes="test")
        assert r.parameter_values == {"key": "value"}
        assert r.notes == "test"

    def test_parameter_schema(self):
        p = ParameterSchema(
            name="host",
            type="string",
            description="Database host",
            required=True,
            default=None,
            secret=False,
        )
        assert p.name == "host"
        assert p.required is True


# ─── Plugin Config Update Schema ──────────────────────────────────────


class TestPluginConfigUpdate:
    def test_valid_config_update(self):
        body = PluginConfigUpdate(config_overrides={"key": "value"}, notes="test")
        assert body.config_overrides == {"key": "value"}
        assert body.notes == "test"

    def test_config_update_requires_overrides(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PluginConfigUpdate()


# ─── CLI Tests ─────────────────────────────────────────────────────────


class TestCLI:
    def test_plugin_list_empty(self, tmp_path: Path, monkeypatch, capsys):
        monkeypatch.setattr("mes.config.settings.PLUGIN_DIR", str(tmp_path))
        monkeypatch.setattr("mes.config.settings.PLUGIN_USER_DIR", str(tmp_path / "user"))
        from mes.cli import cmd_list
        import argparse
        cmd_list(argparse.Namespace())
        out = capsys.readouterr().out
        assert "No plugins found" in out

    def test_plugin_list_with_plugins(self, tmp_path: Path, monkeypatch, capsys):
        monkeypatch.setattr("mes.config.settings.PLUGIN_DIR", str(tmp_path))
        monkeypatch.setattr("mes.config.settings.PLUGIN_USER_DIR", str(tmp_path / "user"))
        plugin_dir = tmp_path / "my_plugin"
        plugin_dir.mkdir()
        manifest = {"id": "my-plugin", "name": "My Plugin", "version": "2.0.0", "origin": "system"}
        with open(plugin_dir / "manifest.yaml", "w") as f:
            yaml.dump(manifest, f)

        from mes.cli import cmd_list
        import argparse
        cmd_list(argparse.Namespace())
        out = capsys.readouterr().out
        assert "my-plugin" in out
        assert "2.0.0" in out

    def test_plugin_search_match(self, tmp_path: Path, monkeypatch, capsys):
        monkeypatch.setattr("mes.config.settings.PLUGIN_DIR", str(tmp_path))
        monkeypatch.setattr("mes.config.settings.PLUGIN_USER_DIR", str(tmp_path / "user"))
        plugin_dir = tmp_path / "dispatch_plugin"
        plugin_dir.mkdir()
        manifest = {"id": "dispatch-opt", "name": "Dispatch Optimizer", "version": "1.0.0"}
        with open(plugin_dir / "manifest.yaml", "w") as f:
            yaml.dump(manifest, f)

        from mes.cli import cmd_search
        import argparse
        cmd_search(argparse.Namespace(keyword="dispatch"))
        out = capsys.readouterr().out
        assert "dispatch-opt" in out

    def test_plugin_search_no_match(self, tmp_path: Path, monkeypatch, capsys):
        monkeypatch.setattr("mes.config.settings.PLUGIN_DIR", str(tmp_path))
        monkeypatch.setattr("mes.config.settings.PLUGIN_USER_DIR", str(tmp_path / "user"))
        from mes.cli import cmd_search
        import argparse
        cmd_search(argparse.Namespace(keyword="nonexistent"))
        out = capsys.readouterr().out
        assert "No plugins matching" in out

    def test_plugin_info(self, tmp_path: Path, monkeypatch, capsys):
        monkeypatch.setattr("mes.config.settings.PLUGIN_DIR", str(tmp_path))
        monkeypatch.setattr("mes.config.settings.PLUGIN_USER_DIR", str(tmp_path / "user"))
        plugin_dir = tmp_path / "info_plugin"
        plugin_dir.mkdir()
        manifest = {
            "id": "info-plugin",
            "name": "Info Plugin",
            "version": "3.0.0",
            "author": "Tester",
            "description": "A plugin for testing info",
            "comment": "Test comment",
            "category": "test",
            "origin": "system",
        }
        with open(plugin_dir / "manifest.yaml", "w") as f:
            yaml.dump(manifest, f)

        from mes.cli import cmd_info
        import argparse
        cmd_info(argparse.Namespace(plugin_id="info-plugin"))
        out = capsys.readouterr().out
        assert "Info Plugin" in out
        assert "3.0.0" in out
        assert "Tester" in out
        assert "system" in out

    def test_plugin_info_not_found(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr("mes.config.settings.PLUGIN_DIR", str(tmp_path))
        monkeypatch.setattr("mes.config.settings.PLUGIN_USER_DIR", str(tmp_path / "user"))
        from mes.cli import cmd_info
        import argparse
        with pytest.raises(SystemExit):
            cmd_info(argparse.Namespace(plugin_id="nonexistent"))

    def test_extras_list(self, capsys):
        from mes.cli import cmd_adapter_extras
        import argparse
        cmd_adapter_extras(argparse.Namespace())
        out = capsys.readouterr().out
        assert "opcua" in out
        assert "mqtt" in out
        assert "sap" in out
        assert "oracle" in out

    def test_main_parser_help(self):
        from mes.cli import main
        with pytest.raises(SystemExit) as exc:
            main(["--help"])
        assert exc.value.code == 0


# ─── Adapter-to-Plugin Bridge Tests ───────────────────────────────────


class TestAdapterPluginBridge:
    def test_find_plugin_adapter_returns_instance(self):
        manifest = _make_manifest(
            id="modbus-driver",
            extension_points=[{"type": "equipment_driver", "name": "modbus"}],
        )
        instance = DummyPlugin()
        info = PluginInfo(manifest=manifest, path=Path("/tmp"), instance=instance)
        info.is_loaded = True
        info.is_running = True

        mock_manager = MagicMock()
        mock_manager.plugins = {"modbus-driver": info}

        with patch("mes.adapters.factory.plugin_manager", mock_manager, create=True):
            from mes.adapters.factory import _find_plugin_adapter
            # Patch the import inside the function
            with patch("mes.main.plugin_manager", mock_manager):
                result = _find_plugin_adapter("modbus", "equipment_driver")
                assert result is instance

    def test_find_plugin_adapter_returns_none(self):
        mock_manager = MagicMock()
        mock_manager.plugins = {}

        with patch("mes.main.plugin_manager", mock_manager):
            from mes.adapters.factory import _find_plugin_adapter
            result = _find_plugin_adapter("unknown", "equipment_driver")
            assert result is None


# ─── REST API Tests (using httpx + TestClient pattern) ────────────────


def _build_test_app(plugin_manager: PluginManager) -> FastAPI:
    """Create a minimal FastAPI app with plugin routes for testing."""
    from mes.framework.plugin.routes import router

    app = FastAPI()
    app.include_router(router)
    return app


class TestPluginRoutes:
    @pytest.mark.asyncio
    async def test_list_plugins_empty(self):
        manager = PluginManager()
        app = _build_test_app(manager)

        with patch("mes.framework.plugin.routes.get_db_session") as mock_session_dep:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_session.execute = AsyncMock(return_value=mock_result)

            async def fake_session():
                yield mock_session

            mock_session_dep.return_value = fake_session()
            app.dependency_overrides[
                __import__("mes.framework.db", fromlist=["get_db_session"]).get_db_session
            ] = fake_session

            with patch("mes.main.plugin_manager", manager):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    resp = await client.get("/api/v1/plugins")
                    assert resp.status_code == 200
                    body = resp.json()
                    assert body["data"] == []

    @pytest.mark.asyncio
    async def test_catalog_endpoint(self):
        manager = PluginManager()
        app = _build_test_app(manager)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/plugins/catalog")
            assert resp.status_code == 200
            body = resp.json()
            assert isinstance(body["data"], list)
            assert len(body["data"]) > 0
            # Every entry should have required fields
            for entry in body["data"]:
                assert "type" in entry
                assert "category" in entry
                assert "is_installed" in entry


# ─── PluginManager Extended Tests ─────────────────────────────────────


class TestPluginManagerExtended:
    @pytest.mark.asyncio
    async def test_discover_scans_both_dirs(self, tmp_path: Path, monkeypatch):
        """Test that discover_all scans both system and user directories."""
        sys_dir = tmp_path / "system"
        usr_dir = tmp_path / "user"
        sys_dir.mkdir()
        usr_dir.mkdir()
        monkeypatch.setattr("mes.config.settings.PLUGIN_DIR", str(sys_dir))
        monkeypatch.setattr("mes.config.settings.PLUGIN_USER_DIR", str(usr_dir))

        # System plugin
        sp = sys_dir / "sys_plugin"
        sp.mkdir()
        manifest = {"id": "sys-plugin", "name": "Sys Plugin", "version": "1.0.0", "origin": "system"}
        with open(sp / "manifest.yaml", "w") as f:
            yaml.dump(manifest, f)
        plugin_code = '''
from mes.framework.plugin.base import MESPlugin
from typing import Any
class TestMESPlugin(MESPlugin):
    async def initialize(self, config: dict[str, Any]) -> None:
        self.config = config
    async def start(self) -> None:
        pass
    async def stop(self) -> None:
        pass
'''
        with open(sp / "plugin.py", "w") as f:
            f.write(plugin_code)

        # User plugin
        up = usr_dir / "usr_plugin"
        up.mkdir()
        manifest2 = {"id": "usr-plugin", "name": "User Plugin", "version": "1.0.0", "origin": "user"}
        with open(up / "manifest.yaml", "w") as f:
            yaml.dump(manifest2, f)
        with open(up / "plugin.py", "w") as f:
            f.write(plugin_code)

        manager = PluginManager()
        discovered = await manager.discover_all()
        assert "sys-plugin" in discovered
        assert "usr-plugin" in discovered

    @pytest.mark.asyncio
    async def test_resolve_config_with_overrides_merges(self):
        manager = PluginManager()
        manifest = _make_manifest()
        param_values = {"weight": 0.9}
        result = await manager.resolve_config_with_overrides(manifest, param_values)
        assert result["weight"] == 0.9
        assert result["mode"] == "auto"

    @pytest.mark.asyncio
    async def test_resolve_config_with_config_overrides(self):
        manager = PluginManager()
        manifest = _make_manifest()
        param_values = {"weight": 0.8}
        config_overrides = {"mode": "manual"}
        result = await manager.resolve_config_with_overrides(manifest, param_values, config_overrides)
        assert result["weight"] == 0.8
        assert result["mode"] == "manual"

    def test_get_plugin_not_loaded(self):
        manager = PluginManager()
        assert manager.get_plugin("nonexistent") is None

    def test_validate_parameters_all_optional(self):
        manager = PluginManager()
        manifest = _make_manifest()  # No parameters defined, just config_schema
        errors = manager.validate_parameters(manifest, {})
        assert errors == []

    def test_validate_parameters_missing_required(self):
        from mes.framework.plugin.manifest import ManifestParameter
        manager = PluginManager()
        manifest = _make_manifest(
            parameters=[
                {"name": "host", "type": "string", "description": "DB host", "required": True},
                {"name": "port", "type": "integer", "description": "DB port", "required": False, "default": 5432},
            ]
        )
        errors = manager.validate_parameters(manifest, {})
        assert len(errors) == 1
        assert "host" in errors[0]

    def test_validate_parameters_all_provided(self):
        manager = PluginManager()
        manifest = _make_manifest(
            parameters=[
                {"name": "host", "type": "string", "description": "DB host", "required": True},
            ]
        )
        errors = manager.validate_parameters(manifest, {"host": "localhost"})
        assert errors == []
