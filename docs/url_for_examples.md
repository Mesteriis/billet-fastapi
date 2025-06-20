# 🔗 Примеры использования url_for

В проекте используется метод `api_client.url_for()` для получения URL endpoints в тестах. Это обеспечивает типобезопасность и автоматическое обновление URL при изменении роутов.

## 🎯 Основные примеры

### Аутентификация

```python
# Тесты auth endpoints
@pytest.mark.asyncio
async def test_registration(api_client):
    url = api_client.url_for("registration")  # /auth/register
    response = await api_client.post(url, json={
        "email": "test@example.com",
        "username": "testuser",
        "password": "password123"
    })
    assert response.status_code == 201

@pytest.mark.asyncio
async def test_login(api_client):
    url = api_client.url_for("login")  # /auth/login
    response = await api_client.post(url, json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
```

### Пользователи

```python
# Тесты user endpoints
@pytest.mark.asyncio
async def test_get_user_profile(api_client, verified_user):
    await api_client.force_auth(user=verified_user)

    url = api_client.url_for("get_user_profile")  # /users/profile
    response = await api_client.get(url)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_get_user_by_id(api_client, admin_user):
    await api_client.force_auth(user=admin_user)

    url = api_client.url_for("get_user", user_id=123)  # /users/123
    response = await api_client.get(url)
    assert response.status_code == 200
```

### Realtime endpoints

```python
# WebSocket и SSE
@pytest.mark.asyncio
async def test_sse_connection(api_client):
    url = api_client.url_for("sse_endpoint")  # /realtime/events
    response = await api_client.get(url)
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_realtime_send(api_client, verified_user):
    await api_client.force_auth(user=verified_user)

    url = api_client.url_for("send_message")  # /realtime/send
    response = await api_client.post(url, json={
        "message": "Test message",
        "target": "broadcast"
    })
    assert response.status_code == 200
```

## 🔧 Реализация url_for

Метод `url_for()` реализован в `AsyncApiTestClient`:

```python
def url_for(self, name: str, /, **path_params: Any) -> str:
    """
    Генерация URL для заданного имени endpoint с интеллектуальной обработкой ошибок.

    Args:
        name: Имя route функции
        **path_params: Параметры пути

    Returns:
        Сгенерированный URL

    Example:
        client.url_for("get_user", user_id=123)
        client.url_for("auth:login")  # С префиксом роутера
    """
    if not self._app:
        raise ValueError("FastAPI app не инициализировано.")

    try:
        return self._app.url_path_for(name, **path_params)
    except Exception as e:
        # Интеллектуальные предложения похожих routes
        similar_routes = self._find_similar_routes(name, self._get_available_routes())

        error_msg = f"Route '{name}' не найден."
        if similar_routes:
            error_msg += f"\n\nВозможные варианты:"
            for route, similarity in similar_routes[:5]:
                error_msg += f"\n  - {route} (схожесть: {similarity:.2%})"

        raise ValueError(error_msg) from e
```

## 📋 Доступные endpoints

### Auth routes

- `registration` → `/auth/register`
- `login` → `/auth/login`
- `refresh_token` → `/auth/refresh`
- `logout` → `/auth/logout`

### User routes

- `get_user_profile` → `/users/profile`
- `update_user_profile` → `/users/profile`
- `get_user` → `/users/{user_id}`
- `get_users_list` → `/users/`

### Realtime routes

- `sse_endpoint` → `/realtime/events`
- `send_message` → `/realtime/send`
- `broadcast_message` → `/realtime/broadcast`

### Messaging routes

- `send_user_notification` → `/messaging/user-notification`
- `send_admin_notification` → `/messaging/admin-notification`
- `messaging_health` → `/messaging/health`

## 🚨 Обработка ошибок

Если endpoint не найден, `url_for()` предоставляет интеллектуальные предложения:

```python
# Неправильное имя
url = api_client.url_for("registeration")  # Опечатка

# Ошибка:
# Route 'registeration' не найден.
#
# Возможные варианты:
#   - registration (схожесть: 92%)
#   - get_user_profile (схожесть: 35%)
```

## 🧪 Использование в тестах

### Базовый паттерн

```python
@pytest.mark.asyncio
async def test_endpoint(api_client):
    # 1. Получить URL
    url = api_client.url_for("endpoint_name")

    # 2. Аутентификация (если нужна)
    user = await api_client.force_auth()

    # 3. Выполнить запрос
    response = await api_client.post(url, json=data)

    # 4. Проверить результат
    assert response.status_code == 200
```

### С параметрами пути

```python
@pytest.mark.asyncio
async def test_get_user_by_id(api_client):
    user_id = 123
    url = api_client.url_for("get_user", user_id=user_id)
    # URL: /users/123

    response = await api_client.get(url)
    assert response.status_code == 200
```

### Обработка ошибок маршрутизации

```python
@pytest.mark.asyncio
async def test_invalid_route_name(api_client):
    with pytest.raises(ValueError, match="Route 'invalid_route' не найден"):
        api_client.url_for("invalid_route")
```

## 🔍 Отладка routes

Для просмотра всех доступных routes:

```python
# В тестах или отладке
available_routes = api_client._get_available_routes()
print(f"Доступно {len(available_routes)} routes:")
for route in sorted(available_routes):
    print(f"  - {route}")
```

## 💡 Лучшие практики

### ✅ Рекомендуется

```python
# Используйте точные имена функций
url = api_client.url_for("get_user_profile")

# Передавайте параметры через kwargs
url = api_client.url_for("get_user", user_id=user.id)

# Обрабатывайте ошибки
try:
    url = api_client.url_for("endpoint_name")
except ValueError as e:
    pytest.fail(f"Неверное имя endpoint: {e}")
```

### ❌ Избегайте

```python
# Не используйте hardcoded URLs
url = "/users/profile"  # Плохо

# Не игнорируйте ошибки
url = api_client.url_for("wrong_name")  # Может упасть
```

## 🔗 См. также

- [AsyncApiTestClient](../tests/utils_test/api_test_client.py) - полная реализация
- [Тесты аутентификации](../tests/test_auth.py) - примеры использования
- [Тесты пользователей](../tests/test_users.py) - больше примеров
- [Unified Style тесты](../tests/test_unified_style.py) - демонстрация стиля
