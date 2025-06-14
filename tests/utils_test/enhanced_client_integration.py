"""
Интеграция расширенного тестового клиента с существующими тестами API.

Этот модуль демонстрирует, как заменить стандартный AsyncClient на улучшенный
AsyncApiTestClient в существующих тестах с минимальными изменениями.
"""

import asyncio

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories.user_factory import UserFactory
from tests.utils_test.api_test_client import AsyncApiTestClient, ChainStep, RetryStrategy, TestScenarioType

# === ФИКСТУРЫ ДЛЯ ИНТЕГРАЦИИ ===


@pytest.fixture
async def enhanced_client(app: FastAPI) -> AsyncApiTestClient:
    """Улучшенный тестовый клиент с дополнительными возможностями."""
    async with AsyncApiTestClient(app=app, base_url="http://test") as client:
        # Включаем трекинг производительности
        client.enable_performance_tracking()

        # Настраиваем директорию для снимков
        client.setup_snapshots_dir("tests/snapshots")

        yield client


@pytest.fixture
async def auth_enhanced_client(enhanced_client: AsyncApiTestClient) -> AsyncApiTestClient:
    """Аутентифицированный улучшенный клиент."""
    await enhanced_client.force_auth(email="test@example.com", is_superuser=False, email_verified=True)
    return enhanced_client


@pytest.fixture
async def admin_enhanced_client(enhanced_client: AsyncApiTestClient) -> AsyncApiTestClient:
    """Аутентифицированный админ клиент."""
    await enhanced_client.force_auth(email="admin@example.com", is_superuser=True, email_verified=True)
    return enhanced_client


# === ПЕРЕПИСАННЫЕ ТЕСТЫ АУТЕНТИФИКАЦИИ ===


@pytest.mark.auth
@pytest.mark.enhanced
class TestEnhancedAuthFlow:
    """Улучшенные тесты аутентификации с продвинутыми возможностями."""

    @pytest.mark.asyncio
    async def test_registration_with_snapshots(self, enhanced_client: AsyncApiTestClient):
        """Тест регистрации с созданием снимка API."""
        user_data = {
            "email": "snapshot@example.com",
            "username": "snapshotuser",
            "full_name": "Snapshot User",
            "password": "SnapshotPassword123!",
            "password_confirm": "SnapshotPassword123!",
        }

        # Создаем снимок API до изменений
        snapshot = await enhanced_client.create_api_snapshot("/api/v1/auth/register", method="POST", json=user_data)

        assert snapshot.method == "POST"
        assert snapshot.status_code == 201
        print(f"API snapshot created: {snapshot.checksum}")

    @pytest.mark.asyncio
    async def test_auth_chain_flow(self, enhanced_client: AsyncApiTestClient):
        """Тест полного цикла аутентификации через chain API."""

        # Определяем шаги цепочки
        steps = [
            ChainStep(
                method="POST",
                url="/api/v1/auth/register",
                data={
                    "email": "chain@example.com",
                    "username": "chainuser",
                    "full_name": "Chain User",
                    "password": "ChainPassword123!",
                    "password_confirm": "ChainPassword123!",
                },
                expected_status=201,
                description="Регистрация пользователя",
                extract_data=lambda r: {"tokens": r.json()["tokens"]},
            ),
            ChainStep(
                method="GET",
                url="/api/v1/auth/me",
                headers=lambda ctx: {"Authorization": f"Bearer {ctx['tokens']['access_token']}"},
                expected_status=200,
                description="Получение профиля пользователя",
                validate_response=lambda r, ctx: r.json()["email"] == "chain@example.com",
            ),
            ChainStep(
                method="POST",
                url="/api/v1/auth/refresh",
                data=lambda ctx: {"refresh_token": ctx["tokens"]["refresh_token"]},
                expected_status=200,
                description="Обновление токенов",
                extract_data=lambda r: {"new_tokens": r.json()},
            ),
            ChainStep(
                method="POST",
                url="/api/v1/auth/logout",
                data=lambda ctx: {"refresh_token": ctx["new_tokens"]["refresh_token"]},
                expected_status=204,
                description="Выход из системы",
            ),
        ]

        # Выполняем цепочку тестов
        responses = await enhanced_client.run_test_chain(steps)

        assert len(responses) == 4
        assert all(r.status_code in [200, 201, 204] for r in responses)


# === ДЕМОНСТРАЦИОННЫЕ ТЕСТЫ ===


@pytest.mark.demo
class TestEnhancedClientDemo:
    """Демонстрационные тесты новых возможностей."""

    @pytest.mark.asyncio
    async def test_all_features_demo(self, enhanced_client: AsyncApiTestClient):
        """Демонстрация всех новых возможностей клиента."""

        print("\n🚀 Демонстрация расширенного клиента API")

        # 1. Снимки API
        print("\n📸 Создание снимков API...")
        snapshot = await enhanced_client.create_api_snapshot("/")
        print(f"   Снимок создан: {snapshot.checksum}")

        # 2. Мокирование внешних API
        print("\n🎭 Мокирование внешних API...")
        enhanced_client.mock_external_api("https://external.example.com/api", {"status": "mocked"}, status_code=200)
        print("   Внешний API замокан")

        # 3. Performance tracking
        print("\n⚡ Трекинг производительности...")
        enhanced_client.enable_performance_tracking()

        # Делаем несколько запросов
        for i in range(3):
            await enhanced_client.get("/")

        stats = enhanced_client.get_performance_stats()
        print(f"   Статистика: {stats['total_requests']} запросов, среднее время: {stats['avg_response_time']:.3f}s")

        # 4. Тестовые сессии
        print("\n📊 Тестовая сессия...")
        async with enhanced_client.test_session(TestScenarioType.INTEGRATION) as session:
            await enhanced_client.get("/health")
            print(f"   Сессия: {session.session_id}, метрик: {len(session.metrics)}")

        # 5. Chain тестирование
        print("\n🔗 Chain тестирование...")
        chain = [
            ChainStep("GET", "/", description="Главная страница"),
            ChainStep("GET", "/health", description="Проверка здоровья"),
        ]

        responses = await enhanced_client.run_test_chain(chain)
        print(f"   Выполнено {len(responses)} шагов в цепочке")

        print("\n✅ Демонстрация завершена!")


if __name__ == "__main__":
    # Запуск демонстрационных тестов
    pytest.main([__file__ + "::TestEnhancedClientDemo::test_all_features_demo", "-v", "-s"])
