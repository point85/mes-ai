"""
OPC-UA Equipment Adapter: asyncua client wrapper.

Manages the OPC-UA session lifecycle, security setup, NodeId resolution,
read/write operations, and data change subscriptions.

Requires the `asyncua` package (optional dependency):
    pip install asyncua
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from mes.adapters.equipment.exceptions import (
    CommunicationTimeoutError,
    EquipmentConnectionError,
    TagNotFoundError,
)

from .config import OPCUASettings

logger = logging.getLogger("mes.adapters.equipment.opcua")

# OPC-UA variant type → MES data_type string
_UA_TYPE_MAP: dict[str, str] = {
    "Boolean": "bool",
    "SByte": "int",
    "Byte": "int",
    "Int16": "int",
    "UInt16": "int",
    "Int32": "int",
    "UInt32": "int",
    "Int64": "int",
    "UInt64": "int",
    "Float": "float",
    "Double": "float",
    "String": "string",
    "ByteString": "string",
    "DateTime": "string",
}


class OPCUAClient:
    """
    Async wrapper around asyncua.Client.

    Handles connection, security negotiation, NodeId caching,
    read/write, subscriptions, and address space browsing.
    """

    def __init__(self, opcua_settings: OPCUASettings | None = None) -> None:
        self._settings = opcua_settings or OPCUASettings()
        self._client: Any = None  # asyncua.Client
        self._session_active = False
        self._node_cache: dict[str, Any] = {}  # tag_name → asyncua.Node
        self._subscription: Any = None  # asyncua.Subscription
        self._monitored_items: dict[str, Any] = {}  # tag_name → MonitoredItem handle
        self._callbacks: dict[str, Callable] = {}  # tag_name → user callback
        self._handler: _SubHandler | None = None

    # ──────────────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Establish OPC-UA session with configured security."""
        try:
            from asyncua import Client  # type: ignore[import-not-found]
            from asyncua.crypto.security_policies import SecurityPolicyBasic256Sha256  # type: ignore[import-not-found]
        except ImportError as exc:
            raise EquipmentConnectionError(
                message="asyncua package not installed. Install with: pip install asyncua"
            ) from exc

        url = self._settings.EQUIP_OPCUA_URL
        if not url:
            raise EquipmentConnectionError(message="MES_EQUIP_OPCUA_URL not configured")

        try:
            self._client = Client(
                url=url,
                timeout=self._settings.EQUIP_OPCUA_REQUEST_TIMEOUT,
            )

            # Security setup
            await self._configure_security(SecurityPolicyBasic256Sha256)

            # Authentication
            self._configure_auth()

            # Connect
            await self._client.connect()
            self._session_active = True
            logger.info("OPC-UA connected to %s", url)

        except EquipmentConnectionError:
            raise
        except Exception as exc:
            self._session_active = False
            raise EquipmentConnectionError(
                message=f"OPC-UA connection failed: {exc}"
            ) from exc

    async def disconnect(self) -> None:
        """Close OPC-UA session and clean up subscriptions."""
        if self._subscription:
            try:
                await self._subscription.delete()
            except Exception:
                logger.debug("Subscription cleanup warning (non-fatal)")
            self._subscription = None
            self._monitored_items.clear()
            self._callbacks.clear()

        if self._client and self._session_active:
            try:
                await self._client.disconnect()
            except Exception:
                logger.debug("Disconnect warning (non-fatal)")

        self._session_active = False
        self._node_cache.clear()
        self._handler = None
        logger.info("OPC-UA disconnected")

    async def health_check(self) -> bool:
        """Check if the OPC-UA session is active by reading the server state."""
        if not self._client or not self._session_active:
            return False
        try:
            from asyncua import ua  # type: ignore[import-not-found]
            node = self._client.get_node(ua.ObjectIds.Server_ServerStatus_State)
            await asyncio.wait_for(
                node.read_value(),
                timeout=self._settings.EQUIP_OPCUA_REQUEST_TIMEOUT,
            )
            return True
        except Exception:
            return False

    # ──────────────────────────────────────────────────────────────
    # Tag Operations
    # ──────────────────────────────────────────────────────────────

    async def read_tag(self, tag_name: str) -> tuple[Any, str, str]:
        """
        Read a tag value from the OPC-UA server.

        Returns:
            (value, quality, data_type) tuple.
        """
        node = await self._resolve_node(tag_name)
        try:
            data_value = await asyncio.wait_for(
                node.read_data_value(),
                timeout=self._settings.EQUIP_OPCUA_REQUEST_TIMEOUT,
            )
        except asyncio.TimeoutError as exc:
            raise CommunicationTimeoutError(
                message=f"Timeout reading tag '{tag_name}'"
            ) from exc
        except Exception as exc:
            raise CommunicationTimeoutError(
                message=f"Error reading tag '{tag_name}': {exc}"
            ) from exc

        value = data_value.Value.Value if data_value.Value else None
        quality = _map_status_code(data_value.StatusCode)
        data_type = _map_variant_type(data_value.Value)
        return value, quality, data_type

    async def write_tag(self, tag_name: str, value: Any) -> None:
        """Write a value to an OPC-UA tag."""
        node = await self._resolve_node(tag_name)
        try:
            from asyncua import ua  # type: ignore[import-not-found]

            # Read current data type so we can write with the correct variant type
            dv = await asyncio.wait_for(
                node.read_data_value(),
                timeout=self._settings.EQUIP_OPCUA_REQUEST_TIMEOUT,
            )
            variant_type = dv.Value.VariantType if dv.Value else None

            if variant_type:
                new_value = ua.DataValue(ua.Variant(value, variant_type))
            else:
                new_value = ua.DataValue(ua.Variant(value))

            await asyncio.wait_for(
                node.write_value(new_value),
                timeout=self._settings.EQUIP_OPCUA_REQUEST_TIMEOUT,
            )
        except asyncio.TimeoutError as exc:
            raise CommunicationTimeoutError(
                message=f"Timeout writing tag '{tag_name}'"
            ) from exc
        except Exception as exc:
            raise CommunicationTimeoutError(
                message=f"Error writing tag '{tag_name}': {exc}"
            ) from exc

    async def subscribe_tag(
        self, tag_name: str, callback: Callable, interval_ms: int
    ) -> str:
        """
        Create a monitored item subscription for a tag.

        Returns:
            The handle_id string for later unsubscribe.
        """
        node = await self._resolve_node(tag_name)

        # Lazily create the shared subscription
        if not self._subscription:
            self._handler = _SubHandler(self._callbacks)
            self._subscription = await self._client.create_subscription(
                period=interval_ms,
                handler=self._handler,
            )

        self._callbacks[tag_name] = callback
        handle = await self._subscription.subscribe_data_change(node)
        self._monitored_items[tag_name] = handle

        logger.debug("OPC-UA subscription created for '%s' (interval=%dms)", tag_name, interval_ms)
        return tag_name  # use tag_name as handle ID for simplicity

    async def unsubscribe_tag(self, tag_name: str) -> None:
        """Remove a monitored item subscription."""
        handle = self._monitored_items.pop(tag_name, None)
        self._callbacks.pop(tag_name, None)

        if handle and self._subscription:
            try:
                await self._subscription.unsubscribe(handle)
            except Exception:
                logger.debug("Unsubscribe warning for '%s' (non-fatal)", tag_name)

    async def browse(self, root_node_id: str | None = None) -> list[dict[str, Any]]:
        """
        Browse the OPC-UA address space.

        Returns list of dicts with keys: tag_name, data_type, access, description.
        """
        from asyncua import ua  # type: ignore[import-not-found]

        if root_node_id:
            root = self._client.get_node(root_node_id)
        else:
            # Default: browse Objects folder
            root = self._client.get_node(ua.ObjectIds.ObjectsFolder)

        results: list[dict[str, Any]] = []
        await self._browse_recursive(root, results, depth=0, max_depth=3)
        return results

    async def read_state_tag(self) -> str | None:
        """Read the configured equipment state tag, if any."""
        state_tag = self._settings.EQUIP_OPCUA_STATE_TAG
        if not state_tag:
            return None
        value, _quality, _dtype = await self.read_tag(state_tag)
        return str(value) if value is not None else None

    async def read_equipment_id_tag(self) -> str | None:
        """Read the configured equipment identifier tag, if any."""
        equipment_id_tag = self._settings.EQUIP_OPCUA_EQUIPMENT_ID_TAG
        if not equipment_id_tag:
            return None
        value, _quality, _dtype = await self.read_tag(equipment_id_tag)
        return str(value) if value is not None else None

    # ──────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────

    async def _resolve_node(self, tag_name: str) -> Any:
        """Resolve a tag name to an asyncua Node, using cache."""
        if tag_name in self._node_cache:
            return self._node_cache[tag_name]

        from asyncua import ua  # type: ignore[import-not-found]

        # Try as NodeId string first (e.g. "ns=2;s=Temperature")
        if tag_name.startswith("ns=") or tag_name.startswith("i=") or tag_name.startswith("s="):
            node = self._client.get_node(tag_name)
        else:
            # Treat as string identifier in the configured namespace
            ns = self._settings.EQUIP_OPCUA_NAMESPACE
            node_id = ua.NodeId(tag_name, ns)
            node = self._client.get_node(node_id)

        # Validate the node exists by reading its class
        try:
            await asyncio.wait_for(
                node.read_node_class(),
                timeout=self._settings.EQUIP_OPCUA_REQUEST_TIMEOUT,
            )
        except Exception as exc:
            raise TagNotFoundError(tag_name=tag_name) from exc

        self._node_cache[tag_name] = node
        return node

    async def _configure_security(self, basic256sha256_policy: Any) -> None:
        """Configure OPC-UA security mode and policy."""
        mode = self._settings.EQUIP_OPCUA_SECURITY_MODE.lower()
        policy = self._settings.EQUIP_OPCUA_SECURITY_POLICY

        if mode == "none" or policy == "none":
            return  # No security

        from asyncua import ua  # type: ignore[import-not-found]

        mode_map = {
            "sign": ua.MessageSecurityMode.Sign,
            "sign_and_encrypt": ua.MessageSecurityMode.SignAndEncrypt,
        }
        security_mode = mode_map.get(mode)
        if not security_mode:
            return

        cert_path = self._settings.EQUIP_OPCUA_CLIENT_CERT
        key_path = self._settings.EQUIP_OPCUA_CLIENT_KEY
        server_cert = self._settings.EQUIP_OPCUA_SERVER_CERT

        if cert_path and key_path:
            await self._client.set_security(
                basic256sha256_policy,
                certificate=cert_path,
                private_key=key_path,
                server_certificate=server_cert or None,
                mode=security_mode,
            )

    def _configure_auth(self) -> None:
        """Configure OPC-UA authentication (username/password)."""
        auth_type = self._settings.EQUIP_OPCUA_AUTH_TYPE.lower()

        if auth_type == "username":
            self._client.set_user(self._settings.EQUIP_OPCUA_USERNAME)
            self._client.set_password(self._settings.EQUIP_OPCUA_PASSWORD)
        # anonymous and certificate auth require no additional client config
        # (certificate auth is handled by set_security above)

    async def _browse_recursive(
        self,
        node: Any,
        results: list[dict[str, Any]],
        depth: int,
        max_depth: int,
    ) -> None:
        """Recursively browse the address space up to max_depth."""
        if depth > max_depth:
            return

        from asyncua import ua  # type: ignore[import-not-found]

        try:
            children = await node.get_children()
        except Exception:
            return

        for child in children:
            try:
                node_class = await child.read_node_class()
                browse_name = await child.read_browse_name()
                tag_name = str(child.nodeid)

                if node_class == ua.NodeClass.Variable:
                    try:
                        dv = await child.read_data_value()
                        data_type = _map_variant_type(dv.Value)
                        access = await child.get_access_level()
                        access_str = "readwrite"
                        if access:
                            readable = ua.AccessLevel.CurrentRead in access
                            writable = ua.AccessLevel.CurrentWrite in access
                            if readable and writable:
                                access_str = "readwrite"
                            elif readable:
                                access_str = "read"
                            elif writable:
                                access_str = "write"
                    except Exception:
                        data_type = "string"
                        access_str = "readwrite"

                    results.append({
                        "tag_name": tag_name,
                        "data_type": data_type,
                        "access": access_str,
                        "description": browse_name.Name if browse_name else "",
                    })
                elif node_class == ua.NodeClass.Object:
                    await self._browse_recursive(child, results, depth + 1, max_depth)
            except Exception:
                continue


