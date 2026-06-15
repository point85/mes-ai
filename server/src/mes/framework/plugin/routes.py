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
import os
import shutil
import subprocess
import sys
from pathlib import Path
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


def _is_erp_simulator_plugin(plugin_id: str) -> bool:
    return plugin_id.endswith("-simulator")


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

    # Kafka Java Bridge: auto-inject bridge_jar from the known build output path
    # so the user never has to type a filesystem path in the DT-CLIENT form.
    if plugin_id == _KAFKA_BRIDGE_ID and not param_values.get("bridge_jar"):
        plugin_dir = _kafka_bridge_plugin_dir()
        if plugin_dir is not None:
            computed_jar = plugin_dir / _KAFKA_BRIDGE_JAR_REL
            param_values = {**param_values, "bridge_jar": str(computed_jar.resolve())}

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

    # Enforce single-active-ERP rule: only one plugin with erp_inbound/erp_outbound
    # extension points may run at a time.
    _ERP_EP_TYPES = {"erp_inbound", "erp_outbound"}
    incoming_ep_types = {ep.type for ep in info.manifest.extension_points}
    if incoming_ep_types & _ERP_EP_TYPES:
        incoming_is_simulator = _is_erp_simulator_plugin(plugin_id)
        for other_id, other_info in plugin_manager._plugins.items():
            if other_id == plugin_id:
                continue
            if not other_info.is_running:
                continue
            other_ep_types = {ep.type for ep in other_info.manifest.extension_points}
            if other_ep_types & _ERP_EP_TYPES:
                other_is_simulator = _is_erp_simulator_plugin(other_id)
                if incoming_is_simulator or other_is_simulator:
                    continue
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"ERP plugin '{other_id}' is already active. "
                        f"Disable it before enabling '{plugin_id}'."
                    ),
                )

    db_cfg.enabled = True
    if body and body.notes is not None:
        db_cfg.notes = body.notes
    await session.flush()

    # Load and start the plugin at runtime
    try:
        await plugin_manager.enable_plugin(plugin_id, effective_values)
    except Exception as exc:
        detail = str(exc) or repr(exc)
        info.error = detail
        logger.error(
            "Failed to enable plugin '%s': %s",
            plugin_id, detail, exc_info=True,
        )
        raise HTTPException(status_code=500, detail=detail)

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


def _find_mvn() -> str | None:
    """
    Locate the mvn executable.

    Search order:
      1. shutil.which with the current PATH
      2. MAVEN_HOME / M2_HOME environment variables
      3. Common Windows installation prefixes (C:\\dev_support, Program Files, etc.)
      4. /usr/local/bin, /opt/maven/bin on Linux/macOS
    """
    # 1. Standard PATH lookup (works when the server is started from a shell
    #    that already has Maven on PATH)
    mvn = shutil.which("mvn") or shutil.which("mvn.cmd")
    if mvn:
        return mvn

    # 2. Well-known environment variables set by Maven installers
    for env_var in ("MAVEN_HOME", "M2_HOME"):
        home = os.environ.get(env_var)
        if home:
            for candidate in (Path(home) / "bin" / "mvn", Path(home) / "bin" / "mvn.cmd"):
                if candidate.is_file():
                    return str(candidate)

    # 3. Scan common installation roots on Windows and POSIX
    common_roots: list[Path] = []
    if sys.platform == "win32":
        for root in ("C:\\dev_support", "C:\\Program Files", "C:\\Program Files (x86)",
                     "C:\\tools", str(Path.home())):
            common_roots.append(Path(root))
    else:
        for root in ("/usr/local", "/opt", "/usr", str(Path.home())):
            common_roots.append(Path(root))

    for root in common_roots:
        if not root.exists():
            continue
        for child in sorted(root.iterdir(), reverse=True):
            if child.is_dir() and "maven" in child.name.lower():
                for name in ("bin/mvn", "bin/mvn.cmd"):
                    candidate = child / name
                    if candidate.is_file():
                        return str(candidate)
                # One level deeper (e.g. root/maven/bin)
                for grandchild in child.iterdir():
                    if grandchild.is_dir():
                        for name in ("bin/mvn", "bin/mvn.cmd"):
                            candidate = grandchild / name
                            if candidate.is_file():
                                return str(candidate)

    return None


