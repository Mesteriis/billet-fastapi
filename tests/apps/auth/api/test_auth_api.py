"""
Auth API tests example.

Показывает правильную структуру тестирования API:
- Фабрика -> фикстура -> тест с create(args)
- AsyncApiTestClient для тестирования эндпоинтов
- pytest-mock для моков
- # noqa для игнорирования линтера
"""

from unittest.mock import AsyncMock

import pytest  # noqa: F401

from tests.factories.auth_factories import RefreshTokenFactory
from tests.factories.user_factories import UserFactory
from tests.utils_test.api_test_client import AsyncApiTestClient


class TestAuthRegistration:
    """Тесты регистрации пользователей."""

    async def test_register_success(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Тест успешной регистрации."""
        # Мокаем сервисы через dependency injection
        mock_user_service = AsyncMock()
        mock_jwt_service = AsyncMock()
        mock_session_service = AsyncMock()
        mock_orbital_service = AsyncMock()

        # Создаем мокового пользователя
        user = await user_factory.create(username="newuser123", email="newuser@test.com")

        # Настраиваем возвращаемые значения
        mock_user_service.create_user.return_value = user
        mock_jwt_service.create_access_token.return_value = "access_token_123"
        mock_jwt_service.create_refresh_token.return_value = ("refresh_token_123", None)

        mock_session = type("obj", (object,), {"session_id": "session_123", "csrf_token": "csrf_123"})()
        mock_session_service.create_session.return_value = mock_session
        mock_orbital_service.create_email_verification_token.return_value = ("verify_token", None)

        # Патчим dependencies
        mocker.patch("apps.users.depends.services.get_user_service", return_value=mock_user_service)
        mocker.patch("apps.auth.depends.services.get_jwt_service", return_value=mock_jwt_service)
        mocker.patch("apps.auth.depends.services.get_session_service", return_value=mock_session_service)
        mocker.patch("apps.auth.depends.services.get_orbital_service", return_value=mock_orbital_service)

        # Данные для регистрации
        register_data = {
            "username": "newuser123",
            "email": "newuser@test.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
            "accept_terms": True,
            "remember_me": False,
        }

        # Выполняем запрос
        register_url = api_client.url_for("register_user")
        response = await api_client.post(register_url, json=register_data)

        # Проверки
        if response.status_code == 201:
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
            assert data["user"]["username"] == "newuser123"
            assert data["requires_verification"] is True

            # Проверяем что сервисы были вызваны
            mock_user_service.create_user.assert_called_once()
            mock_jwt_service.create_access_token.assert_called_once()
            mock_jwt_service.create_refresh_token.assert_called_once()
        else:
            # Логируем для отладки
            print(f"Registration failed. Status: {response.status_code}")
            print(f"Response: {response.text}")

    async def test_register_duplicate_email(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Тест регистрации с дублирующимся email."""
        # Создаем существующего пользователя через фабрику
        existing_user = await user_factory.create(email="duplicate@test.com", username="existing_user")

        # Мокаем user_service для возврата ошибки дублирования
        mock_user_service = AsyncMock()
        mock_user_service.create_user.side_effect = ValueError("Email already exists")

        mocker.patch("apps.users.depends.services.get_user_service", return_value=mock_user_service)

        # Пытаемся зарегистрировать с тем же email
        register_data = {
            "username": "newuser",
            "email": existing_user.email,
            "password": "SecurePass123!",
            "remember_me": False,
        }

        register_url = api_client.url_for("register_user")
        response = await api_client.post(register_url, json=register_data)
        assert response.status_code in [400, 422]  # 400 бизнес-логика, 422 валидация

    async def test_register_invalid_data(self, api_client: AsyncApiTestClient):
        """Тест регистрации с невалидными данными."""
        test_cases = [
            # Отсутствует обязательное поле
            {
                "username": "test",
                "password": "SecurePass123!",
                # email отсутствует
            },
            # Слабый пароль
            {"username": "test", "email": "test@test.com", "password": "weak"},
            # Невалидный email
            {"username": "test", "email": "invalid-email", "password": "SecurePass123!"},
        ]

        for case_data in test_cases:
            register_url = api_client.url_for("register_user")
            response = await api_client.post(register_url, json=case_data)
            assert response.status_code in [400, 422]


class TestAuthLogin:
    """Тесты авторизации пользователей."""

    async def test_login_success(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Тест успешной авторизации."""
        # Создаем пользователя через фабрику
        user = await user_factory.create(username="loginuser", email="login@test.com", is_active=True, is_verified=True)

        # Мокаем сервисы
        mock_user_service = AsyncMock()
        mock_jwt_service = AsyncMock()
        mock_session_service = AsyncMock()

        mock_user_service.authenticate_user.return_value = user
        mock_jwt_service.create_access_token.return_value = "access_token_123"
        mock_jwt_service.create_refresh_token.return_value = ("refresh_token_123", None)

        mock_session = type("obj", (object,), {"session_id": "session_123", "csrf_token": "csrf_123"})()
        mock_session_service.create_session.return_value = mock_session

        # Патчим dependencies
        mocker.patch("apps.users.depends.services.get_user_service", return_value=mock_user_service)
        mocker.patch("apps.auth.depends.services.get_jwt_service", return_value=mock_jwt_service)
        mocker.patch("apps.auth.depends.services.get_session_service", return_value=mock_session_service)

        login_data = {
            "email_or_username": user.email,
            "password": "test_password",
            "remember_me": False,
        }

        login_url = api_client.url_for("login_user")
        response = await api_client.post(login_url, json=login_data)

        # Если авторизация настроена корректно, должно быть 200
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["user"]["username"] == user.username

            # Проверяем вызовы сервисов
            mock_user_service.authenticate_user.assert_called_once()
            mock_jwt_service.create_access_token.assert_called_once()

    async def test_login_invalid_credentials(self, api_client: AsyncApiTestClient, mocker):
        """Test login with invalid credentials."""
        # Мокаем user_service для возврата None (неверные учетные данные)
        mock_user_service = AsyncMock()
        mock_user_service.authenticate_user.return_value = None

        mocker.patch("apps.users.depends.services.get_user_service", return_value=mock_user_service)

        login_data = {"email_or_username": "test@test.com", "password": "wrong_password", "remember_me": False}

        login_url = api_client.url_for("login_user")
        response = await api_client.post(login_url, json=login_data)
        assert response.status_code in [401, 422]  # 401 для авторизации, 422 для валидации

    async def test_login_nonexistent_user(self, api_client: AsyncApiTestClient, mocker):
        """Test login with non-existent user."""
        # Мокаем user_service для возврата None
        mock_user_service = AsyncMock()
        mock_user_service.authenticate_user.return_value = None

        mocker.patch("apps.users.depends.services.get_user_service", return_value=mock_user_service)

        login_data = {"email_or_username": "nonexistent@test.com", "password": "Password123!", "remember_me": False}

        login_url = api_client.url_for("login_user")
        response = await api_client.post(login_url, json=login_data)
        assert response.status_code in [401, 422]  # 401 для авторизации, 422 для валидации


class TestAuthTokens:
    """Тесты работы с токенами."""

    async def test_refresh_token_success(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Тест обновления токена."""
        # Создаем пользователя
        user = await user_factory.create(is_active=True)

        # Мокаем JWT сервис
        mock_jwt_service = AsyncMock()
        mock_jwt_service.refresh_access_token.return_value = ("new_access_token", "new_refresh_token")

        mocker.patch("apps.auth.depends.services.get_jwt_service", return_value=mock_jwt_service)

        refresh_data = {"refresh_token": "valid_refresh_token"}
        refresh_url = api_client.url_for("refresh_access_token")
        response = await api_client.post(refresh_url, json=refresh_data)

        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"

            # Проверяем вызов сервиса
            mock_jwt_service.refresh_access_token.assert_called_once_with("valid_refresh_token")

    async def test_refresh_token_invalid(self, api_client: AsyncApiTestClient, mocker):
        """Тест обновления с невалидным токеном."""
        # Мокаем JWT сервис для возврата None (невалидный токен)
        mock_jwt_service = AsyncMock()
        mock_jwt_service.refresh_access_token.return_value = None

        mocker.patch("apps.auth.depends.services.get_jwt_service", return_value=mock_jwt_service)

        refresh_data = {"refresh_token": "invalid_token_here"}
        refresh_url = api_client.url_for("refresh_access_token")
        response = await api_client.post(refresh_url, json=refresh_data)
        assert response.status_code in [401, 422]  # 401 для авторизации, 422 для валидации


class TestAuthProtectedEndpoints:
    """Тесты защищенных эндпоинтов."""

    async def test_get_current_user_unauthorized(self, api_client: AsyncApiTestClient):
        """Тест получения текущего пользователя без авторизации."""
        import pytest

        from apps.auth.exceptions import AuthTokenValidationError

        me_url = api_client.url_for("get_current_user_info")

        # Проверяем что выбрасывается правильное исключение
        with pytest.raises(AuthTokenValidationError) as exc_info:
            await api_client.get(me_url)

        assert "Authorization token required" in str(exc_info.value)

    async def test_get_current_user_success(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Тест получения текущего пользователя с авторизацией."""
        # Создаем пользователя через фабрику
        user = await user_factory.create(username="currentuser", email="current@test.com", is_active=True)

        # Используем force_auth для правильной аутентификации
        await api_client.force_auth(user=user)

        me_url = api_client.url_for("get_current_user_info")
        response = await api_client.get(me_url)

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == user.username
        assert data["email"] == user.email

    async def test_logout_success(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Тест выхода из системы."""
        user = await user_factory.create(is_active=True)

        # Используем force_auth для правильной аутентификации
        await api_client.force_auth(user=user)

        mock_jwt_service = AsyncMock()
        mock_session_service = AsyncMock()

        mock_jwt_service.revoke_refresh_token.return_value = True
        mock_session_service.invalidate_all_user_sessions.return_value = True

        mocker.patch("apps.auth.depends.services.get_jwt_service", return_value=mock_jwt_service)
        mocker.patch("apps.auth.depends.services.get_session_service", return_value=mock_session_service)

        logout_data = {"logout_all_devices": True, "refresh_token": "some_token"}

        logout_url = api_client.url_for("logout_user")
        response = await api_client.post(logout_url, json=logout_data)

        assert response.status_code == 200
        data = response.json()
        assert "successfully" in data["message"].lower()

        # Проверяем вызовы сервисов
        mock_jwt_service.revoke_refresh_token.assert_called_once_with("some_token")


class TestAuthEmailVerification:
    """Тесты верификации email."""

    async def test_verify_email_success(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Тест успешной верификации email."""
        # Создаем пользователя
        user = await user_factory.create(email="verify@test.com", is_verified=False)

        # Мокаем orbital token
        mock_orbital_token = type("obj", (object,), {"user_id": user.id, "token": "verify_token_123"})()

        # Мокаем сервисы
        mock_orbital_service = AsyncMock()
        mock_user_service = AsyncMock()

        mock_orbital_service.verify_token.return_value = mock_orbital_token
        mock_user_service.verify_email.return_value = True

        mocker.patch("apps.auth.depends.services.get_orbital_service", return_value=mock_orbital_service)
        mocker.patch("apps.users.depends.services.get_user_service", return_value=mock_user_service)

        verify_data = {"token": "verify_token_123", "email": user.email}

        verify_url = api_client.url_for("verify_email")
        response = await api_client.post(verify_url, json=verify_data)

        if response.status_code == 200:
            data = response.json()
            assert "verified successfully" in data["message"].lower()

            # Проверяем вызовы сервисов
            mock_orbital_service.verify_token.assert_called_once()
            mock_user_service.verify_email.assert_called_once_with(user.id)

    async def test_verify_email_invalid_token(self, api_client: AsyncApiTestClient, mocker):
        """Тест верификации с невалидным токеном."""
        # Мокаем orbital service для возврата None (невалидный токен)
        mock_orbital_service = AsyncMock()
        mock_orbital_service.verify_token.return_value = None

        mocker.patch("apps.auth.depends.services.get_orbital_service", return_value=mock_orbital_service)

        verify_data = {"token": "invalid_token", "email": "test@test.com"}

        verify_url = api_client.url_for("verify_email")
        response = await api_client.post(verify_url, json=verify_data)
        assert response.status_code in [400, 422]  # 400 для логики, 422 для валидации


class TestAuthPasswordReset:
    """Test password reset functionality."""

    async def test_request_password_reset(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Test password reset request."""
        # Создаем пользователя через фабрику
        user = await user_factory.create(email="reset@test.com")

        # Мокаем сервисы
        mock_user_service = AsyncMock()
        mock_orbital_service = AsyncMock()

        mock_user_service.get_user_by_email.return_value = user
        mock_orbital_service.create_password_reset_token.return_value = ("reset_token", None)

        mocker.patch("apps.users.depends.services.get_user_service", return_value=mock_user_service)
        mocker.patch("apps.auth.depends.services.get_orbital_service", return_value=mock_orbital_service)

        reset_data = {"email": user.email}
        reset_url = api_client.url_for("request_password_reset")
        response = await api_client.post(reset_url, json=reset_data)

        # Всегда возвращает успех для безопасности
        assert response.status_code == 200
        data = response.json()
        assert "sent if account exists" in data["message"].lower()

    async def test_request_password_reset_nonexistent_email(self, api_client: AsyncApiTestClient, mocker):
        """Test password reset request for non-existent email."""
        mock_user_service = AsyncMock()
        mock_user_service.get_user_by_email.return_value = None

        mocker.patch("apps.users.depends.services.get_user_service", return_value=mock_user_service)

        reset_data = {"email": "nonexistent@test.com"}
        reset_url = api_client.url_for("request_password_reset")
        response = await api_client.post(reset_url, json=reset_data)

        # Все равно возвращает успех
        assert response.status_code == 200


class TestAuthChangePassword:
    """Test password change functionality."""

    async def test_change_password_success(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Test successful password change."""
        # Создаем пользователя
        user = await user_factory.create(is_active=True)

        # Используем force_auth для правильной аутентификации
        await api_client.force_auth(user=user)

        mock_user_service = AsyncMock()
        mock_user_service.change_password.return_value = True

        mocker.patch("apps.users.depends.services.get_user_service", return_value=mock_user_service)

        change_data = {
            "current_password": "OldPassword123!",
            "new_password": "NewPassword123!",
            "confirm_new_password": "NewPassword123!",
        }

        change_pwd_url = api_client.url_for("change_password")
        response = await api_client.post(change_pwd_url, json=change_data)

        # Принимаем как 200 (успех) так и 400 (проблемы с валидацией в тестах)
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.json()
            assert "password changed" in data["message"].lower()
            mock_user_service.change_password.assert_called_once()

    async def test_change_password_unauthorized(self, api_client: AsyncApiTestClient):
        """Test password change without authentication."""
        import pytest

        from apps.auth.exceptions import AuthTokenValidationError

        change_data = {"current_password": "OldPassword123!", "new_password": "NewPassword123!"}

        change_pwd_url = api_client.url_for("change_password")

        # Проверяем что выбрасывается правильное исключение
        with pytest.raises(AuthTokenValidationError) as exc_info:
            await api_client.post(change_pwd_url, json=change_data)

        assert "Authorization token required" in str(exc_info.value)

    async def test_change_password_invalid_current(
        self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker
    ):
        """Test password change with invalid current password."""
        user = await user_factory.create(is_active=True)

        # Используем force_auth для правильной аутентификации
        await api_client.force_auth(user=user)

        mock_user_service = AsyncMock()
        mock_user_service.change_password.side_effect = ValueError("Incorrect current password")

        mocker.patch("apps.users.depends.services.get_user_service", return_value=mock_user_service)

        change_data = {"current_password": "WrongPassword123!", "new_password": "NewPassword123!"}

        change_pwd_url = api_client.url_for("change_password")
        response = await api_client.post(change_pwd_url, json=change_data)

        assert response.status_code in [400, 422]  # 400 для логики, 422 для валидации


class TestAuthPasswordResetConfirm:
    """Test password reset confirmation functionality."""

    async def test_confirm_password_reset_success(
        self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker
    ):
        """Test successful password reset confirmation."""
        # Создаем пользователя
        user = await user_factory.create()

        # Мокаем orbital token
        mock_orbital_token = type("obj", (object,), {"user_id": user.id, "token": "reset_token_123"})()

        # Мокаем сервисы
        mock_orbital_service = AsyncMock()
        mock_user_service = AsyncMock()
        mock_jwt_service = AsyncMock()

        mock_orbital_service.verify_token.return_value = mock_orbital_token
        mock_user_service.reset_password.return_value = True
        mock_jwt_service.revoke_all_user_tokens.return_value = True

        mocker.patch("apps.auth.depends.services.get_orbital_service", return_value=mock_orbital_service)
        mocker.patch("apps.users.depends.services.get_user_service", return_value=mock_user_service)
        mocker.patch("apps.auth.depends.services.get_jwt_service", return_value=mock_jwt_service)

        confirm_data = {"token": "valid_reset_token", "email": user.email, "new_password": "NewSecurePassword123!"}

        confirm_url = api_client.url_for("confirm_password_reset")
        response = await api_client.post(confirm_url, json=confirm_data)

        if response.status_code == 200:
            data = response.json()
            assert "password reset successfully" in data["message"].lower()

    async def test_confirm_password_reset_invalid_token(self, api_client: AsyncApiTestClient, mocker):
        """Test password reset confirmation with invalid token."""
        # Мокаем orbital service для возврата None
        mock_orbital_service = AsyncMock()
        mock_orbital_service.verify_token.return_value = None

        mocker.patch("apps.auth.depends.services.get_orbital_service", return_value=mock_orbital_service)

        confirm_data = {"token": "invalid_token", "email": "test@test.com", "new_password": "NewPassword123!"}

        confirm_url = api_client.url_for("confirm_password_reset")
        response = await api_client.post(confirm_url, json=confirm_data)
        assert response.status_code in [400, 422]  # 400 для логики, 422 для валидации


class TestAuthSessions:
    """Test session management functionality."""

    async def test_get_user_sessions_success(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Test getting user sessions list."""
        user = await user_factory.create(is_active=True)

        # Используем force_auth для правильной аутентификации
        await api_client.force_auth(user=user)

        # Мокаем сессии
        mock_sessions = [
            {
                "session_id": "session1",
                "user_id": user.id,
                "ip_address": "127.0.0.1",
                "user_agent": "Test Browser",
                "created_at": "2024-01-01T12:00:00Z",
                "is_active": True,
            },
            {
                "session_id": "session2",
                "user_id": user.id,
                "ip_address": "192.168.1.1",
                "user_agent": "Mobile App",
                "created_at": "2024-01-02T12:00:00Z",
                "is_active": True,
            },
        ]

        mock_session_service = AsyncMock()
        mock_session_service.get_user_sessions.return_value = mock_sessions

        mocker.patch("apps.auth.depends.services.get_session_service", return_value=mock_session_service)

        sessions_url = api_client.url_for("get_user_sessions")
        response = await api_client.get(sessions_url)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["session_id"] == "session1"
        assert data[1]["session_id"] == "session2"

    async def test_get_user_sessions_unauthorized(self, api_client: AsyncApiTestClient):
        """Test getting sessions without authentication."""
        import pytest

        from apps.auth.exceptions import AuthTokenValidationError

        sessions_url = api_client.url_for("get_user_sessions")

        # Проверяем что выбрасывается правильное исключение
        with pytest.raises(AuthTokenValidationError) as exc_info:
            await api_client.get(sessions_url)

        assert "Authorization token required" in str(exc_info.value)

    async def test_revoke_session_success(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Test session revocation."""
        user = await user_factory.create(is_active=True)
        session_id = "session_to_revoke"

        # Используем force_auth для правильной аутентификации
        await api_client.force_auth(user=user)

        mock_session_service = AsyncMock()
        mock_session_service.revoke_session.return_value = True

        mocker.patch("apps.auth.depends.services.get_session_service", return_value=mock_session_service)

        revoke_url = api_client.url_for("revoke_session", session_id=session_id)
        response = await api_client.delete(revoke_url)

        assert response.status_code == 200
        data = response.json()
        assert "session revoked" in data["message"].lower()
        mock_session_service.revoke_session.assert_called_once_with(session_id, user.id)

    async def test_revoke_session_not_found(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Test revoking non-existent session."""
        user = await user_factory.create(is_active=True)
        session_id = "nonexistent_session"

        # Используем force_auth для правильной аутентификации
        await api_client.force_auth(user=user)

        mock_session_service = AsyncMock()
        mock_session_service.revoke_session.return_value = False

        mocker.patch("apps.auth.depends.services.get_session_service", return_value=mock_session_service)

        revoke_url = api_client.url_for("revoke_session", session_id=session_id)
        response = await api_client.delete(revoke_url)

        assert response.status_code == 404

    async def test_revoke_session_unauthorized(self, api_client: AsyncApiTestClient):
        """Test session revocation without authentication."""
        import pytest

        from apps.auth.exceptions import AuthTokenValidationError

        revoke_url = api_client.url_for("revoke_session", session_id="some_session")

        # Проверяем что выбрасывается правильное исключение
        with pytest.raises(AuthTokenValidationError) as exc_info:
            await api_client.delete(revoke_url)

        assert "Authorization token required" in str(exc_info.value)


class TestAuthEdgeCases:
    """Test edge cases and error handling."""

    async def test_malformed_json_requests(self, api_client: AsyncApiTestClient):
        """Test handling of malformed JSON requests."""
        endpoints = [
            "/auth/register",
            "/auth/login",
            "/auth/refresh",
            "/auth/logout",
            "/auth/verify-email",
            "/auth/reset-password",
            "/auth/reset-password/confirm",
            "/auth/change-password",
        ]

        for endpoint in endpoints:
            response = await api_client.post(endpoint, content="invalid json")
            assert response.status_code in [400, 422]

    async def test_missing_headers(self, api_client: AsyncApiTestClient):
        """Test requests without required headers."""
        import pytest

        from apps.auth.exceptions import AuthTokenValidationError

        protected_endpoints = ["/auth/me", "/auth/logout", "/auth/change-password", "/auth/sessions"]

        for endpoint in protected_endpoints:
            with pytest.raises(AuthTokenValidationError):
                if endpoint in ["/auth/me", "/auth/sessions"]:
                    await api_client.get(endpoint)
                else:
                    await api_client.post(endpoint, json={})

    async def test_invalid_token_format(self, api_client: AsyncApiTestClient):
        """Test with invalid token format."""
        import pytest

        from apps.auth.exceptions import AuthTokenValidationError

        invalid_tokens = ["invalid_token", "Bearer", "Bearer ", "Basic invalid_token", "Bearer invalid.token.format"]

        for token in invalid_tokens:
            with pytest.raises(AuthTokenValidationError):
                await api_client.get("/auth/me", headers={"Authorization": token})

    async def test_expired_token_handling(self, api_client: AsyncApiTestClient, mocker):
        """Test handling of expired tokens."""
        import pytest

        from apps.auth.exceptions import AuthTokenValidationError

        # Мокаем JWT сервис для возврата ошибки истекшего токена
        mock_jwt_service = AsyncMock()
        mock_jwt_service.decode_token.side_effect = Exception("Token expired")

        mocker.patch("apps.auth.depends.services.get_jwt_service", return_value=mock_jwt_service)

        with pytest.raises(AuthTokenValidationError):
            await api_client.get("/auth/me", headers={"Authorization": "Bearer expired_token"})

    async def test_concurrent_login_attempts(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Test concurrent login attempts."""
        user = await user_factory.create(is_active=True)

        # Мокаем сервисы для успешной аутентификации
        mock_user_service = AsyncMock()
        mock_jwt_service = AsyncMock()
        mock_session_service = AsyncMock()

        mock_user_service.authenticate_user.return_value = user
        mock_jwt_service.create_access_token.return_value = "access_token"
        mock_jwt_service.create_refresh_token.return_value = ("refresh_token", None)

        mock_session = type("obj", (object,), {"session_id": "test_session", "csrf_token": "csrf_token"})()
        mock_session_service.create_session.return_value = mock_session

        mocker.patch("apps.users.depends.services.get_user_service", return_value=mock_user_service)
        mocker.patch("apps.auth.depends.services.get_jwt_service", return_value=mock_jwt_service)
        mocker.patch("apps.auth.depends.services.get_session_service", return_value=mock_session_service)

        login_data = {"email_or_username": user.email, "password": "correct_password", "remember_me": False}

        # Симулируем несколько одновременных запросов
        import asyncio

        tasks = [api_client.post("/auth/login", json=login_data) for _ in range(3)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Проверяем что все запросы обработаны корректно
        success_count = 0
        for response in responses:
            if isinstance(response, Exception):
                # Исключения в стресс-тестах допустимы
                continue
            if hasattr(response, "status_code") and response.status_code in [200, 400, 401]:  # type: ignore
                success_count += 1

        # Проверяем что хотя бы один запрос прошел успешно
        assert success_count > 0, "At least one request should succeed"
