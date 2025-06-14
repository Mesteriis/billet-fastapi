"""Модели данных для WebSocket и SSE."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field

from tools.pydantic import BaseModel


class MessageType(str, Enum):
    """Типы сообщений."""

    TEXT = "text"
    JSON = "json"
    NOTIFICATION = "notification"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    SYSTEM = "system"
    BROADCAST = "broadcast"
    PRIVATE = "private"


class SSEConnectionStatus(str, Enum):
    """Статусы соединения."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class WSMessage(BaseModel):
    """Модель WebSocket сообщения."""

    id: str = Field(..., description="Уникальный ID сообщения")
    type: MessageType = Field(default=MessageType.TEXT, description="Тип сообщения")
    content: str | dict[str, Any] = Field(..., description="Содержимое сообщения")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Время создания")
    sender_id: str | None = Field(None, description="ID отправителя")
    recipient_id: str | None = Field(None, description="ID получателя")
    channel: str | None = Field(None, description="Канал сообщения")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Дополнительные метаданные")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class SSEMessage(BaseModel):
    """Модель SSE сообщения."""

    id: str = Field(..., description="Уникальный ID события")
    event: str = Field(default="message", description="Тип события")
    data: str | dict[str, Any] = Field(..., description="Данные события")
    retry: int | None = Field(None, description="Время повтора в миллисекундах")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Время создания")

    def to_sse_format(self) -> str:
        """Преобразование в формат SSE."""
        lines = []

        if self.id:
            lines.append(f"id: {self.id}")

        if self.event:
            lines.append(f"event: {self.event}")

        if self.retry:
            lines.append(f"retry: {self.retry}")

        # Обрабатываем данные
        if isinstance(self.data, dict):
            import json

            data_str = json.dumps(self.data, ensure_ascii=False)
        else:
            data_str = str(self.data)

        # Разбиваем данные на строки для SSE формата
        for line in data_str.split("\n"):
            lines.append(f"data: {line}")

        lines.append("")  # Пустая строка в конце
        return "\n".join(lines)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class WSConnectionInfo(BaseModel):
    """Информация о WebSocket соединении."""

    connection_id: str = Field(..., description="ID соединения")
    user_id: str | None = Field(None, description="ID пользователя")
    status: SSEConnectionStatus = Field(default=SSEConnectionStatus.CONNECTING, description="Статус соединения")
    connected_at: datetime = Field(default_factory=datetime.utcnow, description="Время подключения")
    last_activity: datetime = Field(default_factory=datetime.utcnow, description="Последняя активность")
    channels: list[str] = Field(default_factory=list, description="Подписанные каналы")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Метаданные соединения")
    ip_address: str | None = Field(None, description="IP адрес клиента")
    user_agent: str | None = Field(None, description="User agent клиента")


class WSSubscription(BaseModel):
    """Модель подписки на канал."""

    connection_id: str = Field(..., description="ID соединения")
    channel: str = Field(..., description="Название канала")
    filters: dict[str, Any] = Field(default_factory=dict, description="Фильтры сообщений")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Время создания подписки")


class WSCommand(BaseModel):
    """Команда WebSocket."""

    action: str = Field(..., description="Действие команды")
    data: dict[str, Any] = Field(default_factory=dict, description="Данные команды")
    request_id: str | None = Field(None, description="ID запроса для ответа")


class WSResponse(BaseModel):
    """Ответ на команду WebSocket."""

    request_id: str = Field(..., description="ID исходного запроса")
    success: bool = Field(..., description="Успешность выполнения")
    data: dict[str, Any] | None = Field(None, description="Данные ответа")
    error: str | None = Field(None, description="Сообщение об ошибке")


class BroadcastMessage(BaseModel):
    """Сообщение для рассылки."""

    message: WSMessage = Field(..., description="Сообщение для рассылки")
    channels: list[str] | None = Field(None, description="Каналы для рассылки")
    user_ids: list[str] | None = Field(None, description="ID пользователей для рассылки")
    exclude_connections: list[str] = Field(default_factory=list, description="Исключить соединения")
    include_sender: bool = Field(default=False, description="Включить отправителя")


class ChannelMessage(BaseModel):
    """Сообщение для канала."""

    channel: str = Field(..., description="Название канала")
    message: WSMessage = Field(..., description="Сообщение")
    persist: bool = Field(default=False, description="Сохранить сообщение для новых подключений")


class NotificationMessage(BaseModel):
    """Уведомление."""

    title: str = Field(..., description="Заголовок уведомления")
    content: str = Field(..., description="Содержимое уведомления")
    type: str = Field(default="info", description="Тип уведомления (info, success, warning, error)")
    action_url: str | None = Field(None, description="URL для действия")
    auto_hide: bool = Field(default=True, description="Автоматически скрывать уведомление")
    duration: int = Field(default=5000, description="Длительность показа в миллисекундах")


class HeartbeatMessage(BaseModel):
    """Сообщение heartbeat."""

    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Время отправки")
    server_time: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Время сервера")


class SystemMessage(BaseModel):
    """Системное сообщение."""

    level: str = Field(..., description="Уровень сообщения (info, warning, error)")
    message: str = Field(..., description="Текст сообщения")
    component: str | None = Field(None, description="Компонент системы")
    details: dict[str, Any] = Field(default_factory=dict, description="Дополнительные детали")
