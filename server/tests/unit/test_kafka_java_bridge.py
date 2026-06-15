"""
Unit tests for the kafka_java_bridge plugin.

All tests are fully isolated — no JVM, no Kafka broker, no gRPC network I/O.
External calls (subprocess.Popen, grpc.aio) are replaced by mocks.

Test coverage:
  - _resolve_java_exe: plugin param, JAVA_HOME env var, PATH fallback, bad path
  - _check_java_version: happy path, too old, not found, unparseable output
  - KafkaJavaBridgePlugin.initialize: config parsing, jar check, java version check
  - KafkaJavaBridgePlugin.publish: success, gRPC failure
  - KafkaJavaBridgePlugin.health_check: healthy, unhealthy, stub None
  - KafkaJavaBridgePlugin.run_connectivity_test: round-trip success, publish failure,
      receive timeout, message mismatch
  - NativeSdkBridgePlugin._start_bridge / _stop_bridge: port pre-check, happy path
  - NativeSdkBridgePlugin._check_port_available: free port, in-use port
"""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

# ---------------------------------------------------------------------------
# Helpers: make the plugin importable without real gRPC stubs on disk
# ---------------------------------------------------------------------------

def _install_fake_stubs() -> None:
    """
    Inject minimal fake kafka_bridge_pb2 / kafka_bridge_pb2_grpc modules into
    sys.modules under the same synthetic package name that _load_stubs() uses,
    so that calling _load_stubs() is a no-op (stubs already present).
    """
    import types

    pkg_name = "_kafka_bridge_proto"
    if pkg_name in sys.modules:
        return

    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = []  # type: ignore[attr-defined]
    pkg.__package__ = pkg_name

    # --- pb2 ---
    pb2 = types.ModuleType(f"{pkg_name}.kafka_bridge_pb2")
    pb2.__package__ = pkg_name

    def _make_request(**kwargs):
        m = MagicMock()
        for k, v in kwargs.items():
            setattr(m, k, v)
        return m

    pb2.HealthRequest    = lambda **kw: _make_request(**kw)
    pb2.PublishRequest   = lambda **kw: _make_request(**kw)
    pb2.SubscribeRequest = lambda **kw: _make_request(**kw)

    # --- pb2_grpc ---
    pb2_grpc = types.ModuleType(f"{pkg_name}.kafka_bridge_pb2_grpc")
    pb2_grpc.__package__ = pkg_name
    pb2_grpc.KafkaBridgeStub = MagicMock

    sys.modules[pkg_name]                          = pkg
    sys.modules[f"{pkg_name}.kafka_bridge_pb2"]     = pb2
    sys.modules[f"{pkg_name}.kafka_bridge_pb2_grpc"] = pb2_grpc
    setattr(pkg, "kafka_bridge_pb2",      pb2)
    setattr(pkg, "kafka_bridge_pb2_grpc", pb2_grpc)


_install_fake_stubs()

# Load the plugin module directly by path so this test works regardless of
# whether the plugins/ directory is on sys.path (it is not by default).
import importlib.util as _ilu

_plugin_path = (
    Path(__file__).resolve().parents[2]
    / "plugins" / "system" / "kafka_java_bridge" / "plugin.py"
)
_spec = _ilu.spec_from_file_location("_kafka_bridge_plugin_under_test", str(_plugin_path))
_plugin_mod = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_plugin_mod)  # type: ignore[union-attr]

KafkaJavaBridgePlugin = _plugin_mod.KafkaJavaBridgePlugin
_check_java_version   = _plugin_mod._check_java_version
_resolve_java_exe     = _plugin_mod._resolve_java_exe

from mes.framework.plugin.base import NativeSdkBridgePlugin, _check_port_available


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def plugin() -> KafkaJavaBridgePlugin:
    """Return an uninitialised plugin instance with fake stubs already loaded."""
    p = KafkaJavaBridgePlugin()
    # Point the module-level globals to our fake stubs
    _plugin_mod._pb2 = sys.modules["_kafka_bridge_proto.kafka_bridge_pb2"]
    _plugin_mod._pb2_grpc = sys.modules["_kafka_bridge_proto.kafka_bridge_pb2_grpc"]
    return p


