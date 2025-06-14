"""
Тесты для API роутов аутентификации.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.auth
class TestRegistration:
    """Тесты регистрации пользователей."""

    @pytest.mark.asyncio
    async def test_register_success(self, async_client: AsyncClient, db_session: AsyncSession, helpers):
        """Тест успешной регистрации."""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "NewPassword123!",
            "password_confirm": "NewPassword123!",
        }

        response = await async_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 201
        data = response.json()

        # Проверяем структуру ответа
        assert "user" in data
        assert "tokens" in data

        # Проверяем пользователя
        helpers.assert_user_response(data["user"], "newuser@example.com")

        # Проверяем токены
        helpers.assert_token_response(data["tokens"])

    @pytest.mark.asyncio
    async def test_register_existing_email(self, async_client: AsyncClient, test_user, db_session: AsyncSession):
        """Тест регистрации с существующим email."""
        user_data = {
            "email": "test@example.com",  # Уже существует
            "username": "newuser",
            "full_name": "New User",
            "password": "NewPassword123!",
            "password_confirm": "NewPassword123!",
        }

        response = await async_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "email" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_invalid_password(self, async_client: AsyncClient, db_session: AsyncSession):
        """Тест регистрации с невалидным паролем."""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "weak",  # Слабый пароль
            "password_confirm": "weak",
        }

        response = await async_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_password_mismatch(self, async_client: AsyncClient, db_session: AsyncSession):
        """Тест регистрации с несовпадающими паролями."""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "StrongPassword123!",
            "password_confirm": "DifferentPassword123!",
        }

        response = await async_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 422


@pytest.mark.auth
class TestLogin:
    """Тесты входа в систему."""

    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient, test_user, db_session: AsyncSession, helpers):
        """Тест успешного входа."""
        login_data = {"email": "test@example.com", "password": "TestPassword123!"}

        response = await async_client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 200
        data = response.json()

        # Проверяем структуру ответа
        assert "user" in data
        assert "tokens" in data

        # Проверяем пользователя
        helpers.assert_user_response(data["user"], "test@example.com")

        # Проверяем токены
        helpers.assert_token_response(data["tokens"])

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, async_client: AsyncClient, db_session: AsyncSession):
        """Тест входа с несуществующим email."""
        login_data = {"email": "nonexistent@example.com", "password": "TestPassword123!"}

        response = await async_client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, async_client: AsyncClient, test_user, db_session: AsyncSession):
        """Тест входа с неверным паролем."""
        login_data = {"email": "test@example.com", "password": "WrongPassword123!"}

        response = await async_client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data


@pytest.mark.auth
class TestTokenOperations:
    """Тесты операций с токенами."""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, async_client: AsyncClient, test_user, db_session: AsyncSession, helpers):
        """Тест успешного обновления токена."""
        # Сначала входим в систему
        login_data = {"email": "test@example.com", "password": "TestPassword123!"}

        login_response = await async_client.post("/api/v1/auth/login", json=login_data)
        assert login_response.status_code == 200

        refresh_token = login_response.json()["tokens"]["refresh_token"]

        # Обновляем токен
        refresh_data = {"refresh_token": refresh_token}
        response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)

        assert response.status_code == 200
        data = response.json()

        # Проверяем новые токены
        helpers.assert_token_response(data)

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, async_client: AsyncClient, db_session: AsyncSession):
        """Тест обновления с невалидным токеном."""
        refresh_data = {"refresh_token": "invalid-token"}
        response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_validate_token_success(self, async_client: AsyncClient, auth_headers: dict):
        """Тест валидации токена."""
        response = await async_client.get("/api/v1/auth/validate", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is True
        assert "user_id" in data
        assert "email" in data
        assert data["token_type"] == "access"

    @pytest.mark.asyncio
    async def test_validate_token_invalid(self, async_client: AsyncClient):
        """Тест валидации невалидного токена."""
        headers = {"Authorization": "Bearer invalid-token"}
        response = await async_client.get("/api/v1/auth/validate", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["valid"] is False
        assert "error" in data


@pytest.mark.auth
class TestLogout:
    """Тесты выхода из системы."""

    @pytest.mark.asyncio
    async def test_logout_success(
        self, async_client: AsyncClient, test_user, auth_headers: dict, db_session: AsyncSession
    ):
        """Тест успешного выхода."""
        # Сначала входим в систему для получения refresh токена
        login_data = {"email": "test@example.com", "password": "TestPassword123!"}

        login_response = await async_client.post("/api/v1/auth/login", json=login_data)
        refresh_token = login_response.json()["tokens"]["refresh_token"]

        # Выходим из системы
        logout_data = {"refresh_token": refresh_token}
        response = await async_client.post("/api/v1/auth/logout", json=logout_data, headers=auth_headers)

        assert response.status_code == 204

        # Проверяем, что токен больше нельзя использовать
        refresh_response = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert refresh_response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_all_success(self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession):
        """Тест выхода из всех устройств."""
        response = await async_client.post("/api/v1/auth/logout-all", headers=auth_headers)

        assert response.status_code == 204


@pytest.mark.auth
class TestCurrentUser:
    """Тесты получения информации о текущем пользователе."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, async_client: AsyncClient, auth_headers: dict, test_user, helpers):
        """Тест получения информации о текущем пользователе."""
        response = await async_client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        helpers.assert_user_response(data, "test@example.com")

    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, async_client: AsyncClient):
        """Тест получения информации без токена."""
        response = await async_client.get("/api/v1/auth/me")

        assert response.status_code == 401


