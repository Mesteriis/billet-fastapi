"""Общая логика для работы с FastStream и RabbitMQ."""

import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any

from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue

from core.config import get_settings

from .models import (
    MessageModel,
    OrderProcessingMessage,
    OrderProcessingPayload,
    SystemEventMessage,
    SystemEventPayload,
    UserNotificationMessage,
    UserNotificationPayload,
)

logger = logging.getLogger(__name__)


# Определяем exchanges и queues
from faststream.rabbit import ExchangeType

notifications_exchange = RabbitExchange("notifications", type=ExchangeType.TOPIC, durable=True)
orders_exchange = RabbitExchange("orders", type=ExchangeType.DIRECT, durable=True)
system_exchange = RabbitExchange("system", type=ExchangeType.FANOUT, durable=True)

# Очереди для уведомлений
user_notifications_queue = RabbitQueue("user_notifications", durable=True)
admin_notifications_queue = RabbitQueue("admin_notifications", durable=True)

# Очереди для заказов
order_processing_queue = RabbitQueue("order_processing", durable=True)
order_completed_queue = RabbitQueue("order_completed", durable=True)

# Системные очереди
system_events_queue = RabbitQueue("system_events", durable=True)


@lru_cache
def get_broker() -> RabbitBroker:
    """Получить настроенный брокер RabbitMQ."""
    settings = get_settings()

    broker = RabbitBroker(
        url=settings.RABBITMQ_URL,
        max_consumers=10,
        graceful_timeout=30,
        logger=logger,
    )

    return broker


