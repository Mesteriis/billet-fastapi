# Realtime система с бинарными данными и WebRTC

## Обзор

Система `realtime` предоставляет современные возможности для взаимодействия в реальном времени, включая:

- **WebSocket** - двунаправленная связь в реальном времени
- **Server-Sent Events (SSE)** - односторонняя связь от сервера к клиенту
- **WebRTC** - peer-to-peer аудио/видео связь и передача данных
- **Бинарные данные** - поддержка передачи файлов, изображений, видео
- **Каналы и комнаты** - система подписок и группировки пользователей

## Архитектура

```
src/realtime/
├── __init__.py              # Экспорты модуля
├── models.py                # Pydantic модели с поддержкой бинарных данных
├── auth.py                  # Аутентификация WebSocket/SSE
├── connection_manager.py    # Управление соединениями
├── routes/
│   ├── ws_routes.py         # WebSocket роуты
│   ├── sse_routes.py        # SSE роуты
│   └── webrtc_routes.py     # WebRTC сигналинг
└── clients/
    ├── ws_client.py         # WebSocket клиент
    └── sse_client.py        # SSE клиент

templates/realtime/
├── websocket_test.html      # Тестовая страница WebSocket
└── sse_test.html           # Тестовая страница SSE
```

## Новые возможности

### 1. Поддержка бинарных данных

#### Отправка файлов через WebSocket

```python
import base64
from core.realtime import WSClient, BinaryMessage

# Создание клиента
client = WSClient("ws://localhost:8000/realtime/ws")

async with client:
    # Отправка файла
    with open("image.png", "rb") as f:
        file_data = f.read()

    binary_message = BinaryMessage.from_bytes(
        data=file_data,
        content_type="image/png",
        filename="image.png"
    )

    await client.send_binary(binary_message)
```

#### Получение бинарных данных

```python
async def handle_binary_message(message):
    """Обработчик бинарных сообщений."""
    if message.get("type") == "binary":
        # Декодируем бинарные данные
        binary_data = base64.b64decode(message["binary_data"])

        # Сохраняем файл
        filename = message.get("filename", "received_file")
        with open(f"downloads/{filename}", "wb") as f:
            f.write(binary_data)

        print(f"Получен файл: {filename}, размер: {len(binary_data)} байт")

client.on_message(handle_binary_message)
```

#### Отправка через HTTP API

```bash
# Загрузка файла
curl -X POST "http://localhost:8000/realtime/binary/upload" \
  -H "Authorization: Bearer your_token" \
  -F "file=@image.png" \
  -F "channel=general"

# Отправка текста как бинарные данные
curl -X POST "http://localhost:8000/realtime/binary/text" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your_token" \
  -d '{
    "text": "Это сообщение будет отправлено как бинарные данные",
    "channel": "general"
  }'
```

### 2. WebRTC функциональность

#### Создание комнаты

```python
import asyncio
from core.realtime.routes import webrtc_rooms

# Создание комнаты через API
response = await client.post("/realtime/webrtc/rooms", json={
    "room_id": "meeting_123",
    "name": "Встреча команды",
    "max_participants": 10
})
```

#### WebRTC сигналинг через WebSocket

```javascript
// Подключение к WebRTC сигналингу
const signalingSocket = new WebSocket('ws://localhost:8000/realtime/webrtc/signaling?room_id=meeting_123');

// Создание RTCPeerConnection
const peerConnection = new RTCPeerConnection({
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' }
    ]
});

// Отправка offer
signalingSocket.send(JSON.stringify({
    signal_type: 'offer',
    target_peer_id: 'peer_456',
    room_id: 'meeting_123',
    sdp: offer.sdp
}));

// Обработка входящих сигналов
signalingSocket.onmessage = (event) => {
    const signal = JSON.parse(event.data);

    switch(signal.signal_type) {
        case 'offer':
            await peerConnection.setRemoteDescription(new RTCSessionDescription({
                type: 'offer',
                sdp: signal.sdp
            }));
            break;

        case 'answer':
            await peerConnection.setRemoteDescription(new RTCSessionDescription({
                type: 'answer',
                sdp: signal.sdp
            }));
            break;

        case 'ice-candidate':
            await peerConnection.addIceCandidate(new RTCIceCandidate(signal.ice_candidate));
            break;
    }
};
```

#### Получение медиа потока

```javascript
// Получение доступа к камере и микрофону
async function startLocalVideo() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: true,
    });

    // Добавление треков в peer connection
    stream.getTracks().forEach((track) => {
      peerConnection.addTrack(track, stream);
    });

    // Отображение локального видео
    document.getElementById("localVideo").srcObject = stream;
  } catch (error) {
    console.error("Ошибка доступа к медиа:", error);
  }
}

// Обработка удаленного потока
peerConnection.ontrack = (event) => {
  document.getElementById("remoteVideo").srcObject = event.streams[0];
};
```

