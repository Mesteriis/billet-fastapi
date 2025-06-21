"""FastStream RabbitMQ Messaging Core.

This module provides the core messaging functionality using FastStream and RabbitMQ
for asynchronous message processing in the application.

Features:
    - RabbitMQ broker integration with FastStream
    - Pre-configured exchanges and queues for different message types
    - Async message client for sending and consuming messages
    - Support for user notifications, order processing, and system events
    - Graceful connection management with context managers
    - Rich error handling and logging

Components:
    - MessageClient: Async client for message operations
    - Pre-configured exchanges: notifications, orders, system
    - Pre-configured queues for different message types
    - Helper functions for broker setup and management

Example:
    Basic message sending::

        from core.messaging.core import get_message_client

        async def notify_user():
            client = get_message_client()
            async with client.session():
                await client.send_user_notification(
                    user_id=123,
                    message="Welcome to the platform!",
                    notification_type="welcome"
                )

    Order processing workflow::

        async def process_order(order_id: int):
            client = get_message_client()
            async with client.session():
                # Send processing notification
                await client.send_order_processing(
                    order_id=order_id,
                    status="processing",
                    details={"step": "payment_validation"}
                )

                # Later, send completion
                await client.send_order_processing(
                    order_id=order_id,
                    status="completed",
                    details={"total_amount": 99.99}
                )

    System events::

        async def log_system_event():
            client = get_message_client()
            async with client.session():
                await client.send_system_event(
                    event_name="user_registered",
                    event_data={"user_id": 123, "source": "web"},
                    severity="info"
                )

    Message consumption::

        async def setup_handlers():
            client = get_message_client()

            async def handle_notification(message: dict):
                user_id = message["payload"]["user_id"]
                print(f"Processing notification for user {user_id}")

            await client.consume_user_notifications(handle_notification)

Note:
    All messaging operations are async and require proper connection management.
    Use the session context manager for automatic connection handling.
"""

import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any

from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue

