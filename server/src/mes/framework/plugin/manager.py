"""
PLUGIN-FW: Plugin lifecycle manager.

Manages the full plugin lifecycle per ARCHITECTURE.md §7.4:
    discover → validate manifest → load module → initialize(config) → start() → stop()

Plugin isolation:
- Plugin errors are caught and logged; a failing plugin does not crash the server.
- Plugin database tables use prefix: plugin_{plugin_id}_
- Plugin configuration is stored in the database, not environment variables.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

from mes.config import settings
from mes.framework.events import event_bus

from .base import MESPlugin
from .manifest import PluginManifest

logger = logging.getLogger("mes.plugin")


class PluginInfo:
    """Runtime state for a loaded plugin."""

    def __init__(
        self,
        manifest: PluginManifest,
        instance: MESPlugin,
        path: Path,
    ) -> None:
        self.manifest = manifest
        self.instance = instance
        self.path = path
        self.is_running: bool = False
        self.error: str | None = None


class PluginManager:
    """
    Manages plugin discovery, loading, lifecycle, and extension point registration.

    Usage:
        manager = PluginManager()
        await manager.discover_and_load()  # Scans plugin directories
        await manager.start_all()           # Starts all loaded plugins
        await manager.stop_all()            # Stops all running plugins
    """

    def __init__(self) -> None:
        self._plugins: dict[str, PluginInfo] = {}

    @property
    def plugins(self) -> dict[str, PluginInfo]:
        """Returns the registry of loaded plugins keyed by plugin ID."""
        return dict(self._plugins)

    async def discover_and_load(self) -> list[str]:
        """
        Scan configured plugin directories for plugins, validate manifests,
        and load plugin instances.

        Returns:
            List of successfully loaded plugin IDs.
        """
        loaded: list[str] = []
        plugin_dir = Path(settings.PLUGIN_DIR)

        if not plugin_dir.exists():
            logger.info("Plugin directory '%s' does not exist, skipping discovery", plugin_dir)
            return loaded

        for candidate in plugin_dir.iterdir():
            if not candidate.is_dir():
                continue

            manifest_path = candidate / "manifest.yaml"
            if not manifest_path.exists():
                logger.debug("Skipping '%s' — no manifest.yaml found", candidate.name)
                continue

            try:
                plugin_id = await self._load_plugin(candidate, manifest_path)
                loaded.append(plugin_id)
            except Exception as exc:
                logger.error(
                    "Failed to load plugin from '%s': %s",
                    candidate.name,
                    exc,
                    exc_info=True,
                )

        logger.info("Discovered and loaded %d plugin(s): %s", len(loaded), loaded)
        return loaded

    async def _load_plugin(self, plugin_path: Path, manifest_path: Path) -> str:
        """
        Load a single plugin: validate manifest, import module, instantiate.

        Args:
            plugin_path: Directory containing the plugin.
            manifest_path: Path to manifest.yaml.

        Returns:
            Plugin ID.

        Raises:
            Exception: On validation or import failure.
        """
        # 1. Validate manifest
        manifest = PluginManifest.from_yaml(manifest_path)
        plugin_id = manifest.id

        if plugin_id in self._plugins:
            raise ValueError(f"Plugin '{plugin_id}' is already loaded")

        # 2. Check dependencies
        for dep_id in manifest.dependencies:
            if dep_id not in self._plugins:
                raise ValueError(
                    f"Plugin '{plugin_id}' requires '{dep_id}' which is not loaded"
                )

        # 3. Load Python module
        plugin_module_path = plugin_path / "plugin.py"
        if not plugin_module_path.exists():
            raise FileNotFoundError(f"Plugin entry point not found: {plugin_module_path}")

        module_name = f"mes_plugin_{plugin_id.replace('-', '_')}"
        spec = importlib.util.spec_from_file_location(module_name, plugin_module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot create module spec for {plugin_module_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # 4. Find and instantiate MESPlugin subclass
        plugin_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, MESPlugin)
                and attr is not MESPlugin
            ):
                plugin_class = attr
                break

        if plugin_class is None:
            raise TypeError(
                f"No MESPlugin subclass found in {plugin_module_path}"
            )

        instance = plugin_class()

        # 5. Initialize with config
        config = self._resolve_config(manifest)
        await instance.initialize(config)

        # 6. Register event handlers
        event_handlers = instance.get_event_handlers()
        if event_handlers:
            for topic, handler in event_handlers.items():
                event_bus.subscribe(topic, handler)
                logger.debug(
                    "Plugin '%s': registered event handler for '%s'",
                    plugin_id,
                    topic,
                )

        # 7. Store plugin info
        self._plugins[plugin_id] = PluginInfo(
            manifest=manifest,
            instance=instance,
            path=plugin_path,
        )

        logger.info("Loaded plugin '%s' v%s", plugin_id, manifest.version)
        return plugin_id

    async def start_all(self) -> None:
        """Start all loaded plugins that are not yet running."""
        for plugin_id, info in self._plugins.items():
            if info.is_running:
                continue
            try:
                await info.instance.start()
                info.is_running = True
                logger.info("Started plugin '%s'", plugin_id)

                # Emit plugin.loaded event
                from mes.framework.events import MESEvent

                await event_bus.publish(
                    MESEvent(
                        event_type="plugin.loaded",
                        source="PLUGIN-FW",
                        payload={"plugin_id": plugin_id, "version": info.manifest.version},
                    )
                )
            except Exception as exc:
                info.error = str(exc)
                logger.error(
                    "Failed to start plugin '%s': %s",
                    plugin_id,
                    exc,
                    exc_info=True,
                )

                # Emit plugin.error event
                from mes.framework.events import MESEvent

                await event_bus.publish(
                    MESEvent(
                        event_type="plugin.error",
                        source="PLUGIN-FW",
                        payload={"plugin_id": plugin_id, "error": str(exc)},
                    )
                )

    async def stop_all(self) -> None:
        """Stop all running plugins in reverse load order."""
        for plugin_id in reversed(list(self._plugins.keys())):
            info = self._plugins[plugin_id]
            if not info.is_running:
                continue
            try:
                await info.instance.stop()
                info.is_running = False
                logger.info("Stopped plugin '%s'", plugin_id)
            except Exception as exc:
                logger.error(
                    "Error stopping plugin '%s': %s",
                    plugin_id,
                    exc,
                    exc_info=True,
                )

    async def get_plugin_routes(self) -> list:
        """Collect all FastAPI routers from loaded plugins."""
        routers = []
        for plugin_id, info in self._plugins.items():
            try:
                routes = info.instance.get_routes()
                if routes:
                    if isinstance(routes, list):
                        routers.extend(routes)
                    else:
                        routers.append(routes)
            except Exception as exc:
                logger.error(
                    "Error getting routes from plugin '%s': %s",
                    plugin_id,
                    exc,
                )
        return routers

    def get_plugin(self, plugin_id: str) -> PluginInfo | None:
        """Get a loaded plugin's info by ID."""
        return self._plugins.get(plugin_id)

    def is_loaded(self, plugin_id: str) -> bool:
        """Check if a plugin is loaded."""
        return plugin_id in self._plugins

    def _resolve_config(self, manifest: PluginManifest) -> dict[str, Any]:
        """
        Resolve plugin configuration by extracting defaults from the
        manifest's JSON Schema config_schema.

        DB overrides are merged at request time in the REST API layer
        (routes.py) where an async DB session is available.
        """
        config: dict[str, Any] = {}
        schema = manifest.config_schema
        properties = schema.get("properties", {})
        for key, prop_def in properties.items():
            if "default" in prop_def:
                config[key] = prop_def["default"]
        return config

    async def resolve_config_with_overrides(
        self, manifest: PluginManifest, overrides: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Merge manifest defaults with user-provided DB overrides.

        Args:
            manifest: Plugin manifest (provides config_schema defaults).
            overrides: Dict of user config overrides from the plugin_config table.

        Returns:
            Merged configuration dict.
        """
        config = self._resolve_config(manifest)
        config.update(overrides)
        return config
