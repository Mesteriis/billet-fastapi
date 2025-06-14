"""Модели данных для WebSocket, SSE и WebRTC."""

import base64
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import Field, validator

from tools.pydantic import BaseModel


class MessageType(str, Enum):
    """Типы сообщений."""

    TEXT = "text"
    BINARY = "binary"
    JSON = "json"
    COMMAND = "command"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    BROADCAST = "broadcast"
    CHANNEL = "channel"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    WEBRTC = "webrtc"


class ConnectionStatus(str, Enum):
    """Статусы подключения."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class WebRTCSignalType(str, Enum):
    """Типы WebRTC сигналов."""

    OFFER = "offer"
    ANSWER = "answer"
    ICE_CANDIDATE = "ice-candidate"
    ICE_GATHERING_STATE = "ice-gathering-state"
    CONNECTION_STATE = "connection-state"
    DATA_CHANNEL = "data-channel"


class BaseMessage(BaseModel):
    """Базовая модель сообщения."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    type: MessageType
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class WSMessage(BaseMessage):
    """Модель WebSocket сообщения."""

    data: str | dict[str, Any] | bytes | None = None
    binary_data: str | None = None  # Base64 encoded binary
    channel: str | None = None
    user_id: str | None = None
    metadata: dict[str, Any] | None = None

    @validator("binary_data")
    def validate_binary_data(cls, v):
        if v is not None:
            try:
                base64.b64decode(v)
            except Exception:
                raise ValueError("Invalid base64 encoded binary data")
        return v

    def get_binary_data(self) -> bytes | None:
        """Получить бинарные данные как bytes."""
        if self.binary_data:
            return base64.b64decode(self.binary_data)
        return None

    def set_binary_data(self, data: bytes) -> None:
        """Установить бинарные данные из bytes."""
        self.binary_data = base64.b64encode(data).decode("utf-8")
        self.type = MessageType.BINARY


class SSEMessage(BaseMessage):
    """Модель SSE сообщения."""

    event: str | None = None
    data: str | dict[str, Any]
    retry: int | None = None
    channel: str | None = None
    user_id: str | None = None


class BinaryMessage(BaseMessage):
    """Модель для бинарных сообщений."""

    type: MessageType = MessageType.BINARY
    content_type: str = "application/octet-stream"
    binary_data: str  # Base64 encoded
    filename: str | None = None
    size: int | None = None
    checksum: str | None = None  # MD5 checksum

    @validator("binary_data")
    def validate_binary_data(cls, v):
        try:
            decoded = base64.b64decode(v)
            return v
        except Exception:
            raise ValueError("Invalid base64 encoded binary data")

    def get_binary_data(self) -> bytes:
        """Получить бинарные данные как bytes."""
        return base64.b64decode(self.binary_data)

    @classmethod
    def from_bytes(
        cls, data: bytes, content_type: str = "application/octet-stream", filename: str | None = None
    ) -> "BinaryMessage":
        """Создать BinaryMessage из bytes."""
        import hashlib

        binary_data = base64.b64encode(data).decode("utf-8")
        checksum = hashlib.md5(data, usedforsecurity=False).hexdigest()

        return cls(
            binary_data=binary_data, content_type=content_type, filename=filename, size=len(data), checksum=checksum
        )


class WebRTCMessage(BaseMessage):
    """Модель для WebRTC сообщений."""

    type: MessageType = MessageType.WEBRTC
    signal_type: WebRTCSignalType
    peer_id: str
    target_peer_id: str | None = None
    room_id: str | None = None

    # WebRTC данные
    sdp: str | None = None  # Session Description Protocol
    ice_candidate: dict[str, Any] | None = None
    connection_state: str | None = None
    gathering_state: str | None = None
    data_channel_config: dict[str, Any] | None = None

    metadata: dict[str, Any] | None = None


class WSCommand(BaseModel):
    """Модель команды WebSocket."""

    action: str
    data: dict[str, Any] | None = None
    channel: str | None = None
    target_user: str | None = None
    binary_data: str | None = None  # Base64 encoded

    def get_binary_data(self) -> bytes | None:
        """Получить бинарные данные как bytes."""
        if self.binary_data:
            return base64.b64decode(self.binary_data)
        return None

    def set_binary_data(self, data: bytes) -> None:
        """Установить бинарные данные из bytes."""
        self.binary_data = base64.b64encode(data).decode("utf-8")


class WSResponse(BaseModel):
    """Модель ответа WebSocket."""

    success: bool
    message: str | None = None
    data: dict[str, Any] | None = None
    error_code: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class WSConnectionInfo(BaseModel):
    """Информация о WebSocket подключении."""

    connection_id: str
    user_id: str | None = None
    channels: list[str] = Field(default_factory=list)
    connected_at: datetime
    last_activity: datetime
    ip_address: str | None = None
    user_agent: str | None = None
    status: ConnectionStatus = ConnectionStatus.CONNECTED
    supports_binary: bool = True
    supports_webrtc: bool = False

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class NotificationMessage(BaseMessage):
    """Модель уведомления."""

    type: MessageType = MessageType.NOTIFICATION
    title: str
    body: str
    icon: str | None = None
    badge: str | None = None
    tag: str | None = None
    actions: list[dict[str, str]] | None = None
    data: dict[str, Any] | None = None
    user_id: str | None = None
    channel: str | None = None


class BroadcastMessage(BaseMessage):
    """Модель широковещательного сообщения."""

    type: MessageType = MessageType.BROADCAST
    data: str | dict[str, Any]
    exclude_users: list[str] | None = None
    include_channels: list[str] | None = None
    exclude_channels: list[str] | None = None
    binary_data: str | None = None  # Base64 encoded

    def get_binary_data(self) -> bytes | None:
        """Получить бинарные данные как bytes."""
        if self.binary_data:
            return base64.b64decode(self.binary_data)
        return None


class ChannelMessage(BaseMessage):
    """Модель сообщения канала."""

    type: MessageType = MessageType.CHANNEL
    channel: str
    data: str | dict[str, Any]
    sender_id: str | None = None
    persistent: bool = False  # Сохранить для новых подписчиков
    binary_data: str | None = None  # Base64 encoded

    def get_binary_data(self) -> bytes | None:
        """Получить бинарные данные как bytes."""
        if self.binary_data:
            return base64.b64decode(self.binary_data)
        return None


class WebRTCPeerConnection(BaseModel):
    """Информация о WebRTC соединении между пирами."""

    peer_id: str
    target_peer_id: str
    room_id: str | None = None
    connection_state: str = "new"
    ice_gathering_state: str = "new"
    ice_connection_state: str = "new"
    signaling_state: str = "stable"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class WebRTCRoom(BaseModel):
    """Модель WebRTC комнаты."""

    room_id: str
    name: str | None = None
    max_participants: int = 10
    participants: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str | None = None
    settings: dict[str, Any] | None = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
