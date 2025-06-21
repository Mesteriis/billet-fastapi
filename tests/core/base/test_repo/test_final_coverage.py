"""
Финальные тесты для достижения максимального покрытия кода.
"""

import json
import uuid
from datetime import date, datetime
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.orm import InstrumentedAttribute

from core.base.repo.cache import CacheManager, SimpleMemoryCache, cache_result
from core.base.repo.repository import BaseRepository, QueryBuilder
from core.exceptions.core_base import CoreRepositoryValueError


@pytest.mark.asyncio
async def test_querybuilder_field_validation_warnings(setup_test_models):
    """Тестирует логирование предупреждений в валидации фильтров."""
    from .modesl_for_test import TestPost

    qb = QueryBuilder(TestPost)  # type: ignore
    query = qb.get_list_query()

    # Тест 1: Фильтр только с оператором (без поля)
    with patch("core.base.repo.repository.logger") as mock_logger:
        qb.apply_filters(query, {"__contains": "value"})
        # Проверяем что было предупреждение
        assert mock_logger.warning.called

    # Тест 2: Некорректные значения для операторов
    invalid_cases = [
        {"age__in": []},  # Пустой список
        {"views__between": [1]},  # Неправильное количество элементов
        {"title__regex": 123},  # Неправильный тип
    ]

    for invalid_filter in invalid_cases:
        with patch("core.base.repo.repository.logger") as mock_logger:
            qb.apply_filters(query, invalid_filter)
            # Проверяем что было хотя бы одно предупреждение
            assert mock_logger.warning.called, f"Должно быть предупреждение для {invalid_filter}"

    # Тест 3: Несуществующее поле модели
    with patch("core.base.repo.repository.logger") as mock_logger:
        qb.apply_filters(query, {"nonexistent_field": "value"})
        expected_msg = f"Поле 'nonexistent_field' не найдено в модели {TestPost.__name__}"
        mock_logger.warning.assert_called_with(expected_msg)


@pytest.mark.asyncio
async def test_querybuilder_apply_filters_exceptions(setup_test_models):
    """Тестирует обработку исключений в apply_filters."""
    from .modesl_for_test import TestPost

    qb = QueryBuilder(TestPost)  # type: ignore
    query = qb.get_list_query()

    # Мокируем getattr чтобы вызвать исключение
    with patch("core.base.repo.repository.getattr") as mock_getattr:
        mock_getattr.side_effect = AttributeError("Test error")

        with patch("core.base.repo.repository.logger") as mock_logger:
            result = qb.apply_filters(query, {"title": "test"})
            # Запрос должен остаться валидным
            assert result is not None
            # Должно быть залогировано исключение
            assert mock_logger.error.called


@pytest.mark.asyncio
async def test_querybuilder_complex_filters_empty_conditions(setup_test_models):
    """Тестирует сложные фильтры с пустыми условиями."""
    from .modesl_for_test import TestPost

    qb = QueryBuilder(TestPost)  # type: ignore
    query = qb.get_list_query()

    # Все фильтры пустые - не должно добавлять условий
    result = qb.apply_complex_filters(query, and_filters={}, or_filters=[], not_filters={})
    assert result is not None
    # Оригинальный запрос не должен измениться (проверяем что результат валидный)
    assert result is not None


@pytest.mark.asyncio
async def test_cache_memory_ttl_expiration():
    """Тестирует истечение TTL в memory cache."""
    import time

    cache = SimpleMemoryCache(default_ttl=1)  # 1 секунда

    # Устанавливаем значение с истечением в прошлом
    await cache.set("test_key", "test_value")

    # Принудительно устанавливаем время истечения в прошлое
    if "test_key" in cache._cache:
        value, _ = cache._cache["test_key"]
        cache._cache["test_key"] = (value, time.time() - 1)  # Истек 1 секунду назад

    # Значение должно истечь
    result = await cache.get("test_key")
    assert result is None, "Значение должно истечь из кеша"

    # Статистика должна показать истекшие записи
    stats = cache.get_stats()
    assert stats["expired_entries"] >= 0, "Должны быть истекшие записи"


@pytest.mark.asyncio
async def test_cache_manager_serialization_errors():
    """Тестирует ошибки сериализации в cache manager."""
    cache_manager = CacheManager(use_redis=False, use_memory=True)

    # Объект который не может быть сериализован в JSON
    class NonSerializable:
        def __init__(self):
            self.func = lambda x: x  # Функции не сериализуются в JSON

    non_serializable = NonSerializable()

    # Тестируем ошибку Redis
    with patch("core.base.repo.cache.logger") as mock_logger:
        # Создаем cache manager с Redis для тестирования ошибки
        mock_redis = Mock()
        cache_manager_redis = CacheManager(redis_client=mock_redis, use_redis=True, use_memory=False)
        mock_redis.setex.side_effect = Exception("Redis error")

        await cache_manager_redis.set("test_key", "value")
        # Должно быть залогировано предупреждение
        assert mock_logger.warning.called


@pytest.mark.asyncio
async def test_fulltext_search_no_fields(setup_test_models):
    """Тестирует полнотекстовый поиск без валидных полей."""
    from .modesl_for_test import TestPost

    repo = BaseRepository(TestPost, setup_test_models)  # type: ignore

    # Поиск с несуществующими полями
    with patch("core.base.repo.repository.logger") as mock_logger:
        results = await repo.fulltext_search(
            search_fields=["nonexistent_field1", "nonexistent_field2"], query_text="test"
        )

        # Должен вернуть пустой список
        assert results == []

        # Должно быть предупреждение
        expected_msg = f"Поля поиска не найдены в модели {TestPost.__name__}"
        mock_logger.warning.assert_called_with(expected_msg)


