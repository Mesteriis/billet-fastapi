# WebSocket и SSE система

Комплексная система для взаимодействия с фронтендом в реальном времени через WebSocket и Server-Sent Events (SSE) с поддержкой отключаемой авторизации.

## Возможности

- ✅ WebSocket соединения с автоматическим переподключением
- ✅ Server-Sent Events для потоковой передачи данных
- ✅ Отключаемая авторизация через JWT и API ключи
- ✅ Система каналов и подписок
- ✅ Персональные сообщения
- ✅ Система уведомлений
- ✅ Heartbeat для контроля соединений
- ✅ Менеджер соединений с автоочисткой
- ✅ Клиентские библиотеки для Python
- ✅ Полная документация и примеры

## Архитектура

```
src/streaming/
├── auth.py              # Система авторизации
├── connection_manager.py # Менеджер соединений
├── ws_models.py         # Модели данных
├── ws_routes.py         # WebSocket роутеры
├── sse_routes.py        # SSE роутеры
├── ws_client.py         # WebSocket клиент
└── sse_client.py        # SSE клиент
```

## Быстрый старт

### 1. Настройка переменных окружения

```env
# Включение компонентов
WEBSOCKET_ENABLED=true
SSE_ENABLED=true
WEBSOCKET_AUTH_REQUIRED=false
SSE_AUTH_REQUIRED=false

# Настройки WebSocket
WEBSOCKET_HEARTBEAT_INTERVAL=30
WEBSOCKET_MAX_CONNECTIONS=1000
WEBSOCKET_MESSAGE_QUEUE_SIZE=100
WEBSOCKET_DISCONNECT_TIMEOUT=60

# Настройки SSE
SSE_HEARTBEAT_INTERVAL=30
SSE_MAX_CONNECTIONS=500
SSE_RETRY_TIMEOUT=3000
SSE_MAX_MESSAGE_SIZE=1048576

# Авторизация
WS_JWT_SECRET_KEY=your-websocket-secret-key
WS_JWT_ALGORITHM=HS256
WS_JWT_EXPIRE_MINUTES=60
WS_API_KEY_HEADER=X-API-Key
WS_API_KEYS=api-key-1,api-key-2
```

### 2. Запуск сервера

```bash
# Установка зависимостей
uv sync

# Запуск сервера
WEBSOCKET_ENABLED=true SSE_ENABLED=true uvicorn src.main:app --reload
```

### 3. Тестирование

Откройте браузер:

- WebSocket тест: http://localhost:8000/ws/test-page
- SSE тест: http://localhost:8000/sse/test

## WebSocket API

### Подключение

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/connect?token=your-jwt-token");

ws.onopen = function (event) {
  console.log("WebSocket подключен");
};

ws.onmessage = function (event) {
  const data = JSON.parse(event.data);
  console.log("Получено сообщение:", data);
};
```

### Команды WebSocket

#### Ping

```json
{
  "action": "ping",
  "request_id": "unique-id"
}
```

#### Подписка на канал

```json
{
  "action": "subscribe",
  "data": { "channel": "test_channel" },
  "request_id": "unique-id"
}
```

#### Отправка сообщения в канал

```json
{
  "action": "send_to_channel",
  "data": {
    "channel": "test_channel",
    "content": "Привет всем!"
  },
  "request_id": "unique-id"
}
```

#### Отправка личного сообщения

```json
{
  "action": "send_to_user",
  "data": {
    "user_id": "user123",
    "content": "Личное сообщение"
  },
  "request_id": "unique-id"
}
```

### HTTP API для WebSocket

#### Рассылка всем

```bash
curl -X POST "http://localhost:8000/ws/broadcast" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "id": "msg-123",
      "type": "broadcast",
      "content": "Сообщение всем пользователям"
    }
  }'
```

#### Отправка в канал

```bash
curl -X POST "http://localhost:8000/ws/send-to-channel" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "notifications",
    "message": {
      "id": "msg-124",
      "type": "notification",
      "content": {
        "title": "Новое уведомление",
        "message": "Содержимое уведомления"
      }
    },
    "persist": true
  }'
```

## SSE API

### Подключение

```javascript
const eventSource = new EventSource(
  "http://localhost:8000/sse/connect?token=your-jwt-token"
);

eventSource.onopen = function (event) {
  console.log("SSE подключен");
};

eventSource.addEventListener("message", function (event) {
  const data = JSON.parse(event.data);
  console.log("Получено сообщение:", data);
});

eventSource.addEventListener("notification", function (event) {
  const notification = JSON.parse(event.data);
  console.log("Уведомление:", notification);
});
```

### HTTP API для SSE

#### Отправка события в канал

```bash
curl -X POST "http://localhost:8000/sse/send-to-channel" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "news",
    "event": "news_update",
    "data": {
      "title": "Новая статья",
      "content": "Содержимое новости"
    }
  }'
```

#### Отправка уведомления

```bash
curl -X POST "http://localhost:8000/sse/notification" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Важное уведомление",
    "content": "Текст уведомления",
    "type": "warning"
  }'
