"""Интеграция FastStream с FastAPI."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException

from tools.pydantic import BaseModel

from .broker import create_faststream_app, get_broker
from .client import MessageClient, get_message_client

logger = logging.getLogger(__name__)


# Pydantic модели для API endpoints
class UserNotificationRequest(BaseModel):
    """Запрос на отправку уведомления пользователю."""

    user_id: int
    message: str
    notification_type: str = "info"


class AdminNotificationRequest(BaseModel):
    """Запрос на отправку админского уведомления."""

    message: str
    notification_type: str = "info"


class OrderProcessingRequest(BaseModel):
    """Запрос на отправку сообщения о заказе."""

    order_id: int
    status: str
    details: dict[str, Any] = {}


class SystemEventRequest(BaseModel):
    """Запрос на отправку системного события."""

    event_name: str
    event_data: dict[str, Any] = {}
    severity: str = "info"


class CustomMessageRequest(BaseModel):
    """Запрос на отправку произвольного сообщения."""

    message: dict[str, Any]
    exchange_name: str
    routing_key: str | None = None


class MessageResponse(BaseModel):
    """Ответ при отправке сообщения."""

    success: bool
    message: str
    message_id: str | None = None


# Lifespan менеджер для FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом FastAPI приложения."""
    # Запуск
    broker = get_broker()
    client = get_message_client()

    try:
        await broker.connect()
        logger.info("FastStream broker подключен")

        # Запуск FastStream в фоновом режиме
        faststream_app = create_faststream_app()

        # Импортируем обработчики, чтобы они зарегистрировались
        from . import handlers  # noqa: F401

        # Запускаем брокер в фоновой задаче
        broker_task = asyncio.create_task(broker.start())

        yield {"broker": broker, "client": client, "broker_task": broker_task}

    finally:
        # Остановка
        try:
            broker_task.cancel()
            await broker.close()
            logger.info("FastStream broker отключен")
        except Exception as e:
            logger.error(f"Ошибка при остановке брокера: {e}")


def create_messaging_router():
    """Создание роутера для сообщений."""
    from fastapi import APIRouter

    router = APIRouter(prefix="/messaging", tags=["messaging"])

    @router.post("/user-notification", response_model=MessageResponse)
    async def send_user_notification(
        request: UserNotificationRequest, client: MessageClient = Depends(get_message_client)
    ):
        """Отправить уведомление пользователю."""
        try:
            await client.send_user_notification(
                user_id=request.user_id, message=request.message, notification_type=request.notification_type
            )
            return MessageResponse(success=True, message=f"Уведомление отправлено пользователю {request.user_id}")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления пользователю: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/admin-notification", response_model=MessageResponse)
    async def send_admin_notification(
        request: AdminNotificationRequest, client: MessageClient = Depends(get_message_client)
    ):
        """Отправить админское уведомление."""
        try:
            await client.send_admin_notification(message=request.message, notification_type=request.notification_type)
            return MessageResponse(success=True, message="Админское уведомление отправлено")
        except Exception as e:
            logger.error(f"Ошибка отправки админского уведомления: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/order-processing", response_model=MessageResponse)
    async def send_order_processing(
        request: OrderProcessingRequest, client: MessageClient = Depends(get_message_client)
    ):
        """Отправить сообщение об обработке заказа."""
        try:
            await client.send_order_processing(
                order_id=request.order_id, status=request.status, details=request.details
            )
            return MessageResponse(success=True, message=f"Сообщение о заказе {request.order_id} отправлено")
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения о заказе: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/system-event", response_model=MessageResponse)
    async def send_system_event(request: SystemEventRequest, client: MessageClient = Depends(get_message_client)):
        """Отправить системное событие."""
        try:
            await client.send_system_event(
                event_name=request.event_name, event_data=request.event_data, severity=request.severity
            )
            return MessageResponse(success=True, message=f"Системное событие '{request.event_name}' отправлено")
        except Exception as e:
            logger.error(f"Ошибка отправки системного события: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/custom-message", response_model=MessageResponse)
    async def send_custom_message(request: CustomMessageRequest, client: MessageClient = Depends(get_message_client)):
        """Отправить произвольное сообщение."""
        try:
            await client.send_custom_message(
                message=request.message, exchange_name=request.exchange_name, routing_key=request.routing_key
            )
            return MessageResponse(success=True, message=f"Сообщение отправлено в exchange '{request.exchange_name}'")
        except Exception as e:
            logger.error(f"Ошибка отправки произвольного сообщения: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/health")
    async def messaging_health():
        """Проверка состояния системы сообщений."""
        try:
            broker = get_broker()
            is_connected = hasattr(broker, "_connection") and broker._connection is not None

            return {
                "status": "healthy" if is_connected else "unhealthy",
                "connected": is_connected,
                "broker_url": broker.url if hasattr(broker, "url") else None,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    return router


# Функция для интеграции с существующим FastAPI приложением
def setup_messaging(app: FastAPI) -> None:
    """Настройка системы сообщений в FastAPI приложении."""
    # Добавляем роутер для сообщений
    messaging_router = create_messaging_router()
    app.include_router(messaging_router)

    # Добавляем middleware для логирования
    @app.middleware("http")
    async def messaging_middleware(request, call_next):
        # Логируем вызовы API сообщений
        if request.url.path.startswith("/messaging"):
            logger.info(f"Messaging API call: {request.method} {request.url.path}")

        response = await call_next(request)
        return response

    logger.info("Система сообщений FastStream настроена для FastAPI")


# Пример создания полного приложения с поддержкой сообщений
def create_app_with_messaging() -> FastAPI:
    """Создать FastAPI приложение с поддержкой FastStream."""
    app = FastAPI(
        title="API с поддержкой FastStream",
        description="FastAPI приложение с интегрированной системой сообщений RabbitMQ",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Настраиваем систему сообщений
    setup_messaging(app)

    # Добавляем базовые endpoints
    @app.get("/")
    async def root():
        return {"message": "FastAPI с FastStream и RabbitMQ готово к работе!"}

    @app.get("/health")
    async def health():
        return {"status": "healthy", "service": "fastapi-faststream"}

    return app


# Создаем экземпляр приложения (можно использовать для запуска)
app = create_app_with_messaging()
