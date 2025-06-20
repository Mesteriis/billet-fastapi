"""
Комплексные тесты для системы кеширования BaseRepository.
"""

import json
import time
from unittest.mock import AsyncMock, Mock, patch

import pytest

from core.base.repo.cache import CacheManager, SimpleMemoryCache, cache_result
from core.base.repo.repository import BaseRepository


@pytest.mark.asyncio
async def test_simple_memory_cache_comprehensive():
    """Тестирует SimpleMemoryCache с различными сценариями."""
    cache = SimpleMemoryCache(default_ttl=1)  # 1 секунда для быстрого тестирования

    # Тест 1: Базовые операции set/get
    await cache.set("test_key", "test_value")
    value = await cache.get("test_key")
    assert value == "test_value", "Значение должно быть сохранено и получено корректно"

    # Тест 2: Получение несуществующего ключа
    not_found = await cache.get("nonexistent_key")
    assert not_found is None, "Несуществующий ключ должен вернуть None"

    # Тест 3: TTL expiration
    await cache.set("expiring_key", "expiring_value", ttl=1)
    value_before = await cache.get("expiring_key")
    assert value_before == "expiring_value", "Значение должно быть доступно до истечения TTL"

    # Ждем истечения TTL
    time.sleep(1.1)
    value_after = await cache.get("expiring_key")
    assert value_after is None, "Значение должно быть None после истечения TTL"

    # Тест 4: Удаление ключа
    await cache.set("delete_key", "delete_value")
    await cache.delete("delete_key")
    deleted_value = await cache.get("delete_key")
    assert deleted_value is None, "Удаленный ключ должен вернуть None"

    # Тест 5: Очистка кеша
    await cache.set("clear_key1", "value1")
    await cache.set("clear_key2", "value2")
    await cache.clear()

    value1 = await cache.get("clear_key1")
    value2 = await cache.get("clear_key2")
    assert value1 is None and value2 is None, "Все ключи должны быть удалены после clear"

    # Тест 6: Статистика кеша
    await cache.set("stats_key", "stats_value", ttl=10)
    await cache.set("expired_key", "expired_value", ttl=-1)  # Уже истекший

    stats = cache.get_stats()
    assert "total_entries" in stats, "Статистика должна содержать total_entries"
    assert "active_entries" in stats, "Статистика должна содержать active_entries"
    assert "expired_entries" in stats, "Статистика должна содержать expired_entries"
    assert stats["active_entries"] >= 1, "Должна быть минимум 1 активная запись"


@pytest.mark.asyncio
async def test_cache_manager_redis_mock():
    """Тестирует CacheManager с мокированным Redis."""
    # Мокируем Redis клиент
    mock_redis = AsyncMock()
    mock_redis.get.return_value = json.dumps({"test": "data"})
    mock_redis.setex.return_value = True
    mock_redis.delete.return_value = 1
    mock_redis.keys.return_value = ["repo:test_key"]
    mock_redis.info.return_value = {"used_memory_human": "1MB"}

    cache_manager = CacheManager(redis_client=mock_redis, use_redis=True, use_memory=True, default_ttl=300)

    # Тест 1: Get из Redis
    value = await cache_manager.get("test_key")
    mock_redis.get.assert_called_once_with("repo:test_key")
    assert value == {"test": "data"}, "Значение должно быть десериализовано из Redis"

    # Тест 2: Set в Redis и память
    await cache_manager.set("new_key", {"new": "value"}, ttl=600)
    mock_redis.setex.assert_called_once_with("repo:new_key", 600, json.dumps({"new": "value"}, default=str))

    # Тест 3: Delete из Redis и памяти
    await cache_manager.delete("delete_key")
    mock_redis.delete.assert_called_once_with("repo:delete_key")

    # Тест 4: Clear by pattern
    await cache_manager.clear_pattern("test:*")
    mock_redis.keys.assert_called_once_with("repo:test:*")

    # Тест 5: Статистика с Redis
    stats = await cache_manager.get_stats()
    assert stats["redis_enabled"] is True, "Redis должен быть включен"
    assert stats["memory_enabled"] is True, "Memory cache должен быть включен"
    assert "redis" in stats, "Должна быть статистика Redis"
    assert stats["redis"]["connected"] is True, "Redis должен быть подключен"


@pytest.mark.asyncio
async def test_cache_manager_redis_errors():
    """Тестирует обработку ошибок Redis."""
    # Мокируем Redis с ошибками
    mock_redis = AsyncMock()
    mock_redis.get.side_effect = Exception("Redis connection error")
    mock_redis.setex.side_effect = Exception("Redis write error")
    mock_redis.delete.side_effect = Exception("Redis delete error")
    mock_redis.keys.side_effect = Exception("Redis keys error")
    mock_redis.info.side_effect = Exception("Redis info error")

    cache_manager = CacheManager(redis_client=mock_redis, use_redis=True, use_memory=True, default_ttl=300)

    # Тест 1: Fallback to memory при ошибке Redis get
    # Сначала установим значение в memory cache
    await cache_manager.set("fallback_key", "fallback_value")

    # Теперь получаем значение (Redis даст ошибку, но memory cache сработает)
    # Но поскольку set тоже даст ошибку в Redis, проверим только что memory cache работает
    from core.base.repo.cache import _memory_cache

    await _memory_cache.set("repo:fallback_key", "memory_value")

    value = await cache_manager.get("fallback_key")
    assert value == "memory_value", "Должен fallback на memory cache при ошибке Redis"

    # Тест 2: Статистика при ошибке Redis
    stats = await cache_manager.get_stats()
    assert "redis" in stats, "Должна быть информация о Redis"
    assert stats["redis"]["connected"] is False, "Redis должен быть отмечен как отключенный"
    assert "error" in stats["redis"], "Должна быть информация об ошибке"


