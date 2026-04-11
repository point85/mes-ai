"""
AVEVA Historian Adapter: Configuration settings.

All settings are read from environment variables with MES_ prefix.
The Historian Data REST API v2 is OData-based and uses FQN
(datasource.tagname) addressing.

Ref: https://docs.aveva.com/bundle/sp-historian/page/338478.html
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AVEVAHistorianSettings(BaseSettings):
    """
    AVEVA Historian REST API v2 configuration.

    Env vars (all prefixed MES_):
        MES_AVEVA_BASE_URL          Historian REST API base URL
        MES_AVEVA_AUTH_MODE         negotiate | bearer | basic
        MES_AVEVA_USERNAME          DOMAIN\\user for negotiate, or user for basic
        MES_AVEVA_PASSWORD          password
        MES_AVEVA_BEARER_TOKEN      bearer token for AVEVA Insight (cloud)
        MES_AVEVA_VERIFY_SSL        verify SSL certificate
        MES_AVEVA_TIMEOUT_SEC       HTTP request timeout
        MES_AVEVA_DATASOURCE        default data source name (e.g. Baytown)
        MES_AVEVA_EQUIPMENT_ID      MES equipment UUID this historian maps to
        MES_AVEVA_TAG_PREFIX        FQN prefix for tag filtering
        MES_AVEVA_STATE_TAG_FQN     FQN for equipment state monitoring
        MES_AVEVA_STATE_MODEL_ID    state model (packml, semi_e10)
        MES_AVEVA_POLL_INTERVAL_SEC polling interval for subscriptions
    """

    # Connection
    AVEVA_BASE_URL: str = ""  # e.g. http://historian:32569/Historian/v2
    AVEVA_AUTH_MODE: str = "negotiate"  # negotiate | bearer | basic
    AVEVA_USERNAME: str = ""
    AVEVA_PASSWORD: str = ""
    AVEVA_BEARER_TOKEN: str = ""
    AVEVA_VERIFY_SSL: bool = True
    AVEVA_TIMEOUT_SEC: int = Field(default=30, ge=1)

    # Data source and equipment identity
    AVEVA_DATASOURCE: str = ""  # Default historian data source
    AVEVA_EQUIPMENT_ID: str = ""  # MES equipment id this historian maps to
    AVEVA_TAG_PREFIX: str = ""  # Filter prefix for FQN browsing

    # State monitoring
    AVEVA_STATE_TAG_FQN: str = ""  # FQN for equipment state tag
    AVEVA_STATE_MODEL_ID: str = ""  # packml | semi_e10

    # Polling
    AVEVA_POLL_INTERVAL_SEC: int = Field(default=5, ge=1)

    model_config = SettingsConfigDict(
        env_prefix="MES_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
