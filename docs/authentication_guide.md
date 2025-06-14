# Руководство по аутентификации

## Обзор

Проект поддерживает множественные типы аутентификации для различных сценариев использования:

- **JWT Bearer токены** - основной метод для веб-приложений
- **API ключи** - для внешних сервисов и интеграций
- **WebSocket/SSE аутентификация** - для real-time соединений
- **Опциональная аутентификация** - для публичных endpoints с персонализацией
- **Ролевая авторизация** - система прав доступа

## Типы аутентификации

### 1. JWT Bearer токены

Основной метод аутентификации для пользователей:

```python
# Зависимости
from apps.auth.dependencies import get_current_user, get_current_active_user

@router.get("/protected")
async def protected_endpoint(current_user: User = Depends(get_current_user)):
    return {"user": current_user.email}
```

**Endpoints:**

- `POST /auth/register` - регистрация
- `POST /auth/login` - вход в систему
- `POST /auth/refresh` - обновление токенов
- `POST /auth/logout` - выход из системы
- `GET /auth/validate` - валидация токена

### 2. API ключи

Для внешних сервисов и интеграций:

```python
async def verify_api_key(api_key: str = Query(...)) -> dict:
    # Проверка API ключа
    if api_key not in valid_keys:
        raise HTTPException(status_code=401)
    return valid_keys[api_key]

@router.get("/api/data")
async def api_endpoint(api_info: dict = Depends(verify_api_key)):
    return {"data": "protected"}
```

**Использование:**

- `GET /api/data?api_key=service_key_123`
- `Headers: X-API-Key: api_key_12345`

### 3. WebSocket аутентификация

Для real-time соединений:

```python
from core.realtime.auth import WSAuthenticator

# Получение токена для WebSocket
@router.get("/ws-token")
async def get_ws_token(current_user: User = Depends(get_current_user)):
    ws_token = ws_auth.create_access_token({
        "user_id": str(current_user.id),
        "email": current_user.email
    })
    return {"ws_token": ws_token}
```

**Подключение:**

- `ws://localhost:8000/realtime/ws?token=<ws_token>`
- `Headers: Authorization: Bearer <token>`
- `Headers: X-API-Key: <api_key>`

### 4. Опциональная аутентификация

Для endpoints, работающих с анонимными пользователями:

```python
from apps.auth.dependencies import get_optional_current_user

@router.get("/public")
async def public_endpoint(
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    if current_user:
        return {"content": "personalized", "user": current_user.email}
    return {"content": "public"}
```

### 5. Ролевая авторизация

Система прав доступа:

```python
from apps.auth.dependencies import get_current_superuser, get_current_verified_user

# Только для суперпользователей
@router.get("/admin/users")
async def admin_endpoint(admin: User = Depends(get_current_superuser)):
    return {"users": [...]}

# Только для верифицированных пользователей
@router.get("/verified-only")
async def verified_endpoint(user: User = Depends(get_current_verified_user)):
    return {"premium_content": [...]}
```

## Примеры использования

### Полный цикл аутентификации

```python
# 1. Регистрация
response = await client.post("/auth/register", json={
    "email": "user@example.com",
    "username": "user",
    "password": "SecurePassword123!",
    "password_confirm": "SecurePassword123!",
    "full_name": "User Name"
})

# 2. Вход в систему
response = await client.post("/auth/login", json={
    "email": "user@example.com",
    "password": "SecurePassword123!"
})
tokens = response.json()["tokens"]

# 3. Использование токена
headers = {"Authorization": f"Bearer {tokens['access_token']}"}
response = await client.get("/auth/me", headers=headers)

# 4. Обновление токена
response = await client.post("/auth/refresh", json={
    "refresh_token": tokens["refresh_token"]
})

# 5. Выход из системы
response = await client.post("/auth/logout", json={
    "refresh_token": tokens["refresh_token"]
})
```

### WebSocket с аутентификацией

```python
# Получение токена
response = await client.get("/ws-token", headers=headers)
ws_token = response.json()["ws_token"]

# Подключение к WebSocket
async with websockets.connect(f"ws://localhost:8000/realtime/ws?token={ws_token}") as ws:
    await ws.send(json.dumps({"type": "ping"}))
    response = await ws.recv()
```

## Безопасность

### Лучшие практики

1. **Время жизни токенов:**

   - Access токены: 30 минут
   - Refresh токены: 30 дней
   - WebSocket токены: 1 час

2. **Хранение токенов:**

   - Access токены: память приложения
   - Refresh токены: httpOnly cookies или secure storage

3. **Валидация:**

   - Проверка истечения токенов
   - Проверка отзыва токенов
   - Валидация подписи JWT

4. **Мониторинг:**
   - Логирование попыток входа
   - Отслеживание подозрительной активности
   - Блокировка после множественных неудачных попыток

### Конфигурация

```python
# В settings
JWT_SECRET_KEY = "your-secret-key"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30

# API ключи
WS_API_KEYS = ["api_key_1", "api_key_2"]
WS_API_KEY_HEADER = "X-API-Key"

# WebSocket/SSE
WEBSOCKET_AUTH_REQUIRED = True
SSE_AUTH_REQUIRED = True
WS_JWT_EXPIRE_MINUTES = 60
```

## Тестирование

### Фикстуры

```python
# Тестовый клиент с аутентификацией
@pytest.fixture
async def authenticated_client(api_client):
    await api_client.login_as_user()
    return api_client

@pytest.fixture
async def admin_client(api_client):
    await api_client.login_as_admin()
    return api_client
```

### Примеры тестов

```python
async def test_protected_endpoint(authenticated_client):
    response = await authenticated_client.get("/protected")
    assert response.status_code == 200

async def test_admin_endpoint(admin_client):
    response = await admin_client.get("/admin/users")
    assert response.status_code == 200

async def test_optional_auth(api_client):
    # Без токена
    response = await api_client.get("/public")
    assert response.json()["is_personalized"] is False

    # С токеном
    await api_client.login_as_user()
    response = await api_client.get("/public")
    assert response.json()["is_personalized"] is True
```

## Миграции и база данных

Проект использует умную фикстуру миграций для тестов:

```python
# Автоматическая проверка и применение миграций
@pytest.fixture(scope="session")
async def setup_test_database():
    # Проверяет наличие миграций
    # Создает временную SQLite БД
    # Применяет все миграции
    # Настраивает тестовое окружение
```

**Создание миграций:**

```bash
# Убедитесь, что PostgreSQL запущен
alembic revision --autogenerate -m "Initial migration"

# Запуск тестов (автоматически применит миграции)
pytest
```

## Примеры и документация

- **Примеры кода:** `examples/auth_simple_examples.py`
- **FastAPI endpoints:** `examples/auth_endpoints_examples.py`
- **URL примеры:** `docs/url_for_examples.md`
- **Тесты:** `tests/apps/auth/`

## Заключение

Система аутентификации проекта обеспечивает:

- ✅ Множественные типы аутентификации
- ✅ Безопасность и лучшие практики
- ✅ Гибкость для различных сценариев
- ✅ Полное покрытие тестами
- ✅ Подробную документацию и примеры
- ✅ Автоматическое управление миграциями

Используйте подходящий тип аутентификации для вашего случая использования и следуйте рекомендациям по безопасности.
