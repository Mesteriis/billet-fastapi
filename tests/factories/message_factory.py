"""
Фабрика для создания тестовых сообщений и событий.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict

from core.messaging.models import Message, MessagePriority, MessageStatus
from core.realtime.models import (
    BroadcastMessage,
    MessageType,
    NotificationMessage,
    SSEMessage,
    WSCommand,
    WSMessage,
    WSResponse,
)


def make_ws_message(**kwargs) -> WSMessage:
    """Создает WebSocket сообщение."""
    defaults = {
        "type": MessageType.TEXT,
        "data": "Test message",
        "channel": "test_channel",
        "user_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow(),
    }
    defaults.update(kwargs)
    return WSMessage(**defaults)


def make_ws_command(**kwargs) -> WSCommand:
    """Создает WebSocket команду."""
    defaults = {
        "action": "test_action",
        "data": {"key": "value"},
        "channel": "test_channel",
    }
    defaults.update(kwargs)
    return WSCommand(**defaults)


def make_ws_response(**kwargs) -> WSResponse:
    """Создает WebSocket ответ."""
    defaults = {
        "success": True,
        "message": "Operation successful",
        "data": {"result": "ok"},
        "timestamp": datetime.utcnow(),
    }
    defaults.update(kwargs)
    return WSResponse(**defaults)


def make_ws_error_response(**kwargs) -> WSResponse:
    """Создает WebSocket ответ с ошибкой."""
    defaults = {
        "success": False,
        "message": "Operation failed",
        "error_code": "VALIDATION_ERROR",
        "timestamp": datetime.utcnow(),
    }
    defaults.update(kwargs)
    return WSResponse(**defaults)


def make_sse_message(**kwargs) -> SSEMessage:
    """Создает SSE сообщение."""
    defaults = {
        "type": MessageType.NOTIFICATION,
        "event": "test_event",
        "data": "Test SSE message",
        "timestamp": datetime.utcnow(),
    }
    defaults.update(kwargs)
    return SSEMessage(**defaults)


def make_notification(**kwargs) -> NotificationMessage:
    """Создает уведомление."""
    defaults = {
        "type": MessageType.NOTIFICATION,
        "title": "Test Notification",
        "body": "This is a test notification",
        "user_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow(),
    }
    defaults.update(kwargs)
    return NotificationMessage(**defaults)


def make_broadcast_message(**kwargs) -> BroadcastMessage:
    """Создает широковещательное сообщение."""
    defaults = {
        "type": MessageType.BROADCAST,
        "data": "Broadcast message to all users",
        "timestamp": datetime.utcnow(),
    }
    defaults.update(kwargs)
    return BroadcastMessage(**defaults)


def make_message(**kwargs) -> Message:
    """Создает сообщение для messaging системы."""
    defaults = {
        "id": str(uuid.uuid4()),
        "routing_key": "test.message",
        "payload": {"message": "Test message"},
        "status": MessageStatus.PENDING,
        "priority": MessagePriority.NORMAL,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=1),
        "retry_count": 0,
        "max_retries": 3,
    }
    defaults.update(kwargs)
    return Message(**defaults)


def make_high_priority_message(**kwargs) -> Message:
    """Создает сообщение с высоким приоритетом."""
    return make_message(priority=MessagePriority.HIGH, **kwargs)


def make_failed_message(**kwargs) -> Message:
    """Создает неудачное сообщение."""
    return make_message(status=MessageStatus.FAILED, retry_count=3, error="Test error", **kwargs)


def make_expired_message(**kwargs) -> Message:
    """Создает просроченное сообщение."""
    return make_message(expires_at=datetime.utcnow() - timedelta(hours=1), **kwargs)


# Функции для создания списков сообщений
def make_message_batch(count: int = 5, **kwargs) -> list[Message]:
    """Создает партию сообщений."""
    return [make_message(**kwargs) for _ in range(count)]


def make_ws_message_conversation(count: int = 10, channel: str = "test_chat") -> list[WSMessage]:
    """Создает разговор из WebSocket сообщений."""
    messages = []
    users = [str(uuid.uuid4()) for _ in range(3)]  # 3 пользователя в разговоре

    for i in range(count):
        user_id = users[i % len(users)]
        message = make_ws_message(
            data=f"Message {i + 1} from user {user_id[:8]}",
            channel=channel,
            user_id=user_id,
            timestamp=datetime.utcnow() + timedelta(seconds=i),
        )
        messages.append(message)

    return messages


def make_notification_batch(user_id: str, count: int = 5) -> list[NotificationMessage]:
    """Создает партию уведомлений для пользователя."""
    notifications = []
    for i in range(count):
        notification = make_notification(
            title=f"Notification {i + 1}",
            body=f"This is notification number {i + 1}",
            user_id=user_id,
            timestamp=datetime.utcnow() + timedelta(seconds=i),
        )
        notifications.append(notification)

    return notifications


# Шаблоны для разных типов сообщений
MESSAGE_TEMPLATES = {
    "welcome": {
        "type": MessageType.NOTIFICATION,
        "title": "Welcome!",
        "body": "Welcome to our platform!",
    },
    "system_alert": {
        "type": MessageType.BROADCAST,
        "data": "System maintenance scheduled for tonight",
    },
    "user_joined": {
        "type": MessageType.CHANNEL,
        "data": "User has joined the channel",
    },
    "error": {
        "type": MessageType.ERROR,
        "data": "An error occurred",
    },
}


def make_message_from_template(template_name: str, **kwargs) -> dict[str, Any]:
    """Создает сообщение из шаблона."""
    if template_name not in MESSAGE_TEMPLATES:
        raise ValueError(f"Unknown template: {template_name}")

    template = MESSAGE_TEMPLATES[template_name].copy()
    template.update(kwargs)
    return template


# Утилиты для тестирования
def assert_message_structure(message: dict[str, Any], required_fields: list[str] = None):
    """Проверяет структуру сообщения."""
    if required_fields is None:
        required_fields = ["type", "timestamp"]

    for field in required_fields:
        assert field in message, f"Missing required field: {field}"


def assert_ws_message_valid(message: WSMessage):
    """Проверяет валидность WebSocket сообщения."""
    assert message.type is not None
    assert message.timestamp is not None
    assert message.id is not None
    assert isinstance(message.type, MessageType)


def assert_response_success(response: WSResponse):
    """Проверяет успешность ответа."""
    assert response.success is True
    assert response.error_code is None
    assert response.timestamp is not None


def assert_response_error(response: WSResponse, expected_error_code: str = None):
    """Проверяет ответ с ошибкой."""
    assert response.success is False
    if expected_error_code:
        assert response.error_code == expected_error_code
    assert response.timestamp is not None
