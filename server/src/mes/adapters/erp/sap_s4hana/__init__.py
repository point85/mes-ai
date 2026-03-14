"""
SAP S/4HANA ERP Adapter.

Vendor-specific adapter for SAP S/4HANA integration via OData V4 APIs.
Maps SAP production planning, material management, and shop floor control
APIs to MES canonical DTOs.

API families used:
  - Production Order (API_PRODUCTION_ORDER_2_SRV)
  - Material Master (API_MATERIAL_SRV)
  - Product (API_PRODUCT_SRV)
  - Bill of Material (API_BILL_OF_MATERIAL_SRV)
  - Routing/Recipe (API_PRODUCTION_ROUTING)
  - Work Center (API_WORK_CENTERS)
  - Production Order Confirmation (API_PROD_ORDER_CONFIRMATION_2_SRV)

Set MES_ERP_ADAPTER=sap_s4hana to enable.
"""
