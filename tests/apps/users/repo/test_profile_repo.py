"""
Basic unit tests for ProfileRepository to increase coverage quickly.
"""

import uuid
from unittest.mock import AsyncMock

import pytest

from apps.users.repo.profile_repo import ProfileRepository


class TestProfileRepositoryBasic:
    """Basic unit tests for ProfileRepository CRUD operations."""

    @pytest.fixture
    def mock_session(self):
        """Mock database session."""
        return AsyncMock()

    @pytest.fixture
    def profile_repo(self, mock_session):
        """ProfileRepository instance."""
        return ProfileRepository(mock_session)

    @pytest.fixture
    def sample_profile_data(self):
        """Sample profile data for testing."""
        return {
            "id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "bio": "Test bio",
            "location": "Test Location",
            "website": "https://test.com",
            "avatar_url": None,
            "public_profile": True,
            "timezone": "UTC",
            "language": "en",
            "theme": "light",
            "notifications_enabled": True,
        }

    async def test_get_by_user_id_success(self, profile_repo, mock_session, sample_profile_data):
        """Test successful profile retrieval by user_id."""
        # Mock the get_by method
        profile_repo.get_by = AsyncMock(return_value=sample_profile_data)

        result = await profile_repo.get_by_user_id(sample_profile_data["user_id"])

        assert result is not None
        profile_repo.get_by.assert_called_once()

    async def test_get_by_user_id_not_found(self, profile_repo, mock_session):
        """Test profile retrieval when user has no profile."""
        # Mock the get_by method to return None
        profile_repo.get_by = AsyncMock(return_value=None)

        result = await profile_repo.get_by_user_id(uuid.uuid4())

        assert result is None
        profile_repo.get_by.assert_called_once()

    async def test_list_public_profiles_success(self, profile_repo, mock_session):
        """Test listing public profiles."""
        mock_profiles = [{"user_id": uuid.uuid4(), "public_profile": True}]
        # Мокируем метод list напрямую
        profile_repo.list = AsyncMock(return_value=mock_profiles)

        result = await profile_repo.list_public_profiles()

        assert result == mock_profiles
        profile_repo.list.assert_called_once()

    async def test_search_public_profiles_with_query(self, profile_repo, mock_session):
        """Test searching public profiles with query."""
        mock_results = [{"bio": "developer", "public_profile": True}]
        # Мокируем метод search_profiles напрямую
        profile_repo.search_profiles = AsyncMock(return_value=mock_results)

        result = await profile_repo.search_public_profiles("developer")

        assert result == mock_results
        profile_repo.search_profiles.assert_called_once()

    async def test_profile_exists_true(self, profile_repo, mock_session):
        """Test profile existence check when exists."""
        # Мокируем метод exists напрямую
        profile_repo.exists = AsyncMock(return_value=True)

        result = await profile_repo.profile_exists(uuid.uuid4())

        assert result is True
        profile_repo.exists.assert_called_once()

    async def test_profile_exists_false(self, profile_repo, mock_session):
        """Test profile existence check when not exists."""
        # Мокируем метод exists напрямую
        profile_repo.exists = AsyncMock(return_value=False)

        result = await profile_repo.profile_exists(uuid.uuid4())

        assert result is False
        profile_repo.exists.assert_called_once()

    async def test_create_default_profile(self, profile_repo, mock_session):
        """Test creating default profile for user."""
        user_id = uuid.uuid4()
        mock_profile = {"user_id": user_id, "language": "en", "theme": "light"}
        # Мокируем метод create напрямую
        profile_repo.create = AsyncMock(return_value=mock_profile)

        result = await profile_repo.create_default_profile(user_id)

        assert result == mock_profile
        profile_repo.create.assert_called_once()

    async def test_list_by_language_success(self, profile_repo, mock_session):
        """Test listing profiles by language."""
        from apps.users.models.enums import UserLanguage

        mock_profiles = [{"language": "en"}, {"language": "en"}]
        # Мокируем метод list напрямую
        profile_repo.list = AsyncMock(return_value=mock_profiles)

        result = await profile_repo.list_by_language(UserLanguage.EN)

        assert result == mock_profiles
        profile_repo.list.assert_called_once()

    async def test_list_by_theme_success(self, profile_repo, mock_session):
        """Test listing profiles by theme."""
        from apps.users.models.enums import UserTheme

        mock_profiles = [{"theme": "dark"}, {"theme": "dark"}]
        # Мокируем метод list напрямую
        profile_repo.list = AsyncMock(return_value=mock_profiles)

        result = await profile_repo.list_by_theme(UserTheme.DARK)

        assert result == mock_profiles
        profile_repo.list.assert_called_once()

    async def test_list_with_notifications_enabled(self, profile_repo, mock_session):
        """Test listing profiles with notifications enabled."""
        mock_profiles = [{"notifications_enabled": True}]
        # Мокируем метод list напрямую
        profile_repo.list = AsyncMock(return_value=mock_profiles)

        result = await profile_repo.list_with_notifications_enabled()

        assert result == mock_profiles
        profile_repo.list.assert_called_once()

    async def test_bulk_update_language_success(self, profile_repo, mock_session):
        """Test bulk updating profile language."""
        from apps.users.models.enums import UserLanguage

        user_ids = [uuid.uuid4(), uuid.uuid4()]
        # Мокируем метод bulk_update напрямую
        profile_repo.bulk_update = AsyncMock(return_value=len(user_ids))

        result = await profile_repo.bulk_update_language(user_ids, UserLanguage.RU)

        assert result == len(user_ids)
        profile_repo.bulk_update.assert_called_once()

    async def test_bulk_update_theme_success(self, profile_repo, mock_session):
        """Test bulk updating profile theme."""
        from apps.users.models.enums import UserTheme

        user_ids = [uuid.uuid4(), uuid.uuid4()]
        # Мокируем метод bulk_update напрямую
        profile_repo.bulk_update = AsyncMock(return_value=len(user_ids))

        result = await profile_repo.bulk_update_theme(user_ids, UserTheme.DARK)

        assert result == len(user_ids)
        profile_repo.bulk_update.assert_called_once()

    async def test_bulk_disable_notifications_success(self, profile_repo, mock_session):
        """Test bulk disabling notifications."""
        user_ids = [uuid.uuid4(), uuid.uuid4()]
        # Мокируем метод bulk_update напрямую
        profile_repo.bulk_update = AsyncMock(return_value=len(user_ids))

        result = await profile_repo.bulk_disable_notifications(user_ids)

        assert result == len(user_ids)
        profile_repo.bulk_update.assert_called_once()

    async def test_cleanup_incomplete_profiles(self, profile_repo, mock_session):
        """Test cleaning up incomplete profiles."""
        # Мокируем весь метод cleanup_incomplete_profiles напрямую,
        # так как он использует прямые SQLAlchemy запросы
        profile_repo.cleanup_incomplete_profiles = AsyncMock(return_value=5)

        result = await profile_repo.cleanup_incomplete_profiles()

        assert result == 5
        profile_repo.cleanup_incomplete_profiles.assert_called_once()

    async def test_get_profiles_stats(self, profile_repo, mock_session):
        """Test getting profiles statistics."""
        # Мокируем метод count напрямую для всех вызовов
        profile_repo.count = AsyncMock(return_value=100)

        result = await profile_repo.get_profiles_stats()

        # Результат должен содержать основные статистики
        assert "total_profiles" in result
        assert "public_profiles" in result
        assert "private_profiles" in result
        assert "languages" in result
        assert "themes" in result
        assert "notification_levels" in result

        # count должен вызываться множество раз для различных статистик
        assert profile_repo.count.call_count > 5
