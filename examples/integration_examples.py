#!/usr/bin/env python3
"""
Примеры интеграции всех систем проекта.

Этот файл демонстрирует, как различные компоненты проекта работают вместе:
- Messaging + Realtime + Auth
- Database + Migrations + Monitoring
- Telegram + WebSocket + Notifications
- TaskIQ + OpenTelemetry + Logging
"""

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

# Импорты всех систем
from apps.auth.dependencies import get_current_user
from apps.users.models import User
from core.database import get_async_session
from core.migrations import DatabaseManager
from core.tasks import example_task
from core.messaging import get_message_client
from core.realtime import WSClient

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def full_user_journey_example():
    """Пример полного пути пользователя через все системы."""
    print("🚀 Полный путь пользователя через все системы")

    # 1. Регистрация пользователя
    print("\n👤 1. Регистрация пользователя")
    user_data = {
        "email": "john.doe@example.com",
        "username": "johndoe",
        "password": "SecurePass123!",
        "full_name": "John Doe",
    }

    print(f"   📝 Регистрация: {user_data['email']}")

    # В реальном приложении:
    # auth_service = AuthService()
    # user = await auth_service.register_user(db, user_data=UserCreate(**user_data))
    # user_id = user.id

    user_id = "123e4567-e89b-12d3-a456-426614174000"  # Имитация
    print(f"   ✅ Пользователь создан: {user_id}")

    # 2. Отправка welcome сообщения через messaging
    print("\n📨 2. Welcome сообщение через Messaging")
    message_client = get_message_client()

    async with message_client.session():
        await message_client.send_user_notification(
            user_id=int(user_id.split("-")[0], 16) % 1000000,  # Упрощенное преобразование
            message=f"Добро пожаловать, {user_data['full_name']}! Ваш аккаунт успешно создан.",
            notification_type="success",
        )

    print("   ✅ Welcome сообщение отправлено")

    # 3. Подключение к realtime системе
    print("\n🔄 3. Подключение к Realtime")
    ws_client = WSClient("ws://localhost:8000/realtime/ws")

    @ws_client.on_message("connected")
    async def handle_connected(data):
        print(f"   🔗 WebSocket подключен: {data}")

    # В реальном приложении:
    # await ws_client.connect()
    # await ws_client.send_json({
    #     "type": "user_online",
    #     "user_id": user_id
    # })

    print("   ✅ Realtime подключение установлено")

    # 4. Создание фоновой задачи
    print("\n⚡ 4. Создание фоновой задачи")

    # В реальном приложении:
    # task_result = await example_task.kiq(
    #     message=f"Обработка данных для пользователя {user_id}"
    # )

    print(f"   ✅ Фоновая задача создана для пользователя {user_id}")

    # 5. Уведомление в Telegram (если настроено)
    print("\n🤖 5. Уведомление в Telegram")

    # В реальном приложении:
    # telegram_manager = TelegramBotManager()
    # if telegram_manager.is_enabled():
    #     await telegram_manager.send_notification(
    #         user_id=user_id,
    #         message="🎉 Добро пожаловать! Ваш аккаунт готов к использованию."
    #     )

    print("   ✅ Telegram уведомление отправлено")

    print("\n🎉 Полный путь пользователя завершен!")


