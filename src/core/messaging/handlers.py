"""Обработчики сообщений RabbitMQ."""

import logging
from typing import Any

from faststream import Depends
from faststream.rabbit import RabbitMessage

from .broker import (
    admin_notifications_queue,
    get_broker,
    order_completed_queue,
    order_processing_queue,
    system_events_queue,
    user_notifications_queue,
)
from .models import OrderProcessingMessage, SystemEventMessage, UserNotificationMessage

logger = logging.getLogger(__name__)

# Создаем брокер для регистрации обработчиков
broker = get_broker()


@broker.subscriber(user_notifications_queue)
async def handle_user_notification(
    message: dict[str, Any],
    raw_message: RabbitMessage = Depends(),
) -> None:
    """Обработчик уведомлений пользователей."""
    try:
        # Валидируем сообщение
        notification = UserNotificationMessage(**message)

        logger.info(
            f"Получено уведомление для пользователя {notification.payload.user_id}: " f"{notification.payload.message}"
        )

        # Здесь можно добавить логику отправки уведомления
        # Например, через email, push-уведомления, SMS и т.д.
        await process_user_notification(notification)

        # Подтверждаем обработку сообщения
        await raw_message.ack()

    except Exception as e:
        logger.error(f"Ошибка обработки уведомления пользователя: {e}")
        await raw_message.nack(requeue=True)


@broker.subscriber(admin_notifications_queue)
async def handle_admin_notification(
    message: dict[str, Any],
    raw_message: RabbitMessage = Depends(),
) -> None:
    """Обработчик админских уведомлений."""
    try:
        notification = UserNotificationMessage(**message)

        logger.info(f"Получено админское уведомление: {notification.payload.message}")

        # Логика для админских уведомлений
        await process_admin_notification(notification)

        await raw_message.ack()

    except Exception as e:
        logger.error(f"Ошибка обработки админского уведомления: {e}")
        await raw_message.nack(requeue=True)


@broker.subscriber(order_processing_queue)
async def handle_order_processing(
    message: dict[str, Any],
    raw_message: RabbitMessage = Depends(),
) -> None:
    """Обработчик сообщений о заказах в процессе обработки."""
    try:
        order_msg = OrderProcessingMessage(**message)

        logger.info(f"Получено сообщение о заказе {order_msg.payload.order_id}: " f"статус {order_msg.payload.status}")

        # Логика обработки заказа
        await process_order(order_msg)

        await raw_message.ack()

    except Exception as e:
        logger.error(f"Ошибка обработки сообщения о заказе: {e}")
        await raw_message.nack(requeue=True)


@broker.subscriber(order_completed_queue)
async def handle_order_completed(
    message: dict[str, Any],
    raw_message: RabbitMessage = Depends(),
) -> None:
    """Обработчик завершенных заказов."""
    try:
        order_msg = OrderProcessingMessage(**message)

        logger.info(f"Заказ {order_msg.payload.order_id} завершен со статусом {order_msg.payload.status}")

        # Логика для завершенных заказов
        await process_completed_order(order_msg)

        await raw_message.ack()

    except Exception as e:
        logger.error(f"Ошибка обработки завершенного заказа: {e}")
        await raw_message.nack(requeue=True)


@broker.subscriber(system_events_queue)
async def handle_system_event(
    message: dict[str, Any],
    raw_message: RabbitMessage = Depends(),
) -> None:
    """Обработчик системных событий."""
    try:
        event = SystemEventMessage(**message)

        logger.info(f"Получено системное событие {event.payload.event_name} " f"с уровнем {event.payload.severity}")

        # Логика обработки системных событий
        await process_system_event(event)

        await raw_message.ack()

    except Exception as e:
        logger.error(f"Ошибка обработки системного события: {e}")
        await raw_message.nack(requeue=True)


# Бизнес-логика обработчиков


async def process_user_notification(notification: UserNotificationMessage) -> None:
    """Бизнес-логика обработки уведомлений пользователей."""
    user_id = notification.payload.user_id
    message = notification.payload.message
    notification_type = notification.payload.notification_type

    # Здесь может быть логика отправки через различные каналы
    if notification_type == "error":
        logger.error(f"Критическое уведомление для пользователя {user_id}: {message}")
        # Отправка через приоритетный канал

    elif notification_type == "warning":
        logger.warning(f"Предупреждение для пользователя {user_id}: {message}")
        # Отправка через обычный канал

    else:  # info
        logger.info(f"Информационное уведомление для пользователя {user_id}: {message}")
        # Отправка через стандартный канал

    # Пример: сохранение в базу данных, отправка email и т.д.
    await save_notification_to_db(user_id, message, notification_type)


