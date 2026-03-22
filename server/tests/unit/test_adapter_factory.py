"""
Unit tests for adapter resolution via PluginManager.

Covers:
- get_adapter_by_type returns adapter for running plugin
- get_adapter_by_type returns None when no plugin provides the type
- adapter_health checks running adapter plugins
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from mes.framework.plugin.base import MESPlugin
from mes.framework.plugin.manager import PluginManager, PluginInfo
from mes.framework.plugin.manifest import PluginManifest


def _make_manifest(**overrides) -> PluginManifest:
    data = {
        "id": "test-adapter",
        "name": "Test Adapter",
        "version": "1.0.0",
        "description": "A test adapter plugin",
        "author": "Test",
        "config_schema": {},
        **overrides,
    }
    return PluginManifest(**data)


class _DummyAdapter:
    """Fake adapter returned by a plugin."""
    pass


class _DummyPlugin(MESPlugin):
    """Plugin that wraps a fake adapter."""

    def __init__(self, adapter=None):
        self._adapter = adapter or _DummyAdapter()

    async def initialize(self, config: dict) -> None:
        pass

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    def get_adapter(self):
        return self._adapter

    async def health_check(self) -> bool:
        return True


class TestGetAdapterByType:
    def test_returns_adapter_for_running_plugin(self):
        adapter = _DummyAdapter()
        plugin = _DummyPlugin(adapter=adapter)
        manifest = _make_manifest(
            id="mock-erp",
            extension_points=[{"type": "erp_inbound", "name": "mock"}],
        )
        info = PluginInfo(manifest=manifest, path=Path("/tmp"), instance=plugin)
        info.is_loaded = True
        info.is_running = True

        mgr = PluginManager()
        mgr._plugins["mock-erp"] = info

        result = mgr.get_adapter_by_type("erp_inbound")
        assert result is adapter

    def test_returns_none_when_no_match(self):
        mgr = PluginManager()
        result = mgr.get_adapter_by_type("erp_inbound")
        assert result is None

    def test_skips_non_running_plugin(self):
        plugin = _DummyPlugin()
        manifest = _make_manifest(
            id="mock-erp",
            extension_points=[{"type": "erp_inbound", "name": "mock"}],
        )
        info = PluginInfo(manifest=manifest, path=Path("/tmp"), instance=plugin)
        info.is_loaded = True
        info.is_running = False  # Not running

        mgr = PluginManager()
        mgr._plugins["mock-erp"] = info

        result = mgr.get_adapter_by_type("erp_inbound")
        assert result is None

    def test_returns_dict_entry_for_multi_adapter_plugin(self):
        """Plugin returning a dict of adapters keyed by extension point type."""
        inbound = _DummyAdapter()
        outbound = _DummyAdapter()

        class _MultiPlugin(MESPlugin):
            async def initialize(self, config: dict) -> None: pass
            async def start(self) -> None: pass
            async def stop(self) -> None: pass
            def get_adapter(self):
                return {"erp_inbound": inbound, "erp_outbound": outbound}

        manifest = _make_manifest(
            id="multi-erp",
            extension_points=[
                {"type": "erp_inbound", "name": "mock"},
                {"type": "erp_outbound", "name": "mock"},
            ],
        )
        plugin = _MultiPlugin()
        info = PluginInfo(manifest=manifest, path=Path("/tmp"), instance=plugin)
        info.is_loaded = True
        info.is_running = True

        mgr = PluginManager()
        mgr._plugins["multi-erp"] = info

        assert mgr.get_adapter_by_type("erp_inbound") is inbound
        assert mgr.get_adapter_by_type("erp_outbound") is outbound


class TestGetAdapterPlugin:
    def test_returns_plugin_info(self):
        plugin = _DummyPlugin()
        manifest = _make_manifest(
            id="equip-driver",
            extension_points=[{"type": "equipment_driver", "name": "opcua"}],
        )
        info = PluginInfo(manifest=manifest, path=Path("/tmp"), instance=plugin)
        info.is_loaded = True
        info.is_running = True

        mgr = PluginManager()
        mgr._plugins["equip-driver"] = info

        result = mgr.get_adapter_plugin("equipment_driver")
        assert result is info

    def test_returns_none_when_no_match(self):
        mgr = PluginManager()
        result = mgr.get_adapter_plugin("test_equipment")
        assert result is None


class TestAdapterHealth:
    @pytest.mark.asyncio
    async def test_health_reports_running_adapters(self):
        plugin = _DummyPlugin()
        manifest = _make_manifest(
            id="mock-erp",
            extension_points=[{"type": "erp_inbound", "name": "mock"}],
        )
        info = PluginInfo(manifest=manifest, path=Path("/tmp"), instance=plugin)
        info.is_loaded = True
        info.is_running = True

        mgr = PluginManager()
        mgr._plugins["mock-erp"] = info

        health = await mgr.adapter_health()
        assert health == {"mock-erp": True}

    @pytest.mark.asyncio
    async def test_health_empty_when_no_adapters(self):
        mgr = PluginManager()
        health = await mgr.adapter_health()
        assert health == {}

    @pytest.mark.asyncio
    async def test_health_catches_exceptions(self):
        class _FailPlugin(MESPlugin):
            async def initialize(self, config: dict) -> None: pass
            async def start(self) -> None: pass
            async def stop(self) -> None: pass
            async def health_check(self) -> bool:
                raise RuntimeError("health check failed")

        manifest = _make_manifest(
            id="fail-adapter",
            extension_points=[{"type": "equipment_driver", "name": "fail"}],
        )
        plugin = _FailPlugin()
        info = PluginInfo(manifest=manifest, path=Path("/tmp"), instance=plugin)
        info.is_loaded = True
        info.is_running = True

        mgr = PluginManager()
        mgr._plugins["fail-adapter"] = info

        health = await mgr.adapter_health()
        assert health == {"fail-adapter": False}