from core.config import get_settings
from core.exceptions.core_base import CoreMessagingPublishError

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
    """Asynchronous RabbitMQ client for message operations using FastStream.

    Provides high-level interface for sending and consuming messages
    across different exchanges and queues. Manages connections automatically
    and provides typed message sending methods.

    Attributes:
        broker (RabbitBroker): The FastStream RabbitMQ broker instance
        _is_connected (bool): Internal connection state tracking

    Example:
        Basic usage with session management::

            client = MessageClient()
            async with client.session():
                await client.send_user_notification(
                    user_id=123,
                    message="Hello World!",
                    notification_type="info"
                )

        Manual connection management::

            client = MessageClient()
            await client.connect()
            try:
                await client.send_system_event("app_started", {})
            finally:
                await client.disconnect()

        Custom broker configuration::

            custom_broker = get_broker()
            client = MessageClient(broker=custom_broker)

    Note:
        Always use the session context manager or manual connect/disconnect
        to ensure proper connection lifecycle management.
    """

    def __init__(self, broker: RabbitBroker | None = None):
        """Initialize the message client.

        Args:
            broker (RabbitBroker | None): Custom broker instance.
                If None, uses the default broker from get_broker()

        Example:
            With default broker::

                client = MessageClient()

            With custom broker::

                custom_broker = RabbitBroker("amqp://custom-server")
                client = MessageClient(broker=custom_broker)
        """
        self.broker = broker or get_broker()
        self._is_connected = False

    async def connect(self) -> None:
        """Establish connection to the RabbitMQ broker.

        Raises:
            ConnectionError: If connection to RabbitMQ fails
            Exception: Other broker connection errors

        Example:
            Manual connection::

                client = MessageClient()
                await client.connect()
                # Now client is ready for operations

        Note:
            This method is idempotent - calling it multiple times
            on an already connected client has no effect.
        """
        if not self._is_connected:
            await self.broker.connect()
            self._is_connected = True
            logger.info("MessageClient подключен к RabbitMQ")

    async def disconnect(self) -> None:
        """Close connection to the RabbitMQ broker.

        Example:
            Clean disconnection::

                client = MessageClient()
                await client.connect()
                # ... operations ...
                await client.disconnect()

        Note:
            This method is idempotent - calling it multiple times
            or on a disconnected client has no effect.
        """
        if self._is_connected:
            await self.broker.close()
            self._is_connected = False
            logger.info("MessageClient отключен от RabbitMQ")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator["MessageClient", None]:
        """Context manager for automatic connection lifecycle.

        Automatically connects on entry and disconnects on exit,
        even if exceptions occur during message operations.

        Yields:
            MessageClient: Connected client instance

        Example:
            Recommended usage pattern::

                client = MessageClient()
                async with client.session():
                    await client.send_user_notification(123, "Hello!")
                    await client.send_system_event("user_notified", {})
                # Automatically disconnected here

            Error handling::

                async with client.session():
                    try:
                        await client.send_user_notification(123, "Hello!")
                    except Exception as e:
                        logger.error(f"Failed to send notification: {e}")
                        # Still disconnects properly
        """
        try:
            await self.connect()
            yield self
        finally:
            await self.disconnect()

    # Message sending methods with comprehensive documentation

    async def send_user_notification(
        self,
        user_id: int,
        message: str,
        notification_type: str = "info",
        routing_key: str = "user.notification",
        **kwargs,
    ) -> None:
        """Send notification message to a specific user.

        Publishes a user notification message to the notifications exchange
        with the specified routing key for proper queue routing.

        Args:
            user_id (int): Target user identifier
            message (str): Notification message content
            notification_type (str): Type of notification ("info", "warning", "error", "success")
            routing_key (str): RabbitMQ routing key for message routing
            **kwargs: Additional message metadata

        Example:
            Basic notification::

                await client.send_user_notification(
                    user_id=123,
                    message="Your order has been confirmed",
                    notification_type="success"
                )

            With custom routing::

                await client.send_user_notification(
                    user_id=456,
                    message="Payment failed",
                    notification_type="error",
                    routing_key="user.payment.error",
                    priority=5
                )

        Note:
            The message is automatically wrapped in UserNotificationMessage
            with proper timestamp and metadata before publishing.
        """
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
        """Send notification message to administrators.

        Publishes an admin notification to alert system administrators
        about important events or issues requiring attention.

        Args:
            message (str): Admin notification message content
            notification_type (str): Notification severity ("info", "warning", "error", "critical")
            routing_key (str): RabbitMQ routing key for admin notifications
            **kwargs: Additional message metadata

        Example:
            System alert::

                await client.send_admin_notification(
                    message="High memory usage detected: 95%",
                    notification_type="warning",
                    routing_key="admin.system.warning"
                )

            Critical error::

                await client.send_admin_notification(
                    message="Database connection lost",
                    notification_type="critical",
                    routing_key="admin.database.error"
                )

        Note:
            Admin notifications use user_id=0 as a special identifier
            to distinguish them from regular user notifications.
        """
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
        """Send order processing status message.

        Publishes order status updates for tracking order processing
        workflow across different services and systems.

        Args:
            order_id (int): Order identifier
            status (str): Current order status ("pending", "processing", "completed", "failed")
            details (dict[str, Any] | None): Additional order details and metadata
            **kwargs: Additional message metadata

        Example:
            Order started processing::

                await client.send_order_processing(
                    order_id=12345,
                    status="processing",
                    details={
                        "step": "payment_validation",
                        "estimated_completion": "2024-01-15T10:30:00Z"
                    }
                )

            Order completed::

                await client.send_order_processing(
                    order_id=12345,
                    status="completed",
                    details={
                        "total_amount": 99.99,
                        "completion_time": "2024-01-15T10:25:33Z",
                        "items_count": 3
                    }
                )

        Note:
            The routing key is automatically determined based on status:
            - "processing"/"pending" → "process" routing key
            - Other statuses → "completed" routing key
        """
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
        """Send system-wide event message.

        Publishes system events for monitoring, analytics, and
        cross-service communication about important system occurrences.

        Args:
            event_name (str): Descriptive name of the event
            event_data (dict[str, Any] | None): Event-specific data and context
            severity (str): Event severity level ("debug", "info", "warning", "error", "critical")
            **kwargs: Additional message metadata

        Example:
            User registration event::

                await client.send_system_event(
                    event_name="user_registered",
                    event_data={
                        "user_id": 123,
                        "email": "user@example.com",
                        "registration_source": "web",
                        "ip_address": "192.168.1.1"
                    },
                    severity="info"
                )

            Security event::

                await client.send_system_event(
                    event_name="suspicious_login_attempt",
                    event_data={
                        "user_id": 456,
                        "ip_address": "10.0.0.1",
                        "attempt_count": 5,
                        "blocked": True
                    },
                    severity="warning"
                )

        Note:
            System events use fanout exchange, so all subscribers
            will receive the message regardless of routing keys.
        """
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
        """Send custom message to specified exchange.

        Provides flexibility for sending arbitrary messages that don't
        fit the predefined message types. Useful for custom integrations
        and specialized messaging patterns.

        Args:
            message (MessageModel | dict[str, Any]): Message content (model or dict)
            exchange_name (str): Target exchange name ("notifications", "orders", "system")
            routing_key (str | None): Optional routing key for directed delivery

        Raises:
            ValueError: If exchange_name is not recognized

        Example:
            Custom notification::

                custom_msg = {
                    "type": "custom_alert",
                    "data": {"alert_id": 789, "message": "Custom alert"},
                    "timestamp": "2024-01-15T10:30:00Z"
                }

                await client.send_custom_message(
                    message=custom_msg,
                    exchange_name="notifications",
                    routing_key="custom.alert"
                )

            Using message model::

                msg = CustomMessageModel(
                    content="Custom content",
                    metadata={"priority": "high"}
                )

                await client.send_custom_message(
                    message=msg,
                    exchange_name="system"
                )

        Note:
            Available exchanges are: "notifications", "orders", "system".
            Routing key is optional for fanout exchanges.
        """
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
            raise CoreMessagingPublishError("rabbitmq", f"Неизвестный exchange: {exchange_name}")

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
    """Get global message client instance.

    Returns a singleton MessageClient instance for application-wide
    message operations. The instance is created lazily on first access.

    Returns:
        MessageClient: Global message client instance

    Example:
        Getting the global client::

            from core.messaging.core import get_message_client

            async def send_welcome_message(user_id: int):
                client = get_message_client()
                async with client.session():
                    await client.send_user_notification(
                        user_id=user_id,
                        message="Welcome to our platform!",
                        notification_type="welcome"
                    )

    Note:
        The global client uses the default broker configuration.
        For custom configurations, create MessageClient instances directly.
    """
    global _client
    if _client is None:
        _client = MessageClient()
    return _client


