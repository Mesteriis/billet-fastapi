"""
Конфигурация pytest для всех тестов.
"""

import asyncio
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Импорты для pytest-mock-resources
from pytest_mock_resources import create_sqlite_fixture

# Импорты для pytest-rabbitmq
from pytest_rabbitmq import factories
from sqlalchemy.ext.asyncio import AsyncSession

# Импорт конфигурации логирования для тестов
from tests.conftest_logging import capture_logs, quiet_logger, setup_logging_for_tests, verbose_logger

from apps.auth.auth_service import auth_service

# Импорты нашего приложения
from apps.base.models import BaseModel
from apps.users.models import User
from apps.users.schemas import UserCreate
from core.config import get_settings
from core.database import get_db
from main import app as main_app


# Настройки для тестов
@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для async тестов."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Фикстура SQLite с нашими моделями
pg = create_sqlite_fixture(
    BaseModel,  # Наша базовая модель
    session=True,
)

# Фикстура RabbitMQ
from pathlib import Path

rabbitmq_proc = factories.rabbitmq_proc(port=None, logsdir=Path("/tmp"))
rabbitmq = factories.rabbitmq("rabbitmq_proc")


@pytest_asyncio.fixture
async def db_session(pg: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Фикстура сессии базы данных для тестов."""
    yield pg


@pytest.fixture
def override_get_db(db_session: AsyncSession):
    """Переопределяет зависимость get_db для тестов."""

    async def _get_test_db():
        yield db_session

    return _get_test_db


@pytest.fixture
def app(override_get_db) -> FastAPI:
    """Фикстура FastAPI приложения для тестов."""
    # Переопределяем зависимость базы данных
    main_app.dependency_overrides[get_db] = override_get_db

    yield main_app

    # Очищаем переопределения
    main_app.dependency_overrides.clear()


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """Синхронный тестовый клиент."""
    with TestClient(app) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Асинхронный тестовый клиент."""
    from httpx import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client


# Фикстуры для тестовых пользователей
@pytest_asyncio.fixture
async def test_user_data() -> UserCreate:
    """Данные тестового пользователя."""
    return UserCreate(
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        password="TestPassword123!",
        password_confirm="TestPassword123!",
    )


@pytest_asyncio.fixture
async def admin_user_data() -> UserCreate:
    """Данные тестового админа."""
    return UserCreate(
        email="admin@example.com",
        username="admin",
        full_name="Admin User",
        password="AdminPassword123!",
        password_confirm="AdminPassword123!",
    )


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_user_data: UserCreate) -> User:
    """Создает тестового пользователя в БД."""
    user = await auth_service.register_user(db_session, user_data=test_user_data, auto_verify=True)
    await db_session.commit()

    # Получаем полного пользователя из БД
    from src.apps.users.repository import UserRepository

    repo = UserRepository()
    db_user = await repo.get_by_email(db_session, email=test_user_data.email)
    return db_user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession, admin_user_data: UserCreate) -> User:
    """Создает тестового админа в БД."""
    user = await auth_service.register_user(db_session, user_data=admin_user_data, auto_verify=True)

    # Делаем пользователя админом
    from src.apps.users.repository import UserRepository

    repo = UserRepository()
    db_user = await repo.get_by_email(db_session, email=admin_user_data.email)
    await repo.update(db_session, db_obj=db_user, obj_in={"is_superuser": True})
    await db_session.commit()

    return db_user


@pytest_asyncio.fixture
async def auth_headers(db_session: AsyncSession, test_user: User) -> dict[str, str]:
    """Создает заголовки аутентификации для тестов."""
    # Входим в систему
    login_response = await auth_service.login(db_session, email=test_user.email, password="TestPassword123!")

    access_token = login_response.tokens.access_token
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture
async def admin_auth_headers(db_session: AsyncSession, admin_user: User) -> dict[str, str]:
    """Создает заголовки аутентификации для админа."""
    # Входим в систему как админ
    login_response = await auth_service.login(db_session, email=admin_user.email, password="AdminPassword123!")

    access_token = login_response.tokens.access_token
    return {"Authorization": f"Bearer {access_token}"}


