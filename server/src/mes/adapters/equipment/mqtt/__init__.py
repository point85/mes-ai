"""
MQTT Equipment Adapter.

Implements the EquipmentAdapter interface for MQTT-connected
production equipment using the aiomqtt library.

Supports:
- TLS with optional client certificate authentication
- Username/password broker authentication
- Tag-to-topic mapping under a configurable prefix
- Local value cache from retained messages and subscriptions
- Event-driven data change callbacks
- Equipment state from a dedicated MQTT topic

Configuration:
    MES_EQUIP_ADAPTER=mqtt
    MES_EQUIP_MQTT_BROKER_HOST=mqtt-broker.local
    MES_EQUIP_MQTT_BROKER_PORT=1883
    MES_EQUIP_MQTT_TOPIC_PREFIX=mes/equipment
"""