@pytest.fixture()
def fake_jar(tmp_path: Path) -> Path:
    """Create a zero-byte file that passes the is_file() check."""
    jar = tmp_path / "kafka-bridge-1.0.0-shaded.jar"
    jar.touch()
    return jar


def _minimal_config(jar: Path, **overrides) -> dict[str, Any]:
    cfg: dict[str, Any] = {
        "bridge_jar":         str(jar),
        "bridge_port":        "50053",
        "bootstrap_servers":  "localhost:9092",
        "topics":             "[]",
        "consumer_group":     "test-group",
        "poll_timeout_ms":    "500",
        "mes_event_type":     "data.collected",
        "java_home":          "",
    }
    cfg.update(overrides)
    return cfg


# ---------------------------------------------------------------------------
# _resolve_java_exe
# ---------------------------------------------------------------------------

class TestResolveJavaExe:

    def test_returns_path_java_when_nothing_set(self, monkeypatch):
        monkeypatch.delenv("JAVA_HOME", raising=False)
        assert _resolve_java_exe("") == "java"

    def test_uses_java_home_env_var(self, tmp_path, monkeypatch):
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        java_exe = bin_dir / ("java.exe" if os.name == "nt" else "java")
        java_exe.touch()
        monkeypatch.setenv("JAVA_HOME", str(tmp_path))
        result = _resolve_java_exe("")
        assert result == str(java_exe)

    def test_plugin_param_takes_precedence_over_env(self, tmp_path, monkeypatch):
        # env JAVA_HOME points elsewhere
        monkeypatch.setenv("JAVA_HOME", "/does/not/exist")
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        java_exe = bin_dir / ("java.exe" if os.name == "nt" else "java")
        java_exe.touch()
        result = _resolve_java_exe(str(tmp_path))
        assert result == str(java_exe)

    def test_plugin_param_bad_path_raises(self, tmp_path):
        with pytest.raises(RuntimeError, match="java_home plugin parameter"):
            _resolve_java_exe(str(tmp_path / "nonexistent"))

    def test_java_home_env_bad_path_raises(self, tmp_path, monkeypatch):
        monkeypatch.setenv("JAVA_HOME", str(tmp_path / "nonexistent"))
        with pytest.raises(RuntimeError, match="JAVA_HOME environment variable"):
            _resolve_java_exe("")


# ---------------------------------------------------------------------------
# _check_java_version
# ---------------------------------------------------------------------------

