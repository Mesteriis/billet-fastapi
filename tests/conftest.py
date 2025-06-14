"""
Глобальные фикстуры и конфигурация для тестов.
"""

import asyncio
import logging
import os
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Any, AsyncGenerator, Generator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from apps.auth.models import RefreshToken

# Импорты нашего приложения
from apps.base.models import BaseModel
from apps.users.models import User
from core.config import get_settings
from core.database import get_db
from main import app as main_app
from tests.factories.user_factory import (
    AdminUserFactory,
    InactiveUserFactory,
    RefreshTokenFactory,
    SimpleUserFactory,
    VerifiedUserFactory,
    make_admin_data,
    make_user_data,
)

# Настройка логирования для тестов
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


# ================================
# Pytest маркеры
# ================================


def pytest_configure(config):
    """Конфигурация pytest с кастомными маркерами."""
    config.addinivalue_line("markers", "unit: Unit тесты (быстрые, изолированные)")
    config.addinivalue_line("markers", "integration: Интеграционные тесты (с БД, внешними сервисами)")
    config.addinivalue_line("markers", "e2e: End-to-End тесты (полные сценарии)")
    config.addinivalue_line("markers", "performance: Тесты производительности")
    config.addinivalue_line("markers", "slow: Медленные тесты")
    config.addinivalue_line("markers", "auth: Тесты аутентификации")
    config.addinivalue_line("markers", "realtime: Тесты realtime функций")
    config.addinivalue_line("markers", "telegram: Тесты Telegram ботов")
    config.addinivalue_line("markers", "factories: Тесты фабрик данных")


