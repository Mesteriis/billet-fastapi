"""
Простые JWT тесты для увеличения покрытия.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

from apps.auth.services.jwt_service import JWTService


class TestJWTServiceSimple:
    """Простые JWT тесты."""

    def test_jwt_service_init(self):
        """Test JWT service initialization."""
        mock_refresh_repo = MagicMock()
        mock_user_repo = MagicMock()

        service = JWTService(mock_refresh_repo, mock_user_repo)

        assert service._refresh_token_repo == mock_refresh_repo
        assert service._user_repo == mock_user_repo

    def test_hash_token(self):
        """Test token hashing."""
        mock_refresh_repo = MagicMock()
        mock_user_repo = MagicMock()

        service = JWTService(mock_refresh_repo, mock_user_repo)

        token = "test_token_123"
        hash_result = service._hash_token(token)
        assert isinstance(hash_result, str)
        assert len(hash_result) > 0
        assert hash_result != token

    def test_generate_jti(self):
        """Test JWT ID generation."""
        mock_refresh_repo = MagicMock()
        mock_user_repo = MagicMock()

        service = JWTService(mock_refresh_repo, mock_user_repo)

        jti1 = service._generate_jti()
        jti2 = service._generate_jti()
        assert isinstance(jti1, str)
        assert isinstance(jti2, str)
        assert jti1 != jti2

    def test_get_user_permissions_basic(self):
        """Test basic user permissions."""
        mock_refresh_repo = MagicMock()
        mock_user_repo = MagicMock()

        service = JWTService(mock_refresh_repo, mock_user_repo)

        mock_user = MagicMock()
        mock_user.role = MagicMock()
        mock_user.role.value = "user"
        mock_user.is_verified = True
        mock_user.is_superuser = False

        permissions = service._get_user_permissions(mock_user)
        assert isinstance(permissions, list)
        assert "read:profile" in permissions

    def test_get_user_permissions_admin(self):
        """Test admin user permissions."""
        mock_refresh_repo = MagicMock()
        mock_user_repo = MagicMock()

        service = JWTService(mock_refresh_repo, mock_user_repo)

        mock_user = MagicMock()
        mock_user.role = MagicMock()
        mock_user.role.value = "admin"
        mock_user.is_verified = True
        mock_user.is_superuser = False

        permissions = service._get_user_permissions(mock_user)
        assert isinstance(permissions, list)
        assert "read:users" in permissions
        assert "write:users" in permissions

    async def test_get_active_tokens_count(self):
        """Test getting active tokens count."""
        mock_refresh_repo = AsyncMock()
        mock_user_repo = MagicMock()

        mock_refresh_repo.count_active_tokens.return_value = 5

        service = JWTService(mock_refresh_repo, mock_user_repo)

        user_id = uuid.uuid4()
        count = await service.get_active_tokens_count(user_id)

        assert count == 5

    async def test_cleanup_expired_tokens(self):
        """Test cleanup of expired tokens."""
        mock_refresh_repo = AsyncMock()
        mock_user_repo = MagicMock()

        mock_refresh_repo.cleanup_expired_tokens.return_value = 10

        service = JWTService(mock_refresh_repo, mock_user_repo)

        count = await service.cleanup_expired_tokens()
        assert count == 10

    async def test_revoke_all_user_tokens(self):
        """Test revoking all user tokens."""
        mock_refresh_repo = AsyncMock()
        mock_user_repo = MagicMock()

        mock_refresh_repo.revoke_all_user_tokens.return_value = 3

        service = JWTService(mock_refresh_repo, mock_user_repo)

        user_id = uuid.uuid4()
        count = await service.revoke_all_user_tokens(user_id)
        assert count == 3
