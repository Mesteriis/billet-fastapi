#!/usr/bin/env python3
"""
Примеры использования realtime системы (WebSocket + SSE + WebRTC).

Этот файл содержит практические примеры работы с системой реального времени:
- WebSocket соединения и обмен сообщениями
- Server-Sent Events для потоковых данных
- WebRTC сигналинг для P2P связи
- Передача бинарных данных
- Система каналов и комнат
"""

import asyncio
import json
import logging

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

# Импорты realtime системы
from core.realtime import (
    BinaryMessage,
    WebRTCSignalType,
    WSClient,
    connection_manager,
    create_sse_client,
    create_ws_client,
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def websocket_basic_example():
    """Базовый пример работы с WebSocket."""
    print("🔌 Базовый пример WebSocket")

    # Создание клиента
    client = WSClient("ws://localhost:8000/realtime/ws")

    # Обработчики событий
    @client.on_message("text")
    async def handle_text_message(data):
        print(f"📝 Получено текстовое сообщение: {data}")

    @client.on_message("system")
    async def handle_system_message(data):
        print(f"⚙️ Системное сообщение: {data}")

    @client.on_message("heartbeat")
    async def handle_heartbeat(data):
        print(f"💓 Heartbeat: {data}")

    try:
        # Подключение
        await client.connect()
        print("✅ WebSocket подключен")

        # Отправка сообщений
        await client.send_text("Привет, WebSocket!")
        await client.send_json({"type": "greeting", "message": "Hello from client"})

        # Отправка команды
        await client.send_command("join_channel", {"channel": "general"})

        # Ping для проверки соединения
        await client.ping()

        # Ожидание ответов (в реальном приложении здесь был бы event loop)
        await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Ошибка WebSocket: {e}")
    finally:
        await client.disconnect()
        print("🔌 WebSocket отключен")


async def websocket_authenticated_example():
    """Пример аутентифицированного WebSocket соединения."""
    print("\n🔐 Пример аутентифицированного WebSocket")

    # Создание аутентифицированного клиента
    client = create_ws_client(
        url="ws://localhost:8000/realtime/ws",
        token="your-jwt-token-here",  # В реальном приложении получить из auth
    )

    @client.on_message("connected")
    async def handle_connected(data):
        print(f"🔗 Аутентифицированное соединение установлено: {data}")

    @client.on_message("error")
    async def handle_error(data):
        print(f"❌ Ошибка аутентификации: {data}")

    try:
        await client.connect()

        # Отправка персонального сообщения
        await client.send_json({"type": "private_message", "recipient_id": 123, "message": "Приватное сообщение"})

        await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Ошибка аутентифицированного WebSocket: {e}")
    finally:
        await client.disconnect()


async def sse_basic_example():
    """Базовый пример работы с SSE."""
    print("\n📡 Базовый пример SSE")

    # Создание SSE клиента
    client = create_sse_client("http://localhost:8000/realtime/events")

    @client.on_event("connected")
    async def handle_connected(event_data):
        print(f"📡 SSE подключен: {event_data}")

    @client.on_event("message")
    async def handle_message(event_data):
        print(f"📨 SSE сообщение: {event_data}")

    @client.on_event("notification")
    async def handle_notification(event_data):
        print(f"🔔 SSE уведомление: {event_data}")

    @client.on_event("heartbeat")
    async def handle_heartbeat(event_data):
        print(f"💓 SSE heartbeat: {event_data}")

    try:
        await client.connect()
        print("✅ SSE подключен")

        # Отправка данных через SSE
        await client.send_to_user(123, {"message": "Hello via SSE"})
        await client.send_to_channel("general", {"announcement": "Server update"})
        await client.broadcast({"global": "Global message"})

        # Ожидание событий
        await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"Ошибка SSE: {e}")
    finally:
        await client.disconnect()
        print("📡 SSE отключен")


async def chat_room_example():
    """Пример чат-комнаты с WebSocket."""
    print("\n💬 Пример чат-комнаты")

    # Создаем двух клиентов для имитации чата
    client1 = WSClient("ws://localhost:8000/realtime/ws")
    client2 = WSClient("ws://localhost:8000/realtime/ws")

    @client1.on_message("text")
    async def client1_handle_message(data):
        print(f"👤 Клиент 1 получил: {data}")

    @client1.on_message("user_joined")
    async def client1_user_joined(data):
        print(f"👋 Клиент 1: пользователь присоединился - {data}")

    @client2.on_message("text")
    async def client2_handle_message(data):
        print(f"👥 Клиент 2 получил: {data}")

    try:
        # Подключение клиентов
        await client1.connect()
        await client2.connect()

        # Присоединение к каналу
        await client1.send_command("join_channel", {"channel": "chat_room_1"})
        await client2.send_command("join_channel", {"channel": "chat_room_1"})

        # Обмен сообщениями
        await client1.send_json(
            {
                "type": "chat_message",
                "channel": "chat_room_1",
                "message": "Привет всем в комнате!",
                "username": "Пользователь1",
            }
        )

        await asyncio.sleep(0.5)

        await client2.send_json(
            {
                "type": "chat_message",
                "channel": "chat_room_1",
                "message": "Привет! Как дела?",
                "username": "Пользователь2",
            }
        )

        await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Ошибка чат-комнаты: {e}")
    finally:
        await client1.disconnect()
        await client2.disconnect()
        print("💬 Чат-комната закрыта")


