# 🔧 Переменные окружения

Полная документация всех переменных окружения для проекта FastAPI с Messaging и Realtime системами.

## 📋 Список всех переменных

### 🎯 Основные настройки проекта

| Переменная            | Тип  | Значение по умолчанию        | Описание                                   |
| --------------------- | ---- | ---------------------------- | ------------------------------------------ |
| `PROJECT_NAME`        | str  | `"Mango Message"`            | Название проекта                           |
| `PROJECT_DESCRIPTION` | str  | `"API for messaging system"` | Описание проекта                           |
| `VERSION`             | str  | `"1.0.0"`                    | Версия проекта                             |
| `API_V1_STR`          | str  | `"/api/v1"`                  | Префикс API v1                             |
| `TZ`                  | str  | `"Europe/Moscow"`            | Временная зона                             |
| `DEBUG`               | bool | `false`                      | Режим отладки                              |
| `TESTING`             | bool | `false`                      | Режим тестирования                         |
| `ENVIRONMENT`         | str  | `"development"`              | Окружение (development/staging/production) |

### 🗄️ База данных PostgreSQL

| Переменная                | Тип  | Значение по умолчанию | Описание                                 |
| ------------------------- | ---- | --------------------- | ---------------------------------------- |
| `POSTGRES_SERVER`         | str  | `"localhost"`         | Хост PostgreSQL сервера                  |
| `POSTGRES_USER`           | str  | `"postgres"`          | Пользователь PostgreSQL                  |
| `POSTGRES_PASSWORD`       | str  | `"postgres"`          | Пароль PostgreSQL                        |
| `POSTGRES_DB`             | str  | `"mango_msg"`         | Название базы данных                     |
| `SQLALCHEMY_DATABASE_URI` | str  | `auto-generated`      | Полный URI подключения к БД              |
| `DB_POOL_SIZE`            | int  | `20`                  | Размер пула соединений                   |
| `DB_MAX_OVERFLOW`         | int  | `10`                  | Максимальное переполнение пула           |
| `DB_POOL_TIMEOUT`         | int  | `30`                  | Таймаут пула соединений (сек)            |
| `DB_POOL_RECYCLE`         | int  | `1800`                | Время переиспользования соединений (сек) |
| `DB_ECHO`                 | bool | `false`               | Логирование SQL запросов                 |

### 🔴 Redis

| Переменная       | Тип | Значение по умолчанию | Описание                       |
| ---------------- | --- | --------------------- | ------------------------------ |
| `REDIS_HOST`     | str | `"localhost"`         | Хост Redis сервера             |
| `REDIS_PORT`     | int | `6379`                | Порт Redis сервера             |
| `REDIS_DB`       | int | `0`                   | Номер базы данных Redis        |
| `REDIS_PASSWORD` | str | `null`                | Пароль для Redis (опционально) |
| `REDIS_URL`      | str | `auto-generated`      | Полный URI подключения к Redis |

### 🐰 RabbitMQ

| Переменная          | Тип | Значение по умолчанию | Описание                          |
| ------------------- | --- | --------------------- | --------------------------------- |
| `RABBITMQ_HOST`     | str | `"localhost"`         | Хост RabbitMQ сервера             |
| `RABBITMQ_PORT`     | int | `5672`                | Порт RabbitMQ сервера             |
| `RABBITMQ_USER`     | str | `"guest"`             | Пользователь RabbitMQ             |
| `RABBITMQ_PASSWORD` | str | `"guest"`             | Пароль RabbitMQ                   |
| `RABBITMQ_VHOST`    | str | `"/"`                 | Виртуальный хост RabbitMQ         |
| `RABBITMQ_URL`      | str | `auto-generated`      | Полный URI подключения к RabbitMQ |

### 🔐 Безопасность и аутентификация

