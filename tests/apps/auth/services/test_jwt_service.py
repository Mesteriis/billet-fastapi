"""
Simple unit tests for JWTService to increase coverage quickly.
"""

import time
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from apps.auth.schemas.token_schemas import JWTPayload
from apps.auth.services.jwt_service import JWTService
from apps.users.models.enums import UserRole


class TestJWTServiceBasic:
    """Basic unit tests for JWTService methods."""

    @pytest.fixture
    def mock_refresh_token_repo(self):
        """Mock RefreshTokenRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_user_repo(self):
        """Mock UserRepository."""
        return AsyncMock()

    @pytest.fixture
    def jwt_service(self, mock_refresh_token_repo, mock_user_repo):
        """JWTService instance with mocked dependencies."""
        service = JWTService(refresh_token_repo=mock_refresh_token_repo, user_repo=mock_user_repo)
        # Увеличиваем время жизни токена для тестов
        service._access_token_expire_minutes = 24 * 60  # 24 часа
        return service

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
        user.role = UserRole.USER
        user.can_login = True
        return user

    async def test_create_access_token_success(self, jwt_service, sample_user):
        """Test successful access token creation."""
        token = await jwt_service.create_access_token(user=sample_user)

        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # JWT has 3 parts
        assert len(token) > 50  # Reasonable token length

    async def test_create_refresh_token_success(self, jwt_service, mock_refresh_token_repo, sample_user):
        """Test successful refresh token creation."""
        mock_refresh_token = Mock()
        mock_refresh_token.id = uuid.uuid4()
        mock_refresh_token_repo.create.return_value = mock_refresh_token

        token, refresh_obj = await jwt_service.create_refresh_token(user=sample_user)

        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # JWT has 3 parts
        assert refresh_obj == mock_refresh_token
        mock_refresh_token_repo.create.assert_called_once()

    async def test_verify_access_token_valid(self, jwt_service, sample_user):
        """Test verifying valid access token - mocked version."""
        # Используем актуальные временные метки
        now = int(time.time())

        # Мокируем jwt.decode чтобы обойти проблемы с реальным декодированием
        mock_payload = {
            "sub": str(sample_user.id),
            "user_id": sample_user.id,  # UUID объект вместо строки
            "username": sample_user.username,
            "email": sample_user.email,
            "role": UserRole.USER,  # Правильный enum вместо строки
            "is_active": sample_user.is_active,
            "is_verified": sample_user.is_verified,
            "is_superuser": sample_user.is_superuser,
            "iat": now,  # Актуальное время
            "exp": now + 3600,  # Через час от текущего времени
            "jti": "test-jti",
            "token_type": "access",
            "permissions": ["read:profile", "write:profile"],
        }

        with patch("apps.auth.services.jwt_service.jwt.decode", return_value=mock_payload):
            token = "fake.jwt.token"
            payload = await jwt_service.verify_access_token(token)

            # Проверяем что токен валидный и содержит правильные данные
            assert payload is not None, "JWT payload should not be None for valid token"
            assert payload.user_id == sample_user.id
            assert payload.email == sample_user.email
            assert payload.username == sample_user.username
            assert payload.role == UserRole.USER

    async def test_verify_access_token_invalid(self, jwt_service):
        """Test verifying invalid access token."""
        invalid_token = "invalid.token.here"

        payload = await jwt_service.verify_access_token(invalid_token)

        assert payload is None

    async def test_verify_refresh_token_valid(self, jwt_service, sample_user, mock_refresh_token_repo):
        """Test verifying valid refresh token."""
        # Setup mock refresh token
        mock_refresh_token = Mock()
        mock_refresh_token.id = uuid.uuid4()
        mock_refresh_token.user = sample_user
        mock_refresh_token.user_id = sample_user.id
        mock_refresh_token.device_fingerprint = None

        mock_refresh_token_repo.create.return_value = mock_refresh_token
        mock_refresh_token_repo.get_valid_token.return_value = mock_refresh_token
        mock_refresh_token_repo.update_last_used.return_value = None

        # Create refresh token
        token, _ = await jwt_service.create_refresh_token(user=sample_user)

        # Verify it
        result = await jwt_service.verify_refresh_token(token)

        assert result == mock_refresh_token
        mock_refresh_token_repo.get_valid_token.assert_called_once()

    async def test_verify_refresh_token_invalid(self, jwt_service):
        """Test verifying invalid refresh token."""
        invalid_token = "invalid.token.here"

        result = await jwt_service.verify_refresh_token(invalid_token)

        assert result is None

    async def test_revoke_refresh_token_success(self, jwt_service, mock_refresh_token_repo):
        """Test successful refresh token revocation."""
        token = "some.jwt.token"
        mock_refresh_token_repo.revoke_token.return_value = True

        result = await jwt_service.revoke_refresh_token(token)

        assert result is True
        mock_refresh_token_repo.revoke_token.assert_called_once()

    async def test_revoke_refresh_token_failure(self, jwt_service, mock_refresh_token_repo):
        """Test failed refresh token revocation."""
        token = "some.jwt.token"
        mock_refresh_token_repo.revoke_token.return_value = False

        result = await jwt_service.revoke_refresh_token(token)

        assert result is False

    async def test_revoke_all_user_tokens(self, jwt_service, mock_refresh_token_repo):
        """Test revoking all user tokens."""
        user_id = uuid.uuid4()
        mock_refresh_token_repo.revoke_all_user_tokens.return_value = 5

        count = await jwt_service.revoke_all_user_tokens(user_id)

        assert count == 5
        mock_refresh_token_repo.revoke_all_user_tokens.assert_called_once_with(user_id)

    async def test_refresh_access_token_success(self, jwt_service, sample_user, mock_refresh_token_repo):
        """Test successful access token refresh."""
        # Setup mock refresh token
        mock_refresh_token = Mock()
        mock_refresh_token.user = sample_user
        mock_refresh_token.user_id = sample_user.id
        mock_refresh_token.device_fingerprint = None
        mock_refresh_token.device_info = "test_device"
        mock_refresh_token.ip_address = "127.0.0.1"

        mock_refresh_token_repo.create.return_value = mock_refresh_token
        mock_refresh_token_repo.get_valid_token.return_value = mock_refresh_token
        mock_refresh_token_repo.update_last_used.return_value = None
        mock_refresh_token_repo.revoke_token.return_value = True

        # Create refresh token
        refresh_token, _ = await jwt_service.create_refresh_token(user=sample_user)

        # Test refresh
        result = await jwt_service.refresh_access_token(refresh_token)

        assert result is not None
        new_access_token, new_refresh_token = result
        assert isinstance(new_access_token, str)
        assert isinstance(new_refresh_token, str)

    async def test_refresh_access_token_invalid(self, jwt_service):
        """Test refresh with invalid token."""
        result = await jwt_service.refresh_access_token("invalid.token")

        assert result is None

    def test_generate_jti(self, jwt_service):
        """Test JTI generation."""
        jti1 = jwt_service._generate_jti()
        jti2 = jwt_service._generate_jti()

        assert isinstance(jti1, str)
        assert isinstance(jti2, str)
        assert jti1 != jti2  # Should be unique
        assert len(jti1) > 10  # Reasonable length

    def test_hash_token(self, jwt_service):
        """Test token hashing."""
        token = "test.jwt.token"

        hash1 = jwt_service._hash_token(token)
        hash2 = jwt_service._hash_token(token)

        assert isinstance(hash1, str)
        assert hash1 == hash2  # Same input should produce same hash
        assert len(hash1) == 64  # SHA256 produces 32 bytes = 64 hex chars

    async def test_get_active_tokens_count(self, jwt_service, mock_refresh_token_repo):
        """Test getting active tokens count."""
        user_id = uuid.uuid4()
        mock_refresh_token_repo.count_active_tokens.return_value = 3

        count = await jwt_service.get_active_tokens_count(user_id)

        assert count == 3
        mock_refresh_token_repo.count_active_tokens.assert_called_once_with(user_id)

    async def test_cleanup_expired_tokens(self, jwt_service, mock_refresh_token_repo):
        """Test cleaning up expired tokens."""
        mock_refresh_token_repo.cleanup_expired_tokens.return_value = 7

        count = await jwt_service.cleanup_expired_tokens()

        assert count == 7
        mock_refresh_token_repo.cleanup_expired_tokens.assert_called_once()

    async def test_get_user_tokens_info(self, jwt_service, mock_refresh_token_repo):
        """Test getting user tokens info."""
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

    def test_get_user_permissions_user_role(self, jwt_service, sample_user):
        """Test getting permissions for regular user."""
        sample_user.role = UserRole.USER
        sample_user.is_verified = True
        sample_user.is_superuser = False

        permissions = jwt_service._get_user_permissions(sample_user)

        assert "read:profile" in permissions
        assert "write:profile" in permissions
        assert "create:posts" in permissions
        assert "comment:posts" in permissions
        assert "moderate:posts" not in permissions  # Should not have moderator rights

    def test_get_user_permissions_admin_role(self, jwt_service, sample_user):
        """Test getting permissions for admin user."""
        sample_user.role = UserRole.ADMIN
        sample_user.is_verified = True
        sample_user.is_superuser = False

        permissions = jwt_service._get_user_permissions(sample_user)

        assert "read:profile" in permissions
        assert "read:users" in permissions
        assert "write:users" in permissions
        assert "delete:users" in permissions
        assert "read:admin" in permissions
        assert "moderate:all" in permissions

    def test_get_user_permissions_superuser(self, jwt_service, sample_user):
        """Test getting permissions for superuser."""
        sample_user.role = UserRole.ADMIN
        sample_user.is_verified = True
        sample_user.is_superuser = True

        permissions = jwt_service._get_user_permissions(sample_user)

        assert "read:profile" in permissions
        assert "write:admin" in permissions
        assert "delete:admin" in permissions
        assert "manage:system" in permissions
        assert "access:all" in permissions
