"""
STOMP JMS Adapter: Low-level STOMP client wrapper.

Wraps the stomp.py library to provide:
- Async-friendly connect/disconnect lifecycle
- SSL/TLS support
- Heartbeat configuration
- Automatic reconnection with configurable retry
- Message send/subscribe/unsubscribe
- Callback-driven message receipt

The client runs stomp.py's listener in a background thread (as stomp.py
is thread-based) and bridges callbacks to asyncio via run_coroutine_threadsafe.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from collections.abc import Callable
from typing import Any

from .config import STOMPSettings

logger = logging.getLogger("mes.adapters.messaging.stomp")


class STOMPListener:
    """
    stomp.py listener that bridges incoming messages to an async callback.

    stomp.py invokes listener methods from its receiver thread, so we use
    asyncio.run_coroutine_threadsafe to dispatch into the event loop.
    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        on_message: Callable[[str, dict[str, str], str], Any],
        on_error: Callable[[dict[str, str], str], Any] | None = None,
    ) -> None:
        self._loop = loop
        self._on_message = on_message
        self._on_error = on_error
        self._connected = threading.Event()

    def on_connected(self, frame: Any) -> None:
        logger.info("STOMP connected: %s", frame.headers.get("server", "unknown"))
        self._connected.set()

    def on_message(self, frame: Any) -> None:
        destination = frame.headers.get("destination", "")
        body = frame.body if isinstance(frame.body, str) else frame.body.decode("utf-8")
        headers = dict(frame.headers)
        try:
            asyncio.run_coroutine_threadsafe(
                self._on_message(destination, headers, body),
                self._loop,
            )
        except Exception:
            logger.exception("Error dispatching STOMP message from %s", destination)

    def on_error(self, frame: Any) -> None:
        body = frame.body if isinstance(frame.body, str) else frame.body.decode("utf-8")
        headers = dict(frame.headers)
        logger.error("STOMP error frame: %s — %s", headers, body)
        if self._on_error:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._on_error(headers, body),
                    self._loop,
                )
            except Exception:
                logger.exception("Error dispatching STOMP error")

    def on_disconnected(self) -> None:
        logger.warning("STOMP disconnected")
        self._connected.clear()

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()


class STOMPClient:
    """
    Async-friendly wrapper around the stomp.py Connection.

    Lifecycle: create → connect() → send/subscribe → disconnect()
    """

    def __init__(
        self,
        settings: STOMPSettings,
        on_message: Callable[[str, dict[str, str], str], Any],
        on_error: Callable[[dict[str, str], str], Any] | None = None,
    ) -> None:
        self._settings = settings
        self._on_message = on_message
        self._on_error = on_error
        self._conn: Any = None
        self._listener: STOMPListener | None = None
        self._subscription_counter = 0

    async def connect(self) -> None:
        """Connect to the STOMP broker."""
        import stomp

        loop = asyncio.get_running_loop()
        self._listener = STOMPListener(loop, self._on_message, self._on_error)

        host_and_port = [(self._settings.STOMP_BROKER_HOST, self._settings.STOMP_BROKER_PORT)]

        if self._settings.STOMP_USE_SSL:
            self._conn = stomp.Connection(
                host_and_ports=host_and_port,
                heartbeats=(
                    self._settings.STOMP_HEARTBEAT_SEND_MS,
                    self._settings.STOMP_HEARTBEAT_RECV_MS,
                ),
                reconnect_attempts_max=self._settings.STOMP_RECONNECT_ATTEMPTS,
                reconnect_sleep_initial=self._settings.STOMP_RECONNECT_DELAY_SEC,
            )
            self._conn.set_ssl(host_and_port)
        else:
            self._conn = stomp.Connection(
                host_and_ports=host_and_port,
                heartbeats=(
                    self._settings.STOMP_HEARTBEAT_SEND_MS,
                    self._settings.STOMP_HEARTBEAT_RECV_MS,
                ),
                reconnect_attempts_max=self._settings.STOMP_RECONNECT_ATTEMPTS,
                reconnect_sleep_initial=self._settings.STOMP_RECONNECT_DELAY_SEC,
            )

        self._conn.set_listener("mes-stomp", self._listener)

        connect_kwargs: dict[str, Any] = {"wait": True}
        if self._settings.STOMP_USERNAME:
            connect_kwargs["username"] = self._settings.STOMP_USERNAME
            connect_kwargs["passcode"] = self._settings.STOMP_PASSWORD
        if self._settings.STOMP_VHOST != "/":
            connect_kwargs["headers"] = {"host": self._settings.STOMP_VHOST}

        await loop.run_in_executor(None, lambda: self._conn.connect(**connect_kwargs))
        logger.info(
            "STOMP client connected to %s:%d",
            self._settings.STOMP_BROKER_HOST,
            self._settings.STOMP_BROKER_PORT,
        )

    async def disconnect(self) -> None:
        """Disconnect from the STOMP broker."""
        if self._conn and self._conn.is_connected():
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._conn.disconnect)
            logger.info("STOMP client disconnected")
        self._conn = None
        self._listener = None

    def subscribe(self, destination: str, ack: str = "auto") -> str:
        """
        Subscribe to a broker destination.

        Args:
            destination: Queue or topic path (e.g. /queue/mes.inbound, /topic/events).
            ack: Acknowledgement mode — 'auto', 'client', or 'client-individual'.

        Returns:
            Subscription ID for later unsubscribe.
        """
        if not self._conn:
            raise RuntimeError("STOMP client not connected")
        self._subscription_counter += 1
        sub_id = f"mes-sub-{self._subscription_counter}"
        self._conn.subscribe(destination=destination, id=sub_id, ack=ack)
        logger.info("Subscribed to %s (id=%s, ack=%s)", destination, sub_id, ack)
        return sub_id

    def unsubscribe(self, sub_id: str) -> None:
        """Unsubscribe from a destination by subscription ID."""
        if self._conn and self._conn.is_connected():
            self._conn.unsubscribe(id=sub_id)
            logger.info("Unsubscribed %s", sub_id)

    def send(
        self,
        destination: str,
        body: str,
        content_type: str = "application/json",
        headers: dict[str, str] | None = None,
    ) -> None:
        """
        Send a message to a broker destination.

        Args:
            destination: Queue or topic path.
            body: Message body (typically JSON).
            content_type: Content-Type header value.
            headers: Additional STOMP headers.
        """
        if not self._conn:
            raise RuntimeError("STOMP client not connected")
        send_headers = {"content-type": content_type}
        if headers:
            send_headers.update(headers)
        self._conn.send(destination=destination, body=body, headers=send_headers)
        logger.debug("Sent message to %s (%d bytes)", destination, len(body))

    @property
    def is_connected(self) -> bool:
        """Check if the client is connected to the broker."""
        if self._conn is None:
            return False
        return self._conn.is_connected()

    async def health_check(self) -> bool:
        """Return True if connected to the broker."""
        return self.is_connected