class TestCheckJavaVersion:

    def _run_result(self, stderr: str, returncode: int = 0):
        r = MagicMock()
        r.stderr = stderr
        r.stdout = ""
        r.returncode = returncode
        return r

    def test_happy_path_java21(self):
        with patch("subprocess.run", return_value=self._run_result(
            'openjdk version "21.0.1" 2023-10-17\n'
        )):
            _check_java_version("java", min_major=17)  # should not raise

    def test_version_too_old_raises(self):
        with patch("subprocess.run", return_value=self._run_result(
            'openjdk version "11.0.20" 2023-07-18 LTS\n'
        )):
            with pytest.raises(RuntimeError, match="Java 17\\+"):
                _check_java_version("java", min_major=17)

    def test_java_not_found_raises(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with pytest.raises(RuntimeError, match="not found"):
                _check_java_version("/no/such/java", min_major=17)

    def test_unparseable_output_does_not_raise(self, caplog):
        with patch("subprocess.run", return_value=self._run_result("some garbage output")):
            # Should log a warning but not raise
            _check_java_version("java", min_major=17)

    def test_version_exactly_at_minimum_passes(self):
        with patch("subprocess.run", return_value=self._run_result(
            'openjdk version "17.0.0" 2021-09-14\n'
        )):
            _check_java_version("java", min_major=17)  # should not raise


# ---------------------------------------------------------------------------
# KafkaJavaBridgePlugin.initialize
# ---------------------------------------------------------------------------

class TestInitialize:

    @pytest.mark.asyncio
    async def test_happy_path(self, plugin, fake_jar, monkeypatch):
        monkeypatch.delenv("JAVA_HOME", raising=False)
        monkeypatch.setattr(_plugin_mod, "_check_java_version", lambda *a, **kw: None)
        await plugin.initialize(_minimal_config(fake_jar))
        assert plugin._jar_path == str(fake_jar)
        assert plugin._port == 50053
        assert plugin._bootstrap_servers == "localhost:9092"

    @pytest.mark.asyncio
    async def test_jar_not_found_raises(self, plugin, tmp_path, monkeypatch):
        monkeypatch.delenv("JAVA_HOME", raising=False)
        monkeypatch.setattr(_plugin_mod, "_check_java_version", lambda *a, **kw: None)
        cfg = _minimal_config(tmp_path / "missing.jar")
        with pytest.raises(FileNotFoundError, match="Kafka bridge jar not found"):
            await plugin.initialize(cfg)

    @pytest.mark.asyncio
    async def test_topics_parsed_from_json_array(self, plugin, fake_jar, monkeypatch):
        monkeypatch.delenv("JAVA_HOME", raising=False)
        monkeypatch.setattr(_plugin_mod, "_check_java_version", lambda *a, **kw: None)
        cfg = _minimal_config(fake_jar, topics='["equipment.events","quality.results"]')
        await plugin.initialize(cfg)
        assert plugin._topics == ["equipment.events", "quality.results"]

    @pytest.mark.asyncio
    async def test_topics_parsed_from_csv(self, plugin, fake_jar, monkeypatch):
        monkeypatch.delenv("JAVA_HOME", raising=False)
        monkeypatch.setattr(_plugin_mod, "_check_java_version", lambda *a, **kw: None)
        cfg = _minimal_config(fake_jar, topics="topic.a,topic.b")
        await plugin.initialize(cfg)
        assert plugin._topics == ["topic.a", "topic.b"]

    @pytest.mark.asyncio
    async def test_java_version_check_failure_propagates(self, plugin, fake_jar, monkeypatch):
        monkeypatch.delenv("JAVA_HOME", raising=False)
        def _fail(*a, **kw): raise RuntimeError("Java 17+ required but found 11")
        monkeypatch.setattr(_plugin_mod, "_check_java_version", _fail)
        with pytest.raises(RuntimeError, match="Java 17\\+"):
            await plugin.initialize(_minimal_config(fake_jar))


# ---------------------------------------------------------------------------
# KafkaJavaBridgePlugin.publish
# ---------------------------------------------------------------------------

class TestPublish:

    def _stub_with_publish(self, success: bool, error: str = ""):
        stub = MagicMock()
        resp = MagicMock()
        resp.success = success
        resp.error = error
        stub.Publish = AsyncMock(return_value=resp)
        return stub

    @pytest.mark.asyncio
    async def test_publish_success(self, plugin):
        plugin._stub = self._stub_with_publish(True)
        ok, err = await plugin.publish("test.topic", b"hello")
        assert ok is True
        assert err == ""

    @pytest.mark.asyncio
    async def test_publish_broker_error(self, plugin):
        plugin._stub = self._stub_with_publish(False, "topic not found")
        ok, err = await plugin.publish("test.topic", b"hello")
        assert ok is False
        assert "topic not found" in err

    @pytest.mark.asyncio
    async def test_publish_no_stub_returns_error(self, plugin):
        plugin._stub = None
        ok, err = await plugin.publish("test.topic", b"hello")
        assert ok is False
        assert "not started" in err

    @pytest.mark.asyncio
    async def test_publish_grpc_exception(self, plugin):
        stub = MagicMock()
        stub.Publish = AsyncMock(side_effect=RuntimeError("gRPC channel closed"))
        plugin._stub = stub
        ok, err = await plugin.publish("test.topic", b"hello")
        assert ok is False
        assert "gRPC channel closed" in err


# ---------------------------------------------------------------------------
# KafkaJavaBridgePlugin.health_check
# ---------------------------------------------------------------------------

class TestHealthCheck:

    @pytest.mark.asyncio
    async def test_healthy(self, plugin):
        stub = MagicMock()
        resp = MagicMock()
        resp.healthy = True
        stub.HealthCheck = AsyncMock(return_value=resp)
        plugin._stub = stub
        assert await plugin.health_check() is True

    @pytest.mark.asyncio
    async def test_unhealthy(self, plugin):
        stub = MagicMock()
        resp = MagicMock()
        resp.healthy = False
        stub.HealthCheck = AsyncMock(return_value=resp)
        plugin._stub = stub
        assert await plugin.health_check() is False

    @pytest.mark.asyncio
    async def test_stub_none_returns_false(self, plugin):
        plugin._stub = None
        assert await plugin.health_check() is False

    @pytest.mark.asyncio
    async def test_grpc_exception_returns_false(self, plugin):
        stub = MagicMock()
        stub.HealthCheck = AsyncMock(side_effect=RuntimeError("connection reset"))
        plugin._stub = stub
        assert await plugin.health_check() is False


# ---------------------------------------------------------------------------
# KafkaJavaBridgePlugin.run_connectivity_test
# ---------------------------------------------------------------------------

class TestRunConnectivityTest:

    def _make_stub(self, messages: list[bytes]) -> MagicMock:
        """
        Build a stub whose Subscribe() returns an async generator that yields
        KafkaMessage-like mocks for each byte string in *messages*.
        Publish always succeeds.
        """
        stub = MagicMock()

        async def _gen(*args, **kwargs):
            for raw in messages:
                msg = MagicMock()
                msg.value = raw
                yield msg

        stub.Subscribe = MagicMock(side_effect=_gen)

        pub_resp = MagicMock()
        pub_resp.success = True
        pub_resp.error = ""
        stub.Publish = AsyncMock(return_value=pub_resp)
        return stub

    @pytest.mark.asyncio
    async def test_round_trip_success(self, plugin):
        # Use an Event so the generator waits for publish regardless of how
        # long the rebalance sleep inside run_connectivity_test takes.
        published = asyncio.Event()
        sent_holder: list[str] = []

        async def _fake_publish(topic, value, **_kw):
            sent_holder.append(value.decode())
            published.set()
            return True, ""

        plugin.publish = _fake_publish  # type: ignore[method-assign]

        async def _gen(*args, **kwargs):
            await published.wait()          # wait until publish has fired
            msg = MagicMock()
            msg.value = sent_holder[0].encode()
            yield msg

        stub = MagicMock()
        stub.Subscribe = MagicMock(side_effect=_gen)
        plugin._stub = stub

        result = await plugin.run_connectivity_test(timeout_sec=10.0)
        assert result["match"] is True
        assert result["sent"] == result["received"]

    @pytest.mark.asyncio
    async def test_no_stub_raises(self, plugin):
        plugin._stub = None
        with pytest.raises(RuntimeError, match="not started"):
            await plugin.run_connectivity_test(timeout_sec=5.0)

    @pytest.mark.asyncio
    async def test_publish_failure_raises(self, plugin):
        async def _bad_publish(topic, value, **_kw):
            return False, "broker unavailable"

        plugin.publish = _bad_publish  # type: ignore[method-assign]

        async def _gen(*args, **kwargs):
            # never yields — should be cancelled
            await asyncio.sleep(60)
            return
            yield  # make it a generator

        stub = MagicMock()
        stub.Subscribe = MagicMock(side_effect=_gen)
        plugin._stub = stub

        with pytest.raises(RuntimeError, match="Publish step failed"):
            await plugin.run_connectivity_test(timeout_sec=5.0)

    @pytest.mark.asyncio
    async def test_receive_timeout_raises(self, plugin):
        async def _ok_publish(topic, value, **_kw):
            return True, ""

        plugin.publish = _ok_publish  # type: ignore[method-assign]

        async def _silent_gen(*args, **kwargs):
            await asyncio.sleep(60)
            return
            yield  # generator that never yields a message

        stub = MagicMock()
        stub.Subscribe = MagicMock(side_effect=_silent_gen)
        plugin._stub = stub

        with pytest.raises(RuntimeError, match="Timed out"):
            await plugin.run_connectivity_test(timeout_sec=2.0)

    @pytest.mark.asyncio
    async def test_message_mismatch_raises(self, plugin):
        async def _ok_publish(topic, value, **_kw):
            return True, ""

        plugin.publish = _ok_publish  # type: ignore[method-assign]

        async def _wrong_gen(*args, **kwargs):
            msg = MagicMock()
            msg.value = b"totally different message"
            yield msg

        stub = MagicMock()
        stub.Subscribe = MagicMock(side_effect=_wrong_gen)
        plugin._stub = stub

        with pytest.raises(RuntimeError, match="Message mismatch"):
            await plugin.run_connectivity_test(timeout_sec=5.0)


# ---------------------------------------------------------------------------
# NativeSdkBridgePlugin._check_port_available
# ---------------------------------------------------------------------------

class TestCheckPortAvailable:

    def test_free_port_does_not_raise(self):
        # Find a free ephemeral port
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            free_port = s.getsockname()[1]
        _check_port_available(f"127.0.0.1:{free_port}")  # should not raise

    def test_in_use_port_raises(self):
        # Bind a socket ourselves without SO_REUSEADDR so the OS holds it
        # exclusively, then verify _check_port_available detects it.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):  # Windows
                s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)  # type: ignore[attr-defined]
            s.bind(("127.0.0.1", 0))
            s.listen(1)
            in_use_port = s.getsockname()[1]
            with pytest.raises(RuntimeError, match="already in use"):
                _check_port_available(f"127.0.0.1:{in_use_port}")

    def test_unparseable_address_does_not_raise(self):
        # Should silently skip the check rather than crash
        _check_port_available("not-a-valid-address")


