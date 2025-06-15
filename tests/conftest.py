"""
Конфигурация pytest для всех тестов.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from apps.base.models import BaseModel
from core.database import get_db
from main import app as main_app
from tests.factories.user_factory import AdminUserFactory, SimpleUserFactory, VerifiedUserFactory, make_user_data
from tests.utils_test.api_test_client import AsyncApiTestClient


@pytest.fixture(scope="session")
def event_loop():
    """Event loop для async тестов."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def temp_dir():
    """Временная директория для тестов."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture(scope="function")
def sync_engine():
    """Синхронный SQLite движок для тестов."""
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # Создаем все таблицы
    BaseModel.metadata.create_all(engine)

    yield engine

    # Очистка
    BaseModel.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
async def async_engine():
    """Асинхронный SQLite движок для тестов."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # Создаем все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    yield engine

    # Очистка
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Асинхронная сессия БД для тестов."""
    async_session_maker = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest.fixture(scope="function")
def app(async_session) -> FastAPI:
    """FastAPI приложение с переопределенной БД."""

    async def override_get_db():
        yield async_session

    main_app.dependency_overrides[get_db] = override_get_db

    yield main_app

    # Очистка
    main_app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def api_client(app: FastAPI, async_session) -> AsyncGenerator[AsyncApiTestClient, None]:
    """AsyncApiTestClient для тестов."""
    async with AsyncApiTestClient(app=app, base_url="http://test") as client:
        # Интегрируем сессию БД
        client.db_session = async_session
        yield client


# Фикстуры пользователей
@pytest.fixture(scope="function")
def sample_user():
    """Простой тестовый пользователь."""
    return SimpleUserFactory()


@pytest.fixture(scope="function")
def verified_user():
    """Верифицированный пользователь."""
    return VerifiedUserFactory()


@pytest.fixture(scope="function")
def admin_user():
    """Администратор."""
    return AdminUserFactory()


@pytest.fixture(scope="function")
def test_user_data():
    """Данные для создания пользователя."""
    return make_user_data()


# Вспомогательные классы
class TestHelpers:
    """Вспомогательные методы для тестов."""

    @staticmethod
    def assert_user_response(response_data: dict, expected_email: str):
        """Проверяет структуру ответа пользователя."""
        assert "id" in response_data
        assert "email" in response_data
        assert "username" in response_data
        assert "full_name" in response_data
        assert "is_active" in response_data
        assert "is_verified" in response_data
        assert response_data["email"] == expected_email

    @staticmethod
    def assert_token_response(response_data: dict):
        """Проверяет структуру ответа с токенами."""
        assert "access_token" in response_data
        assert "refresh_token" in response_data
        assert "token_type" in response_data
        assert response_data["token_type"] == "bearer"


@pytest.fixture(scope="function")
def helpers():
    """Фикстура вспомогательных методов."""
    return TestHelpers
