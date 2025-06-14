# FastStream с RabbitMQ - Документация

## Обзор

FastStream — это современная Python библиотека для работы с системами сообщений (message brokers), которая предоставляет удобный асинхронный интерфейс для работы с RabbitMQ, Apache Kafka, Redis и другими брокерами сообщений.

В нашем проекте мы используем FastStream для:

- Асинхронной обработки сообщений
- Реализации микросервисной архитектуры
- Отправки уведомлений пользователям
- Обработки системных событий
- Управления заказами и их состояниями

## Архитектура системы

### Exchanges и Queues

Наша система использует следующую структуру:

#### Exchanges:

- **notifications** (topic) - для уведомлений пользователей и администраторов
- **orders** (direct) - для сообщений о заказах
- **system** (fanout) - для системных событий

#### Queues:

- **user_notifications** - уведомления для пользователей (routing_key: `user.*`)
- **admin_notifications** - уведомления для администраторов (routing_key: `admin.*`)
- **order_processing** - заказы в обработке (routing_key: `process`)
- **order_completed** - завершенные заказы (routing_key: `completed`)
- **system_events** - системные события (получает все сообщения из system exchange)

## Конфигурация

### Переменные окружения

```bash
# RabbitMQ настройки
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_VHOST=/
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
```

### Настройка в config.py

```python
from core.config import get_settings

settings = get_settings()
print(settings.RABBITMQ_URL)  # amqp://guest:guest@localhost:5672/
```

## Модели сообщений

### Базовая модель

```python
from core.streaming import MessageModel

message = MessageModel(
    type="custom_event",
    source="api_service",
    payload={"data": "example"},
    correlation_id="unique_id"  # Опционально для трекинга
)
```

### Уведомления пользователей

```python
from core.streaming import UserNotificationMessage

notification = UserNotificationMessage(
    source="notification_service",
    payload=UserNotificationMessage.PayloadModel(
        user_id=123,
        message="Ваш заказ готов к получению",
        notification_type="info"  # info, warning, error
    )
)
```

### Сообщения о заказах

```python
from core.streaming import OrderProcessingMessage

order_message = OrderProcessingMessage(
    source="order_service",
    payload=OrderProcessingMessage.PayloadModel(
        order_id=456,
        status="completed",
        details={"total": 1999.99, "items": 3}
    )
)
```

### Системные события

```python
from core.streaming import SystemEventMessage

system_event = SystemEventMessage(
    source="monitoring",
    payload=SystemEventMessage.PayloadModel(
        event_name="high_cpu_usage",
        event_data={"cpu_percent": 85, "server": "web-01"},
        severity="warning"  # info, warning, error, critical
    )
)
```

## Использование клиента

### Базовое использование

```python
from core.streaming import MessageClient, get_message_client

# Получение глобального экземпляра
client = get_message_client()

# Или создание нового экземпляра
client = MessageClient()

# Использование с контекстным менеджером
async with client.session():
    await client.send_user_notification(
        user_id=123,
        message="Привет!",
        notification_type="info"
    )
```

### Отправка различных типов сообщений

```python
async def send_messages_example():
    client = get_message_client()

    async with client.session():
        # Уведомление пользователю
        await client.send_user_notification(
            user_id=123,
            message="Ваш заказ принят",
            notification_type="info"
        )

        # Админское уведомление
        await client.send_admin_notification(
            message="Высокая нагрузка на сервер",
            notification_type="warning"
        )

        # Сообщение о заказе
        await client.send_order_processing(
            order_id=456,
            status="processing",
            details={"priority": "high"}
        )

        # Системное событие
        await client.send_system_event(
            event_name="service_restart",
            event_data={"service": "payment-service"},
            severity="info"
        )
```

### Массовая отправка сообщений

```python
import asyncio

async def send_bulk_notifications():
    client = get_message_client()
    user_ids = [1, 2, 3, 4, 5]

    async with client.session():
        tasks = []
        for user_id in user_ids:
            task = client.send_user_notification(
                user_id=user_id,
                message=f"Персональное предложение для вас!",
                notification_type="info"
            )
            tasks.append(task)

        # Отправляем все параллельно
        await asyncio.gather(*tasks)
        print(f"Отправлено {len(tasks)} уведомлений")
```

## Обработчики сообщений

### Создание собственных обработчиков

