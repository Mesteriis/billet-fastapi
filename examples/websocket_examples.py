"""Примеры использования WebSocket и SSE клиентов."""

import asyncio
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Импорты из нашего streaming модуля
from core.streaming import create_authenticated_client, create_sse_client, create_ws_client


async def websocket_basic_example():
    """Базовый пример использования WebSocket клиента."""
    print("=== WebSocket Basic Example ===")

    # Создаем клиент
    client = create_ws_client(host="localhost", port=8000)

    # Добавляем обработчики событий
    @client.on_message("system")
    async def handle_system_message(data):
        print(f"Системное сообщение: {data}")

    @client.on_message("text")
    async def handle_text_message(data):
        print(f"Текстовое сообщение: {data}")

    @client.on_message("heartbeat")
    async def handle_heartbeat(data):
        print(f"Heartbeat: {data.get('content', {}).get('timestamp', 'unknown')}")

    try:
        # Подключаемся
        connected = await client.connect()
        if not connected:
            print("Не удалось подключиться")
            return

        print(f"Подключен! Connection ID: {client.connection_id}")

        # Отправляем ping
        pong = await client.ping()
        print(f"Ping успешен: {pong}")

        # Отправляем обычное сообщение
        message_id = await client.send_message("Привет, сервер!")
        print(f"Сообщение отправлено: {message_id}")

        # Подписываемся на канал
        subscribed = await client.subscribe_to_channel("test_channel")
        print(f"Подписка на канал: {subscribed}")

        # Отправляем сообщение в канал
        sent = await client.send_to_channel("test_channel", "Сообщение в канал")
        print(f"Сообщение в канал отправлено: {sent}")

        # Ждем немного для получения сообщений
        await asyncio.sleep(5)

    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        await client.disconnect()
        print("WebSocket отключен")


async def websocket_authenticated_example():
    """Пример использования аутентифицированного WebSocket клиента."""
    print("\n=== WebSocket Authenticated Example ===")

    # Создаем аутентифицированный клиент с API ключом
    client = create_authenticated_client(
        host="localhost",
        port=8000,
        api_key="test-api-key",  # Замените на реальный API ключ
        user_id="user123",
    )

    @client.on_message("connected")
    async def handle_connected(data):
        print(f"Подключен как аутентифицированный пользователь: {data}")

    @client.on_message("error")
    async def handle_error(data):
        print(f"Ошибка: {data}")

    try:
        # Подключаемся
        connected = await client.connect()
        if connected:
            print("Аутентифицированное подключение успешно!")

            # Отправляем сообщение другому пользователю
            sent = await client.send_to_user("user456", "Привет от user123!")
            print(f"Личное сообщение отправлено: {sent}")

            # Ждем немного
            await asyncio.sleep(3)
        else:
            print("Не удалось подключиться с аутентификацией")

    except Exception as e:
        print(f"Ошибка аутентификации: {e}")
    finally:
        await client.disconnect()


async def sse_basic_example():
    """Базовый пример использования SSE клиента."""
    print("\n=== SSE Basic Example ===")

    # Создаем SSE клиент
    client = create_sse_client(host="localhost", port=8000)

    # Добавляем обработчики событий
    @client.on_event("connected")
    async def handle_connected(event_data):
        print(f"SSE подключен: {event_data}")

    @client.on_event("message")
    async def handle_message(event_data):
        print(f"SSE сообщение: {event_data}")

    @client.on_event("notification")
    async def handle_notification(event_data):
        print(f"SSE уведомление: {event_data}")

    @client.on_event("heartbeat")
    async def handle_heartbeat(event_data):
        print(f"SSE heartbeat: {event_data.get('data', {}).get('timestamp', 'unknown')}")

    try:
        # Подключаемся
        connected = await client.connect()
        if connected:
            print("SSE подключен!")

            # Отправляем уведомление всем
            sent = await client.send_notification(
                title="Тестовое уведомление", content="Это тестовое уведомление через SSE", notification_type="info"
            )
            print(f"Уведомление отправлено: {sent}")

            # Ждем события
            await asyncio.sleep(10)
        else:
            print("Не удалось подключиться к SSE")

    except Exception as e:
        print(f"Ошибка SSE: {e}")
    finally:
        await client.disconnect()