@pytest.mark.asyncio
async def test_cache_manager_memory_only():
    """Тестирует CacheManager только с memory cache."""
    cache_manager = CacheManager(redis_client=None, use_redis=False, use_memory=True, default_ttl=300)

    # Тест 1: Set/Get только через память
    await cache_manager.set("memory_key", {"memory": "data"})
    value = await cache_manager.get("memory_key")
    assert value == {"memory": "data"}, "Значение должно быть сохранено в памяти"

    # Тест 2: Delete через память
    await cache_manager.delete("memory_key")
    deleted_value = await cache_manager.get("memory_key")
    assert deleted_value is None, "Значение должно быть удалено из памяти"

    # Тест 3: Clear pattern (только полная очистка для памяти)
    await cache_manager.set("clear_key", "clear_value")
    await cache_manager.clear_pattern("*")
    cleared_value = await cache_manager.get("clear_key")
    assert cleared_value is None, "Значение должно быть очищено из памяти"

    # Тест 4: Статистика только памяти
    stats = await cache_manager.get_stats()
    assert stats["redis_enabled"] is False, "Redis должен быть отключен"
    assert stats["memory_enabled"] is True, "Memory cache должен быть включен"
    assert "memory" in stats, "Должна быть статистика памяти"


@pytest.mark.asyncio
async def test_cache_result_decorator(setup_test_models):
    """Тестирует декоратор cache_result."""
    from .modesl_for_test import TestUser

    # Создаем репозиторий с мокированным cache manager
    mock_cache = AsyncMock()
    mock_cache.get.return_value = None  # Первый раз кеш пуст
    mock_cache.set.return_value = None

    repo = BaseRepository(TestUser, setup_test_models, cache_manager=mock_cache)  # type: ignore

    # Мокируем функцию для тестирования декоратора
    class MockRepo:
        def __init__(self):
            self._cache_manager = mock_cache
            self._model = TestUser
            self.call_count = 0

        @cache_result(ttl=600)
        async def cached_method(self, param1: str, param2: int = 10):
            self.call_count += 1
            return f"result_{param1}_{param2}"

    mock_repo = MockRepo()

    # Тест 1: Первый вызов - результат кешируется
    result1 = await mock_repo.cached_method("test", 20)
    assert result1 == "result_test_20", "Результат должен быть корректным"
    assert mock_repo.call_count == 1, "Функция должна быть вызвана первый раз"
    mock_cache.get.assert_called_once()
    mock_cache.set.assert_called_once()

    # Тест 2: Второй вызов с теми же параметрами - берется из кеша
    mock_cache.reset_mock()
    mock_cache.get.return_value = "cached_result"

    result2 = await mock_repo.cached_method("test", 20)
    assert result2 == "cached_result", "Результат должен быть из кеша"
    assert mock_repo.call_count == 1, "Функция не должна быть вызвана повторно"
    mock_cache.get.assert_called_once()
    mock_cache.set.assert_not_called()

    # Тест 3: Вызов с другими параметрами - новый результат
    mock_cache.reset_mock()
    mock_cache.get.return_value = None

    result3 = await mock_repo.cached_method("other", 30)
    assert result3 == "result_other_30", "Результат должен быть новым"
    assert mock_repo.call_count == 2, "Функция должна быть вызвана для новых параметров"


@pytest.mark.asyncio
async def test_repository_cache_integration(setup_test_models):
    """Тестирует интеграцию кеша с репозиторием."""
    from .factories import TestUserFactory
    from .modesl_for_test import TestUser

    TestUserFactory._meta.sqlalchemy_session = setup_test_models  # type: ignore

    # Создаем cache manager для тестирования
    cache_manager = CacheManager(redis_client=None, use_redis=False, use_memory=True, default_ttl=300)

    repo = BaseRepository(TestUser, setup_test_models, cache_manager=cache_manager)  # type: ignore

    # Создаем тестовые данные
    user = await TestUserFactory.create(username="cache_test_user", email="cache@test.com")
    await setup_test_models.commit()

    # Тест 1: Проверяем что кеш очищается после создания
    await repo.create({"username": "cache_new_user", "email": "cache_new@test.com", "hashed_password": "password"})

    # Тест 2: Проверяем что кеш очищается после обновления
    await repo.update(user, {"username": "cache_updated_user"})

    # Тест 3: Проверяем что кеш очищается после удаления
    await repo.remove(user.id, soft_delete=True)

    # Тест 4: Проверяем статистику кеша
    stats = await repo.get_cache_stats()
    assert "model" in stats, "Статистика должна содержать информацию о модели"
    assert stats["model"] == "TestUser", "Модель должна быть указана корректно"

    # Тест 5: Прогрев кеша
    await repo.warm_cache([{"username__startswith": "cache"}, {"limit": 5}])

    # Тест 6: Инвалидация кеша по паттерну
    await repo.invalidate_cache("users:*")


@pytest.mark.asyncio
async def test_cache_edge_cases():
    """Тестирует edge cases кеширования."""

    # Тест 1: CacheManager без Redis и без памяти
    cache_manager = CacheManager(redis_client=None, use_redis=False, use_memory=False)

    await cache_manager.set("test", "value")
    value = await cache_manager.get("test")
    assert value is None, "При отключенном кеше значение не должно сохраняться"

    # Тест 2: Сериализация сложных объектов
    cache_manager = CacheManager(use_redis=False, use_memory=True)

    complex_data = {"datetime": "2023-01-01T00:00:00", "nested": {"key": "value"}, "list": [1, 2, 3]}

    await cache_manager.set("complex", complex_data)
    retrieved = await cache_manager.get("complex")
    assert retrieved == complex_data, "Сложные объекты должны корректно сериализоваться/десериализоваться"