```

## Python клиенты

### WebSocket клиент

```python
import asyncio
from core.streaming import create_ws_client


async def main():
    # Создаем клиент
    client = create_ws_client(host="localhost", port=8000)

    # Добавляем обработчики
    @client.on_message("text")
    async def handle_message(data):
        print(f"Получено: {data}")

    # Подключаемся
    await client.connect()

    # Подписываемся на канал
    await client.subscribe_to_channel("test_channel")

    # Отправляем сообщение
    await client.send_to_channel("test_channel", "Привет!")

    # Ждем события
    await asyncio.sleep(10)

    # Отключаемся
    await client.disconnect()


asyncio.run(main())
```

### SSE клиент

```python
import asyncio
from core.streaming import create_sse_client


async def main():
    # Создаем клиент
    client = create_sse_client(host="localhost", port=8000)

    # Добавляем обработчики
    @client.on_event("notification")
    async def handle_notification(event_data):
        print(f"Уведомление: {event_data}")

    # Подключаемся
    await client.connect()

    # Отправляем уведомление
    await client.send_notification(
        title="Тест",
        content="Тестовое уведомление"
    )

    # Ждем события
    await asyncio.sleep(10)

    # Отключаемся
    await client.disconnect()


asyncio.run(main())
```

## Авторизация

### JWT токены

```python
from core.streaming import authenticator

# Создание токена
token = authenticator.create_access_token({
    "sub": "user123",
    "name": "Иван Иванов",
    "role": "user"
})

# Использование в клиенте
client = create_ws_client(
    host="localhost",
    port=8000,
    token=token
)
```

### API ключи

```env
# Настройка API ключей
WS_API_KEYS=secret123,admin456,client789
```

```python
# Использование API ключа
client = create_ws_client(
    host="localhost",
    port=8000,
    api_key="secret123"
)
```

### Отключение авторизации

```env
# Отключить авторизацию для WebSocket
WEBSOCKET_AUTH_REQUIRED=false

# Отключить авторизацию для SSE
SSE_AUTH_REQUIRED=false
```

## Системы каналов

### Подписка на каналы

```python
# WebSocket
await client.subscribe_to_channel("news")
await client.subscribe_to_channel("notifications")

# Отписка
await client.unsubscribe_from_channel("news")
```

### Персистентные сообщения

```python
# Сообщения сохраняются для новых подписчиков
await connection_manager.broadcast_to_channel(
    "important_updates",
    message,
    persist=True
)
```

## Мониторинг и статистика

### Получение статистики

```bash
curl "http://localhost:8000/ws/stats"
```

```json
{
  "websocket": {
    "total": 25,
    "max": 1000,
    "users": 15
  },
  "sse": {
    "total": 10,
    "max": 500,
    "users": 8
  },
  "channels": {
    "total": 5,
    "subscriptions": 45
  },
  "total_connections": 35
}
```

### Список активных соединений

```bash
curl "http://localhost:8000/ws/connections"
```

### Принудительное закрытие соединения

```bash
curl -X DELETE "http://localhost:8000/ws/connections/connection-id"
```

## Система уведомлений

### Типы уведомлений

- `info` - Информационные
- `success` - Успешные операции
- `warning` - Предупреждения
- `error` - Ошибки

### Отправка уведомлений

```python
from core.streaming import NotificationMessage

notification = NotificationMessage(
    title="Обновление системы",
    content="Система будет недоступна с 22:00 до 23:00",
    type="warning",
    auto_hide=False,
    duration=10000
)

# Отправка всем
await connection_manager.broadcast_to_all(notification)

# Отправка в канал
await connection_manager.broadcast_to_channel("admin", notification)

# Отправка пользователю
await connection_manager.send_to_user("user123", notification)
```

## Heartbeat и контроль соединений

### Настройка Heartbeat

```env
# WebSocket heartbeat каждые 30 секунд
WEBSOCKET_HEARTBEAT_INTERVAL=30

# SSE heartbeat каждые 30 секунд
SSE_HEARTBEAT_INTERVAL=30

# Таймаут неактивных соединений
WEBSOCKET_DISCONNECT_TIMEOUT=60
```

### Автоматическая очистка

```python
# Ручная очистка неактивных соединений
await connection_manager.cleanup_inactive_connections()
```

## Обработка ошибок

### WebSocket ошибки

```python
@client.on_message("error")
async def handle_error(data):
    error_type = data.get("content", {}).get("type")
    error_message = data.get("content", {}).get("error")
    print(f"Ошибка {error_type}: {error_message}")
```

### SSE ошибки

```python
@client.on_event("error")
async def handle_error(event_data):
    error = event_data.get("data", {})
    print(f"SSE ошибка: {error}")
```

### Переподключение

```python
# WebSocket автопереподключение
client = create_ws_client(
    host="localhost",
    port=8000,
    auto_reconnect=True,
    max_reconnect_attempts=10,
    reconnect_interval=5
)