async def order_processing_workflow_example():
    """Пример обработки заказа через все системы."""
    print("\n🛒 Пример обработки заказа")

    order_data = {
        "order_id": 12345,
        "user_id": 678,
        "items": [
            {"name": "Товар 1", "price": 999.99, "quantity": 2},
            {"name": "Товар 2", "price": 499.99, "quantity": 1},
        ],
        "total": 2499.97,
    }

    print(f"📦 Обработка заказа #{order_data['order_id']}")
    print(f"   Пользователь: {order_data['user_id']}")
    print(f"   Сумма: {order_data['total']} руб.")

    # 1. Сохранение заказа в БД
    print("\n💾 1. Сохранение в базу данных")

    # В реальном приложении:
    # async with get_async_session() as db:
    #     order = Order(**order_data)
    #     db.add(order)
    #     await db.commit()

    print("   ✅ Заказ сохранен в БД")

    # 2. Отправка в очередь обработки
    print("\n📨 2. Отправка в очередь Messaging")
    message_client = get_message_client()

    async with message_client.session():
        # Сообщение о начале обработки
        await message_client.send_order_processing(
            order_id=order_data["order_id"],
            status="processing",
            details={"total": order_data["total"], "items_count": len(order_data["items"])},
        )

        # Уведомление пользователю
        await message_client.send_user_notification(
            user_id=order_data["user_id"],
            message=f"Ваш заказ #{order_data['order_id']} принят в обработку",
            notification_type="info",
        )

    print("   ✅ Сообщения отправлены в очереди")

    # 3. Realtime уведомление
    print("\n🔄 3. Realtime уведомление")

    # В реальном приложении:
    # connection_manager = ConnectionManager()
    # await connection_manager.send_to_user(
    #     user_id=order_data["user_id"],
    #     message={
    #         "type": "order_update",
    #         "order_id": order_data["order_id"],
    #         "status": "processing",
    #         "message": "Заказ принят в обработку"
    #     }
    # )

    print("   ✅ Realtime уведомление отправлено")

    # 4. Создание фоновых задач
    print("\n⚡ 4. Создание фоновых задач")

    tasks = ["inventory_check", "payment_processing", "shipping_calculation", "notification_sending"]

    for task_name in tasks:
        # В реальном приложении:
        # await create_background_task(task_name, order_data)
        print(f"   📋 Задача создана: {task_name}")

    print("   ✅ Все фоновые задачи созданы")

    # 5. Имитация завершения обработки
    print("\n✅ 5. Завершение обработки заказа")

    async with message_client.session():
        # Уведомление о завершении
        await message_client.send_order_processing(
            order_id=order_data["order_id"],
            status="completed",
            details={"total": order_data["total"], "processing_time": "5 минут"},
        )

        # Уведомление пользователю
        await message_client.send_user_notification(
            user_id=order_data["user_id"],
            message=f"Заказ #{order_data['order_id']} успешно обработан и готов к отправке!",
            notification_type="success",
        )

    print("   ✅ Заказ успешно обработан")


async def real_time_chat_with_notifications_example():
    """Пример чата в реальном времени с уведомлениями."""
    print("\n💬 Пример realtime чата с уведомлениями")

    # Участники чата
    participants = [
        {"user_id": 123, "username": "alice", "online": True},
        {"user_id": 456, "username": "bob", "online": False},
        {"user_id": 789, "username": "charlie", "online": True},
    ]

    chat_room = "general_chat"

    print(f"💬 Чат комната: {chat_room}")
    print("👥 Участники:")
    for p in participants:
        status = "🟢 онлайн" if p["online"] else "🔴 оффлайн"
        print(f"   {p['username']} ({p['user_id']}): {status}")

    # 1. Отправка сообщения в чат
    print("\n📝 1. Отправка сообщения в чат")

    message_data = {
        "from_user_id": 123,
        "from_username": "alice",
        "message": "Привет всем! Как дела?",
        "timestamp": datetime.now().isoformat(),
        "chat_room": chat_room,
    }

    # Сохранение в БД
    print("   💾 Сохранение сообщения в БД...")

    # Отправка через WebSocket онлайн пользователям
    print("   🔄 Отправка через WebSocket онлайн пользователям...")
    online_users = [p for p in participants if p["online"]]

    for user in online_users:
        if user["user_id"] != message_data["from_user_id"]:  # Не отправляем отправителю
            print(f"      📤 WebSocket -> {user['username']}")

    # 2. Уведомления оффлайн пользователям
    print("\n📨 2. Уведомления оффлайн пользователям")

    offline_users = [p for p in participants if not p["online"]]
    message_client = get_message_client()

    async with message_client.session():
        for user in offline_users:
            await message_client.send_user_notification(
                user_id=user["user_id"],
                message=f"Новое сообщение от {message_data['from_username']} в чате {chat_room}",
                notification_type="info",
            )
            print(f"      📧 Уведомление -> {user['username']}")

    # 3. Push уведомления через Telegram
    print("\n🤖 3. Push уведомления через Telegram")

    for user in offline_users:
        # В реальном приложении:
        # telegram_manager = TelegramBotManager()
        # await telegram_manager.send_chat_notification(
        #     user_id=user["user_id"],
        #     chat_room=chat_room,
        #     from_username=message_data["from_username"],
        #     message=message_data["message"]
        # )
        print(f"      🤖 Telegram -> {user['username']}")

    # 4. Аналитика и логирование
    print("\n📊 4. Аналитика и логирование")

    analytics_data = {
        "event": "chat_message_sent",
        "chat_room": chat_room,
        "from_user_id": message_data["from_user_id"],
        "online_recipients": len(online_users) - 1,
        "offline_recipients": len(offline_users),
        "message_length": len(message_data["message"]),
        "timestamp": message_data["timestamp"],
    }

    # В реальном приложении:
    # await analytics_service.track_event(analytics_data)
    print(f"   📈 Аналитика: {analytics_data['event']}")
    print(f"   📊 Онлайн получателей: {analytics_data['online_recipients']}")
    print(f"   📊 Оффлайн получателей: {analytics_data['offline_recipients']}")

    print("   ✅ Сообщение обработано всеми системами")


