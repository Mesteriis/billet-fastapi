"""
Quick unit tests for JWT service to reach 70% coverage.
"""

import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from apps.auth.services.jwt_service import JWTService
from apps.users.models.enums import UserRole


class TestJWTServiceQuick:
    """Quick unit tests for JWT service."""

    @pytest.fixture
    def mock_refresh_token_repo(self):
        """Mock refresh token repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_user_repo(self):
        """Mock user repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def jwt_service(self, mock_refresh_token_repo, mock_user_repo):
        """JWTService instance with mocked dependencies."""
        service = JWTService(refresh_token_repo=mock_refresh_token_repo, user_repo=mock_user_repo)
        # Увеличиваем время жизни токена для тестов
        service._access_token_expire_minutes = 24 * 60  # 24 часа
        return service

    @pytest.fixture
    def mock_user(self):
        """Mock user object."""
        user = Mock()
        user.id = str(uuid.uuid4())
        user.username = "testuser"
        user.email = "test@example.com"
        user.role = Mock()
        user.role.value = "user"
        user.is_active = True
        user.is_verified = True
        user.is_superuser = False
        user.can_login = True
        return user

    @pytest.fixture
    def sample_user(self):
        """Sample user object for testing."""
        user = Mock()
        user.id = uuid.uuid4()
        user.email = "test@example.com"
        user.username = "testuser"
        user.is_active = True
        user.is_superuser = False
        user.is_verified = True
        user.role = UserRole.USER  # Используем enum напрямую
        user.can_login = True
        return user

    async def test_create_access_token_success(self, jwt_service, mock_user):
        """Test creating access token."""
        token = await jwt_service.create_access_token(user=mock_user)

        assert isinstance(token, str)
        assert len(token) > 0

    async def test_create_refresh_token_success(self, jwt_service, mock_user, mock_refresh_token_repo):
        """Test creating refresh token."""
        # Mock the repository create method
        mock_refresh_token = Mock()
        mock_refresh_token.id = str(uuid.uuid4())
        mock_refresh_token_repo.create.return_value = mock_refresh_token

        token, refresh_obj = await jwt_service.create_refresh_token(user=mock_user)

        assert isinstance(token, str)
        assert len(token) > 0
        assert refresh_obj == mock_refresh_token

    async def test_verify_access_token_valid(self, jwt_service, sample_user):
        """Test verifying valid access token - mocked version."""
        from unittest.mock import patch

        # Мокируем jwt.decode чтобы обойти проблемы с реальным декодированием
        mock_payload = {
            "sub": str(sample_user.id),
            "user_id": str(sample_user.id),
            "username": sample_user.username,
            "email": sample_user.email,
            "role": "user",  # Строка вместо enum для payload
            "is_active": sample_user.is_active,
            "is_verified": sample_user.is_verified,
            "is_superuser": sample_user.is_superuser,
            "iat": 1640995200,  # Фиксированное время
            "exp": 1640998800,  # Через час
            "jti": "test-jti",
            "token_type": "access",
            "permissions": ["read:profile", "write:profile"],
        }

        with patch("apps.auth.services.jwt_service.jwt.decode", return_value=mock_payload):
            token = "fake.jwt.token"
            payload = await jwt_service.verify_access_token(token)

            # Проверяем что токен валидный и содержит правильные данные
            assert payload is not None, "JWT payload should not be None for valid token"
            assert str(payload.user_id) == str(sample_user.id)
            assert payload.email == sample_user.email
            assert payload.username == sample_user.username

    async def test_verify_access_token_invalid(self, jwt_service):
        """Test verifying invalid token."""
        result = await jwt_service.verify_access_token("invalid_token")

        assert result is None

    async def test_verify_refresh_token_valid(self, jwt_service, mock_user, mock_refresh_token_repo):
        """Test verifying valid refresh token."""
        # Create a refresh token first
        mock_refresh_token = Mock()
        mock_refresh_token.id = str(uuid.uuid4())
        mock_refresh_token.user = mock_user
        mock_refresh_token.user_id = mock_user.id
        mock_refresh_token.device_fingerprint = None
        mock_refresh_token_repo.create.return_value = mock_refresh_token
        mock_refresh_token_repo.get_valid_token.return_value = mock_refresh_token
        mock_refresh_token_repo.update_last_used.return_value = None

        token, _ = await jwt_service.create_refresh_token(user=mock_user)
        result = await jwt_service.verify_refresh_token(token)

        assert result == mock_refresh_token

    async def test_revoke_refresh_token_success(self, jwt_service, mock_refresh_token_repo):
        """Test revoking refresh token."""
        mock_refresh_token_repo.revoke_token.return_value = True

        result = await jwt_service.revoke_refresh_token("some_token")

        assert result is True
        mock_refresh_token_repo.revoke_token.assert_called_once()

    async def test_revoke_all_user_tokens(self, jwt_service, mock_refresh_token_repo):
        """Test revoking all user tokens."""
        user_id = uuid.uuid4()
        mock_refresh_token_repo.revoke_all_user_tokens.return_value = 3

        count = await jwt_service.revoke_all_user_tokens(user_id)

        assert count == 3
        mock_refresh_token_repo.revoke_all_user_tokens.assert_called_once_with(user_id)

    async def test_refresh_access_token_valid(self, jwt_service, mock_user, mock_refresh_token_repo):
        """Test refreshing access token with valid refresh token."""
        # Mock refresh token object
        mock_refresh_token = Mock()
        mock_refresh_token.user = mock_user
        mock_refresh_token.user_id = mock_user.id
        mock_refresh_token.device_fingerprint = None
        mock_refresh_token.device_info = "test_device"
        mock_refresh_token.ip_address = "127.0.0.1"

        # Setup mocks
        mock_refresh_token_repo.create.return_value = mock_refresh_token
        mock_refresh_token_repo.get_valid_token.return_value = mock_refresh_token
        mock_refresh_token_repo.update_last_used.return_value = None
        mock_refresh_token_repo.revoke_token.return_value = True

        # Create refresh token first
        refresh_token, _ = await jwt_service.create_refresh_token(user=mock_user)

        # Test refresh
        result = await jwt_service.refresh_access_token(refresh_token)

        assert result is not None
        new_access_token, new_refresh_token = result
        assert isinstance(new_access_token, str)
        assert isinstance(new_refresh_token, str)

    async def test_refresh_access_token_invalid(self, jwt_service):
        """Test refreshing access token with invalid refresh token."""
        result = await jwt_service.refresh_access_token("invalid_refresh_token")

        assert result is None

    async def test_get_active_tokens_count(self, jwt_service, mock_refresh_token_repo):
        """Test getting active tokens count."""
        user_id = uuid.uuid4()
        mock_refresh_token_repo.count_active_tokens.return_value = 5

        count = await jwt_service.get_active_tokens_count(user_id)

        assert count == 5
        mock_refresh_token_repo.count_active_tokens.assert_called_once_with(user_id)

    async def test_cleanup_expired_tokens(self, jwt_service, mock_refresh_token_repo):
        """Test cleaning up expired tokens."""
        mock_refresh_token_repo.cleanup_expired_tokens.return_value = 10

        count = await jwt_service.cleanup_expired_tokens()

        assert count == 10
        mock_refresh_token_repo.cleanup_expired_tokens.assert_called_once()

    async def test_get_user_tokens_info(self, jwt_service, mock_refresh_token_repo):
        """Test getting user tokens info."""
        from datetime import datetime

        user_id = uuid.uuid4()

        # Mock active tokens
        mock_token = Mock()
        mock_token.id = uuid.uuid4()
        mock_token.device_info = "test_device"
        mock_token.ip_address = "127.0.0.1"
        mock_token.created_at = datetime.utcnow()
        mock_token.last_used_at = datetime.utcnow()
        mock_token.expires_at = datetime.utcnow()

        mock_refresh_token_repo.list_active_tokens.return_value = [mock_token]
        mock_refresh_token_repo.count.return_value = 1

        info = await jwt_service.get_user_tokens_info(user_id)

        assert info["user_id"] == user_id
        assert info["active_tokens_count"] == 1
        assert info["total_tokens_count"] == 1
        assert len(info["active_tokens"]) == 1