class _SubHandler:
    """
    OPC-UA subscription handler that dispatches data change
    notifications to registered callbacks.
    """

    def __init__(self, callbacks: dict[str, Callable]) -> None:
        self._callbacks = callbacks

    def datachange_notification(self, node: Any, val: Any, data: Any) -> None:
        """Called by asyncua when a monitored item changes."""
        tag_name = str(node.nodeid)

        callback = self._callbacks.get(tag_name)
        if not callback:
            # Try matching by string identifier
            for key, cb in self._callbacks.items():
                if key in tag_name:
                    callback = cb
                    break

        if callback:
            from mes.adapters.equipment.dtos import TagValue

            tag_value = TagValue(
                tag_name=tag_name,
                value=val,
                quality="good",
                timestamp=datetime.now(timezone.utc),
                data_type=_infer_python_type(val),
            )
            try:
                result = callback(tag_value)
                if asyncio.iscoroutine(result):
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(result)
                    else:
                        loop.run_until_complete(result)
            except Exception:
                logger.exception("Subscription callback error for node %s", tag_name)


def _map_status_code(status_code: Any) -> str:
    """Map OPC-UA StatusCode to quality string."""
    if status_code is None:
        return "uncertain"
    try:
        from asyncua import ua  # type: ignore[import-not-found]
        if status_code == ua.StatusCodes.Good:
            return "good"
        elif status_code == ua.StatusCodes.Bad:
            return "bad"
        # Check if it's a good-range code
        code_val = getattr(status_code, "value", status_code)
        if isinstance(code_val, int) and code_val == 0:
            return "good"
        return "uncertain"
    except Exception:
        return "uncertain"


def _map_variant_type(variant: Any) -> str:
    """Map asyncua Variant to MES data_type string."""
    if variant is None:
        return "string"
    try:
        type_name = variant.VariantType.name
        return _UA_TYPE_MAP.get(type_name, "string")
    except Exception:
        return _infer_python_type(getattr(variant, "Value", None))


def _infer_python_type(value: Any) -> str:
    """Infer MES data_type from a Python value."""
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, (list, tuple)):
        return "array"
    return "string"