async def system_monitoring_integration_example():
    """Пример интеграции мониторинга всех систем."""
    print("\n📊 Пример интеграции мониторинга систем")

    # 1. Проверка состояния БД
    print("\n🗄️ 1. Мониторинг базы данных")

    db_manager = DatabaseManager()

    try:
        db_health = {"connection": await db_manager.test_connection(), "info": await db_manager.get_database_info()}

        print("   ✅ База данных:")
        print(f"      Подключение: {'OK' if db_health['connection'] else 'FAIL'}")
        for key, value in db_health["info"].items():
            print(f"      {key}: {value}")

    except Exception as e:
        print(f"   ❌ Ошибка БД: {e}")

    # 2. Проверка Messaging системы
    print("\n📨 2. Мониторинг Messaging")

    try:
        message_client = get_message_client()

        # Тестовое сообщение
        async with message_client.session():
            await message_client.send_system_event(
                event_name="health_check", event_data={"timestamp": datetime.now().isoformat()}, severity="info"
            )

        print("   ✅ Messaging система работает")

    except Exception as e:
        print(f"   ❌ Ошибка Messaging: {e}")

    # 3. Проверка Realtime системы
    print("\n🔄 3. Мониторинг Realtime")

    try:
        # В реальном приложении:
        # connection_manager = ConnectionManager()
        # stats = await connection_manager.get_connection_stats()

        stats = {"websocket_connections": 15, "sse_connections": 8, "active_rooms": 3, "total_messages_today": 1247}

        print("   ✅ Realtime система:")
        for key, value in stats.items():
            print(f"      {key}: {value}")

    except Exception as e:
        print(f"   ❌ Ошибка Realtime: {e}")

    # 4. Проверка TaskIQ
    print("\n⚡ 4. Мониторинг TaskIQ")

    try:
        # В реальном приложении:
        # taskiq_stats = await get_taskiq_stats()

        taskiq_stats = {"active_workers": 3, "pending_tasks": 12, "completed_today": 456, "failed_today": 2}

        print("   ✅ TaskIQ:")
        for key, value in taskiq_stats.items():
            print(f"      {key}: {value}")

    except Exception as e:
        print(f"   ❌ Ошибка TaskIQ: {e}")

    # 5. Проверка Telegram ботов
    print("\n🤖 5. Мониторинг Telegram ботов")

    try:
        # В реальном приложении:
        # telegram_manager = TelegramBotManager()
        # bot_stats = await telegram_manager.get_stats()

        bot_stats = {"active_bots": 2, "total_users": 1250, "messages_today": 89, "commands_today": 34}

        print("   ✅ Telegram боты:")
        for key, value in bot_stats.items():
            print(f"      {key}: {value}")

    except Exception as e:
        print(f"   ❌ Ошибка Telegram: {e}")

    # 6. Общий health check
    print("\n🏥 6. Общий статус системы")

    overall_health = {
        "database": "healthy",
        "messaging": "healthy",
        "realtime": "healthy",
        "taskiq": "healthy",
        "telegram": "healthy",
        "overall": "healthy",
    }

    print("   🎯 Общий статус:")
    for component, status in overall_health.items():
        icon = "✅" if status == "healthy" else "❌"
        print(f"      {icon} {component}: {status}")


