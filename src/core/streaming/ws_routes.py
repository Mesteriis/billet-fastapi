"""WebSocket роутеры."""

import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from core.config import get_settings

from .auth import WSAuthenticator, WSAuthError, get_ws_auth
from .connection_manager import connection_manager
from .ws_models import (
    BroadcastMessage,
    ChannelMessage,
    MessageType,
    NotificationMessage,
    WSCommand,
    WSMessage,
    WSResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["WebSocket"])
settings = get_settings()


@router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(None, description="JWT токен для авторизации"),
    api_key: str | None = Query(None, description="API ключ для авторизации"),
    user_id: str | None = Query(None, description="ID пользователя"),
    channels: str | None = Query(None, description="Каналы для подписки через запятую"),
    auth: WSAuthenticator = Depends(get_ws_auth),
):
    """WebSocket соединение."""
    if not settings.WEBSOCKET_ENABLED:
        await websocket.close(code=1013, reason="WebSocket отключен")
        return

    connection_id = str(uuid.uuid4())

    try:
        # Аутентификация
        user_data = await auth.authenticate_websocket(token=token, api_key=api_key)

        # Подключение
        connection_info = await connection_manager.connect_websocket(websocket, connection_id, user_data)

        # Подписка на каналы
        if channels:
            channel_list = [ch.strip() for ch in channels.split(",") if ch.strip()]
            for channel in channel_list:
                await connection_manager.subscribe_to_channel(connection_id, channel)

        # Отправляем приветственное сообщение
        welcome_message = WSMessage(
            id=str(uuid.uuid4()),
            type=MessageType.SYSTEM,
            content={
                "message": "Подключение установлено",
                "connection_id": connection_id,
                "authenticated": user_data["authenticated"],
                "server_time": connection_info.connected_at.isoformat(),
            },
        )
        await connection_manager.send_to_websocket(connection_id, welcome_message)

        # Основной цикл обработки сообщений
        while True:
            try:
                data = await websocket.receive_text()
                await handle_websocket_message(connection_id, data, user_data)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message from {connection_id}: {e}")
                error_message = WSMessage(
                    id=str(uuid.uuid4()),
                    type=MessageType.ERROR,
                    content={"error": "Ошибка обработки сообщения", "details": str(e)},
                )
                await connection_manager.send_to_websocket(connection_id, error_message)

    except WSAuthError as e:
        await websocket.close(code=4001, reason=str(e))
        return
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        await websocket.close(code=1011, reason="Внутренняя ошибка сервера")
        return
    finally:
        await connection_manager.disconnect_websocket(connection_id)


async def handle_websocket_message(connection_id: str, data: str, user_data: dict[str, Any]):
    """Обработка сообщения от WebSocket клиента."""
    try:
        # Парсим JSON
        try:
            message_data = json.loads(data)
        except json.JSONDecodeError:
            # Если не JSON, обрабатываем как текст
            message_data = {"action": "message", "data": {"content": data}}

        # Создаем команду
        command = WSCommand(**message_data)

        # Обрабатываем команду
        response = await process_websocket_command(connection_id, command, user_data)

        # Отправляем ответ если есть request_id
        if command.request_id and response:
            response_message = WSMessage(id=str(uuid.uuid4()), type=MessageType.JSON, content=response.dict())
            await connection_manager.send_to_websocket(connection_id, response_message)

    except Exception as e:
        logger.error(f"Error handling message from {connection_id}: {e}")


