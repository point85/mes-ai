"""
PLUGIN-FW: Plugin lifecycle manager.

Plugin lifecycle:
    available → installed (parameter values provided) → enabled (running) → disabled → uninstalled

Two plugin directories:
    - system: plugins created by project contributors (PLUGIN_DIR)
    - user:   plugins created by end users (PLUGIN_USER_DIR)

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

from mes.framework.events import event_bus

from .base import MESPlugin
from .manifest import PluginManifest

logger = logging.getLogger("mes.plugin")


class PluginInfo:
    """Runtime state for a discovered plugin."""

    def __init__(
        self,
        manifest: PluginManifest,
        path: Path,
        instance: MESPlugin | None = None,
    ) -> None:
        self.manifest = manifest
        self.path = path
        self.instance = instance
        self.is_loaded: bool = False
        self.is_running: bool = False
        self.error: str | None = None


class PluginManager:
    """
    Manages plugin discovery, installation, lifecycle, and extension point registration.

    Scans both system and user plugin directories. Only installed+enabled plugins
    are loaded and started at boot time.

    Usage:
        manager = PluginManager()
        await manager.discover_all()       # Scans both directories for manifests
        await manager.load_and_start()     # Loads + starts installed & enabled plugins
        await manager.stop_all()           # Stops all running plugins

    Install/uninstall/enable/disable are triggered via REST API or CLI and update DB state.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, PluginInfo] = {}

    @property
    def plugins(self) -> dict[str, PluginInfo]:
        """Returns the registry of all discovered plugins keyed by plugin ID."""
        return dict(self._plugins)

    # ── Discovery ─────────────────────────────────────────────────────

    async def discover_all(self) -> list[str]:
        """
        Scan system and user plugin directories for plugins with manifest.yaml.
        Populates self._plugins with PluginInfo (manifest + path only, not loaded).

        Returns:
            List of discovered plugin IDs.
        """
        discovered: list[str] = []

        for plugin_dir, origin in [
            (Path("plugins/system"), "system"),
            (Path("plugins/user"), "user"),
        ]:
            if not plugin_dir.exists():
                logger.info("Plugin directory '%s' does not exist, skipping", plugin_dir)
                continue

            for candidate in sorted(plugin_dir.iterdir()):
                if not candidate.is_dir():
                    continue

                manifest_path = candidate / "manifest.yaml"
                if not manifest_path.exists():
                    logger.debug("Skipping '%s' — no manifest.yaml found", candidate.name)
                    continue

                try:
                    manifest = PluginManifest.from_yaml(manifest_path)
                    # Enforce the origin based on which directory it lives in
                    manifest.origin = origin
                    if manifest.id in self._plugins:
                        logger.warning(
                            "Duplicate plugin '%s' found in %s — ignoring",
                            manifest.id,
                            candidate,
                        )
                        continue
                    self._plugins[manifest.id] = PluginInfo(
                        manifest=manifest,
                        path=candidate,
                    )
                    discovered.append(manifest.id)
                except Exception as exc:
                    logger.error(
                        "Failed to parse manifest in '%s': %s",
                        candidate.name,
                        exc,
                        exc_info=True,
                    )

        logger.info("Discovered %d plugin(s): %s", len(discovered), discovered)
        return discovered

    # ── Loading & Starting (for installed+enabled plugins) ─────────────

    async def load_and_start(
        self, installed_ids: set[str] | dict[str, dict[str, Any]] | None = None,
    ) -> list[str]:
        """
        Load and start all plugins that are installed + enabled.

        Args:
            installed_ids: Either
                - a set of plugin IDs that are installed+enabled in DB, or
                - a mapping of plugin_id -> config dict (parameter_values merged
                  with config_overrides) so user-supplied values reach
                  ``initialize(config)`` on server restart.
                If None, loads ALL discovered plugins (backward compat).

        Returns:
            List of successfully started plugin IDs.
        """
        started: list[str] = []
        id_filter: set[str] | None
        config_map: dict[str, dict[str, Any]]
        if installed_ids is None:
            id_filter = None
            config_map = {}
        elif isinstance(installed_ids, dict):
            id_filter = set(installed_ids.keys())
            config_map = installed_ids
        else:
            id_filter = installed_ids
            config_map = {}

        for plugin_id, info in self._plugins.items():
            if id_filter is not None and plugin_id not in id_filter:
                continue
            try:
                # Propagate persisted configuration so initialize() sees the
                # same values the user entered via the DT-CLIENT.
                if plugin_id in config_map:
                    info._parameter_values = config_map[plugin_id]  # type: ignore[attr-defined]
                await self._load_plugin(info)
                await self._start_plugin(plugin_id, info)
                started.append(plugin_id)
            except Exception as exc:
                info.error = str(exc)
                logger.error(
                    "Failed to load/start plugin '%s': %s",
                    plugin_id,
                    exc,
                    exc_info=True,
                )
        return started

    async def _load_plugin(self, info: PluginInfo) -> None:
        """Load a single plugin: import module, instantiate, initialize."""
        if info.is_loaded:
            return

        plugin_path = info.path
        manifest = info.manifest
        plugin_id = manifest.id

        # Check dependencies
        for dep_id in manifest.dependencies:
            dep = self._plugins.get(dep_id)
            if dep is None or not dep.is_loaded:
                raise ValueError(
                    f"Plugin '{plugin_id}' requires '{dep_id}' which is not loaded"
                )

        # Load Python module as a package so relative imports work
        plugin_module_path = plugin_path / "plugin.py"
        if not plugin_module_path.exists():
            raise FileNotFoundError(f"Plugin entry point not found: {plugin_module_path}")

        package_name = f"mes_plugin_{plugin_id.replace('-', '_')}"
        module_name = f"{package_name}.plugin"

        # Register parent directory on sys.path so sub-modules are importable
        parent_dir = str(plugin_path.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        # Create a virtual package for the plugin directory
        pkg_init = plugin_path / "__init__.py"
        pkg_spec = importlib.util.spec_from_file_location(
            package_name,
            str(pkg_init) if pkg_init.exists() else None,
            submodule_search_locations=[str(plugin_path)],
        )
        if pkg_spec is not None:
            pkg_module = importlib.util.module_from_spec(pkg_spec)
            sys.modules[package_name] = pkg_module
            if pkg_spec.loader is not None and pkg_init.exists():
                pkg_spec.loader.exec_module(pkg_module)

        # Load plugin.py as a sub-module of the package
        spec = importlib.util.spec_from_file_location(
            module_name, plugin_module_path,
            submodule_search_locations=[],
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot create module spec for {plugin_module_path}")

        module = importlib.util.module_from_spec(spec)
        module.__package__ = package_name
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Find and instantiate MESPlugin subclass
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

        # Initialize with resolved config (manifest defaults + parameter_values set by enable_plugin)
        config = self._resolve_config(manifest)
        parameter_values = getattr(info, "_parameter_values", None)
        if parameter_values:
            config.update(parameter_values)
        await instance.initialize(config)

        # Register event handlers
        event_handlers = instance.get_event_handlers()
        if event_handlers:
            for topic, handler in event_handlers.items():
                event_bus.subscribe(topic, handler)
                logger.debug(
                    "Plugin '%s': registered event handler for '%s'",
                    plugin_id,
                    topic,
                )

        info.instance = instance
        info.is_loaded = True
        info.error = None
        logger.info("Loaded plugin '%s' v%s", plugin_id, manifest.version)

    async def _start_plugin(self, plugin_id: str, info: PluginInfo) -> None:
        """Start a loaded plugin."""
        if not info.is_loaded or info.instance is None:
            raise RuntimeError(f"Plugin '{plugin_id}' is not loaded")
        if info.is_running:
            return

        await info.instance.start()
        info.is_running = True
        info.error = None
        logger.info("Started plugin '%s'", plugin_id)

        from mes.framework.events import MESEvent
        await event_bus.publish(
            MESEvent(
                event_type="plugin.loaded",
                source="PLUGIN-FW",
                payload={"plugin_id": plugin_id, "version": info.manifest.version},
            )
        )

    # ── Stop ──────────────────────────────────────────────────────────

    async def stop_plugin(self, plugin_id: str) -> None:
        """Stop a single running plugin."""
        info = self._plugins.get(plugin_id)
        if info is None or not info.is_running or info.instance is None:
            return
        try:
            await info.instance.stop()
            info.is_running = False
            logger.info("Stopped plugin '%s'", plugin_id)
        except Exception as exc:
            logger.error("Error stopping plugin '%s': %s", plugin_id, exc, exc_info=True)

    async def stop_all(self) -> None:
        """Stop all running plugins in reverse discovery order."""
        for plugin_id in reversed(list(self._plugins.keys())):
            await self.stop_plugin(plugin_id)

    # ── Enable/Disable (runtime, after DB state changes) ──────────────

    async def enable_plugin(self, plugin_id: str, parameter_values: dict[str, Any] | None = None) -> None:
        """Load and start a plugin at runtime (after it's been installed in DB)."""
        info = self._plugins.get(plugin_id)
        if info is None:
            raise ValueError(f"Plugin '{plugin_id}' not found")
        if info.is_running:
            return

        # Reset any stale startup error so a new enable attempt reports the
        # current outcome rather than a previous failure.
        info.error = None

        # Apply parameter values to config resolution if provided
        if parameter_values:
            # Store for config resolution
            info._parameter_values = parameter_values  # type: ignore[attr-defined]

        if info.is_loaded and info.instance is not None:
            # Plugin was previously loaded (then disabled). Re-initialize with the
            # latest config so settings (e.g. auth_type) reflect the current values.
            config = self._resolve_config(info.manifest)
            pv = getattr(info, "_parameter_values", None)
            if pv:
                config.update(pv)
            await info.instance.initialize(config)
        else:
            await self._load_plugin(info)
        await self._start_plugin(plugin_id, info)

    async def disable_plugin(self, plugin_id: str) -> None:
        """Stop a running plugin at runtime."""
        await self.stop_plugin(plugin_id)

    # ── Routes ────────────────────────────────────────────────────────

    async def get_plugin_routes(self) -> list:
        """Collect all FastAPI routers from loaded plugins."""
        routers = []
        for plugin_id, info in self._plugins.items():
            if not info.is_loaded or info.instance is None:
                continue
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

    # ── Query ─────────────────────────────────────────────────────────

    def get_plugin(self, plugin_id: str) -> PluginInfo | None:
        """Get a discovered plugin's info by ID."""
        return self._plugins.get(plugin_id)

    def is_loaded(self, plugin_id: str) -> bool:
        """Check if a plugin is loaded."""
        info = self._plugins.get(plugin_id)
        return info is not None and info.is_loaded

    # ── Config Resolution ─────────────────────────────────────────────

    def _resolve_config(self, manifest: PluginManifest) -> dict[str, Any]:
        """
        Resolve plugin configuration from manifest parameters and legacy config_schema.

        Priority: parameter defaults → config_schema defaults → parameter_values override.
        """
        config: dict[str, Any] = {}

        # Legacy config_schema defaults
        schema = manifest.config_schema
        properties = schema.get("properties", {})
        for key, prop_def in properties.items():
            if "default" in prop_def:
                config[key] = prop_def["default"]

        # New-style parameter defaults
        for param in manifest.parameters:
            if param.default is not None:
                config[param.name] = param.default

        return config

    async def resolve_config_with_overrides(
        self, manifest: PluginManifest, parameter_values: dict[str, Any],
        config_overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Merge manifest defaults with user parameter values and config overrides.

        Args:
            manifest: Plugin manifest (provides defaults).
            parameter_values: User-provided parameter values from install.
            config_overrides: Additional runtime overrides.

        Returns:
            Merged configuration dict.
        """
        config = self._resolve_config(manifest)
        config.update(parameter_values)
        if config_overrides:
            config.update(config_overrides)
        return config

    def validate_parameters(self, manifest: PluginManifest, parameter_values: dict[str, Any]) -> list[str]:
        """
        Validate that all required parameters are provided.

        Returns:
            List of error messages (empty if valid).
        """
        errors: list[str] = []
        for param in manifest.parameters:
            if param.required and param.name not in parameter_values:
                errors.append(f"Required parameter '{param.name}' is missing")
        return errors

    # ── Adapter Access ────────────────────────────────────────────────

    def get_adapter_by_type(self, adapter_type: str) -> Any:
        """
        Find the running plugin that provides the given adapter extension point
        type and return its adapter instance.

        Args:
            adapter_type: Extension point type (e.g. "erp_inbound", "equipment_driver").

        Returns:
            The adapter instance, or None if no running plugin provides it.
        """
        for info in self._iter_adapter_plugins(adapter_type):
            adapter = info.instance.get_adapter()
            if isinstance(adapter, dict):
                return adapter.get(adapter_type)
            return adapter
        return None

    def get_preferred_adapter_by_type(self, adapter_type: str, plugin_id: str | None = None) -> Any:
        """Return an adapter, optionally preferring a specific plugin ID."""
        for info in self._iter_adapter_plugins(adapter_type, preferred_plugin_id=plugin_id):
            adapter = info.instance.get_adapter()
            if isinstance(adapter, dict):
                return adapter.get(adapter_type)
            return adapter
        return None

    def get_adapter_plugin(self, adapter_type: str) -> "PluginInfo | None":
        """
        Find the running plugin that provides the given adapter type.

        Returns:
            PluginInfo for the adapter plugin, or None.
        """
        for info in self._iter_adapter_plugins(adapter_type):
            return info
        return None

    def get_preferred_adapter_plugin(
        self,
        adapter_type: str,
        plugin_id: str | None = None,
    ) -> "PluginInfo | None":
        """Return the plugin providing an adapter, optionally preferring a plugin ID."""
        for info in self._iter_adapter_plugins(adapter_type, preferred_plugin_id=plugin_id):
            return info
        return None

    def _iter_adapter_plugins(
        self,
        adapter_type: str,
        preferred_plugin_id: str | None = None,
    ):
        preferred: list[PluginInfo] = []
        primary: list[PluginInfo] = []
        simulator: list[PluginInfo] = []

        for info in self._plugins.values():
            if not info.is_running or info.instance is None:
                continue
            for ep in info.manifest.extension_points:
                if ep.type == adapter_type:
                    if preferred_plugin_id and info.manifest.id == preferred_plugin_id:
                        preferred.append(info)
                    elif self._is_erp_simulator_plugin(info):
                        simulator.append(info)
                    else:
                        primary.append(info)
                    break

        ordered = preferred + primary + simulator
        for info in ordered:
            yield info

    @staticmethod
    def _is_erp_simulator_plugin(info: "PluginInfo") -> bool:
        return info.manifest.category == "erp" and info.manifest.id.endswith("-simulator")

    async def adapter_health(self) -> dict[str, bool]:
        """Check health of all running adapter plugins."""
        results: dict[str, bool] = {}
        adapter_types = {
            "erp_inbound", "erp_outbound", "equipment_driver", "test_equipment",
        }
        for info in self._plugins.values():
            if not info.is_running or info.instance is None:
                continue
            has_adapter = any(
                ep.type in adapter_types for ep in info.manifest.extension_points
            )
            if has_adapter:
                try:
                    results[info.manifest.id] = await info.instance.health_check()
                except Exception:
                    results[info.manifest.id] = False
        return results
