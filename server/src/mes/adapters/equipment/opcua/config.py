"""
OPC-UA Equipment Adapter: Configuration settings.

All settings are read from environment variables with MES_ prefix
alongside the base settings.  These extend the core EQUIP_OPCUA_URL
already defined in config.py.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OPCUASettings(BaseSettings):
    """
    OPC-UA specific configuration.

    Env vars (all prefixed MES_):
        MES_EQUIP_OPCUA_URL             opc.tcp://... endpoint
        MES_EQUIP_OPCUA_SECURITY_MODE   none | sign | sign_and_encrypt
        MES_EQUIP_OPCUA_SECURITY_POLICY none | Basic256Sha256 | Aes128Sha256RsaOaep
        MES_EQUIP_OPCUA_AUTH_TYPE       anonymous | username | certificate
        MES_EQUIP_OPCUA_USERNAME        username for username auth
        MES_EQUIP_OPCUA_PASSWORD        password for username auth
        MES_EQUIP_OPCUA_CLIENT_CERT     path to client X.509 certificate (DER)
        MES_EQUIP_OPCUA_CLIENT_KEY      path to client private key (PEM)
        MES_EQUIP_OPCUA_SERVER_CERT     path to trusted server certificate (DER)
        MES_EQUIP_OPCUA_NAMESPACE       default namespace index for tag resolution
        MES_EQUIP_OPCUA_EQUIPMENT_ID    equipment identifier for state reporting
        MES_EQUIP_OPCUA_STATE_TAG       OPC-UA node for equipment state
        MES_EQUIP_OPCUA_REQUEST_TIMEOUT request timeout in seconds
        MES_EQUIP_OPCUA_SESSION_TIMEOUT session timeout in milliseconds
        MES_EQUIP_OPCUA_SUB_INTERVAL_MS default subscription sampling interval
    """

    # Connection
    EQUIP_OPCUA_URL: str = ""
    EQUIP_OPCUA_SECURITY_MODE: str = "none"  # none | sign | sign_and_encrypt
    EQUIP_OPCUA_SECURITY_POLICY: str = "none"  # none | Basic256Sha256 | Aes128Sha256RsaOaep
    EQUIP_OPCUA_AUTH_TYPE: str = "anonymous"  # anonymous | username | certificate
    EQUIP_OPCUA_USERNAME: str = ""
    EQUIP_OPCUA_PASSWORD: str = ""
    EQUIP_OPCUA_CLIENT_CERT: str = ""
    EQUIP_OPCUA_CLIENT_KEY: str = ""
    EQUIP_OPCUA_SERVER_CERT: str = ""

    # Namespace and tag resolution
    EQUIP_OPCUA_NAMESPACE: int = Field(default=2, ge=0)

    # Equipment identity
    EQUIP_OPCUA_EQUIPMENT_ID: str = "OPCUA-EQUIP-01"

    # State mapping: tag whose value represents equipment state
    EQUIP_OPCUA_STATE_TAG: str = ""

    # Timeouts
    EQUIP_OPCUA_REQUEST_TIMEOUT: int = Field(default=10, ge=1)
    EQUIP_OPCUA_SESSION_TIMEOUT: int = Field(default=60000, ge=1000)  # ms

    # Subscriptions
    EQUIP_OPCUA_SUB_INTERVAL_MS: int = Field(default=1000, ge=50)

    model_config = SettingsConfigDict(
        env_prefix="MES_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
