"""
Демонстрация новой системы моков.

Показывает как использовать MockDependencyManager для решения
проблем с dependency injection в FastAPI тестах.
"""

import pytest

from tests.utils_test.mock_system import MockDependencyManager, create_mock_session, create_mock_user


class TestMockSystemDemo:
    """Демонстрационные тесты новой системы моков."""

    def test_mock_manager_basic_usage(self, mock_manager, mocker):
        """Демонстрация базового использования менеджера моков."""
        # Патчим все зависимости
        mock_manager.patch_dependencies(mocker)

        # Получаем моки
        jwt_service = mock_manager.get_mock("jwt_service")
        user_service = mock_manager.get_mock("user_service")

        # Проверяем что моки настроены правильно
        assert jwt_service is not None
        assert user_service is not None
        assert hasattr(jwt_service, "create_access_token")
        assert hasattr(user_service, "create_user")

    def test_auto_mock_all_fixture(self, auto_mock_all):
        """Демонстрация автоматического мокирования всех зависимостей."""
        # auto_mock_all автоматически настроил все моки

        jwt_service = auto_mock_all.get_mock("jwt_service")
        orbital_service = auto_mock_all.get_mock("orbital_service")
        session_service = auto_mock_all.get_mock("session_service")

        # Все сервисы доступны и настроены
        assert jwt_service is not None
        assert orbital_service is not None
        assert session_service is not None

    def test_helper_functions(self):
        """Демонстрация helper функций для создания тестовых данных."""
        # Создаем мок пользователя
        user = create_mock_user(email="demo@test.com", username="demouser", is_active=True, is_verified=False)

        assert user.email == "demo@test.com"
        assert user.username == "demouser"
        assert user.is_active is True
        assert user.is_verified is False

        # Создаем мок сессии
        session = create_mock_session(session_id="demo_session", user_id=user.id, ip_address="192.168.1.1")

        assert session.session_id == "demo_session"
        assert session.user_id == user.id
        assert session.ip_address == "192.168.1.1"

    async def test_mock_service_behavior(self, auto_mock_all):
        """Демонстрация настройки поведения моков."""
        jwt_service = auto_mock_all.get_mock("jwt_service")

        # Настраиваем специфическое поведение
        jwt_service.create_access_token.return_value = "custom_token_123"
        jwt_service.revoke_all_user_tokens.return_value = 10

        # Тестируем поведение
        token = await jwt_service.create_access_token(create_mock_user())
        revoked_count = await jwt_service.revoke_all_user_tokens("user_id")

        assert token == "custom_token_123"
        assert revoked_count == 10

    async def test_mock_service_call_tracking(self, auto_mock_all):
        """Демонстрация отслеживания вызовов моков."""
        jwt_service = auto_mock_all.get_mock("jwt_service")
        user_service = auto_mock_all.get_mock("user_service")

        user = create_mock_user()

        # Вызываем методы
        await jwt_service.create_access_token(user)
        await jwt_service.revoke_refresh_token("some_token")
        await user_service.authenticate_user("test@test.com", "password")

        # Проверяем что методы были вызваны
        jwt_service.create_access_token.assert_called_once_with(user)
        jwt_service.revoke_refresh_token.assert_called_once_with("some_token")
        user_service.authenticate_user.assert_called_once_with("test@test.com", "password")


# Пример использования в реальном тесте
class TestRealWorldExample:
    """Пример использования в реальном API тесте."""

    async def test_jwt_operations_example(self, auto_mock_all):
        """Пример теста JWT операций с новой системой моков."""
        # Получаем моки
        jwt_service = auto_mock_all.get_mock("jwt_service")
        user_service = auto_mock_all.get_mock("user_service")

        # Создаем тестовые данные
        user = create_mock_user(email="jwt@test.com", username="jwtuser")

        # Настраиваем поведение моков
        user_service.authenticate_user.return_value = user
        jwt_service.create_access_token.return_value = "access_token_123"
        jwt_service.create_refresh_token.return_value = ("refresh_token_123", create_mock_session())

        # Симулируем логику авторизации
        authenticated_user = await user_service.authenticate_user("jwt@test.com", "password")
        access_token = await jwt_service.create_access_token(authenticated_user)
        refresh_token, session = await jwt_service.create_refresh_token(authenticated_user)

        # Проверяем результаты
        assert authenticated_user == user
        assert access_token == "access_token_123"
        assert refresh_token == "refresh_token_123"

        # Проверяем что все методы вызваны корректно
        user_service.authenticate_user.assert_called_once_with("jwt@test.com", "password")
        jwt_service.create_access_token.assert_called_once_with(user)
        jwt_service.create_refresh_token.assert_called_once_with(user)
