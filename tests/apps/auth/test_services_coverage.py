"""
Тесты для полного покрытия сервисов аутентификации.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.auth.auth_service import AuthService
from apps.auth.jwt_service import JWTService, jwt_service
from apps.auth.models import RefreshToken
from apps.auth.password_service import PasswordService, password_service
from tests.factories.user_factory import create_verified_user, make_user_data


class TestAuthService:
    """Тесты для сервиса аутентификации."""

    @pytest.fixture
    def auth_service(self):
        """Фикстура сервиса аутентификации."""
        return AuthService()

    @pytest.fixture
    def mock_db_session(self):
        """Мокированная сессия БД."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, auth_service, mock_db_session):
        """Тест успешной аутентификации пользователя."""
        # Создаем тестового пользователя
        user_data = make_user_data(email="test@example.com", is_active=True, is_verified=True)
        user = create_verified_user(**user_data)

        with (
            patch.object(auth_service, "_get_user_by_email", return_value=user),
            patch.object(password_service, "verify_password", return_value=True),
        ):
            result = await auth_service.authenticate_user(mock_db_session, "test@example.com", "password123")

            assert result == user

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_credentials(self, auth_service, mock_db_session):
        """Тест аутентификации с неверными данными."""
        user = create_verified_user(email="test@example.com")

        with (
            patch.object(auth_service, "_get_user_by_email", return_value=user),
            patch.object(password_service, "verify_password", return_value=False),
        ):
            result = await auth_service.authenticate_user(mock_db_session, "test@example.com", "wrong_password")

            assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_not_found(self, auth_service, mock_db_session):
        """Тест аутентификации несуществующего пользователя."""
        with patch.object(auth_service, "_get_user_by_email", return_value=None):
            result = await auth_service.authenticate_user(mock_db_session, "nonexistent@example.com", "password123")

            assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_inactive_user(self, auth_service, mock_db_session):
        """Тест аутентификации неактивного пользователя."""
        user = create_verified_user(email="test@example.com", is_active=False)

        with (
            patch.object(auth_service, "_get_user_by_email", return_value=user),
            patch.object(password_service, "verify_password", return_value=True),
        ):
            result = await auth_service.authenticate_user(mock_db_session, "test@example.com", "password123")

            assert result is None


class TestJWTService:
    """Тесты для JWT сервиса."""

    def test_create_access_token(self):
        """Тест создания access токена."""
        user = create_verified_user()

        token = jwt_service.create_access_token(user)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self):
        """Тест создания refresh токена."""
        user = create_verified_user()

        token = jwt_service.create_refresh_token(user)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token_valid(self):
        """Тест декодирования валидного access токена."""
        user = create_verified_user()
        token = jwt_service.create_access_token(user)

        payload = jwt_service.decode_access_token(token)

        assert payload is not None
        assert payload["user_id"] == str(user.id)
        assert payload["type"] == "access"


class TestPasswordService:
    """Тесты для сервиса паролей."""

    def test_hash_password(self):
        """Тест хеширования пароля."""
        password = "test_password_123"

        hashed = password_service.hash_password(password)

        assert isinstance(hashed, str)
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """Тест проверки правильного пароля."""
        password = "test_password_123"
        hashed = password_service.hash_password(password)

        is_valid = password_service.verify_password(password, hashed)

        assert is_valid is True

    def test_verify_password_incorrect(self):
        """Тест проверки неправильного пароля."""
        password = "test_password_123"
        wrong_password = "wrong_password"
        hashed = password_service.hash_password(password)

        is_valid = password_service.verify_password(wrong_password, hashed)

        assert is_valid is False
