# Декораторы изоляции тестов

Полная система декораторов для изоляции тестов от данных других тестов, решающая проблему загрязнения данных между тестами.

## Обзор

Система предоставляет 4 различных стратегии изоляции, каждая с разными компромиссами между скоростью и надежностью:

| Стратегия                   | Скорость | Надежность    | Ресурсы | Применение           |
| --------------------------- | -------- | ------------- | ------- | -------------------- |
| `transaction_isolated_test` | ⚡⚡⚡   | ⭐⭐⭐        | 💚      | Быстрые unit-тесты   |
| `schema_isolated_test`      | ⚡⚡     | ⭐⭐⭐⭐      | 💛      | Интеграционные тесты |
| `database_reset_test`       | ⚡       | ⭐⭐⭐⭐⭐    | 🧡      | Критичные тесты      |
| `complete_isolation_test`   | 🐌       | ⚠️ **ОШИБКИ** | ❤️      | **НЕ РЕКОМЕНДУЕТСЯ** |

## Импорт

```python
from tests.utils_test.isolation_decorators import (
    transaction_isolated_test,
    database_reset_test,
    schema_isolated_test,
    complete_isolation_test,
    isolated_data_context,
)
```

## Стратегии изоляции

### 1. Transaction Isolation (Рекомендуется для большинства тестов)

**Принцип:** Использует PostgreSQL savepoints для создания вложенных транзакций. Все изменения автоматически откатываются.

```python
@transaction_isolated_test(verbose=True)
async def test_user_creation(setup_test_models):
    """Все изменения будут откачены после теста."""
    session = setup_test_models

    user = await UserFactory.create(username="test_user")
    post = await PostFactory.create(title="Test Post", author=user)

    assert user.id is not None
    assert post.author_id == user.id

    # Данные автоматически откатятся
```

**Преимущества:**

- ⚡ Самый быстрый метод (~10-20% накладных расходов)
- 🔄 Автоматический откат всех изменений
- 🛡️ Надежная изоляция через ACID транзакции

**Недостатки:**

- ⚠️ Не работает с DDL операциями (CREATE/DROP TABLE)
- ⚠️ Проблемы с тестами, использующими COMMIT/ROLLBACK

**Когда использовать:**

- Unit-тесты с созданием/изменением данных
- Быстрые тесты репозиториев и сервисов
- Тесты бизнес-логики

### 2. Schema Isolation (Баланс скорости и изоляции)

**Принцип:** Создает отдельную PostgreSQL схему для каждого теста. Полная изоляция с умеренными затратами.

```python
@schema_isolated_test(verbose=True)
async def test_complex_workflow(setup_test_models):
    """Тест выполняется в собственной схеме."""
    session = setup_test_models

    # Создаем сложную структуру данных
    users = await UserFactory.create_batch(5)
    categories = await CategoryFactory.create_batch(3)

    for user in users:
        posts = await PostFactory.create_batch(
            2,
            author=user,
            category=categories[0]
        )

    # Схема будет полностью удалена после теста
```

**Преимущества:**

- 🔒 Полная изоляция - каждый тест в своей схеме
- 🚀 Умеренная скорость (~50-100% накладных расходов)
- ✅ Работает с любыми SQL операциями
- 🧹 Автоматическая очистка всей схемы

**Недостатки:**

- 💾 Больше использует ресурсы БД
- ⏱️ Время на создание/удаление схемы

**Когда использовать:**

- Интеграционные тесты
- Тесты со сложными связями данных
- Тесты с DDL операциями

### 3. Database Reset (Максимальная надежность)

**Принцип:** Полностью удаляет и пересоздает все таблицы перед каждым тестом. 100% гарантия чистоты данных.

```python
@database_reset_test(verbose=True)
async def test_from_scratch(setup_test_models):
    """БД полностью чистая перед тестом."""
    session = setup_test_models

    # Начинаем с абсолютно чистой БД
    admin = await UserFactory.create(
        username="admin",
        is_superuser=True
    )

    # Создаем начальную структуру данных
    setup_data = await create_initial_data(admin)

    # Тест начального состояния системы
    assert_initial_state(setup_data)
```

**Преимущества:**

- 🏆 100% гарантия чистоты данных
- 🧼 Полная очистка всех таблиц и индексов
- 🔄 Сброс всех счетчиков и последовательностей
- ✅ Работает при любых проблемах с изоляцией

**Недостатки:**

- 🐌 Самый медленный (~200-500% накладных расходов)
- 💪 Интенсивное использование ресурсов

**Когда использовать:**

- Критически важные тесты
- Тесты миграций БД
- Тесты, требующие гарантированно чистое состояние
- Дебаг проблем с загрязнением данных

### 4. Complete Isolation ⚠️ **НЕ РЕКОМЕНДУЕТСЯ - ИМЕЕТ ОШИБКИ**