### 3. Расширенные каналы и уведомления

#### Подписка на каналы с фильтрацией

```python
# Подписка на канал с бинарными данными
await client.subscribe_to_channel("file_sharing", {
    "binary_data": True,
    "max_file_size": 10 * 1024 * 1024,  # 10MB
    "allowed_types": ["image/*", "video/*", "application/pdf"]
})

# Подписка на уведомления пользователя
await client.subscribe_to_channel(f"user_{user_id}", {
    "notification_types": ["message", "call", "file"]
})
```

#### Персистентные сообщения

```python
# Отправка сообщения, которое получат новые подписчики
channel_message = ChannelMessage(
    channel="announcements",
    data="Важное объявление для всех пользователей",
    persistent=True  # Сохранить для новых подписчиков
)

await client.send_channel_message(channel_message)
```

## Конфигурация

### Переменные окружения

```bash
# WebSocket настройки
WEBSOCKET_ENABLED=true
WEBSOCKET_AUTH_REQUIRED=false
WEBSOCKET_MAX_CONNECTIONS=1000
WEBSOCKET_HEARTBEAT_INTERVAL=30
WEBSOCKET_BINARY_MAX_SIZE=52428800  # 50MB

# SSE настройки
SSE_ENABLED=true
SSE_AUTH_REQUIRED=false
SSE_MAX_CONNECTIONS=500
SSE_HEARTBEAT_INTERVAL=15
SSE_RETRY_TIMEOUT=3000

# WebRTC настройки
WEBRTC_ENABLED=true
WEBRTC_STUN_SERVERS=stun:stun.l.google.com:19302,stun:stun1.l.google.com:19302
WEBRTC_MAX_ROOMS=100
WEBRTC_MAX_PARTICIPANTS_PER_ROOM=10

# Бинарные данные
BINARY_DATA_ENABLED=true
BINARY_MAX_FILE_SIZE=52428800  # 50MB
BINARY_ALLOWED_TYPES=image/*,video/*,audio/*,application/pdf,text/*
BINARY_COMPRESSION_ENABLED=true
```

### Конфигурация в коде

```python
from core.config import get_settings

settings = get_settings()

# Проверка возможностей
if settings.WEBSOCKET_ENABLED:
    print("WebSocket включен")

if settings.WEBRTC_ENABLED:
    print("WebRTC включен")

if settings.BINARY_DATA_ENABLED:
    print(f"Максимальный размер файла: {settings.BINARY_MAX_FILE_SIZE / 1024 / 1024}MB")
```

## API Endpoints

### WebSocket

- `WS /realtime/ws` - основной WebSocket endpoint
- `GET /realtime/test` - тестовая страница
- `POST /realtime/send` - отправка сообщения
- `POST /realtime/binary/send` - отправка бинарных данных
- `POST /realtime/binary/upload` - загрузка файла
- `POST /realtime/broadcast` - широковещательная отправка

### SSE

- `GET /realtime/events` - SSE поток событий
- `GET /realtime/sse-test` - тестовая страница SSE
- `POST /realtime/notifications/send` - отправка уведомления
- `POST /realtime/notifications/channel` - уведомление в канал
- `POST /realtime/notifications/broadcast` - широковещательное уведомление

### WebRTC

- `WS /realtime/webrtc/signaling` - сигналинг WebSocket
- `POST /realtime/webrtc/rooms` - создание комнаты
- `GET /realtime/webrtc/rooms` - список комнат
- `GET /realtime/webrtc/rooms/{room_id}` - информация о комнате
- `PUT /realtime/webrtc/rooms/{room_id}` - обновление комнаты
- `DELETE /realtime/webrtc/rooms/{room_id}` - удаление комнаты
- `POST /realtime/webrtc/signal` - отправка сигнала
- `GET /realtime/webrtc/connections` - активные соединения

## Клиенты

### Python WebSocket клиент

```python
from core.realtime.clients import WSClient, create_authenticated_client

# Простой клиент
client = WSClient("ws://localhost:8000/realtime/ws")

# Аутентифицированный клиент
auth_client = create_authenticated_client(
    url="ws://localhost:8000/realtime/ws",
    token="your_jwt_token"
)

async with auth_client as client:
    # Отправка текста
    await client.send_text("Привет!")

    # Отправка в канал
    await client.send_to_channel("general", "Сообщение в канал")

    # Отправка бинарных данных
    with open("file.pdf", "rb") as f:
        await client.send_binary(f.read(), content_type="application/pdf")

    # WebRTC сигналинг
    await client.send_webrtc_signal(
        signal_type="offer",
        target_peer_id="peer_123",
        sdp="v=0\r\no=- 123456 ..."
    )
```