# ---------------------------------------------------------------------------
# NativeSdkBridgePlugin._start_bridge / _stop_bridge
# ---------------------------------------------------------------------------

class TestBridgeLifecycle:
    """Use KafkaJavaBridgePlugin as the concrete subclass under test."""

    @pytest.fixture()
    def live_plugin(self, fake_jar, monkeypatch) -> KafkaJavaBridgePlugin:
        """Plugin with _jar_path set but no subprocess launched."""
        p = KafkaJavaBridgePlugin()
        p._jar_path = str(fake_jar)
        p._port = 59999  # unlikely to be in use
        p._bootstrap_servers = "localhost:9092"
        p._java_exe = "java"
        return p

    @pytest.mark.asyncio
    async def test_start_bridge_launches_popen(self, live_plugin):
        mock_proc = MagicMock()
        mock_proc.stdout = MagicMock()
        mock_proc.stderr = MagicMock()
        mock_proc.returncode = None
        mock_proc.poll.return_value = None

        with patch("mes.framework.plugin.base._check_port_available"), \
             patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            await live_plugin._start_bridge()

        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        assert "java" in cmd[0]
        assert "-jar" in cmd
        assert str(live_plugin._port) in cmd
        assert live_plugin._monitor_task is not None
        live_plugin._monitor_task.cancel()

    @pytest.mark.asyncio
    async def test_start_bridge_checks_port_first(self, live_plugin):
        with patch(
            "mes.framework.plugin.base._check_port_available",
            side_effect=RuntimeError("port 59999 already in use"),
        ):
            with pytest.raises(RuntimeError, match="already in use"):
                await live_plugin._start_bridge()

        assert live_plugin._bridge_proc is None

    @pytest.mark.asyncio
    async def test_stop_bridge_terminates_process(self, live_plugin):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = None   # still running
        live_plugin._bridge_proc = mock_proc

        with patch("mes.framework.plugin.base._terminate_proc") as mock_term:
            await live_plugin._stop_bridge()

        mock_term.assert_called_once_with(mock_proc)
        assert live_plugin._bridge_proc is None

    @pytest.mark.asyncio
    async def test_stop_bridge_noop_if_already_stopped(self, live_plugin):
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0   # already exited
        live_plugin._bridge_proc = mock_proc

        with patch("mes.framework.plugin.base._terminate_proc") as mock_term:
            await live_plugin._stop_bridge()

        mock_term.assert_not_called()
