"""
CLI entry-point for MES plugin management.

Usage:
    python -m mes.cli plugin list
    python -m mes.cli plugin search <keyword>
    python -m mes.cli plugin install <extra>
    python -m mes.cli plugin info <plugin_id>

These commands can be run offline without a running server (except
'info' which reads from the plugin directory).
"""

from __future__ import annotations

import argparse
import importlib
import subprocess
import sys
from pathlib import Path

from mes.config import settings
from mes.framework.plugin.manifest import PluginManifest


def _discover_manifests() -> list[PluginManifest]:
    """Scan the plugin directory and return parsed manifests."""
    plugin_dir = Path(settings.PLUGIN_DIR)
    manifests: list[PluginManifest] = []
    if not plugin_dir.exists():
        return manifests
    for candidate in sorted(plugin_dir.iterdir()):
        manifest_path = candidate / "manifest.yaml"
        if candidate.is_dir() and manifest_path.exists():
            try:
                manifests.append(PluginManifest.from_yaml(manifest_path))
            except Exception as exc:
                print(f"  WARNING: {candidate.name}: {exc}", file=sys.stderr)
    return manifests


EXTRAS_CATALOG = {
    "opcua": "OPC-UA equipment adapter (asyncua)",
    "mqtt": "MQTT equipment adapter (aiomqtt)",
    "sap": "SAP S/4HANA ERP adapter (pyrfc)",
    "oracle": "Oracle Cloud ERP adapter (oracledb)",
    "modbus": "Modbus TCP equipment adapter (pymodbus)",
    "kafka": "Kafka event bus transport (aiokafka)",
    "nats": "NATS event bus transport (nats-py)",
    "rabbitmq": "RabbitMQ event bus transport (aio-pika)",
    "redis": "Redis cache/transport (redis)",
    "all": "Install all optional adapter dependencies",
}


def cmd_list(_args: argparse.Namespace) -> None:
    """List plugins in the configured plugin directory."""
    manifests = _discover_manifests()
    if not manifests:
        print("No plugins found in", settings.PLUGIN_DIR)
        return
    print(f"{'ID':<30} {'Version':<10} {'Name'}")
    print("-" * 70)
    for m in manifests:
        print(f"{m.id:<30} {m.version:<10} {m.name}")
    print(f"\n{len(manifests)} plugin(s) found.")


def cmd_search(args: argparse.Namespace) -> None:
    """Search plugins by keyword (matches id, name, description)."""
    keyword = args.keyword.lower()
    manifests = _discover_manifests()
    matches = [
        m
        for m in manifests
        if keyword in m.id.lower()
        or keyword in m.name.lower()
        or keyword in m.description.lower()
    ]
    if not matches:
        print(f"No plugins matching '{args.keyword}'")
        return
    print(f"{'ID':<30} {'Version':<10} {'Name'}")
    print("-" * 70)
    for m in matches:
        print(f"{m.id:<30} {m.version:<10} {m.name}")


def cmd_info(args: argparse.Namespace) -> None:
    """Show detailed information about a plugin."""
    manifests = _discover_manifests()
    match = next((m for m in manifests if m.id == args.plugin_id), None)
    if match is None:
        print(f"Plugin '{args.plugin_id}' not found.")
        sys.exit(1)

    print(f"Plugin: {match.name}")
    print(f"  ID:          {match.id}")
    print(f"  Version:     {match.version}")
    print(f"  Author:      {match.author or '(not set)'}")
    print(f"  Description: {match.description or '(none)'}")
    print(f"  Min MES:     {match.min_mes_version}")
    if match.extension_points:
        print(f"  Extensions:  {', '.join(ep.type for ep in match.extension_points)}")
    if match.event_subscriptions:
        print(f"  Events:      {', '.join(match.event_subscriptions)}")
    if match.dependencies:
        print(f"  Depends on:  {', '.join(match.dependencies)}")
    if match.config_schema.get("properties"):
        print("  Config keys:", ", ".join(match.config_schema["properties"].keys()))


def cmd_install(args: argparse.Namespace) -> None:
    """Install an adapter extra via pip."""
    extra = args.extra
    if extra not in EXTRAS_CATALOG:
        print(f"Unknown extra '{extra}'. Available extras:")
        for name, desc in EXTRAS_CATALOG.items():
            installed = _is_installed(name)
            status = "installed" if installed else "not installed"
            print(f"  {name:<12} {desc} [{status}]")
        sys.exit(1)

    print(f"Installing mes-ai[{extra}] ...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", f"mes-ai[{extra}]"],
        capture_output=False,
    )
    sys.exit(result.returncode)


def cmd_extras(_args: argparse.Namespace) -> None:
    """List available pip extras and their installation status."""
    print(f"{'Extra':<12} {'Installed':<12} {'Description'}")
    print("-" * 70)
    for name, desc in EXTRAS_CATALOG.items():
        if name == "all":
            continue
        installed = "yes" if _is_installed(name) else "no"
        print(f"{name:<12} {installed:<12} {desc}")


_EXTRA_CHECK_MODULES = {
    "opcua": "asyncua",
    "mqtt": "aiomqtt",
    "sap": "pyrfc",
    "oracle": "oracledb",
    "modbus": "pymodbus",
    "kafka": "aiokafka",
    "nats": "nats",
    "rabbitmq": "aio_pika",
    "redis": "redis",
}


def _is_installed(extra: str) -> bool:
    """Check if the package(s) for a given extra are importable."""
    module_name = _EXTRA_CHECK_MODULES.get(extra)
    if module_name is None:
        return False
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="mes",
        description="MES AI command-line interface",
    )
    sub = parser.add_subparsers(dest="command")

    # ── plugin sub-commands ──
    plugin_parser = sub.add_parser("plugin", help="Plugin management")
    plugin_sub = plugin_parser.add_subparsers(dest="plugin_cmd")

    plugin_sub.add_parser("list", help="List discovered plugins")

    search_p = plugin_sub.add_parser("search", help="Search plugins by keyword")
    search_p.add_argument("keyword", help="Search term")

    info_p = plugin_sub.add_parser("info", help="Show plugin details")
    info_p.add_argument("plugin_id", help="Plugin ID")

    install_p = plugin_sub.add_parser("install", help="Install an adapter extra")
    install_p.add_argument("extra", help="Extra name (e.g. opcua, sap, oracle)")

    plugin_sub.add_parser("extras", help="List available pip extras")

    args = parser.parse_args(argv)

    if args.command == "plugin":
        handlers = {
            "list": cmd_list,
            "search": cmd_search,
            "info": cmd_info,
            "install": cmd_install,
            "extras": cmd_extras,
        }
        handler = handlers.get(args.plugin_cmd)
        if handler is None:
            plugin_parser.print_help()
            sys.exit(1)
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
