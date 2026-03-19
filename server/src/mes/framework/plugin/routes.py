"""
PLUGIN-FW: REST API routes for plugin management.

Endpoints:
    GET  /api/v1/plugins              — List all discovered plugins
    GET  /api/v1/plugins/{plugin_id}  — Get plugin detail + config
    PUT  /api/v1/plugins/{plugin_id}/config   — Update plugin config overrides
    POST /api/v1/plugins/{plugin_id}/enable   — Enable a plugin
    POST /api/v1/plugins/{plugin_id}/disable  — Disable a plugin
    GET  /api/v1/plugins/catalog      — List available adapter types
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
    PluginConfigUpdate,
    PluginDetail,
    PluginEnableRequest,
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
        row = PluginConfig(plugin_id=plugin_id, enabled=True, config_overrides={})
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
    """List all discovered plugins with their status."""
    from mes.main import plugin_manager

    summaries = []
    # Get DB config rows indexed by plugin_id
    db_configs: dict[str, PluginConfig] = {}
    result = await session.execute(
        select(PluginConfig).where(PluginConfig.is_active.is_(True))
    )
    for row in result.scalars().all():
        db_configs[row.plugin_id] = row

    for plugin_id, info in plugin_manager.plugins.items():
        db_cfg = db_configs.get(plugin_id)
        summaries.append(
            PluginSummary(
                id=info.manifest.id,
                name=info.manifest.name,
                version=info.manifest.version,
                description=info.manifest.description,
                author=info.manifest.author,
                is_loaded=True,
                is_running=info.is_running,
                enabled=db_cfg.enabled if db_cfg else True,
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

    # Merge config: manifest defaults + DB overrides
    resolved_config = plugin_manager._resolve_config(info.manifest)
    resolved_config.update(db_cfg.config_overrides)

    detail = PluginDetail(
        id=info.manifest.id,
        name=info.manifest.name,
        version=info.manifest.version,
        description=info.manifest.description,
        author=info.manifest.author,
        is_loaded=True,
        is_running=info.is_running,
        enabled=db_cfg.enabled,
        error=info.error,
        extension_points=[ep.type for ep in info.manifest.extension_points],
        min_mes_version=info.manifest.min_mes_version,
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


@router.put("/{plugin_id}/config")
async def update_plugin_config(
    plugin_id: str,
    body: PluginConfigUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    """Update configuration overrides for a plugin."""
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


@router.post("/{plugin_id}/enable")
async def enable_plugin(
    plugin_id: str,
    body: PluginEnableRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    """Enable a plugin (will be started on next boot or immediately if loaded)."""
    from mes.main import plugin_manager

    info = plugin_manager.get_plugin(plugin_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    db_cfg = await _get_or_create_plugin_config(session, plugin_id)
    db_cfg.enabled = True
    if body and body.notes is not None:
        db_cfg.notes = body.notes
    await session.commit()

    # If loaded but not running, start it now
    if not info.is_running:
        try:
            await info.instance.start()
            info.is_running = True
            logger.info("Plugin '%s' enabled and started", plugin_id)
        except Exception as exc:
            info.error = str(exc)
            logger.error("Plugin '%s' enabled but failed to start: %s", plugin_id, exc)

    return success_response({"plugin_id": plugin_id, "enabled": True, "is_running": info.is_running})


@router.post("/{plugin_id}/disable")
async def disable_plugin(
    plugin_id: str,
    body: PluginEnableRequest | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    """Disable a plugin (stops it immediately if running)."""
    from mes.main import plugin_manager

    info = plugin_manager.get_plugin(plugin_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")

    db_cfg = await _get_or_create_plugin_config(session, plugin_id)
    db_cfg.enabled = False
    if body and body.notes is not None:
        db_cfg.notes = body.notes
    await session.commit()

    # Stop the plugin if running
    if info.is_running:
        try:
            await info.instance.stop()
            info.is_running = False
            logger.info("Plugin '%s' disabled and stopped", plugin_id)
        except Exception as exc:
            logger.error("Plugin '%s' disable error during stop: %s", plugin_id, exc)

    return success_response({"plugin_id": plugin_id, "enabled": False, "is_running": info.is_running})