async def chat_room_example():
    """Пример реализации чат-комнаты с WebSocket."""
    print("\n=== Chat Room Example ===")

    # Создаем двух клиентов для имитации чата
    client1 = create_ws_client(host="localhost", port=8000)
    client2 = create_ws_client(host="localhost", port=8000)

    # Настраиваем обработчики для первого клиента
    @client1.on_message("text")
    async def client1_handle_message(data):
        content = data.get("content", "")
        sender = data.get("sender_id", "unknown")
        if sender != client1.connection_id:
            print(f"[Клиент 1] Получено сообщение от {sender}: {content}")

    # Настраиваем обработчики для второго клиента
    @client2.on_message("text")
    async def client2_handle_message(data):
        content = data.get("content", "")
        sender = data.get("sender_id", "unknown")
        if sender != client2.connection_id:
            print(f"[Клиент 2] Получено сообщение от {sender}: {content}")

    try:
        # Подключаем оба клиента
        connected1 = await client1.connect()
        connected2 = await client2.connect()

        if not (connected1 and connected2):
            print("Не удалось подключить всех клиентов")
            return

        # Подписываем на канал чата
        await client1.subscribe_to_channel("chat_room")
        await client2.subscribe_to_channel("chat_room")

        print("Чат-комната готова!")

        # Имитируем диалог
        await asyncio.sleep(1)
        await client1.send_to_channel("chat_room", "Привет! Как дела?")

        await asyncio.sleep(1)
        await client2.send_to_channel("chat_room", "Привет! Всё отлично, а у тебя?")

        await asyncio.sleep(1)
        await client1.send_to_channel("chat_room", "Тоже хорошо! Классная погода сегодня.")

        await asyncio.sleep(1)
        await client2.send_to_channel("chat_room", "Да, согласен! 😊")

        # Ждем немного чтобы увидеть все сообщения
        await asyncio.sleep(3)

    except Exception as e:
        print(f"Ошибка в чате: {e}")
    finally:
        await client1.disconnect()
        await client2.disconnect()
        print("Чат закрыт")


async def notification_system_example():
    """Пример системы уведомлений с SSE."""
    print("\n=== Notification System Example ===")

    # Создаем клиент-администратор для отправки уведомлений
    admin_client = create_sse_client(host="localhost", port=8000)

    # Создаем клиент-пользователь для получения уведомлений
    user_client = create_sse_client(host="localhost", port=8000)

    @user_client.on_event("notification")
    async def handle_notification(event_data):
        notification = event_data.get("data", {})
        title = notification.get("title", "")
        content = notification.get("content", "")
        notif_type = notification.get("type", "info")
        print(f"[УВЕДОМЛЕНИЕ {notif_type.upper()}] {title}: {content}")

    try:
        # Подключаем клиентов
        admin_connected = await admin_client.connect()
        user_connected = await user_client.connect()

        if not (admin_connected and user_connected):
            print("Не удалось подключить клиентов")
            return

        print("Система уведомлений готова!")

        # Отправляем разные типы уведомлений
        await asyncio.sleep(1)
        await admin_client.send_notification(
            title="Добро пожаловать!",
            content="Добро пожаловать в нашу систему уведомлений",
            notification_type="success",
        )

        await asyncio.sleep(2)
        await admin_client.send_notification(
            title="Важная информация", content="Система будет недоступна с 22:00 до 23:00", notification_type="warning"
        )

        await asyncio.sleep(2)
        await admin_client.send_notification(
            title="Обновление", content="Доступна новая версия приложения", notification_type="info"
        )

        # Ждем получения всех уведомлений
        await asyncio.sleep(5)

    except Exception as e:
        print(f"Ошибка в системе уведомлений: {e}")
    finally:
        await admin_client.disconnect()
        await user_client.disconnect()
        print("Система уведомлений остановлена")


async def connection_monitoring_example():
    """Пример мониторинга соединений."""
    print("\n=== Connection Monitoring Example ===")

    client = create_ws_client(host="localhost", port=8000)

    @client.on_message("connected")
    async def handle_connected(data):
        print("✅ Соединение установлено")
        print(f"   Connection ID: {client.connection_id}")
        print(f"   Статус: {client.get_status()}")

    @client.on_message("disconnected")
    async def handle_disconnected(data):
        print("❌ Соединение разорвано")

    @client.on_message("error")
    async def handle_error(data):
        print(f"🚫 Ошибка: {data}")

    try:
        # Включаем автоматическое переподключение
        client.auto_reconnect = True
        client.max_reconnect_attempts = 5

        connected = await client.connect()
        if connected:
            print("Мониторинг соединения запущен...")

            # Проверяем статус каждые 3 секунды
            for i in range(10):
                await asyncio.sleep(3)
                status = client.get_status()
                print(f"Статус соединения: {status['status']}")
                print(f"Последний ping: {status['last_ping']}")
                print(f"Попытки переподключения: {status['reconnect_attempts']}")
                print("---")

    except KeyboardInterrupt:
        print("\nМониторинг прерван пользователем")
    except Exception as e:
        print(f"Ошибка мониторинга: {e}")
    finally:
        await client.disconnect()


async def main():
    """Главная функция для запуска всех примеров."""
    print("🚀 Запуск примеров WebSocket и SSE клиентов")
    print("Убедитесь, что сервер запущен на localhost:8000")
    print("=" * 50)

    try:
        # Запускаем примеры по очереди
        await websocket_basic_example()
        await websocket_authenticated_example()
        await sse_basic_example()
        await chat_room_example()
        await notification_system_example()
        await connection_monitoring_example()

    except KeyboardInterrupt:
        print("\n⏹️  Примеры прерваны пользователем")
    except Exception as e:
        print(f"❌ Ошибка в примерах: {e}")

    print("\n✅ Все примеры завершены!")


if __name__ == "__main__":
    # Запускаем примеры
    asyncio.run(main())
