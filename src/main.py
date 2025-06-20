"""Main FastAPI application with TaskIQ integration."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from core.config import get_settings
from core.taskiq_client import broker
from core.telemetry import instrument_fastapi_app, setup_telemetry

# Импортируем телеграм компоненты
try:
    from core.telegram import TelegramBotsConfig
    from core.telegram.handlers.admin import register_admin_handlers
    from core.telegram.handlers.basic import register_basic_handlers
    from core.telegram.manager import get_bot_manager

    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

# Импортируем realtime компоненты
try:
    from core.realtime import connection_manager, sse_router, webrtc_router, ws_router

    REALTIME_AVAILABLE = True
except ImportError:
    REALTIME_AVAILABLE = False

# Импортируем messaging компоненты
try:
    from core.messaging import get_message_client

    MESSAGING_AVAILABLE = True
except ImportError:
    MESSAGING_AVAILABLE = False


settings = get_settings()

# Настройка OpenTelemetry трассировки
setup_telemetry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения.

    Args:
        app: Экземпляр FastAPI приложения.

    Yields:
        None: После инициализации всех компонентов.
    """
    # Startup
    await broker.startup()

    # Инициализация Telegram ботов
    if TELEGRAM_AVAILABLE and settings.TELEGRAM_BOTS_ENABLED:
        try:
            # Регистрируем обработчики команд
            register_basic_handlers()
            register_admin_handlers()

            # Инициализируем и запускаем ботов
            bot_manager = get_bot_manager()
            await bot_manager.initialize_bots()
            await bot_manager.start_polling_bots()
            await bot_manager.setup_webhooks()
            await bot_manager.start_webhook_server()

        except Exception as e:
            print(f"Ошибка инициализации Telegram ботов: {e}")

    yield

    # Shutdown
    await broker.shutdown()

    # Остановка Telegram ботов
    if TELEGRAM_AVAILABLE and settings.TELEGRAM_BOTS_ENABLED:
        try:
            bot_manager = get_bot_manager()
            await bot_manager.stop_all_bots()
        except Exception as e:
            print(f"Ошибка остановки Telegram ботов: {e}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
)

# Инструментация FastAPI для OpenTelemetry
instrument_fastapi_app(app)

# Подключаем роуты для аутентификации и пользователей
# from apps.auth.routes import router as auth_router
# from apps.users.routes import router as users_router

# app.include_router(auth_router, prefix=settings.API_V1_STR)
# app.include_router(users_router, prefix=settings.API_V1_STR)

# Подключаем Realtime роутеры (WebSocket, SSE, WebRTC)
if REALTIME_AVAILABLE:
    if settings.WEBSOCKET_ENABLED:
        app.include_router(ws_router)
    if settings.SSE_ENABLED:
        app.include_router(sse_router)
    if settings.WEBRTC_ENABLED:  # WebRTC по умолчанию включен
        app.include_router(webrtc_router)


@app.get("/")
async def root() -> dict[str, Any]:
    """Корневой эндпоинт.

    Returns:
        dict: Информация о приложении и доступных сервисах.
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

    # Добавляем Realtime эндпоинты
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

    # Добавляем Messaging эндпоинты
    if MESSAGING_AVAILABLE:
        response["endpoints"]["messaging"] = "/messaging"

    # Добавляем информацию о Telegram ботах
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
    """Проверка здоровья приложения.

    Returns:
        dict: Статус здоровья приложения.
    """
    return {"status": "healthy", "app": settings.PROJECT_NAME, "version": settings.VERSION}
