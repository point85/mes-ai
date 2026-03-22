"""
PLUGIN-FW: Base class and extension point definitions for MES plugins.

Every plugin must subclass MESPlugin and implement the lifecycle methods.
Extension points define the categories of functionality a plugin can provide.
"""

from __future__ import annotations

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
