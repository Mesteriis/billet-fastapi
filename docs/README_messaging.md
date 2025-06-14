# 📨 Messaging система - Краткое руководство

Быстрое руководство по использованию системы сообщений FastStream + RabbitMQ.

## 🚀 Быстрый старт

### Отправка сообщения

```python
from core.messaging import get_message_client


async def send_notification():
    client = get_message_client()

    async with client.session():
        await client.send_user_notification(
            user_id=123,
            message="Добро пожаловать!",
            notification_type="info"
        )
```

### Обработка сообщений

```python
from core.messaging import get_message_client


async def setup_handlers():
    client = get_message_client()

    async def handle_notification(message: dict):
        print(f"Получено: {message}")

    await client.consume_user_notifications(handle_notification)
```

## 📋 Основные методы

### Отправка

```python
# Уведомление пользователю
await client.send_user_notification(user_id, message, notification_type)

# Админское уведомление
await client.send_admin_notification(message, notification_type)

# Обработка заказа
await client.send_order_processing(order_id, status, details)

# Системное событие
await client.send_system_event(event_name, event_data, severity)
```

### Подписка

```python
# Подписка на уведомления
await client.consume_user_notifications(handler)
await client.consume_admin_notifications(handler)
await client.consume_order_processing(handler)
await client.consume_system_events(handler)
```

## ⚙️ Настройка

```bash
# .env
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
```

## 🔗 Интеграция с FastAPI

```python
from fastapi import Depends
from core.messaging import get_message_client, MessageClient


@app.post("/notify")
async def notify_user(
        user_id: int,
        message: str,
        client: MessageClient = Depends(get_message_client)
):
    async with client.session():
        await client.send_user_notification(user_id, message, "info")
    return {"status": "sent"}
```

## 📊 Мониторинг

```bash
# Проверка состояния
curl http://localhost:8000/messaging/health

# RabbitMQ Management UI
open http://localhost:15672
```

## 📚 Подробная документация

- [🐰 FastStream + RabbitMQ](FASTSTREAM_RABBITMQ.md) - полная документация
- [📋 Примеры](../examples/messaging_examples.py) - практические примеры

## 🧪 Тестирование

```python
import pytest
from core.messaging import MessageClient


@pytest.mark.asyncio
async def test_send_notification():
    client = get_message_client()

    async with client.session():
        await client.send_user_notification(123, "Test", "info")

    # Проверка отправки
```

---

**См. также**: [FASTSTREAM_RABBITMQ.md](FASTSTREAM_RABBITMQ.md) для подробной документации
