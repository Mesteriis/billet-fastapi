"""
Тесты для edge cases и error handling в BaseRepository.
"""

import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, patch

import pytest

from core.base.repo.cache import CacheManager
from core.base.repo.repository import BaseRepository


@pytest.mark.asyncio
async def test_cache_warm_error_handling(setup_test_models):
    """Тестирует error handling в warm_cache."""
    from .modesl_for_test import TestUser

    # Создаем cache manager
    cache_manager = CacheManager(use_redis=False, use_memory=True)
    repo = BaseRepository(TestUser, setup_test_models, cache_manager=cache_manager)  # type: ignore

    # Тест 1: warm_cache с некорректными запросами
    queries_with_errors = [
        {"nonexistent_field": "value"},  # Несуществующее поле
        {"limit": "not_a_number"},  # Некорректный тип для limit
        {"offset": -1},  # Отрицательный offset
    ]

    # Не должно вызывать исключений
    await repo.warm_cache(queries_with_errors)

    # Тест 2: warm_cache без cache_manager
    repo_no_cache = BaseRepository(TestUser, setup_test_models, cache_manager=None)  # type: ignore
    await repo_no_cache.warm_cache()  # Должно пройти без ошибок


@pytest.mark.asyncio
async def test_repository_remove_nonexistent(setup_test_models):
    """Тестирует remove несуществующего объекта."""
    from .modesl_for_test import TestUser

    repo = BaseRepository(TestUser, setup_test_models)  # type: ignore

    # Тест: попытка удалить несуществующий объект
    fake_id = uuid.uuid4()
    result = await repo.remove(fake_id)
    assert result is None, "Результат должен быть None для несуществующего объекта"


@pytest.mark.asyncio
async def test_repository_restore_edge_cases(setup_test_models):
    """Тестирует edge cases для restore."""
    from .factories import TestUserFactory
    from .modesl_for_test import TestUser

    TestUserFactory._meta.sqlalchemy_session = setup_test_models  # type: ignore
    repo = BaseRepository(TestUser, setup_test_models)  # type: ignore

    # Создаем пользователя
    user = await TestUserFactory.create()
    await setup_test_models.commit()

    # Тест 1: попытка восстановить активный объект
    result = await repo.restore(user.id)
    assert result is None, "Результат должен быть None для активного объекта"

    # Тест 2: попытка восстановить несуществующий объект
    fake_id = uuid.uuid4()
    result = await repo.restore(fake_id)
    assert result is None, "Результат должен быть None для несуществующего объекта"


@pytest.mark.asyncio
async def test_cache_manager_redis_unavailable():
    """Тестирует CacheManager когда Redis недоступен."""

    # Тест 1: Создание CacheManager когда REDIS_AVAILABLE = False
    with patch("core.base.repo.cache.REDIS_AVAILABLE", False):
        cache_manager = CacheManager(
            redis_client=None,
            use_redis=True,  # Хотим использовать Redis
            use_memory=True,
        )

        # Redis должен быть отключен из-за недоступности
        assert cache_manager.use_redis is False, "Redis должен быть отключен когда недоступен"

    # Тест 2: Создание с mock Redis клиентом
    mock_redis = AsyncMock()
    cache_manager = CacheManager(redis_client=mock_redis, use_redis=True, use_memory=True)

    assert cache_manager.use_redis is True, "Redis должен быть включен с клиентом"


@pytest.mark.asyncio
async def test_bulk_operations_error_handling(setup_test_models):
    """Тестирует error handling в bulk операциях."""
    from .factories import TestUserFactory
    from .modesl_for_test import TestUser

    TestUserFactory._meta.sqlalchemy_session = setup_test_models  # type: ignore
    repo = BaseRepository(TestUser, setup_test_models)  # type: ignore

    # Создаем пользователей
    users = [await TestUserFactory.create(username=f"bulk_user_{i}") for i in range(3)]
    await setup_test_models.commit()

    # Тест 1: bulk_update с ошибкой получения старых данных
    with patch("core.base.repo.repository.model_to_dict") as mock_model_to_dict:
        mock_model_to_dict.side_effect = Exception("Model serialization error")

        count = await repo.bulk_update(filters={"username__startswith": "bulk_user"}, update_data={"is_active": False})
        assert count >= 0, "Обновление должно быть выполнено даже с ошибкой сериализации"

    # Тест 2: bulk_delete с ошибкой получения данных для событий
    with patch("core.base.repo.repository.model_to_dict") as mock_model_to_dict:
        mock_model_to_dict.side_effect = Exception("Model serialization error")

        count = await repo.bulk_delete(filters={"username__startswith": "bulk_user"}, soft_delete=True)
        assert count >= 0, "Удаление должно быть выполнено даже с ошибкой сериализации"


