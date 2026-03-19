"""
Oracle Cloud ERP: Configuration settings.

Oracle-specific settings beyond the generic ERP_* config values.
These are loaded from environment variables with the MES_ prefix.

Oracle Cloud ERP uses REST APIs (not OData) with OAuth2 authentication.
Base URL format: https://<pod>.fa.us2.oraclecloud.com
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OracleSettings(BaseSettings):
    """
    Oracle Cloud ERP (Fusion)-specific configuration.

    Env vars (all prefixed MES_):
        MES_ORACLE_BUSINESS_UNIT         Business unit for manufacturing
        MES_ORACLE_ORGANIZATION_CODE     Inventory organization code
        MES_ORACLE_PLANT_CODE            Plant/site code
        MES_ORACLE_WORK_ORDER_PATH       REST path for work orders
        MES_ORACLE_ITEM_PATH             REST path for inventory items
        MES_ORACLE_STRUCTURE_PATH        REST path for item structures (BOMs)
        MES_ORACLE_WORK_CENTER_PATH      REST path for work centers
        MES_ORACLE_ROUTING_PATH          REST path for routings
        MES_ORACLE_COMPLETION_PATH       REST path for completions
        MES_ORACLE_TRANSACTION_PATH      REST path for material transactions
        MES_ORACLE_QUALITY_PATH          REST path for quality results
        MES_ORACLE_TOKEN_URL             OAuth2 token endpoint (Oracle IDCS)
        MES_ORACLE_TOKEN_SCOPE           OAuth2 scope for ERP APIs
        MES_ORACLE_REQUEST_TIMEOUT_SEC   HTTP request timeout
        MES_ORACLE_PAGE_SIZE             Items per page (limit)
    """

    # Organizational context
    ORACLE_BUSINESS_UNIT: str = Field(
        default="Manufacturing BU",
        description="Oracle business unit name for manufacturing",
    )
    ORACLE_ORGANIZATION_CODE: str = Field(
        default="M1",
        description="Inventory organization code",
    )
    ORACLE_PLANT_CODE: str = Field(
        default="M1",
        description="Plant/site code for filtering",
    )

    # REST API paths (relative to ERP_BASE_URL)
    ORACLE_WORK_ORDER_PATH: str = Field(
        default="/fscmRestApi/resources/11.13.18.05/workOrders",
        description="Work Orders REST path",
    )
    ORACLE_ITEM_PATH: str = Field(
        default="/fscmRestApi/resources/11.13.18.05/inventoryItemsV2",
        description="Inventory Items REST path",
    )
    ORACLE_STRUCTURE_PATH: str = Field(
        default="/fscmRestApi/resources/11.13.18.05/itemStructures",
        description="Item Structures (BOMs) REST path",
    )
    ORACLE_WORK_CENTER_PATH: str = Field(
        default="/fscmRestApi/resources/11.13.18.05/workCenters",
        description="Work Centers REST path",
    )
    ORACLE_ROUTING_PATH: str = Field(
        default="/fscmRestApi/resources/11.13.18.05/workOrderOperations",
        description="Routing/Operations REST path",
    )
    ORACLE_COMPLETION_PATH: str = Field(
        default="/fscmRestApi/resources/11.13.18.05/workOrderCompletions",
        description="Work Order Completions REST path",
    )
    ORACLE_TRANSACTION_PATH: str = Field(
        default="/fscmRestApi/resources/11.13.18.05/inventoryTransactions",
        description="Inventory Transactions REST path",
    )
    ORACLE_QUALITY_PATH: str = Field(
        default="/fscmRestApi/resources/11.13.18.05/qualityResults",
        description="Quality Results REST path",
    )

    # OAuth2 (Oracle Identity Cloud Service / OCI IAM)
    ORACLE_TOKEN_URL: str = Field(
        default="",
        description="Oracle IDCS OAuth2 token endpoint (falls back to MES_ERP_TOKEN_URL)",
    )
    ORACLE_TOKEN_SCOPE: str = Field(
        default="",
        description="OAuth2 scope for Oracle ERP API access",
    )

    # Request configuration
    ORACLE_REQUEST_TIMEOUT_SEC: int = Field(
        default=30,
        ge=5,
        description="HTTP request timeout in seconds",
    )
    ORACLE_PAGE_SIZE: int = Field(
        default=100,
        ge=10,
        le=500,
        description="Items per page (Oracle uses ?limit= parameter)",
    )

    model_config = SettingsConfigDict(
        env_prefix="MES_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


oracle_settings = OracleSettings()
