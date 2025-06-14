"""Инициализация модуля routes для realtime пакета."""

from .sse_routes import router as sse_router
from .webrtc_routes import router as webrtc_router
from .ws_routes import router as ws_router

__all__ = ["sse_router", "webrtc_router", "ws_router"]
