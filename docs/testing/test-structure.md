# Структура тестов проекта

## Общая организация

Тесты организованы по принципу зеркалирования структуры исходного кода:

```
src/                     tests/
├── apps/               ├── apps/
│   ├── auth/          │   ├── auth/
│   ├── users/         │   ├── users/
│   └── base/          │   └── base/
├── core/              ├── core/
│   ├── messaging/     │   ├── messaging/
│   ├── realtime/      │   ├── realtime/
│   ├── streaming/     │   ├── streaming/
│   ├── telegram/      │   ├── telegram/
│   ├── migrations/    │   ├── migrations/
│   └── taskiq/        │   └── taskiq/
└── tools/             └── tools/
```

## Детальная структура

### tests/apps/ - Тесты приложений

#### tests/apps/auth/ - Аутентификация

- `test_auth_service.py` - Тесты сервиса аутентификации
- `test_jwt_tokens.py` - Тесты JWT токенов
- `test_password_hashing.py` - Тесты хеширования паролей
- `test_login_endpoints.py` - Тесты API входа
- `test_registration.py` - Тесты регистрации
- `test_refresh_tokens.py` - Тесты обновления токенов
- `test_permissions.py` - Тесты прав доступа

#### tests/apps/users/ - Пользователи

- `test_user_model.py` - Тесты модели пользователя
- `test_user_repository.py` - Тесты репозитория пользователей
- `test_user_service.py` - Тесты сервиса пользователей
- `test_user_api.py` - Тесты API пользователей
- `test_user_profile.py` - Тесты профиля пользователя
- `test_user_settings.py` - Тесты настроек пользователя

#### tests/apps/base/ - Базовые компоненты

- `test_base_model.py` - Тесты базовой модели
- `test_base_repository.py` - Тесты базового репозитория
- `test_base_service.py` - Тесты базового сервиса
- `test_exceptions.py` - Тесты исключений
- `test_validators.py` - Тесты валидаторов

### tests/core/ - Тесты ядра системы

#### tests/core/messaging/ - Система сообщений

- `test_message_broker.py` - Тесты брокера сообщений
- `test_message_queue.py` - Тесты очереди сообщений
- `test_message_handler.py` - Тесты обработчика сообщений
- `test_message_routing.py` - Тесты маршрутизации сообщений
- `test_message_serialization.py` - Тесты сериализации

#### tests/core/realtime/ - Real-time коммуникации

- `test_websocket_manager.py` - Тесты менеджера WebSocket
- `test_sse_handler.py` - Тесты Server-Sent Events
- `test_connection_pool.py` - Тесты пула соединений
- `test_realtime_models.py` - Тесты моделей real-time
- `test_realtime_routes.py` - Тесты маршрутов real-time

#### tests/core/streaming/ - Стриминг данных

- `test_stream_processor.py` - Тесты процессора потоков
- `test_stream_pipeline.py` - Тесты пайплайна обработки
- `test_stream_transformers.py` - Тесты трансформеров
- `test_stream_aggregators.py` - Тесты агрегаторов

#### tests/core/telegram/ - Telegram боты

- `test_bot_config.py` - Тесты конфигурации ботов
- `test_bot_manager.py` - Тесты менеджера ботов
- `test_message_handlers.py` - Тесты обработчиков сообщений
- `test_command_handlers.py` - Тесты обработчиков команд
- `test_callback_handlers.py` - Тесты callback обработчиков
- `test_middleware.py` - Тесты middleware
- `test_templates.py` - Тесты шаблонов сообщений

#### tests/core/migrations/ - Миграции БД

- `test_database_manager.py` - Тесты менеджера БД
- `test_migration_runner.py` - Тесты запуска миграций
- `test_migration_validator.py` - Тесты валидации миграций
- `test_backup_restore.py` - Тесты бэкапа и восстановления

#### tests/core/taskiq/ - Очереди задач

- `test_task_broker.py` - Тесты брокера задач
- `test_task_scheduler.py` - Тесты планировщика
- `test_task_worker.py` - Тесты воркеров
- `test_task_result.py` - Тесты результатов задач

### tests/tools/ - Тесты инструментов

- `test_class_finder.py` - Тесты поиска классов
- `test_code_generators.py` - Тесты генераторов кода
- `test_validators.py` - Тесты валидаторов
- `test_helpers.py` - Тесты вспомогательных функций

### tests/e2e/ - End-to-End тесты