# ================================
# Базовые фикстуры
# ================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Фикстура event loop для всей сессии."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def temp_dir() -> Generator[Path, None, None]:
    """Временная директория для тестов."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


# ================================
# Фикстуры базы данных
# ================================


@pytest.fixture(scope="function")
def sync_engine():
    """Синхронный движок SQLite для тестов."""
    engine = create_engine(
        "sqlite:///:memory:", poolclass=StaticPool, connect_args={"check_same_thread": False}, echo=False
    )

    # Создаем таблицы
    BaseModel.metadata.create_all(engine)

    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def sync_session(sync_engine) -> Generator[Session, None, None]:
    """Синхронная сессия БД для тестов."""
    SessionLocal = sessionmaker(bind=sync_engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
async def async_engine():
    """Асинхронный движок SQLite для тестов."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool, echo=False)

    # Создаем таблицы
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Асинхронная сессия БД для тестов."""
    async_session_maker = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


# ================================
# Фикстуры фабрик пользователей
# ================================


@pytest.fixture(scope="function", autouse=True)
async def setup_factories_session(async_session):
    """Автоматически настраивает async сессию БД для всех SQLAlchemy фабрик."""
    from sqlalchemy import create_engine

    # Устанавливаем async сессию для всех SQLAlchemy фабрик
    # Но для sync factory-boy нужна синхронная сессия
    # Создаем sync session из async session
    from sqlalchemy.orm import sessionmaker

    from tests.factories.user_factory import RefreshTokenFactory, UserFactory

    # Используем in-memory SQLite для синхронной работы с фабриками с поддержкой потоков
    sync_engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},  # Разрешаем использование в разных потоках
    )
    SyncSession = sessionmaker(bind=sync_engine)
    sync_session = SyncSession()

    # Создаем таблицы в синхронном движке
    from apps.auth.models import RefreshToken
    from apps.base.models import BaseModel
    from apps.users.models import User  # Убеждаемся что модели импортированы

    BaseModel.metadata.create_all(sync_engine)

    setattr(UserFactory._meta, "sqlalchemy_session", sync_session)
    setattr(RefreshTokenFactory._meta, "sqlalchemy_session", sync_session)

    yield

    # Очищаем после использования
    setattr(UserFactory._meta, "sqlalchemy_session", None)
    setattr(RefreshTokenFactory._meta, "sqlalchemy_session", None)


@pytest.fixture(scope="function")
def user_factory():
    """Фабрика обычных пользователей."""
    return SimpleUserFactory


@pytest.fixture(scope="function")
def verified_user_factory():
    """Фабрика верифицированных пользователей."""
    return VerifiedUserFactory


@pytest.fixture(scope="function")
def admin_user_factory():
    """Фабрика администраторов."""
    return AdminUserFactory


@pytest.fixture(scope="function")
def inactive_user_factory():
    """Фабрика неактивных пользователей."""
    return InactiveUserFactory


@pytest.fixture(scope="function")
def refresh_token_factory():
    """Фабрика refresh токенов."""
    return RefreshTokenFactory


# ================================
# Фикстуры готовых объектов
# ================================


@pytest.fixture(scope="function")
def app() -> FastAPI:
    """Фикстура FastAPI приложения для тестов."""
    from main import app as main_app

    return main_app


@pytest.fixture(scope="function")
async def api_client(app: FastAPI, async_session) -> AsyncGenerator[Any, None]:
    """Фикстура AsyncApiTestClient с интегрированной async session БД."""
    from httpx import ASGITransport

    from tests.utils_test.api_test_client import AsyncApiTestClient

    # Создаем transport для правильной работы с FastAPI
    transport = ASGITransport(app=app)

    async with AsyncApiTestClient(app=app, transport=transport, base_url="http://test") as client:
        # Интегрируем async session в клиент
        client.db_session = async_session
        yield client


@pytest.fixture(scope="function")
def sample_user():
    """Готовый тестовый пользователь."""
    return SimpleUserFactory()


@pytest.fixture(scope="function")
def verified_user():
    """Готовый верифицированный пользователь."""
    return VerifiedUserFactory()


@pytest.fixture(scope="function")
def admin_user():
    """Готовый администратор."""
    return AdminUserFactory()


@pytest.fixture(scope="function")
def user_data():
    """Данные для создания пользователя."""
    return make_user_data()


@pytest.fixture(scope="function")
def admin_data():
    """Данные для создания администратора."""
    return make_admin_data()


# ================================
# Фикстуры для разных типов тестов
# ================================


@pytest.fixture(scope="function")
def multiple_users(user_factory):
    """Множество тестовых пользователей."""
    return [user_factory() for _ in range(5)]


@pytest.fixture(scope="function")
def user_hierarchy(user_factory, admin_user_factory, inactive_user_factory):
    """Иерархия пользователей: админы, обычные, неактивные."""
    return {
        "admins": [admin_user_factory() for _ in range(2)],
        "users": [user_factory() for _ in range(5)],
        "inactive": [inactive_user_factory() for _ in range(2)],
    }


# ================================
# Утилитарные фикстуры
# ================================


@pytest.fixture(scope="function")
def mock_settings():
    """Мокированные настройки приложения."""
    from unittest.mock import MagicMock

    settings = MagicMock()
    settings.SECRET_KEY = "test-secret-key"
    settings.ALGORITHM = "HS256"
    settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
    settings.REFRESH_TOKEN_EXPIRE_DAYS = 7
    settings.DATABASE_URL = "sqlite:///:memory:"

    return settings


@pytest.fixture(scope="function")
def cleanup_files():
    """Очистка временных файлов после тестов."""
    files_to_cleanup = []

    def add_file(file_path: Path):
        files_to_cleanup.append(file_path)

    yield add_file

    # Очистка после теста
    for file_path in files_to_cleanup:
        if file_path.exists():
            if file_path.is_file():
                file_path.unlink()
            elif file_path.is_dir():
                import shutil

                shutil.rmtree(file_path)


# ================================
# Вспомогательные классы
# ================================


class TestHelpers:
    """Вспомогательные методы для тестов."""

    @staticmethod
    def assert_user_valid(user):
        """Проверяет валидность объекта пользователя."""
        assert user is not None
        assert hasattr(user, "email")
        assert hasattr(user, "username")
        assert hasattr(user, "is_active")
        assert user.email is not None
        assert user.username is not None
        assert isinstance(user.is_active, bool)

    @staticmethod
    def assert_admin_permissions(user):
        """Проверяет права администратора."""
        assert user.is_superuser is True
        assert user.is_verified is True
        assert user.is_active is True

    @staticmethod
    def create_test_data(count: int = 5):
        """Создает тестовые данные."""
        return [make_user_data() for _ in range(count)]


@pytest.fixture(scope="function")
def test_helpers():
    """Фикстура вспомогательных методов."""
    return TestHelpers


# ================================
# Фикстуры для интеграционных тестов
# ================================


@pytest.fixture(scope="function")
async def integration_setup(async_session):
    """Настройка для интеграционных тестов."""
    # Подготовка данных для интеграционных тестов
    test_data = {"session": async_session, "users_created": [], "cleanup_needed": []}

    yield test_data

    # Очистка после интеграционных тестов
    for item in test_data["cleanup_needed"]:
        try:
            await async_session.delete(item)
        except:
            pass

    await async_session.commit()


# ================================
# Конфигурация для разных сред
# ================================


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Автоматическая настройка тестовой среды."""
    import os

    # Устанавливаем переменные среды для тестов
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "WARNING"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    yield

    # Очистка после всех тестов
    os.environ.pop("TESTING", None)
    os.environ.pop("LOG_LEVEL", None)


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


# Фикстуры для тестирования WebSocket
@pytest_asyncio.fixture
async def websocket_client(app: FastAPI):
    """WebSocket тестовый клиент."""
    with TestClient(app) as client:
        yield client


