# Тестирование

Автономные тесты для FastAPI приложения с использованием [pytest-mock-resources](https://pytest-mock-resources.readthedocs.io/en/latest/quickstart.html) и [pytest-rabbitmq](https://pypi.org/project/pytest-rabbitmq/).

## Структура тестов

```
tests/
├── conftest.py                     # Основные фикстуры
├── test_auth/
│   ├── __init__.py
│   └── test_routes.py             # Тесты API аутентификации
├── test_users/
│   ├── __init__.py
│   └── test_user_routes.py        # Тесты API пользователей
└── README.md                      # Эта документация
```

## Фикстуры

### База данных

- **PostgreSQL**: Автоматически запускается через Docker с помощью `pytest-mock-resources`
- **Миграции**: Применяются автоматически перед каждым тестом
- **Очистка**: База данных очищается после каждого теста

### RabbitMQ

- **Брокер сообщений**: Автоматически запускается через Docker с помощью `pytest-rabbitmq`
- **Очистка**: Очереди очищаются после каждого теста

### Пользователи

- **test_user**: Обычный пользователь для тестов
- **admin_user**: Админ пользователь для тестов
- **auth_headers**: Заголовки аутентификации для API запросов
- **admin_auth_headers**: Заголовки админа для API запросов

## Запуск тестов

### Установка зависимостей

```bash
# Установка основных зависимостей
uv sync

# Установка зависимостей для тестирования
uv sync --group test
```

### Команды запуска

```bash
# Все тесты
make test

# Тесты с покрытием
make test-cov

# Тесты аутентификации
make test-auth

# Тесты пользователей
make test-users

# Интеграционные тесты
make test-integration

# Unit тесты
make test-unit

# Быстрые тесты (без медленных)
make test-fast

# Наблюдение за тестами
make test-watch
```

### Запуск напрямую через pytest

```bash
# Все тесты
uv run pytest -v

# Конкретная группа тестов
uv run pytest -v -m auth
uv run pytest -v -m users
uv run pytest -v -m integration

# Конкретный файл
uv run pytest tests/test_auth/test_routes.py -v

# Конкретный тест
uv run pytest tests/test_auth/test_routes.py::TestRegistration::test_register_success -v
```

## Маркеры тестов

- `@pytest.mark.auth` - Тесты аутентификации
- `@pytest.mark.users` - Тесты пользователей
- `@pytest.mark.integration` - Интеграционные тесты
- `@pytest.mark.unit` - Unit тесты
- `@pytest.mark.slow` - Медленные тесты
- `@pytest.mark.mocked` - Тесты с моками
- `@pytest.mark.performance` - Тесты производительности
- `@pytest.mark.e2e` - E2E тесты
- `@pytest.mark.factory` - Тесты фабрик

## Автономность тестов

Все тесты полностью автономны и не требуют внешних сервисов:

1. **PostgreSQL** - Автоматически запускается в Docker контейнере
2. **RabbitMQ** - Автоматически запускается в Docker контейнере
3. **Redis** - Мокируется или эмулируется
4. **Email/SMS** - Мокируются

## Структура тестов

### Тесты аутентификации (test_auth/)

#### TestRegistration

- `test_register_success` - Успешная регистрация
- `test_register_existing_email` - Регистрация с существующим email
- `test_register_invalid_password` - Невалидный пароль
- `test_register_password_mismatch` - Несовпадающие пароли

#### TestLogin

- `test_login_success` - Успешный вход
- `test_login_invalid_email` - Несуществующий email
- `test_login_invalid_password` - Неверный пароль

#### TestTokenOperations

- `test_refresh_token_success` - Обновление токена
- `test_refresh_token_invalid` - Невалидный refresh токен
- `test_validate_token_success` - Валидация токена
- `test_validate_token_invalid` - Невалидный токен

#### TestLogout

- `test_logout_success` - Выход из системы
- `test_logout_all_success` - Выход из всех устройств

#### TestCurrentUser

- `test_get_current_user_success` - Получение текущего пользователя
- `test_get_current_user_unauthorized` - Без токена

#### TestAuthenticationFlow

- `test_complete_auth_flow` - Полный цикл аутентификации
- `test_multiple_sessions` - Множественные сессии

### Тесты пользователей (test_users/)

#### TestUserProfile

- `test_get_my_profile` - Получение профиля
- `test_update_my_profile` - Обновление профиля
- `test_change_my_password` - Смена пароля

#### TestUserRetrieval

- `test_get_user_by_id` - Получение пользователя по ID
- `test_get_users_list` - Список пользователей
- `test_search_users` - Поиск пользователей

#### TestAdminOperations

- `test_admin_update_user` - Админ обновляет пользователя
- `test_admin_deactivate_user` - Деактивация пользователя
- `test_admin_delete_user_soft` - Мягкое удаление
- `test_admin_delete_user_hard` - Полное удаление

#### TestUserManagementFlow

- `test_complete_user_lifecycle` - Полный жизненный цикл
- `test_user_profile_management` - Управление профилем

## Покрытие кода

Цель: **80%** покрытия кода

```bash
# Отчет в терминале
make test-cov

# HTML отчет
open htmlcov/index.html
```

## Отладка тестов

### Логирование

Логи доступны в консоли во время выполнения тестов.

### Отладка конкретного теста

```bash
uv run pytest tests/test_auth/test_routes.py::TestRegistration::test_register_success -v -s
```

### Использование pdb

```python
import pdb; pdb.set_trace()
```

## Хелперы для тестов

### TestHelpers

Вспомогательный класс с методами:

- `create_test_users()` - Создание тестовых пользователей
- `assert_user_response()` - Проверка структуры ответа пользователя
- `assert_token_response()` - Проверка структуры токенов

### Использование в тестах

```python
async def test_example(helpers):
    # Создаем тестовых пользователей
    users = await helpers.create_test_users(db_session, count=5)

    # Проверяем ответ
    helpers.assert_user_response(response_data, "test@example.com")
    helpers.assert_token_response(token_data)
```

## CI/CD

Тесты интегрированы в CI/CD пайплайн и автоматически запускаются при каждом коммите.

## Расширенное тестирование

### Фабрики данных

В папке `tests/factories/` содержатся фабрики для создания тестовых данных:

#### SQLAlchemy фабрики

- `UserFactory` - создание пользователей в БД
- `AdminUserFactory` - создание администраторов
- `InactiveUserFactory` - создание неактивных пользователей

#### Pydantic фабрики

- `UserCreateFactory` - схемы для создания пользователей
- `UserUpdateFactory` - схемы для обновления пользователей
- `UserResponseFactory` - схемы ответов API

#### Утилиты

```python
# Создание пользователей в БД
users = await create_users_batch(session, count=10)
admin = await create_admin_user(session)

# Создание схем
user_schemas = create_user_schemas_batch(count=5)
```

### Мокирование внешних API

В папке `tests/mocking/` находятся инструменты для мокирования:

#### Основные классы

- `ExternalAPIMocker` - универсальный мокер API
- `TelegramBotMocker` - мокирование Telegram бота
- `MockedAPIResponse` - создание ответов API

#### Фикстуры

```python
@pytest.mark.mocked
async def test_with_mocked_payment(mock_payment_service):
    result = await payment_service.create_payment(amount=1000)
    assert result["status"] == "pending"

@pytest.mark.mocked
async def test_with_mocked_telegram(mock_telegram_bot):
    await mock_telegram_bot.send_message(chat_id=123, text="Test")
    mock_telegram_bot.send_message.assert_called_once()
```

### Performance тестирование

#### Нагрузочные тесты (Locust)

```bash
# Запуск нагрузочных тестов
make test-load

# Веб-интерфейс Locust
locust -f tests/performance/load_tests.py --host http://localhost:8000
```

#### Бенчмарки (pytest-benchmark)

```bash
# Запуск бенчмарков
make test-performance

# С сохранением результатов
pytest -m performance --benchmark-json=reports/benchmark.json
```

#### Классы нагрузочных тестов

- `UserLoadTest` - тестирование пользовательских операций
- `APILoadTest` - общее тестирование API
- `DatabaseLoadTest` - тестирование операций с БД

### E2E тестирование

#### Установка Playwright

```bash
make install-playwright
```

#### Структура E2E тестов

```
tests/e2e/
├── conftest.py          # Фикстуры браузера
├── utils.py             # Хелперы для E2E
├── test_auth_flow.py    # Тесты аутентификации
└── test_user_profile.py # Тесты профиля
```

#### Основные хелперы

- `AuthHelper` - работа с аутентификацией
- `PageHelper` - базовые операции со страницами
- `APIHelper` - мокирование API в браузере
- `NavigationHelper` - навигация по приложению

#### Запуск E2E тестов

```bash
make test-e2e
```

**Подробное руководство**: [E2E_TESTING_GUIDE.md](E2E_TESTING_GUIDE.md)

### Параллельное выполнение

#### pytest-xdist

```bash
# Автоматическое определение количества процессов
make test-parallel

# Явное указание количества процессов
pytest -n 4
```

#### Стратегии распределения

- `--dist=load` - распределение по времени выполнения
- `--dist=each` - каждый тест на каждом воркере
- `--dist=no` - без распределения

### Команды тестирования

#### Основные команды

```bash
make test                # Все тесты
make test-parallel       # Параллельно
make test-fast          # Быстрые тесты
make test-cov           # С покрытием
```

#### По типам

```bash
make test-auth          # Аутентификация
make test-users         # Пользователи
make test-mocked        # С моками
make test-performance   # Производительность
make test-e2e           # E2E тесты
make test-factories     # Фабрики
```

#### Отчеты

```bash
make test-report        # HTML и JSON отчеты
```

### Структура отчетов

```
reports/
├── test_report.html     # HTML отчет pytest
├── test_results.json    # JSON результаты
├── benchmark.json       # Результаты бенчмарков
├── load_test_report.html # Отчет нагрузочных тестов
├── screenshots/         # Скриншоты E2E тестов
└── videos/             # Видео E2E тестов
```

## Лучшие практики

1. **Изоляция тестов** - Каждый тест независим
2. **Очистка данных** - Автоматическая очистка после каждого теста
3. **Meaningful names** - Понятные имена тестов
4. **Arrange-Act-Assert** - Четкая структура тестов
5. **Mocking** - Мокирование внешних зависимостей
6. **Fixtures** - Переиспользование общих настроек
7. **Фабрики данных** - Использование фабрик для создания тестовых объектов
8. **Параллельное выполнение** - Ускорение тестов через параллелизм
9. **Performance мониторинг** - Регулярное измерение производительности
10. **E2E покрытие** - Тестирование критических пользовательских сценариев

## Troubleshooting

### 🔧 Частые проблемы

1. **ImportError: No module named 'src'**

   ```bash
   # Проверьте PYTHONPATH
   export PYTHONPATH="${PYTHONPATH}:${PWD}/src"
   ```

2. **AsyncIO warnings**

   ```python
   # Добавьте в pytest.ini
   asyncio_mode = "auto"
   ```

3. **Моки не работают**

   ```python
   # Проверьте правильность path для patch
   @patch('core.routes.send_email_notification')  # Правильно
   @patch('src.core.tasks.send_email_notification')  # Неправильно
   ```

4. **Тесты медленные**
   ```bash
   # Используйте параллельный запуск
   pytest tests/ -n auto
   ```

## Метрики качества

### 📊 Цели

- **Покрытие кода**: >90%
- **Время выполнения**: <30 секунд
- **Количество тестов**: >100
- **Flaky тесты**: 0%

### 📈 Мониторинг

```bash
# Статистика тестов
pytest tests/ --collect-only -q

# Время выполнения
pytest tests/ --durations=10

# Покрытие по файлам
pytest tests/ --cov=src --cov-report=term-missing
```

---

**Документация обновлена**: 2024-12-19
**Версия**: 1.0.0
**Мaintainer**: TaskIQ Team
