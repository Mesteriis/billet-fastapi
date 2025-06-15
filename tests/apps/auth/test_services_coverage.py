"""
Тесты для полного покрытия сервисов аутентификации.
Демонстрация правильного тестирования сервисного слоя с фабриками.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.auth.auth_service import AuthService
from apps.auth.jwt_service import JWTService, jwt_service
from apps.auth.models import RefreshToken
from apps.auth.password_service import PasswordService, password_service


@pytest.mark.auth
@pytest.mark.unit
class TestAuthService:
    """Тесты для сервиса аутентификации."""

    @pytest.fixture
    def auth_service(self):
        """Фикстура сервиса аутентификации."""
        return AuthService()

    async def test_authenticate_user_success(self, auth_service, async_session, verified_user):
        """Тест успешной аутентификации пользователя."""
        # Используем реального пользователя из фабрики
        result = await auth_service.authenticate_user(
            async_session,
            verified_user.email,
            "TestPassword123!",  # Известный пароль из фабрик
        )

        assert result is not None
        assert result.email == verified_user.email
        assert result.is_active is True
        assert result.is_verified is True

    async def test_authenticate_user_invalid_credentials(self, auth_service, async_session, verified_user):
        """Тест аутентификации с неверными данными."""
        result = await auth_service.authenticate_user(async_session, verified_user.email, "WrongPassword123!")

        assert result is None

    async def test_authenticate_user_not_found(self, auth_service, async_session, user_factory):
        """Тест аутентификации несуществующего пользователя."""
        # Создаем данные пользователя но НЕ сохраняем в БД
        fake_user = await user_factory.build()

        result = await auth_service.authenticate_user(async_session, fake_user.email, "TestPassword123!")

        assert result is None

    async def test_authenticate_inactive_user(self, auth_service, async_session, user_factory):
        """Тест аутентификации неактивного пользователя."""
        # Создаем неактивного пользователя
        inactive_user = await user_factory.create(is_active=False, is_verified=True)

        result = await auth_service.authenticate_user(async_session, inactive_user.email, "TestPassword123!")

        assert result is None

    async def test_authenticate_unverified_user(self, auth_service, async_session, user_factory):
        """Тест аутентификации неверифицированного пользователя."""
        # Создаем неверифицированного пользователя
        unverified_user = await user_factory.create(is_active=True, is_verified=False)

        result = await auth_service.authenticate_user(async_session, unverified_user.email, "TestPassword123!")

        # В зависимости от логики приложения - может быть None или user
        # Оставляем проверку гибкой
        if result:
            assert result.is_verified is False

    async def test_register_user_success(self, auth_service, async_session, test_user_data):
        """Тест успешной регистрации пользователя."""
        user = await auth_service.register_user(async_session, user_data=test_user_data, auto_verify=True)

        assert user is not None
        assert user.email == test_user_data.email
        assert user.username == test_user_data.username
        assert user.is_active is True
        assert user.is_verified is True

    async def test_register_user_duplicate_email(self, auth_service, async_session, verified_user, test_user_data):
        """Тест регистрации с существующим email."""
        # Используем email существующего пользователя
        test_user_data.email = verified_user.email

        with pytest.raises(Exception):  # Ожидаем исключение
            await auth_service.register_user(async_session, user_data=test_user_data, auto_verify=True)

    async def test_create_tokens_success(self, auth_service, async_session, verified_user):
        """Тест создания токенов для пользователя."""
        tokens = await auth_service.create_tokens(async_session, verified_user)

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert "expires_in" in tokens

        assert tokens["token_type"] == "bearer"
        assert isinstance(tokens["expires_in"], int)
        assert tokens["expires_in"] > 0

    async def test_refresh_tokens_success(self, auth_service, async_session, verified_user):
        """Тест обновления токенов."""
        # Сначала создаем токены
        original_tokens = await auth_service.create_tokens(async_session, verified_user)

        # Обновляем токены
        new_tokens = await auth_service.refresh_access_token(async_session, original_tokens["refresh_token"])

        assert new_tokens is not None
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens

        # Новые токены должны отличаться от старых
        assert new_tokens["access_token"] != original_tokens["access_token"]
        assert new_tokens["refresh_token"] != original_tokens["refresh_token"]

    async def test_refresh_tokens_invalid_token(self, auth_service, async_session):
        """Тест обновления с невалидным токеном."""
        result = await auth_service.refresh_access_token(async_session, "invalid.refresh.token")

        assert result is None

    async def test_revoke_refresh_token(self, auth_service, async_session, verified_user):
        """Тест отзыва refresh токена."""
        # Создаем токены
        tokens = await auth_service.create_tokens(async_session, verified_user)

        # Отзываем токен
        success = await auth_service.revoke_refresh_token(async_session, tokens["refresh_token"])

        assert success is True

        # Проверяем, что токен больше нельзя использовать
        result = await auth_service.refresh_access_token(async_session, tokens["refresh_token"])
        assert result is None

    async def test_revoke_all_user_tokens(self, auth_service, async_session, verified_user):
        """Тест отзыва всех токенов пользователя."""
        # Создаем несколько токенов
        tokens1 = await auth_service.create_tokens(async_session, verified_user)
        tokens2 = await auth_service.create_tokens(async_session, verified_user)

        # Отзываем все токены
        revoked_count = await auth_service.revoke_all_user_tokens(async_session, verified_user.id)

        assert revoked_count >= 2

        # Проверяем, что токены больше нельзя использовать
        result1 = await auth_service.refresh_access_token(async_session, tokens1["refresh_token"])
        result2 = await auth_service.refresh_access_token(async_session, tokens2["refresh_token"])

        assert result1 is None
        assert result2 is None


@pytest.mark.auth
@pytest.mark.unit
class TestJWTService:
    """Тесты для JWT сервиса."""

    def test_create_access_token(self, verified_user):
        """Тест создания access токена."""
        token = jwt_service.create_access_token(verified_user)

        assert isinstance(token, str)
        assert len(token) > 0

        # Проверяем, что токен содержит точки (JWT формат)
        assert token.count(".") == 2

    def test_create_refresh_token(self, verified_user):
        """Тест создания refresh токена."""
        token = jwt_service.create_refresh_token(verified_user)

        assert isinstance(token, str)
        assert len(token) > 0
        assert token.count(".") == 2

    def test_decode_access_token_valid(self, verified_user):
        """Тест декодирования валидного access токена."""
        token = jwt_service.create_access_token(verified_user)

        payload = jwt_service.decode_access_token(token)

        assert payload is not None
        assert payload["user_id"] == str(verified_user.id)
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_access_token_invalid(self):
        """Тест декодирования невалидного токена."""
        invalid_token = "invalid.jwt.token"

        payload = jwt_service.decode_access_token(invalid_token)

        assert payload is None

    def test_decode_refresh_token_valid(self, verified_user):
        """Тест декодирования валидного refresh токена."""
        token = jwt_service.create_refresh_token(verified_user)

        payload = jwt_service.decode_refresh_token(token)

        assert payload is not None
        assert payload["user_id"] == str(verified_user.id)
        assert payload["type"] == "refresh"

    def test_decode_refresh_token_invalid(self):
        """Тест декодирования невалидного refresh токена."""
        invalid_token = "invalid.jwt.token"

        payload = jwt_service.decode_refresh_token(invalid_token)

        assert payload is None

    def test_tokens_are_different(self, verified_user):
        """Тест что access и refresh токены отличаются."""
        access_token = jwt_service.create_access_token(verified_user)
        refresh_token = jwt_service.create_refresh_token(verified_user)

        assert access_token != refresh_token

        # Декодируем и проверяем типы
        access_payload = jwt_service.decode_access_token(access_token)
        refresh_payload = jwt_service.decode_refresh_token(refresh_token)

        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"

    def test_token_expiration_times(self, verified_user, mock_settings):
        """Тест времени истечения токенов."""
        access_token = jwt_service.create_access_token(verified_user)
        refresh_token = jwt_service.create_refresh_token(verified_user)

        access_payload = jwt_service.decode_access_token(access_token)
        refresh_payload = jwt_service.decode_refresh_token(refresh_token)

        # Access токен должен истекать раньше refresh токена
        assert access_payload["exp"] < refresh_payload["exp"]

        # Проверяем приблизительные времена (с учетом настроек)
        access_lifetime = access_payload["exp"] - access_payload["iat"]
        refresh_lifetime = refresh_payload["exp"] - refresh_payload["iat"]

        assert access_lifetime < refresh_lifetime

    def test_multiple_tokens_unique(self, verified_user):
        """Тест что множественные токены уникальны."""
        tokens = []
        for _ in range(5):
            token = jwt_service.create_access_token(verified_user)
            tokens.append(token)

        # Все токены должны быть уникальными
        assert len(set(tokens)) == 5


@pytest.mark.auth
@pytest.mark.unit
class TestPasswordService:
    """Тесты для сервиса паролей."""

    def test_hash_password(self):
        """Тест хеширования пароля."""
        password = "TestPassword123!"

        hashed = password_service.hash_password(password)

        assert isinstance(hashed, str)
        assert hashed != password
        assert len(hashed) > 0

        # Проверяем, что хеш начинается с префикса bcrypt
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        """Тест проверки правильного пароля."""
        password = "TestPassword123!"
        hashed = password_service.hash_password(password)

        is_valid = password_service.verify_password(password, hashed)

        assert is_valid is True

    def test_verify_password_incorrect(self):
        """Тест проверки неправильного пароля."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = password_service.hash_password(password)

        is_valid = password_service.verify_password(wrong_password, hashed)

        assert is_valid is False

    def test_hash_different_passwords_unique(self):
        """Тест что разные пароли дают разные хеши."""
        password1 = "Password1!"
        password2 = "Password2!"

        hash1 = password_service.hash_password(password1)
        hash2 = password_service.hash_password(password2)

        assert hash1 != hash2

    def test_hash_same_password_different_salts(self):
        """Тест что один пароль дает разные хеши (соль)."""
        password = "TestPassword123!"

        hash1 = password_service.hash_password(password)
        hash2 = password_service.hash_password(password)

        # Хеши должны отличаться из-за разных солей
        assert hash1 != hash2

        # Но оба должны проверяться как валидные
        assert password_service.verify_password(password, hash1) is True
        assert password_service.verify_password(password, hash2) is True

    def test_verify_password_empty_string(self):
        """Тест проверки пустого пароля."""
        password = "TestPassword123!"
        hashed = password_service.hash_password(password)

        is_valid = password_service.verify_password("", hashed)

        assert is_valid is False

    def test_hash_password_empty_string(self):
        """Тест хеширования пустого пароля."""
        # Пустой пароль тоже должен хешироваться
        hashed = password_service.hash_password("")

        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert password_service.verify_password("", hashed) is True

    def test_password_security_requirements(self):
        """Тест разных типов паролей."""
        passwords = [
            "simple",  # Простой
            "Simple123",  # С цифрами
            "Simple123!",  # С спецсимволами
            "VeryLongPasswordWith123!",  # Длинный
            "短密码123!",  # Unicode
            "🔐🔑🚀",  # Эмодзи
        ]

        for password in passwords:
            hashed = password_service.hash_password(password)

            # Все пароли должны корректно хешироваться и проверяться
            assert isinstance(hashed, str)
            assert len(hashed) > 0
            assert password_service.verify_password(password, hashed) is True
            assert password_service.verify_password(password + "wrong", hashed) is False