# Фикстуры для мокирования
@pytest.fixture
def mock_redis():
    """Мок Redis клиента."""
    return AsyncMock()


@pytest.fixture
def mock_email_service():
    """Мок сервиса отправки email."""
    return AsyncMock()


@pytest.fixture
def mock_sms_service():
    """Мок сервиса отправки SMS."""
    return AsyncMock()


# Фикстуры настроек для тестов
@pytest.fixture
def test_settings():
    """Настройки для тестов."""
    settings = get_settings()
    # Переопределяем настройки для тестов
    settings.TRACING_ENABLED = False
    settings.SECRET_KEY = "test-secret-key"
    settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
    settings.REFRESH_TOKEN_EXPIRE_DAYS = 7
    return settings


# Маркеры pytest
def pytest_configure(config):
    """Конфигурация pytest."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "auth: marks tests as authentication tests")
    config.addinivalue_line("markers", "users: marks tests as user management tests")


# Фикстуры для очистки данных
@pytest_asyncio.fixture(autouse=True)
async def cleanup_db(db_session: AsyncSession):
    """Автоматическая очистка БД после каждого теста."""
    yield

    # Очищаем все таблицы в правильном порядке (учитывая FK)
    await db_session.execute("DELETE FROM refresh_tokens")
    await db_session.execute("DELETE FROM users")
    await db_session.commit()


# Фикстура для проверки OpenTelemetry в тестах
@pytest.fixture
def mock_tracer():
    """Мок OpenTelemetry tracer."""
    from unittest.mock import MagicMock

    return MagicMock()


# Фикстура для тестирования WebSocket
@pytest_asyncio.fixture
async def websocket_client(app: FastAPI):
    """WebSocket тестовый клиент."""
    from fastapi.testclient import TestClient

    return TestClient(app)


# Хелперы для тестов
class TestHelpers:
    """Вспомогательные методы для тестов."""

    @staticmethod
    async def create_test_users(db_session: AsyncSession, count: int = 5):
        """Создает несколько тестовых пользователей."""
        users = []
        for i in range(count):
            user_data = UserCreate(
                email=f"user{i}@example.com",
                username=f"user{i}",
                full_name=f"User {i}",
                password="TestPassword123!",
                password_confirm="TestPassword123!",
            )
            user = await auth_service.register_user(db_session, user_data=user_data, auto_verify=True)
            users.append(user)

        await db_session.commit()
        return users

    @staticmethod
    def assert_user_response(response_data: dict, expected_email: str):
        """Проверяет структуру ответа пользователя."""
        assert "id" in response_data
        assert "email" in response_data
        assert "username" in response_data
        assert "created_at" in response_data
        assert "updated_at" in response_data
        assert response_data["email"] == expected_email
        # Проверяем, что пароль не возвращается
        assert "password" not in response_data
        assert "hashed_password" not in response_data

    @staticmethod
    def assert_token_response(response_data: dict):
        """Проверяет структуру ответа с токенами."""
        assert "access_token" in response_data
        assert "refresh_token" in response_data
        assert "token_type" in response_data
        assert "expires_in" in response_data
        assert response_data["token_type"] == "bearer"


@pytest.fixture
def helpers():
    """Фикстура с вспомогательными методами."""
    return TestHelpers


# Конфигурация pytest-alembic
@pytest.fixture
def alembic_config():
    """Конфигурация Alembic для тестов."""
    import tomllib
    from pathlib import Path

    from alembic.config import Config

    # Создаем конфигурацию Alembic
    config = Config()

    # Читаем настройки из pyproject.toml
    pyproject_path = Path("pyproject.toml")
    if pyproject_path.exists():
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)
            alembic_settings = pyproject_data.get("tool", {}).get("alembic", {})

            # Устанавливаем настройки
            for key, value in alembic_settings.items():
                config.set_main_option(key.replace("_", "-"), str(value))

    # Устанавливаем URL тестовой базы данных
    test_settings = get_settings()
    config.set_main_option("sqlalchemy.url", test_settings.SQLALCHEMY_DATABASE_URI)

    return config


@pytest.fixture
def alembic_engine(pg):
    """Engine для Alembic тестов."""
    return pg.get_bind().sync_engine
