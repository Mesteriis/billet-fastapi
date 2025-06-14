"""Server-Sent Events роутеры."""

import asyncio
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from core.config import get_settings

from .auth import WSAuthenticator, WSAuthError, get_ws_auth, optional_auth
from .connection_manager import connection_manager
from .ws_models import MessageType, NotificationMessage, SSEMessage, WSMessage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sse", tags=["Server-Sent Events"])
settings = get_settings()


@router.get("/connect")
async def sse_endpoint(
    request: Request,
    token: str | None = Query(None, description="JWT токен для авторизации"),
    api_key: str | None = Query(None, description="API ключ для авторизации"),
    channels: str | None = Query(None, description="Каналы для подписки через запятую"),
    last_event_id: str | None = Query(None, description="ID последнего события"),
    auth: WSAuthenticator = Depends(get_ws_auth),
):
    """SSE соединение."""
    if not settings.SSE_ENABLED:
        raise HTTPException(status_code=503, detail="SSE отключен")

    connection_id = str(uuid.uuid4())

    try:
        # Аутентификация
        user_data = await auth.authenticate_sse(token=token, api_key=api_key)

        # Создаем соединение
        message_queue = await connection_manager.connect_sse(connection_id, user_data)

        # Подписка на каналы
        if channels:
            channel_list = [ch.strip() for ch in channels.split(",") if ch.strip()]
            for channel in channel_list:
                await connection_manager.subscribe_to_channel(connection_id, channel)

        # Отправляем приветственное сообщение
        welcome_message = SSEMessage(
            id=str(uuid.uuid4()),
            event="connected",
            data={
                "message": "SSE соединение установлено",
                "connection_id": connection_id,
                "authenticated": user_data["authenticated"],
                "retry": settings.SSE_RETRY_TIMEOUT,
            },
            retry=settings.SSE_RETRY_TIMEOUT,
        )
        await connection_manager.send_to_sse(connection_id, welcome_message)

        # Создаем генератор событий
        async def event_generator():
            try:
                while True:
                    try:
                        # Ждем сообщение с таймаутом
                        message = await asyncio.wait_for(message_queue.get(), timeout=settings.SSE_HEARTBEAT_INTERVAL)

                        # Отправляем сообщение в SSE формате
                        yield f"{message.to_sse_format()}\n"

                    except TimeoutError:
                        # Отправляем heartbeat если нет сообщений
                        heartbeat = SSEMessage(
                            id=str(uuid.uuid4()),
                            event="heartbeat",
                            data={
                                "timestamp": connection_manager.get_connection_info(
                                    connection_id
                                ).last_activity.isoformat()
                            },
                            retry=settings.SSE_RETRY_TIMEOUT,
                        )
                        yield f"{heartbeat.to_sse_format()}\n"

            except Exception as e:
                logger.error(f"SSE generator error for {connection_id}: {e}")
                error_message = SSEMessage(
                    id=str(uuid.uuid4()), event="error", data={"error": "Ошибка потока", "details": str(e)}
                )
                yield f"{error_message.to_sse_format()}\n"
            finally:
                await connection_manager.disconnect_sse(connection_id)

        # Возвращаем потоковый ответ
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
                "X-Connection-ID": connection_id,
            },
        )

    except WSAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error(f"SSE connection error: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/send-to-channel")
async def send_sse_to_channel(
    channel: str,
    event: str,
    data: dict[str, Any],
    event_id: str | None = None,
    retry: int | None = None,
    user_data: dict[str, Any] = Depends(optional_auth),
):
    """Отправка SSE сообщения в канал."""
    if not settings.SSE_ENABLED:
        raise HTTPException(status_code=503, detail="SSE отключен")

    # Создаем SSE сообщение
    sse_message = SSEMessage(
        id=event_id or str(uuid.uuid4()), event=event, data=data, retry=retry or settings.SSE_RETRY_TIMEOUT
    )

    # Отправляем в канал через connection manager
    ws_message = WSMessage(id=sse_message.id, type=MessageType.JSON, content=data, channel=channel)

    await connection_manager.broadcast_to_channel(channel, ws_message)

    return {"success": True, "message": f"SSE событие отправлено в канал {channel}"}


@router.post("/send-to-user/{user_id}")
async def send_sse_to_user(
    user_id: str,
    event: str,
    data: dict[str, Any],
    event_id: str | None = None,
    retry: int | None = None,
    user_data: dict[str, Any] = Depends(optional_auth),
):
    """Отправка SSE сообщения пользователю."""
    if not settings.SSE_ENABLED:
        raise HTTPException(status_code=503, detail="SSE отключен")

    # Создаем сообщение
    ws_message = WSMessage(id=event_id or str(uuid.uuid4()), type=MessageType.JSON, content=data, recipient_id=user_id)

    sent_count = await connection_manager.send_to_user(user_id, ws_message)

    return {"success": True, "message": f"SSE событие отправлено пользователю {user_id}", "sent_count": sent_count}


@router.post("/broadcast")
async def broadcast_sse(
    event: str,
    data: dict[str, Any],
    event_id: str | None = None,
    retry: int | None = None,
    exclude_connections: list | None = None,
    user_data: dict[str, Any] = Depends(optional_auth),
):
    """Рассылка SSE события всем соединениям."""
    if not settings.SSE_ENABLED:
        raise HTTPException(status_code=503, detail="SSE отключен")

    # Создаем сообщение
    ws_message = WSMessage(id=event_id or str(uuid.uuid4()), type=MessageType.BROADCAST, content=data)

    await connection_manager.broadcast_to_all(ws_message, exclude_connections=exclude_connections or [])

    return {"success": True, "message": "SSE событие разослано всем"}