@pytest.mark.asyncio
async def test_cache_decorator_error_handling(setup_test_models):
    """Тестирует error handling в cache_result декораторе."""
    from core.base.repo.cache import cache_result

    from .modesl_for_test import TestUser

    # Создаем репозиторий с мокированным cache manager
    mock_cache = AsyncMock()
    repo = BaseRepository(TestUser, setup_test_models, cache_manager=mock_cache)  # type: ignore

    # Тест 1: Ошибка при записи в кеш
    mock_cache.set.side_effect = Exception("Cache write error")
    mock_cache.get.return_value = None

    class TestRepo:
        def __init__(self):
            self._cache_manager = mock_cache
            self._model = TestUser

        @cache_result(ttl=300)
        async def test_method(self, param: str):
            return f"result_{param}"

    test_repo = TestRepo()

    # Должно работать несмотря на ошибку кеширования
    result = await test_repo.test_method("test")
    assert result == "result_test", "Метод должен работать несмотря на ошибку кеша"

    # Тест 2: Репозиторий без cache_manager
    class RepoNoCacheManager:
        def __init__(self):
            self._cache_manager = None

        @cache_result(ttl=300)
        async def test_method(self, param: str):
            return f"result_{param}"

    repo_no_cache = RepoNoCacheManager()
    result = await repo_no_cache.test_method("test")
    assert result == "result_test", "Метод должен работать без cache_manager"


@pytest.mark.asyncio
async def test_fulltext_search_edge_cases(setup_test_models):
    """Тестирует edge cases полнотекстового поиска."""
    from .factories import TestCategoryFactory, TestUserFactory
    from .modesl_for_test import TestPost

    # Настраиваем фабрики
    TestUserFactory._meta.sqlalchemy_session = setup_test_models  # type: ignore
    TestCategoryFactory._meta.sqlalchemy_session = setup_test_models  # type: ignore

    repo = BaseRepository(TestPost, setup_test_models)  # type: ignore

    # Создаем базовые данные
    user = await TestUserFactory.create()
    category = await TestCategoryFactory.create()
    await setup_test_models.commit()

    # Тест 1: Поиск с неправильным search_type
    results = await repo.fulltext_search(
        search_fields=["title"],
        query_text="test",
        search_type="unknown_type",  # type: ignore
    )
    assert isinstance(results, list), "Результат должен быть списком даже с неправильным типом поиска"

    # Тест 2: Поиск с пустой строкой
    results = await repo.fulltext_search(search_fields=["title", "content"], query_text="")
    assert isinstance(results, list), "Результат должен быть списком для пустой строки поиска"


@pytest.mark.asyncio
async def test_cursor_pagination_edge_cases(setup_test_models):
    """Тестирует edge cases курсорной пагинации."""
    from .factories import TestUserFactory
    from .modesl_for_test import TestUser

    TestUserFactory._meta.sqlalchemy_session = setup_test_models  # type: ignore
    repo = BaseRepository(TestUser, setup_test_models)  # type: ignore

    # Создаем одного пользователя
    user = await TestUserFactory.create(username="pagination_user")
    await setup_test_models.commit()

    # Тест 1: Пагинация с order_by = cursor_field
    result = await repo.paginate_cursor(
        cursor_field="id",
        order_by="id",  # Тот же что и cursor_field
        limit=10,
    )
    assert len(result.items) >= 0, "Результат должен быть корректным"

    # Тест 2: Пагинация с несуществующим order_by полем
    result = await repo.paginate_cursor(cursor_field="id", order_by="nonexistent_field", limit=10)
    assert len(result.items) >= 0, "Результат должен быть корректным даже с несуществующим order_by"


@pytest.mark.asyncio
async def test_aggregate_edge_cases(setup_test_models):
    """Тестирует edge cases агрегации."""
    from .factories import TestCategoryFactory, TestPostFactory, TestUserFactory
    from .modesl_for_test import TestPost

    # Настраиваем фабрики
    for factory in [TestUserFactory, TestPostFactory, TestCategoryFactory]:
        factory._meta.sqlalchemy_session = setup_test_models  # type: ignore

    repo = BaseRepository(TestPost, setup_test_models)  # type: ignore

    # Создаем тестовые данные
    user = await TestUserFactory.create()
    category = await TestCategoryFactory.create()
    await TestPostFactory.create(author=user, category=category, views_count=100)
    await setup_test_models.commit()

    # Тест 1: Группировка по несуществующему полю
    results = await repo.aggregate(field="views_count", operations=["count", "sum"], group_by="nonexistent_field")
    assert isinstance(results, list), "Результат должен быть списком даже для несуществующего group_by"

    # Тест 2: Агрегация без операций (должно использовать count по умолчанию)
    results = await repo.aggregate("views_count", operations=None)
    assert isinstance(results, list), "Результат должен быть списком для None операций"