| Переменная                    | Тип | Значение по умолчанию    | Описание                                |
| ----------------------------- | --- | ------------------------ | --------------------------------------- |
| `SECRET_KEY`                  | str | `"your-secret-key-here"` | **ОБЯЗАТЕЛЬНО:** Секретный ключ для JWT |
| `ALGORITHM`                   | str | `"HS256"`                | Алгоритм шифрования JWT                 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | `30`                     | Время жизни access токена (мин)         |
| `REFRESH_TOKEN_EXPIRE_DAYS`   | int | `30`                     | Время жизни refresh токена (дни)        |

#### Cookies

| Переменная        | Тип  | Значение по умолчанию | Описание                           |
| ----------------- | ---- | --------------------- | ---------------------------------- |
| `COOKIE_SECURE`   | bool | `true`                | Secure флаг для cookies            |
| `COOKIE_SAMESITE` | str  | `"Lax"`               | SameSite атрибут cookies           |
| `COOKIE_MAX_AGE`  | int  | `3600`                | Максимальный возраст cookies (сек) |

### 🌐 CORS

| Переменная     | Тип       | Значение по умолчанию                                | Описание                                  |
| -------------- | --------- | ---------------------------------------------------- | ----------------------------------------- |
| `CORS_ORIGINS` | list[str] | `["http://localhost:8000", "https://api.sh-inc.ru"]` | Разрешенные CORS origins                  |
| `CORS_MAX_AGE` | int       | `600`                                                | Максимальный возраст CORS preflight (сек) |

### 💾 Кэширование

| Переменная     | Тип | Значение по умолчанию | Описание               |
| -------------- | --- | --------------------- | ---------------------- |
| `CACHE_TTL`    | int | `300`                 | Время жизни кэша (сек) |
| `CACHE_PREFIX` | str | `"mango_msg:"`        | Префикс ключей кэша    |

### 🚦 Rate Limiting

| Переменная              | Тип | Значение по умолчанию | Описание                |
| ----------------------- | --- | --------------------- | ----------------------- |
| `RATE_LIMIT_PER_MINUTE` | int | `60`                  | Лимит запросов в минуту |
| `RATE_LIMIT_PER_HOUR`   | int | `1000`                | Лимит запросов в час    |

### 📊 Логирование

| Переменная         | Тип | Значение по умолчанию                                    | Описание                              |
| ------------------ | --- | -------------------------------------------------------- | ------------------------------------- |
| `LOG_LEVEL`        | str | `"INFO"`                                                 | Уровень логирования                   |
| `LOG_FORMAT`       | str | `"%(asctime)s - %(name)s - %(levelname)s - %(message)s"` | Формат логов                          |
| `LOG_FILE`         | str | `"app.log"`                                              | Файл для записи логов                 |
| `LOG_MAX_BYTES`    | int | `10485760`                                               | Максимальный размер файла лога (10MB) |
| `LOG_BACKUP_COUNT` | int | `5`                                                      | Количество backup файлов логов        |

### 🚨 Алерты и уведомления

| Переменная            | Тип  | Значение по умолчанию | Описание                  |
| --------------------- | ---- | --------------------- | ------------------------- |
| `ENABLE_ALERTS`       | bool | `false`               | Включить алерты           |
| `ALERT_EMAIL`         | str  | `null`                | Email для алертов         |
| `ALERT_SLACK_WEBHOOK` | str  | `null`                | Slack webhook для алертов |

### ⚙️ Фоновые задачи

| Переменная                | Тип  | Значение по умолчанию | Описание                         |
| ------------------------- | ---- | --------------------- | -------------------------------- |
| `ENABLE_BACKGROUND_TASKS` | bool | `true`                | Включить фоновые задачи          |
| `MAX_BACKGROUND_WORKERS`  | int  | `4`                   | Максимальное количество воркеров |

### 🔄 TaskIQ

| Переменная                  | Тип | Значение по умолчанию | Описание                             |
| --------------------------- | --- | --------------------- | ------------------------------------ |
| `TASKIQ_BROKER_URL`         | str | `auto-generated`      | URL брокера TaskIQ (Redis DB 1)      |
| `TASKIQ_RESULT_BACKEND_URL` | str | `auto-generated`      | URL бэкенда результатов (Redis DB 2) |
| `TASKIQ_MAX_RETRIES`        | int | `3`                   | Максимальное количество повторов     |
| `TASKIQ_RETRY_DELAY`        | int | `5`                   | Задержка между повторами (сек)       |
| `TASKIQ_TASK_TIMEOUT`       | int | `300`                 | Таймаут выполнения задачи (сек)      |

