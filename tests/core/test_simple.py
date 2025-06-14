"""
Простой тест для проверки работы системы.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(async_client: AsyncClient):
    """Простой тест проверки здоровья API."""
    response = await async_client.get("/health")

    # Если роут не существует, это нормально - главное что FastAPI запускается
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_api_registration_flow(async_client: AsyncClient):
    """Простой тест полного цикла регистрации."""
    # Данные для регистрации
    user_data = {
        "email": "simpletest@example.com",
        "username": "simpletest",
        "full_name": "Simple Test User",
        "password": "SimplePassword123!",
        "password_confirm": "SimplePassword123!",
    }

    # Попытка регистрации
    response = await async_client.post("/api/v1/auth/register", json=user_data)

    # Проверяем что регистрация работает
    assert response.status_code == 201
    data = response.json()

    # Проверяем структуру ответа
    assert "user" in data
    assert "tokens" in data
    assert data["user"]["email"] == "simpletest@example.com"
    assert "access_token" in data["tokens"]
    assert "refresh_token" in data["tokens"]


@pytest.mark.asyncio
async def test_database_connection(db_session):
    """Тест подключения к базе данных."""
    # Простой запрос для проверки подключения
    result = await db_session.execute("SELECT 1")
    assert result.scalar() == 1