**ВНИМАНИЕ:** Этот декоратор имеет критические проблемы с очисткой схем при прерванных транзакциях.

**Проблемы:**

- 🚫 При ошибке в тесте транзакция прерывается
- 🚫 Нельзя выполнить `SET search_path TO public` в прерванной транзакции
- 🚫 Схемы могут остаться неочищенными
- 🚫 Может привести к загрязнению базы данных

**Вместо `@complete_isolation_test()` используйте:**

```python
# ✅ РЕКОМЕНДУЕТСЯ: для критичных тестов
@database_reset_test(verbose=True)
async def test_critical_workflow(setup_test_models):
    """Надежная изоляция для критичных тестов."""
    session = setup_test_models

    # Создаем сложную структуру данных
    users = await UserFactory.create_batch(10)
    # БД будет полностью очищена после теста
```

**Почему `database_reset_test` лучше:**

- ✅ 100% надежная очистка данных
- ✅ Работает при любых ошибках в тестах
- ✅ Простая и понятная логика
- ✅ Нет проблем с прерванными транзакциями

**Статус:** Декоратор оставлен только для обратной совместимости, но не рекомендуется к использованию.

## Контекстный менеджер

Для частичной изоляции используйте `isolated_data_context`:

```python
async def test_partial_isolation(setup_test_models):
    session = setup_test_models

    # Создаем постоянные данные
    permanent_user = await UserFactory.create(username="permanent")

    # Изолированный блок
    async with isolated_data_context(session, strategy="transaction"):
        # Временные данные
        temp_user = await UserFactory.create(username="temporary")
        temp_posts = await PostFactory.create_batch(3, author=temp_user)

        # Данные доступны только в этом блоке

    # temp_user и temp_posts автоматически удалены
    # permanent_user остался
```

## Обработка ошибок

Все декораторы поддерживают автоматическую очистку при ошибках:

```python
@transaction_isolated_test(cleanup_on_error=True, verbose=True)
async def test_with_error_handling(setup_test_models):
    session = setup_test_models

    user = await UserFactory.create(username="test_user")

    try:
        # Код, который может вызвать ошибку
        risky_operation(user)
    except SomeException:
        # Данные автоматически очищены даже при ошибке
        pass
```

## Параметры декораторов

### Общие параметры

- `cleanup_on_error: bool = True` - Очищать данные при ошибках
- `verbose: bool = False` - Подробное логирование процесса изоляции

### Пример с параметрами

```python
@transaction_isolated_test(
    cleanup_on_error=False,  # Оставить данные при ошибке для дебага
    verbose=True             # Подробные логи
)
async def test_debug_mode(setup_test_models):
    # Тест с отладочной информацией
    pass
```

## Сравнение производительности

Примерные затраты времени на различные стратегии (на основе создания 100 записей):

```python
# Без изоляции
create_100_records()  # ~0.1s

# С декораторами изоляции
@transaction_isolated_test()      # ~0.12s (+20%)
@schema_isolated_test()          # ~0.15s (+50%)
@database_reset_test()           # ~0.3s (+200%)
@complete_isolation_test()       # ~0.5s (+400%)
```

## Рекомендации по использованию

### Для разных типов тестов

1. **Unit-тесты (95% случаев)**

   ```python
   @transaction_isolated_test()
   ```

2. **Интеграционные тесты**

   ```python
   @schema_isolated_test()
   ```

3. **Критичные/E2E тесты**
   ```python
   @database_reset_test()  # ✅ Рекомендуется
   # НЕ используйте @complete_isolation_test() - имеет ошибки!
   ```

### Паттерны использования

#### Параллельное выполнение тестов

```python
@transaction_isolated_test()
async def test_concurrent_safe(setup_test_models):
    """Безопасно для параллельного выполнения."""
    unique_id = uuid.uuid4().hex[:8]

    user = await UserFactory.create(
        username=f"user_{unique_id}",
        email=f"user_{unique_id}@example.com"
    )

    # Каждый тест изолирован от других
```

#### Тестирование миграций

```python
@database_reset_test()
async def test_migration_workflow(setup_test_models):
    """Тест с чистой БД для миграций."""
    # Применяем миграцию
    apply_migration("001_initial")

    # Тестируем результат на чистой БД
    check_migration_result()
```

#### Комплексное тестирование

```python
class TestUserWorkflow:
    @transaction_isolated_test()
    async def test_user_creation(self, setup_test_models):
        """Быстрый тест создания пользователя."""
        pass

    @schema_isolated_test()
    async def test_user_complex_workflow(self, setup_test_models):
        """Сложный workflow с изоляцией."""
        pass

    @database_reset_test()
    async def test_user_system_integration(self, setup_test_models):
        """Полный системный тест."""
        pass
```

## Отладка проблем с изоляцией

### Включение подробного логирования

