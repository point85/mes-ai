"""
MQTT Equipment Adapter: Configuration settings.

All settings are read from environment variables with MES_ prefix.

Env vars:
    MES_EQUIP_MQTT_BROKER_HOST        Broker hostname (default localhost)
    MES_EQUIP_MQTT_BROKER_PORT        Broker port (default 1883, 8883 for TLS)
    MES_EQUIP_MQTT_USE_TLS            Enable TLS (default false)
    MES_EQUIP_MQTT_TLS_CA_CERT        Path to CA certificate
    MES_EQUIP_MQTT_TLS_CLIENT_CERT    Path to client certificate
    MES_EQUIP_MQTT_TLS_CLIENT_KEY     Path to client private key
    MES_EQUIP_MQTT_USERNAME           Username for broker auth
    MES_EQUIP_MQTT_PASSWORD           Password for broker auth
    MES_EQUIP_MQTT_CLIENT_ID          MQTT client ID
    MES_EQUIP_MQTT_EQUIPMENT_ID       Equipment identifier for state reporting
    MES_EQUIP_MQTT_TOPIC_PREFIX       Base topic prefix (default mes/equipment)
    MES_EQUIP_MQTT_STATE_TOPIC        Topic for equipment state
    MES_EQUIP_MQTT_QOS                Quality of Service (0, 1, or 2)
    MES_EQUIP_MQTT_KEEPALIVE          Keepalive interval in seconds
    MES_EQUIP_MQTT_RECONNECT_INTERVAL Reconnect interval in seconds
    MES_EQUIP_MQTT_TIMEOUT            Operation timeout in seconds
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MQTTSettings(BaseSettings):
    """MQTT-specific configuration for the equipment adapter."""

    # Connection
    EQUIP_MQTT_BROKER_HOST: str = "localhost"
    EQUIP_MQTT_BROKER_PORT: int = Field(default=1883, ge=1, le=65535)
    EQUIP_MQTT_USE_TLS: bool = False
    EQUIP_MQTT_TLS_CA_CERT: str = ""
    EQUIP_MQTT_TLS_CLIENT_CERT: str = ""
    EQUIP_MQTT_TLS_CLIENT_KEY: str = ""

    # Authentication
    EQUIP_MQTT_USERNAME: str = ""
    EQUIP_MQTT_PASSWORD: str = ""

    # Client identity
    EQUIP_MQTT_CLIENT_ID: str = "mes-mqtt-equip-01"

    # Equipment identity
    EQUIP_MQTT_EQUIPMENT_ID: str = "MQTT-EQUIP-01"

    # Topics
    EQUIP_MQTT_TOPIC_PREFIX: str = "mes/equipment"
    EQUIP_MQTT_STATE_TOPIC: str = ""

    # QoS and timing
    EQUIP_MQTT_QOS: int = Field(default=1, ge=0, le=2)
    EQUIP_MQTT_KEEPALIVE: int = Field(default=60, ge=5)
    EQUIP_MQTT_RECONNECT_INTERVAL: int = Field(default=5, ge=1)
    EQUIP_MQTT_TIMEOUT: int = Field(default=10, ge=1)

    model_config = SettingsConfigDict(
        env_prefix="MES_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
