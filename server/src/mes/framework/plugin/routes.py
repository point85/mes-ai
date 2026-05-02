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
    GET   /api/v1/plugins/catalog                 — List available adapter plugins
"""

from __future__ import annotations

import logging
import subprocess
import sys
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mes.framework.api.responses import list_response, success_response
from mes.framework.db import get_db_session

from .models import PluginConfig
from .schemas import (
    AdapterInfo,
    CompanionInfo,
    ParameterSchema,
    PluginConfigUpdate,
    PluginDetail,
    PluginEnableRequest,
    PluginInstallRequest,
    PluginSummary,
)

logger = logging.getLogger("mes.plugin.routes")

router = APIRouter(prefix="/api/v1/plugins", tags=["Plugins"])

# Adapter extension-point types used to identify adapter plugins in the catalog.
_ADAPTER_EP_TYPES = frozenset({
    "erp_inbound", "erp_outbound", "equipment_driver", "test_equipment",
})


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


# ─── Companion cascade helpers ────────────────────────────────────────


async def _build_companion_infos(
    pm: Any, companions: list, session: AsyncSession,
) -> list[dict[str, Any]]:
    """Build CompanionInfo dicts for a plugin's companion list."""
    infos = []
    for c in companions:
        ci = CompanionInfo(
            id=c.id, type=c.type, name=c.name,
            path=c.path, dev_port=c.dev_port, description=c.description,
        )
        if c.type == "plugin":
            comp_cfg = await _get_or_create_plugin_config(session, c.id)
            ci.installed = comp_cfg.installed
            ci.enabled = comp_cfg.enabled
        infos.append(ci.model_dump())
    return infos


async def _cascade_install_companions(
    pm: Any, companions: list, session: AsyncSession,
) -> list[str]:
    """Install plugin-type companions that aren't already installed."""
    installed = []
    for c in companions:
        if c.type != "plugin":
            continue
        comp_info = pm.get_plugin(c.id)
        if comp_info is None:
            logger.warning("Companion plugin '%s' not found — skipping", c.id)
            continue
        comp_cfg = await _get_or_create_plugin_config(session, c.id)
        if not comp_cfg.installed:
            comp_cfg.installed = True
            comp_cfg.enabled = False
            installed.append(c.id)
            logger.info("Cascade-installed companion plugin '%s'", c.id)
    return installed


async def _cascade_enable_companions(
    pm: Any, companions: list, session: AsyncSession,
) -> list[str]:
    """Enable plugin-type companions that are installed but not yet enabled."""
    enabled = []
    for c in companions:
        if c.type != "plugin":
            continue
        comp_info = pm.get_plugin(c.id)
        if comp_info is None:
            continue
        comp_cfg = await _get_or_create_plugin_config(session, c.id)
        if comp_cfg.installed and not comp_cfg.enabled:
            comp_cfg.enabled = True
            try:
                await pm.enable_plugin(c.id, comp_cfg.parameter_values)
                enabled.append(c.id)
                logger.info("Cascade-enabled companion plugin '%s'", c.id)
            except Exception as exc:
                logger.warning("Failed to cascade-enable '%s': %s", c.id, exc)
    return enabled


async def _cascade_uninstall_companions(
    pm: Any, companions: list, session: AsyncSession,
) -> list[str]:
    """Uninstall plugin-type companions."""
    uninstalled = []
    for c in companions:
        if c.type != "plugin":
            continue
        comp_info = pm.get_plugin(c.id)
        if comp_info is None:
            continue
        if comp_info.is_running:
            await pm.disable_plugin(c.id)
        comp_cfg = await _get_or_create_plugin_config(session, c.id)
        if comp_cfg.installed:
            comp_cfg.installed = False
            comp_cfg.enabled = False
            comp_cfg.parameter_values = {}
            comp_cfg.config_overrides = {}
            uninstalled.append(c.id)
            logger.info("Cascade-uninstalled companion plugin '%s'", c.id)
    return uninstalled


async def _cascade_disable_companions(
    pm: Any, companions: list, session: AsyncSession,
) -> list[str]:
    """Disable plugin-type companions."""
    disabled = []
    for c in companions:
        if c.type != "plugin":
            continue
        comp_info = pm.get_plugin(c.id)
        if comp_info is None:
            continue
        comp_cfg = await _get_or_create_plugin_config(session, c.id)
        if comp_cfg.enabled:
            comp_cfg.enabled = False
            await pm.disable_plugin(c.id)
            disabled.append(c.id)
            logger.info("Cascade-disabled companion plugin '%s'", c.id)
    return disabled


