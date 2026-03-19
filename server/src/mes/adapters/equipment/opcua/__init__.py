"""
OPC-UA Equipment Adapter.

Implements the EquipmentAdapter interface for OPC-UA enabled
production equipment using the asyncua library.

Supports:
- Security modes: None, Sign, SignAndEncrypt
- Authentication: Anonymous, Username/Password, Certificate
- Tag read/write via NodeId or browse-path resolution
- Data change subscriptions with configurable sampling intervals
- Address space browsing
- Equipment state derived from configurable OPC-UA node

Configuration:
    MES_EQUIP_ADAPTER=opcua
    MES_EQUIP_OPCUA_URL=opc.tcp://plc-01:4840
    MES_EQUIP_OPCUA_SECURITY_MODE=none
    MES_EQUIP_OPCUA_NAMESPACE=2
"""
