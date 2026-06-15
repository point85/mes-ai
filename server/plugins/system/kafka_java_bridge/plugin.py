"""
Kafka Java Bridge Plugin.

Bridges the Apache Kafka Java SDK into the MES plugin framework via a gRPC
sidecar process.  The Java bridge (a fat-jar built from bridge/pom.xml) is
launched as a child subprocess; the Python plugin communicates with it over
a loopback gRPC channel.

Architecture:
    MES Python server
      └─ KafkaJavaBridgePlugin (this file)
            ├─ asyncio.create_subprocess_exec → kafka-bridge-*.jar (Java, port 50051)
            │     └─ Apache Kafka Java SDK (org.apache.kafka:kafka-clients)
            │           └─ Kafka broker (TCP)
            └─ grpc.aio.Channel → gRPC calls on 127.0.0.1:50051
                  ├─ HealthCheck   (startup polling)
                  ├─ Subscribe     (server-streaming → MES event bus)
                  └─ Publish       (called by other plugins / REST endpoints)

Prerequisites (Python side):
    pip install grpcio grpcio-tools
    python proto/generate_stubs.py   # generates kafka_bridge_pb2*.py

Prerequisites (Java side):
    mvn -f bridge/pom.xml clean package -q
    # produces bridge/target/kafka-bridge-1.0.0-shaded.jar

Configuration example (CLI):
    python -m mes.cli plugin install kafka-java-bridge \\
        --param bootstrap_servers=localhost:9092 \\
        --param topics='["equipment.events","quality.results"]' \\
        --param consumer_group=mes-factory-floor \\
        --param bridge_jar=/path/to/kafka-bridge-1.0.0-shaded.jar \\
        --param bridge_port=50051

    python -m mes.cli plugin enable kafka-java-bridge
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any

from mes.framework.plugin.base import NativeSdkBridgePlugin

logger = logging.getLogger("mes.plugins.kafka_java_bridge")


def _resolve_java_exe(java_home: str = "") -> str:
    """
    Return the ``java`` executable to use.

    Resolution order:
      1. Plugin parameter ``java_home`` (if non-empty).
      2. ``JAVA_HOME`` environment variable (if set).
      3. ``java`` on the system PATH.
    """
    import os

    def _exe_from_home(home: str, source: str) -> str:
        p = Path(home) / "bin" / ("java.exe" if os.name == "nt" else "java")
        if p.is_file():
            return str(p)
        raise RuntimeError(
            f"{source} is set to '{home}' but '{p}' does not exist. "
            "Check that it points to a Java 17+ installation directory."
        )

    if java_home:
        return _exe_from_home(java_home, "java_home plugin parameter")

    env_java_home = os.environ.get("JAVA_HOME", "")
    if env_java_home:
        return _exe_from_home(env_java_home, "JAVA_HOME environment variable")

    return "java"


def _check_java_version(java_exe: str = "java", min_major: int = 17) -> None:
    """
    Verify that *java_exe* meets *min_major*.

    Raises :class:`RuntimeError` with a clear human-readable message so the
    plugin enable step surfaces it immediately instead of entering an infinite
    restart loop.
    """
    try:
        result = subprocess.run(
            [java_exe, "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        raise RuntimeError(
            f"'{java_exe}' not found.  Install Java {min_major}+ and either "
            "set the java_home plugin parameter or add Java's bin/ to PATH."
        )
    # java -version prints to stderr
    output = (result.stderr or result.stdout).strip()
    m = re.search(r'"(\d+)[.\-_]', output)
    if m:
        major = int(m.group(1))
        if major < min_major:
            raise RuntimeError(
                f"Java {min_major}+ is required to run the Kafka bridge jar, "
                f"but '{java_exe}' is version {major}.\n"
                f"  Detected: {output.splitlines()[0]}\n"
                f"Set the java_home plugin parameter to a Java {min_major}+ "
                "installation directory (the folder that contains bin/java)."
            )
        logger.debug("Java version check passed: major=%d (>=%d) [%s]", major, min_major, java_exe)
    else:
        logger.warning("Could not parse Java version from '%s': %s — proceeding anyway", java_exe, output)


# ── Lazy import of generated gRPC stubs ──────────────────────────────────────
# The stubs are generated from proto/kafka_bridge.proto via generate_stubs.py.
# We import them lazily so that the plugin module can be imported for manifest
# inspection even before the stubs have been generated.

_pb2: Any = None
_pb2_grpc: Any = None


def _load_stubs() -> None:
    global _pb2, _pb2_grpc
    if _pb2 is not None:
        return
    _proto_dir = Path(__file__).parent / "proto"
    if not (_proto_dir / "kafka_bridge_pb2.py").exists():
        raise RuntimeError(
            "Generated gRPC stubs not found.  Run:\n"
            f"  python {_proto_dir / 'generate_stubs.py'}"
        )
    import importlib.util
    import types
    import sys

    # kafka_bridge_pb2_grpc.py contains `from . import kafka_bridge_pb2`, which
    # is a relative import.  Loading files as bare top-level modules gives them
    # no parent package, causing "attempted relative import with no known parent
    # package".  Solution: create a synthetic package and load both stubs as
    # sub-modules of it so the relative import resolves correctly.
    pkg_name = "_kafka_bridge_proto"
    if pkg_name not in sys.modules:
        pkg = types.ModuleType(pkg_name)
        pkg.__path__ = [str(_proto_dir)]   # type: ignore[attr-defined]
        pkg.__package__ = pkg_name
        sys.modules[pkg_name] = pkg

    for short_name, file_name in [
        ("kafka_bridge_pb2",      "kafka_bridge_pb2.py"),
        ("kafka_bridge_pb2_grpc", "kafka_bridge_pb2_grpc.py"),
    ]:
        full_name = f"{pkg_name}.{short_name}"
        if full_name not in sys.modules:
            spec = importlib.util.spec_from_file_location(
                full_name, str(_proto_dir / file_name),
            )
            mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
            mod.__package__ = pkg_name
            sys.modules[full_name] = mod
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            # Attach as attribute so `from . import <name>` resolves via the package
            setattr(sys.modules[pkg_name], short_name, mod)

    _pb2      = sys.modules[f"{pkg_name}.kafka_bridge_pb2"]
    _pb2_grpc = sys.modules[f"{pkg_name}.kafka_bridge_pb2_grpc"]


# ─────────────────────────────────────────────────────────────────────────────


class KafkaJavaBridgePlugin(NativeSdkBridgePlugin):
    """
    MES plugin that connects to Kafka via the official Apache Kafka Java SDK.

    The Java bridge sidecar process is managed entirely by the
    :class:`NativeSdkBridgePlugin` base class (launch, stdout/stderr logging,
    auto-restart on crash).  This class owns the gRPC channel lifecycle and
    translates incoming Kafka records into :class:`~mes.framework.events.schema.MESEvent`
    objects on the MES event bus.
    """

    def __init__(self) -> None:
        super().__init__()
        self._config: dict[str, Any] = {}
        self._channel: Any = None   # grpc.aio.Channel
        self._stub: Any = None      # KafkaBridgeStub
        self._consumer_task: asyncio.Task[None] | None = None
        self._port: int = 50051
        self._jar_path: str = ""
        self._java_exe: str = "java"
        self._bootstrap_servers: str = "localhost:9092"
        self._topics: list[str] = []
        self._consumer_group: str = "mes-kafka-bridge"
        self._poll_timeout_ms: int = 1000
        self._mes_event_type: str = "data.collected"

    # ── NativeSdkBridgePlugin ─────────────────────────────────────────────────

    def bridge_command(self) -> list[str]:
        """Return the command to launch the Java bridge fat-jar."""
        return [
            self._java_exe,
            "-jar", self._jar_path,
            "--port",               str(self._port),
            "--bootstrap-servers",  self._bootstrap_servers,
            "--bind-address",       "127.0.0.1",
        ]

    @property
    def bridge_address(self) -> str:
        return f"127.0.0.1:{self._port}"

    @property
    def bridge_startup_timeout_sec(self) -> float:
        return float(self._config.get("startup_timeout_sec", 60.0))

    # ── MESPlugin lifecycle ───────────────────────────────────────────────────

    async def initialize(self, config: dict[str, Any]) -> None:
        _load_stubs()
        self._config = config

        self._jar_path          = config["bridge_jar"]
        self._port              = int(config.get("bridge_port",      50051))
        self._java_exe          = _resolve_java_exe(config.get("java_home", ""))
        self._bootstrap_servers = config.get("bootstrap_servers",    "localhost:9092")
        self._consumer_group    = config.get("consumer_group",       "mes-kafka-bridge")
        self._poll_timeout_ms   = int(config.get("poll_timeout_ms",  1000))
        self._mes_event_type    = config.get("mes_event_type",       "data.collected")

        # topics: accept JSON array string or comma-separated plain string
        raw_topics = config.get("topics", "[]")
        if isinstance(raw_topics, str):
            raw_topics = raw_topics.strip()
            if raw_topics.startswith("["):
                self._topics = json.loads(raw_topics)
            else:
                self._topics = [t.strip() for t in raw_topics.split(",") if t.strip()]
        else:
            self._topics = list(raw_topics)

        if not Path(self._jar_path).is_file():
            raise FileNotFoundError(
                f"Kafka bridge jar not found: {self._jar_path}\n"
                "Build it with:  mvn -f bridge/pom.xml clean package -q"
            )

        _check_java_version(self._java_exe, min_major=17)

        logger.info(
            "Kafka bridge plugin initialised — broker=%s topics=%s port=%d",
            self._bootstrap_servers, self._topics, self._port,
        )

    async def start(self) -> None:
        import grpc.aio  # type: ignore[import]

        # 1. Launch the Java subprocess (base class)
        await self._start_bridge()

        # 2. Wait until the bridge is ready (health-check polling).
        #    On any failure, kill the subprocess so its port is released
        #    immediately and a subsequent enable attempt can succeed.
        try:
            await self._wait_for_healthy()
        except Exception:
            logger.warning(
                "Bridge startup failed — terminating subprocess to release port %d", self._port
            )
            await self._stop_bridge()
            raise

        # 3. Open persistent gRPC channel
        self._channel = grpc.aio.insecure_channel(
            self.bridge_address,
            options=[
                ("grpc.keepalive_time_ms",              30_000),
                ("grpc.keepalive_timeout_ms",           10_000),
                ("grpc.keepalive_permit_without_calls", 1),
            ],
        )
        self._stub = _pb2_grpc.KafkaBridgeStub(self._channel)

        # 4. Start the streaming consumer task
        if self._topics:
            self._consumer_task = asyncio.create_task(
                self._consume_loop(), name="kafka-java-bridge-consumer"
            )
            logger.info("Kafka consumer stream started for topics: %s", self._topics)
        else:
            logger.info("No topics configured — subscribe-only mode (publish available)")

    async def stop(self) -> None:
        # 1. Cancel consumer stream
        if self._consumer_task is not None:
            self._consumer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._consumer_task
            self._consumer_task = None

        # 2. Close gRPC channel
        if self._channel is not None:
            await self._channel.close(grace=2.0)
            self._channel = None
            self._stub = None

        # 3. Terminate Java subprocess (base class)
        await self._stop_bridge()
        logger.info("Kafka bridge plugin stopped")

    async def health_check(self) -> bool:
        if self._stub is None:
            return False
        try:
            resp = await self._stub.HealthCheck(
                _pb2.HealthRequest(), timeout=3.0
            )
            return bool(resp.healthy)
        except Exception:  # noqa: BLE001
            return False

    # ── Public API ────────────────────────────────────────────────────────────

    async def publish(
        self,
        topic: str,
        value: bytes,
        *,
        key: str = "",
        headers: dict[str, str] | None = None,
    ) -> tuple[bool, str]:
        """
        Publish a message to Kafka via the Java bridge.

        Returns ``(success, error_message)``.  On success ``error_message`` is empty.
        Can be called by other plugins or REST route handlers that obtain this
        plugin instance via ``PluginManager.get_plugin("kafka-java-bridge")``.
        """
        if self._stub is None:
            return False, "Plugin not started"
        request = _pb2.PublishRequest(
            topic=topic,
            key=key,
            value=value,
            headers=headers or {},
        )
        try:
            resp = await self._stub.Publish(request, timeout=15.0)
            return resp.success, resp.error
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

    async def run_connectivity_test(self, timeout_sec: float = 35.0) -> dict[str, Any]:
        """
        Round-trip Kafka connectivity test.

        Steps:
          1. Start an active consumer task on a unique throw-away topic so the
             gRPC RPC is immediately initiated and the Java KafkaConsumer begins
             its group-join protocol.
          2. Wait for Kafka's initial rebalance delay (default 3 s broker-side)
             plus a safety margin so the consumer has a committed partition
             assignment *before* we publish.
          3. Publish a test message to that topic.
          4. Read the message back through the queue the consumer task fills.
          5. Verify the received value matches what was sent.

        Why the wait matters: the Java bridge uses ``auto.offset.reset=latest``.
        If we publish before the consumer has been assigned its starting offset
        (which the broker sets to the current high-watermark), the message lands
        *below* that offset and is never delivered.

        Returns a dict with ``topic``, ``sent``, ``received``, and ``match`` keys.
        Raises :class:`RuntimeError` on any failure.
        """
        import uuid
        import time as _time

        if self._stub is None:
            raise RuntimeError("Plugin not started — stub is None")

        test_topic = f"mes-bridge-test-{uuid.uuid4().hex[:8]}"
        test_group = f"__mes_test_{uuid.uuid4().hex[:8]}__"
        sent_value = f"MES Kafka round-trip test {_time.time()}"

        # Queue filled by the consumer task as messages arrive.
        received_queue: asyncio.Queue[str] = asyncio.Queue()

        sub_req = _pb2.SubscribeRequest(
            topics=[test_topic],
            consumer_group=test_group,
            poll_timeout_ms=500,
        )

        async def _consume() -> None:
            """
            Actively iterate the Subscribe stream so the gRPC RPC is initiated
            immediately (grpc.aio does not send the request until the first
            iteration).  Messages are pushed into *received_queue*.
            """
            try:
                async for msg in self._stub.Subscribe(sub_req):
                    await received_queue.put(
                        msg.value.decode("utf-8", errors="replace")
                    )
            except asyncio.CancelledError:
                pass
            except Exception as exc:  # noqa: BLE001
                logger.debug("Connectivity test consumer task error: %s", exc)

        # 1. Start the consumer task.  The first iteration of the async-for
        #    loop inside _consume() sends the Subscribe RPC to the Java bridge,
        #    which starts the KafkaConsumer on a background thread.
        consumer_task = asyncio.create_task(_consume())

        # 2. Wait for the Kafka group coordinator to finish the initial
        #    rebalance and assign a partition to our consumer.
        #    group.initial.rebalance.delay.ms defaults to 3000 ms broker-side;
        #    we add 2 s of margin for broker round-trips and topic auto-creation.
        _REBALANCE_WAIT_SEC = 5.0
        await asyncio.sleep(_REBALANCE_WAIT_SEC)

        try:
            # 3. Publish
            ok, err = await self.publish(test_topic, sent_value.encode())
            if not ok:
                raise RuntimeError(f"Publish step failed: {err}")
            logger.info(
                "Connectivity test: published '%s' to '%s'", sent_value, test_topic
            )

            # 4. Receive
            remaining = max(timeout_sec - _REBALANCE_WAIT_SEC - 1.0, 5.0)
            try:
                received_value = await asyncio.wait_for(
                    received_queue.get(), timeout=remaining
                )
            except asyncio.TimeoutError:
                raise RuntimeError(
                    f"Timed out after {timeout_sec:.0f}s waiting for message on "
                    f"'{test_topic}'. Check that the Kafka broker is reachable and "
                    "that auto.create.topics.enable=true on the broker."
                )
        finally:
            consumer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await consumer_task

        # 5. Validate
        if received_value != sent_value:
            raise RuntimeError(
                f"Message mismatch — sent: '{sent_value}', received: '{received_value}'"
            )

        logger.info(
            "Connectivity test passed: topic=%s sent=%r received=%r",
            test_topic, sent_value, received_value,
        )
        return {
            "topic": test_topic,
            "sent": sent_value,
            "received": received_value,
            "match": True,
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _wait_for_healthy(self) -> None:
        """
        Poll the bridge HealthCheck RPC until the Java process is ready.

        We allow a grace period equal to ``bridge_startup_timeout_sec`` to
        account for JVM startup time (typically 3-8 s on a factory PC).
        """
        import grpc  # type: ignore[import]
        import grpc.aio

        deadline = asyncio.get_event_loop().time() + self.bridge_startup_timeout_sec
        attempt = 0

        # Open a temporary channel just for the health poll
        async with grpc.aio.insecure_channel(self.bridge_address) as probe_channel:
            probe_stub = _pb2_grpc.KafkaBridgeStub(probe_channel)
            while asyncio.get_event_loop().time() < deadline:
                attempt += 1
                try:
                    resp = await probe_stub.HealthCheck(
                        _pb2.HealthRequest(), timeout=2.0
                    )
                    if resp.healthy:
                        logger.info(
                            "Bridge healthy after %d attempt(s) — version=%s broker=%s",
                            attempt, resp.version, resp.kafka_broker,
                        )
                        return
                    logger.debug("Bridge alive but not healthy yet (attempt %d)", attempt)
                except grpc.aio.AioRpcError:
                    logger.debug("Bridge not yet reachable (attempt %d)", attempt)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Health poll error (attempt %d): %s", attempt, exc)

                await asyncio.sleep(0.75)

        raise RuntimeError(
            f"Kafka bridge did not become healthy within "
            f"{self.bridge_startup_timeout_sec:.0f}s "
            f"(tried {attempt} times)"
        )

    async def _consume_loop(self) -> None:
        """
        Maintain a server-streaming Subscribe RPC to the Java bridge.

        Each received :class:`KafkaMessage` is converted to a
        :class:`~mes.framework.events.schema.MESEvent` and published on the
        MES event bus under the configured ``mes_event_type`` topic.

        If the stream is interrupted (gRPC error, bridge restart), the loop
        waits briefly and reopens the stream so no manual intervention is
        needed.
        """
        import grpc  # type: ignore[import]

        request = _pb2.SubscribeRequest(
            topics=self._topics,
            consumer_group=self._consumer_group,
            poll_timeout_ms=self._poll_timeout_ms,
        )

        while True:
            try:
                logger.debug("Opening Subscribe stream for topics: %s", self._topics)
                async for msg in self._stub.Subscribe(request):
                    await self._on_kafka_message(msg)

                # onCompleted reached — bridge closed the stream cleanly
                logger.info("Subscribe stream ended cleanly — reopening")

            except asyncio.CancelledError:
                logger.debug("Consumer task cancelled")
                return

            except grpc.aio.AioRpcError as exc:
                logger.warning(
                    "Subscribe stream error (%s) — will retry in 5 s: %s",
                    exc.code(), exc.details(),
                )
                await asyncio.sleep(5.0)

            except Exception as exc:  # noqa: BLE001
                logger.error("Unexpected consumer error — retrying in 5 s: %s", exc)
                await asyncio.sleep(5.0)

    async def _on_kafka_message(self, msg: Any) -> None:
        """
        Convert a gRPC :class:`KafkaMessage` to a :class:`MESEvent` and publish
        it on the MES event bus.

        The raw Kafka record value bytes are decoded as UTF-8 (with replacement
        for non-UTF-8 payloads — binary payloads are available as hex in the
        ``value_hex`` field).
        """
        from mes.framework.events.bus import event_bus
        from mes.framework.events.schema import MESEvent

        value_bytes: bytes = msg.value
        payload: dict[str, Any] = {
            "topic":        msg.topic,
            "partition":    msg.partition,
            "offset":       msg.offset,
            "key":          msg.key,
            "value":        value_bytes.decode("utf-8", errors="replace"),
            "timestamp_ms": msg.timestamp_ms,
            "headers":      dict(msg.headers),
        }
        # Include hex encoding so consumers can recover binary payloads
        if not value_bytes.isascii():
            payload["value_hex"] = value_bytes.hex()

        event = MESEvent(
            event_type=self._mes_event_type,
            source=f"kafka_java_bridge:{msg.topic}",
            payload=payload,
        )
        await event_bus.publish(event)
        logger.debug(
            "Published event %s from kafka/%s:%d@%d",
            event.event_id, msg.topic, msg.partition, msg.offset,
        )
