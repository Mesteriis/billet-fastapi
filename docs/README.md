# 📚 Документация проекта

Добро пожаловать в документацию FastAPI проекта с интегрированными системами messaging, realtime, аутентификации и управления пользователями.

## 🏗️ Обзор проекта

Это современный FastAPI проект с разделенными системами:

- **📨 Messaging** - асинхронная обработка сообщений через FastStream + RabbitMQ
- **🔄 Realtime** - взаимодействие в реальном времени через WebSocket, SSE и WebRTC
- **🔐 Auth & Users** - система аутентификации JWT и управления пользователями
- **💾 Database** - PostgreSQL с автоматическими миграциями и мониторингом
- **⚡ TaskIQ** - фоновые задачи и планировщик
- **🤖 Telegram** - интеграция с Telegram ботами (опционально)

## 📋 Структура документации

### 🏛️ Архитектура и структура

- [📋 Структура приложений](APPS_STRUCTURE.md) - система Auth и Users
- [🏛️ Улучшения архитектуры](ARCHITECTURE_IMPROVEMENTS.md) - SOLID принципы и доменная архитектура
- [🔧 Переменные окружения](ENV_VARIABLES.md) - полный список всех настроек (89 переменных)

### 💾 База данных и миграции

- [🗄️ Автоматическое создание БД](DATABASE_AUTO_CREATE.md) - DatabaseManager и CLI команды
- [🔄 Миграции Alembic](ALEMBIC_MIGRATION.md) - настройка в pyproject.toml
- [⚙️ Конфигурация](CONFIGURATION_MIGRATION.md) - централизация настроек

### 📨 Messaging система

- [🐰 FastStream + RabbitMQ](FASTSTREAM_RABBITMQ.md) - полная документация по системе сообщений
- [📋 Messaging API](README_messaging.md) - краткое руководство по использованию

### 🔄 Realtime система

- [🌐 WebSocket и SSE](websocket-sse.md) - система реального времени
- [📡 Realtime с бинарными данными](REALTIME_BINARY_WEBRTC.md) - WebRTC и файлы
- [📋 Streaming API](README_stream.md) - краткое руководство

### 🧪 Тестирование

- [🧪 Руководство по тестированию](README_tests.md) - comprehensive тестирование
- [🎭 E2E тестирование](E2E_TESTING_GUIDE.md) - Playwright тесты

### 🔧 Инструменты разработки

- [🔗 Pre-commit хуки](PRE_COMMIT_GUIDE.md) - настройка и использование
- [💡 Рекомендации Pre-commit](PRE_COMMIT_RECOMMENDATIONS.md) - улучшения качества кода

### 🤖 Дополнительные модули

- [🤖 Telegram боты](telegram-bots.md) - интеграция с Telegram
- [⚡ TaskIQ](taskiq.md) - фоновые задачи

### 📊 Мониторинг и рефакторинг

- [🔍 Анализ рефакторинга](REFACTORING_ANALYSIS.md) - анализ архитектуры и улучшения

## 🚀 Быстрый старт

### 1. Установка и настройка

```bash
# Клонирование и установка
git clone <repository-url>
cd blank-fastapi-projects
uv sync

# Настройка окружения
cp .env.example .env
# Отредактируйте .env файл

# Запуск инфраструктуры
docker-compose up -d postgres rabbitmq redis
```

### 2. Подготовка базы данных

```bash
# Автоматическое создание БД и применение миграций
make db-ensure
make migrate-safe
```

### 3. Запуск приложения

```bash
# Основное приложение
uvicorn src.main:app --reload

# Приложение будет доступно на http://localhost:8000
```

## 📖 Основные руководства

### Для начинающих

1. **[Переменные окружения](ENV_VARIABLES.md)** - настройка конфигурации
2. **[Автоматическое создание БД](DATABASE_AUTO_CREATE.md)** - подготовка базы данных
3. **[Структура приложений](APPS_STRUCTURE.md)** - понимание архитектуры

### Для разработчиков

1. **[FastStream + RabbitMQ](FASTSTREAM_RABBITMQ.md)** - система сообщений
2. **[WebSocket и SSE](websocket-sse.md)** - realtime функциональность
3. **[Руководство по тестированию](README_tests.md)** - написание тестов

### Для DevOps

1. **[Миграции Alembic](ALEMBIC_MIGRATION.md)** - управление схемой БД
2. **[Pre-commit хуки](PRE_COMMIT_GUIDE.md)** - автоматизация качества кода
3. **[E2E тестирование](E2E_TESTING_GUIDE.md)** - интеграционные тесты

## 🔧 Основные команды

### База данных

```bash
make db-info              # Информация о БД
make db-create            # Создание БД
make db-ensure            # Проверка/создание БД
make migrate-safe         # Безопасная миграция
make migrate-status       # Статус миграций
```

### Разработка

```bash
make dev                  # Запуск в режиме разработки
make test                 # Запуск тестов
make lint                 # Проверка кода
make format              # Форматирование кода
```

### Качество кода

