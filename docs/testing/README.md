# Система тестирования

Документация по тестированию для проекта Blank FastAPI Projects.

## Структура тестов

Тесты организованы согласно структуре проекта:

```
tests/
├── apps/                 # Тесты приложений
│   ├── auth/            # Тесты аутентификации
│   ├── users/           # Тесты пользователей
│   └── base/            # Тесты базовых компонентов
├── core/                # Тесты ядра системы
│   ├── messaging/       # Тесты системы сообщений
│   ├── realtime/        # Тесты WebSocket/SSE
│   ├── streaming/       # Тесты стриминга
│   ├── telegram/        # Тесты Telegram ботов
│   ├── migrations/      # Тесты миграций
│   └── taskiq/          # Тесты очередей
├── tools/               # Тесты инструментов
├── e2e/                 # End-to-end тесты
├── factories/           # Фабрики тестовых данных
├── mocking/             # Моки и стабы
├── performance/         # Тесты производительности
└── reports/             # Отчеты о тестировании

```

## Конфигурация тестов

### conftest.py

Главный файл конфигурации pytest содержит:

- **Асинхронные фикстуры SQLite** для тестирования БД
- **Фикстуры FastAPI** для тестирования API
- **HTTP клиенты** для интеграционных тестов
- **Вспомогательные методы** для создания тестовых данных

### Ключевые фикстуры

```python
@pytest_asyncio.fixture(scope="session")
async def db_session() -> AsyncSession:
    """Асинхронная сессия SQLite для тестов."""

@pytest.fixture
def app() -> FastAPI:
    """FastAPI приложение для тестов."""

@pytest_asyncio.fixture
async def async_client(app) -> AsyncClient:
    """Асинхронный HTTP клиент."""
```

## Типы тестов

### 1. Модульные тесты (Unit Tests)

- Тестируют отдельные функции и классы
- Используют моки для изоляции
- Быстрые и независимые

### 2. Интеграционные тесты (Integration Tests)

- Тестируют взаимодействие компонентов
- Используют тестовую БД
- Проверяют API endpoints

### 3. End-to-End тесты (E2E Tests)

- Тестируют полные пользовательские сценарии
- Используют реальные зависимости
- Проверяют работу всей системы

### 4. Тесты производительности

- Нагрузочные тесты
- Тесты времени отклика
- Профилирование кода

## Запуск тестов

### Все тесты

```bash
make test
# или
python -m pytest tests/
```

### Конкретные модули

```bash
# Тесты аутентификации
python -m pytest tests/apps/auth/

# Тесты realtime
python -m pytest tests/core/realtime/

# Тесты с покрытием
python -m pytest tests/ --cov=src --cov-report=html
```

### Параллельный запуск

```bash
# С pytest-xdist
python -m pytest tests/ -n auto
```

## Маркеры тестов

```python
@pytest.mark.asyncio     # Асинхронные тесты
@pytest.mark.auth        # Тесты аутентификации
@pytest.mark.users       # Тесты пользователей
@pytest.mark.realtime    # Тесты realtime
@pytest.mark.telegram    # Тесты Telegram
@pytest.mark.slow        # Медленные тесты
@pytest.mark.integration # Интеграционные тесты
```

## Моки и стабы

### Библиотеки

- **pytest-httpx** - Мокирование HTTP запросов
- **responses** - Мокирование внешних API
- **pytest-mock** - Универсальные моки

### Примеры

```python
# Мокирование внешнего API
@responses.activate
def test_external_api():
    responses.add(
        responses.GET,
        "https://api.example.com/data",
        json={"key": "value"},
        status=200
    )

# Мокирование с pytest-mock
def test_service_method(mocker):
    mock_service = mocker.patch("app.services.SomeService")
    mock_service.method.return_value = "test_result"
```

## Фабрики данных

### Factory Boy

```python
class UserFactory(factory.Factory):
    class Meta:
        model = User

    email = factory.Faker("email")
    username = factory.Faker("user_name")
    full_name = factory.Faker("name")
```

### Mixer

```python
from mixer.backend.sqlalchemy import Mixer

mixer = Mixer(session=db_session, commit=True)
user = mixer.blend(User, email="test@example.com")
```

## Тестирование AsyncIO

### Особенности

- Используем `pytest-asyncio`
- Фикстуры должны быть async
- Правильная работа с event loop

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result == expected_value
```

## Тестирование WebSocket

```python
@pytest.mark.asyncio
async def test_websocket_connection():
    async with websockets.connect("ws://localhost:8000/ws") as websocket:
        await websocket.send("test message")
        response = await websocket.recv()
        assert response == "expected response"
```

## Тестирование Telegram ботов

```python
@pytest.mark.telegram
async def test_telegram_command():
    # Мокируем Telegram API
    with patch("aiogram.Bot.send_message") as mock_send:
        await handle_start_command(message)
        mock_send.assert_called_once()
```

## Отчеты и покрытие

### HTML отчеты

```bash
python -m pytest tests/ --cov=src --cov-report=html
```

### Покрытие кода

- Минимальное покрытие: 80%
- Исключения: миграции, настройки
- Отчеты сохраняются в `htmlcov/`

## Непрерывная интеграция

### GitHub Actions

```yaml
- name: Run tests
  run: |
    python -m pytest tests/ \
      --cov=src \
      --cov-report=xml \
      --cov-fail-under=80
```

## Лучшие практики

1. **Изоляция тестов** - каждый тест независим
2. **Понятные имена** - тест должен объяснять что проверяет
3. **Один тест - одна проверка** - не перегружать тесты
4. **Используйте фикстуры** - для переиспользования данных
5. **Мокируйте внешние зависимости** - для стабильности
6. **Группируйте тесты** - используйте классы и маркеры
7. **Документируйте сложные тесты** - добавляйте docstrings

## Отладка тестов

### Полезные флаги

```bash
# Остановиться на первой ошибке
pytest -x

# Подробный вывод
pytest -v

# Показать print statements
pytest -s

# Запустить конкретный тест
pytest tests/apps/auth/test_login.py::test_successful_login
```

### Отладка с pdb

```python
import pdb; pdb.set_trace()  # Точка остановки
```

## Проблемы и решения

### Общие проблемы

1. **Циркулярные импорты** - используйте строковые ссылки
2. **Проблемы с async/await** - правильно используйте pytest-asyncio
3. **Проблемы с БД** - очищайте данные между тестами
4. **Медленные тесты** - используйте моки и фикстуры

### Решения

- Регулярно рефакторить тесты
- Использовать линтеры для тестов
- Следить за покрытием кода
- Автоматизировать запуск тестов