async def binary_data_example():
    """Пример передачи бинарных данных."""
    print("\n📁 Пример передачи бинарных данных")

    client = WSClient("ws://localhost:8000/realtime/ws")

    @client.on_message("binary")
    async def handle_binary(data):
        print(f"📦 Получены бинарные данные: {len(data)} байт")

    @client.on_message("file_received")
    async def handle_file_received(data):
        print(f"📄 Файл получен: {data}")

    try:
        await client.connect()

        # Создание тестового файла в памяти
        test_file_content = b"This is a test file content with some binary data \x00\x01\x02"

        # Создание BinaryMessage
        binary_msg = BinaryMessage.from_bytes(
            data=test_file_content, content_type="application/octet-stream", filename="test_file.bin"
        )

        # Отправка бинарных данных
        await client.send_binary(binary_msg)
        print(f"📤 Отправлен файл: {binary_msg.filename} ({len(test_file_content)} байт)")

        # Отправка изображения (имитация)
        image_data = b"\x89PNG\r\n\x1a\n" + b"fake_png_data" * 100
        image_msg = BinaryMessage.from_bytes(data=image_data, content_type="image/png", filename="test_image.png")

        await client.send_binary(image_msg)
        print(f"📤 Отправлено изображение: {image_msg.filename}")

        await asyncio.sleep(1)

    except Exception as e:
        logger.error(f"Ошибка передачи бинарных данных: {e}")
    finally:
        await client.disconnect()


async def notification_system_example():
    """Пример системы уведомлений через SSE."""
    print("\n🔔 Пример системы уведомлений")

    # Клиент для получения уведомлений
    user_client = create_sse_client("http://localhost:8000/realtime/events")

    @user_client.on_event("notification")
    async def handle_notification(event_data):
        notification = json.loads(event_data) if isinstance(event_data, str) else event_data
        print(f"🔔 Уведомление: {notification.get('title', 'Без заголовка')}")
        print(f"   Сообщение: {notification.get('message', 'Без сообщения')}")
        print(f"   Тип: {notification.get('type', 'info')}")

    @user_client.on_event("system_alert")
    async def handle_system_alert(event_data):
        alert = json.loads(event_data) if isinstance(event_data, str) else event_data
        print(f"🚨 СИСТЕМНОЕ ОПОВЕЩЕНИЕ: {alert.get('message')}")

    try:
        await user_client.connect()

        # Имитация отправки уведомлений
        notifications = [
            {"title": "Новое сообщение", "message": "У вас новое сообщение от пользователя", "type": "info"},
            {"title": "Платеж обработан", "message": "Ваш платеж успешно обработан", "type": "success"},
            {"title": "Предупреждение", "message": "Срок действия подписки истекает через 3 дня", "type": "warning"},
        ]

        for notification in notifications:
            await user_client.send_to_user(123, notification)
            await asyncio.sleep(0.5)

        # Системное оповещение
        await user_client.broadcast({"message": "Плановое обслуживание сервера через 30 минут", "severity": "warning"})

        await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"Ошибка системы уведомлений: {e}")
    finally:
        await user_client.disconnect()


async def webrtc_signaling_example():
    """Пример WebRTC сигналинга."""
    print("\n🎥 Пример WebRTC сигналинга")

    # Два клиента для P2P соединения
    peer1 = WSClient("ws://localhost:8000/realtime/webrtc/signaling")
    peer2 = WSClient("ws://localhost:8000/realtime/webrtc/signaling")

    @peer1.on_message("webrtc_signal")
    async def peer1_handle_signal(data):
        print(f"🎯 Peer1 получил сигнал: {data.get('signal_type')}")

    @peer2.on_message("webrtc_signal")
    async def peer2_handle_signal(data):
        print(f"🎯 Peer2 получил сигнал: {data.get('signal_type')}")

    try:
        await peer1.connect()
        await peer2.connect()

        # Создание комнаты
        await peer1.send_json({"type": "create_room", "room_id": "video_call_123"})

        # Присоединение к комнате
        await peer2.send_json({"type": "join_room", "room_id": "video_call_123"})

        # WebRTC Offer от peer1
        offer_sdp = "v=0\r\no=- 123456789 2 IN IP4 127.0.0.1\r\n..."  # Упрощенный SDP
        await peer1.send_webrtc_signal(signal_type=WebRTCSignalType.OFFER, target_peer_id="peer2", sdp=offer_sdp)

        await asyncio.sleep(0.5)

        # WebRTC Answer от peer2
        answer_sdp = "v=0\r\no=- 987654321 2 IN IP4 127.0.0.1\r\n..."  # Упрощенный SDP
        await peer2.send_webrtc_signal(signal_type=WebRTCSignalType.ANSWER, target_peer_id="peer1", sdp=answer_sdp)

        # ICE кандидаты
        ice_candidate = {
            "candidate": "candidate:1 1 UDP 2130706431 192.168.1.100 54400 typ host",
            "sdpMid": "0",
            "sdpMLineIndex": 0,
        }

        await peer1.send_webrtc_signal(
            signal_type=WebRTCSignalType.ICE_CANDIDATE, target_peer_id="peer2", ice_candidate=ice_candidate
        )

        await asyncio.sleep(1)
        print("🎥 WebRTC сигналинг завершен")

    except Exception as e:
        logger.error(f"Ошибка WebRTC сигналинга: {e}")
    finally:
        await peer1.disconnect()
        await peer2.disconnect()