```bash
make pre-commit-run      # Запуск pre-commit хуков
make test-cov            # Тесты с покрытием
make check-architecture  # Проверка архитектуры
```

## 🌐 API Endpoints

### Core API

- `GET /` - Информация о приложении
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc документация

### Messaging API

- `POST /messaging/user-notification` - Уведомление пользователю
- `POST /messaging/admin-notification` - Админское уведомление
- `GET /messaging/health` - Проверка состояния

### Realtime API

- `WS /realtime/ws` - Основной WebSocket
- `GET /realtime/events` - SSE поток
- `WS /realtime/webrtc/signaling` - WebRTC сигналинг

### Auth API

- `POST /auth/register` - Регистрация
- `POST /auth/login` - Вход в систему
- `GET /profile` - Профиль пользователя

## 📊 Архитектура

```
src/
├── apps/                   # Бизнес-логика приложений
│   ├── auth/              # Система аутентификации
│   ├── users/             # Управление пользователями
│   └── base/              # Базовые компоненты
├── core/                   # Основная инфраструктура
│   ├── config.py          # Настройки приложения
│   ├── database.py        # Подключение к БД
│   ├── migrations/        # Система миграций
│   └── tasks.py           # TaskIQ задачи
├── messaging/             # Система сообщений
├── realtime/             # Система реального времени
├── telegram/             # Telegram боты
└── main.py              # Точка входа FastAPI
```

## 🔍 Поиск по документации

### По компонентам

- **База данных**: [DATABASE_AUTO_CREATE.md](DATABASE_AUTO_CREATE.md), [ALEMBIC_MIGRATION.md](ALEMBIC_MIGRATION.md)
- **Messaging**: [FASTSTREAM_RABBITMQ.md](FASTSTREAM_RABBITMQ.md)
- **Realtime**: [websocket-sse.md](websocket-sse.md), [REALTIME_BINARY_WEBRTC.md](REALTIME_BINARY_WEBRTC.md)
- **Аутентификация**: [APPS_STRUCTURE.md](APPS_STRUCTURE.md)
- **Тестирование**: [README_tests.md](README_tests.md), [E2E_TESTING_GUIDE.md](E2E_TESTING_GUIDE.md)

### По задачам

- **Настройка проекта**: [ENV_VARIABLES.md](ENV_VARIABLES.md), [CONFIGURATION_MIGRATION.md](CONFIGURATION_MIGRATION.md)
- **Разработка**: [PRE_COMMIT_GUIDE.md](PRE_COMMIT_GUIDE.md), [ARCHITECTURE_IMPROVEMENTS.md](ARCHITECTURE_IMPROVEMENTS.md)
- **Развертывание**: [DATABASE_AUTO_CREATE.md](DATABASE_AUTO_CREATE.md), [ALEMBIC_MIGRATION.md](ALEMBIC_MIGRATION.md)

## 📚 Примеры кода

Практические примеры использования всех компонентов находятся в папке [`../examples/`](../examples/):

- **[auth_examples.py](../examples/auth_examples.py)** - аутентификация и пользователи
- **[database_examples.py](../examples/database_examples.py)** - работа с БД и миграциями
- **[messaging_examples.py](../examples/messaging_examples.py)** - система сообщений
- **[realtime_examples.py](../examples/realtime_examples.py)** - realtime функциональность
- **[telegram_examples.py](../examples/telegram_examples.py)** - Telegram боты
- **[integration_examples.py](../examples/integration_examples.py)** - интеграция систем

## 🤝 Вклад в документацию

### Добавление новой документации

1. Создайте новый `.md` файл в папке `docs/`
2. Следуйте структуре существующих документов
3. Добавьте ссылку в этот README
4. Обновите соответствующие разделы

### Структура документа

```markdown
# Заголовок документа

## Описание

Краткое описание того, что покрывает документ.

## Основные разделы

- Раздел 1
- Раздел 2

## Примеры

Практические примеры использования.

## См. также

Ссылки на связанные документы.
```

## 🔗 Полезные ссылки

### Внешние ресурсы

- [FastAPI документация](https://fastapi.tiangolo.com/)
- [SQLAlchemy документация](https://docs.sqlalchemy.org/)
- [FastStream документация](https://faststream.airt.ai/)
- [aiogram документация](https://docs.aiogram.dev/)
- [Alembic документация](https://alembic.sqlalchemy.org/)

### Инструменты разработки

- [Ruff](https://docs.astral.sh/ruff/) - линтер и форматтер
- [pytest](https://docs.pytest.org/) - тестирование
- [Playwright](https://playwright.dev/python/) - E2E тесты
- [pre-commit](https://pre-commit.com/) - хуки качества кода

## 📞 Поддержка

- 🐛 [Issues](https://github.com/your-repo/issues) - сообщения об ошибках в документации
- 💬 [Discussions](https://github.com/your-repo/discussions) - вопросы и обсуждения
- 📧 Email: docs@yourcompany.com

---

**Последнее обновление**: 2024-12-19  
**Версия документации**: 1.0.0  
**Документов**: 20+ файлов  
**Покрытие**: Все компоненты проекта