```python
@transaction_isolated_test(verbose=True)
async def test_with_debug_logs(setup_test_models):
    # Получите подробные логи о процессе изоляции
    pass
```

### Временное отключение очистки для дебага

```python
@transaction_isolated_test(cleanup_on_error=False)
async def test_debug_data_left(setup_test_models):
    # Данные останутся в БД при ошибке для анализа
    pass
```

### Проверка изоляции

```python
async def test_isolation_verification(setup_test_models):
    """Проверяем что изоляция работает корректно."""

    # Тест 1: создаем данные
    async with isolated_data_context(setup_test_models):
        user1 = await UserFactory.create(username="isolated_user")
        assert user1.id is not None

    # Тест 2: данные должны исчезнуть
    async with isolated_data_context(setup_test_models):
        # БД должна быть чистой
        users_count = await count_users(setup_test_models)
        assert users_count == 0
```

## Интеграция с существующими тестами

### Поэтапная миграция

1. **Найдите проблемные тесты**

   ```bash
   # Тесты, которые падают при параллельном запуске
   pytest -n 4 tests/problem_tests/
   ```

2. **Добавьте изоляцию**

   ```python
   # Было
   async def test_user_creation(setup_test_models):
       pass

   # Стало
   @transaction_isolated_test()
   async def test_user_creation(setup_test_models):
       pass
   ```

3. **Проверьте результат**
   ```bash
   # Должны проходить параллельно
   pytest -n 4 tests/fixed_tests/
   ```

### Маркировка тестов

```python
# В pyproject.toml
[tool.pytest.ini_options]
markers = [
    "isolated: tests with data isolation",
    "transaction_isolated: tests with transaction isolation",
    "schema_isolated: tests with schema isolation",
    "database_reset: tests with database reset",
]

# В тестах
@pytest.mark.isolated
@transaction_isolated_test()
async def test_with_marker(setup_test_models):
    pass
```

### Запуск только изолированных тестов

```bash
# Только изолированные тесты
pytest -m "isolated"

# Исключить медленные тесты изоляции
pytest -m "not database_reset"

# Только быстрые изолированные тесты
pytest -m "transaction_isolated"
```

## Лучшие практики

1. **Выбор стратегии по умолчанию**

   - 90%+ тестов: `@transaction_isolated_test()`
   - Сложные тесты: `@schema_isolated_test()`
   - Критичные тесты: `@database_reset_test()`

2. **Комбинирование с фабриками**

   ```python
   @transaction_isolated_test()
   async def test_with_factories(setup_test_models):
       # ✅ Всегда используйте фабрики для создания данных
       user = await UserFactory.create()

       # ❌ Не создавайте данные напрямую
       # user = TestUser(username="test")
   ```

3. **Уникальные данные**

   ```python
   @transaction_isolated_test()
   async def test_unique_data(setup_test_models):
       # ✅ Генерируйте уникальные данные
       unique_id = uuid.uuid4().hex[:8]
       user = await UserFactory.create(username=f"user_{unique_id}")
   ```

4. **Группировка тестов**

   ```python
   class TestUserIsolated:
       """Все тесты этого класса изолированы."""

       @transaction_isolated_test()
       async def test_create_user(self, setup_test_models):
           pass

       @transaction_isolated_test()
       async def test_update_user(self, setup_test_models):
           pass
   ```

## Решение проблем

### Проблема: Медленные тесты

**Решение:** Используйте более быструю стратегию изоляции

```python
# Медленно
@database_reset_test()
async def test_simple_operation(setup_test_models):
    pass

# Быстро
@transaction_isolated_test()
async def test_simple_operation(setup_test_models):
    pass
```

### Проблема: Сохранение данных между тестами

**Решение:** Включите verbose режим для диагностики

```python
@transaction_isolated_test(verbose=True)
async def test_debug_isolation(setup_test_models):
    # Смотрите логи для понимания процесса изоляции
    pass
```

### Проблема: Ошибки с транзакциями

**Решение:** Используйте schema isolation

```python
# Проблемы с транзакциями
@transaction_isolated_test()  # Может не работать

# Решение
@schema_isolated_test()       # Всегда работает
```

### Проблема: Нехватка ресурсов БД

**Решение:** Оптимизируйте стратегии изоляции

```python
# Много ресурсов
@complete_isolation_test()

# Меньше ресурсов, но надежно
@schema_isolated_test()

# Минимум ресурсов
@transaction_isolated_test()
```

## Заключение

Декораторы изоляции решают одну из главных проблем в тестировании - загрязнение данных между тестами. Выбирайте стратегию в зависимости от требований к скорости и надежности:

- **Быстро и надежно:** `@transaction_isolated_test()`
- **Сбалансированно:** `@schema_isolated_test()`
- **Максимально надежно:** `@database_reset_test()` или `@complete_isolation_test()`

Правильное использование декораторов изоляции обеспечит стабильность тестов и возможность параллельного выполнения.
