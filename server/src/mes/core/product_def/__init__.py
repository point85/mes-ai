"""
PROD-DEF: Product Definition module.

Implements the ISA-95 product definition hierarchy:
ProductDefinition → BillOfMaterial → BOMItem
ProductDefinition → OperationsDefinition → ProcessSegment → SegmentParameter

Products and routes are master data — in production they are synced from ERP
via ERPInboundAdapter. The MES holds a local execution copy for offline
resilience and real-time sequencing (see Decision D024).
"""