class MessageClient:
    """Асинхронный клиент для работы с RabbitMQ через FastStream."""

    def __init__(self, broker: RabbitBroker | None = None):
        self.broker = broker or get_broker()
        self._is_connected = False

    async def connect(self) -> None:
        """Подключение к брокеру."""
        if not self._is_connected:
            await self.broker.connect()
            self._is_connected = True
            logger.info("MessageClient подключен к RabbitMQ")

    async def disconnect(self) -> None:
        """Отключение от брокера."""
        if self._is_connected:
            await self.broker.close()
            self._is_connected = False
            logger.info("MessageClient отключен от RabbitMQ")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator["MessageClient", None]:
        """Контекстный менеджер для автоматического подключения/отключения."""
        try:
            await self.connect()
            yield self
        finally:
            await self.disconnect()

    # Методы для отправки сообщений

    async def send_user_notification(
        self,
        user_id: int,
        message: str,
        notification_type: str = "info",
        routing_key: str = "user.notification",
        **kwargs,
    ) -> None:
        """Отправить уведомление пользователю."""
        msg = UserNotificationMessage(
            source="api",
            payload=UserNotificationPayload(user_id=user_id, message=message, notification_type=notification_type),
            **kwargs,
        )

        await self.broker.publish(msg.model_dump(), exchange=notifications_exchange, routing_key=routing_key)
        logger.info(f"Отправлено уведомление пользователю {user_id}: {message}")

    async def send_admin_notification(
        self, message: str, notification_type: str = "info", routing_key: str = "admin.notification", **kwargs
    ) -> None:
        """Отправить уведомление администратору."""
        msg = UserNotificationMessage(
            source="system",
            payload=UserNotificationPayload(
                user_id=0,  # 0 для админских уведомлений
                message=message,
                notification_type=notification_type,
            ),
            **kwargs,
        )

        await self.broker.publish(msg.model_dump(), exchange=notifications_exchange, routing_key=routing_key)
        logger.info(f"Отправлено админское уведомление: {message}")

    async def send_order_processing(
        self, order_id: int, status: str, details: dict[str, Any] | None = None, **kwargs
    ) -> None:
        """Отправить сообщение об обработке заказа."""
        msg = OrderProcessingMessage(
            source="order_service",
            payload=OrderProcessingPayload(order_id=order_id, status=status, details=details or {}),
            **kwargs,
        )

        routing_key = "process" if status in ["processing", "pending"] else "completed"

        await self.broker.publish(msg.model_dump(), exchange=orders_exchange, routing_key=routing_key)
        logger.info(f"Отправлено сообщение о заказе {order_id}: {status}")

    async def send_system_event(
        self, event_name: str, event_data: dict[str, Any] | None = None, severity: str = "info", **kwargs
    ) -> None:
        """Отправить системное событие."""
        msg = SystemEventMessage(
            source="system",
            payload=SystemEventPayload(event_name=event_name, event_data=event_data or {}, severity=severity),
            **kwargs,
        )

        await self.broker.publish(msg.model_dump(), exchange=system_exchange)
        logger.info(f"Отправлено системное событие: {event_name}")

    async def send_custom_message(
        self,
        message: MessageModel | dict[str, Any],
        exchange_name: str,
        routing_key: str | None = None,
    ) -> None:
        """Отправить произвольное сообщение."""
        if isinstance(message, MessageModel):
            message_data = message.model_dump()
        else:
            message_data = message

        # Определяем exchange по имени
        exchange_map = {
            "notifications": notifications_exchange,
            "orders": orders_exchange,
            "system": system_exchange,
        }

        exchange = exchange_map.get(exchange_name)
        if not exchange:
            raise ValueError(f"Неизвестный exchange: {exchange_name}")

        if routing_key:
            await self.broker.publish(message_data, exchange=exchange, routing_key=routing_key)
        else:
            await self.broker.publish(message_data, exchange=exchange)
        logger.info(f"Отправлено произвольное сообщение в {exchange_name}")

    # Методы для получения сообщений (для тестирования и debugging)

    async def consume_user_notifications(
        self, handler: Callable[[dict[str, Any]], None], auto_ack: bool = True
    ) -> None:
        """Подписаться на уведомления пользователей."""

        @self.broker.subscriber(user_notifications_queue)
        async def handle_user_notification(message: dict[str, Any]) -> None:
            try:
                await handler(message)
                logger.info(f"Обработано уведомление пользователя: {message.get('id')}")
            except Exception as e:
                logger.error(f"Ошибка обработки уведомления пользователя: {e}")
                if not auto_ack:
                    raise

    async def consume_admin_notifications(
        self, handler: Callable[[dict[str, Any]], None], auto_ack: bool = True
    ) -> None:
        """Подписаться на админские уведомления."""

        @self.broker.subscriber(admin_notifications_queue)
        async def handle_admin_notification(message: dict[str, Any]) -> None:
            try:
                await handler(message)
                logger.info(f"Обработано админское уведомление: {message.get('id')}")
            except Exception as e:
                logger.error(f"Ошибка обработки админского уведомления: {e}")
                if not auto_ack:
                    raise

    async def consume_order_processing(self, handler: Callable[[dict[str, Any]], None], auto_ack: bool = True) -> None:
        """Подписаться на сообщения обработки заказов."""

        @self.broker.subscriber(order_processing_queue)
        async def handle_order_processing(message: dict[str, Any]) -> None:
            try:
                await handler(message)
                logger.info(f"Обработано сообщение о заказе: {message.get('id')}")
            except Exception as e:
                logger.error(f"Ошибка обработки сообщения о заказе: {e}")
                if not auto_ack:
                    raise

    async def consume_system_events(self, handler: Callable[[dict[str, Any]], None], auto_ack: bool = True) -> None:
        """Подписаться на системные события."""

        @self.broker.subscriber(system_events_queue)
        async def handle_system_event(message: dict[str, Any]) -> None:
            try:
                await handler(message)
                logger.info(f"Обработано системное событие: {message.get('id')}")
            except Exception as e:
                logger.error(f"Ошибка обработки системного события: {e}")
                if not auto_ack:
                    raise


# Глобальный экземпляр клиента
_client: MessageClient | None = None


def get_message_client() -> MessageClient:
    """Получить глобальный экземпляр клиента."""
    global _client
    if _client is None:
        _client = MessageClient()
    return _client


async def setup_broker() -> RabbitBroker:
    """Настройка и подключение к брокеру."""
    broker = get_broker()

    try:
        await broker.connect()
        logger.info("Успешно подключен к RabbitMQ")
        return broker
    except Exception as e:
        logger.error(f"Ошибка подключения к RabbitMQ: {e}")
        raise


async def close_broker(broker: RabbitBroker | None = None) -> None:
    """Закрытие соединения с брокером."""
    if broker is None:
        broker = get_broker()

    try:
        await broker.close()
        logger.info("Соединение с RabbitMQ закрыто")
    except Exception as e:
        logger.error(f"Ошибка при закрытии соединения с RabbitMQ: {e}")


def create_faststream_app() -> FastStream:
    """Создать FastStream приложение."""
    broker = get_broker()
    app = FastStream(broker)
    return app
