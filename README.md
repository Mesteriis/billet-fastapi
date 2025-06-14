# FastAPI Project с Messaging и Realtime системами

Современный FastAPI проект с разделенными системами:

- **Messaging** (FastStream + RabbitMQ) - асинхронная обработка сообщений
- **Realtime** (WebSocket + SSE + WebRTC) - взаимодействие в реальном времени с бинарными данными
- **Apps** (Auth + Users) - система аутентификации и управления пользователями
- **Core** (Database + Migrations + TaskIQ) - основная инфраструктура

## 🚀 Возможности

- ⚡ **FastAPI** с асинхронными endpoints
- 🐰 **Messaging**: FastStream с RabbitMQ для асинхронной обработки сообщений
- 🔄 **Realtime**: WebSocket, SSE и WebRTC для взаимодействия в реальном времени
- 📁 **Бинарные данные**: передача файлов, изображений, видео через WebSocket/SSE
- 🎥 **WebRTC**: P2P аудио/видео связь и передача данных
- 🔐 **Аутентификация**: JWT с refresh токенами и системой ролей
- 👥 **Пользователи**: полная система управления пользователями
- 🗄️ **PostgreSQL** с SQLAlchemy (асинхронный) и автоматическими миграциями
- 🔄 **Redis** для кэширования и TaskIQ
- 📊 **OpenTelemetry** для трейсинга
- 🧪 **Comprehensive тестирование** с pytest
- 🔧 **Линтинг и форматирование** с ruff
- 🐳 **Docker** поддержка
- 🤖 **Telegram боты** (опционально)

## 📚 Документация

### 🏗️ Архитектура и структура

- [📋 Структура приложений](docs/APPS_STRUCTURE.md) - система Auth и Users
- [🏛️ Улучшения архитектуры](docs/ARCHITECTURE_IMPROVEMENTS.md) - SOLID принципы и доменная архитектура
- [🔧 Переменные окружения](docs/ENV_VARIABLES.md) - полный список всех настроек (89 переменных)

### 💾 База данных и миграции

- [🗄️ Автоматическое создание БД](docs/DATABASE_AUTO_CREATE.md) - DatabaseManager и CLI команды
- [🔄 Миграции Alembic](docs/ALEMBIC_MIGRATION.md) - настройка в pyproject.toml
- [⚙️ Конфигурация](docs/CONFIGURATION_MIGRATION.md) - централизация настроек

### 📨 Messaging система

- [🐰 FastStream + RabbitMQ](docs/FASTSTREAM_RABBITMQ.md) - полная документация по системе сообщений
- [📋 Messaging API](docs/README.md) - краткое руководство по использованию

### 🔄 Realtime система

- [🌐 WebSocket и SSE](docs/websocket-sse.md) - система реального времени
- [📡 Realtime с бинарными данными](docs/REALTIME_BINARY_WEBRTC.md) - WebRTC и файлы
- [📋 Streaming API](docs/README_stream.md) - краткое руководство

### 🧪 Тестирование

- [🧪 Руководство по тестированию](docs/README_tests.md) - comprehensive тестирование
- [🎭 E2E тестирование](docs/E2E_TESTING_GUIDE.md) - Playwright тесты

### 🔧 Инструменты разработки

- [🔗 Pre-commit хуки](docs/PRE_COMMIT_GUIDE.md) - настройка и использование
- [💡 Рекомендации Pre-commit](docs/PRE_COMMIT_RECOMMENDATIONS.md) - улучшения качества кода

### 🤖 Дополнительные модули

- [🤖 Telegram боты](docs/telegram-bots.md) - интеграция с Telegram
- [⚡ TaskIQ](docs/taskiq.md) - фоновые задачи

## 🏗️ Структура проекта

```
src/
├── apps/                   # Бизнес-логика приложений
│   ├── auth/              # Система аутентификации (JWT, пароли)
│   ├── users/             # Управление пользователями
│   └── base/              # Базовые компоненты (модели, репозитории)
├── core/                   # Основная инфраструктура
│   ├── config.py          # Настройки приложения
│   ├── database.py        # Подключение к БД
│   ├── migrations/        # Система миграций с автосозданием БД
│   ├── tasks.py           # TaskIQ задачи
│   └── telemetry.py       # OpenTelemetry трейсинг
├── messaging/             # Система сообщений FastStream + RabbitMQ
│   ├── core.py           # MessageClient и брокер
│   └── models.py         # Pydantic модели сообщений
├── realtime/             # Система реального времени
│   ├── routes/           # WebSocket, SSE, WebRTC роуты
│   ├── clients/          # Клиенты для подключения
│   ├── models.py         # Модели с поддержкой бинарных данных
│   └── auth.py           # Аутентификация для WebSocket/SSE
├── telegram/             # Telegram боты (опционально)
│   ├── handlers/         # Обработчики команд
│   └── manager.py        # Менеджер ботов
├── tools/                # Утилиты проекта
└── main.py              # Точка входа FastAPI
```

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
# Клонирование репозитория
git clone <repository-url>
cd blank-fastapi-projects

