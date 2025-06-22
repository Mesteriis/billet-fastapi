"""
Централизованная система моков для FastAPI тестов.

Решает проблемы с dependency injection и вложенными зависимостями.
"""

from typing import Any, Dict, Type
from unittest.mock import AsyncMock, Mock

import pytest


class MockDependencyManager:
    """
    Менеджер для централизованного управления моками зависимостей.

    Решает проблемы:
    - Вложенные зависимости (Service -> Repo -> DB)
    - AsyncMock vs Mock конфликты
    - Сложная настройка цепочек моков
    """

    def __init__(self):
        self.mocks: Dict[str, Any] = {}
        self.patchers: list = []

    def create_service_mocks(self) -> Dict[str, Any]:
        """
        Создает полный набор моков для Auth и User сервисов.

        Returns:
            Dict с настроенными моками для всех сервисов
        """
        # ================== REPOSITORIES MOCKS ==================

        # Auth repositories
        self.mocks["refresh_token_repo"] = AsyncMock()
        self.mocks["orbital_token_repo"] = AsyncMock()
        self.mocks["user_session_repo"] = AsyncMock()

        # User repositories
        self.mocks["user_repo"] = AsyncMock()
        self.mocks["profile_repo"] = AsyncMock()

        # ================== SERVICES MOCKS ==================

        # Auth services - создаем как AsyncMock для полной поддержки async/await
        self.mocks["jwt_service"] = AsyncMock()
        self._setup_jwt_service_defaults()

        self.mocks["orbital_service"] = AsyncMock()
        self._setup_orbital_service_defaults()

        self.mocks["session_service"] = AsyncMock()
        self._setup_session_service_defaults()

        # User services
        self.mocks["user_service"] = AsyncMock()
        self._setup_user_service_defaults()

        self.mocks["profile_service"] = AsyncMock()
        self._setup_profile_service_defaults()

        return self.mocks

    def _setup_jwt_service_defaults(self):
        """Настраивает дефолтные возвращаемые значения для JWT сервиса."""
        jwt_service = self.mocks["jwt_service"]

        # Основные методы JWT сервиса с дефолтными значениями
        jwt_service.create_access_token.return_value = "access_token_123"
        jwt_service.create_refresh_token.return_value = ("refresh_token_123", Mock())
        jwt_service.verify_access_token.return_value = Mock()
        jwt_service.verify_refresh_token.return_value = Mock()
        jwt_service.revoke_refresh_token.return_value = True
        jwt_service.revoke_all_user_tokens.return_value = 5
        jwt_service.refresh_access_token.return_value = ("new_access", "new_refresh")
        jwt_service.get_active_tokens_count.return_value = 3
        jwt_service.cleanup_expired_tokens.return_value = 10
        jwt_service.get_user_tokens_info.return_value = {"active_tokens_count": 2}

    def _setup_orbital_service_defaults(self):
        """Настраивает дефолтные возвращаемые значения для Orbital сервиса."""
        orbital_service = self.mocks["orbital_service"]

        orbital_service.create_email_verification_token.return_value = ("token_123", Mock())
        orbital_service.create_password_reset_token.return_value = ("reset_token", Mock())
        orbital_service.verify_token.return_value = Mock()
        orbital_service.consume_token.return_value = True
        orbital_service.cleanup_expired_tokens.return_value = 5

    def _setup_session_service_defaults(self):
        """Настраивает дефолтные возвращаемые значения для Session сервиса."""
        session_service = self.mocks["session_service"]

        session_service.create_session.return_value = Mock(session_id="session_123", csrf_token="csrf_123")
        session_service.get_session.return_value = Mock()
        session_service.invalidate_session.return_value = True
        session_service.invalidate_all_user_sessions.return_value = True
        session_service.get_user_sessions.return_value = []
        session_service.get_user_session_info.return_value = {"sessions": []}
        session_service.cleanup_expired_sessions.return_value = 3
        session_service.revoke_session.return_value = True

    def _setup_user_service_defaults(self):
        """Настраивает дефолтные возвращаемые значения для User сервиса."""
        user_service = self.mocks["user_service"]

        user_service.create_user.return_value = Mock()
        user_service.get_user_by_id.return_value = Mock()
        user_service.get_user_by_email.return_value = Mock()
        user_service.get_user_by_username.return_value = Mock()
        user_service.authenticate_user.return_value = Mock()
        user_service.update_user.return_value = Mock()
        user_service.delete_user.return_value = True
        user_service.activate_user.return_value = True
        user_service.deactivate_user.return_value = True
        user_service.verify_email.return_value = True
        user_service.change_password.return_value = True
        user_service.reset_password.return_value = True
        user_service.search_users.return_value = []
        user_service.get_user_stats.return_value = {"total_users": 100}
        user_service.update_last_login.return_value = True
        user_service.update_last_seen.return_value = True

    def _setup_profile_service_defaults(self):
        """Настраивает дефолтные возвращаемые значения для Profile сервиса."""
        profile_service = self.mocks["profile_service"]

        profile_service.create_profile.return_value = Mock()
        profile_service.get_profile_by_user_id.return_value = Mock()
        profile_service.update_profile.return_value = Mock()
        profile_service.delete_profile.return_value = True
        profile_service.search_profiles.return_value = []
        profile_service.get_public_profiles.return_value = []

    def patch_dependencies(self, mocker):
        """
        Патчит все dependency functions в FastAPI.

        Args:
            mocker: pytest-mock fixture
        """
        # ================== REPOSITORY DEPENDENCY FUNCTIONS ==================

        # Auth repository dependencies
        mocker.patch(
            "apps.auth.depends.repositories.get_refresh_token_repo", return_value=self.mocks["refresh_token_repo"]
        )
        mocker.patch(
            "apps.auth.depends.repositories.get_orbital_token_repo", return_value=self.mocks["orbital_token_repo"]
        )
        mocker.patch(
            "apps.auth.depends.repositories.get_user_session_repo", return_value=self.mocks["user_session_repo"]
        )

        # User repository dependencies
        mocker.patch("apps.users.depends.repositories.get_user_repo", return_value=self.mocks["user_repo"])
        mocker.patch("apps.users.depends.repositories.get_profile_repo", return_value=self.mocks["profile_repo"])

        # ================== SERVICE DEPENDENCY FUNCTIONS ==================

        # Auth service dependencies - теперь сервисы будут создаваться с мокированными репозиториями
        mocker.patch("apps.auth.depends.services.get_jwt_service", return_value=self.mocks["jwt_service"])
        mocker.patch("apps.auth.depends.services.get_orbital_service", return_value=self.mocks["orbital_service"])
        mocker.patch("apps.auth.depends.services.get_session_service", return_value=self.mocks["session_service"])

        # User service dependencies
        mocker.patch("apps.users.depends.services.get_user_service", return_value=self.mocks["user_service"])
        mocker.patch("apps.users.depends.services.get_profile_service", return_value=self.mocks["profile_service"])

        # ================== ДОПОЛНИТЕЛЬНОЕ МОКИРОВАНИЕ ==================

        # Мокируем прямые импорты сервисов (на случай если используются)
        mocker.patch("apps.auth.services.jwt_service.JWTService", return_value=self.mocks["jwt_service"])
        mocker.patch("apps.auth.services.orbital_service.OrbitalService", return_value=self.mocks["orbital_service"])
        mocker.patch("apps.auth.services.session_service.SessionService", return_value=self.mocks["session_service"])
        mocker.patch("apps.users.services.user_service.UserService", return_value=self.mocks["user_service"])
        mocker.patch("apps.users.services.profile_service.ProfileService", return_value=self.mocks["profile_service"])

    def get_mock(self, name: str) -> Any:
        """
        Получает мок по имени.

        Args:
            name: Имя мока (например, 'jwt_service', 'user_repo')

        Returns:
            Настроенный мок
        """
        return self.mocks.get(name)

    def reset_all_mocks(self):
        """Сбрасывает все моки к исходному состоянию."""
        for mock in self.mocks.values():
            if hasattr(mock, "reset_mock"):
                mock.reset_mock()


