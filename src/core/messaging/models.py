"""Модели для сообщений RabbitMQ."""

from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import uuid4

from pydantic import Field

from tools.pydantic import BaseModel

PayloadType = TypeVar("PayloadType", bound=BaseModel)


class MessageModel(BaseModel, Generic[PayloadType]):
    """Базовая модель сообщения."""

    id: str = Field(default_factory=lambda: str(uuid4()), description="Уникальный идентификатор сообщения")
    type: str = Field(description="Тип сообщения")
    payload: PayloadType = Field(description="Данные сообщения")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Время создания сообщения")
    source: str = Field(description="Источник сообщения")
    correlation_id: str | None = Field(default=None, description="ID для корреляции сообщений")
    reply_to: str | None = Field(default=None, description="Очередь для ответа")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class UserNotificationPayload(BaseModel):
    user_id: int
    message: str
    notification_type: str = "info"  # info, warning, error


class UserNotificationMessage(MessageModel[UserNotificationPayload]):
    """Сообщение уведомления пользователя."""

    type: str = Field(default="user_notification", description="Тип сообщения")


class OrderProcessingPayload(BaseModel):
    order_id: int
    status: str
    details: dict[str, Any] = {}


class OrderProcessingMessage(MessageModel[OrderProcessingPayload]):
    """Сообщение обработки заказа."""

    type: str = Field(default="order_processing", description="Тип сообщения")


class SystemEventPayload(BaseModel):
    event_name: str
    event_data: dict[str, Any] = {}
    severity: str = "info"  # info, warning, error, critical


class SystemEventMessage(MessageModel[SystemEventPayload]):
    """Системное событие."""

    type: str = Field(default="system_event", description="Тип сообщения")


class AdminNotificationPayload(BaseModel):
    event_name: str
    event_data: dict[str, Any] = {}
    severity: str = "info"  # info, warning, error, critical


class AdminNotificationMessage(MessageModel[AdminNotificationPayload]):
    """AdminNotificationMessage событие."""

    type: str = Field(default="admin_event", description="Тип сообщения")