async def process_websocket_command(
    connection_id: str, command: WSCommand, user_data: dict[str, Any]
) -> WSResponse | None:
    """Обработка команды WebSocket."""
    action = command.action.lower()

    try:
        if action == "ping":
            return WSResponse(
                request_id=command.request_id or str(uuid.uuid4()), success=True, data={"message": "pong"}
            )

        elif action == "subscribe":
            channel = command.data.get("channel")
            if not channel:
                raise ValueError("Не указан канал для подписки")

            await connection_manager.subscribe_to_channel(connection_id, channel)
            return WSResponse(
                request_id=command.request_id or str(uuid.uuid4()),
                success=True,
                data={"message": f"Подписка на канал {channel} оформлена"},
            )

        elif action == "message":
            # Простое текстовое сообщение
            content = command.data.get("content", "")

            # Эхо сообщение
            echo_message = WSMessage(
                id=str(uuid.uuid4()), type=MessageType.TEXT, content=f"Эхо: {content}", sender_id="server"
            )
            await connection_manager.send_to_websocket(connection_id, echo_message)

            return WSResponse(
                request_id=command.request_id or str(uuid.uuid4()),
                success=True,
                data={"message": "Сообщение обработано"},
            )

        else:
            raise ValueError(f"Неизвестная команда: {action}")

    except Exception as e:
        logger.error(f"Error processing command {action}: {e}")
        return WSResponse(request_id=command.request_id or str(uuid.uuid4()), success=False, error=str(e))


@router.get("/stats")
async def get_stats():
    """Получение статистики соединений."""
    return connection_manager.get_connections_stats()


# HTTP эндпоинты для управления WebSocket соединениями


@router.post("/broadcast", summary="Рассылка сообщения всем соединениям")
async def broadcast_message(
    message: BroadcastMessage,
    auth_data: dict[str, Any] = Depends(lambda: {"authenticated": True}),  # Можно заменить на require_auth
):
    """Рассылка сообщения всем WebSocket соединениям."""
    if not settings.WEBSOCKET_ENABLED:
        raise HTTPException(status_code=503, detail="WebSocket отключен")

    await connection_manager.broadcast_to_all(message.message, exclude_connections=message.exclude_connections)

    return {"success": True, "message": "Сообщение разослано"}


@router.post("/send-to-channel", summary="Отправка сообщения в канал")
async def send_to_channel(
    channel_message: ChannelMessage, auth_data: dict[str, Any] = Depends(lambda: {"authenticated": True})
):
    """Отправка сообщения в канал."""
    if not settings.WEBSOCKET_ENABLED:
        raise HTTPException(status_code=503, detail="WebSocket отключен")

    await connection_manager.broadcast_to_channel(
        channel_message.channel, channel_message.message, persist=channel_message.persist
    )

    return {"success": True, "message": f"Сообщение отправлено в канал {channel_message.channel}"}


@router.post("/send-to-user/{user_id}", summary="Отправка сообщения пользователю")
async def send_to_user(
    user_id: str, message: WSMessage, auth_data: dict[str, Any] = Depends(lambda: {"authenticated": True})
):
    """Отправка сообщения конкретному пользователю."""
    if not settings.WEBSOCKET_ENABLED:
        raise HTTPException(status_code=503, detail="WebSocket отключен")

    sent_count = await connection_manager.send_to_user(user_id, message)

    return {"success": True, "message": f"Сообщение отправлено пользователю {user_id}", "sent_count": sent_count}


@router.post("/notification", summary="Отправка уведомления")
async def send_notification(
    notification: NotificationMessage,
    channel: str | None = None,
    user_id: str | None = None,
    auth_data: dict[str, Any] = Depends(lambda: {"authenticated": True}),
):
    """Отправка уведомления в канал или пользователю."""
    if not settings.WEBSOCKET_ENABLED:
        raise HTTPException(status_code=503, detail="WebSocket отключен")

    message = WSMessage(id=str(uuid.uuid4()), type=MessageType.NOTIFICATION, content=notification.dict())

    if user_id:
        sent_count = await connection_manager.send_to_user(user_id, message)
        return {"success": True, "message": f"Уведомление отправлено пользователю {user_id}", "sent_count": sent_count}
    elif channel:
        await connection_manager.broadcast_to_channel(channel, message)
        return {"success": True, "message": f"Уведомление отправлено в канал {channel}"}
    else:
        await connection_manager.broadcast_to_all(message)
        return {"success": True, "message": "Уведомление разослано всем"}


@router.get("/connections", summary="Список активных соединений")
async def get_active_connections(auth_data: dict[str, Any] = Depends(lambda: {"authenticated": True})):
    """Получение списка активных соединений."""
    if not settings.WEBSOCKET_ENABLED:
        raise HTTPException(status_code=503, detail="WebSocket отключен")

    return {
        "websocket_connections": list(connection_manager.ws_connections.keys()),
        "sse_connections": list(connection_manager.sse_connections.keys()),
        "total": len(connection_manager.ws_connections) + len(connection_manager.sse_connections),
    }


