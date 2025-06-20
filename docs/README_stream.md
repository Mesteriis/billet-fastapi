# 🔄 Realtime система - Краткое руководство

Быстрое руководство по использованию системы реального времени (WebSocket + SSE + WebRTC).

## 🚀 Быстрый старт

### WebSocket клиент

```python
from src.core.realtime import WSClient


async def websocket_example():
    client = WSClient("ws://localhost:8000/realtime/ws")

    @client.on_message("text")
    async def handle_message(data):
        print(f"Получено: {data}")

    await client.connect()
    await client.send_text("Привет!")
    await client.disconnect()
```

### SSE клиент

```python
from src.core.realtime import create_sse_client


async def sse_example():
    client = create_sse_client("http://localhost:8000/realtime/events")

    @client.on_event("notification")
    async def handle_notification(data):
        print(f"Уведомление: {data}")

    await client.connect()
```

## 📋 Основные возможности

### WebSocket

```python
# Отправка сообщений
await client.send_text("Текстовое сообщение")
await client.send_json({"type": "data", "value": 123})
await client.send_command("join_channel", {"channel": "general"})

# Отправка файлов
from src.core.realtime import BinaryMessage

binary_msg = BinaryMessage.from_bytes(file_data, "image/png", "photo.png")
await client.send_binary(binary_msg)
```

### SSE (Server-Sent Events)

```python
# Отправка событий
await client.send_to_user(user_id, {"message": "Персональное уведомление"})
await client.send_to_channel("general", {"announcement": "Объявление"})
await client.broadcast({"global": "Глобальное сообщение"})
```

### WebRTC сигналинг

```python
# WebRTC соединение
await client.send_webrtc_signal(
    signal_type="offer",
    target_peer_id="peer_123",
    sdp="v=0..."
)
```

## 🔗 Интеграция с FastAPI

### WebSocket endpoint

```python
from fastapi import WebSocket
from src.core.realtime import ConnectionManager

connection_manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await connection_manager.connect_websocket(websocket, "user_123", 123)

    try:
        while True:
            data = await websocket.receive_text()
            await connection_manager.broadcast({"message": data})
    except WebSocketDisconnect:
        await connection_manager.disconnect_websocket("user_123")
```

### SSE endpoint

```python
from fastapi.responses import StreamingResponse

@app.get("/events")
async def sse_endpoint():
    async def event_generator():
        while True:
            yield f"data: {json.dumps({'time': datetime.now().isoformat()})}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

## ⚙️ Настройка

```bash
# .env
WEBSOCKET_ENABLED=true
SSE_ENABLED=true
REALTIME_MAX_CONNECTIONS=1000
```

## 🎯 Основные endpoints

```bash
# WebSocket
WS   /realtime/ws                    # Основной WebSocket
WS   /realtime/webrtc/signaling     # WebRTC сигналинг

# SSE
GET  /realtime/events               # SSE поток событий
GET  /realtime/sse-test            # Тестовая страница

# HTTP API
POST /realtime/send                 # Отправка сообщения
POST /realtime/broadcast           # Широковещательная отправка
POST /realtime/binary/upload       # Загрузка файла
```

## 📊 Мониторинг

```python
# Статистика соединений
from src.core.realtime import connection_manager

stats = await connection_manager.get_connection_stats()
print(f"Активных соединений: {stats['websocket_count']}")
print(f"SSE соединений: {stats['sse_count']}")
```

## 🔐 Аутентификация

```python
# Аутентифицированный клиент
from src.core.realtime import create_ws_client

client = create_ws_client(
    url="ws://localhost:8000/realtime/ws",
    token="your-jwt-token"
)
```

## 📁 Бинарные данные

```python
# Отправка файла
with open("image.png", "rb") as f:
    file_data = f.read()

binary_msg = BinaryMessage.from_bytes(
    data=file_data,
    content_type="image/png",
    filename="image.png"
)

await client.send_binary(binary_msg)
```

## 🏠 Каналы и комнаты

```python
# Присоединение к каналу
await client.send_command("join_channel", {"channel": "chat_room_1"})

# Отправка в канал
await client.send_json({
    "type": "channel_message",
    "channel": "chat_room_1",
    "message": "Привет всем в комнате!"
})
```

## 📚 Подробная документация

- [🌐 WebSocket и SSE](websocket-sse.md) - полная документация
- [📡 Realtime с бинарными данными](REALTIME_BINARY_WEBRTC.md) - WebRTC и файлы
- [📋 Примеры](../examples/realtime_examples.py) - практические примеры

## 🧪 Тестирование

```python
import pytest
from src.core.realtime import WSClient


@pytest.mark.asyncio
async def test_websocket_connection():
    client = WSClient("ws://localhost:8000/realtime/ws")

    await client.connect()
    await client.send_text("Test message")
    await client.disconnect()
```

## 🎮 Клиентский JavaScript

```javascript
// WebSocket
const ws = new WebSocket("ws://localhost:8000/realtime/ws");
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Получено:", data);
};

// SSE
const eventSource = new EventSource("/realtime/events");
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("SSE событие:", data);
};
```

---

**См. также**:

- [websocket-sse.md](websocket-sse.md) для подробной документации
- [REALTIME_BINARY_WEBRTC.md](REALTIME_BINARY_WEBRTC.md) для WebRTC
