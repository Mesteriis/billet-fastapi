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
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from core.database import get_db
from main import app as main_app
from main import settings
from tests.utils_test.api_test_client import AsyncApiTestClient

# Настройка логирования для тестов - максимально агрессивный подход
# Полностью отключаем все логирование кроме CRITICAL
logging.disable(logging.INFO)

# Создаем наш тестовый логгер с принудительным включением
logger = logging.getLogger("test_session")
logger.setLevel(logging.INFO)
logger.disabled = False  # Принудительно включаем наш логгер


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
    """Event loop with proper isolation for asyncpg compatibility"""
    # Создаем новую политику event loop для изоляции
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()

    # Устанавливаем loop как текущий для asyncpg
    asyncio.set_event_loop(loop)
    old_loop = asyncio.get_event_loop()

    try:
        yield loop
    finally:
        # Корректно закрываем loop
        try:
            # Отменяем все pending tasks
            pending = asyncio.all_tasks(loop)
            if pending:
                for task in pending:
                    if not task.done():
                        task.cancel()
                # Ждем завершения отмененных задач
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

            # Закрываем генераторы
            loop.run_until_complete(loop.shutdown_asyncgens())

            # Закрываем default executor
            if hasattr(loop, "shutdown_default_executor"):
                loop.run_until_complete(loop.shutdown_default_executor())
        except Exception as e:
            logger.warning(f"Warning during loop cleanup: {e}")
        finally:
            # Восстанавливаем предыдущий loop если он был
            if old_loop != loop:
                try:
                    asyncio.set_event_loop(old_loop)
                except:
                    pass
            loop.close()


@pytest.fixture(scope="session")
def temp_dir():
    """Временная директория для тестов."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def postgres_container():
    """Оптимизированный PostgreSQL контейнер для тестов."""
    from testcontainers.postgres import PostgresContainer

    try:
        # Используем более стабильный образ PostgreSQL
        with PostgresContainer(
            image="postgres:15-alpine",
            driver="asyncpg",  # Явно указываем драйвер
        ).with_env("POSTGRES_INITDB_ARGS", "--auth-host=trust --auth-local=trust") as pg:
            yield pg

    except Exception as e:
        logger.warning(f"PostgreSQL container failed: {e}")

        class MockContainer:
            def get_connection_url(self):
                return "sqlite+aiosqlite:///:memory:"

        yield MockContainer()


@pytest_asyncio.fixture(scope="function")
async def async_engine(postgres_container, event_loop):
    """Асинхронный движок БД для тестов."""
    uri = postgres_container.get_connection_url()

    # Конвертируем PostgreSQL URL в asyncpg формат
    if "postgresql+psycopg2://" in uri:
        uri = uri.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    elif "postgresql://" in uri:
        uri = uri.replace("postgresql://", "postgresql+asyncpg://")

    logger.info(f"Database URI: {uri[:50]}...")

    # ИСПРАВЛЕНИЕ: Убираем устаревший параметр 'loop' и упрощаем конфигурацию
    engine_config = {
        "echo": False,  # Отключаем эхо для изоляции
        "poolclass": NullPool,  # Используем NullPool для избежания проблем
        "pool_pre_ping": True,  # Проверяем соединения
        "pool_recycle": 300,  # Перезапускаем соединения каждые 5 минут
    }

    # Для asyncpg добавляем специальные параметры
    if "asyncpg" in uri:
        engine_config["connect_args"] = {
            "server_settings": {
                "application_name": "pytest_test",
                "timezone": "UTC",
            },
            "command_timeout": 60,
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
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Асинхронная сессия БД для тестов."""
    async_session_maker = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,  # Отключаем автофлуш для контроля
        autocommit=False,  # Явно отключаем autocommit
    )

    async with async_session_maker() as session:
        yield session


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

    async def override_get_db():
        yield async_session

    main_app.dependency_overrides[get_db] = override_get_db
    try:
        yield main_app
    finally:
        main_app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def api_client(app: FastAPI, async_session) -> AsyncGenerator[AsyncApiTestClient, None]:
    """API клиент для тестов."""
    async with AsyncApiTestClient(app=app, db=async_session) as client:
        yield client


# === Фабрики для тестовых данных ===


@pytest.fixture
def user_factory(setup_test_models):
    """Фабрика для создания пользователей."""
    try:
        from tests.core.base.test_repo.factories import UserFactory

        UserFactory._meta.sqlalchemy_session = setup_test_models  # type: ignore
        return UserFactory
    except ImportError:
        return None


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