- `test_user_registration_flow.py` - Полный поток регистрации
- `test_authentication_flow.py` - Полный поток аутентификации
- `test_messaging_flow.py` - Полный поток обмена сообщениями
- `test_realtime_communication.py` - Real-time коммуникации
- `test_telegram_bot_interaction.py` - Взаимодействие с Telegram ботом

### tests/factories/ - Фабрики тестовых данных

- `user_factory.py` - Фабрика пользователей
- `message_factory.py` - Фабрика сообщений
- `auth_factory.py` - Фабрика данных аутентификации
- `telegram_factory.py` - Фабрика Telegram данных

### tests/mocking/ - Моки и стабы

- `auth_mocks.py` - Моки для аутентификации
- `database_mocks.py` - Моки для БД
- `external_api_mocks.py` - Моки внешних API
- `telegram_mocks.py` - Моки Telegram API

### tests/performance/ - Тесты производительности

- `test_api_performance.py` - Производительность API
- `test_database_performance.py` - Производительность БД
- `test_websocket_performance.py` - Производительность WebSocket
- `test_memory_usage.py` - Использование памяти

### tests/reports/ - Отчеты тестирования

- `coverage_reports/` - Отчеты покрытия кода
- `performance_reports/` - Отчеты производительности
- `test_results/` - Результаты тестов

## Соглашения по именованию

### Файлы тестов

- Префикс `test_` для всех файлов тестов
- Имя файла отражает тестируемый модуль: `test_user_service.py`
- Группировка по функциональности: `test_auth_endpoints.py`

### Классы тестов

```python
class TestUserService:
    """Тесты для UserService."""

class TestUserModel:
    """Тесты для модели User."""
```

### Методы тестов

```python
def test_create_user_success(self):
    """Тест успешного создания пользователя."""

def test_create_user_invalid_email(self):
    """Тест создания пользователя с некорректным email."""

def test_login_with_valid_credentials(self):
    """Тест входа с валидными данными."""
```

## Принципы организации

### 1. Зеркалирование структуры

Каждый модуль исходного кода имеет соответствующий тестовый модуль.

### 2. Группировка по функциональности

Тесты группируются по классам и функциональным областям.

### 3. Изоляция тестов

Каждый тест независим и может выполняться отдельно.

### 4. Иерархия сложности

- Unit тесты - самые простые и быстрые
- Integration тесты - средней сложности
- E2E тесты - самые сложные и медленные

### 5. Переиспользование

Общие фикстуры и утилиты выносятся в `conftest.py` и `factories/`.

## Конфигурация по уровням

### conftest.py (корневой)

- Глобальные фикстуры
- Настройки pytest
- Базовые утилиты

### conftest.py (в подпапках)

- Специфичные фикстуры для модуля
- Локальные настройки
- Модульные утилиты

### Пример структуры conftest.py

```python
# tests/conftest.py - глобальный
@pytest.fixture
def db_session():
    """Глобальная фикстура БД."""

# tests/apps/auth/conftest.py - для auth
@pytest.fixture
def auth_service():
    """Фикстура сервиса аутентификации."""

# tests/core/telegram/conftest.py - для telegram
@pytest.fixture
def telegram_bot():
    """Фикстура Telegram бота."""
```

## Зависимости между тестами

### Допустимые зависимости

- От фабрик и утилит
- От глобальных фикстур
- От моков внешних сервисов

### Недопустимые зависимости

- Между конкретными тестами
- От результатов других тестов
- От порядка выполнения

## Маркировка тестов

### По модулям

```python
@pytest.mark.auth      # Тесты аутентификации
@pytest.mark.users     # Тесты пользователей
@pytest.mark.realtime  # Real-time тесты
@pytest.mark.telegram  # Telegram тесты
```

### По типам

```python
@pytest.mark.unit         # Модульные тесты
@pytest.mark.integration # Интеграционные тесты
@pytest.mark.e2e         # End-to-end тесты
@pytest.mark.performance # Тесты производительности
```

### По скорости

```python
@pytest.mark.fast  # Быстрые тесты (< 1с)
@pytest.mark.slow  # Медленные тесты (> 5с)
```

## Лучшие практики структуры

1. **Один тестовый файл на один модуль** исходного кода
2. **Группировка тестов в классы** по тестируемой функциональности
3. **Использование описательных имен** для тестов и классов
4. **Логическая группировка** внутри тестового файла
5. **Выделение общих фикстур** в conftest.py
6. **Использование фабрик** для создания тестовых данных
7. **Изоляция внешних зависимостей** через моки
