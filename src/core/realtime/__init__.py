"""Модуль для работы с WebSocket, SSE и WebRTC в реальном времени."""

from .auth import WSAuthenticator, authenticator, get_ws_auth, optional_auth, require_auth
from .clients.sse_client import SimpleSyncSSEClient, SSEClient, create_authenticated_sse_client, create_sse_client
from .clients.ws_client import WSClient, create_authenticated_client, create_ws_client
from .connection_manager import ConnectionManager, connection_manager
from .models import (
    BinaryMessage,
    BroadcastMessage,
    ChannelMessage,
    ConnectionStatus,
    MessageType,
    NotificationMessage,
    SSEMessage,
    WebRTCMessage,
    WebRTCSignalType,
    WSCommand,
    WSConnectionInfo,
    WSMessage,
    WSResponse,
)
from .routes.sse_routes import router as sse_router
from .routes.webrtc_routes import router as webrtc_router
from .routes.ws_routes import router as ws_router

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
    "ConnectionStatus",
    "WSConnectionInfo",
    "NotificationMessage",
    "BroadcastMessage",
    "ChannelMessage",
    "BinaryMessage",
    "WebRTCMessage",
    "WebRTCSignalType",
    # Routes
    "ws_router",
    "sse_router",
    "webrtc_router",
    # Clients
    "WSClient",
    "SSEClient",
    "SimpleSyncSSEClient",
    "create_ws_client",
    "create_authenticated_client",
    "create_sse_client",
    "create_authenticated_sse_client",
]