async def connection_monitoring_example():
    """Пример мониторинга соединений."""
    print("\n📊 Пример мониторинга соединений")

    client = WSClient("ws://localhost:8000/realtime/ws")

    @client.on_message("connected")
    async def handle_connected(data):
        print(f"🔗 Соединение установлено: {data}")

    @client.on_message("disconnected")
    async def handle_disconnected(data):
        print(f"🔌 Соединение разорвано: {data}")

    @client.on_message("error")
    async def handle_error(data):
        print(f"❌ Ошибка соединения: {data}")

    @client.on_message("stats")
    async def handle_stats(data):
        print(f"📈 Статистика соединения: {data}")

    try:
        await client.connect()

        # Запрос статистики соединений
        await client.send_command("get_connection_stats", {})

        # Запрос информации о комнатах
        await client.send_command("get_rooms", {})

        # Запрос активных пользователей
        await client.send_command("get_active_users", {})

        await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"Ошибка мониторинга: {e}")
    finally:
        await client.disconnect()


def create_fastapi_realtime_app():
    """Создание FastAPI приложения с realtime endpoints."""
    print("\n🌐 Создание FastAPI приложения с Realtime")

    app = FastAPI(title="Realtime Example API")

    @app.websocket("/ws/chat")
    async def websocket_chat(websocket: WebSocket):
        """WebSocket endpoint для чата."""
        connection_id = f"chat_{id(websocket)}"
        user_id = 123  # В реальном приложении получить из токена

        await connection_manager.connect_websocket(websocket, connection_id, user_id)

        try:
            while True:
                data = await websocket.receive_text()
                message_data = json.loads(data)

                # Отправка сообщения в канал
                if message_data.get("type") == "chat_message":
                    await connection_manager.send_to_channel(
                        message_data.get("channel", "general"),
                        {
                            "type": "chat_message",
                            "message": message_data.get("message"),
                            "username": message_data.get("username", "Anonymous"),
                            "timestamp": asyncio.get_event_loop().time(),
                        },
                    )

        except WebSocketDisconnect:
            await connection_manager.disconnect_websocket(connection_id)

    @app.get("/sse/notifications")
    async def sse_notifications():
        """SSE endpoint для уведомлений."""

        async def event_generator():
            # Имитация потока уведомлений
            notifications = [
                {"type": "welcome", "message": "Добро пожаловать!"},
                {"type": "info", "message": "Новые функции доступны"},
                {"type": "warning", "message": "Обновление через 5 минут"},
            ]

            for notification in notifications:
                yield f"data: {json.dumps(notification)}\n\n"
                await asyncio.sleep(1)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    @app.get("/stats")
    async def get_connection_stats():
        """Получение статистики соединений."""
        stats = await connection_manager.get_connection_stats()
        return {
            "websocket_connections": stats.get("websocket_count", 0),
            "sse_connections": stats.get("sse_count", 0),
            "total_users": stats.get("unique_users", 0),
            "active_channels": stats.get("active_channels", []),
        }

    print("✅ FastAPI приложение создано с realtime endpoints:")
    print("   WS  /ws/chat")
    print("   GET /sse/notifications")
    print("   GET /stats")

    return app


async def main():
    """Главная функция с запуском всех примеров."""
    print("🎯 Примеры использования Realtime системы")
    print("=" * 50)

    try:
        # Базовые примеры (закомментированы, так как требуют запущенного сервера)
        print("💡 Для запуска примеров необходим запущенный FastAPI сервер:")
        print("   uvicorn src.main:app --reload")
        print("\n🔧 Затем раскомментируйте нужные примеры и запустите снова")

        # await websocket_basic_example()
        # await websocket_authenticated_example()
        # await sse_basic_example()
        # await chat_room_example()
        # await binary_data_example()
        # await notification_system_example()
        # await webrtc_signaling_example()
        # await connection_monitoring_example()

        # Создание FastAPI приложения
        app = create_fastapi_realtime_app()

        print("\n🎉 Примеры подготовлены!")
        print("\n🚀 Для тестирования:")
        print("   1. Запустите основное приложение: uvicorn src.main:app --reload")
        print("   2. Раскомментируйте нужные примеры в main()")
        print("   3. Запустите этот скрипт снова")
        print("\n🌐 Или запустите FastAPI приложение из примеров:")
        print("   uvicorn examples.realtime_examples:app --reload --port 8001")

    except Exception as e:
        logger.error(f"Ошибка выполнения примеров: {e}")
        raise


if __name__ == "__main__":
    # Запуск примеров
    asyncio.run(main())