```python
from core.streaming import get_broker
from core.streaming import UserNotificationMessage

broker = get_broker()


@broker.subscriber("user_notifications")
async def handle_user_notification(message: dict):
    """Обработчик уведомлений пользователей."""
    try:
        notification = UserNotificationMessage(**message)

        # Ваша бизнес-логика
        await send_email_notification(notification)
        await send_push_notification(notification)

        print(f"Уведомление обработано: {notification.id}")

    except Exception as e:
        print(f"Ошибка обработки: {e}")
        raise  # Сообщение будет возвращено в очередь
```

### Подписка на сообщения через клиента

```python
async def setup_message_consumers():
    """Настройка потребителей сообщений."""
    client = get_message_client()

    async def handle_user_notifications(message: dict):
        print(f"Получено уведомление: {message}")
        # Логика обработки

    async def handle_system_events(message: dict):
        print(f"Системное событие: {message}")
        # Логика обработки

    await client.connect()

    # Регистрируем обработчики
    await client.consume_user_notifications(handle_user_notifications)
    await client.consume_system_events(handle_system_events)

    # Запускаем обработку
    try:
        await client.broker.start()
    except KeyboardInterrupt:
        print("Остановка...")
    finally:
        await client.disconnect()
```

## Интеграция с FastAPI

### Автоматическая настройка

```python
from fastapi import FastAPI
from core.streaming import setup_messaging

app = FastAPI()

# Автоматическая настройка FastStream
setup_messaging(app)

# Или использование готового приложения
from core.streaming import create_app_with_messaging

app = create_app_with_messaging()
```

### API endpoints для сообщений

После настройки доступны следующие endpoints:

```bash
# Отправка уведомления пользователю
POST /messaging/user-notification
{
    "user_id": 123,
    "message": "Ваш заказ готов",
    "notification_type": "info"
}

# Отправка админского уведомления
POST /messaging/admin-notification
{
    "message": "Критическая ошибка в системе",
    "notification_type": "error"
}

# Отправка сообщения о заказе
POST /messaging/order-processing
{
    "order_id": 456,
    "status": "completed",
    "details": {"total": 1999.99}
}

# Отправка системного события
POST /messaging/system-event
{
    "event_name": "high_memory_usage",
    "event_data": {"memory_percent": 85},
    "severity": "warning"
}

# Проверка состояния системы сообщений
GET /messaging/health
```

### Использование в роутерах FastAPI

```python
from fastapi import APIRouter, Depends
from core.streaming import get_message_client, MessageClient

router = APIRouter()


@router.post("/orders/{order_id}/complete")
async def complete_order(
        order_id: int,
        client: MessageClient = Depends(get_message_client)
):
    # Логика завершения заказа
    order = await complete_order_logic(order_id)

    # Отправляем уведомление
    await client.send_order_processing(
        order_id=order_id,
        status="completed",
        details={"total": order.total}
    )

    await client.send_user_notification(
        user_id=order.user_id,
        message=f"Ваш заказ #{order_id} успешно завершен!",
        notification_type="info"
    )

    return {"status": "completed", "order_id": order_id}
```

## Тестирование

### Модульные тесты

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from core.streaming import MessageClient


@pytest.fixture
def mock_broker():
    broker = MagicMock()
    broker.connect = AsyncMock()
    broker.close = AsyncMock()
    broker.publish = AsyncMock()
    return broker


@pytest.fixture
def client(mock_broker):
    return MessageClient(broker=mock_broker)


@pytest.mark.asyncio
async def test_send_notification(client, mock_broker):
    await client.send_user_notification(
        user_id=123,
        message="Test",
        notification_type="info"
    )

    mock_broker.publish.assert_called_once()
    call_args = mock_broker.publish.call_args[0][0]
    assert call_args["payload"]["user_id"] == 123
```

### Интеграционные тесты

```python
@pytest.mark.asyncio
async def test_full_message_flow():
    """Тест полного цикла отправки и получения сообщения."""
    # Требует запущенного RabbitMQ
    client = MessageClient()

    received_messages = []

    async def handler(message):
        received_messages.append(message)

    await client.connect()
    await client.consume_user_notifications(handler)

    # Отправляем сообщение
    await client.send_user_notification(
        user_id=123,
        message="Integration test",
        notification_type="info"
    )

    # Проверяем получение (требует времени на обработку)
    await asyncio.sleep(1)
    assert len(received_messages) == 1

    await client.disconnect()
```

### Запуск тестов

```bash
# Все тесты
pytest tests/test_streaming.py

# Только модульные тесты
pytest tests/test_streaming.py::TestMessageClient -v

# Только интеграционные тесты (требует RabbitMQ)
pytest tests/test_streaming.py::TestIntegration -v
```

## Развертывание

### Docker Compose для разработки

```yaml
# docker-compose.yml
version: "3.8"

