from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import MetaData, delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from core.base.repo import BaseRepository

from .modesl_for_test import (
    TestBaseModel,
    TestCategory,
    TestComment,
    TestPost,
    TestProfile,
    TestTag,
    TestUser,
    post_tags_table,
)

# Кэш для созданных таблиц
_tables_created = False

# Используем logger из корневого conftest.py
logger = logging.getLogger("test_session")


@asynccontextmanager
async def create_models_for_test(async_engine, session: AsyncSession):
    """Создает тестовые модели и обеспечивает их очистку."""
    try:
        logger.info(f"Создаем таблицы через engine: {async_engine}")

        # Создаем таблицы для тестов через engine
        async with async_engine.begin() as conn:
            await conn.run_sync(TestBaseModel.metadata.create_all)

        logger.info("Таблицы созданы успешно")
        yield

    finally:
        # Очищаем данные между тестами, но не удаляем таблицы
        try:
            logger.info("Очищаем данные после теста")
            # Очищаем в правильном порядке (с учетом foreign keys)
            await session.execute(delete(TestComment))
            await session.execute(delete(TestPost))
            await session.execute(delete(TestProfile))
            await session.execute(delete(TestUser))
            await session.execute(delete(TestCategory))
            await session.execute(delete(TestTag))
            await session.commit()
        except Exception as e:
            logger.debug(f"Cleanup error: {e}")  # Изменено с ERROR на DEBUG
            await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def setup_test_models(async_engine, async_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Настройка тестовых моделей для каждого теста."""
    async with create_models_for_test(async_engine, async_session):
        yield async_session


@pytest_asyncio.fixture(scope="function")
async def repo_session(setup_test_models: AsyncSession) -> AsyncSession:
    """Сессия для тестов репозитория с настроенными моделями."""
    return setup_test_models


# Алиас для совместимости с существующими тестами
@pytest_asyncio.fixture(scope="function")
async def session(repo_session: AsyncSession) -> AsyncSession:
    """Алиас для session фикстуры."""
    return repo_session


# Фабрики с оптимизированным переиспользованием сессии
@pytest.fixture(scope="function")
def user_factory(setup_test_models: AsyncSession):
    from .factories import TestUserFactory

    TestUserFactory._meta.sqlalchemy_session = setup_test_models  # type: ignore
    return TestUserFactory


@pytest.fixture(scope="function")
def post_factory(setup_test_models: AsyncSession):
    from .factories import TestPostFactory

    TestPostFactory._meta.sqlalchemy_session = setup_test_models  # type: ignore
    return TestPostFactory


@pytest.fixture(scope="function")
def category_factory(setup_test_models: AsyncSession):
    from .factories import TestCategoryFactory

    TestCategoryFactory._meta.sqlalchemy_session = setup_test_models  # type: ignore
    return TestCategoryFactory


@pytest.fixture(scope="function")
def tag_factory(setup_test_models: AsyncSession):
    from .factories import TestTagFactory

    TestTagFactory._meta.sqlalchemy_session = setup_test_models  # type: ignore
    return TestTagFactory


@pytest.fixture(scope="function")
def comment_factory(setup_test_models: AsyncSession):
    from .factories import TestCommentFactory

    TestCommentFactory._meta.sqlalchemy_session = setup_test_models  # type: ignore
    return TestCommentFactory


@pytest.fixture(scope="function")
def profile_factory(setup_test_models: AsyncSession):
    from .factories import TestProfileFactory

    TestProfileFactory._meta.sqlalchemy_session = setup_test_models  # type: ignore
    return TestProfileFactory


@pytest.fixture(scope="session")
def post_create_schema():
    from .shemes_for_test import TestPostCreate

    return TestPostCreate


@pytest.fixture(scope="session")
def post_update_schema():
    from .shemes_for_test import TestPostUpdate

    return TestPostUpdate


@pytest_asyncio.fixture(scope="function")
async def post_repo(setup_test_models: AsyncSession) -> Any:
    """Репозиторий постов для тестов."""
    return BaseRepository(TestPost, setup_test_models)  # type: ignore


# Фикстуры для создания сущностей для тестов
@pytest_asyncio.fixture(scope="function")
async def user(user_factory) -> Any:
    """Пользователь для тестов."""
    return await user_factory.create()


# Убираем setup_database фикстуру так как она конфликтует со scope
# Используем setup_test_models для создания таблиц


@pytest_asyncio.fixture(scope="function")
async def user_repo(setup_test_models: AsyncSession) -> Any:
    """Репозиторий пользователей для тестов."""
    return BaseRepository(TestUser, setup_test_models)  # type: ignore


@pytest_asyncio.fixture(scope="function")
async def tag_repo(setup_test_models: AsyncSession) -> Any:
    """Репозиторий тегов для тестов."""
    return BaseRepository(TestTag, setup_test_models)  # type: ignore


# Очистка данных между тестами
@pytest_asyncio.fixture(scope="function", autouse=True)
async def cleanup_data(async_session):
    """Очистка данных между тестами для изоляции."""
    yield

    # Очищаем данные после каждого теста с улучшенной обработкой ошибок
    try:
        # Для PostgreSQL отключаем constraints
        if "postgresql" in str(async_session.bind.url):
            await async_session.execute("SET session_replication_role = replica")

        # Очищаем таблицы в правильном порядке
        table_order = [
            TestComment.__table__,
            post_tags_table,
            TestTag.__table__,
            TestPost.__table__,
            TestProfile.__table__,
            TestCategory.__table__,
            TestUser.__table__,
        ]

        for table in table_order:
            try:
                await async_session.execute(table.delete())
            except Exception:
                # Игнорируем ошибки удаления отдельных таблиц
                continue

        # Включаем обратно constraints для PostgreSQL
        if "postgresql" in str(async_session.bind.url):
            await async_session.execute("SET session_replication_role = DEFAULT")

        await async_session.commit()

    except Exception as e:
        try:
            await async_session.rollback()
        except Exception:
            pass
        # Логируем только в debug режиме
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Cleanup completed with errors: {e}")
