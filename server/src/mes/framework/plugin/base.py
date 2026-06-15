"""
PLUGIN-FW: Base class and extension point definitions for MES plugins.

Every plugin must subclass MESPlugin and implement the lifecycle methods.
Extension points define the categories of functionality a plugin can provide.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import socket
import subprocess
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class ExtensionPointType(str, Enum):
    """
    Types of extension points plugins can implement.
    Per ARCHITECTURE.md §7.5.
    """

    DISPATCH_STRATEGY = "dispatch_strategy"
    OPERATION_HOOK = "operation_hook"
    REST_ENDPOINT = "rest_endpoint"
    EVENT_HANDLER = "event_handler"
    DATA_PROCESSOR = "data_processor"
    REPORT_GENERATOR = "report_generator"
    EQUIPMENT_DRIVER = "equipment_driver"
    EQUIPMENT_STATE_MODEL = "equipment_state_model"
    ERP_INBOUND = "erp_inbound"
    ERP_OUTBOUND = "erp_outbound"
    TEST_EQUIPMENT = "test_equipment"
    NATIVE_SDK_BRIDGE = "native_sdk_bridge"


class MESPlugin(ABC):
    """
    Base class all MES plugins must implement.

    Lifecycle:
        discover → validate manifest → load module → initialize(config)
            → start() → [running] → stop() → unload

    Subclass this and implement the abstract methods. Override the optional
    methods (get_routes, get_event_handlers) to register REST endpoints
    and event subscriptions.
    """

    @abstractmethod
    async def initialize(self, config: dict[str, Any]) -> None:
        """
        Called when the plugin is loaded. Use this to set up resources,
        validate configuration, and register internal state.

        Args:
            config: Plugin configuration (merged from manifest defaults + user overrides).
        """
        ...

    @abstractmethod
    async def start(self) -> None:
        """
        Called after all plugins have been initialized.
        Begin active operation (start background tasks, open connections, etc.).
        """
        ...

    @abstractmethod
    async def stop(self) -> None:
        """
        Called on shutdown or when the plugin is disabled.
        Clean up resources, close connections, cancel background tasks.
        """
        ...

    def get_routes(self) -> list | None:
        """
        Return FastAPI APIRouter(s) to register with the application, or None.
        Routers should use the prefix declared in the manifest's rest_endpoint extension point.
        """
        return None

    def get_event_handlers(self) -> dict[str, Any] | None:
        """
        Return a mapping of event_type pattern -> async handler callable, or None.

        Example:
            return {
                "wip.unit.completed": self.on_unit_completed,
                "equipment.state.changed": self.on_state_change,
            }
        """
        return None

    async def health_check(self) -> bool:
        """
        Check if the plugin can communicate with its external system.
        Override this for adapter plugins that connect to external services.
        Default returns True (healthy) for non-adapter plugins.
        """
        return True

    def get_adapter(self) -> Any:
        """
        Return the adapter interface instance(s) this plugin provides.

        For single-adapter plugins (e.g. equipment), return the adapter instance.
        For multi-adapter plugins (e.g. ERP with inbound + outbound), return a dict:
            {"erp_inbound": inbound_instance, "erp_outbound": outbound_instance}

        Returns None for non-adapter plugins.
        """
        return None


_bridge_logger = logging.getLogger("mes.plugins.native_sdk_bridge")


def _terminate_proc(proc: subprocess.Popen[bytes]) -> None:
    """Terminate *proc* gracefully, escalating to kill after 5 s."""
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        _bridge_logger.warning("Bridge did not exit after SIGTERM — sending SIGKILL")
        proc.kill()
        proc.wait()


def _check_port_available(bridge_address: str) -> None:
    """
    Verify that the TCP port in *bridge_address* (``"host:port"`` format) is not
    already bound by another process.

    Raises :class:`RuntimeError` with an actionable message if the port is in
    use, so the caller can surface it before wasting time launching a subprocess
    that will fail immediately with a ``BindException``.

    Common cause: an orphaned bridge process from a previous uvicorn --reload
    cycle.  On Windows, ``subprocess.Popen`` children are not automatically
    killed when the parent process is replaced by the reloader.
    """
    try:
        host, port_str = bridge_address.rsplit(":", 1)
        port = int(port_str)
    except (ValueError, AttributeError):
        return  # can't parse — skip check rather than block startup

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # On Windows SO_REUSEADDR allows binding an already-bound port, which
        # would give a false "port is free" result.  SO_EXCLUSIVEADDRUSE
        # (Windows-only) prevents that.  On POSIX, omitting SO_REUSEADDR is
        # sufficient for an accurate probe.
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):  # Windows
            s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)  # type: ignore[attr-defined]
        try:
            s.bind((host, port))
        except OSError:
            raise RuntimeError(
                f"Port {port} on {host} is already in use — an orphaned bridge "
                "process from a previous server run is likely still holding it.\n"
                f"  On Windows: run  netstat -ano | findstr :{port}  to find the PID, "
                "then  Stop-Process -Id <PID>.\n"
                f"  On Linux:   run  fuser -k {port}/tcp\n"
                "Alternatively, set a different bridge_port in the plugin configuration."
            )


class NativeSdkBridgePlugin(MESPlugin, ABC):
    """
    Intermediate base class for plugins that delegate to an out-of-process
    native-SDK bridge written in C++, C#, or Java.

    The bridge exposes a gRPC service on localhost; this base class handles:
      - Launching the bridge subprocess on ``start()``
      - Logging bridge stdout/stderr
      - Detecting unexpected bridge exit and restarting automatically
      - Clean termination on ``stop()``

    Concrete subclasses must still implement ``initialize()``, ``start()``, and
    ``stop()``.  The protected helpers ``_start_bridge()`` / ``_stop_bridge()``
    should be called from those methods to manage the subprocess lifecycle.

    Extension point type: ``native_sdk_bridge``

    Typical concrete ``start()``::

        async def start(self) -> None:
            await self._start_bridge()          # launch the bridge process
            await self._wait_for_bridge_port()  # custom health-check (gRPC, TCP …)
            self._consumer_task = asyncio.create_task(self._consume_loop())

    Typical concrete ``stop()``::

        async def stop(self) -> None:
            if self._consumer_task:
                self._consumer_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._consumer_task
            await self._stop_bridge()
    """

    def __init__(self) -> None:
        self._bridge_proc: subprocess.Popen[bytes] | None = None
        self._monitor_task: asyncio.Task[None] | None = None

    # ── Abstract ──────────────────────────────────────────────────────────────

    @abstractmethod
    def bridge_command(self) -> list[str]:
        """
        Return the full command + args needed to start the bridge process.

        Example (Java fat-jar)::

            return [
                "java", "-jar", "/path/to/kafka-bridge.jar",
                "--port", "50051",
                "--bootstrap-servers", "localhost:9092",
            ]
        """
        ...

    # ── Tuneable properties ───────────────────────────────────────────────────

    @property
    def bridge_address(self) -> str:
        """
        gRPC target address for the bridge.
        Override in the concrete plugin to match ``bridge_command()`` ``--port``.
        Default: ``127.0.0.1:50051``
        """
        return "127.0.0.1:50051"

    @property
    def bridge_startup_timeout_sec(self) -> float:
        """Seconds to wait for the bridge to become healthy. Default: 30.0"""
        return 30.0

    # ── Protected lifecycle helpers ───────────────────────────────────────────

    async def _start_bridge(self) -> None:
        """
        Launch the bridge subprocess and start a monitor task that logs its
        output and restarts it on unexpected exit.

        Uses ``subprocess.Popen`` (via ``asyncio.to_thread``) so that the call
        works on any asyncio event loop implementation, including
        ``SelectorEventLoop`` on Windows where ``create_subprocess_exec``
        raises ``NotImplementedError``.

        Call this from your concrete ``start()`` implementation *before* opening
        the gRPC channel.
        """
        # Pre-flight: verify the port is available before launching the
        # subprocess.  A port-in-use error here almost always means an orphaned
        # bridge process from a previous server run (e.g. after uvicorn --reload
        # killed the old worker without terminating its children).
        _check_port_available(self.bridge_address)

        cmd = self.bridge_command()
        _bridge_logger.info("Starting bridge: %s", " ".join(cmd))
        self._bridge_proc = await asyncio.to_thread(
            lambda: subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        )
        self._monitor_task = asyncio.create_task(
            self._monitor_bridge(), name="native-sdk-bridge-monitor"
        )

    async def _stop_bridge(self) -> None:
        """
        Cancel the monitor task and terminate the bridge process cleanly.

        Call this from your concrete ``stop()`` implementation *after* closing
        the gRPC channel.
        """
        if self._monitor_task is not None:
            self._monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._monitor_task
            self._monitor_task = None

        proc = self._bridge_proc
        if proc is not None and proc.poll() is None:
            await asyncio.to_thread(_terminate_proc, proc)
        self._bridge_proc = None
        _bridge_logger.info("Bridge process stopped")

    # ── Internal monitor ──────────────────────────────────────────────────────

    async def _monitor_bridge(self) -> None:
        """
        Background task that:
        1. Drains stdout/stderr from the bridge and forwards to the Python logger.
        2. Detects when the process exits unexpectedly and restarts it.

        I/O is done via ``asyncio.to_thread`` so it works on any event loop
        type (including ``SelectorEventLoop`` on Windows).
        """
        proc = self._bridge_proc
        if proc is None:
            return

        plugin_name = type(self).__name__

        # Port-in-use errors are permanent — retrying won't help and will just
        # flood the log.  We signal this from the drain thread via a flag.
        port_in_use_seen = [False]

        _PORT_IN_USE_MARKERS = ("BindException", "Address already in use")

        def _drain(pipe, level: int) -> None:
            """Read lines from *pipe* in a thread until EOF."""
            try:
                for raw_line in iter(pipe.readline, b""):
                    line = raw_line.decode(errors="replace").rstrip()
                    if line:
                        _bridge_logger.log(level, "[%s bridge] %s", plugin_name, line)
                        if any(m in line for m in _PORT_IN_USE_MARKERS):
                            port_in_use_seen[0] = True
            except Exception:  # noqa: BLE001
                pass  # pipe closed — normal on process exit

        # Maximum consecutive quick exits (< _QUICK_EXIT_THRESHOLD_SEC) before
        # we stop restarting — these indicate a permanent launch failure (wrong
        # Java version, missing jar, bad args …) that retrying won't fix.
        _QUICK_EXIT_THRESHOLD_SEC = 3.0
        _MAX_QUICK_EXITS = 3
        quick_exit_count = 0

        try:
            while True:
                assert proc.stdout is not None
                assert proc.stderr is not None
                stdout_task = asyncio.create_task(
                    asyncio.to_thread(_drain, proc.stdout, logging.INFO)
                )
                stderr_task = asyncio.create_task(
                    asyncio.to_thread(_drain, proc.stderr, logging.WARNING)
                )

                started_at = time.monotonic()
                ret = await asyncio.to_thread(proc.wait)
                elapsed = time.monotonic() - started_at
                # Let the drain threads finish reading whatever's left
                with contextlib.suppress(Exception):
                    await asyncio.gather(stdout_task, stderr_task)

                if ret == 0:
                    _bridge_logger.info("[%s bridge] exited cleanly (rc=0)", plugin_name)
                    return

                # Port conflict — retrying will never succeed; stop immediately.
                if port_in_use_seen[0]:
                    _bridge_logger.error(
                        "[%s bridge] exited because the port is already in use — "
                        "an orphaned bridge process from a previous server run may "
                        "still be holding it. Kill that process or change bridge_port. "
                        "Giving up.",
                        plugin_name,
                    )
                    return

                if elapsed < _QUICK_EXIT_THRESHOLD_SEC:
                    quick_exit_count += 1
                    if quick_exit_count >= _MAX_QUICK_EXITS:
                        _bridge_logger.error(
                            "[%s bridge] exited immediately %d times in a row (rc=%d, "
                            "uptime=%.1fs) — permanent launch failure "
                            "(wrong Java version? missing jar? port in use?). Giving up.",
                            plugin_name, quick_exit_count, ret, elapsed,
                        )
                        return
                else:
                    quick_exit_count = 0

                _bridge_logger.error(
                    "[%s bridge] exited unexpectedly (rc=%d, uptime=%.1fs) — restarting in 3 s",
                    plugin_name, ret, elapsed,
                )
                await asyncio.sleep(3.0)

                # Re-check port before restarting
                try:
                    _check_port_available(self.bridge_address)
                except RuntimeError as port_exc:
                    _bridge_logger.error(
                        "[%s bridge] port still in use before restart — %s. Giving up.",
                        plugin_name, port_exc,
                    )
                    return

                cmd = self.bridge_command()
                _bridge_logger.info("Restarting bridge: %s", " ".join(cmd))
                port_in_use_seen[0] = False
                proc = await asyncio.to_thread(
                    lambda: subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                    )
                )
                self._bridge_proc = proc

        except asyncio.CancelledError:
            pass

