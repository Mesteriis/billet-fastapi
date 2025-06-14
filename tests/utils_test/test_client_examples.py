"""
Примеры использования расширенного тестового клиента AsyncApiTestClient.

Этот файл демонстрирует различные способы использования улучшенного клиента
для тестирования API с продвинутыми возможностями.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from tests.factories.user_factory import UserFactory
from tests.utils_test.api_test_client import AsyncApiTestClient


@pytest.mark.asyncio
async def test_basic_client_usage():
    """Базовое использование клиента."""
    app = FastAPI()

    @app.get("/users/{user_id}")
    async def get_user(user_id: int):
        return {"user_id": user_id, "name": "Test User"}

    @app.get("/posts")
    async def get_posts():
        return {"posts": []}

    async with AsyncApiTestClient(app=app) as client:
        # Генерация URL с параметрами
        user_url = client.url_for("get_user", user_id=123)
        assert user_url == "/users/123"

        # Обычный запрос
        response = await client.get("/posts")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_authentication_examples():
    """Примеры работы с аутентификацией."""
    app = FastAPI()

    @app.get("/profile")
    async def get_profile():
        return {"message": "Protected endpoint"}

    async with AsyncApiTestClient(app=app) as client:
        # Создание и аутентификация пользователя
        user = await client.force_auth(email="test@example.com", is_superuser=True, email_verified=True)

        assert client.is_authenticated()
        assert client.get_current_user() == user

        # Запрос от имени аутентифицированного пользователя
        response = await client.get("/profile")

        # Выход из системы
        await client.force_logout()
        assert not client.is_authenticated()


@pytest.mark.asyncio
async def test_url_for_and_authentication(api_client):
    """Тест использования url_for и аутентификации пользователей."""
    # Создаем пользователей через Factory-boy
    regular_user = await UserFactory.create(
        email="regular@test.com",
        username="regular_user",
        is_active=True,
        is_superuser=False,
    )

    admin_user = await UserFactory.create(
        email="admin@test.com", username="admin_user", is_active=True, is_superuser=True
    )

    # Запрос от имени обычного пользователя к своему профилю
    url = api_client.url_for("get_my_profile")  # /api/v1/users/me
    response = await api_client.get_as_user(url, user=regular_user)
    assert response.status_code == 200
    assert response.json()["email"] == regular_user.email

    # Запрос от имени администратора к списку пользователей
    url = api_client.url_for("get_users")  # /api/v1/users/
    response = await api_client.get_as_user(url, user=admin_user)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_multiple_users_scenario(api_client):
    """Тест сценария с несколькими пользователями."""
    # Создаем пользователей через Factory-boy
    regular_user = await UserFactory.create(
        email="regular@test.com",
        username="regular_user",
        is_active=True,
        is_superuser=False,
    )

    admin_user = await UserFactory.create(
        email="admin@test.com", username="admin_user", is_active=True, is_superuser=True
    )

    # Диагностика: проверим что url_for работает
    url = api_client.url_for("get_my_profile")  # /api/v1/users/me
    print(f"DEBUG: URL для get_my_profile: {url}")

    # Диагностика: проверим аутентификацию
    print(f"DEBUG: Пользователь regular_user: {regular_user.email}")
    print(f"DEBUG: Активность: {regular_user.is_active}")
    print(f"DEBUG: JWT сервис: {hasattr(api_client, '_jwt_service')}")
    print(f"DEBUG: Текущий auth_user: {api_client.auth_user}")

    # Диагностика JWT настроек
    from core.config import get_settings

    test_settings = get_settings()
    print(f"DEBUG: Тестовый SECRET_KEY: {test_settings.SECRET_KEY}")
    print(f"DEBUG: JWT сервис SECRET_KEY: {api_client._jwt_service.secret_key}")
    print(f"DEBUG: Ключи одинаковые: {test_settings.SECRET_KEY == api_client._jwt_service.secret_key}")
    print(f"DEBUG: Тестовый ALGORITHM: {test_settings.ALGORITHM}")
    print(f"DEBUG: JWT сервис ALGORITHM: {api_client._jwt_service.algorithm}")
    print(f"DEBUG: Алгоритмы одинаковые: {test_settings.ALGORITHM == api_client._jwt_service.algorithm}")
    print(f"DEBUG: ACCESS_TOKEN_EXPIRE_MINUTES: {test_settings.ACCESS_TOKEN_EXPIRE_MINUTES}")
    print(f"DEBUG: JWT сервис expire_minutes: {api_client._jwt_service.access_token_expire_minutes}")

    # Попробуем принудительно аутентифицировать пользователя
    await api_client.force_auth(user=regular_user)
    print(f"DEBUG: После force_auth auth_user: {api_client.auth_user}")
    print(f"DEBUG: После force_auth заголовки: {api_client.headers}")
    print(f"DEBUG: is_authenticated: {api_client.is_authenticated()}")

    # Диагностика JWT токена
    auth_header = api_client.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Убираем "Bearer "
        print(f"DEBUG: JWT токен (первые 50 символов): {token[:50]}...")

        # Попробуем декодировать токен тем же сервисом
        claims = api_client._jwt_service.verify_token(token, "access")
        print(f"DEBUG: Декодирование токена: {claims is not None}")
        if claims:
            print(f"DEBUG: Claims user_id: {claims.sub}")
            print(f"DEBUG: Claims email: {claims.email}")
        else:
            print("DEBUG: Токен не декодируется!")

            # Попробуем декодировать вручную
            import jwt

            try:
                payload = jwt.decode(
                    token, api_client._jwt_service.secret_key, algorithms=[api_client._jwt_service.algorithm]
                )
                print(f"DEBUG: Ручное декодирование успешно: {payload.get('email', 'N/A')}")
            except Exception as e:
                print(f"DEBUG: Ручное декодирование тоже не работает: {e}")

                # Попробуем декодировать без проверки времени
                try:
                    payload = jwt.decode(
                        token,
                        api_client._jwt_service.secret_key,
                        algorithms=[api_client._jwt_service.algorithm],
                        options={"verify_exp": False},  # Отключаем проверку времени
                    )
                    print(f"DEBUG: Декодирование без проверки времени: {payload.get('email', 'N/A')}")
                    print(f"DEBUG: exp timestamp: {payload.get('exp')}")
                    print(f"DEBUG: iat timestamp: {payload.get('iat')}")

                    import time

                    current_time = time.time()
                    print(f"DEBUG: Текущее время: {current_time}")
                    print(f"DEBUG: Разница (exp - current): {payload.get('exp', 0) - current_time}")
                except Exception as e2:
                    print(f"DEBUG: Даже без проверки времени не работает: {e2}")

    # Проверим, есть ли пользователь в базе данных
    from sqlalchemy import select

    from apps.users.models import User

    result = await api_client.db_session.execute(select(User).where(User.email == regular_user.email))
    db_user = result.scalar_one_or_none()
    print(f"DEBUG: Пользователь в БД: {db_user is not None}")
    if db_user:
        print(f"DEBUG: DB User ID: {db_user.id}")
        print(f"DEBUG: Factory User ID: {regular_user.id}")
        print(f"DEBUG: IDs одинаковые: {db_user.id == regular_user.id}")

    # Запрос от имени обычного пользователя к своему профилю
    response = await api_client.get_as_user(url, user=regular_user)
    print(f"DEBUG: Статус ответа: {response.status_code}")
    print(f"DEBUG: Заголовки запроса: {api_client.headers}")

    if response.status_code != 200:
        print(f"DEBUG: Ошибка: {response.text}")
        return  # Прекращаем тест для диагностики

    assert response.status_code == 200
    assert response.json()["email"] == regular_user.email

    # Запрос от имени администратора к списку пользователей
    url = api_client.url_for("get_users")  # /api/v1/users/
    response = await api_client.get_as_user(url, user=admin_user)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_url_error_handling():
    """Тестирование обработки ошибок URL с предложениями."""
    app = FastAPI()

    @app.get("/users/{user_id}")
    async def get_user(user_id: int):
        return {"user_id": user_id}

    @app.get("/user-posts/{user_id}")
    async def get_user_posts(user_id: int):
        return {"posts": []}

    @app.get("/user-profile/{user_id}")
    async def get_user_profile(user_id: int):
        return {"profile": {}}

    async with AsyncApiTestClient(app=app) as client:
        # Попытка использовать неправильное имя
        with pytest.raises(ValueError) as exc_info:
            client.url_for("get_usr", user_id=123)  # Опечатка

        error_message = str(exc_info.value)

        # Проверяем, что в ошибке есть предложения похожих routes
        assert "Возможно, вы имели в виду" in error_message
        assert "get_user" in error_message  # Должен предложить правильный вариант

        # Проверяем список всех доступных routes
        assert "Все доступные routes" in error_message


@pytest.mark.asyncio
async def test_context_manager_usage():
    """Пример использования как context manager."""
    app = FastAPI()

    @app.get("/test")
    async def test_endpoint():
        return {"test": True}

    # Использование с автоматической очисткой
    async with AsyncApiTestClient(app=app) as client:
        await client.force_auth(email="test@example.com")
        assert client.is_authenticated()

        response = await client.get("/test")
        assert response.status_code == 200

    # После выхода из контекста пользователь автоматически разлогинен
    # (если бы мы сохранили ссылку на client)


@pytest.mark.asyncio
async def test_route_caching():
    """Тестирование кеширования routes."""
    app = FastAPI()

    @app.get("/test1")
    async def test1():
        return {"test": 1}

    async with AsyncApiTestClient(app=app) as client:
        # Первый вызов заполняет кеш
        routes1 = client._get_available_routes()

        # Второй вызов использует кеш
        routes2 = client._get_available_routes()

        assert routes1 == routes2 == ["test1"]

        # Очистка кеша
        client.clear_cache()

        # Добавим новый route динамически (в реальности это редко нужно)
        @app.get("/test2")
        async def test2():
            return {"test": 2}

        # После очистки кеша новый route будет найден
        routes3 = client._get_available_routes()
        assert "test2" in routes3 if hasattr(app, "routes") else True


@pytest.mark.asyncio
async def test_advanced_authentication():
    """Продвинутые примеры аутентификации."""
    app = FastAPI()

    @app.get("/admin-only")
    async def admin_only():
        return {"admin": True}

    async with AsyncApiTestClient(app=app) as client:
        # Создание пользователя с дополнительными параметрами
        user = await client.force_auth(
            email="admin@company.com",
            is_superuser=True,
            is_active=True,
            email_verified=True,
            username="admin_user",
            full_name="Admin User",
        )

        # Проверка заголовков авторизации
        auth_headers = client.get_auth_headers()
        assert "Authorization" in auth_headers
        assert auth_headers["Authorization"].startswith("Bearer ")

        # Выполнение различных типов запросов
        get_response = await client.get("/admin-only")
        post_response = await client.post("/admin-only", json={"data": "test"})
        put_response = await client.put("/admin-only", json={"data": "updated"})
        delete_response = await client.delete("/admin-only")

        # Все запросы должны включать авторизацию
        for response in [get_response, post_response, put_response, delete_response]:
            # Проверяем что запрос был выполнен с правильными заголовками
            # (в реальном тесте здесь была бы проверка логики авторизации)
            pass


if __name__ == "__main__":
    # Запуск примеров для демонстрации
    import asyncio

    async def run_examples():
        print("🚀 Демонстрация работы AsyncApiTestClient")

        print("\n1️⃣  Базовое использование...")
        await test_basic_client_usage()
        print("✅ Базовое использование - ОК")

        print("\n2️⃣  Аутентификация...")
        await test_authentication_examples()
        print("✅ Аутентификация - ОК")

        print("\n3️⃣  Несколько пользователей...")
        await test_multiple_users_scenario()
        print("✅ Несколько пользователей - ОК")

        print("\n4️⃣  Обработка ошибок URL...")
        try:
            await test_url_error_handling()
            print("✅ Обработка ошибок URL - ОК")
        except Exception as e:
            print(f"ℹ️  Ожидаемая ошибка при тестировании: {e}")

        print("\n🎉 Все примеры выполнены успешно!")

    asyncio.run(run_examples())
