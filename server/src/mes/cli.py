"""
CLI entry-point for MES plugin management.

Offline commands (no server required):
    python -m mes.cli plugin list
    python -m mes.cli plugin search <keyword>
    python -m mes.cli plugin info <plugin_id>

Server commands (calls REST API at MES_SERVER_URL):
    python -m mes.cli plugin install <plugin_id> [--param key=value ...]
    python -m mes.cli plugin uninstall <plugin_id>
    python -m mes.cli plugin enable <plugin_id>
    python -m mes.cli plugin disable <plugin_id>
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from mes.framework.plugin.manifest import PluginManifest

# Default server URL for CLI → REST API calls
DEFAULT_SERVER_URL = "http://localhost:8000"


def _discover_manifests() -> list[PluginManifest]:
    """Scan both system and user plugin directories and return parsed manifests."""
    manifests: list[PluginManifest] = []
    for plugin_dir in [Path("plugins/system"), Path("plugins/user")]:
        if not plugin_dir.exists():
            continue
        for candidate in sorted(plugin_dir.iterdir()):
            manifest_path = candidate / "manifest.yaml"
            if candidate.is_dir() and manifest_path.exists():
                try:
                    manifests.append(PluginManifest.from_yaml(manifest_path))
                except Exception as exc:
                    print(f"  WARNING: {candidate.name}: {exc}", file=sys.stderr)
    return manifests


def cmd_list(_args: argparse.Namespace) -> None:
    """List plugins discovered in system and user directories."""
    manifests = _discover_manifests()
    if not manifests:
        print("No plugins found in plugins/system or plugins/user")
        return
    print(f"{'ID':<30} {'Version':<10} {'Origin':<8} {'Category':<12} {'Name'}")
    print("-" * 90)
    for m in manifests:
        origin = m.origin or "?"
        category = m.category or ""
        print(f"{m.id:<30} {m.version:<10} {origin:<8} {category:<12} {m.name}")
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
    print(f"  Comment:     {match.comment or '(none)'}")
    print(f"  Category:    {match.category or '(none)'}")
    print(f"  Origin:      {match.origin or '(none)'}")
    print(f"  Min MES:     {match.min_mes_version}")
    if match.extension_points:
        print(f"  Extensions:  {', '.join(ep.type for ep in match.extension_points)}")
    if match.event_subscriptions:
        print(f"  Events:      {', '.join(match.event_subscriptions)}")
    if match.dependencies:
        print(f"  Depends on:  {', '.join(match.dependencies)}")
    if match.parameters:
        print("  Parameters:")
        for p in match.parameters:
            req = "required" if p.required else "optional"
            default = f", default={p.default}" if p.default is not None else ""
            print(f"    {p.name} ({p.type}, {req}{default}): {p.description}")
    if match.config_schema.get("properties"):
        print("  Config keys:", ", ".join(match.config_schema["properties"].keys()))


def cmd_install(args: argparse.Namespace) -> None:
    """Install a plugin via the server REST API."""
    server = args.server or DEFAULT_SERVER_URL
    param_values: dict[str, str] = {}
    for pv in args.param or []:
        if "=" not in pv:
            print(f"Invalid --param format: '{pv}' (expected key=value)")
            sys.exit(1)
        k, v = pv.split("=", 1)
        param_values[k] = v

    body = json.dumps({"parameter_values": param_values}).encode()
    url = f"{server}/api/v1/plugins/{args.plugin_id}/install"
    _api_post(url, body, f"Installed plugin '{args.plugin_id}'")


def cmd_uninstall(args: argparse.Namespace) -> None:
    """Uninstall a plugin via the server REST API."""
    server = args.server or DEFAULT_SERVER_URL
    url = f"{server}/api/v1/plugins/{args.plugin_id}/uninstall"
    _api_post(url, b"{}", f"Uninstalled plugin '{args.plugin_id}'")


def cmd_enable(args: argparse.Namespace) -> None:
    """Enable a plugin via the server REST API."""
    server = args.server or DEFAULT_SERVER_URL
    url = f"{server}/api/v1/plugins/{args.plugin_id}/enable"
    _api_post(url, b"{}", f"Enabled plugin '{args.plugin_id}'")


def cmd_disable(args: argparse.Namespace) -> None:
    """Disable a plugin via the server REST API."""
    server = args.server or DEFAULT_SERVER_URL
    url = f"{server}/api/v1/plugins/{args.plugin_id}/disable"
    _api_post(url, b"{}", f"Disabled plugin '{args.plugin_id}'")


def _api_post(url: str, body: bytes, success_msg: str) -> None:
    """Make a POST request to the MES server API."""
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:  # noqa: S310
            data = json.loads(resp.read())
            print(success_msg)
            if "data" in data:
                payload = data["data"]
                for k, v in payload.items():
                    if k in ("companions_installed", "companions_enabled"):
                        print(f"  {k}: {', '.join(v)}")
                    elif k == "client_apps":
                        for app in v:
                            port = app.get("dev_port", "")
                            print(f"  companion client: {app.get('name', app['id'])}"
                                  f" — cd {app.get('path', '')} && npm run dev"
                                  + (f" (port {port})" if port else ""))
                    else:
                        print(f"  {k}: {v}")
    except urllib.error.HTTPError as exc:
        detail = json.loads(exc.read()) if exc.readable() else {}
        print(f"Error ({exc.code}): {detail.get('detail', exc.reason)}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"Cannot reach server: {exc.reason}", file=sys.stderr)
        sys.exit(1)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="mes",
        description="MES AI command-line interface",
    )
    parser.add_argument(
        "--server", default=None,
        help=f"Server URL for API commands (default: {DEFAULT_SERVER_URL})",
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

    install_p = plugin_sub.add_parser("install", help="Install a plugin (requires server)")
    install_p.add_argument("plugin_id", help="Plugin ID")
    install_p.add_argument("--param", action="append", help="Parameter as key=value")

    uninstall_p = plugin_sub.add_parser("uninstall", help="Uninstall a plugin (requires server)")
    uninstall_p.add_argument("plugin_id", help="Plugin ID")

    enable_p = plugin_sub.add_parser("enable", help="Enable a plugin (requires server)")
    enable_p.add_argument("plugin_id", help="Plugin ID")

    disable_p = plugin_sub.add_parser("disable", help="Disable a plugin (requires server)")
    disable_p.add_argument("plugin_id", help="Plugin ID")

    args = parser.parse_args(argv)

    if args.command == "plugin":
        handlers = {
            "list": cmd_list,
            "search": cmd_search,
            "info": cmd_info,
            "install": cmd_install,
            "uninstall": cmd_uninstall,
            "enable": cmd_enable,
            "disable": cmd_disable,
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
