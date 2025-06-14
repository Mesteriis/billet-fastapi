# Руководство по логированию в тестах

## Обзор

Система логирования для тестов предназначена для:

- Отключения шумных логеров из внешних библиотек
- Настройки оптимального уровня логирования для тестовой среды
- Предоставления гибких инструментов для отладки тестов
- Автоматической конфигурации через переменные окружения

## Быстрый старт

### Автоматическая настройка

Система автоматически настраивается при импорте:

```python
# Просто импортируйте в своих тестах
from tests.utils_test.logging_config import test_logger

# Используйте готовый логер
test_logger.info("Сообщение в тесте")
```

### Переменные окружения

Управляйте уровнем логирования через переменные окружения:

```bash
# Тихий режим (только ERROR и выше)
export TEST_LOG_LEVEL=quiet
pytest

# Подробный режим (включая DEBUG)
export TEST_LOG_LEVEL=verbose
pytest

# Стандартный режим (INFO и выше)
export TEST_LOG_LEVEL=normal
pytest
```

## Основные функции

### 1. Настройка уровней логирования

```python
from tests.utils_test.logging_config import TestLoggingConfig

# Тихий режим - только критические ошибки
TestLoggingConfig.setup_test_logging(quiet_mode=True)

# Подробный режим - все сообщения включая DEBUG
TestLoggingConfig.setup_test_logging(
    level=logging.DEBUG,
    disable_external=False
)

# Кастомная настройка
TestLoggingConfig.setup_test_logging(
    level=logging.INFO,
    format_string="%(name)s: %(message)s",
    disable_external=True
)
```

### 2. Управление внешними логерами

```python
# Полностью отключить все внешние логеры
TestLoggingConfig.silence_all_external()

# Включить DEBUG для конкретных логеров
TestLoggingConfig.enable_debug_for(['httpx', 'sqlalchemy'])

# Создать логер для тестов
logger = TestLoggingConfig.create_test_logger('my_test')
```

### 3. Быстрые функции

```python
from tests.utils_test.logging_config import (
    setup_quiet_testing,
    setup_verbose_testing,
    setup_normal_testing
)

# Быстрая настройка режимов
setup_quiet_testing()    # Тихий режим
setup_verbose_testing()  # Подробный режим
setup_normal_testing()   # Стандартный режим
```

## Использование в pytest

### Фикстуры

```python
def test_with_quiet_logs(quiet_logger):
    """Тест с временно отключенными внешними логерами."""
    # Внешние логеры отключены только в этом тесте
    pass

def test_with_verbose_logs(verbose_logger):
    """Тест с временно включенным подробным логированием."""
    # DEBUG логирование включено только в этом тесте
    pass

def test_with_log_capture(capture_logs):
    """Тест с захватом логов."""
    logger = get_test_logger('test')
    logger.info("Тестовое сообщение")

    # Проверяем захваченные логи
    assert "Тестовое сообщение" in capture_logs.getvalue()
```

### Маркеры

```python
@pytest.mark.quiet_logs
def test_quiet():
    """Тест с отключенными внешними логерами."""
    pass

@pytest.mark.verbose_logs
def test_verbose():
    """Тест с включенным подробным логированием."""
    pass
```

### Командная строка

```bash
# Запуск с подробным выводом
pytest -v -s

# Запуск в тихом режиме
TEST_LOG_LEVEL=quiet pytest

# Запуск с отключенным захватом вывода
pytest --capture=no
```

## Отключаемые логеры

Система автоматически отключает или понижает уровень следующих логеров:

### HTTP клиенты

- `httpx`, `httpcore`
- `urllib3`, `requests`

### WebSocket

- `websockets` и все подмодули

### FastAPI и связанные

- `fastapi`, `uvicorn`, `starlette`

### Базы данных

- `sqlalchemy` и все подмодули
- `alembic`

### Тестирование

- `pytest`, `_pytest`

### Другие библиотеки

- `pydantic`, `faker`, `factory_boy`
- `passlib`, `jose`, `cryptography`

## Примеры использования

### Базовый тест с логированием

```python
import pytest
from tests.conftest_logging import get_test_logger

class TestMyFeature:
    def test_something(self):
        logger = get_test_logger('my_feature')

        logger.info("Начинаем тест")

        try:
            # Ваш тестовый код
            result = some_function()
            logger.info(f"Результат: {result}")

            assert result == expected_value
            logger.info("Тест прошел успешно")

        except Exception as e:
            logger.error(f"Ошибка в тесте: {e}")
            raise
```

### Тест с AsyncApiTestClient