# Установка с uv (рекомендуется)
uv sync

# Или с pip
pip install -e .
```

### 2. Настройка окружения

```bash
# Копирование примера конфигурации
cp .env.example .env

# Редактирование настроек (минимум)
# SECRET_KEY=your-super-secret-key-change-this-in-production
# POSTGRES_PASSWORD=your-secure-password
```

### 3. Запуск инфраструктуры

```bash
# Запуск PostgreSQL и RabbitMQ через Docker
docker-compose up -d postgres rabbitmq

# Или установка локально (macOS)
brew install postgresql rabbitmq
brew services start postgresql rabbitmq
```

### 4. Подготовка базы данных

```bash
# Автоматическое создание БД и применение миграций
make db-ensure
make migrate-safe

# Или пошагово
make db-create
make migrate-up
```

### 5. Запуск приложения

```bash
# Основное приложение
uvicorn src.main:app --reload

# Или через make
make dev

# Приложение будет доступно на http://localhost:8000
```

## 📨 Быстрый старт с Messaging

```python
from core.messaging import get_message_client


async def send_notification():
    client = get_message_client()

    async with client.session():
        # Уведомление пользователю
        await client.send_user_notification(
            user_id=123,
            message="Ваш заказ готов!",
            notification_type="info"
        )

        # Системное событие
        await client.send_system_event(
            event_name="order_completed",
            event_data={"order_id": 456},
            severity="info"
        )
```

## 🔄 Быстрый старт с Realtime

```python
from core.realtime import WSClient, create_sse_client, BinaryMessage

# WebSocket клиент
client = WSClient("ws://localhost:8000/realtime/ws")

async with client:
    # Отправка текста
    await client.send_text("Привет!")

    # Отправка файла
    with open("image.png", "rb") as f:
        file_data = f.read()

    binary_msg = BinaryMessage.from_bytes(file_data, "image/png", "image.png")
    await client.send_binary(binary_msg)

    # WebRTC сигналинг
    await client.send_webrtc_signal(
        signal_type="offer",
        target_peer_id="peer_123",
        sdp="v=0..."
    )

# SSE клиент для уведомлений
sse_client = create_sse_client("http://localhost:8000/realtime/events")
async with sse_client:
    async for event in sse_client.events():
        print(f"Event: {event.event}, Data: {event.data}")
```

## 🔐 Быстрый старт с аутентификацией

```python
from apps.auth.auth_service import AuthService
from apps.users.schemas import UserCreate

# Регистрация пользователя
user_data = UserCreate(
    email="user@example.com",
    username="testuser",
    password="SecurePass123!",
    password_confirm="SecurePass123!"
)

auth_service = AuthService()
user = await auth_service.register_user(db, user_data=user_data)

# Вход в систему
response = await auth_service.login(db, email="user@example.com", password="SecurePass123!")
access_token = response.tokens.access_token
```

## 🌐 API Endpoints

### Core API

```bash
GET  /                      # Информация о приложении
GET  /docs                  # Swagger UI
GET  /redoc                 # ReDoc документация
POST /tasks/example         # Пример TaskIQ задачи
```

### Messaging API

```bash
POST /messaging/user-notification     # Уведомление пользователю
POST /messaging/admin-notification    # Админское уведомление
POST /messaging/order-processing      # Сообщение о заказе
POST /messaging/system-event          # Системное событие
GET  /messaging/health               # Проверка состояния
```

### Realtime API

```bash
# WebSocket
WS   /realtime/ws                    # Основной WebSocket
GET  /realtime/test                  # Тестовая страница
POST /realtime/send                  # Отправка сообщения
POST /realtime/binary/upload         # Загрузка файла
POST /realtime/broadcast             # Широковещательная отправка

# SSE
GET  /realtime/events                # SSE поток
GET  /realtime/sse-test             # Тестовая страница SSE
POST /realtime/notifications/send    # Отправка уведомления

# WebRTC
WS   /realtime/webrtc/signaling     # WebRTC сигналинг
POST /realtime/webrtc/rooms         # Создание комнаты
GET  /realtime/webrtc/rooms         # Список комнат
```

## 🧪 Тестирование

Проект включает комплексную систему тестирования с автоматическим применением миграций:

```bash
# Создание миграций (обязательно перед тестами)
alembic revision --autogenerate -m "Initial migration"

# Все тесты
make test

# Тесты с покрытием
make test-cov

# Быстрые тесты
make test-fast

# E2E тесты (требует Playwright)
make test-e2e