@router.delete("/connections/{connection_id}", summary="Закрытие соединения")
async def close_connection(connection_id: str, auth_data: dict[str, Any] = Depends(lambda: {"authenticated": True})):
    """Принудительное закрытие соединения."""
    if not settings.WEBSOCKET_ENABLED:
        raise HTTPException(status_code=503, detail="WebSocket отключен")

    # Закрываем WebSocket соединение
    if connection_id in connection_manager.ws_connections:
        await connection_manager.disconnect_websocket(connection_id)
        return {"success": True, "message": f"WebSocket соединение {connection_id} закрыто"}

    # Закрываем SSE соединение
    if connection_id in connection_manager.sse_connections:
        await connection_manager.disconnect_sse(connection_id)
        return {"success": True, "message": f"SSE соединение {connection_id} закрыто"}

    raise HTTPException(status_code=404, detail="Соединение не найдено")


@router.get("/test-page", response_class=HTMLResponse, summary="Тестовая страница WebSocket")
async def websocket_test_page():
    """Простая тестовая страница для WebSocket."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            #messages { border: 1px solid #ccc; height: 300px; overflow-y: scroll; padding: 10px; margin: 10px 0; }
            input, button { margin: 5px; padding: 5px; }
        </style>
    </head>
    <body>
        <h1>WebSocket Test Page</h1>
        <div>
            <button onclick="connect()">Подключиться</button>
            <button onclick="disconnect()">Отключиться</button>
            <span id="status">Отключено</span>
        </div>
        <div>
            <input type="text" id="messageInput" placeholder="Введите сообщение..." />
            <button onclick="sendMessage()">Отправить</button>
        </div>
        <div>
            <input type="text" id="channelInput" placeholder="Канал..." />
            <button onclick="subscribe()">Подписаться</button>
            <button onclick="unsubscribe()">Отписаться</button>
        </div>
        <div id="messages"></div>

        <script>
            let ws = null;
            const messagesDiv = document.getElementById('messages');
            const statusSpan = document.getElementById('status');

            function connect() {
                ws = new WebSocket('ws://localhost:8000/ws/connect');

                ws.onopen = function(event) {
                    statusSpan.textContent = 'Подключено';
                    addMessage('Подключение установлено');
                };

                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    addMessage('Получено: ' + JSON.stringify(data, null, 2));
                };

                ws.onclose = function(event) {
                    statusSpan.textContent = 'Отключено';
                    addMessage('Соединение закрыто');
                };

                ws.onerror = function(error) {
                    addMessage('Ошибка: ' + error);
                };
            }

            function disconnect() {
                if (ws) {
                    ws.close();
                }
            }

            function sendMessage() {
                const input = document.getElementById('messageInput');
                if (ws && input.value) {
                    const message = {
                        action: 'message',
                        data: { content: input.value },
                        request_id: 'test_' + Date.now()
                    };
                    ws.send(JSON.stringify(message));
                    input.value = '';
                }
            }

            function subscribe() {
                const input = document.getElementById('channelInput');
                if (ws && input.value) {
                    const message = {
                        action: 'subscribe',
                        data: { channel: input.value },
                        request_id: 'sub_' + Date.now()
                    };
                    ws.send(JSON.stringify(message));
                }
            }

            function unsubscribe() {
                const input = document.getElementById('channelInput');
                if (ws && input.value) {
                    const message = {
                        action: 'unsubscribe',
                        data: { channel: input.value },
                        request_id: 'unsub_' + Date.now()
                    };
                    ws.send(JSON.stringify(message));
                }
            }

            function addMessage(message) {
                const div = document.createElement('div');
                div.textContent = new Date().toLocaleTimeString() + ': ' + message;
                messagesDiv.appendChild(div);
                messagesDiv.scrollTop = messagesDiv.scrollHeight;
            }
        </script>
    </body>
    </html>
    """
    return html_content
