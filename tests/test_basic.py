"""Базовые тесты для проверки настройки."""

import pytest


def test_basic_import():
    """Тест базового импорта."""
    from src.core.config import get_settings

    settings = get_settings()
    assert settings.PROJECT_NAME == "Mango Message"


def test_simple_math():
    """Простой тест вычислений."""
    assert 2 + 2 == 4
    assert 10 - 5 == 5


@pytest.mark.asyncio
async def test_async_function():
    """Тест асинхронной функции."""
    import asyncio

    async def simple_async():
        await asyncio.sleep(0.01)
        return "async works"

    result = await simple_async()
    assert result == "async works"