@router.post("/notification")
async def send_sse_notification(
    notification: NotificationMessage,
    channel: str | None = None,
    user_id: str | None = None,
    user_data: dict[str, Any] = Depends(optional_auth),
):
    """Отправка уведомления через SSE."""
    if not settings.SSE_ENABLED:
        raise HTTPException(status_code=503, detail="SSE отключен")

    # Создаем сообщение уведомления
    ws_message = WSMessage(id=str(uuid.uuid4()), type=MessageType.NOTIFICATION, content=notification.dict())

    if user_id:
        sent_count = await connection_manager.send_to_user(user_id, ws_message)
        return {"success": True, "message": f"Уведомление отправлено пользователю {user_id}", "sent_count": sent_count}
    elif channel:
        await connection_manager.broadcast_to_channel(channel, ws_message)
        return {"success": True, "message": f"Уведомление отправлено в канал {channel}"}
    else:
        await connection_manager.broadcast_to_all(ws_message)
        return {"success": True, "message": "Уведомление разослано всем"}


@router.get("/stats")
async def get_sse_stats(user_data: dict[str, Any] = Depends(optional_auth)):
    """Получение статистики SSE соединений."""
    if not settings.SSE_ENABLED:
        raise HTTPException(status_code=503, detail="SSE отключен")

    stats = connection_manager.get_connections_stats()
    return {"sse": stats["sse"], "channels": stats["channels"]}


@router.delete("/connections/{connection_id}")
async def close_sse_connection(connection_id: str, user_data: dict[str, Any] = Depends(optional_auth)):
    """Закрытие SSE соединения."""
    if not settings.SSE_ENABLED:
        raise HTTPException(status_code=503, detail="SSE отключен")

    if connection_id in connection_manager.sse_connections:
        await connection_manager.disconnect_sse(connection_id)
        return {"success": True, "message": f"SSE соединение {connection_id} закрыто"}
    else:
        raise HTTPException(status_code=404, detail="SSE соединение не найдено")


@router.get("/test")
async def sse_test_page():
    """Простая тестовая страница для SSE."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SSE Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            #events { border: 1px solid #ccc; height: 400px; overflow-y: scroll; padding: 10px; margin: 10px 0; }
            button { margin: 5px; padding: 5px; }
            .event { margin: 5px 0; padding: 5px; border-left: 3px solid #007bff; background: #f8f9fa; }
        </style>
    </head>
    <body>
        <h1>Server-Sent Events Test</h1>
        <div>
            <button onclick="connect()">Подключиться</button>
            <button onclick="disconnect()">Отключиться</button>
            <span id="status">Отключено</span>
        </div>
        <div>
            <button onclick="sendTestNotification()">Тестовое уведомление</button>
            <button onclick="clearEvents()">Очистить</button>
        </div>
        <div id="events"></div>

        <script>
            let eventSource = null;
            const eventsDiv = document.getElementById('events');
            const statusSpan = document.getElementById('status');

            function connect() {
                eventSource = new EventSource('/sse/connect');

                eventSource.onopen = function(event) {
                    statusSpan.textContent = 'Подключено';
                    addEvent('connection', 'Подключение к SSE установлено', new Date());
                };

                eventSource.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    addEvent('message', JSON.stringify(data, null, 2), new Date());
                };

                eventSource.addEventListener('connected', function(event) {
                    const data = JSON.parse(event.data);
                    addEvent('connected', JSON.stringify(data, null, 2), new Date());
                });

                eventSource.addEventListener('notification', function(event) {
                    const data = JSON.parse(event.data);
                    addEvent('notification', JSON.stringify(data, null, 2), new Date());
                });

                eventSource.addEventListener('heartbeat', function(event) {
                    const data = JSON.parse(event.data);
                    addEvent('heartbeat', 'Heartbeat: ' + data.timestamp, new Date());
                });

                eventSource.onerror = function(event) {
                    statusSpan.textContent = 'Ошибка';
                    addEvent('error', 'Ошибка SSE соединения', new Date());
                };

                eventSource.addEventListener('error', function(event) {
                    const data = JSON.parse(event.data);
                    addEvent('error', JSON.stringify(data, null, 2), new Date());
                });
            }

            function disconnect() {
                if (eventSource) {
                    eventSource.close();
                    statusSpan.textContent = 'Отключено';
                    addEvent('connection', 'SSE соединение закрыто', new Date());
                }
            }

            function sendTestNotification() {
                fetch('/sse/notification', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        title: 'Тестовое уведомление',
                        content: 'Это тестовое уведомление от SSE API',
                        type: 'info'
                    })
                })
                .then(response => response.json())
                .then(data => {
                    addEvent('api', 'Уведомление отправлено: ' + data.message, new Date());
                })
                .catch(error => {
                    addEvent('error', 'Ошибка отправки: ' + error, new Date());
                });
            }

            function clearEvents() {
                eventsDiv.innerHTML = '';
            }

            function addEvent(type, message, timestamp) {
                const div = document.createElement('div');
                div.className = 'event';
                div.innerHTML = `
                    <strong>[${type}]</strong> ${timestamp.toLocaleTimeString()}<br>
                    <pre>${message}</pre>
                `;
                eventsDiv.appendChild(div);
                eventsDiv.scrollTop = eventsDiv.scrollHeight;
            }
        </script>
    </body>
    </html>
    """

    from fastapi.responses import HTMLResponse

    return HTMLResponse(content=html_content)
