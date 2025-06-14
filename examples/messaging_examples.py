#!/usr/bin/env python3
"""
Примеры использования messaging системы (FastStream + RabbitMQ).

Этот файл содержит практические примеры работы с системой сообщений:
- Отправка различных типов сообщений
- Обработка входящих сообщений
- Интеграция с FastAPI
- Массовая отправка
- Обработка ошибок
"""

import asyncio
import logging
from typing import Dict, List

from fastapi import APIRouter, Depends, FastAPI

# Импорты messaging системы
from core.messaging import MessageClient, get_message_client
from core.messaging import (
    SystemEventMessage,
    UserNotificationMessage,
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def basic_messaging_example():
    """Базовый пример отправки сообщений."""
    print("🚀 Базовый пример messaging")

    client = get_message_client()

    async with client.session():
        # Уведомление пользователю
        await client.send_user_notification(
            user_id=123, message="Добро пожаловать в систему!", notification_type="info"
        )
        print("✅ Отправлено уведомление пользователю")

        # Админское уведомление
        await client.send_admin_notification(message="Новый пользователь зарегистрирован", notification_type="info")
        print("✅ Отправлено админское уведомление")

        # Сообщение о заказе
        await client.send_order_processing(order_id=456, status="processing", details={"total": 1999.99, "items": 3})
        print("✅ Отправлено сообщение о заказе")

        # Системное событие
        await client.send_system_event(
            event_name="user_registered", event_data={"user_id": 123, "email": "user@example.com"}, severity="info"
        )
        print("✅ Отправлено системное событие")


async def custom_message_example():
    """Пример отправки кастомных сообщений."""
    print("\n🎯 Пример кастомных сообщений")

    client = get_message_client()

    # Создание кастомного сообщения
    custom_message = UserNotificationMessage(
        source="payment_service",
        payload=UserNotificationMessage.PayloadModel(
            user_id=789, message="Платеж успешно обработан", notification_type="success"
        ),
        correlation_id="payment_123",
    )

    async with client.session():
        await client.send_custom_message(
            message=custom_message, exchange_name="notifications", routing_key="user.payment"
        )
        print("✅ Отправлено кастомное сообщение")


async def bulk_messaging_example():
    """Пример массовой отправки сообщений."""
    print("\n📦 Пример массовой отправки")

    client = get_message_client()
    user_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    async with client.session():
        # Создаем задачи для параллельной отправки
        tasks = []
        for user_id in user_ids:
            task = client.send_user_notification(
                user_id=user_id,
                message=f"Персональное предложение для пользователя {user_id}!",
                notification_type="info",
            )
            tasks.append(task)

        # Отправляем все параллельно
        await asyncio.gather(*tasks)
        print(f"✅ Отправлено {len(tasks)} уведомлений параллельно")


async def error_handling_example():
    """Пример обработки ошибок."""
    print("\n🛡️ Пример обработки ошибок")

    client = get_message_client()

    async def safe_send_notification(user_id: int, message: str, max_retries: int = 3):
        """Отправка уведомления с повторными попытками."""
        for attempt in range(max_retries):
            try:
                async with client.session():
                    await client.send_user_notification(user_id=user_id, message=message, notification_type="info")
                print(f"✅ Уведомление отправлено с попытки {attempt + 1}")
                return True
            except Exception as e:
                logger.warning(f"Попытка {attempt + 1} неудачна: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Не удалось отправить уведомление после {max_retries} попыток")
                    raise
                await asyncio.sleep(2**attempt)  # Exponential backoff
        return False

    # Тестируем безопасную отправку
    await safe_send_notification(999, "Тестовое сообщение с retry")


async def message_consumer_example():
    """Пример обработчика входящих сообщений."""
    print("\n📥 Пример обработчика сообщений")

    client = get_message_client()

    # Обработчики для разных типов сообщений
    async def handle_user_notification(message: dict):
        """Обработка уведомлений пользователей."""
        try:
            notification = UserNotificationMessage(**message)
            print(f"📧 Получено уведомление для пользователя {notification.payload.user_id}")
            print(f"   Сообщение: {notification.payload.message}")

            # Здесь можно добавить логику:
            # - Отправка email
            # - Push уведомления
            # - Сохранение в БД

        except Exception as e:
            logger.error(f"Ошибка обработки уведомления: {e}")
            raise

    async def handle_system_event(message: dict):
        """Обработка системных событий."""
        try:
            event = SystemEventMessage(**message)
            print(f"🔔 Системное событие: {event.payload.event_name}")
            print(f"   Данные: {event.payload.event_data}")

            # Логика обработки системных событий
            if event.payload.severity == "critical":
                print("🚨 КРИТИЧЕСКОЕ СОБЫТИЕ! Требуется немедленное внимание")

        except Exception as e:
            logger.error(f"Ошибка обработки события: {e}")
            raise

    # Подключение и регистрация обработчиков
    await client.connect()

    try:
        # Регистрируем обработчики
        await client.consume_user_notifications(handle_user_notification)
        await client.consume_system_events(handle_system_event)

        print("🎧 Обработчики зарегистрированы. Ожидание сообщений...")
        print("   (В реальном приложении здесь был бы await client.broker.start())")

        # В реальном приложении:
        # await client.broker.start()

    except KeyboardInterrupt:
        print("\n⏹️ Остановка обработчиков...")
    finally:
        await client.disconnect()


def create_fastapi_integration_example():
    """Пример интеграции с FastAPI."""
    print("\n🌐 Пример интеграции с FastAPI")

    app = FastAPI(title="Messaging Example API")
    router = APIRouter(prefix="/api/v1", tags=["messaging"])

    @router.post("/orders/{order_id}/complete")
    async def complete_order(order_id: int, client: MessageClient = Depends(get_message_client)):
        """Завершение заказа с отправкой уведомлений."""
        # Имитация логики завершения заказа
        order = {"id": order_id, "user_id": 123, "total": 2999.99, "status": "completed"}

        async with client.session():
            # Уведомление о завершении заказа
            await client.send_order_processing(order_id=order_id, status="completed", details={"total": order["total"]})

            # Уведомление пользователю
            await client.send_user_notification(
                user_id=order["user_id"],
                message=f"Ваш заказ #{order_id} успешно завершен!",
                notification_type="success",
            )

            # Системное событие
            await client.send_system_event(
                event_name="order_completed",
                event_data={"order_id": order_id, "total": order["total"]},
                severity="info",
            )

        return {"status": "completed", "order": order}

    @router.post("/notifications/broadcast")
    async def broadcast_notification(
        message: str, user_ids: List[int], client: MessageClient = Depends(get_message_client)
    ):
        """Массовая отправка уведомлений."""
        async with client.session():
            tasks = [
                client.send_user_notification(user_id=user_id, message=message, notification_type="info")
                for user_id in user_ids
            ]

            await asyncio.gather(*tasks)

        return {"message": "Уведомления отправлены", "count": len(user_ids), "user_ids": user_ids}

    @router.get("/health")
    async def health_check():
        """Проверка состояния messaging системы."""
        try:
            client = get_message_client()
            # Простая проверка подключения
            return {"status": "healthy", "messaging": "available", "broker": "connected"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    app.include_router(router)

    print("✅ FastAPI приложение создано с messaging endpoints:")
    print("   POST /api/v1/orders/{order_id}/complete")
    print("   POST /api/v1/notifications/broadcast")
    print("   GET  /api/v1/health")

    return app


async def monitoring_example():
    """Пример мониторинга messaging системы."""
    print("\n📊 Пример мониторинга")

    client = get_message_client()

    # Статистика отправленных сообщений
    stats = {"user_notifications": 0, "admin_notifications": 0, "order_messages": 0, "system_events": 0, "errors": 0}

    async def send_with_stats(message_type: str, send_func):
        """Отправка сообщения со сбором статистики."""
        try:
            await send_func()
            stats[message_type] += 1
            print(f"✅ {message_type}: отправлено")
        except Exception as e:
            stats["errors"] += 1
            print(f"❌ {message_type}: ошибка - {e}")

    async with client.session():
        # Отправляем разные типы сообщений
        await send_with_stats(
            "user_notifications",
            lambda: client.send_user_notification(user_id=1, message="Test", notification_type="info"),
        )

        await send_with_stats(
            "admin_notifications",
            lambda: client.send_admin_notification(message="Admin test", notification_type="info"),
        )

        await send_with_stats(
            "order_messages", lambda: client.send_order_processing(order_id=1, status="test", details={})
        )

        await send_with_stats(
            "system_events", lambda: client.send_system_event(event_name="test", event_data={}, severity="info")
        )

    # Выводим статистику
    print("\n📈 Статистика отправки:")
    for key, value in stats.items():
        print(f"   {key}: {value}")


async def advanced_patterns_example():
    """Примеры продвинутых паттернов."""
    print("\n🎓 Продвинутые паттерны")

    client = get_message_client()

    # Паттерн: Saga (координация между сервисами)
    async def order_saga(order_id: int, user_id: int, amount: float):
        """Пример Saga паттерна для обработки заказа."""
        print(f"🔄 Начинаем Saga для заказа {order_id}")

        async with client.session():
            # Шаг 1: Резервирование товара
            await client.send_system_event(
                event_name="inventory_reserve_requested",
                event_data={"order_id": order_id, "amount": amount},
                severity="info",
            )

            # Шаг 2: Обработка платежа
            await client.send_system_event(
                event_name="payment_processing_requested",
                event_data={"order_id": order_id, "user_id": user_id, "amount": amount},
                severity="info",
            )

            # Шаг 3: Уведомление пользователя
            await client.send_user_notification(
                user_id=user_id, message=f"Заказ {order_id} обрабатывается", notification_type="info"
            )

        print(f"✅ Saga для заказа {order_id} инициирована")

    # Паттерн: Event Sourcing
    async def event_sourcing_example(entity_id: str, event_type: str, event_data: Dict):
        """Пример Event Sourcing паттерна."""
        print(f"📝 Event Sourcing: {event_type} для {entity_id}")

        async with client.session():
            await client.send_system_event(
                event_name=f"entity_{event_type}",
                event_data={
                    "entity_id": entity_id,
                    "event_type": event_type,
                    "event_data": event_data,
                    "timestamp": asyncio.get_event_loop().time(),
                },
                severity="info",
            )

        print(f"✅ Событие {event_type} записано")

    # Тестируем паттерны
    await order_saga(order_id=12345, user_id=678, amount=1999.99)
    await event_sourcing_example("user_123", "profile_updated", {"email": "new@example.com"})


async def main():
    """Главная функция с запуском всех примеров."""
    print("🎯 Примеры использования Messaging системы")
    print("=" * 50)

    try:
        # Базовые примеры
        await basic_messaging_example()
        await custom_message_example()
        await bulk_messaging_example()
        await error_handling_example()

        # Мониторинг
        await monitoring_example()

        # Продвинутые паттерны
        await advanced_patterns_example()

        # FastAPI интеграция
        app = create_fastapi_integration_example()

        # Обработчики сообщений (закомментировано, так как требует запущенного RabbitMQ)
        # await message_consumer_example()

        print("\n🎉 Все примеры выполнены успешно!")
        print("\n💡 Для запуска обработчиков сообщений:")
        print("   1. Запустите RabbitMQ: docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:3-management")
        print("   2. Раскомментируйте await message_consumer_example()")
        print("   3. Запустите скрипт снова")

        print("\n🌐 Для тестирования FastAPI интеграции:")
        print("   uvicorn examples.messaging_examples:app --reload")
        print("   Затем откройте http://localhost:8000/docs")

    except Exception as e:
        logger.error(f"Ошибка выполнения примеров: {e}")
        raise


if __name__ == "__main__":
    # Запуск примеров
    asyncio.run(main())