# Конкретные группы
make test-auth
make test-users
make test-messaging
make test-realtime
```

**Фикстура миграций**: Автоматически проверяет наличие миграций и применяет их к временной SQLite БД для тестов. Подробнее в [документации](docs/testing/migrations_fixture.md).

## 🧹 Очистка проекта

Автоматическая система очистки от временных файлов и мусора:

```bash
# Предварительный просмотр очистки
make clean-dry

# Очистка проекта
make clean

# Подробная очистка
make clean-verbose
```

**Безопасно удаляет:**

- Кеш Python (`__pycache__/`, `*.pyc`)
- Кеш тестов (`.pytest_cache/`, `.coverage`)
- Кеш линтеров (`.mypy_cache/`, `.ruff_cache/`)
- Отчеты (`htmlcov/`, `reports/`)
- Временные файлы (`.DS_Store`, `*.tmp`)

**НЕ удаляет важные файлы:**

- Виртуальные окружения (`.venv/`, `venv/`)
- Зависимости (`node_modules/`)
- Исходный код (`src/`, `tests/`)
- Конфигурацию (`.git/`, `pyproject.toml`)

Подробнее: [Документация по очистке](docs/project_cleanup.md)

## 🔐 Аутентификация

Проект поддерживает множественные типы аутентификации:

- **JWT Bearer токены** - основной метод для веб-приложений
- **API ключи** - для внешних сервисов и интеграций
- **WebSocket/SSE аутентификация** - для real-time соединений
- **Опциональная аутентификация** - для публичных endpoints с персонализацией
- **Ролевая авторизация** - система прав доступа (user, admin, superuser)

**Примеры и документация:**

- [Полное руководство по аутентификации](docs/authentication_guide.md)
- [Примеры кода](examples/auth_simple_examples.py)
- [FastAPI endpoints](examples/auth_endpoints_examples.py)
- [Использование url_for](docs/url_for_examples.md)

## 🔧 Команды разработки

### База данных

```bash
make db-info              # Информация о БД
make db-create            # Создание БД
make db-ensure            # Проверка/создание БД
make migrate-safe         # Безопасная миграция
make migrate-status       # Статус миграций
```

### Качество кода

```bash
make lint                 # Проверка кода
make format              # Форматирование
make pre-commit-run      # Запуск pre-commit хуков
make check-architecture  # Проверка архитектуры
```

### Разработка

```bash
make dev                 # Запуск в режиме разработки
make setup-dev           # Настройка окружения разработки
make clean               # Очистка временных файлов
```

## 🐳 Docker

```bash
# Запуск всех сервисов
docker-compose up -d

# Только инфраструктура для разработки
docker-compose up -d postgres rabbitmq redis

# Сборка и запуск приложения
docker-compose up --build app
```

## ⚙️ Конфигурация

### Основные переменные окружения

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

# Компоненты (включение/отключение)
WEBSOCKET_ENABLED=true
SSE_ENABLED=true
TELEGRAM_BOTS_ENABLED=false
TRACING_ENABLED=true
```

**Полный список**: [📋 Переменные окружения](docs/ENV_VARIABLES.md) (89 переменных)

## 📊 Мониторинг

### OpenTelemetry трейсинг

- Автоматическая инструментация HTTP запросов
- Трейсинг операций с БД
- Мониторинг бизнес-логики

### Health checks

```bash
curl http://localhost:8000/                    # Общее состояние
curl http://localhost:8000/messaging/health    # Состояние messaging
```

### Логирование

- Структурированные логи
- Разные уровни для разных компонентов
- Интеграция с OpenTelemetry

## 🚀 Развертывание

### Production настройки

```bash
# Безопасность
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=very-long-and-secure-production-key

# Производительность
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=20

# Мониторинг
TRACING_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=https://your-otel-collector:4317
```

### Docker Production

```dockerfile
FROM python:3.12-slim
COPY . /app
WORKDIR /app
RUN pip install -e .
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🤝 Вклад в проект

1. Fork проекта
2. Создайте feature branch (`git checkout -b feature/amazing-feature`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

### Требования к коду

- Покрытие тестами >80%
- Соблюдение pre-commit хуков
- Документация для новых функций
- Соответствие архитектурным принципам

## 📄 Лицензия

CC BY-NC-ND 4.0

## 🆘 Поддержка

- 📖 [Документация](docs/) - полная документация проекта
- 🐛 [Issues](https://github.com/your-repo/issues) - сообщения об ошибках
- 💬 [Discussions](https://github.com/your-repo/discussions) - вопросы и обсуждения
- 📧 Email: support@yourcompany.com

---

**Последнее обновление**: 2024-12-19  
**Версия**: 1.0.0  
**Python**: 3.12+  
**FastAPI**: 0.104+