# ─── Kafka Java Bridge: prepare (build jar + generate stubs) ─────────────

_KAFKA_BRIDGE_ID = "kafka-java-bridge"
_KAFKA_BRIDGE_JAR_REL = "bridge/target/kafka-bridge-1.0.0-shaded.jar"
_KAFKA_BRIDGE_STUB_REL = "proto/kafka_bridge_pb2.py"
_KAFKA_BRIDGE_POM_REL  = "bridge/pom.xml"
_KAFKA_BRIDGE_GEN_REL  = "proto/generate_stubs.py"


def _kafka_bridge_plugin_dir() -> Path | None:
    """Resolve the kafka_java_bridge plugin directory from the PluginManager."""
    from mes.main import plugin_manager
    info = plugin_manager.get_plugin(_KAFKA_BRIDGE_ID)
    if info is not None:
        return info.path
    # Fallback: locate relative to this file (server/src/mes/framework/plugin/routes.py)
    here = Path(__file__).resolve()
    candidate = here.parents[4] / "plugins" / "system" / "kafka_java_bridge"
    return candidate if candidate.is_dir() else None


class KafkaPrepareResponse(BaseModel):
    jar_path: str
    jar_existed: bool
    jar_built: bool
    stubs_existed: bool
    stubs_generated: bool


