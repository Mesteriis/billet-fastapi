# 📚 Примеры использования

Эта папка содержит практические примеры использования всех компонентов проекта. Каждый файл демонстрирует конкретную систему или интеграцию между системами.

## 📁 Структура примеров

### 🔐 Аутентификация и пользователи

**`auth_examples.py`** - Система аутентификации и управления пользователями

- Регистрация и вход пользователей
- Работа с JWT токенами и refresh токенами
- Система ролей и разрешений
- Защищенные API endpoints
- Управление сессиями
- Лучшие практики безопасности

```bash
python examples/auth_examples.py
# Или FastAPI сервер:
uvicorn examples.auth_examples:app --reload --port 8002
```

### 💾 База данных и миграции

**`database_examples.py`** - Работа с базой данных и миграциями

- Автоматическое создание базы данных
- Управление миграциями Alembic
- CRUD операции с SQLAlchemy
- Мониторинг состояния БД
- Оптимизация производительности
- CLI команды для БД

```bash
python examples/database_examples.py
```

### 📨 Система сообщений

**`messaging_examples.py`** - FastStream + RabbitMQ messaging

- Отправка различных типов сообщений
- Обработка входящих сообщений
- Массовая отправка и обработка ошибок
- Интеграция с FastAPI
- Мониторинг и статистика
- Продвинутые паттерны (Saga, Event Sourcing)

```bash
python examples/messaging_examples.py
# Или FastAPI сервер:
uvicorn examples.messaging_examples:app --reload --port 8001
```

### 🔄 Realtime система

**`realtime_examples.py`** - WebSocket + SSE + WebRTC

- WebSocket соединения и обмен сообщениями
- Server-Sent Events для потоковых данных
- WebRTC сигналинг для P2P связи
- Передача бинарных данных
- Система каналов и комнат
- Мониторинг соединений

```bash
python examples/realtime_examples.py
# Или FastAPI сервер:
uvicorn examples.realtime_examples:app --reload --port 8001
```

### 🤖 Telegram боты

**`telegram_examples.py`** - Интеграция с Telegram

- Создание и настройка ботов
- Обработка команд и сообщений
- Inline клавиатуры и callback запросы
- Обработка файлов и медиа
- Админские функции
- Webhook и polling режимы
- Интеграция с основным приложением

```bash
python examples/telegram_examples.py
```

### 🔗 Интеграция систем

**`integration_examples.py`** - Комплексные сценарии

- Полный путь пользователя через все системы
- Обработка заказов с использованием всех компонентов
- Realtime чат с уведомлениями
- Мониторинг всех систем
- Интегрированное FastAPI приложение

```bash
python examples/integration_examples.py
# Или FastAPI сервер:
uvicorn examples.integration_examples:app --reload --port 8003
```

### 🌐 WebSocket примеры

**`websocket_examples.py`** - Дополнительные WebSocket примеры

- Различные паттерны WebSocket соединений
- Обработка событий и ошибок
- Примеры клиентского кода

```bash
python examples/websocket_examples.py
```

## 🚀 Быстрый старт

### 1. Подготовка окружения

```bash
# Установка зависимостей
uv sync

# Настройка переменных окружения
cp .env.example .env
# Отредактируйте .env файл

# Запуск инфраструктуры
docker-compose up -d postgres rabbitmq redis
```

### 2. Подготовка базы данных

```bash
# Автоматическое создание БД и миграции
make db-ensure
make migrate-safe
```

### 3. Запуск примеров

```bash
# Основное приложение (для realtime примеров)
uvicorn src.main:app --reload

# В другом терминале - примеры
python examples/database_examples.py
python examples/messaging_examples.py
python examples/auth_examples.py
```

## 📋 Примеры по категориям

### 🔰 Базовые примеры

Начните с этих примеров для понимания основ:

1. **`database_examples.py`** - Основы работы с БД
2. **`auth_examples.py`** - Аутентификация пользователей
3. **`messaging_examples.py`** - Отправка сообщений

### 🔄 Realtime примеры

Для работы с данными в реальном времени:

1. **`realtime_examples.py`** - WebSocket и SSE
2. **`websocket_examples.py`** - Дополнительные WebSocket паттерны

### 🤖 Боты и интеграции

Для расширенной функциональности:

1. **`telegram_examples.py`** - Telegram боты
2. **`integration_examples.py`** - Комплексные сценарии

## 🔧 Конфигурация для примеров