```python
@pytest.mark.asyncio
async def test_api_with_logging():
    from tests.utils_test.api_test_client import AsyncApiTestClient
    from tests.utils_test.logging_config import TestLoggingConfig

    # Настраиваем тихий режим для API тестов
    TestLoggingConfig.setup_test_logging(quiet_mode=True)

    client = AsyncApiTestClient()

    # Клиент автоматически использует настроенное логирование
    response = await client.get("/api/test")
    assert response.status_code == 200
```

### Отладка конкретного теста

```python
def test_debug_specific_issue():
    from tests.utils_test.logging_config import TestLoggingConfig

    # Включаем подробное логирование только для этого теста
    TestLoggingConfig.enable_debug_for(['sqlalchemy', 'httpx'])

    # Ваш код для отладки
    # Теперь вы увидите все SQL запросы и HTTP вызовы
```

### Производительное тестирование

```python
def test_performance():
    from tests.utils_test.logging_config import setup_quiet_testing

    # Отключаем все логирование для максимальной производительности
    setup_quiet_testing()

    # Ваши производительные тесты
```

## Конфигурация в pyproject.toml

Добавьте настройки в `pyproject.toml`:

```toml
[tool.pytest.ini_options]
# Кастомные маркеры
markers = [
    "quiet_logs: отключить внешние логеры",
    "verbose_logs: включить подробное логирование"
]

# Переменные окружения для тестов
env = [
    "TEST_LOG_LEVEL=normal"
]
```

## Интеграция с CI/CD

### GitHub Actions

```yaml
- name: Run tests (quiet mode)
  run: |
    export TEST_LOG_LEVEL=quiet
    pytest --tb=short

- name: Run tests (verbose mode for debugging)
  if: failure()
  run: |
    export TEST_LOG_LEVEL=verbose
    pytest --tb=long -v
```

### Makefile

```makefile
test-quiet:
	TEST_LOG_LEVEL=quiet pytest

test-verbose:
	TEST_LOG_LEVEL=verbose pytest -v -s

test-debug:
	TEST_LOG_LEVEL=debug pytest -v -s --pdb
```

## Лучшие практики

### 1. Используйте правильный уровень логирования

```python
# ✅ Хорошо
logger.debug("Детальная информация для отладки")
logger.info("Важная информация о ходе теста")
logger.warning("Потенциальная проблема")
logger.error("Ошибка которая не прерывает тест")
logger.critical("Критическая ошибка")

# ❌ Плохо
logger.info("Очень детальная отладочная информация")  # Должно быть DEBUG
logger.error("Обычная информация")  # Должно быть INFO
```

### 2. Создавайте именованные логеры

```python
# ✅ Хорошо
logger = get_test_logger('auth_tests')
logger = get_test_logger('database_migration')

# ❌ Плохо
logger = logging.getLogger(__name__)  # Не использует нашу систему
```

### 3. Используйте контекстную информацию

```python
# ✅ Хорошо
logger.info(f"Тестируем пользователя {user.email}")
logger.error(f"Ошибка при запросе к {endpoint}: {error}")

# ❌ Плохо
logger.info("Тестируем пользователя")
logger.error("Ошибка при запросе")
```

### 4. Настраивайте логирование в начале теста

```python
def test_complex_scenario():
    # Настройка в начале
    TestLoggingConfig.setup_test_logging(level=logging.DEBUG)
    logger = get_test_logger('complex_test')

    # Остальной код теста
    logger.info("Начинаем сложный сценарий")
```

## Устранение проблем

### Проблема: Слишком много логов от внешних библиотек

```python
# Решение: Используйте тихий режим
from tests.utils_test.logging_config import setup_quiet_testing
setup_quiet_testing()
```

### Проблема: Не видно логов от тестируемого кода

```python
# Решение: Включите подробное логирование
from tests.utils_test.logging_config import setup_verbose_testing
setup_verbose_testing()
```

### Проблема: Нужно видеть логи только от конкретной библиотеки

```python
# Решение: Включите DEBUG для конкретных логеров
TestLoggingConfig.enable_debug_for(['sqlalchemy'])
```

### Проблема: Логи не появляются в pytest

```bash
# Решение: Используйте флаг -s
pytest -s

# Или отключите захват
pytest --capture=no
```

## Расширение системы

### Добавление новых шумных логеров

```python
# В logging_config.py
NOISY_LOGGERS = {
    # Существующие логеры...
    'new_library': logging.WARNING,
    'another_noisy_lib': logging.ERROR,
}
```

### Создание кастомных фикстур

```python
@pytest.fixture
def my_custom_logging():
    # Ваша кастомная настройка
    TestLoggingConfig.setup_test_logging(
        level=logging.INFO,
        format_string="[CUSTOM] %(message)s"
    )
    yield
    # Cleanup если нужен
```

Эта система логирования поможет вам эффективно управлять выводом в тестах и быстро находить проблемы при отладке.