# SSE автопереподключение
sse_client = create_sse_client(
    host="localhost",
    port=8000,
    auto_reconnect=True,
    max_reconnect_attempts=10,
    reconnect_interval=5
)
```

## Производительность

### Лимиты соединений

```env
# Максимум WebSocket соединений
WEBSOCKET_MAX_CONNECTIONS=1000

# Максимум SSE соединений
SSE_MAX_CONNECTIONS=500

# Размер очереди сообщений
WEBSOCKET_MESSAGE_QUEUE_SIZE=100
```

### Оптимизация

- Используйте каналы для группировки пользователей
- Ограничивайте размер сообщений
- Включайте только необходимые heartbeat
- Настраивайте таймауты под ваши нужды

## Безопасность

### Рекомендации

1. **Всегда используйте авторизацию в продакшене**

   ```env
   WEBSOCKET_AUTH_REQUIRED=true
   SSE_AUTH_REQUIRED=true
   ```

2. **Используйте сильные секретные ключи**

   ```env
   WS_JWT_SECRET_KEY=very-long-and-secure-secret-key
   ```

3. **Ограничивайте доступ по IP**

   ```python
   # В middleware FastAPI
   allowed_ips = ["192.168.1.0/24", "10.0.0.0/8"]
   ```

4. **Мониторьте подозрительную активность**
   ```python
   # Логируйте все подключения
   logger.info(f"Connection from {client_ip}: {connection_id}")
   ```

## Развертывание

### Docker

```dockerfile
FROM python:3.13-slim

COPY . /app
WORKDIR /app

RUN pip install uv && uv sync

ENV WEBSOCKET_ENABLED=true
ENV SSE_ENABLED=true
ENV WEBSOCKET_AUTH_REQUIRED=true
ENV SSE_AUTH_REQUIRED=true

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Nginx конфигурация

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # WebSocket прокси
    location /ws/ {
        proxy_pass http://app:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # SSE прокси
    location /sse/ {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_buffering off;
        proxy_cache off;
    }

    # Обычные HTTP запросы
    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Примеры интеграций

### React.js

```jsx
import { useEffect, useState } from "react";

function WebSocketComponent() {
  const [ws, setWs] = useState(null);
  const [messages, setMessages] = useState([]);

  useEffect(() => {
    const websocket = new WebSocket("ws://localhost:8000/ws/connect");

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages((prev) => [...prev, data]);
    };

    setWs(websocket);

    return () => websocket.close();
  }, []);

  const sendMessage = () => {
    if (ws) {
      ws.send(
        JSON.stringify({
          action: "message",
          data: { content: "Hello from React!" },
        })
      );
    }
  };

  return (
    <div>
      <button onClick={sendMessage}>Send Message</button>
      <div>
        {messages.map((msg, idx) => (
          <div key={idx}>{JSON.stringify(msg)}</div>
        ))}
      </div>
    </div>
  );
}
```

### Vue.js

```vue
<template>
  <div>
    <button @click="sendMessage">Send Message</button>
    <div v-for="(msg, idx) in messages" :key="idx">
      {{ msg }}
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      ws: null,
      messages: [],
    };
  },
  mounted() {
    this.ws = new WebSocket("ws://localhost:8000/ws/connect");
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.messages.push(data);
    };
  },
  beforeUnmount() {
    if (this.ws) {
      this.ws.close();
    }
  },
  methods: {
    sendMessage() {
      if (this.ws) {
        this.ws.send(
          JSON.stringify({
            action: "message",
            data: { content: "Hello from Vue!" },
          })
        );
      }
    },
  },
};
</script>
```

## Troubleshooting

### WebSocket не подключается

1. Проверьте `WEBSOCKET_ENABLED=true`
2. Убедитесь что сервер запущен
3. Проверьте URL подключения
4. Проверьте настройки авторизации

### SSE события не приходят

1. Проверьте `SSE_ENABLED=true`
2. Убедитесь в корректности URL
3. Проверьте заголовки CORS
4. Проверьте буферизацию прокси

### Авторизация не работает

1. Проверьте настройки `*_AUTH_REQUIRED`
2. Убедитесь в правильности токенов/ключей
3. Проверьте время действия JWT
4. Проверьте секретные ключи

### Соединения разрываются

1. Настройте heartbeat интервалы
2. Проверьте настройки прокси
3. Увеличьте таймауты
4. Включите автопереподключение в клиентах

## Лучшие практики

1. **Используйте каналы** для группировки связанных данных
2. **Ограничивайте размер сообщений** для производительности
3. **Включайте авторизацию** в продакшене
4. **Мониторьте соединения** и настройте алерты
5. **Тестируйте под нагрузкой** перед продакшеном
6. **Используйте персистентные сообщения** для важных данных
7. **Настройте логирование** для отладки
8. **Планируйте масштабирование** заранее

## Поддержка

Для получения помощи:

1. Проверьте документацию
2. Изучите примеры в `examples/websocket_examples.py`
3. Используйте тестовые страницы
4. Проверьте логи приложения
