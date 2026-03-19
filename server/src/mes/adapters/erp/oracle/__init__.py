"""
Oracle Cloud ERP Adapter.

Vendor-specific adapter for Oracle Cloud ERP (Fusion) integration via
REST APIs. Maps Oracle ERP manufacturing, inventory, product,
and cost management APIs to MES canonical DTOs.

API families used:
  - Manufacturing Work Orders (fscmRestApi/resources/workOrders)
  - Inventory Items (fscmRestApi/resources/inventoryItems)
  - Product Structure (fscmRestApi/resources/itemStructures)
  - Work Center Resources (fscmRestApi/resources/workCenters)
  - Manufacturing Work Order Completions
  - Material Transactions (fscmRestApi/resources/inventoryTransactions)

Set MES_ERP_ADAPTER=oracle to enable.
"""
