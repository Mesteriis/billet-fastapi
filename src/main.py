"""Main FastAPI application with TaskIQ integration."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from core.config import get_settings
from core.taskiq_client import broker
from core.telemetry import instrument_fastapi_app, setup_telemetry

# Import telegram components
try:
    from core.telegram import TelegramBotsConfig
    from core.telegram.handlers.admin import register_admin_handlers
    from core.telegram.handlers.basic import register_basic_handlers
    from core.telegram.manager import get_bot_manager

    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

# Import realtime components
try:
    from core.realtime import connection_manager, sse_router, webrtc_router, ws_router

    REALTIME_AVAILABLE = True
except ImportError:
    REALTIME_AVAILABLE = False

# Import messaging components
try:
    from core.messaging import get_message_client

    MESSAGING_AVAILABLE = True
except ImportError:
    MESSAGING_AVAILABLE = False


settings = get_settings()

# Setup OpenTelemetry tracing
setup_telemetry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager.

    Handles startup and shutdown events for all application services including:
    - TaskIQ broker initialization
    - Telegram bots setup and polling
    - Background services management

    Args:
        app (FastAPI): The FastAPI application instance

    Yields:
        None: Control is yielded back to the application after startup

    Raises:
        Exception: If critical services fail to initialize

    Example:
        Used automatically by FastAPI::

            app = FastAPI(lifespan=lifespan)

    Note:
        This function is called automatically by FastAPI during
        application startup and shutdown.
    """
    # Startup
    await broker.startup()

    # Initialize Telegram bots
    if TELEGRAM_AVAILABLE and settings.TELEGRAM_BOTS_ENABLED:
        try:
            # Register command handlers
            register_basic_handlers()
            register_admin_handlers()

            # Initialize and start bots
            bot_manager = get_bot_manager()
            await bot_manager.initialize_bots()
            await bot_manager.start_polling_bots()
            await bot_manager.setup_webhooks()
            await bot_manager.start_webhook_server()

        except Exception as e:
            print(f"Error initializing Telegram bots: {e}")

    yield

    # Shutdown
    await broker.shutdown()

    # Stop Telegram bots
    if TELEGRAM_AVAILABLE and settings.TELEGRAM_BOTS_ENABLED:
        try:
            bot_manager = get_bot_manager()
            await bot_manager.stop_all_bots()
        except Exception as e:
            print(f"Error stopping Telegram bots: {e}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
)

# Instrument FastAPI for OpenTelemetry
instrument_fastapi_app(app)

# Connect API routes
from apps.api_router import api_router

app.include_router(api_router)

# Connect Realtime routers (WebSocket, SSE, WebRTC)
if REALTIME_AVAILABLE:
    if settings.WEBSOCKET_ENABLED:
        app.include_router(ws_router)
    if settings.SSE_ENABLED:
        app.include_router(sse_router)
    if settings.WEBRTC_ENABLED:  # WebRTC enabled by default
        app.include_router(webrtc_router)


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint providing application information.

    Returns basic information about the application and available services,
    including enabled features and API endpoints.

    Returns:
        dict[str, Any]: Application information and service status

    Example:
        GET request::

            curl http://localhost:8000/

        Response::

            {
                "message": "Welcome to Mango Message",
                "version": "1.0.0",
                "taskiq_enabled": true,
                "telegram_enabled": true,
                "endpoints": {
                    "tasks": "/tasks",
                    "docs": "/docs",
                    "websocket": "/realtime/ws"
                }
            }
    """
    response: dict[str, Any] = {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "taskiq_enabled": True,
        "telegram_enabled": TELEGRAM_AVAILABLE and settings.TELEGRAM_BOTS_ENABLED,
        "messaging_enabled": MESSAGING_AVAILABLE,
        "websocket_enabled": REALTIME_AVAILABLE and settings.WEBSOCKET_ENABLED,
        "sse_enabled": REALTIME_AVAILABLE and settings.SSE_ENABLED,
        "webrtc_enabled": REALTIME_AVAILABLE and getattr(settings, "WEBRTC_ENABLED", True),
        "endpoints": {"tasks": "/tasks", "docs": "/docs", "redoc": "/redoc"},
    }

    # Add Realtime endpoints
    if REALTIME_AVAILABLE:
        if settings.WEBSOCKET_ENABLED:
            response["endpoints"]["websocket"] = "/realtime/ws"
            response["endpoints"]["websocket_test"] = "/realtime/test"
        if settings.SSE_ENABLED:
            response["endpoints"]["sse"] = "/realtime/events"
            response["endpoints"]["sse_test"] = "/realtime/sse-test"
        if getattr(settings, "WEBRTC_ENABLED", True):
            response["endpoints"]["webrtc"] = "/realtime/webrtc"
            response["endpoints"]["webrtc_signaling"] = "/realtime/webrtc/signaling"

    # Add Messaging endpoints
    if MESSAGING_AVAILABLE:
        response["endpoints"]["messaging"] = "/messaging"

    # Add Telegram bots information
    if TELEGRAM_AVAILABLE and settings.TELEGRAM_BOTS_ENABLED:
        try:
            bot_manager = get_bot_manager()
            active_bots = len(bot_manager.bots)
            response["telegram_info"] = {"active_bots": active_bots, "bots": list(bot_manager.bots.keys())}
        except Exception:
            response["telegram_info"] = {"status": "error"}

    return response


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint.

    Provides basic health status information for monitoring and load balancers.

    Returns:
        dict[str, str]: Health status information

    Example:
        GET request::

            curl http://localhost:8000/health

        Response::

            {
                "status": "healthy",
                "app": "Mango Message",
                "version": "1.0.0"
            }

    Note:
        This endpoint is commonly used by:
        - Load balancers for health checks
        - Container orchestrators (Docker, Kubernetes)
        - Monitoring systems
    """
    return {"status": "healthy", "app": settings.PROJECT_NAME, "version": settings.VERSION}
