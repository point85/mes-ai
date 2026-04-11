"""
STOMP JMS Adapter package.

Implements a bidirectional bridge between the MES internal event bus and
a STOMP-compatible JMS message broker (ActiveMQ, Artemis, RabbitMQ, etc.).

Inbound:  Subscribes to broker queues/topics → publishes to MES event bus.
Outbound: Subscribes to MES event topics → publishes to broker destinations.
"""