### Python SSE клиент

```python
from core.realtime.clients import SSEClient, create_sse_client

# SSE клиент
client = create_sse_client(
    url="http://localhost:8000/realtime/events",
    channel="notifications"
)

async with client:
    async for event in client.events():
        if event.event == "notification":
            print(f"Уведомление: {event.data}")
        elif event.event == "binary_data":
            # Обработка бинарных данных
            handle_binary_event(event.data)
```

### JavaScript клиент

```javascript
class RealtimeClient {
  constructor(wsUrl, sseUrl) {
    this.wsUrl = wsUrl;
    this.sseUrl = sseUrl;
    this.ws = null;
    this.eventSource = null;
  }

  // WebSocket подключение
  connectWebSocket() {
    this.ws = new WebSocket(this.wsUrl);

    this.ws.onopen = () => {
      console.log("WebSocket подключен");
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.ws.onclose = () => {
      console.log("WebSocket отключен");
      // Автоматическое переподключение
      setTimeout(() => this.connectWebSocket(), 5000);
    };
  }

  // SSE подключение
  connectSSE(channel) {
    const url = `${this.sseUrl}?channel=${channel}`;
    this.eventSource = new EventSource(url);

    this.eventSource.addEventListener("notification", (event) => {
      const data = JSON.parse(event.data);
      this.showNotification(data.title, data.body);
    });

    this.eventSource.addEventListener("binary_data", (event) => {
      const data = JSON.parse(event.data);
      this.handleBinaryData(data);
    });
  }

  // Отправка бинарных данных
  async sendFile(file, channel = null) {
    const formData = new FormData();
    formData.append("file", file);
    if (channel) formData.append("channel", channel);

    try {
      const response = await fetch("/realtime/binary/upload", {
        method: "POST",
        body: formData,
        headers: {
          Authorization: `Bearer ${this.token}`,
        },
      });

      if (response.ok) {
        console.log("Файл отправлен успешно");
      }
    } catch (error) {
      console.error("Ошибка отправки файла:", error);
    }
  }

  // Обработка бинарных данных
  handleBinaryData(data) {
    if (data.content_type.startsWith("image/")) {
      this.displayImage(data);
    } else if (data.content_type === "application/pdf") {
      this.downloadFile(data);
    }
  }

  // Отображение изображения
  displayImage(data) {
    const img = document.createElement("img");
    img.src = `data:${data.content_type};base64,${data.binary_data}`;
    document.body.appendChild(img);
  }

  // Скачивание файла
  downloadFile(data) {
    const bytes = atob(data.binary_data);
    const byteArray = new Uint8Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) {
      byteArray[i] = bytes.charCodeAt(i);
    }

    const blob = new Blob([byteArray], { type: data.content_type });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    a.href = url;
    a.download = data.filename || "download";
    a.click();

    URL.revokeObjectURL(url);
  }
}

// Использование
const client = new RealtimeClient(
  "ws://localhost:8000/realtime/ws",
  "http://localhost:8000/realtime/events"
);

client.connectWebSocket();
client.connectSSE("general");
```

## Безопасность

### Аутентификация

```python
# JWT токен
from core.realtime.auth import WSAuthenticator

authenticator = WSAuthenticator()

# Проверка токена
auth_data = await authenticator.verify_jwt_token(token)
if auth_data:
    user_id = auth_data["user_id"]

# API ключ
auth_data = await authenticator.verify_api_key(api_key)
```

### Ограничения и валидация

```python
from core.realtime.models import BinaryMessage

# Валидация бинарных данных
try:
    message = BinaryMessage(
        binary_data="invalid_base64",
        content_type="image/png"
    )
except ValueError as e:
    print(f"Ошибка валидации: {e}")

# Проверка размера файла
if len(file_data) > settings.BINARY_MAX_FILE_SIZE:
    raise ValueError("Файл слишком большой")

# Проверка типа файла
allowed_types = settings.BINARY_ALLOWED_TYPES.split(',')
if not any(content_type.startswith(t.strip()) for t in allowed_types):
    raise ValueError("Тип файла не разрешен")
```

## Мониторинг и отладка

### Логирование

```python
import logging

# Настройка логирования
logging.getLogger("realtime").setLevel(logging.DEBUG)
logging.getLogger("realtime.websocket").setLevel(logging.INFO)
logging.getLogger("realtime.webrtc").setLevel(logging.DEBUG)

# Структурированное логирование
logger.info("Binary data sent", extra={
    "file_size": len(data),
    "content_type": content_type,
    "user_id": user_id,
    "channel": channel
})
```