async def process_admin_notification(notification: UserNotificationMessage) -> None:
    """Бизнес-логика обработки админских уведомлений."""
    message = notification.payload.message
    notification_type = notification.payload.notification_type

    # Логика для админских уведомлений - отправка в Slack, email и т.д.
    if notification_type in ["error", "warning"]:
        await send_urgent_admin_alert(message, notification_type)
    else:
        await send_admin_info(message)


async def process_order(order_msg: OrderProcessingMessage) -> None:
    """Бизнес-логика обработки заказов."""
    order_id = order_msg.payload.order_id
    status = order_msg.payload.status
    details = order_msg.payload.details

    if status == "processing":
        logger.info(f"Начинаем обработку заказа {order_id}")
        # Логика начала обработки

    elif status == "pending":
        logger.info(f"Заказ {order_id} ожидает обработки")
        # Логика постановки в очередь

    # Обновление статуса в базе данных
    await update_order_status(order_id, status, details)


async def process_completed_order(order_msg: OrderProcessingMessage) -> None:
    """Бизнес-логика обработки завершенных заказов."""
    order_id = order_msg.payload.order_id
    status = order_msg.payload.status

    if status == "completed":
        logger.info(f"Заказ {order_id} успешно завершен")
        # Отправка уведомления клиенту
        # Обновление статистики

    elif status == "cancelled":
        logger.info(f"Заказ {order_id} отменен")
        # Логика отмены заказа

    elif status == "failed":
        logger.error(f"Заказ {order_id} завершился с ошибкой")
        # Логика обработки ошибок

    await finalize_order(order_id, status)


async def process_system_event(event: SystemEventMessage) -> None:
    """Бизнес-логика обработки системных событий."""
    event_name = event.payload.event_name
    event_data = event.payload.event_data
    severity = event.payload.severity

    if severity == "critical":
        logger.critical(f"Критическое системное событие: {event_name}")
        # Немедленное оповещение администраторов
        await send_critical_alert(event_name, event_data)

    elif severity == "error":
        logger.error(f"Системная ошибка: {event_name}")
        # Логирование ошибки, уведомление техподдержки

    elif severity == "warning":
        logger.warning(f"Системное предупреждение: {event_name}")

    else:  # info
        logger.info(f"Системное событие: {event_name}")

    # Сохранение события в базу для аналитики
    await save_system_event(event_name, event_data, severity)


# Вспомогательные функции (заглушки для примера)


async def save_notification_to_db(user_id: int, message: str, notification_type: str) -> None:
    """Сохранение уведомления в базу данных."""
    # Здесь будет реальная логика сохранения в БД
    logger.debug(f"Сохранено уведомление в БД для пользователя {user_id}")


async def send_urgent_admin_alert(message: str, notification_type: str) -> None:
    """Отправка срочного уведомления администратору."""
    # Интеграция со Slack, Telegram, email и т.д.
    logger.debug(f"Отправлено срочное уведомление администратору: {message}")


async def send_admin_info(message: str) -> None:
    """Отправка информационного уведомления администратору."""
    logger.debug(f"Отправлено информационное уведомление администратору: {message}")


async def update_order_status(order_id: int, status: str, details: dict[str, Any]) -> None:
    """Обновление статуса заказа в базе данных."""
    logger.debug(f"Обновлен статус заказа {order_id} на {status}")


async def finalize_order(order_id: int, status: str) -> None:
    """Финализация заказа."""
    logger.debug(f"Финализирован заказ {order_id} со статусом {status}")


async def send_critical_alert(event_name: str, event_data: dict[str, Any]) -> None:
    """Отправка критического оповещения."""
    logger.debug(f"Отправлено критическое оповещение о событии: {event_name}")


async def save_system_event(event_name: str, event_data: dict[str, Any], severity: str) -> None:
    """Сохранение системного события."""
    logger.debug(f"Сохранено системное событие: {event_name} ({severity})")
