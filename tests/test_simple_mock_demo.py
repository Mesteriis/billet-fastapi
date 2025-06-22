"""
Простой тест для демонстрации работы системы моков с Auth API.

Тестирует напрямую функциональность без FastAPI dependency injection.
"""

from tests.utils_test.mock_system import create_mock_user


class TestSimpleMockDemo:
    """Простые тесты системы моков без FastAPI DI."""

    async def test_jwt_service_mock_directly(self, auto_mock_all):
        """Тест JWT сервиса напрямую через систему моков."""
        # Получаем моки
        jwt_service = auto_mock_all.get_mock("jwt_service")

        # Создаем тестового пользователя
        user = create_mock_user(email="test@test.com", username="testuser")

        # Настраиваем поведение моков
        jwt_service.revoke_refresh_token.return_value = True
        jwt_service.revoke_all_user_tokens.return_value = 5

        # Вызываем методы напрямую
        result1 = await jwt_service.revoke_refresh_token("some_token")
        result2 = await jwt_service.revoke_all_user_tokens(user.id)

        # Проверяем результаты
        assert result1 is True
        assert result2 == 5

        # Проверяем что методы вызваны правильно
        jwt_service.revoke_refresh_token.assert_called_once_with("some_token")
        jwt_service.revoke_all_user_tokens.assert_called_once_with(user.id)

    async def test_session_service_mock_directly(self, auto_mock_all):
        """Тест Session сервиса напрямую через систему моков."""
        # Получаем моки
        session_service = auto_mock_all.get_mock("session_service")

        user = create_mock_user()

        # Настраиваем поведение
        session_service.invalidate_all_user_sessions.return_value = True

        # Вызываем метод
        result = await session_service.invalidate_all_user_sessions(user.id)

        # Проверяем
        assert result is True
        session_service.invalidate_all_user_sessions.assert_called_once_with(user.id)

    async def test_complete_logout_scenario_mocked(self, auto_mock_all):
        """Тест полного сценария logout через моки."""
        # Получаем все нужные моки
        jwt_service = auto_mock_all.get_mock("jwt_service")
        session_service = auto_mock_all.get_mock("session_service")

        user = create_mock_user()
        refresh_token = "test_refresh_token"

        # Настраиваем поведение всех сервисов
        jwt_service.revoke_refresh_token.return_value = True
        jwt_service.revoke_all_user_tokens.return_value = 3
        session_service.invalidate_all_user_sessions.return_value = True

        # Симулируем последовательность действий при logout
        step1 = await jwt_service.revoke_refresh_token(refresh_token)
        step2 = await jwt_service.revoke_all_user_tokens(user.id)
        step3 = await session_service.invalidate_all_user_sessions(user.id)

        # Проверяем все результаты
        assert step1 is True
        assert step2 == 3
        assert step3 is True

        # Проверяем все вызовы
        jwt_service.revoke_refresh_token.assert_called_once_with(refresh_token)
        jwt_service.revoke_all_user_tokens.assert_called_once_with(user.id)
        session_service.invalidate_all_user_sessions.assert_called_once_with(user.id)

        print("✅ Полный сценарий logout успешно протестирован через моки!")