@router.post("/kafka-java-bridge/prepare")
async def prepare_kafka_bridge(force: bool = False):
    """
    Build the Kafka Java fat-jar and generate Python gRPC stubs.

    By default (force=False) each step is skipped if the artifact already
    exists — safe to call repeatedly.  Pass force=true to force a clean
    rebuild and stub regeneration regardless of whether files exist; use this
    after updating library versions in pom.xml.

    Returns the absolute path to the fat-jar so the DT-CLIENT can display it
    and the install step can inject it automatically into bridge_jar.
    """
    plugin_dir = _kafka_bridge_plugin_dir()
    if plugin_dir is None:
        raise HTTPException(status_code=404, detail="kafka-java-bridge plugin directory not found")

    jar_path   = plugin_dir / _KAFKA_BRIDGE_JAR_REL
    stub_path  = plugin_dir / _KAFKA_BRIDGE_STUB_REL
    pom_path   = plugin_dir / _KAFKA_BRIDGE_POM_REL
    gen_script = plugin_dir / _KAFKA_BRIDGE_GEN_REL

    jar_existed   = jar_path.exists()
    stubs_existed = stub_path.exists()
    jar_built     = False
    stubs_generated = False

    # ── Step 1: Build fat-jar ─────────────────────────────────────────────
    if not jar_existed or force:
        if not pom_path.exists():
            raise HTTPException(status_code=500, detail=f"Maven pom.xml not found: {pom_path}")
        logger.info("Building Kafka bridge fat-jar via Maven…")
        mvn_exe = _find_mvn()
        if mvn_exe is None:
            raise HTTPException(
                status_code=500,
                detail=(
                    "mvn not found. Set MAVEN_HOME or M2_HOME, or add Maven's bin/ "
                    "directory to the PATH of the process that starts the MES server."
                ),
            )
        logger.info("Using mvn: %s", mvn_exe)
        try:
            subprocess.check_call(
                [mvn_exe, "-f", str(pom_path), "clean", "package", "-q"],
                timeout=300,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise HTTPException(status_code=500, detail=f"Maven build failed: {exc}")
        if not jar_path.exists():
            raise HTTPException(status_code=500, detail="Maven build succeeded but jar not found at expected path")
        jar_built = True
        logger.info("Kafka bridge jar built: %s", jar_path)

    # ── Step 2: Generate Python gRPC stubs ────────────────────────────────
    if not stubs_existed or force:
        if not gen_script.exists():
            raise HTTPException(status_code=500, detail=f"Stub generator not found: {gen_script}")
        logger.info("Generating Python gRPC stubs…")
        try:
            subprocess.check_call(
                [sys.executable, str(gen_script)],
                timeout=120,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise HTTPException(status_code=500, detail=f"Stub generation failed: {exc}")
        if not stub_path.exists():
            raise HTTPException(status_code=500, detail="Stub generation succeeded but pb2 file not found")
        stubs_generated = True
        logger.info("Kafka bridge stubs generated in %s", plugin_dir / "proto")

    return success_response(KafkaPrepareResponse(
        jar_path=str(jar_path.resolve()),
        jar_existed=jar_existed,
        jar_built=jar_built,
        stubs_existed=stubs_existed,
        stubs_generated=stubs_generated,
    ).model_dump())


@router.get("/kafka-java-bridge/status")
async def kafka_bridge_status():
    """Return current build status of the Kafka bridge jar and Python stubs."""
    plugin_dir = _kafka_bridge_plugin_dir()
    if plugin_dir is None:
        raise HTTPException(status_code=404, detail="kafka-java-bridge plugin directory not found")
    jar_path  = plugin_dir / _KAFKA_BRIDGE_JAR_REL
    stub_path = plugin_dir / _KAFKA_BRIDGE_STUB_REL
    return success_response({
        "jar_exists": jar_path.exists(),
        "jar_path": str(jar_path.resolve()),
        "stubs_exist": stub_path.exists(),
        "mvn_path": _find_mvn(),
    })


class KafkaTestResult(BaseModel):
    topic: str
    sent: str
    received: str
    match: bool


@router.post("/kafka-java-bridge/test")
async def kafka_bridge_test():
    """
    Round-trip Kafka connectivity test.

    Requires the kafka-java-bridge plugin to be running.  The test:
      1. Subscribes to a uniquely-named throw-away topic.
      2. Publishes a text message to that topic.
      3. Consumes the message via the same bridge.
      4. Validates that the received value matches the sent value.

    Returns the topic name, sent value, received value, and a match flag.
    """
    from mes.main import plugin_manager

    info = plugin_manager.get_plugin(_KAFKA_BRIDGE_ID)
    if info is None or not info.is_running or info.instance is None:
        raise HTTPException(
            status_code=503,
            detail="kafka-java-bridge plugin is not running — enable it before running the test",
        )

    try:
        result = await info.instance.run_connectivity_test(timeout_sec=35.0)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return success_response(KafkaTestResult(**result).model_dump())


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
    value: int = Field(..., ge=0, description="Absolute counter value to set")
    unit_id: int = Field(1, ge=1, le=247)
    address: int = Field(100, ge=0, description="Holding register address (default 100 = Good, 101 = Reject, 102 = Rework)")


class ModbusSimMaterialSetupRequest(BaseModel):
    equipment_id: str = Field(..., description="MES equipment UUID")
    material_code: str = Field(..., min_length=1, description="Configured material code to switch to")
    job_number: str | None = Field(None, description="Optional current job / order number")


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
    counter_good = await plugin.get_holding_register(uid, 100)
    counter_reject = await plugin.get_holding_register(uid, 101)
    counter_rework = await plugin.get_holding_register(uid, 102)

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
        "counter": counter_good,
        "counter_good": counter_good,
        "counter_reject": counter_reject,
        "counter_rework": counter_rework,
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
    """Set a counter holding register (HR[address]). Default address 100=Good, 101=Reject, 102=Rework."""
    plugin = _get_modbus_sim_plugin()
    await plugin.set_holding_register(body.unit_id, body.address, body.value)
    return success_response({
        "unit_id": body.unit_id,
        "address": body.address,
        "value": body.value,
    })


@router.post("/modbus-equipment-simulator/set-material-setup")
async def modbus_simulator_set_material_setup(
    body: ModbusSimMaterialSetupRequest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Simulate a Modbus-driven material setup change for a selected equipment.

    Unlike state and counters, the current Modbus simulator does not expose a
    dedicated register map for material changes, so this route applies the same
    equipment-material switch the simulator UI would ultimately drive.
    """
    from uuid import UUID

    from mes.core.physical_model.service import PhysicalModelService as svc
    from mes.core.physical_model.routes import _build_setup_read

    _get_modbus_sim_plugin()
    equip_id = UUID(body.equipment_id)
    em = await svc.find_equipment_material_by_code(session, equip_id, body.material_code)
    equip, em = await svc.set_material_setup(session, equip_id, em.id, body.job_number)
    data = _build_setup_read(equip, em)
    await session.commit()
    return success_response(data.model_dump())
