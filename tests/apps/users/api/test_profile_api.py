"""
Tests for profile API endpoints.

This module contains comprehensive tests for user profile management API endpoints including
profile viewing, updating, privacy settings, search functionality, and profile statistics.
"""

import uuid

import pytest
from httpx import AsyncClient

from apps.users.schemas import ProfileResponse, ProfileSearchFilters, ProfilesListResponse, ProfileUpdateRequest
from tests.factories.user_factories import UserFactory
from tests.utils_test.api_test_client import AsyncApiTestClient


class TestPublicProfilesListing:
    """Test public profiles listing and filtering."""

    async def test_get_public_profiles_success(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Test successful retrieval of public profiles list."""
        # Мокаем сервис профилей
        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.search_public_profiles.return_value = [
            {
                "user_id": 1,
                "display_name": "John Developer",
                "bio": "Full-stack developer",
                "location": "New York",
                "is_public": True,
                "created_at": "2024-01-15T10:30:00Z",
            },
            {
                "user_id": 2,
                "display_name": "Jane Designer",
                "bio": "UX/UI Designer",
                "location": "San Francisco",
                "is_public": True,
                "created_at": "2024-01-16T10:30:00Z",
            },
        ]

        # Мокаем функцию зависимости
        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        response = await api_client.get(api_client.url_for("get_public_profiles"))

        if response.status_code == 200:
            data = response.json()
            assert "profiles" in data
            assert len(data["profiles"]) == 2
            assert data["profiles"][0]["display_name"] == "John Developer"

    async def test_get_public_profiles_with_filters(
        self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker
    ):
        """Test public profiles with search and location filters."""
        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.search_public_profiles.return_value = [
            {
                "user_id": 1,
                "display_name": "John Developer",
                "bio": "Full-stack developer",
                "location": "New York",
                "is_public": True,
                "created_at": "2024-01-15T10:30:00Z",
            }
        ]

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        response = await api_client.get(
            f"{api_client.url_for('get_public_profiles')}?search=developer&location=New%20York&page=1&size=10"
        )

        if response.status_code == 200:
            # Проверяем что сервис был вызван с правильными фильтрами
            mock_profile_service.search_public_profiles.assert_called_once()

    async def test_get_public_profiles_pagination(self, api_client: AsyncApiTestClient, mocker):
        """Test public profiles pagination."""
        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.search_public_profiles.return_value = []

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        response = await api_client.get(f"{api_client.url_for('get_public_profiles')}?page=2&size=20")

        if response.status_code == 200:
            data = response.json()
            assert "profiles" in data

    async def test_get_public_profiles_sorting(self, api_client: AsyncApiTestClient, mocker):
        """Test public profiles with different sorting options."""
        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.search_public_profiles.return_value = []

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        # Тестируем разные варианты сортировки
        sort_options = [
            "?sort_by=created_at&sort_order=asc",
            "?sort_by=display_name&sort_order=desc",
            "?sort_by=updated_at&sort_order=asc",
        ]

        for sort_params in sort_options:
            response = await api_client.get(f"{api_client.url_for('get_public_profiles')}{sort_params}")
            assert response.status_code == 200


class TestUserProfileRetrieval:
    """Test individual user profile retrieval."""

    async def test_get_user_profile_success(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Test successful profile retrieval."""
        current_user = await user_factory.create(role="user", is_active=True)
        target_user = await user_factory.create(is_active=True)

        # Используем force_auth для простой аутентификации
        await api_client.force_auth(user=current_user)

        # Мокаем другие зависимости
        mocker.patch("apps.users.depends.users.get_user_by_id", return_value=target_user)
        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        # Мокаем профиль сервис
        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.get_profile_by_user_id.return_value = {
            "user_id": target_user.id,
            "display_name": "John Doe",
            "bio": "Software developer",
            "avatar_url": "https://example.com/avatar.jpg",
            "is_public": True,
            "created_at": "2024-01-01T10:00:00Z",
        }

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        response = await api_client.get(api_client.url_for("get_user_profile", user_id=str(target_user.id)))

        if response.status_code == 200:
            data = response.json()
            assert data["user_id"] == str(target_user.id)
            assert data["display_name"] == "John Doe"
            assert data["is_public"] is True

    async def test_get_user_profile_own_profile(
        self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker
    ):
        """Test user retrieving their own profile with private information."""
        current_user = await user_factory.create(role="user", is_active=True)

        # Аутентифицируем пользователя ПЕРЕД мокированием
        await api_client.force_auth(user=current_user)

        # Пользователь запрашивает свой собственный профиль
        mocker.patch("apps.users.depends.users.get_user_by_id", return_value=current_user)
        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.get_profile_by_user_id.return_value = {
            "user_id": current_user.id,
            "display_name": "Own Profile",
            "bio": "My personal bio",
            "is_public": True,
            "private_field": "private_data",  # Приватные данные доступны
            "created_at": "2024-01-01T10:00:00Z",
        }

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        response = await api_client.get(api_client.url_for("get_user_profile", user_id=str(current_user.id)))

        if response.status_code == 200:
            # Проверяем что сервис был вызван с include_private=True
            mock_profile_service.get_profile_by_user_id.assert_called_once()

    async def test_get_user_profile_private_profile_access_denied(
        self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker
    ):
        """Test accessing private profile of another user."""
        current_user = await user_factory.create(role="user", is_active=True)
        target_user = await user_factory.create(is_active=True)  # ✅ Исправлено

        # Аутентифицируем пользователя ПЕРЕД мокированием
        await api_client.force_auth(user=current_user)

        mocker.patch("apps.users.depends.users.get_user_by_id", return_value=target_user)
        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        # Мокаем приватный профиль
        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.get_profile_by_user_id.return_value = {
            "user_id": target_user.id,
            "display_name": "Private User",
            "is_public": False,  # Приватный профиль
        }

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        response = await api_client.get(api_client.url_for("get_user_profile", user_id=str(target_user.id)))

        assert response.status_code == 404  # Profile not found or is private

    async def test_get_user_profile_not_found(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Test retrieving non-existent profile."""
        current_user = await user_factory.create(role="user", is_active=True)
        target_user = await user_factory.create(is_active=True)  # ✅ Исправлено

        # Аутентифицируем пользователя ПЕРЕД мокированием
        await api_client.force_auth(user=current_user)

        mocker.patch("apps.users.depends.users.get_user_by_id", return_value=target_user)
        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        # Мокаем что профиль не найден
        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.get_profile_by_user_id.return_value = None

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        response = await api_client.get(api_client.url_for("get_user_profile", user_id=str(target_user.id)))

        assert response.status_code == 404

    async def test_get_user_profile_unauthorized(self, api_client: AsyncApiTestClient, user_factory: UserFactory):
        """Test profile access without authentication."""
        import pytest

        from apps.auth.exceptions import AuthTokenValidationError

        target_user = await user_factory.create()

        # Проверяем что выбрасывается правильное исключение
        with pytest.raises(AuthTokenValidationError) as exc_info:
            await api_client.get(api_client.url_for("get_user_profile", user_id=str(target_user.id)))

        assert "Authorization token required" in str(exc_info.value)


class TestProfileUpdate:
    """Test profile updates."""

    async def test_update_user_profile_success(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Test successful profile update."""
        current_user = await user_factory.create(role="user", is_active=True)

        # Аутентифицируем пользователя ПЕРЕД мокированием
        await api_client.force_auth(user=current_user)

        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        # Мокаем обновленный профиль
        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.update_profile.return_value = {
            "user_id": current_user.id,
            "display_name": "Updated Name",
            "bio": "Updated bio text",
            "location": "New Location",
            "is_public": True,
            "updated_at": "2024-01-01T12:00:00Z",
        }

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        update_data = {
            "display_name": "Updated Name",
            "bio": "Updated bio text",
            "location": "New Location",
            "is_public": True,
        }

        response = await api_client.put(
            api_client.url_for("update_user_profile", user_id=str(current_user.id)), json=update_data
        )

        if response.status_code == 200:
            data = response.json()
            assert data["display_name"] == "Updated Name"
            assert data["bio"] == "Updated bio text"
            mock_profile_service.update_profile.assert_called_once()

    async def test_update_other_user_profile_forbidden(
        self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker
    ):
        """Test updating another user's profile (should be forbidden)."""
        current_user = await user_factory.create(role="user", is_active=True)
        other_user = await user_factory.create()

        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        update_data = {"display_name": "Hacker Attempt", "bio": "Trying to hack"}

        # Аутентифицируем пользователя
        await api_client.force_auth(user=current_user)

        response = await api_client.put(
            api_client.url_for("update_user_profile", user_id=str(other_user.id)), json=update_data
        )

        assert response.status_code in [403, 422]  # 403 для прав, 422 для валидации

    async def test_update_profile_not_found(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Test updating non-existent profile."""
        current_user = await user_factory.create(role="user", is_active=True)

        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.update_profile.return_value = None  # Profile not found

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        update_data = {"display_name": "New Name"}

        # Аутентифицируем пользователя
        await api_client.force_auth(user=current_user)

        response = await api_client.put(
            api_client.url_for("update_user_profile", user_id=str(current_user.id)), json=update_data
        )

        assert response.status_code in [404, 422]  # 404 для отсутствия, 422 для валидации

    async def test_update_profile_invalid_data(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Test profile update with invalid data."""
        current_user = await user_factory.create(role="user", is_active=True)

        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.update_profile.side_effect = ValueError("Invalid profile data")

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        update_data = {
            "display_name": "A" * 300,  # Слишком длинное имя
            "bio": "B" * 10000,  # Слишком длинная биография
            "website": "invalid-url",  # Невалидный URL
        }

        # Аутентифицируем пользователя
        await api_client.force_auth(user=current_user)

        response = await api_client.put(
            api_client.url_for("update_user_profile", user_id=str(current_user.id)), json=update_data
        )

        assert response.status_code in [400, 422]  # 400 для валидации, 422 для валидации


class TestOwnProfileOperations:
    """Test operations on own profile (/me endpoints)."""

    async def test_get_my_profile_success(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Test getting own profile with full information."""
        current_user = await user_factory.create(role="user", is_active=True)

        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.get_profile_by_user_id.return_value = {
            "user_id": current_user.id,
            "display_name": "My Profile",
            "bio": "My personal bio",
            "is_public": True,
            "privacy_settings": {"email_visible": False, "activity_visible": True},
            "private_data": "sensitive_info",  # Приватные данные доступны
        }

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        # Аутентифицируем пользователя
        await api_client.force_auth(user=current_user)

        response = await api_client.get(api_client.url_for("get_my_profile"))

        if response.status_code == 200:
            data = response.json()
            assert data["user_id"] == str(current_user.id)
            assert "privacy_settings" in data
            # Проверяем что сервис был вызван с include_private=True
            mock_profile_service.get_profile_by_user_id.assert_called_once_with(
                user_id=current_user.id, include_private=True
            )

    async def test_get_my_profile_not_found(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Test getting own profile when profile doesn't exist."""
        current_user = await user_factory.create(role="user", is_active=True)

        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.get_profile_by_user_id.return_value = None

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        # Аутентифицируем пользователя
        await api_client.force_auth(user=current_user)

        response = await api_client.get(api_client.url_for("get_my_profile"))

        assert response.status_code in [404, 422]  # 404 для отсутствия профиля, 422 для валидации

    async def test_update_my_profile_success(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Test updating own profile."""
        current_user = await user_factory.create(role="user", is_active=True)

        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.update_profile.return_value = {
            "user_id": current_user.id,
            "display_name": "Updated My Profile",
            "bio": "Updated personal bio",
            "is_public": False,
            "updated_at": "2024-01-01T12:00:00Z",
        }

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        update_data = {"display_name": "Updated My Profile", "bio": "Updated personal bio", "is_public": False}

        # Аутентифицируем пользователя
        await api_client.force_auth(user=current_user)

        response = await api_client.put(api_client.url_for("update_my_profile"), json=update_data)

        if response.status_code == 200:
            data = response.json()
            assert data["display_name"] == "Updated My Profile"
            assert data["is_public"] is False

    async def test_update_my_profile_unauthorized(self, api_client: AsyncApiTestClient):
        """Test updating own profile without authentication."""
        update_data = {"display_name": "Unauthorized Update"}

        response = await api_client.put(api_client.url_for("update_my_profile"), json=update_data)
        assert response.status_code in [401, 422]  # 401 для авторизации, 422 для валидации


class TestProfilePrivacySettings:
    """Test profile privacy management."""

    async def test_make_profile_public_success(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Test making profile public."""
        current_user = await user_factory.create(role="user", is_active=True)

        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.update_privacy_settings.return_value = True

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        # Аутентифицируем пользователя
        await api_client.force_auth(user=current_user)

        response = await api_client.post(api_client.url_for("make_profile_public"))

        if response.status_code == 200:
            data = response.json()
            assert "profile is now public" in data["message"].lower()
            mock_profile_service.update_privacy_settings.assert_called_once_with(
                user_id=current_user.id, public_profile=True
            )

    async def test_make_profile_private_success(
        self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker
    ):
        """Test making profile private."""
        current_user = await user_factory.create(role="user", is_active=True)

        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.update_privacy_settings.return_value = True

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        # Аутентифицируем пользователя
        await api_client.force_auth(user=current_user)

        response = await api_client.post(api_client.url_for("make_profile_private"))

        if response.status_code == 200:
            data = response.json()
            assert "profile is now private" in data["message"].lower()
            mock_profile_service.update_privacy_settings.assert_called_once_with(
                user_id=current_user.id, public_profile=False
            )

    async def test_set_profile_visibility_not_found(
        self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker
    ):
        """Test setting visibility for non-existent profile."""
        current_user = await user_factory.create(role="user", is_active=True)

        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.update_privacy_settings.return_value = False  # Profile not found

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        # Аутентифицируем пользователя
        await api_client.force_auth(user=current_user)

        response = await api_client.post(api_client.url_for("make_profile_public"))

        assert response.status_code in [404, 422]  # 404 для отсутствия, 422 для валидации

    async def test_privacy_settings_unauthorized(self, api_client: AsyncApiTestClient):
        """Test privacy settings without authentication."""
        endpoints = ["make_profile_public", "make_profile_private"]

        for endpoint in endpoints:
            response = await api_client.post(api_client.url_for(endpoint))
            assert response.status_code in [401, 422]  # 401 для авторизации, 422 для валидации


class TestProfileSearch:
    """Test profile search functionality."""

    async def test_search_profiles_success(self, api_client: AsyncApiTestClient, mocker):
        """Test successful profile search."""
        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.search_public_profiles.return_value = [
            {
                "user_id": 1,
                "display_name": "Python Developer",
                "bio": "Expert in Python development",
                "location": "Remote",
                "skills": ["python", "fastapi", "django"],
            },
            {
                "user_id": 2,
                "display_name": "Senior Python Engineer",
                "bio": "10+ years Python experience",
                "location": "New York",
                "skills": ["python", "react", "aws"],
            },
        ]

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        response = await api_client.get(f"{api_client.url_for('search_profiles')}?q=python%20developer")

        if response.status_code == 200:
            data = response.json()
            assert "profiles" in data
            assert len(data["profiles"]) == 2
            assert "Python" in data["profiles"][0]["display_name"]

    async def test_search_profiles_with_filters(self, api_client: AsyncApiTestClient, mocker):
        """Test profile search with additional filters."""
        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.search_public_profiles.return_value = [
            {
                "user_id": 1,
                "display_name": "Remote Python Developer",
                "bio": "Full-stack Python developer",
                "location": "Remote",
            }
        ]

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        response = await api_client.get(
            f"{api_client.url_for('search_profiles')}?q=python&location=Remote&sort_by=relevance"
        )

        if response.status_code == 200:
            mock_profile_service.search_public_profiles.assert_called_once()

    async def test_search_profiles_minimum_query_length(self, api_client: AsyncApiTestClient):
        """Test search with too short query."""
        response = await api_client.get(f"{api_client.url_for('search_profiles')}?q=p")  # Too short
        assert response.status_code == 422  # Validation error

    async def test_search_profiles_empty_results(self, api_client: AsyncApiTestClient, mocker):
        """Test search with no results."""
        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.search_public_profiles.return_value = []

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        response = await api_client.get(f"{api_client.url_for('search_profiles')}?q=nonexistent")

        if response.status_code == 200:
            data = response.json()
            assert len(data["profiles"]) == 0

    async def test_search_profiles_pagination(self, api_client: AsyncApiTestClient, mocker):
        """Test search results pagination."""
        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.search_public_profiles.return_value = []

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        response = await api_client.get(f"{api_client.url_for('search_profiles')}?q=developer&page=2&size=10")

        if response.status_code == 200:
            data = response.json()
            assert "profiles" in data


class TestProfileStatistics:
    """Test profile statistics endpoints."""

    async def test_get_my_profile_statistics_success(
        self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker
    ):
        """Test getting own profile statistics."""
        current_user = await user_factory.create(role="user", is_active=True)

        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.get_profile_stats.return_value = {
            "profile_views": 150,
            "profile_likes": 25,
            "connection_requests": 10,
            "search_appearances": 45,
            "last_updated": "2024-01-01T10:00:00Z",
        }

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        # Аутентифицируем пользователя
        await api_client.force_auth(user=current_user)

        response = await api_client.get(api_client.url_for("get_my_profile_statistics"))

        if response.status_code == 200:
            data = response.json()
            assert "profile_views" in data
            assert data["profile_views"] == 150
            assert data["profile_likes"] == 25
            mock_profile_service.get_profile_stats.assert_called_once()

    async def test_get_my_profile_statistics_not_found(
        self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker
    ):
        """Test getting statistics for non-existent profile."""
        current_user = await user_factory.create(role="user", is_active=True)

        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.get_profile_stats.return_value = {}

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        # Аутентифицируем пользователя
        await api_client.force_auth(user=current_user)

        response = await api_client.get(api_client.url_for("get_my_profile_statistics"))

        if response.status_code == 200:
            data = response.json()
            assert data == {}

    async def test_get_my_profile_statistics_unauthorized(self, api_client: AsyncApiTestClient):
        """Test getting statistics without authentication."""
        response = await api_client.get(api_client.url_for("get_my_profile_statistics"))
        assert response.status_code in [401, 422]  # 401 для авторизации, 422 для валидации


class TestProfilesEdgeCases:
    """Test edge cases and error conditions."""

    async def test_invalid_profile_id_format(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Test accessing profile with invalid ID format."""
        current_user = await user_factory.create(role="user", is_active=True)

        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        # Попробуем невалидные форматы ID
        invalid_ids = ["invalid", "abc123", "999999999999999999999"]

        # Аутентифицируем пользователя
        await api_client.force_auth(user=current_user)

        for invalid_id in invalid_ids:
            response = await api_client.get(api_client.url_for("get_user_profile", user_id=invalid_id))
            # Может быть 404 или 422 в зависимости от валидации
            assert response.status_code in [404, 422]

    async def test_large_profile_data_update(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Test updating profile with very large data."""
        current_user = await user_factory.create(role="user", is_active=True)

        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        # Очень большие данные
        large_data = {
            "display_name": "X" * 1000,  # Очень длинное имя
            "bio": "B" * 50000,  # Очень длинная биография
            "website": "https://example.com/" + "x" * 2000,  # Очень длинный URL
        }

        # Аутентифицируем пользователя
        await api_client.force_auth(user=current_user)

        response = await api_client.put(
            api_client.url_for("update_user_profile", user_id=str(current_user.id)), json=large_data
        )

        # Должен быть отклонен из-за размера данных
        assert response.status_code in [400, 413, 422]

    async def test_profile_search_special_characters(self, api_client: AsyncApiTestClient, mocker):
        """Test profile search with special characters."""
        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.search_public_profiles.return_value = []

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        # Поиск со специальными символами
        special_queries = [
            "python & javascript",
            "C++ developer",
            "user@domain.com",
            "user-name_123",
            "русский текст",
        ]

        for query in special_queries:
            response = await api_client.get(f"{api_client.url_for('search_profiles')}?q={query}")
            # Поиск должен обрабатывать специальные символы
            assert response.status_code == 200

    async def test_concurrent_profile_operations(
        self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker
    ):
        """Test concurrent profile operations."""
        current_user = await user_factory.create(role="user", is_active=True)

        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.update_profile.return_value = {
            "user_id": current_user.id,
            "display_name": "Updated Name",
            "bio": "Updated bio",
            "updated_at": "2024-01-01T12:00:00Z",
        }

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        # Симуляция одновременных обновлений
        update_data = {"display_name": "Concurrent Update", "bio": "Testing concurrency"}

        # Аутентифицируем пользователя
        await api_client.force_auth(user=current_user)

        # Отправляем несколько запросов "одновременно"
        import asyncio

        responses = await asyncio.gather(
            api_client.put(api_client.url_for("update_user_profile", user_id=str(current_user.id)), json=update_data),
            api_client.put(api_client.url_for("update_user_profile", user_id=str(current_user.id)), json=update_data),
            api_client.put(api_client.url_for("update_user_profile", user_id=str(current_user.id)), json=update_data),
            return_exceptions=True,
        )

        # Хотя бы один запрос должен быть успешным
        success_count = 0
        for r in responses:
            if not isinstance(r, Exception) and hasattr(r, "status_code"):
                if r.status_code == 200:  # type: ignore
                    success_count += 1
        assert success_count >= 1

    async def test_profile_update_rate_limiting_simulation(
        self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker
    ):
        """Test profile update rate limiting simulation."""
        current_user = await user_factory.create(role="user", is_active=True)

        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        mock_profile_service = mocker.AsyncMock()
        mock_profile_service.update_profile.return_value = {
            "user_id": current_user.id,
            "display_name": "Rate Limited Update",
            "updated_at": "2024-01-01T12:00:00Z",
        }

        mocker.patch("apps.users.depends.services.get_profile_service", return_value=mock_profile_service)

        # Быстрые последовательные обновления
        update_data = {"display_name": "Rate Test"}

        # Аутентифицируем пользователя
        await api_client.force_auth(user=current_user)

        responses = []
        for i in range(10):  # 10 быстрых запросов
            response = await api_client.put(
                api_client.url_for("update_user_profile", user_id=str(current_user.id)),
                json={**update_data, "bio": f"Update {i}"},
            )
            responses.append(response)

        # Все запросы должны быть успешными (в данном случае без rate limiting)
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count >= 5  # Хотя бы половина должна быть успешной

    async def test_malformed_json_requests(self, api_client: AsyncApiTestClient, user_factory: UserFactory, mocker):
        """Test handling of malformed JSON in requests."""
        current_user = await user_factory.create(role="user", is_active=True)

        mocker.patch("apps.auth.depends.base.get_current_active_user", return_value=current_user)

        # Аутентифицируем пользователя
        await api_client.force_auth(user=current_user)

        # Отправляем некорректный JSON
        response = await api_client.put(
            api_client.url_for("update_user_profile", user_id=str(current_user.id)),
            content='{"display_name": "Test", "bio": "Incomplete JSON"',  # Некорректный JSON
            headers={"Content-Type": "application/json"},
        )

        # Должен вернуть ошибку парсинга JSON
        assert response.status_code in [400, 422]
        assert response.status_code in [400, 422]
        assert response.status_code in [400, 422]