@pytest.mark.auth
@pytest.mark.integration
class TestAuthenticationFlow:
    """Интеграционные тесты полного процесса аутентификации."""

    @pytest.mark.asyncio
    async def test_complete_auth_flow(self, async_client: AsyncClient, db_session: AsyncSession, helpers):
        """Тест полного цикла аутентификации."""
        # 1. Регистрация
        user_data = {
            "email": "flowtest@example.com",
            "username": "flowtest",
            "full_name": "Flow Test User",
            "password": "FlowPassword123!",
            "password_confirm": "FlowPassword123!",
        }

        register_response = await async_client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 201

        tokens = register_response.json()["tokens"]

        # 2. Использование access токена
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        me_response = await async_client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200

        # 3. Обновление токена
        refresh_data = {"refresh_token": tokens["refresh_token"]}
        refresh_response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
        assert refresh_response.status_code == 200

        new_tokens = refresh_response.json()

        # 4. Использование нового access токена
        new_headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
        me_response2 = await async_client.get("/api/v1/auth/me", headers=new_headers)
        assert me_response2.status_code == 200

        # 5. Выход из системы
        logout_data = {"refresh_token": new_tokens["refresh_token"]}
        logout_response = await async_client.post("/api/v1/auth/logout", json=logout_data)
        assert logout_response.status_code == 204

    @pytest.mark.asyncio
    async def test_multiple_sessions(self, async_client: AsyncClient, test_user, db_session: AsyncSession):
        """Тест множественных сессий одного пользователя."""
        login_data = {"email": "test@example.com", "password": "TestPassword123!"}

        # Входим с разных "устройств"
        session1 = await async_client.post("/api/v1/auth/login", json=login_data)
        session2 = await async_client.post("/api/v1/auth/login", json=login_data)

        assert session1.status_code == 200
        assert session2.status_code == 200

        tokens1 = session1.json()["tokens"]
        tokens2 = session2.json()["tokens"]

        # Оба токена должны работать
        headers1 = {"Authorization": f"Bearer {tokens1['access_token']}"}
        headers2 = {"Authorization": f"Bearer {tokens2['access_token']}"}

        me1 = await async_client.get("/api/v1/auth/me", headers=headers1)
        me2 = await async_client.get("/api/v1/auth/me", headers=headers2)

        assert me1.status_code == 200
        assert me2.status_code == 200

        # Выходим из всех сессий
        logout_all_response = await async_client.post("/api/v1/auth/logout-all", headers=headers1)
        assert logout_all_response.status_code == 204

        # Проверяем, что все refresh токены аннулированы
        refresh1 = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": tokens1["refresh_token"]})
        refresh2 = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": tokens2["refresh_token"]})

        assert refresh1.status_code == 401
        assert refresh2.status_code == 401