### Метрики

```python
# Получение статистики
response = await client.get("/realtime/connections")
print(f"Активных соединений: {response['total']}")

# WebRTC статистика
response = await client.get("/realtime/webrtc/connections")
print(f"WebRTC соединений: {response['total']}")

# Статистика по каналам
stats = connection_manager.get_stats()
print(f"Каналов: {len(stats['channels'])}")
```

### Health Checks

```bash
# Проверка WebSocket
curl http://localhost:8000/realtime/health

# Проверка WebRTC
curl http://localhost:8000/realtime/webrtc/health

# Проверка общего состояния
curl http://localhost:8000/health
```

## Примеры использования

### 1. Видеочат

```python
# Создание видеочата
from core.realtime import WebRTCRoom

# Создание комнаты
room = WebRTCRoom(
    room_id="video_call_123",
    name="Видеозвонок",
    max_participants=4
)

# JavaScript на фронтенде
"""
// Получение медиа потока
const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: 1280, height: 720 },
    audio: true
});

// Подключение к сигналингу
const signaling = new WebSocket(
    'ws://localhost:8000/realtime/webrtc/signaling?room_id=video_call_123'
);

// Создание peer connection
const pc = new RTCPeerConnection({
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
});

// Добавление локального потока
stream.getTracks().forEach(track => pc.addTrack(track, stream));
"""
```

### 2. Файловый обмен

```python
# Отправка файла в чат
async def send_file_to_chat(file_path: str, chat_id: str):
    with open(file_path, "rb") as f:
        file_data = f.read()

    binary_message = BinaryMessage.from_bytes(
        data=file_data,
        content_type="application/octet-stream",
        filename=file_path.split("/")[-1]
    )

    await connection_manager.send_to_channel(
        channel=f"chat_{chat_id}",
        message=binary_message.dict()
    )

# Получение файла
async def handle_file_message(message):
    if message.get("type") == "binary":
        filename = message.get("filename", "download")
        binary_data = base64.b64decode(message["binary_data"])

        # Сохранение файла
        with open(f"downloads/{filename}", "wb") as f:
            f.write(binary_data)

        print(f"Файл {filename} сохранен")
```

### 3. Потоковое вещание

```python
# Потоковое вещание камеры
import cv2
import asyncio

async def stream_camera():
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Кодирование кадра в JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        frame_data = buffer.tobytes()

        # Отправка кадра как бинарные данные
        binary_message = BinaryMessage.from_bytes(
            data=frame_data,
            content_type="image/jpeg"
        )

        await connection_manager.broadcast_message(binary_message.dict())
        await asyncio.sleep(1/30)  # 30 FPS

    cap.release()
```

## Развертывание

### Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Установка системных зависимостей для WebRTC
RUN apt-get update && apt-get install -y \
    libopencv-dev \
    libavformat-dev \
    libavcodec-dev \
    libavutil-dev \
    libswscale-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /app
WORKDIR /app

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Nginx конфигурация

```nginx
# WebSocket и SSE прокси
location /realtime/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Увеличиваем таймауты для long-polling SSE
    proxy_read_timeout 86400;
    proxy_send_timeout 86400;

    # Отключаем буферизацию для SSE
    proxy_buffering off;
    proxy_cache off;
}

# Специальная конфигурация для больших файлов
location /realtime/binary/ {
    proxy_pass http://backend;
    client_max_body_size 50M;
    proxy_request_buffering off;
}
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: realtime-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: realtime-app
  template:
    metadata:
      labels:
        app: realtime-app
    spec:
      containers:
        - name: app
          image: realtime-app:latest
          ports:
            - containerPort: 8000
          env:
            - name: WEBSOCKET_ENABLED
              value: "true"
            - name: WEBRTC_ENABLED
              value: "true"
            - name: BINARY_DATA_ENABLED
              value: "true"
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "1Gi"
              cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: realtime-service
spec:
  selector:
    app: realtime-app
  ports:
    - port: 80
      targetPort: 8000
  type: LoadBalancer
```

## Заключение

Система `realtime` предоставляет полноценное решение для взаимодействия в реальном времени с поддержкой:

- ✅ WebSocket для двунаправленной связи
- ✅ SSE для серверных уведомлений
- ✅ WebRTC для P2P аудио/видео
- ✅ Бинарные данные и файлы любого размера
- ✅ Каналы и комнаты для группировки
- ✅ Аутентификация и авторизация
- ✅ Горизонтальное масштабирование
- ✅ Мониторинг и отладка
- ✅ Готовые клиенты для Python и JavaScript

Система готова для использования в продакшене и может быть легко интегрирована в существующие приложения.
