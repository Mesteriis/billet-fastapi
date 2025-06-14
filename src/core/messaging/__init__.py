"""Модуль для работы с FastStream и системой сообщений."""

from .core import MessageClient, create_faststream_app, get_broker, get_message_client
from .models import (
    AdminNotificationMessage,
    MessageModel,
    OrderProcessingMessage,
    SystemEventMessage,
    UserNotificationMessage,
)

__all__ = [
    "AdminNotificationMessage",
    "MessageClient",
    "MessageModel",
    "OrderProcessingMessage",
    "SystemEventMessage",
    "UserNotificationMessage",
    "create_faststream_app",
    "get_broker",
    "get_message_client",
]
