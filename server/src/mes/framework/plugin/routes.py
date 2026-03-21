"""
PLUGIN-FW: REST API routes for plugin management.

Plugin lifecycle: available → installed → enabled/disabled → uninstalled

Endpoints:
    GET   /api/v1/plugins                         — List all plugins (available + installed)
    GET   /api/v1/plugins/{plugin_id}             — Get plugin detail + config
    POST  /api/v1/plugins/{plugin_id}/install     — Install a plugin (provide parameter values)
    POST  /api/v1/plugins/{plugin_id}/uninstall   — Uninstall a plugin
    POST  /api/v1/plugins/{plugin_id}/enable      — Enable an installed plugin
    POST  /api/v1/plugins/{plugin_id}/disable     — Disable a running plugin
    PUT   /api/v1/plugins/{plugin_id}/config      — Update plugin config overrides
    GET   /api/v1/plugins/catalog                 — List available adapter types
"""

from __future__ import annotations

import importlib
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.responses import list_response, success_response
from mes.framework.db import get_db_session

from .models import PluginConfig
from .schemas import (
    AdapterInfo,
    ParameterSchema,
    PluginConfigUpdate,
    PluginDetail,
    PluginEnableRequest,
    PluginInstallRequest,
    PluginSummary,
)

logger = logging.getLogger("mes.plugin.routes")

router = APIRouter(prefix="/api/v1/plugins", tags=["Plugins"])


# ─── Adapter catalog ─────────────────────────────────────────────────

ADAPTER_CATALOG: list[dict[str, Any]] = [
    {
        "type": "mock",
        "category": "erp",
        "description": "In-memory mock ERP adapter for testing",
        "install_extra": None,
        "check_import": None,
    },
    {
        "type": "sap_s4hana",
        "category": "erp",
        "description": "SAP S/4HANA integration via RFC/OData",
        "install_extra": "sap",
        "check_import": "pyrfc",
    },
    {
        "type": "oracle",
        "category": "erp",
        "description": "Oracle Cloud ERP integration via REST",
        "install_extra": "oracle",
        "check_import": "oracledb",
    },
    {
        "type": "mock",
        "category": "equipment",
        "description": "In-memory mock equipment adapter for testing",
        "install_extra": None,
        "check_import": None,
    },
    {
        "type": "opcua",
        "category": "equipment",
        "description": "OPC-UA equipment integration",
        "install_extra": "opcua",
        "check_import": "asyncua",
    },
    {
        "type": "mqtt",
        "category": "equipment",
        "description": "MQTT equipment integration",
        "install_extra": "mqtt",
        "check_import": "aiomqtt",
    },
    {
        "type": "modbus",
        "category": "equipment",
        "description": "Modbus TCP equipment integration",
        "install_extra": "modbus",
        "check_import": "pymodbus",
    },
]


def _is_importable(module_name: str | None) -> bool:
    """Check if a Python module can be imported without side effects."""
    if module_name is None:
        return True
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


# ─── Helper: get or create DB config row for a plugin ─────────────────


