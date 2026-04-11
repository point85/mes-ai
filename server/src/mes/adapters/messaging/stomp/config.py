"""
STOMP JMS Adapter: Configuration settings.

All settings are read from environment variables with MES_ prefix
or supplied via plugin config parameters.

Env vars:
    MES_STOMP_BROKER_HOST              Broker hostname (default localhost)
    MES_STOMP_BROKER_PORT              STOMP port (default 61613)
    MES_STOMP_USE_SSL                  Enable SSL/TLS (default false)
    MES_STOMP_USERNAME                 Username for broker auth
    MES_STOMP_PASSWORD                 Password for broker auth
    MES_STOMP_VHOST                    Virtual host (default /)
    MES_STOMP_HEARTBEAT_SEND_MS       Heartbeat send interval (default 10000)
    MES_STOMP_HEARTBEAT_RECV_MS       Heartbeat recv interval (default 10000)
    MES_STOMP_RECONNECT_ATTEMPTS      Max reconnect attempts (default 10)
    MES_STOMP_RECONNECT_DELAY_SEC     Delay between reconnects (default 5)
    MES_STOMP_INBOUND_SUBSCRIPTIONS   Comma-separated broker destinations to subscribe to
    MES_STOMP_OUTBOUND_DESTINATION    Default broker destination for outbound messages
    MES_STOMP_EVENT_SUBSCRIPTIONS     Comma-separated MES event topics to forward outbound
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class STOMPSettings(BaseSettings):
    """STOMP-specific configuration for the JMS messaging adapter."""

    model_config = SettingsConfigDict(env_prefix="MES_", env_file=".env", extra="ignore")

    # Connection
    STOMP_BROKER_HOST: str = "localhost"
    STOMP_BROKER_PORT: int = Field(default=61613, ge=1, le=65535)
    STOMP_USE_SSL: bool = False
    STOMP_USERNAME: str = ""
    STOMP_PASSWORD: str = ""
    STOMP_VHOST: str = "/"

    # Heartbeat (milliseconds)
    STOMP_HEARTBEAT_SEND_MS: int = Field(default=10000, ge=0)
    STOMP_HEARTBEAT_RECV_MS: int = Field(default=10000, ge=0)

    # Reconnection
    STOMP_RECONNECT_ATTEMPTS: int = Field(default=10, ge=0)
    STOMP_RECONNECT_DELAY_SEC: int = Field(default=5, ge=1)

    # Messaging
    STOMP_INBOUND_SUBSCRIPTIONS: str = "/queue/mes.inbound"
    STOMP_OUTBOUND_DESTINATION: str = "/topic/mes.events"
    STOMP_EVENT_SUBSCRIPTIONS: str = "*"
