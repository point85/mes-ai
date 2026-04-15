"""
AVEVA Historian Adapter: Configuration settings.

All settings are read from environment variables with MES_ prefix.
The Historian Data REST API v2 is OData-based and uses FQN
(datasource.tagname) addressing.

Supports multiple equipment mappings per historian instance — a single
historian server typically has tags from many pieces of equipment.

Ref: https://docs.aveva.com/bundle/sp-historian/page/338478.html
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class EquipmentMapping(BaseModel):
    """One equipment-to-tag mapping within a historian instance."""

    equipment_id: str = ""
    state_tag_fqn: str = ""
    state_model_id: str = ""
    tag_prefix: str = ""


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

    # Data source
    AVEVA_DATASOURCE: str = ""  # Default historian data source

    # Polling
    AVEVA_POLL_INTERVAL_SEC: int = Field(default=5, ge=1)

    # Equipment mappings (populated from plugin config, not env vars)
    AVEVA_EQUIPMENT_MAPPINGS: list[EquipmentMapping] = Field(default_factory=list)

    model_config = SettingsConfigDict(
        env_prefix="MES_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