# ─── Routes ──────────────────────────────────────────────────────────


@router.get("/catalog")
async def list_adapter_catalog():
    """List all discovered adapter plugins and their status."""
    from mes.main import plugin_manager

    items = []
    for plugin_id, info in plugin_manager.plugins.items():
        ep_types = {ep.type for ep in info.manifest.extension_points}
        if not ep_types & _ADAPTER_EP_TYPES:
            continue
        # Derive category from extension point types
        if ep_types & {"erp_inbound", "erp_outbound"}:
            category = "erp"
        elif "test_equipment" in ep_types:
            category = "test_equipment"
        else:
            category = "equipment"
        items.append(
            AdapterInfo(
                type=info.manifest.id,
                category=category,
                description=info.manifest.description or info.manifest.name,
                install_extra=None,
                is_installed=info.is_loaded,
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
            items=[
                ParameterSchema(
                    name=item.name,
                    type=item.type,
                    description=item.description,
                    required=item.required,
                    default=item.default,
                    secret=item.secret,
                )
                for item in p.items
            ],
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
        companions=await _build_companion_infos(
            plugin_manager, info.manifest.companions, session,
        ),
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

    # Auto-install Python dependencies declared in manifest
    pip_deps = info.manifest.pip_dependencies
    if pip_deps:
        logger.info("Installing Python dependencies: %s", pip_deps)
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", *pip_deps, "--quiet"],
                timeout=120,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to install Python dependencies {pip_deps}: {exc}",
            )

    db_cfg = await _get_or_create_plugin_config(session, plugin_id)
    db_cfg.installed = True
    db_cfg.enabled = False  # Installed but not yet enabled
    db_cfg.parameter_values = param_values
    if notes is not None:
        db_cfg.notes = notes
    await session.flush()

    # Cascade install to plugin-type companions
    companions_installed = await _cascade_install_companions(
        plugin_manager, info.manifest.companions, session,
    )
    await session.commit()

    logger.info("Installed plugin '%s'", plugin_id)
    result: dict[str, Any] = {
        "plugin_id": plugin_id,
        "installed": True,
        "enabled": False,
        "parameter_values": param_values,
    }
    if companions_installed:
        result["companions_installed"] = companions_installed
    # Report client-type companions for user info
    client_companions = [
        {"id": c.id, "name": c.name, "path": c.path, "dev_port": c.dev_port}
        for c in info.manifest.companions if c.type == "client"
    ]
    if client_companions:
        result["client_apps"] = client_companions
    return success_response(result)


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
    await session.flush()

    # Cascade uninstall to plugin-type companions
    companions_uninstalled = await _cascade_uninstall_companions(
        plugin_manager, info.manifest.companions, session,
    )
    await session.commit()

    logger.info("Uninstalled plugin '%s'", plugin_id)
    result: dict[str, Any] = {"plugin_id": plugin_id, "installed": False}
    if companions_uninstalled:
        result["companions_uninstalled"] = companions_uninstalled
    return success_response(result)


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

    # Validate required parameters before enabling — consider both install-time
    # parameter_values and runtime config_overrides (saved via "Save Configuration").
    effective_values = {**(db_cfg.parameter_values or {}), **(db_cfg.config_overrides or {})}
    errors = plugin_manager.validate_parameters(info.manifest, effective_values)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})

    db_cfg.enabled = True
    if body and body.notes is not None:
        db_cfg.notes = body.notes
    await session.flush()

    # Load and start the plugin at runtime
    try:
        await plugin_manager.enable_plugin(plugin_id, effective_values)
    except Exception as exc:
        info.error = str(exc)
        logger.error("Failed to enable plugin '%s': %s", plugin_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))

    # Cascade enable to plugin-type companions
    companions_enabled = await _cascade_enable_companions(
        plugin_manager, info.manifest.companions, session,
    )
    await session.commit()

    logger.info("Enabled plugin '%s'", plugin_id)
    result: dict[str, Any] = {"plugin_id": plugin_id, "enabled": True}
    if companions_enabled:
        result["companions_enabled"] = companions_enabled
    return success_response(result)


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
    await session.flush()

    await plugin_manager.disable_plugin(plugin_id)

    # Cascade disable to plugin-type companions
    companions_disabled = await _cascade_disable_companions(
        plugin_manager, info.manifest.companions, session,
    )
    await session.commit()

    logger.info("Disabled plugin '%s'", plugin_id)
    result: dict[str, Any] = {"plugin_id": plugin_id, "enabled": False}
    if companions_disabled:
        result["companions_disabled"] = companions_disabled
    return success_response(result)


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