async def _get_or_create_plugin_config(
    session: AsyncSession, plugin_id: str
) -> PluginConfig:
    """Fetch existing PluginConfig or create a default row."""
    result = await session.execute(
        select(PluginConfig).where(
            PluginConfig.plugin_id == plugin_id,
            PluginConfig.is_active.is_(True),
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = PluginConfig(
            plugin_id=plugin_id,
            installed=False,
            enabled=False,
            parameter_values={},
            config_overrides={},
        )
        session.add(row)
        await session.flush()
    return row


# ─── Routes ──────────────────────────────────────────────────────────


@router.get("/catalog")
async def list_adapter_catalog():
    """List all available adapter types and whether their dependencies are installed."""
    items = []
    for entry in ADAPTER_CATALOG:
        items.append(
            AdapterInfo(
                type=entry["type"],
                category=entry["category"],
                description=entry["description"],
                install_extra=entry["install_extra"],
                is_installed=_is_importable(entry["check_import"]),
            ).model_dump()
        )
    return list_response(items)


@router.get("")
async def list_plugins(
    session: AsyncSession = Depends(get_db_session),
):
    """List all discovered plugins with their status (available, installed, enabled)."""
    from mes.main import plugin_manager

    # Get DB config rows indexed by plugin_id
    db_configs: dict[str, PluginConfig] = {}
    result = await session.execute(
        select(PluginConfig).where(PluginConfig.is_active.is_(True))
    )
    for row in result.scalars().all():
        db_configs[row.plugin_id] = row

    summaries = []
    for plugin_id, info in plugin_manager.plugins.items():
        db_cfg = db_configs.get(plugin_id)
        summaries.append(
            PluginSummary(
                id=info.manifest.id,
                name=info.manifest.name,
                version=info.manifest.version,
                description=info.manifest.description,
                author=info.manifest.author,
                comment=info.manifest.comment,
                category=info.manifest.category,
                origin=info.manifest.origin,
                installed=db_cfg.installed if db_cfg else False,
                enabled=db_cfg.enabled if db_cfg else False,
                is_loaded=info.is_loaded,
                is_running=info.is_running,
                error=info.error,
                extension_points=[
                    ep.type for ep in info.manifest.extension_points
                ],
            ).model_dump()
        )
    return list_response(summaries)


@router.get("/{plugin_id}")
async def get_plugin_detail(
    plugin_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get detailed information about a specific plugin."""
    from mes.main import plugin_manager

    info = plugin_manager.get_plugin(plugin_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    db_cfg = await _get_or_create_plugin_config(session, plugin_id)
    await session.commit()

    # Merge config: manifest defaults + parameter values + DB overrides
    resolved_config = await plugin_manager.resolve_config_with_overrides(
        info.manifest, db_cfg.parameter_values, db_cfg.config_overrides,
    )

    # Build parameter schema list for UI
    param_schemas = [
        ParameterSchema(
            name=p.name,
            type=p.type,
            description=p.description,
            required=p.required,
            default=p.default,
            secret=p.secret,
        ).model_dump()
        for p in info.manifest.parameters
    ]

    detail = PluginDetail(
        id=info.manifest.id,
        name=info.manifest.name,
        version=info.manifest.version,
        description=info.manifest.description,
        author=info.manifest.author,
        comment=info.manifest.comment,
        category=info.manifest.category,
        origin=info.manifest.origin,
        installed=db_cfg.installed,
        enabled=db_cfg.enabled,
        is_loaded=info.is_loaded,
        is_running=info.is_running,
        error=info.error,
        extension_points=[ep.type for ep in info.manifest.extension_points],
        min_mes_version=info.manifest.min_mes_version,
        parameters=param_schemas,
        parameter_values=db_cfg.parameter_values,
        permissions=[
            {"id": p.id, "description": p.description}
            for p in info.manifest.permissions
        ],
        required_core_permissions=info.manifest.required_core_permissions,
        event_subscriptions=info.manifest.event_subscriptions,
        dependencies=info.manifest.dependencies,
        config_schema=info.manifest.config_schema,
        config_values=resolved_config,
        notes=db_cfg.notes,
    )
    return success_response(detail.model_dump())


@router.post("/{plugin_id}/install")
async def install_plugin(
    plugin_id: str,
    body: PluginInstallRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Install a plugin by providing parameter values.
    Validates that all required parameters are present.
    """
    from mes.main import plugin_manager

    info = plugin_manager.get_plugin(plugin_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    param_values = body.parameter_values if body else {}
    notes = body.notes if body else None

    # Validate required parameters
    errors = plugin_manager.validate_parameters(info.manifest, param_values)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    db_cfg = await _get_or_create_plugin_config(session, plugin_id)
    db_cfg.installed = True
    db_cfg.enabled = False  # Installed but not yet enabled
    db_cfg.parameter_values = param_values
    if notes is not None:
        db_cfg.notes = notes
    await session.commit()

    logger.info("Installed plugin '%s'", plugin_id)
    return success_response({
        "plugin_id": plugin_id,
        "installed": True,
        "enabled": False,
        "parameter_values": param_values,
    })


@router.post("/{plugin_id}/uninstall")
async def uninstall_plugin(
    plugin_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Uninstall a plugin — stops it if running, clears DB state."""
    from mes.main import plugin_manager

    info = plugin_manager.get_plugin(plugin_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    # Stop if running
    if info.is_running:
        await plugin_manager.disable_plugin(plugin_id)

    # Clear DB state
    db_cfg = await _get_or_create_plugin_config(session, plugin_id)
    db_cfg.installed = False
    db_cfg.enabled = False
    db_cfg.parameter_values = {}
    db_cfg.config_overrides = {}
    await session.commit()

    logger.info("Uninstalled plugin '%s'", plugin_id)
    return success_response({"plugin_id": plugin_id, "installed": False})


@router.post("/{plugin_id}/enable")
async def enable_plugin_route(
    plugin_id: str,
    body: PluginEnableRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    """Enable an installed plugin — loads and starts it."""
    from mes.main import plugin_manager

    info = plugin_manager.get_plugin(plugin_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    db_cfg = await _get_or_create_plugin_config(session, plugin_id)
    if not db_cfg.installed:
        raise HTTPException(
            status_code=422,
            detail=f"Plugin '{plugin_id}' must be installed before enabling",
        )

    db_cfg.enabled = True
    if body and body.notes is not None:
        db_cfg.notes = body.notes
    await session.commit()

    # Load and start the plugin at runtime
    try:
        await plugin_manager.enable_plugin(plugin_id, db_cfg.parameter_values)
    except Exception as exc:
        info.error = str(exc)
        logger.error("Failed to enable plugin '%s': %s", plugin_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))

    logger.info("Enabled plugin '%s'", plugin_id)
    return success_response({"plugin_id": plugin_id, "enabled": True})


@router.post("/{plugin_id}/disable")
async def disable_plugin_route(
    plugin_id: str,
    body: PluginEnableRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    """Disable a running plugin — stops it."""
    from mes.main import plugin_manager

    info = plugin_manager.get_plugin(plugin_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    db_cfg = await _get_or_create_plugin_config(session, plugin_id)
    db_cfg.enabled = False
    if body and body.notes is not None:
        db_cfg.notes = body.notes
    await session.commit()

    await plugin_manager.disable_plugin(plugin_id)

    logger.info("Disabled plugin '%s'", plugin_id)
    return success_response({"plugin_id": plugin_id, "enabled": False})


@router.put("/{plugin_id}/config")
async def update_plugin_config(
    plugin_id: str,
    body: PluginConfigUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    """Update configuration overrides for an installed plugin."""
    from mes.main import plugin_manager

    info = plugin_manager.get_plugin(plugin_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    db_cfg = await _get_or_create_plugin_config(session, plugin_id)
    db_cfg.config_overrides = body.config_overrides
    if body.notes is not None:
        db_cfg.notes = body.notes
    await session.commit()

    logger.info("Updated config for plugin '%s': %s", plugin_id, body.config_overrides)
    return success_response({"plugin_id": plugin_id, "config_overrides": db_cfg.config_overrides})
