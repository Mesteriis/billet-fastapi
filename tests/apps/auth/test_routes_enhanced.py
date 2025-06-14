"""
Улучшенные тесты для API роутов аутентификации с использованием AsyncApiTestClient.

Демонстрация продвинутых возможностей тестирования API.
"""

import asyncio
import time

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.utils_test.api_test_client import AsyncApiTestClient, ChainStep, RetryStrategy, TestScenarioType


@pytest.fixture
async def enhanced_client(app) -> AsyncApiTestClient:
    """Улучшенный тестовый клиент."""
    async with AsyncApiTestClient(app=app, base_url="http://test") as client:
        client.enable_performance_tracking()
        client.setup_snapshots_dir("tests/snapshots")
        yield client


@pytest.mark.auth
@pytest.mark.enhanced
class TestRegistrationEnhanced:
    """Улучшенные тесты регистрации пользователей."""

    @pytest.mark.asyncio
    async def test_register_success_with_metrics(
        self, enhanced_client: AsyncApiTestClient, db_session: AsyncSession, helpers
    ):
        """Тест успешной регистрации с трекингом производительности."""

        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "full_name": "New User",
            "password": "NewPassword123!",
            "password_confirm": "NewPassword123!",
        }

        async with enhanced_client.test_session(TestScenarioType.INTEGRATION) as session:
            response = await enhanced_client.post("/api/v1/auth/register", json=user_data)

            assert response.status_code == 201
            data = response.json()

            # Проверяем структуру ответа
            assert "user" in data
            assert "tokens" in data

            # Создаем снимок API для будущих регрессионных тестов
            snapshot = await enhanced_client.create_api_snapshot("/api/v1/auth/register", method="POST", json=user_data)

            # Получаем метрики производительности
            perf_stats = enhanced_client.get_performance_stats()

            print(f"📊 Регистрация: {perf_stats['avg_response_time']:.3f}s")
            print(f"📸 Снимок API: {snapshot.checksum}")


@pytest.mark.auth
@pytest.mark.enhanced
class TestLoginEnhanced:
    """Улучшенные тесты входа в систему."""

    @pytest.mark.asyncio
    async def test_login_chain_scenario(self, enhanced_client: AsyncApiTestClient, db_session: AsyncSession):
        """Тест полного сценария входа через chain API."""

        # Создаем пользователя для тестирования
        await enhanced_client.force_auth(email="chaintest@example.com")
        await enhanced_client.force_logout()

        # Определяем шаги цепочки
        login_chain = [
            ChainStep(
                method="POST",
                url="/api/v1/auth/login",
                data={"email": "chaintest@example.com", "password": "TestPassword123!"},
                expected_status=200,
                description="Вход в систему",
                extract_data=lambda r: {"tokens": r.json()["tokens"], "user_id": r.json()["user"]["id"]},
            ),
            ChainStep(method="GET", url="/api/v1/auth/me", expected_status=200, description="Получение профиля"),
            ChainStep(method="GET", url="/api/v1/auth/validate", expected_status=200, description="Валидация токена"),
        ]

        # Выполняем цепочку
        responses = await enhanced_client.run_test_chain(login_chain)

        assert len(responses) == 3
        print(f"🔗 Chain выполнен: {len(responses)} шагов")


@pytest.mark.auth
@pytest.mark.enhanced
@pytest.mark.performance
class TestAuthPerformance:
    """Тесты производительности аутентификации."""

    @pytest.mark.asyncio
    async def test_auth_endpoints_benchmark(self, enhanced_client: AsyncApiTestClient):
        """Бенчмарк производительности эндпоинтов аутентификации."""

        # Создаем тестового пользователя
        await enhanced_client.force_auth(email="benchmark@example.com")
        await enhanced_client.force_logout()

        async with enhanced_client.test_session(TestScenarioType.PERFORMANCE) as session:
            # Бенчмарк входа в систему
            login_data = {"email": "benchmark@example.com", "password": "TestPassword123!"}

            login_times = []
            for _ in range(5):  # 5 попыток входа
                start_time = time.time()

                response = await enhanced_client.post("/api/v1/auth/login", json=login_data)

                end_time = time.time()
                login_times.append(end_time - start_time)

                if response.status_code == 200:
                    # Сразу выходим для следующей попытки
                    tokens = response.json()["tokens"]
                    logout_data = {"refresh_token": tokens["refresh_token"]}
                    await enhanced_client.post("/api/v1/auth/logout", json=logout_data)

            # Анализируем результаты
            avg_login_time = sum(login_times) / len(login_times)
            max_login_time = max(login_times)
            min_login_time = min(login_times)

            print(f"🏃‍♂️ Бенчмарк входа:")
            print(f"   Среднее время: {avg_login_time:.3f}s")
            print(f"   Минимальное: {min_login_time:.3f}s")
            print(f"   Максимальное: {max_login_time:.3f}s")
