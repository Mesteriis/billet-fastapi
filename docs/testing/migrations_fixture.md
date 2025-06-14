# Фикстура миграций для тестов

## Обзор

Фикстура `setup_test_database` автоматически проверяет наличие миграций и применяет их к временной SQLite базе данных для тестов. Это гарантирует, что тестовая схема БД соответствует продакшн схеме.

## Основные возможности

### 1. Проверка наличия миграций

Фикстура проверяет наличие файлов миграций в `migrations/versions/`. Если миграции не найдены, тесты завершаются с понятной ошибкой:

```
❌ МИГРАЦИИ НЕ НАЙДЕНЫ!

Перед запуском тестов необходимо создать миграции:

1. Убедитесь, что PostgreSQL запущен
2. Создайте миграцию: alembic revision --autogenerate -m 'Initial migration'
3. Проверьте созданную миграцию в migrations/versions/
4. Запустите тесты снова

Это гарантирует, что тестовая БД соответствует продакшн схеме.
```

### 2. Автоматическое создание тестовой БД

- Создает временную SQLite базу данных
- Применяет все миграции к тестовой БД
- Проверяет корректность создания таблиц
- Автоматически очищает ресурсы после тестов

### 3. Переопределение настроек

Фикстура временно переопределяет настройки подключения к БД для использования SQLite вместо PostgreSQL.

## Использование

### Базовое использование с сессией БД

```python
import pytest
from sqlalchemy import text

@pytest.mark.integration
async def test_user_creation(migration_db_session):
    """Тест создания пользователя с применением миграций."""
    # Проверяем, что таблица users существует
    result = await migration_db_session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    )
    assert result.fetchone() is not None

    # Создаем пользователя
    from apps.users.models import User
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password"
    )
    migration_db_session.add(user)
    await migration_db_session.commit()

    # Проверяем, что пользователь создан
    result = await migration_db_session.execute(
        text("SELECT COUNT(*) FROM users WHERE email = 'test@example.com'")
    )
    assert result.scalar() == 1
```

### Использование с API клиентом

```python
import pytest

@pytest.mark.integration
async def test_user_registration_api(migration_api_client):
    """Тест регистрации пользователя через API с миграциями."""
    # Данные для регистрации
    user_data = {
        "email": "newuser@example.com",
        "username": "newuser",
        "password": "securepassword123",
        "full_name": "New User"
    }

    # Отправляем запрос на регистрацию
    response = await migration_api_client.post(
        migration_api_client.url_for("register"),
        json=user_data
    )

    # Проверяем успешную регистрацию
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["username"] == user_data["username"]
```

### Использование с аутентификацией

```python
import pytest

@pytest.mark.integration
async def test_protected_endpoint(migration_api_client):
    """Тест защищенного endpoint с аутентификацией."""
    # Создаем и аутентифицируем пользователя
    user = await migration_api_client.force_auth(
        email="admin@example.com",
        is_superuser=True
    )

    # Делаем запрос к защищенному endpoint
    response = await migration_api_client.get(
        migration_api_client.url_for("get_current_user")
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@example.com"
    assert data["is_superuser"] is True
```

## Доступные фикстуры

### `setup_test_database`

Основная фикстура session-уровня, которая:

- Проверяет наличие миграций
- Создает временную SQLite БД
- Применяет миграции
- Переопределяет настройки БД

### `migration_db_session`

Предоставляет async сессию БД с применением миграций:

```python
async def test_database_operations(migration_db_session):
    # Используйте migration_db_session для операций с БД
    pass
```

### `migration_api_client`

Предоставляет API клиент с настроенной БД из миграций:

```python
async def test_api_endpoints(migration_api_client):
    # Используйте migration_api_client для тестирования API
    pass
```

## Создание миграций

Перед запуском тестов убедитесь, что миграции созданы:

```bash
# 1. Запустите PostgreSQL (для создания миграций)
docker run -d --name postgres -e POSTGRES_DB=mango_msg -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:15-alpine

# 2. Создайте миграцию
alembic revision --autogenerate -m "Initial migration"

# 3. Проверьте созданную миграцию
ls migrations/versions/

# 4. Запустите тесты
pytest tests/ -v
```

## Преимущества

1. **Соответствие продакшн схеме**: Тестовая БД создается из тех же миграций, что и продакшн
2. **Автоматическая проверка**: Фикстура заставляет разработчика создать миграции
3. **Изоляция тестов**: Каждый тест получает чистую БД
4. **Производительность**: SQLite быстрее PostgreSQL для тестов
5. **Простота использования**: Достаточно добавить фикстуру в параметры теста

## Устранение неполадок

### Ошибка "МИГРАЦИИ НЕ НАЙДЕНЫ"

Создайте миграции как описано выше.

### Ошибка подключения к PostgreSQL при создании миграций

Убедитесь, что PostgreSQL запущен и доступен на порту 5432.

### Предупреждения о незакрытых соединениях

Это нормально для тестов - SQLite соединения автоматически закрываются при завершении процесса.

## Интеграция с существующими тестами

Фикстуры миграций совместимы с существующими тестами. Просто замените:

```python
# Старый способ
async def test_something(async_session):
    pass

# Новый способ с миграциями
async def test_something(migration_db_session):
    pass
```

Для API тестов:

```python
# Старый способ
async def test_api(api_client):
    pass

# Новый способ с миграциями
async def test_api(migration_api_client):
    pass
```
