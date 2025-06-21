"""
Conftest для API тестов приложений.

Настройка AsyncApiTestClient и фабрик для auth и users API тестов.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.models.auth_models import OrbitalToken, RefreshToken, UserSession

# Импорты моделей
from apps.users.models.user_models import User, UserProfile
from main import app
from tests.factories.auth_factories import OrbitalTokenFactory, RefreshTokenFactory, UserSessionFactory
from tests.factories.base_factories import setup_factory_model, setup_factory_session
from tests.factories.user_factories import UserFactory, UserProfileFactory


@pytest_asyncio.fixture(scope="function")
async def client(async_session: AsyncSession):
    """AsyncClient для API тестов с переопределенной зависимостью БД."""
    from core.database import get_async_session

    async def override_get_async_session():
        """Переопределяем зависимость БД для тестов."""
        yield async_session

    # Переопределяем зависимость
    app.dependency_overrides[get_async_session] = override_get_async_session

    try:
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client
    finally:
        # Очищаем переопределения
        app.dependency_overrides.clear()


# Фикстуры фабрик для API тестов
@pytest.fixture(scope="function")
def user_factory(async_session: AsyncSession):
    """Фабрика пользователей для API тестов."""
    setup_factory_model(UserFactory, User)
    setup_factory_session(UserFactory, async_session)
    return UserFactory


@pytest.fixture(scope="function")
def user_profile_factory(async_session: AsyncSession):
    """Фабрика профилей пользователей для API тестов."""
    setup_factory_model(UserProfileFactory, UserProfile)
    setup_factory_session(UserProfileFactory, async_session)
    return UserProfileFactory


@pytest.fixture(scope="function")
def refresh_token_factory(async_session: AsyncSession):
    """Фабрика refresh токенов для API тестов."""
    setup_factory_model(RefreshTokenFactory, RefreshToken)
    setup_factory_session(RefreshTokenFactory, async_session)
    return RefreshTokenFactory


@pytest.fixture(scope="function")
def user_session_factory(async_session: AsyncSession):
    """Фабрика пользовательских сессий для API тестов."""
    setup_factory_model(UserSessionFactory, UserSession)
    setup_factory_session(UserSessionFactory, async_session)
    return UserSessionFactory


@pytest.fixture(scope="function")
def orbital_token_factory(async_session: AsyncSession):
    """Фабрика orbital токенов для API тестов."""
    setup_factory_model(OrbitalTokenFactory, OrbitalToken)
    setup_factory_session(OrbitalTokenFactory, async_session)
    return OrbitalTokenFactory


# Вспомогательные фикстуры
@pytest_asyncio.fixture(scope="function")
async def test_user(user_factory):
    """Создает тестового пользователя для API тестов."""
    return await user_factory.create(username="apiuser", email="api@test.com", is_active=True, is_verified=True)


@pytest_asyncio.fixture(scope="function")
async def admin_user(user_factory):
    """Создает админ пользователя для API тестов."""
    return await user_factory.create(
        username="apiadmin", email="apiadmin@test.com", is_active=True, is_verified=True, is_superuser=True
    )