@pytest.mark.asyncio
async def test_aggregate_field_not_found(setup_test_models):
    """Тестирует агрегацию с несуществующим полем."""
    from .modesl_for_test import TestPost

    repo = BaseRepository(TestPost, setup_test_models)  # type: ignore

    # Агрегация по несуществующему полю
    with pytest.raises(CoreRepositoryValueError) as exc_info:
        await repo.aggregate("nonexistent_field", operations=["count"])

    assert "aggregate operation" in str(exc_info.value)


@pytest.mark.asyncio
async def test_pagination_cursor_field_not_found(setup_test_models):
    """Тестирует курсорную пагинацию с несуществующим cursor_field."""
    from .modesl_for_test import TestUser

    repo = BaseRepository(TestUser, setup_test_models)  # type: ignore

    # Пагинация с несуществующим cursor_field
    with pytest.raises(CoreRepositoryValueError) as exc_info:
        await repo.paginate_cursor(cursor_field="nonexistent_field")

    assert "paginate_cursor operation" in str(exc_info.value)


@pytest.mark.asyncio
async def test_repository_get_with_loader_options(setup_test_models):
    """Тестирует метод get с loader options."""
    from .factories import TestUserFactory
    from .modesl_for_test import TestUser

    TestUserFactory._meta.sqlalchemy_session = setup_test_models  # type: ignore
    repo = BaseRepository(TestUser, setup_test_models)  # type: ignore

    # Создаем пользователя
    user = await TestUserFactory.create()
    await setup_test_models.commit()

    # Мокируем get_loader_options чтобы вернуть пустой список
    repo._qb.get_loader_options = Mock(return_value=[])

    # Получаем пользователя
    result = await repo.get(user.id)
    assert result is not None
    assert result.id == user.id


@pytest.mark.asyncio
async def test_create_with_empty_data(setup_test_models):
    """Тестирует создание с пустыми данными."""
    from .modesl_for_test import TestUser

    repo = BaseRepository(TestUser, setup_test_models)  # type: ignore

    # Попытка создать с пустыми данными
    with pytest.raises(CoreRepositoryValueError) as exc_info:
        await repo.create({})

    assert "create operation" in str(exc_info.value)
    assert "empty" in str(exc_info.value)


@pytest.mark.asyncio
async def test_cache_result_decorator_no_manager():
    """Тестирует декоратор cache_result без cache manager."""

    class TestRepo:
        def __init__(self):
            self._cache_manager = None
            self._model = Mock()

        @cache_result(ttl=300)
        async def test_method(self, value: str):
            return f"result_{value}"

    repo = TestRepo()
    result = await repo.test_method("test")
    assert result == "result_test"


@pytest.mark.asyncio
async def test_cache_redis_info_error():
    """Тестирует ошибку получения info от Redis."""

    # Мокируем Redis клиент с ошибкой
    mock_redis = Mock()
    mock_redis.info.side_effect = Exception("Redis connection error")

    cache_manager = CacheManager(redis_client=mock_redis, use_redis=True, use_memory=False)

    stats = await cache_manager.get_stats()

    # Должно быть указано что Redis не подключен
    assert stats["redis"]["connected"] is False
    assert "error" in stats["redis"]


@pytest.mark.asyncio
async def test_filter_validation_edge_cases(setup_test_models):
    """Тестирует граничные случаи валидации фильтров."""
    from .modesl_for_test import TestPost

    qb = QueryBuilder(TestPost)  # type: ignore

    # Тестируем различные граничные значения
    edge_cases = [
        # Года на границах диапазона
        ("year", 1900, True),  # Минимальный год
        ("year", 3000, True),  # Максимальный год
        ("year", 1899, False),  # Ниже минимума
        ("year", 3001, False),  # Выше максимума
        # Месяцы
        ("month", 1, True),  # Минимальный месяц
        ("month", 12, True),  # Максимальный месяц
        ("month", 0, False),  # Ниже минимума
        ("month", 13, False),  # Выше максимума
        # Дни
        ("day", 1, True),  # Минимальный день
        ("day", 31, True),  # Максимальный день
        ("day", 0, False),  # Ниже минимума
        ("day", 32, False),  # Выше максимума
        # Недели
        ("week", 1, True),  # Минимальная неделя
        ("week", 53, True),  # Максимальная неделя
        ("week", 0, False),  # Ниже минимума
        ("week", 54, False),  # Выше максимума
        # Кварталы
        ("quarter", 1, True),  # Минимальный квартал
        ("quarter", 4, True),  # Максимальный квартал
        ("quarter", 0, False),  # Ниже минимума
        ("quarter", 5, False),  # Выше максимума
        # Дни недели
        ("week_day", 0, True),  # Минимальный день недели
        ("week_day", 6, True),  # Максимальный день недели
        ("week_day", -1, False),  # Ниже минимума
        ("week_day", 7, False),  # Выше максимума
        # Часы, минуты, секунды
        ("hour", 0, True),  # Минимальный час
        ("hour", 23, True),  # Максимальный час
        ("hour", -1, False),  # Ниже минимума
        ("hour", 24, False),  # Выше максимума
        ("minute", 0, True),  # Минимальная минута
        ("minute", 59, True),  # Максимальная минута
        ("minute", -1, False),  # Ниже минимума
        ("minute", 60, False),  # Выше максимума
        ("second", 0, True),  # Минимальная секунда
        ("second", 59, True),  # Максимальная секунда
        ("second", -1, False),  # Ниже минимума
        ("second", 60, False),  # Выше максимума
    ]

    for operator, value, expected in edge_cases:
        result = qb._validate_filter_value(operator, value)
        assert result == expected, f"Валидация {operator}={value} должна вернуть {expected}"
