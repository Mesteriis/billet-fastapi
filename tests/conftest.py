"""
Главный conftest.py для всех тестов.

Настройка:
- AsyncApiTestClient для API тестов
- Фабрики с правильной настройкой сессий
- База данных для тестов
- Логирование
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import alembic.command
import alembic.config
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from apps.auth.models.auth_models import OrbitalToken, RefreshToken, UserSession  # noqa: F401

# Импорты моделей
from apps.users.models.user_models import User, UserProfile  # noqa: F401
from core.database import get_db  # noqa: F401
from main import app  # noqa: F401
from main import settings  # noqa: F401
from tests.factories.auth_factories import OrbitalTokenFactory, RefreshTokenFactory, UserSessionFactory
from tests.factories.base_factories import setup_factory_model, setup_factory_session
from tests.factories.user_factories import UserFactory, UserProfileFactory
from tests.utils_test.api_test_client import AsyncApiTestClient  # noqa: F401

# Импортируем фикстуры из системы моков
from tests.utils_test.mock_system import auto_mock_all, mock_manager  # noqa: F401

# Настройка логирования для тестов - максимально агрессивный подход
# Полностью отключаем все логирование кроме CRITICAL
logging.disable(logging.INFO)

# Создаем наш тестовый логгер с принудительным включением
logger = logging.getLogger("test_session")
logger.setLevel(logging.INFO)
logger.disabled = False  # Принудительно включаем наш логгер

# URL для тестовой БД (используем in-memory SQLite для простоты)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


def pytest_terminal_summary(terminalreporter, exitstatus):
    total = terminalreporter._numcollected
    passed = len(terminalreporter.stats.get("passed", []))
    failed = len(terminalreporter.stats.get("failed", []))
    terminalreporter.write_sep("-", f"✔ Passed: {passed} / {total}, ❌ Failed: {failed}")


def is_ci_environment() -> bool:
    """Проверяет, запущены ли тесты в CI окружении."""
    ci_indicators = [
        "CI",
        "CONTINUOUS_INTEGRATION",
        "GITHUB_ACTIONS",
        "GITLAB_CI",
        "JENKINS_URL",
        "BUILDKITE",
        "CIRCLECI",
        "TRAVIS",
        "APPVEYOR",
        "BUILD_NUMBER",
        "BUILD_ID",
    ]
    return any(os.getenv(indicator) for indicator in ci_indicators)


@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """Максимально агрессивная настройка - отключаем все кроме критических ошибок."""
    # Полное отключение логирования
    logging.disable(logging.INFO)

    # Включаем только наш тестовый логгер
    test_logger = logging.getLogger("test_session")
    test_logger.disabled = False
    test_logger.setLevel(logging.INFO)

    yield

    # Восстанавливаем логирование после тестов
    logging.disable(logging.NOTSET)


@pytest.fixture(scope="session", autouse=True)
def cleanup_project_artifacts():
    """
    Очищает проект от артефактов перед запуском тестов.

    Выполняется только при ручном запуске тестов (не в CI).
    Можно отключить через переменную окружения SKIP_CLEANUP_ARTIFACTS=1

    Пример отключения:
        SKIP_CLEANUP_ARTIFACTS=1 pytest tests/
    """
    # Проверяем, не отключена ли очистка явно
    if os.getenv("SKIP_CLEANUP_ARTIFACTS"):
        logger.info("🚫 Очистка проекта отключена (SKIP_CLEANUP_ARTIFACTS=1)")
        yield
        return

    if is_ci_environment():
        logger.info("🏗️ Обнаружено CI окружение - очистка проекта пропущена")
        yield
        return

    try:
        # Импортируем класс очистки
        import sys

        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root / "scripts"))

        try:
            from cleanup_project import ProjectCleaner  # type: ignore
        except ImportError as ie:
            logger.warning(f"⚠️ Не удалось импортировать модуль очистки: {ie}")
            yield
            return

        logger.info("🧹 Запуск очистки проекта от артефактов...")

        # Создаем очиститель с минимальным выводом
        cleaner = ProjectCleaner(project_root=project_root, dry_run=False, verbose=False)

        # Запускаем очистку
        success = cleaner.run()

        if success and cleaner.removed_items:
            logger.info(
                f"✨ Очистка завершена: удалено {len(cleaner.removed_items)} элементов, "
                f"освобождено {cleaner.format_size(cleaner.total_size_saved)}"
            )
        elif success:
            logger.info("✨ Проект уже чистый")
        else:
            logger.warning("⚠️ Очистка завершилась с ошибками")

    except Exception as e:
        logger.warning(f"⚠️ Ошибка при очистке проекта: {e}")

    yield


@pytest.fixture(scope="session")
def event_loop():
    """Создаем event loop для всей сессии тестов."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def temp_dir():
    """Временная директория для тестов."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def postgres_container():
    """Оптимизированный PostgreSQL контейнер для тестов."""
    try:
        from testcontainers.postgres import PostgresContainer

        # Используем более стабильную конфигурацию с trust auth
        postgres = (
            PostgresContainer(
                image="postgres:15-alpine",
                driver=None,  # Убираем explicit driver, пусть SQLAlchemy сам определяет
            )
            .with_env("POSTGRES_HOST_AUTH_METHOD", "trust")
            .with_env("POSTGRES_INITDB_ARGS", "--auth-host=trust --auth-local=trust")
        )

        with postgres as pg:
            # Получаем базовый URL и конвертируем в asyncpg
            base_url = pg.get_connection_url()

            # Преобразуем в async URL с правильным драйвером
            if "postgresql://" in base_url and "+asyncpg" not in base_url:
                async_url = base_url.replace("postgresql://", "postgresql+asyncpg://")
            else:
                async_url = base_url

            # Создаем mock объект с async URL
            class AsyncPostgresContainer:
                def get_connection_url(self):
                    return async_url

            yield AsyncPostgresContainer()

    except Exception as e:
        logger.warning(f"PostgreSQL container failed: {e}")
        logger.info("🔄 Переключаюсь на SQLite для тестов")

        # Fallback на SQLite с async поддержкой
        class SQLiteContainer:
            def get_connection_url(self):
                return "sqlite+aiosqlite:///:memory:"

        yield SQLiteContainer()


@pytest_asyncio.fixture(scope="function")
async def async_engine(postgres_container, event_loop):
    """Создаем async engine для тестов."""
    uri = postgres_container.get_connection_url()

    logger.info(f"🔗 Database URI: {uri[:50]}...")

    # Конфигурация для engine
    engine_config = {
        "echo": False,  # Отключаем эхо для изоляции
        "poolclass": NullPool,  # Используем NullPool для избежания проблем
        "pool_pre_ping": True,  # Проверяем соединения
        "pool_recycle": 300,  # Перезапускаем соединения каждые 5 минут
    }

    # Специальные параметры для asyncpg
    if "asyncpg" in uri:
        engine_config["connect_args"] = {
            "server_settings": {
                "application_name": "pytest_test",
                "timezone": "UTC",
            },
            "command_timeout": 60,
        }
    # Специальные параметры для aiosqlite
    elif "aiosqlite" in uri:
        engine_config["connect_args"] = {
            "check_same_thread": False,
        }

    engine = create_async_engine(uri, **engine_config)

    try:
        # Тестируем подключение
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ Подключение к БД успешно")

        yield engine

    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД: {e}")
        raise
    finally:
        try:
            await engine.dispose()
        except Exception as e:
            logger.warning(f"Warning during engine disposal: {e}")


@pytest_asyncio.fixture(scope="function")
async def setup_alembic_migrations(async_engine) -> AsyncGenerator[None, None]:
    """
    Создает таблицы через SQLAlchemy metadata для тестов.

    ВРЕМЕННО: Alembic отключен для избежания конфликтов с контейнерной БД.
    """
    # Временно отключаем Alembic для тестов и используем только metadata
    logger.info("📋 Создаю таблицы через SQLAlchemy metadata (Alembic отключен для тестов)")
    await _create_tables_via_metadata(async_engine)

    yield

    # Очистка данных после тестов (но не удаление схемы)
    await _cleanup_app_data(async_engine)


async def _create_tables_via_metadata(async_engine) -> None:
    """Создает таблицы приложения через SQLAlchemy metadata (fallback)."""
    try:
        from apps.auth.models.auth_models import OrbitalToken, RefreshToken, UserSession
        from apps.users.models.user_models import User, UserProfile

        async with async_engine.begin() as conn:
            # Создаем все таблицы приложения
            await conn.run_sync(User.metadata.create_all)

        logger.info("✅ Таблицы созданы через SQLAlchemy metadata")

    except Exception as e:
        logger.error(f"❌ Ошибка создания таблиц: {e}")
        raise


async def _cleanup_app_data(async_engine) -> None:
    """Очищает данные приложения между тестами (без удаления схемы)."""
    try:
        async with async_engine.begin() as conn:
            # Определяем тип БД для правильной очистки
            db_url = str(async_engine.url)

            if "postgresql" in db_url:
                # PostgreSQL очистка
                await conn.execute(text("SET session_replication_role = replica"))

                cleanup_tables = ["orbital_tokens", "user_sessions", "refresh_tokens", "user_profiles", "users"]
                for table in cleanup_tables:
                    try:
                        await conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
                    except Exception as e:
                        # Игнорируем ошибки для несуществующих таблиц
                        logger.debug(f"Cleanup info for {table}: {e}")

                await conn.execute(text("SET session_replication_role = DEFAULT"))

            elif "sqlite" in db_url:
                # SQLite очистка
                cleanup_tables = ["orbital_tokens", "user_sessions", "refresh_tokens", "user_profiles", "users"]
                for table in cleanup_tables:
                    try:
                        await conn.execute(text(f"DELETE FROM {table}"))
                    except Exception as e:
                        logger.debug(f"Cleanup info for {table}: {e}")

        logger.debug("✅ Данные приложения очищены")

    except Exception as e:
        logger.debug(f"Cleanup info: {e}")


@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine, setup_alembic_migrations) -> AsyncGenerator[AsyncSession, None]:
    """Создаем async session для каждого теста."""
    async_session_maker = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,  # Отключаем автофлуш для контроля
        autocommit=False,  # Явно отключаем autocommit
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()  # Откатываем изменения после каждого теста


@pytest_asyncio.fixture(scope="function")
async def setup_test_models(async_session) -> AsyncGenerator[AsyncSession, None]:
    """
    Настраивает тестовые модели и очищает данные после каждого теста.
    """
    from tests.core.base.test_repo.modesl_for_test import TestBaseModel

    # Создаем таблицы перед тестом
    async with async_session.bind.begin() as conn:
        await conn.run_sync(TestBaseModel.metadata.create_all)

    yield async_session

    # УЛУЧШЕННАЯ система очистки данных с правильной обработкой транзакций
    await _cleanup_test_data(async_session)


async def _cleanup_test_data(session: AsyncSession) -> None:
    """
    Улучшенная очистка тестовых данных между тестами.
    """
    try:
        # Сначала проверяем состояние транзакции
        if session.in_transaction():
            try:
                await session.rollback()
            except Exception:
                pass

        # Используем сессию для очистки данных
        # Отключаем все constraints для быстрой очистки
        await session.execute(text("SET session_replication_role = replica"))

        # Очищаем все тестовые таблицы одним запросом
        await session.execute(
            text("""
            TRUNCATE TABLE 
                test_post_tags,
                test_comments, 
                test_profiles,
                test_posts,
                test_tags, 
                test_categories,
                test_users
            RESTART IDENTITY CASCADE
        """)
        )

        # Включаем constraints обратно
        await session.execute(text("SET session_replication_role = DEFAULT"))
        await session.commit()

        logger.debug("✅ Все тестовые данные успешно очищены")

    except Exception as e:
        logger.debug(f"Cleanup info: {e}")  # Изменено с WARNING на DEBUG

        # Fallback: пересоздаем таблицы если TRUNCATE не работает
        try:
            from tests.core.base.test_repo.modesl_for_test import TestBaseModel

            # Используем engine напрямую для пересоздания таблиц
            async with session.bind.connect() as conn:
                await conn.run_sync(TestBaseModel.metadata.drop_all)
                await conn.run_sync(TestBaseModel.metadata.create_all)
                await conn.commit()

            logger.debug("✅ Таблицы пересозданы для очистки")
        except Exception as fallback_e:
            logger.debug(f"Fallback cleanup info: {fallback_e}")

        # Финальный откат сессии
        try:
            await session.rollback()
        except Exception:
            pass


@pytest.fixture(scope="function")
def app(async_session) -> Generator[FastAPI, None, None]:
    """FastAPI приложение с переопределенной БД."""
    from core.database import get_db
    from main import app as fastapi_app

    async def override_get_db():
        yield async_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        yield fastapi_app
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def api_client(app: FastAPI, async_session) -> AsyncGenerator[AsyncApiTestClient, None]:
    """API клиент для тестов."""
    async with AsyncApiTestClient(app=app, db=async_session) as client:
        yield client


# === Фабрики для тестовых данных ===


@pytest.fixture
def post_factory(setup_test_models):
    """Фабрика для создания постов."""
    try:
        from tests.core.base.test_repo.factories import PostFactory

        PostFactory._meta.sqlalchemy_session = setup_test_models  # type: ignore
        return PostFactory
    except ImportError:
        return None


@pytest.fixture
def category_factory(setup_test_models):
    """Фабрика для создания категорий."""
    try:
        from tests.core.base.test_repo.factories import CategoryFactory

        CategoryFactory._meta.sqlalchemy_session = setup_test_models  # type: ignore
        return CategoryFactory
    except ImportError:
        return None


@pytest.fixture
def tag_factory(setup_test_models):
    """Фабрика для создания тегов."""
    try:
        from tests.core.base.test_repo.factories import TagFactory

        TagFactory._meta.sqlalchemy_session = setup_test_models  # type: ignore
        return TagFactory
    except ImportError:
        return None


@pytest.fixture
def comment_factory(setup_test_models):
    """Фабрика для создания комментариев."""
    try:
        from tests.core.base.test_repo.factories import CommentFactory

        CommentFactory._meta.sqlalchemy_session = setup_test_models  # type: ignore
        return CommentFactory
    except ImportError:
        return None


@pytest.fixture
def profile_factory(setup_test_models):
    """Фабрика для создания профилей."""
    try:
        from tests.core.base.test_repo.factories import ProfileFactory

        ProfileFactory._meta.sqlalchemy_session = setup_test_models  # type: ignore
        return ProfileFactory
    except ImportError:
        return None


# === Репозитории для тестов ===


@pytest.fixture
def user_repo(setup_test_models):
    """Репозиторий пользователей для тестов."""
    from core.base.repo.repository import BaseRepository
    from tests.core.base.test_repo.modesl_for_test import TestUser

    return BaseRepository(TestUser, setup_test_models)  # type: ignore


@pytest.fixture
def post_repo(setup_test_models):
    """Репозиторий постов для тестов."""
    from core.base.repo.repository import BaseRepository
    from tests.core.base.test_repo.modesl_for_test import TestPost

    return BaseRepository(TestPost, setup_test_models)  # type: ignore


@pytest.fixture
def category_repo(setup_test_models):
    """Репозиторий категорий для тестов."""
    from core.base.repo.repository import BaseRepository
    from tests.core.base.test_repo.modesl_for_test import TestCategory

    return BaseRepository(TestCategory, setup_test_models)  # type: ignore


@pytest.fixture
def tag_repo(setup_test_models):
    """Репозиторий тегов для тестов."""
    from core.base.repo.repository import BaseRepository
    from tests.core.base.test_repo.modesl_for_test import TestTag

    return BaseRepository(TestTag, setup_test_models)  # type: ignore


@pytest.fixture
def comment_repo(setup_test_models):
    """Репозиторий комментариев для тестов."""
    from core.base.repo.repository import BaseRepository
    from tests.core.base.test_repo.modesl_for_test import TestComment

    return BaseRepository(TestComment, setup_test_models)  # type: ignore


# Фикстуры фабрик с правильной настройкой сессий
@pytest.fixture(scope="function")
def user_factory(async_session):
    """Фабрика пользователей с настроенной сессией."""
    # Настраиваем модель и сессию для фабрики
    setup_factory_model(UserFactory, User)
    setup_factory_session(UserFactory, async_session)
    return UserFactory


@pytest.fixture(scope="function")
def user_profile_factory(async_session):
    """Фабрика профилей пользователей с настроенной сессией."""
    setup_factory_model(UserProfileFactory, UserProfile)
    setup_factory_session(UserProfileFactory, async_session)
    return UserProfileFactory


@pytest.fixture(scope="function")
def refresh_token_factory(async_session):
    """Фабрика refresh токенов с настроенной сессией."""
    setup_factory_model(RefreshTokenFactory, RefreshToken)
    setup_factory_session(RefreshTokenFactory, async_session)
    return RefreshTokenFactory


@pytest.fixture(scope="function")
def user_session_factory(async_session):
    """Фабрика пользовательских сессий с настроенной сессией."""
    setup_factory_model(UserSessionFactory, UserSession)
    setup_factory_session(UserSessionFactory, async_session)
    return UserSessionFactory


@pytest.fixture(scope="function")
def orbital_token_factory(async_session):
    """Фабрика orbital токенов с настроенной сессией."""
    setup_factory_model(OrbitalTokenFactory, OrbitalToken)
    setup_factory_session(OrbitalTokenFactory, async_session)
    return OrbitalTokenFactory


# Комбинированные фикстуры для удобства
@pytest_asyncio.fixture(scope="function")
async def test_user(user_factory):
    """Создает тестового пользователя для быстрого использования."""
    return await user_factory.create(username="testuser", email="test@example.com", is_active=True, is_verified=True)


@pytest_asyncio.fixture(scope="function")
async def admin_user(user_factory):
    """Создает админ пользователя для тестов."""
    return await user_factory.create(
        username="admin", email="admin@example.com", is_active=True, is_verified=True, is_superuser=True
    )


@pytest_asyncio.fixture(scope="function")
async def test_user_with_profile(user_factory, user_profile_factory):
    """Создает пользователя с профилем."""
    user = await user_factory.create(username="userprofile", email="profile@example.com", is_active=True)

    profile = await user_profile_factory.create(user=user)

    # Возвращаем объект с user и profile
    class UserWithProfile:
        def __init__(self, user, profile):
            self.user = user
            self.profile = profile

    return UserWithProfile(user, profile)


# Утилиты для очистки
@pytest.fixture(autouse=True)
async def reset_faker():
    """Сбрасываем уникальные значения faker между тестами."""
    from tests.factories.base_factories import reset_factories

    await reset_factories()


# Маркеры для категоризации тестов
def pytest_configure(config):
    """Настройка маркеров pytest."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "api: API tests")
    config.addinivalue_line("markers", "auth: Authentication tests")
    config.addinivalue_line("markers", "users: Users tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "slow: Slow running tests")


# Настройки для покрытия
def pytest_collection_modifyitems(config, items):
    """Автоматически добавляем маркеры по именам файлов."""
    for item in items:
        # API тесты
        if "api" in item.nodeid:
            item.add_marker(pytest.mark.api)

        # Auth тесты
        if "auth" in item.nodeid:
            item.add_marker(pytest.mark.auth)

        # Users тесты
        if "users" in item.nodeid:
            item.add_marker(pytest.mark.users)

        # Performance тесты
        if "performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
