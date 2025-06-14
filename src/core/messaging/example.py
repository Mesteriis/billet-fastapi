"""Примеры использования клиента FastStream с RabbitMQ."""

import asyncio
import logging
from typing import Any

from .client import get_message_client
from .models import MessageModel

logger = logging.getLogger(__name__)


async def send_notifications_example():
    """Пример отправки различных уведомлений."""
    client = get_message_client()

    async with client.session():
        # Отправка уведомления пользователю
        await client.send_user_notification(
            user_id=123, message="Ваш заказ №456 принят в обработку", notification_type="info"
        )

        # Отправка предупреждения пользователю
        await client.send_user_notification(
            user_id=123, message="Осталось менее 24 часов до истечения подписки", notification_type="warning"
        )

        # Отправка критического уведомления
        await client.send_user_notification(
            user_id=123, message="Обнаружена подозрительная активность в вашем аккаунте", notification_type="error"
        )

        # Админское уведомление
        await client.send_admin_notification(
            message="Система обработки заказов перегружена", notification_type="warning"
        )


async def send_order_messages_example():
    """Пример отправки сообщений о заказах."""
    client = get_message_client()

    async with client.session():
        # Заказ принят в обработку
        await client.send_order_processing(
            order_id=456, status="processing", details={"priority": "high", "items_count": 3}
        )

        # Заказ завершен
        await client.send_order_processing(
            order_id=456, status="completed", details={"delivery_time": "2024-01-15 14:30:00", "total_amount": 1299.99}
        )


async def send_system_events_example():
    """Пример отправки системных событий."""
    client = get_message_client()

    async with client.session():
        # Информационное событие
        await client.send_system_event(
            event_name="service_started", event_data={"service": "order-processor", "version": "1.2.3"}, severity="info"
        )

        # Предупреждение
        await client.send_system_event(
            event_name="high_memory_usage", event_data={"memory_usage": 85, "threshold": 80}, severity="warning"
        )

        # Критическая ошибка
        await client.send_system_event(
            event_name="database_connection_lost",
            event_data={"database": "main", "retry_count": 3},
            severity="critical",
        )


async def send_custom_message_example():
    """Пример отправки произвольного сообщения."""
    client = get_message_client()

    async with client.session():
        # Создаем произвольное сообщение
        custom_message = MessageModel(
            type="custom_event",
            source="external_service",
            payload={"event_type": "payment_received", "payment_id": "PAY_123456", "amount": 999.99, "currency": "RUB"},
        )

        await client.send_custom_message(message=custom_message, exchange_name="system", routing_key="payment.received")


async def batch_sending_example():
    """Пример массовой отправки сообщений."""
    client = get_message_client()

    async with client.session():
        # Отправка уведомлений нескольким пользователям
        user_ids = [123, 124, 125, 126, 127]

        tasks = []
        for user_id in user_ids:
            task = client.send_user_notification(
                user_id=user_id,
                message=f"Привет, пользователь {user_id}! У нас есть новости для вас.",
                notification_type="info",
            )
            tasks.append(task)

        # Отправляем все уведомления параллельно
        await asyncio.gather(*tasks)
        logger.info(f"Отправлено {len(tasks)} уведомлений")


async def message_consumer_example():
    """Пример подписки на сообщения."""
    client = get_message_client()

    async def handle_user_notification(message: dict[str, Any]) -> None:
        """Обработчик уведомлений пользователей."""
        logger.info(f"Получено уведомление: {message}")
        # Здесь может быть логика отправки email, push-уведомлений и т.д.

    async def handle_system_event(message: dict[str, Any]) -> None:
        """Обработчик системных событий."""
        logger.info(f"Получено системное событие: {message}")
        # Логика мониторинга, алертов и т.д.

    await client.connect()

    # Регистрируем обработчики
    await client.consume_user_notifications(handle_user_notification)
    await client.consume_system_events(handle_system_event)

    # Запускаем обработку сообщений (это заблокирует выполнение)
    # В реальном приложении это должно быть в отдельном процессе/сервисе
    try:
        await client.broker.start()
    except KeyboardInterrupt:
        logger.info("Остановка обработки сообщений...")
    finally:
        await client.disconnect()


async def main():
    """Основная функция для тестирования примеров."""
    logging.basicConfig(level=logging.INFO)

    logger.info("Запуск примеров FastStream с RabbitMQ")

    # Примеры отправки сообщений
    await send_notifications_example()
    await send_order_messages_example()
    await send_system_events_example()
    await send_custom_message_example()
    await batch_sending_example()

    logger.info("Все примеры отправки выполнены")

    # Пример потребления сообщений (раскомментируйте для тестирования)
    # await message_consumer_example()


if __name__ == "__main__":
    asyncio.run(main())
