"""Модуль для работы с WebSocket и SSE."""

# WebSocket и SSE компоненты
from .auth import WSAuthenticator, authenticator, get_ws_auth, optional_auth, require_auth
from .connection_manager import ConnectionManager, connection_manager
from .sse_routes import router as sse_router
from .ws_models import (
    BroadcastMessage,
    ChannelMessage,
    SSEConnectionStatus,
    MessageType,
    NotificationMessage,
    SSEMessage,
    WSCommand,
    WSConnectionInfo,
    WSMessage,
    WSResponse,
)
from .ws_routes import router as ws_router

__all__ = [
    # Auth
    "WSAuthenticator",
    "authenticator",
    "get_ws_auth",
    "require_auth",
    "optional_auth",
    # Connection Manager
    "ConnectionManager",
    "connection_manager",
    # Models
    "WSMessage",
    "SSEMessage",
    "WSCommand",
    "WSResponse",
    "MessageType",
    "SSEConnectionStatus",
    "WSConnectionInfo",
    "NotificationMessage",
    "BroadcastMessage",
    "ChannelMessage",
    # Routes
    "ws_router",
    "sse_router",
]