async def setup_broker() -> RabbitBroker:
    """Setup and connect to RabbitMQ broker.

    Initializes the RabbitMQ broker connection with proper error handling
    and logging. Used during application startup.

    Returns:
        RabbitBroker: Connected broker instance

    Raises:
        ConnectionError: If unable to connect to RabbitMQ
        Exception: Other broker setup errors

    Example:
        Application startup::

            async def startup():
                try:
                    broker = await setup_broker()
                    logger.info("Messaging system ready")
                    return broker
                except Exception as e:
                    logger.error(f"Failed to setup messaging: {e}")
                    raise

    Note:
        This function should be called during application initialization
        before any message operations are attempted.
    """
    broker = get_broker()

    try:
        await broker.connect()
        logger.info("Успешно подключен к RabbitMQ")
        return broker
    except Exception as e:
        logger.error(f"Ошибка подключения к RabbitMQ: {e}")
        raise


async def close_broker(broker: RabbitBroker | None = None) -> None:
    """Close RabbitMQ broker connection.

    Gracefully closes the broker connection with proper error handling
    and logging. Used during application shutdown.

    Args:
        broker (RabbitBroker | None): Broker to close. If None, uses default broker

    Example:
        Application shutdown::

            async def shutdown():
                try:
                    await close_broker()
                    logger.info("Messaging system closed")
                except Exception as e:
                    logger.error(f"Error during messaging shutdown: {e}")

        With specific broker::

            custom_broker = get_broker()
            await close_broker(custom_broker)

    Note:
        This function should be called during application shutdown
        to ensure clean resource cleanup.
    """
    if broker is None:
        broker = get_broker()

    try:
        await broker.close()
        logger.info("Соединение с RabbitMQ закрыто")
    except Exception as e:
        logger.error(f"Ошибка при закрытии соединения с RabbitMQ: {e}")


def create_faststream_app() -> FastStream:
    """Create FastStream application instance.

    Creates a FastStream application with the configured RabbitMQ broker.
    Used for running the messaging service as a standalone application.

    Returns:
        FastStream: Configured FastStream application

    Example:
        Running as standalone service::

            app = create_faststream_app()

            @app.on_startup
            async def startup():
                logger.info("FastStream app starting...")

            if __name__ == "__main__":
                faststream.run(app)

        Integration with web application::

            faststream_app = create_faststream_app()
            # Register message handlers
            # Start with main application

    Note:
        The application uses the default broker configuration.
        Message handlers need to be registered separately.
    """
    broker = get_broker()
    app = FastStream(broker)
    return app
