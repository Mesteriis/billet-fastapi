"""
Simple unit tests for UserService to increase coverage quickly.
"""

import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from apps.users.services.user_service import UserService


class TestUserServiceBasic:
    """Basic unit tests for UserService methods."""

    @pytest.fixture
    def mock_user_repo(self):
        """Mock UserRepository."""
        return AsyncMock()

    @pytest.fixture
    def mock_profile_repo(self):
        """Mock ProfileRepository."""
        return AsyncMock()

    @pytest.fixture
    def user_service(self, mock_user_repo, mock_profile_repo):
        """UserService instance with mocked dependencies."""
        return UserService(user_repo=mock_user_repo, profile_repo=mock_profile_repo)

    @pytest.fixture
    def sample_user(self):
        """Sample user object for testing."""
        user = Mock()
        user.id = uuid.uuid4()
        user.email = "test@example.com"
        user.username = "testuser"
        user.is_active = True
        user.can_login = True
        user.password_hash = "$2b$12$hash"
        return user

    async def test_get_user_by_id_success(self, user_service, mock_user_repo, sample_user):
        """Test successful user retrieval by ID."""
        mock_user_repo.get_by.return_value = sample_user

        result = await user_service.get_user_by_id(sample_user.id)

        assert result == sample_user
        mock_user_repo.get_by.assert_called_once_with(id=sample_user.id)

    async def test_get_user_by_id_not_found(self, user_service, mock_user_repo):
        """Test user retrieval when user not found."""
        user_id = uuid.uuid4()
        mock_user_repo.get_by.return_value = None

        result = await user_service.get_user_by_id(user_id)

        assert result is None
        mock_user_repo.get_by.assert_called_once_with(id=user_id)

    async def test_get_user_by_email_success(self, user_service, mock_user_repo, sample_user):
        """Test successful user retrieval by email."""
        mock_user_repo.get_by_email.return_value = sample_user

        result = await user_service.get_user_by_email(sample_user.email)

        assert result == sample_user
        mock_user_repo.get_by_email.assert_called_once_with(sample_user.email)

    async def test_get_user_by_username_success(self, user_service, mock_user_repo, sample_user):
        """Test successful user retrieval by username."""
        mock_user_repo.get_by_username.return_value = sample_user

        result = await user_service.get_user_by_username(sample_user.username)

        assert result == sample_user
        mock_user_repo.get_by_username.assert_called_once_with(sample_user.username)

    async def test_update_last_login_success(self, user_service, mock_user_repo, sample_user):
        """Test successful last login update."""
        mock_user_repo.get_by.return_value = sample_user
        mock_user_repo.update.return_value = None

        result = await user_service.update_last_login(sample_user.id)

        assert result is True
        mock_user_repo.get_by.assert_called_once_with(id=sample_user.id)
        mock_user_repo.update.assert_called_once()

    async def test_update_last_login_user_not_found(self, user_service, mock_user_repo):
        """Test last login update when user not found."""
        user_id = uuid.uuid4()
        mock_user_repo.get_by.return_value = None

        result = await user_service.update_last_login(user_id)

        assert result is False
        mock_user_repo.get_by.assert_called_once_with(id=user_id)

    async def test_update_last_seen_success(self, user_service, mock_user_repo, sample_user):
        """Test successful last seen update."""
        mock_user_repo.get_by.return_value = sample_user
        mock_user_repo.update.return_value = None

        result = await user_service.update_last_seen(sample_user.id)

        assert result is True
        mock_user_repo.get_by.assert_called_once_with(id=sample_user.id)
        mock_user_repo.update.assert_called_once()

    def test_hash_password(self, user_service):
        """Test password hashing."""
        password = "testpassword123"

        hashed = user_service._hash_password(password)

        assert hashed != password
        assert len(hashed) > 20  # bcrypt hashes are long
        assert hashed.startswith("$2b$")

    def test_verify_password(self, user_service):
        """Test password verification."""
        password = "testpassword123"
        hashed = user_service._hash_password(password)

        # Test correct password
        assert user_service._verify_password(password, hashed) is True

        # Test incorrect password
        assert user_service._verify_password("wrongpassword", hashed) is False

    def test_generate_username_from_email(self, user_service):
        """Test username generation from email."""
        email = "test.user+123@example.com"

        username = user_service._generate_username_from_email(email)

        assert username == "test_user_123"
        assert len(username) <= 50

    async def test_authenticate_user_by_email_success(self, user_service, mock_user_repo, sample_user):
        """Test successful authentication by email."""
        password = "testpassword123"
        sample_user.password_hash = user_service._hash_password(password)

        mock_user_repo.get_by_email.return_value = sample_user
        mock_user_repo.get_by_username.return_value = None
        mock_user_repo.update.return_value = None

        result = await user_service.authenticate_user("test@example.com", password)

        assert result == sample_user
        mock_user_repo.get_by_email.assert_called_once_with("test@example.com")

    async def test_authenticate_user_by_username_success(self, user_service, mock_user_repo, sample_user):
        """Test successful authentication by username."""
        password = "testpassword123"
        sample_user.password_hash = user_service._hash_password(password)

        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_username.return_value = sample_user
        mock_user_repo.update.return_value = None

        result = await user_service.authenticate_user("testuser", password)

        assert result == sample_user
        mock_user_repo.get_by_username.assert_called_once_with("testuser")

    async def test_authenticate_user_not_found(self, user_service, mock_user_repo):
        """Test authentication when user not found."""
        mock_user_repo.get_by_email.return_value = None
        mock_user_repo.get_by_username.return_value = None

        result = await user_service.authenticate_user("notfound@example.com", "password")

        assert result is None

    async def test_authenticate_user_wrong_password(self, user_service, mock_user_repo, sample_user):
        """Test authentication with wrong password."""
        password = "testpassword123"
        sample_user.password_hash = user_service._hash_password(password)

        mock_user_repo.get_by_email.return_value = sample_user

        result = await user_service.authenticate_user("test@example.com", "wrongpassword")

        assert result is None

    async def test_authenticate_user_cannot_login(self, user_service, mock_user_repo, sample_user):
        """Test authentication when user cannot login."""
        password = "testpassword123"
        sample_user.password_hash = user_service._hash_password(password)
        sample_user.can_login = False

        mock_user_repo.get_by_email.return_value = sample_user

        result = await user_service.authenticate_user("test@example.com", password)

        assert result is None