# ================== PYTEST FIXTURES ==================


@pytest.fixture
def mock_manager():
    """
    Фикстура для получения менеджера моков.

    Usage:
        def test_something(mock_manager, mocker):
            mock_manager.create_service_mocks()
            mock_manager.patch_dependencies(mocker)

            jwt_service = mock_manager.get_mock('jwt_service')
            jwt_service.create_access_token.return_value = "custom_token"
    """
    manager = MockDependencyManager()
    manager.create_service_mocks()
    return manager


@pytest.fixture
def auto_mock_all(mock_manager, mocker):
    """
    Автоматически мокирует все зависимости.

    Usage:
        def test_something(auto_mock_all, mock_manager):
            # Все зависимости уже замоканы!
            jwt_service = mock_manager.get_mock('jwt_service')
            # Настраиваем поведение при необходимости
    """
    mock_manager.patch_dependencies(mocker)
    return mock_manager


# ================== HELPER FUNCTIONS ==================


def create_mock_user(user_id=None, email="test@example.com", username="testuser", **kwargs):
    """
    Создает мок пользователя с реалистичными данными.

    Args:
        user_id: UUID пользователя
        email: Email пользователя
        username: Имя пользователя
        **kwargs: Дополнительные атрибуты

    Returns:
        Mock объект пользователя
    """
    import uuid

    user = Mock()
    user.id = user_id or uuid.uuid4()
    user.email = email
    user.username = username
    user.is_active = kwargs.get("is_active", True)
    user.is_verified = kwargs.get("is_verified", True)
    user.is_superuser = kwargs.get("is_superuser", False)
    user.can_login = kwargs.get("can_login", True)
    user.role = kwargs.get("role", "user")

    # Добавляем дополнительные атрибуты
    for key, value in kwargs.items():
        setattr(user, key, value)

    return user


def create_mock_session(session_id="session_123", **kwargs):
    """
    Создает мок сессии.

    Args:
        session_id: ID сессии
        **kwargs: Дополнительные атрибуты

    Returns:
        Mock объект сессии
    """
    session = Mock()
    session.session_id = session_id
    session.csrf_token = kwargs.get("csrf_token", "csrf_123")
    session.user_id = kwargs.get("user_id")
    session.ip_address = kwargs.get("ip_address", "127.0.0.1")
    session.user_agent = kwargs.get("user_agent", "Test Browser")
    session.is_active = kwargs.get("is_active", True)

    return session
