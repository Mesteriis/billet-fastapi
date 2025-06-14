"""Конфигурация брокера RabbitMQ."""

# Все функции перенесены в core.py для избежания дублирования
from .core import (
    admin_notifications_queue,
    create_faststream_app,
    get_broker,
    notifications_exchange,
    order_completed_queue,
    order_processing_queue,
    orders_exchange,
    system_events_queue,
    system_exchange,
    user_notifications_queue,
)

__all__ = [
    "get_broker",
    "create_faststream_app",
    "notifications_exchange",
    "orders_exchange",
    "system_exchange",
    "user_notifications_queue",
    "admin_notifications_queue",
    "order_processing_queue",
    "order_completed_queue",
    "system_events_queue",
]