### 📊 Трассировка (OpenTelemetry)

| Переменная                    | Тип  | Значение по умолчанию | Описание                             |
| ----------------------------- | ---- | --------------------- | ------------------------------------ |
| `TRACING_ENABLED`             | bool | `false`               | Включить трассировку                 |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | str  | `"localhost:4317"`    | Endpoint для OTLP экспорта           |
| `OTEL_EXPORTER_OTLP_INSECURE` | bool | `true`                | Использовать небезопасное соединение |

### 🤖 Telegram боты

| Переменная              | Тип  | Значение по умолчанию | Описание                |
| ----------------------- | ---- | --------------------- | ----------------------- |
| `TELEGRAM_BOTS_ENABLED` | bool | `false`               | Включить Telegram ботов |
| `TELEGRAM_DEBUG`        | bool | `false`               | Режим отладки Telegram  |

### 🔄 WebSocket

| Переменная                     | Тип  | Значение по умолчанию | Описание                           |
| ------------------------------ | ---- | --------------------- | ---------------------------------- |
| `WEBSOCKET_ENABLED`            | bool | `true`                | Включить WebSocket                 |
| `WEBSOCKET_AUTH_REQUIRED`      | bool | `false`               | Требовать аутентификацию           |
| `WEBSOCKET_HEARTBEAT_INTERVAL` | int  | `30`                  | Интервал heartbeat (сек)           |
| `WEBSOCKET_MAX_CONNECTIONS`    | int  | `1000`                | Максимальное количество соединений |
| `WEBSOCKET_MESSAGE_QUEUE_SIZE` | int  | `100`                 | Размер очереди сообщений           |
| `WEBSOCKET_DISCONNECT_TIMEOUT` | int  | `60`                  | Таймаут отключения (сек)           |

### 📡 Server-Sent Events (SSE)

| Переменная               | Тип  | Значение по умолчанию | Описание                            |
| ------------------------ | ---- | --------------------- | ----------------------------------- |
| `SSE_ENABLED`            | bool | `true`                | Включить SSE                        |
| `SSE_AUTH_REQUIRED`      | bool | `false`               | Требовать аутентификацию            |
| `SSE_HEARTBEAT_INTERVAL` | int  | `30`                  | Интервал heartbeat (сек)            |
| `SSE_MAX_CONNECTIONS`    | int  | `500`                 | Максимальное количество соединений  |
| `SSE_RETRY_TIMEOUT`      | int  | `3000`                | Таймаут повтора (мс)                |
| `SSE_MAX_MESSAGE_SIZE`   | int  | `1048576`             | Максимальный размер сообщения (1MB) |

### 🔐 Авторизация WebSocket/SSE

| Переменная              | Тип       | Значение по умолчанию    | Описание                         |
| ----------------------- | --------- | ------------------------ | -------------------------------- |
| `WS_JWT_SECRET_KEY`     | str       | `"websocket-secret-key"` | Секретный ключ для WebSocket JWT |
| `WS_JWT_ALGORITHM`      | str       | `"HS256"`                | Алгоритм для WebSocket JWT       |
| `WS_JWT_EXPIRE_MINUTES` | int       | `60`                     | Время жизни WebSocket JWT (мин)  |
| `WS_API_KEY_HEADER`     | str       | `"X-API-Key"`            | Заголовок для API ключа          |
| `WS_API_KEYS`           | list[str] | `[]`                     | Список разрешенных API ключей    |

## 🚀 Быстрая настройка

### Минимальная конфигурация (.env)

```bash
# Основные настройки
SECRET_KEY=your-super-secret-key-change-this-in-production
ENVIRONMENT=development

# База данных
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=your_app_name

# Redis (опционально)
REDIS_PASSWORD=your-redis-password

# RabbitMQ (опционально)
RABBITMQ_PASSWORD=your-rabbitmq-password
```

