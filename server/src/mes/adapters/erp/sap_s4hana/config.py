"""
SAP S/4HANA: Configuration extensions.

SAP-specific settings beyond the generic ERP_* config values.
These are loaded from environment variables with the MES_ prefix.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SAPSettings(BaseSettings):
    """
    SAP S/4HANA-specific configuration.

    All settings are prefixed with MES_SAP_ in environment variables.
    Falls back to generic ERP_* settings where applicable.
    """

    # SAP organizational context
    SAP_COMPANY_CODE: str = Field(
        default="1000",
        description="SAP company code (Buchungskreis)",
    )
    SAP_PLANT: str = Field(
        default="1000",
        description="SAP plant code (Werk)",
    )
    SAP_STORAGE_LOCATION: str = Field(
        default="0001",
        description="Default storage location (Lagerort)",
    )

    # OData API paths (relative to ERP_BASE_URL)
    SAP_PRODUCTION_ORDER_PATH: str = Field(
        default="/sap/opu/odata4/sap/api_production_order_2_srv/srvd_a2x/sap/productionorder/0001",
        description="Production Order OData V4 path",
    )
    SAP_MATERIAL_PATH: str = Field(
        default="/sap/opu/odata4/sap/api_material_srv/srvd_a2x/sap/material/0001",
        description="Material Master OData V4 path",
    )
    SAP_PRODUCT_PATH: str = Field(
        default="/sap/opu/odata4/sap/api_product_srv/srvd_a2x/sap/product/0001",
        description="Product OData V4 path",
    )
    SAP_BOM_PATH: str = Field(
        default="/sap/opu/odata4/sap/api_bill_of_material_srv/srvd_a2x/sap/billofmaterial/0001",
        description="BOM OData V4 path",
    )
    SAP_ROUTING_PATH: str = Field(
        default="/sap/opu/odata4/sap/api_production_routing/srvd_a2x/sap/productionrouting/0001",
        description="Routing OData V4 path",
    )
    SAP_WORK_CENTER_PATH: str = Field(
        default="/sap/opu/odata4/sap/api_work_centers/srvd_a2x/sap/workcenter/0001",
        description="Work Center OData V4 path",
    )
    SAP_CONFIRMATION_PATH: str = Field(
        default="/sap/opu/odata4/sap/api_prod_order_confirmation_2_srv/srvd_a2x/sap/prodorderconfirmation/0001",
        description="Production Order Confirmation OData V4 path",
    )

    # OAuth2 token endpoint (SAP-specific; overrides generic ERP_TOKEN_URL)
    SAP_TOKEN_URL: str = Field(
        default="",
        description="SAP OAuth2 token endpoint (falls back to MES_ERP_TOKEN_URL)",
    )

    # Request configuration
    SAP_REQUEST_TIMEOUT_SEC: int = Field(
        default=30,
        ge=5,
        description="HTTP request timeout in seconds",
    )
    SAP_PAGE_SIZE: int = Field(
        default=100,
        ge=10,
        le=5000,
        description="OData $top page size for list queries",
    )

    # API key header (when ERP_AUTH_TYPE=api_key)
    SAP_API_KEY_HEADER: str = Field(
        default="APIKey",
        description="Header name for API key authentication",
    )

    model_config = SettingsConfigDict(
        env_prefix="MES_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


sap_settings = SAPSettings()