services:
  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq

  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
    depends_on:
      - rabbitmq

volumes:
  rabbitmq_data:
```

### Переменные окружения для продакшена

```bash
# Production settings
RABBITMQ_HOST=rabbitmq.production.com
RABBITMQ_PORT=5672
RABBITMQ_USER=app_user
RABBITMQ_PASSWORD=secure_password
RABBITMQ_VHOST=/production
```

### Запуск FastStream обработчиков

```bash
# Запуск FastAPI с FastStream
uvicorn src.streaming.fastapi_integration:app --host 0.0.0.0 --port 8000

# Запуск только обработчиков FastStream (отдельный процесс)
faststream run src.streaming.broker:broker
```

### Мониторинг и логирование

```python
import logging

# Настройка логирования для FastStream
logging.getLogger("faststream").setLevel(logging.INFO)
logging.getLogger("src.streaming").setLevel(logging.DEBUG)

# В production рекомендуется использовать structured logging
import structlog

logger = structlog.get_logger()
logger.info("Message sent", user_id=123, message_type="notification")
```

## Лучшие практики

### 1. Обработка ошибок

```python
async def send_notification_with_retry(user_id: int, message: str, max_retries: int = 3):
    """Отправка уведомления с повторными попытками."""
    client = get_message_client()

    for attempt in range(max_retries):
        try:
            async with client.session():
                await client.send_user_notification(
                    user_id=user_id,
                    message=message,
                    notification_type="info"
                )
            return True
        except Exception as e:
            logger.warning(f"Попытка {attempt + 1} неудачна: {e}")
            if attempt == max_retries - 1:
                logger.error(f"Не удалось отправить уведомление после {max_retries} попыток")
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### 2. Валидация сообщений

```python
from pydantic import ValidationError

async def safe_send_order_update(order_data: dict):
    """Безопасная отправка обновления заказа."""
    try:
        # Валидируем данные перед отправкой
        order_message = OrderProcessingMessage(
            source="order_service",
            payload=OrderProcessingMessage.PayloadModel(**order_data)
        )

        client = get_message_client()
        async with client.session():
            await client.send_order_processing(**order_data)

    except ValidationError as e:
        logger.error(f"Некорректные данные заказа: {e}")
        raise ValueError(f"Невалидные данные: {e}")
```

### 3. Мониторинг производительности

```python
import time
from contextlib import asynccontextmanager

@asynccontextmanager
async def timed_message_sending(operation_name: str):
    """Контекстный менеджер для измерения времени отправки."""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.info(f"Операция {operation_name} заняла {duration:.2f} сек")

# Использование
async with timed_message_sending("user_notification"):
    await client.send_user_notification(user_id=123, message="Test")
```

### 4. Graceful shutdown

```python
import signal
import asyncio

class MessageProcessor:
    def __init__(self):
        self.client = get_message_client()
        self.running = True

    async def start(self):
        """Запуск обработчика сообщений."""
        await self.client.connect()

        # Обработка сигналов для корректного завершения
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, self.shutdown)

        try:
            await self.client.broker.start()
        finally:
            await self.client.disconnect()

    def shutdown(self):
        """Корректное завершение работы."""
        logger.info("Получен сигнал завершения")
        self.running = False
```

## Альтернативы и расширения

### Использование с Celery

```python
from celery import Celery
from core.streaming import get_message_client

celery_app = Celery('tasks')


@celery_app.task
async def send_delayed_notification(user_id: int, message: str, delay_seconds: int = 0):
    """Отправка отложенного уведомления через Celery."""
    if delay_seconds > 0:
        await asyncio.sleep(delay_seconds)

    client = get_message_client()
    async with client.session():
        await client.send_user_notification(user_id=user_id, message=message)
```

### Интеграция с другими брокерами

```python
# FastStream поддерживает множество брокеров
from faststream.kafka import KafkaBroker
from faststream.redis import RedisBroker

# Для переключения на Kafka достаточно изменить брокер
kafka_broker = KafkaBroker("localhost:9092")

# Redis Streams
redis_broker = RedisBroker("redis://localhost:6379")
```

## Заключение

FastStream предоставляет мощный и удобный способ работы с системами сообщений в Python. Наша реализация обеспечивает:

- ✅ Типобезопасность с Pydantic моделями
- ✅ Асинхронную обработку сообщений
- ✅ Интеграцию с FastAPI
- ✅ Comprehensive тестирование
- ✅ Удобную разработку и развертывание
- ✅ Масштабируемость и надежность

Система готова для использования в продакшене и может быть легко расширена под новые требования.