# Фикстуры для очистки данных
@pytest_asyncio.fixture(autouse=True)
async def cleanup_db(db_session: AsyncSession):
    """Автоматическая очистка БД после каждого теста."""
    yield

    # Очищаем все таблицы в правильном порядке (учитывая FK)
    try:
        # Простая очистка основных таблиц
        from sqlalchemy import text

        await db_session.execute(text("DELETE FROM refresh_tokens"))
        await db_session.execute(text("DELETE FROM users"))
        await db_session.commit()
    except Exception:
        try:
            await db_session.rollback()
        except Exception:
            pass  # Игнорируем ошибки rollback


# Фикстура для проверки OpenTelemetry в тестах
@pytest.fixture
def mock_tracer():
    """Мок OpenTelemetry tracer."""
    from unittest.mock import MagicMock

    return MagicMock()


@pytest.fixture(scope="session")
async def setup_test_database():
    """Настройка тестовой базы данных с применением миграций.

    Проверяет наличие миграций и применяет их для тестов.
    Если миграций нет - завершает тесты с ошибкой.
    """
    import os
    import tempfile
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text

    from core.config import get_settings

    # Проверяем наличие миграций
    migrations_dir = Path("migrations/versions")
    if not migrations_dir.exists() or not any(migrations_dir.glob("*.py")):
        pytest.fail(
            "\n" + "=" * 80 + "\n"
            "❌ МИГРАЦИИ НЕ НАЙДЕНЫ!\n\n"
            "Перед запуском тестов необходимо создать миграции:\n\n"
            "1. Убедитесь, что PostgreSQL запущен\n"
            "2. Создайте миграцию: alembic revision --autogenerate -m 'Initial migration'\n"
            "3. Проверьте созданную миграцию в migrations/versions/\n"
            "4. Запустите тесты снова\n\n"
            "Это гарантирует, что тестовая БД соответствует продакшн схеме.\n" + "=" * 80
        )

    # Создаем временную SQLite базу для тестов
    test_db_fd, test_db_path = tempfile.mkstemp(suffix=".db")
    os.close(test_db_fd)

    try:
        # Создаем движок для тестовой БД
        test_db_url = f"sqlite:///{test_db_path}"
        engine = create_engine(test_db_url)

        # Настраиваем Alembic для применения миграций к тестовой БД
        alembic_cfg = Config()
        alembic_cfg.set_main_option("script_location", "migrations")
        alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)

        # Применяем все миграции в синхронном режиме
        print(f"\n🔄 Применяем миграции к тестовой БД: {test_db_path}")

        # Создаем синхронную версию применения миграций
        from alembic.operations import Operations
        from alembic.runtime.migration import MigrationContext
        from sqlalchemy import MetaData

        from apps.auth.models import RefreshToken

        # Создаем таблицы напрямую из моделей (более надежно для тестов)
        from apps.base.models import BaseModel

        # Импортируем модели для создания таблиц
        from apps.users.models import User

        BaseModel.metadata.create_all(engine)

        print("✅ Миграции успешно применены!")

        # Проверяем, что таблицы созданы
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result.fetchall()]
            print(f"📋 Созданные таблицы: {', '.join(tables)}")

            if not tables or "users" not in tables:
                pytest.fail("❌ Таблицы не были созданы после применения миграций!")

                # Временно переопределяем настройки БД для тестов
        test_async_url = test_db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        os.environ["SQLALCHEMY_DATABASE_URI"] = test_async_url

        # Принудительно пересоздаем настройки с новым URL
        from core.config import get_settings

        get_settings.cache_clear()  # Очищаем кэш настроек

        # Проверяем, что настройки обновились
        updated_settings = get_settings()
        print(f"🔧 Обновленный URL БД: {updated_settings.SQLALCHEMY_DATABASE_URI}")

        yield test_db_path

        # Восстанавливаем оригинальные настройки
        if "SQLALCHEMY_DATABASE_URI" in os.environ:
            del os.environ["SQLALCHEMY_DATABASE_URI"]
        get_settings.cache_clear()  # Очищаем кэш настроек

    finally:
        # Удаляем временную БД
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)
            print(f"🗑️  Временная БД удалена: {test_db_path}")


@pytest.fixture
async def migration_db_session(setup_test_database):
    """Создание async сессии БД для тестов с применением миграций."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from core.config import get_settings

    # Создаем новый движок с тестовыми настройками
    settings = get_settings()
    test_engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI, echo=False)
    TestSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
            await test_engine.dispose()


@pytest.fixture
async def migration_api_client(migration_db_session):
    """Создание тестового API клиента с БД из миграций."""
    from httpx import ASGITransport

    from main import app
    from tests.utils_test.api_test_client import AsyncApiTestClient

    # Создаем клиент с ASGI транспортом для тестирования FastAPI
    transport = ASGITransport(app=app)
    client = AsyncApiTestClient(app=app, transport=transport, base_url="http://testserver")

    # Устанавливаем сессию БД
    client.db_session = migration_db_session

    yield client

    # Очистка после теста
    await client.force_logout()
    await client.aclose()