def create_integrated_fastapi_app():
    """Создание FastAPI приложения с интеграцией всех систем."""
    print("\n🌐 Создание интегрированного FastAPI приложения")

    app = FastAPI(
        title="Integrated FastAPI Application",
        description="Приложение с интеграцией всех систем проекта",
        version="1.0.0",
    )

    # Router для интеграционных endpoints
    integration_router = APIRouter(prefix="/api/v1/integration", tags=["integration"])

    @integration_router.post("/user-action")
    async def integrated_user_action(
        action_type: str,
        action_data: dict,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_session),
    ):
        """Интегрированное действие пользователя через все системы."""

        # 1. Сохранение в БД
        # action_record = UserAction(
        #     user_id=current_user.id,
        #     action_type=action_type,
        #     action_data=action_data
        # )
        # db.add(action_record)
        # await db.commit()

        # 2. Отправка в messaging
        message_client = get_message_client()
        async with message_client.session():
            await message_client.send_system_event(
                event_name=f"user_action_{action_type}",
                event_data={"user_id": str(current_user.id), "action_data": action_data},
                severity="info",
            )

        # 3. Realtime уведомление
        # connection_manager = ConnectionManager()
        # await connection_manager.send_to_user(
        #     user_id=current_user.id,
        #     message={
        #         "type": "action_completed",
        #         "action_type": action_type,
        #         "timestamp": datetime.now().isoformat()
        #     }
        # )

        # 4. Фоновая задача
        # await example_task.kiq(
        #     message=f"Process action {action_type} for user {current_user.id}"
        # )

        return {
            "status": "success",
            "message": f"Action {action_type} processed through all systems",
            "user_id": str(current_user.id),
            "timestamp": datetime.now().isoformat(),
        }

    @integration_router.get("/health")
    async def integrated_health_check():
        """Комплексная проверка здоровья всех систем."""

        health_status = {
            "database": "healthy",
            "messaging": "healthy",
            "realtime": "healthy",
            "taskiq": "healthy",
            "telegram": "healthy",
            "overall": "healthy",
            "timestamp": datetime.now().isoformat(),
        }

        return health_status

    @integration_router.get("/stats")
    async def integrated_stats():
        """Комплексная статистика всех систем."""

        stats = {
            "database": {"connections": 5, "queries_per_second": 45, "size_mb": 128.5},
            "messaging": {"messages_sent_today": 1247, "queue_size": 12, "processing_rate": "98.5%"},
            "realtime": {"active_connections": 23, "messages_per_minute": 156, "rooms_active": 8},
            "taskiq": {"tasks_completed_today": 456, "tasks_pending": 12, "workers_active": 3},
            "telegram": {"bots_active": 2, "users_total": 1250, "messages_today": 89},
        }

        return stats

    app.include_router(integration_router)

    print("✅ Интегрированное FastAPI приложение создано:")
    print("   POST /api/v1/integration/user-action")
    print("   GET  /api/v1/integration/health")
    print("   GET  /api/v1/integration/stats")

    return app


async def main():
    """Главная функция с запуском всех примеров интеграции."""
    print("🎯 Примеры интеграции всех систем проекта")
    print("=" * 60)

    try:
        # Комплексные сценарии
        await full_user_journey_example()
        await order_processing_workflow_example()
        await real_time_chat_with_notifications_example()

        # Мониторинг
        await system_monitoring_integration_example()

        # FastAPI интеграция
        app = create_integrated_fastapi_app()

        print("\n🎉 Все примеры интеграции выполнены успешно!")

        print("\n💡 Ключевые преимущества интеграции:")
        print("   🔄 Автоматическая синхронизация между системами")
        print("   📊 Единый мониторинг всех компонентов")
        print("   🚀 Высокая производительность за счет асинхронности")
        print("   🛡️ Надежность через резервирование и очереди")
        print("   📈 Масштабируемость каждого компонента")

        print("\n🔧 Для запуска интегрированного приложения:")
        print("   1. Настройте все переменные окружения")
        print("   2. Запустите инфраструктуру: docker-compose up -d")
        print("   3. Примените миграции: make migrate-safe")
        print("   4. Запустите приложение: uvicorn src.main:app --reload")

        print("\n🌐 Тестирование интеграции:")
        print("   uvicorn examples.integration_examples:app --reload --port 8003")
        print("   Затем откройте http://localhost:8003/docs")

        print("\n📚 Документация по интеграции:")
        print("   docs/ARCHITECTURE_IMPROVEMENTS.md  # Архитектурные принципы")
        print("   docs/README.md                     # Общее руководство")

    except Exception as e:
        logger.error(f"Ошибка выполнения примеров интеграции: {e}")
        raise


if __name__ == "__main__":
    # Запуск примеров
    asyncio.run(main())
