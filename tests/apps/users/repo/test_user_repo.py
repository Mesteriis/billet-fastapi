"""
Basic unit tests for UserRepository to increase coverage quickly.
"""

import uuid
from unittest.mock import AsyncMock

import pytest

from apps.users.repo.user_repo import UserRepository


class TestUserRepositoryBasic:
    """Basic unit tests for UserRepository CRUD operations."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def user_repo(self, mock_session):
        """UserRepository instance."""
        return UserRepository(mock_session)

    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing."""
        return {
            "id": uuid.uuid4(),
            "username": "testuser",
            "email": "test@example.com",
            "password_hash": "$2b$12$hash",
            "first_name": "Test",
            "last_name": "User",
            "is_active": True,
            "is_verified": False,
            "is_superuser": False,
        }

    async def test_get_by_email_success(self, user_repo, mock_session):
        """Test successful user retrieval by email."""
        # Mock the query result
        mock_session.execute.return_value.scalar_one_or_none.return_value = {"email": "test@example.com"}

        result = await user_repo.get_by_email("test@example.com")

        assert result is not None
        mock_session.execute.assert_called()

    async def test_get_by_username_success(self, user_repo, mock_session):
        """Test successful user retrieval by username."""
        mock_session.execute.return_value.scalar_one_or_none.return_value = {"username": "testuser"}

        result = await user_repo.get_by_username("testuser")

        assert result is not None
        mock_session.execute.assert_called()

    async def test_email_exists_true(self, user_repo, mock_session):
        """Test email existence check when exists."""
        # Мокируем метод exists напрямую
        user_repo.exists = AsyncMock(return_value=True)

        result = await user_repo.email_exists("test@example.com")

        assert result is True
        user_repo.exists.assert_called_once()

    async def test_email_exists_false(self, user_repo, mock_session):
        """Test email existence check when not exists."""
        # Мокируем метод exists напрямую
        user_repo.exists = AsyncMock(return_value=False)

        result = await user_repo.email_exists("notfound@example.com")

        assert result is False
        user_repo.exists.assert_called_once()

    async def test_username_exists_true(self, user_repo, mock_session):
        """Test username existence check when exists."""
        # Мокируем метод exists напрямую
        user_repo.exists = AsyncMock(return_value=True)

        result = await user_repo.username_exists("testuser")

        assert result is True
        user_repo.exists.assert_called_once()

    async def test_username_exists_false(self, user_repo, mock_session):
        """Test username existence check when not exists."""
        # Мокируем метод exists напрямую
        user_repo.exists = AsyncMock(return_value=False)

        result = await user_repo.username_exists("notfound")

        assert result is False
        user_repo.exists.assert_called_once()

    async def test_get_with_profile_success(self, user_repo, mock_session):
        """Test user retrieval with profile."""
        user_with_profile = {"id": uuid.uuid4(), "profile": {"bio": "Test bio"}}
        mock_session.execute.return_value.scalar_one_or_none.return_value = user_with_profile

        result = await user_repo.get_with_profile(user_with_profile["id"])

        assert result is not None
        mock_session.execute.assert_called()

    async def test_get_active_users_count(self, user_repo, mock_session):
        """Test getting active users count."""
        # Мокируем метод count напрямую
        user_repo.count = AsyncMock(return_value=42)

        result = await user_repo.get_active_users_count()

        assert result == 42
        user_repo.count.assert_called_once()

    async def test_get_verified_users_count(self, user_repo, mock_session):
        """Test getting verified users count."""
        # Мокируем метод count напрямую
        user_repo.count = AsyncMock(return_value=35)

        result = await user_repo.get_verified_users_count()

        assert result == 35
        user_repo.count.assert_called_once()

    async def test_get_new_users_count(self, user_repo, mock_session):
        """Test getting new users count."""
        # Мокируем метод count напрямую
        user_repo.count = AsyncMock(return_value=5)

        result = await user_repo.get_new_users_count(days=7)

        assert result == 5
        user_repo.count.assert_called_once()

    async def test_search_users_with_query(self, user_repo, mock_session):
        """Test searching users with query."""
        mock_results = [{"username": "user1"}, {"username": "user2"}]
        # Мокируем метод list_with_complex_filters напрямую
        user_repo.list_with_complex_filters = AsyncMock(return_value=mock_results)

        result = await user_repo.search_users("test")

        assert result == mock_results
        user_repo.list_with_complex_filters.assert_called_once()

    async def test_bulk_update_status_success(self, user_repo, mock_session):
        """Test bulk updating user status."""
        from apps.users.models.enums import UserStatus

        user_ids = [uuid.uuid4(), uuid.uuid4()]
        # Мокируем метод bulk_update напрямую
        user_repo.bulk_update = AsyncMock(return_value=len(user_ids))

        result = await user_repo.bulk_update_status(user_ids, UserStatus.ACTIVE)

        assert result == len(user_ids)
        user_repo.bulk_update.assert_called_once()

    async def test_bulk_activate_users(self, user_repo, mock_session):
        """Test bulk activating users."""
        user_ids = [uuid.uuid4(), uuid.uuid4()]
        # Мокируем метод bulk_update напрямую
        user_repo.bulk_update = AsyncMock(return_value=len(user_ids))

        result = await user_repo.bulk_activate_users(user_ids)

        assert result == len(user_ids)
        user_repo.bulk_update.assert_called_once()

    async def test_bulk_deactivate_users(self, user_repo, mock_session):
        """Test bulk deactivating users."""
        user_ids = [uuid.uuid4(), uuid.uuid4()]
        # Мокируем метод bulk_update напрямую
        user_repo.bulk_update = AsyncMock(return_value=len(user_ids))

        result = await user_repo.bulk_deactivate_users(user_ids)

        assert result == len(user_ids)
        user_repo.bulk_update.assert_called_once()

    async def test_get_recently_active_users(self, user_repo, mock_session):
        """Test getting recently active users."""
        mock_results = [{"username": "active_user1"}, {"username": "active_user2"}]
        # Мокируем метод list напрямую
        user_repo.list = AsyncMock(return_value=mock_results)

        result = await user_repo.get_recently_active_users(hours=24)

        assert result == mock_results
        user_repo.list.assert_called_once()

    async def test_cleanup_inactive_users(self, user_repo, mock_session):
        """Test cleaning up inactive users."""
        # Мокируем метод bulk_delete напрямую
        user_repo.bulk_delete = AsyncMock(return_value=10)

        result = await user_repo.cleanup_inactive_users(days=365)

        assert result == 10
        user_repo.bulk_delete.assert_called_once()