### Минимальная конфигурация

```bash
# .env
SECRET_KEY=your-secret-key-for-examples
POSTGRES_PASSWORD=postgres
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
REDIS_URL=redis://localhost:6379/0
```

### Полная конфигурация

```bash
# Основные настройки
SECRET_KEY=your-super-secret-key-change-this-in-production
ENVIRONMENT=development
DEBUG=true

# База данных
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=mango_msg

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# Redis
REDIS_URL=redis://localhost:6379/0

# Компоненты
WEBSOCKET_ENABLED=true
SSE_ENABLED=true
TELEGRAM_BOTS_ENABLED=false
TRACING_ENABLED=true

# Telegram (опционально)
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ADMIN_IDS=123456789
```

## 🧪 Тестирование примеров

### Автоматическое тестирование

```bash
# Тестирование всех компонентов
make test

# Тестирование конкретных модулей
make test-auth
make test-messaging
make test-realtime
```

### Ручное тестирование

```bash
# 1. Запустите основное приложение
uvicorn src.main:app --reload

# 2. В другом терминале - примеры
python examples/messaging_examples.py

# 3. Для FastAPI примеров
uvicorn examples.auth_examples:app --reload --port 8002
# Откройте http://localhost:8002/docs
```

## 📊 Мониторинг примеров

### Логи и отладка

```bash
# Включение детального логирования
export LOG_LEVEL=DEBUG

# Запуск с логированием
python examples/integration_examples.py 2>&1 | tee examples.log
```

### Health checks

```bash
# Проверка состояния систем
curl http://localhost:8000/
curl http://localhost:8000/messaging/health

# Для примеров с FastAPI
curl http://localhost:8002/api/v1/health
curl http://localhost:8003/api/v1/integration/health
```

## 🔍 Отладка проблем

### Частые проблемы

1. **Ошибка подключения к БД**

   ```bash
   # Проверьте, запущен ли PostgreSQL
   docker-compose up -d postgres
   make db-test
   ```

2. **Ошибка подключения к RabbitMQ**

   ```bash
   # Проверьте, запущен ли RabbitMQ
   docker-compose up -d rabbitmq
   curl http://localhost:15672  # Management UI
   ```

3. **Ошибки импорта**

   ```bash
   # Убедитесь, что PYTHONPATH настроен
   export PYTHONPATH=src:$PYTHONPATH
   ```

4. **Ошибки миграций**
   ```bash
   # Сброс и повторное применение
   make migrate-reset
   make migrate-safe
   ```

### Логи и диагностика

```bash
# Проверка логов Docker контейнеров
docker-compose logs postgres
docker-compose logs rabbitmq

# Проверка состояния БД
make db-info
make migrate-status

# Мониторинг системы
python examples/integration_examples.py
```

## 📚 Дополнительные ресурсы

### Документация

- [📋 Структура приложений](../docs/APPS_STRUCTURE.md)
- [🗄️ Автоматическое создание БД](../docs/DATABASE_AUTO_CREATE.md)
- [🐰 FastStream + RabbitMQ](../docs/FASTSTREAM_RABBITMQ.md)
- [🌐 WebSocket и SSE](../docs/websocket-sse.md)
- [🤖 Telegram боты](../docs/telegram-bots.md)

### Внешние ресурсы

- [FastAPI документация](https://fastapi.tiangolo.com/)
- [SQLAlchemy документация](https://docs.sqlalchemy.org/)
- [FastStream документация](https://faststream.airt.ai/)
- [aiogram документация](https://docs.aiogram.dev/)

## 🤝 Вклад в примеры

### Добавление новых примеров

1. Создайте новый файл в папке `examples/`
2. Следуйте структуре существующих примеров
3. Добавьте описание в этот README
4. Создайте тесты для примера

### Структура примера

```python
#!/usr/bin/env python3
"""
Описание примера.

Что демонстрирует этот пример:
- Функция 1
- Функция 2
- Интеграция с системой X
"""

import asyncio
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def example_function():
    """Описание функции примера."""
    print("🎯 Название примера")
    # Код примера
    print("✅ Пример завершен")

async def main():
    """Главная функция."""
    print("🎯 Примеры использования X")
    print("=" * 50)

    try:
        await example_function()
        print("\n🎉 Все примеры выполнены успешно!")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
```

---

**Последнее обновление**: 2024-12-19  
**Примеров**: 6 основных файлов  
**Покрытие**: Все основные компоненты проекта
