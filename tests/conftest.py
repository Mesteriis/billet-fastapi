import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator

import alembic.command
import alembic.config
import pytest
import pytest_asyncio
from fastapi import FastAPI
from pytest_mock_resources import create_postgres_fixture
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.database import get_db
from main import app as main_app, settings
from tests.utils_test.api_test_client import AsyncApiTestClient


@pytest.fixture(scope="session")
def event_loop():
    """Event loop для async тестов."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()



@pytest.fixture(scope="session")
def temp_dir():
    """Временная директория для тестов."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)

pg = create_postgres_fixture(
    scope='session',
    async_=True,
)

@pytest_asyncio.fixture(scope="session")
async def async_engine(pg):
    uri = str(pg.url).replace('***', pg.url.password)  # Заменяем на реальный пароль
    engine = create_async_engine(
        uri,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=settings.DB_POOL_RECYCLE,
    )

    alembic_cfg = alembic.config.Config("alembic.ini")
    alembic_cfg.set_main_option("script_location", "alembic")  # путь к миграциям
    alembic_cfg.set_main_option("sqlalchemy.url", uri)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Асинхронная сессия БД для тестов."""
    async_session_maker = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest.fixture(scope="session")
def app(async_session) -> FastAPI:
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
    async with AsyncApiTestClient(app=app, db=async_session) as client:
        yield client




#
#
#
#
#
# # Вспомогательные классы
# class TestHelpers:
#     """Вспомогательные методы для тестов."""
#
#     @staticmethod
#     def assert_user_response(response_data: dict, expected_email: str):
#         """Проверяет структуру ответа пользователя."""
#         assert "id" in response_data
#         assert "email" in response_data
#         assert "username" in response_data
#         assert "full_name" in response_data
#         assert "is_active" in response_data
#         assert "is_verified" in response_data
#         assert response_data["email"] == expected_email
#
#     @staticmethod
#     def assert_token_response(response_data: dict):
#         """Проверяет структуру ответа с токенами."""
#         assert "access_token" in response_data
#         assert "refresh_token" in response_data
#         assert "token_type" in response_data
#         assert response_data["token_type"] == "bearer"
#
#
# @pytest.fixture(scope="function")
# def helpers():
#     """Фикстура вспомогательных методов."""
#     return TestHelpers
#
#
# # Фикстуры для Repository tests
# @pytest.fixture(scope="function")
# async def user_repository(async_session):
#     """Repository для пользователей."""
#     from apps.users.models import User
#     from core.base.repo import BaseRepository
#
#     return BaseRepository(User, async_session)
#
#
# @pytest.fixture(scope="function")
# async def cache_manager():
#     """Cache manager для тестов."""
#     from core.base.repo import CacheManager
#
#     return CacheManager(
#         redis_client=None,  # Используем только memory cache в тестах
#         use_redis=False,
#         use_memory=True,
#         default_ttl=300,
#         key_prefix="test:repo:",
#     )
#
#
# @pytest.fixture(scope="function")
# async def cached_user_repository(async_session, cache_manager):
#     """Repository с кэшированием для пользователей."""
#     from apps.users.models import User
#     from core.base.repo import BaseRepository
#
#     return BaseRepository(User, async_session, cache_manager)
#
#
# @pytest.fixture(scope="function")
# def user_data(faker):
#     """Данные для создания пользователя через repository."""
#     unique_suffix = faker.uuid4()[:8]
#     return {
#         "email": f"{faker.user_name()}_{unique_suffix}@{faker.domain_name()}",
#         "username": f"{faker.user_name()}_{unique_suffix}",
#         "full_name": faker.name(),
#         "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj1yZDFgw8Hm",
#         "is_active": faker.boolean(chance_of_getting_true=80),  # 80% активных
#         "is_verified": faker.boolean(chance_of_getting_true=60),  # 60% верифицированных
#         "is_superuser": faker.boolean(chance_of_getting_true=10),  # 10% суперпользователей
#         "bio": faker.text(max_nb_chars=200),
#     }
#
#
# @pytest.fixture(scope="function")
# def bulk_users_data(faker):
#     """Данные для bulk операций."""
#     return [
#         {
#             "email": f"{faker.user_name()}_{i}_{faker.uuid4()[:4]}@{faker.domain_name()}",
#             "username": f"{faker.user_name()}_{i}_{faker.uuid4()[:4]}",
#             "full_name": faker.name(),
#             "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj1yZDFgw8Hm",
#             "is_active": faker.boolean(chance_of_getting_true=90),  # 90% активных
#             "is_verified": i % 2 == 0,  # Четные верифицированы для предсказуемости тестов
#             "is_superuser": False,
#             "bio": faker.text(max_nb_chars=150),
#         }
#         for i in range(1, 6)  # 5 пользователей
#     ]
#
#
# @pytest.fixture(scope="function")
# def bulk_users_data_predictable(faker):
#     """Данные для bulk операций с предсказуемыми значениями для тестов."""
#     domain = faker.domain_name()
#     return [
#         {
#             "email": f"{faker.user_name()}_bulk_{i}@{domain}",
#             "username": f"{faker.user_name()}_bulk_{i}_{faker.uuid4()[:4]}",
#             "full_name": faker.name(),
#             "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj1yZDFgw8Hm",
#             "is_active": True,  # Все активны для предсказуемости
#             "is_verified": i % 2 == 0,  # Четные верифицированы для предсказуемости тестов
#             "is_superuser": False,
#             "bio": faker.text(max_nb_chars=150) if i % 3 != 0 else None,  # Каждый третий без bio
#         }
#         for i in range(1, 6)  # 5 пользователей
#     ]