### Разработка (.env.development)

```bash
# Наследует базовые настройки + дополнительные
DEBUG=true
DB_ECHO=true
LOG_LEVEL=DEBUG
TRACING_ENABLED=true

# Разрешенные CORS origins для разработки
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000

# WebSocket/SSE без аутентификации для разработки
WEBSOCKET_AUTH_REQUIRED=false
SSE_AUTH_REQUIRED=false
```

### Production (.env.production)

```bash
# Основные настройки
ENVIRONMENT=production
DEBUG=false

# Безопасность
SECRET_KEY=your-production-secret-key-very-long-and-secure
COOKIE_SECURE=true
COOKIE_SAMESITE=Strict

# Производительность
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=20
REDIS_PASSWORD=secure-redis-password

# Алерты
ENABLE_ALERTS=true
ALERT_EMAIL=admin@yourcompany.com
ALERT_SLACK_WEBHOOK=https://hooks.slack.com/services/...

# Трассировка
TRACING_ENABLED=true
OTEL_EXPORTER_OTLP_ENDPOINT=https://your-otel-collector:4317
OTEL_EXPORTER_OTLP_INSECURE=false

# Безопасность WebSocket/SSE
WEBSOCKET_AUTH_REQUIRED=true
SSE_AUTH_REQUIRED=true
WS_API_KEYS=api-key-1,api-key-2,api-key-3
```

### Тестирование (.env.test)

```bash
# Тестовые настройки
TESTING=true
ENVIRONMENT=test
DATABASE_URL=sqlite+aiosqlite:///./test.db

# Отключаем внешние сервисы
TRACING_ENABLED=false
ENABLE_ALERTS=false
TELEGRAM_BOTS_ENABLED=false

# Ускоряем тесты
ACCESS_TOKEN_EXPIRE_MINUTES=5
CACHE_TTL=10
```

## 📁 Файлы конфигурации

### Структура файлов

```
project/
├── .env                    # Основная конфигурация
├── .env.example           # Пример конфигурации
├── .env.development       # Разработка
├── .env.staging           # Staging
├── .env.production        # Production
├── .env.test              # Тестирование
├── telegram.env.example   # Telegram боты
└── websocket.env.example  # WebSocket/SSE
```

### Приоритет загрузки

1. Переменные окружения системы
2. `.env.{ENVIRONMENT}` (например, `.env.production`)
3. `.env.local`
4. `.env`

## 🔍 Валидация переменных

Все переменные окружения валидируются при запуске приложения через Pydantic Settings. Ошибки валидации отображаются с помощью SafeModel с подробным описанием проблем.

### Обязательные переменные в production

- `SECRET_KEY` - должен быть длинным и уникальным
- `POSTGRES_PASSWORD` - надежный пароль для БД
- `REDIS_PASSWORD` - пароль для Redis (если используется)
- `RABBITMQ_PASSWORD` - пароль для RabbitMQ (если используется)

### Рекомендации по безопасности

1. **Никогда не коммитьте** файлы `.env` в систему контроля версий
2. Используйте **разные секретные ключи** для каждого окружения
3. **Ротируйте ключи** регулярно в production
4. Используйте **менеджеры секретов** (HashiCorp Vault, AWS Secrets Manager)
5. **Ограничивайте доступ** к файлам конфигурации (chmod 600)

## 🧪 Тестирование конфигурации

```bash
# Проверить валидность конфигурации
python -c "from core.config import get_settings; print(get_settings())"

# Проверить подключение к БД
python -c "from core.database import test_connection; asyncio.run(test_connection())"

# Проверить все сервисы
python -m src.cli check-services
```

## 📚 Связанная документация

- [README.md](../README.md) - Основная документация
- [APPS_STRUCTURE.md](APPS_STRUCTURE.md) - Структура приложений
- [tests/README.md](README_tests.md) - Документация по тестированию
- [docker-compose.yml](docker-compose.yml) - Docker конфигурация