# ── Modbus Equipment Simulator specific routes ─────────────────────────────

_PACKML_STATE_NAMES: dict[int, str] = {
    0: "Stopped",
    1: "Idle",
    2: "Execute",
    3: "Held",
    4: "Aborted",
}


class ModbusSimSetStateRequest(BaseModel):
    state_code: int = Field(..., ge=0, le=255, description="PackML state: 0=Stopped,1=Idle,2=Execute,3=Held,4=Aborted")
    unit_id: int = Field(1, ge=1, le=247, description="Modbus unit ID")


class ModbusSimSetAlarmRequest(BaseModel):
    alarm_code: int = Field(..., ge=0, le=255, description="Alarm code (0 = no alarm)")
    unit_id: int = Field(1, ge=1, le=247)


class ModbusSimSetCounterRequest(BaseModel):
    value: int = Field(..., ge=0, description="Absolute counter value to set in HR[100]")
    unit_id: int = Field(1, ge=1, le=247)


def _get_modbus_sim_plugin():
    """Return the running ModbusEquipmentSimulatorPlugin instance or raise 503."""
    from mes.main import plugin_manager

    info = plugin_manager.get_plugin("modbus-equipment-simulator")
    if info is None or not info.is_running or info.instance is None:
        raise HTTPException(
            status_code=503,
            detail="modbus-equipment-simulator plugin is not running",
        )
    return info.instance


@router.get("/modbus-equipment-simulator/status")
async def get_modbus_simulator_status():
    """Read current register snapshot from the running Modbus equipment simulator."""
    import struct

    plugin = _get_modbus_sim_plugin()
    uid = plugin._unit_id

    state_code = await plugin.get_holding_register(uid, 0)
    alarm_code = await plugin.get_holding_register(uid, 1)
    temp_hi = await plugin.get_holding_register(uid, 2)
    temp_lo = await plugin.get_holding_register(uid, 3)
    counter = await plugin.get_holding_register(uid, 100)

    try:
        temperature = round(struct.unpack(">f", struct.pack(">HH", temp_hi, temp_lo))[0], 2)
    except Exception:
        temperature = 0.0

    server_running = (
        plugin._server_task is not None and not plugin._server_task.done()
    )

    return success_response({
        "unit_id": uid,
        "state_code": state_code,
        "state_name": _PACKML_STATE_NAMES.get(state_code, f"Unknown({state_code})"),
        "alarm_code": alarm_code,
        "temperature": temperature,
        "counter": counter,
        "server_running": server_running,
    })


@router.post("/modbus-equipment-simulator/set-state")
async def modbus_simulator_set_state(body: ModbusSimSetStateRequest):
    """Set PackML state in simulator HR[0] and update the running coil."""
    plugin = _get_modbus_sim_plugin()
    await plugin.set_holding_register(body.unit_id, 0, body.state_code)
    await plugin.set_coil(body.unit_id, 0, body.state_code == 2)
    return success_response({
        "unit_id": body.unit_id,
        "state_code": body.state_code,
        "state_name": _PACKML_STATE_NAMES.get(body.state_code, f"Unknown({body.state_code})"),
    })


@router.post("/modbus-equipment-simulator/set-alarm")
async def modbus_simulator_set_alarm(body: ModbusSimSetAlarmRequest):
    """Set alarm code in simulator HR[1] and update the alarm coil."""
    plugin = _get_modbus_sim_plugin()
    await plugin.set_holding_register(body.unit_id, 1, body.alarm_code)
    await plugin.set_coil(body.unit_id, 1, body.alarm_code > 0)
    return success_response({
        "unit_id": body.unit_id,
        "alarm_code": body.alarm_code,
    })


@router.post("/modbus-equipment-simulator/set-counter")
async def modbus_simulator_set_counter(body: ModbusSimSetCounterRequest):
    """Set part counter in simulator HR[100]."""
    plugin = _get_modbus_sim_plugin()
    await plugin.set_holding_register(body.unit_id, 100, body.value)
    return success_response({
        "unit_id": body.unit_id,
        "counter": body.value,
    })
