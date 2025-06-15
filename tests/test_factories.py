"""
Тесты фабрик и API клиента.
"""

import pytest


@pytest.mark.factories
async def test_user_factory_creates_valid_user(user_factory):
    """Тест создания пользователя через фабрику."""
    user = await user_factory.create()

    assert user.email is not None
    assert user.username is not None
    assert user.full_name is not None
    assert user.is_active is True
    assert user.is_verified is False  # По умолчанию не верифицирован
    assert user.is_superuser is False


@pytest.mark.factories
async def test_verified_user_factory(verified_user_factory):
    """Тест создания верифицированного пользователя."""
    user = await verified_user_factory.create()

    assert user.is_verified is True
    assert user.email_verified_at is not None
    assert user.is_active is True


@pytest.mark.factories
async def test_admin_user_factory(admin_user_factory):
    """Тест создания администратора."""
    admin = await admin_user_factory.create()

    assert admin.is_superuser is True
    assert admin.is_verified is True
    assert admin.is_active is True
    assert "admin_" in admin.email
    assert "admin_" in admin.username


@pytest.mark.factories
async def test_refresh_token_factory_with_user(refresh_token_factory):
    """Тест создания refresh токена с пользователем."""
    token = await refresh_token_factory.create()

    assert token.jti is not None
    assert token.expires_at is not None
    assert token.is_revoked is False
    assert token.user is not None
    assert token.user.email is not None
    assert token.user_agent is not None
    assert token.ip_address is not None


@pytest.mark.integration
async def test_api_client_with_user_auth(api_client, verified_user):
    """Тест API клиента с аутентификацией пользователя."""
    # Аутентифицируем пользователя
    await api_client.force_auth(verified_user)

    # Получаем URL для тестового эндпоинта
    url = api_client.url_for("current_user")

    # Выполняем запрос к защищенному эндпоинту
    response = await api_client.get(url)

    # Проверяем успешный ответ
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == verified_user.email
    assert data["username"] == verified_user.username
    assert data["is_verified"] is True


@pytest.mark.integration
async def test_api_client_user_creation_flow(api_client, test_user_data):
    """Тест полного флоу создания пользователя через API."""
    # Регистрация пользователя
    register_url = api_client.url_for("register")
    register_response = await api_client.post(register_url, json=test_user_data.model_dump())

    assert register_response.status_code == 201
    register_data = register_response.json()
    assert register_data["email"] == test_user_data.email
    assert register_data["username"] == test_user_data.username

    # Логин пользователя
    login_url = api_client.url_for("login")
    login_data = {"email": test_user_data.email, "password": test_user_data.password}
    login_response = await api_client.post(login_url, json=login_data)

    assert login_response.status_code == 200
    tokens = login_response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"


@pytest.mark.integration
async def test_multiple_users_creation(api_client, user_factory):
    """Тест создания множественных пользователей."""
    users = []

    # Создаем 3 пользователей через фабрику
    for i in range(3):
        user = await user_factory.create()
        users.append(user)

    # Проверяем, что все пользователи уникальны
    emails = [user.email for user in users]
    usernames = [user.username for user in users]

    assert len(set(emails)) == 3  # Все email уникальны
    assert len(set(usernames)) == 3  # Все username уникальны

    # Проверяем, что можем аутентифицироваться под каждым
    for user in users:
        await api_client.force_auth(user)

        url = api_client.url_for("current_user")
        response = await api_client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == user.email