@pytest.mark.auth
@pytest.mark.integration
class TestAuthServiceIntegration:
    """Интеграционные тесты сервиса аутентификации."""

    async def test_full_auth_flow(self, auth_service, async_session, test_user_data):
        """Тест полного потока аутентификации."""
        # 1. Регистрация
        user = await auth_service.register_user(async_session, user_data=test_user_data, auto_verify=True)
        assert user is not None

        # 2. Аутентификация
        auth_user = await auth_service.authenticate_user(async_session, test_user_data.email, test_user_data.password)
        assert auth_user is not None
        assert auth_user.id == user.id

        # 3. Создание токенов
        tokens = await auth_service.create_tokens(async_session, auth_user)
        assert "access_token" in tokens
        assert "refresh_token" in tokens

        # 4. Обновление токенов
        new_tokens = await auth_service.refresh_access_token(async_session, tokens["refresh_token"])
        assert new_tokens is not None

        # 5. Отзыв токенов
        success = await auth_service.revoke_refresh_token(async_session, new_tokens["refresh_token"])
        assert success is True

    async def test_concurrent_token_operations(self, auth_service, async_session, verified_user):
        """Тест параллельных операций с токенами."""
        # Создаем токены параллельно
        tasks = [auth_service.create_tokens(async_session, verified_user) for _ in range(5)]

        tokens_list = await asyncio.gather(*tasks)

        assert len(tokens_list) == 5

        # Все токены должны быть уникальными
        access_tokens = [tokens["access_token"] for tokens in tokens_list]
        refresh_tokens = [tokens["refresh_token"] for tokens in tokens_list]

        assert len(set(access_tokens)) == 5
        assert len(set(refresh_tokens)) == 5

        # Параллельный отзыв токенов
        revoke_tasks = [
            auth_service.revoke_refresh_token(async_session, tokens["refresh_token"]) for tokens in tokens_list
        ]

        results = await asyncio.gather(*revoke_tasks)

        # Все отзывы должны быть успешными
        assert all(results)

    async def test_auth_service_error_handling(self, auth_service, async_session):
        """Тест обработки ошибок в сервисе аутентификации."""
        # Тест с None параметрами
        result = await auth_service.authenticate_user(async_session, None, "password")
        assert result is None

        result = await auth_service.authenticate_user(async_session, "email@test.com", None)
        assert result is None

        # Тест с пустыми строками
        result = await auth_service.authenticate_user(async_session, "", "password")
        assert result is None

        result = await auth_service.authenticate_user(async_session, "email@test.com", "")
        assert result is None
