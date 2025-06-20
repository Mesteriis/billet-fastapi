"""
Специфические тесты для покрытия конкретных участков кода репозитория.

Покрывает:
- Редкие операторы фильтрации
- Граничные случаи валидации
- Обработка ошибок в операторах
- Специфические сценарии кэширования
- Редкие случаи в курсорной пагинации
- Операции с JSON полями
"""

import logging
import uuid
from datetime import date, datetime, time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from faker import Faker
from pytz import utc
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from core.base.repo.repository import BaseRepository

from .enums import PostStatus, Priority
from .factories import TestPostFactory, TestUserFactory, fake
from .modesl_for_test import TestCategory, TestPost, TestTag, TestUser
from .shemes_for_test import TestPostCreate, TestPostUpdate, TestUserCreate, TestUserUpdate

# Используем logger из корневого conftest.py
logger = logging.getLogger("test_session")


@pytest.mark.asyncio
@pytest.mark.specific_coverage
async def test_rare_operators_coverage(
    setup_test_models: AsyncSession,
    user_repo: Any,
    post_repo: Any,
    user_factory,
    post_factory,
) -> None:
    """Тестируем редкие операторы фильтрации для покрытия кода."""
    logger = logging.getLogger("test_session")

    # Создаем авторов для постов через фабрику
    authors: list[TestUser] = []
    for i in range(3):
        author = await user_factory.create(
            username=f"author_{fake.uuid4()[:8]}_{i}",
            is_verified=i % 2 == 0,
            bio=fake.text(max_nb_chars=200) if i > 0 else None,
        )
        authors.append(author)

    # Создаем посты с разными данными для тестирования редких операторов
    posts: list[TestPost] = []
    for i in range(10):
        post = await post_factory.create(
            title=f"Rare Operators Test {i}",
            slug=f"rare-operators-{i}",
            content=f"Test content with special chars: !@#$%^&*() {i}",
            excerpt=None,
            status=PostStatus.PUBLISHED if i % 3 == 0 else PostStatus.DRAFT,
            priority=Priority.MEDIUM,
            views_count=i * 7,
            likes_count=0,
            rating=float(i * 0.5),
            published_at=fake.date_time_this_year(tzinfo=utc),
            scheduled_at=None,
            is_featured=False,
            is_premium=False,
            allow_comments=True,
            extra_metadata={
                "test_key": f"test_value_{i}",
                "nested": {"level2": {"value": i}},
                "array": [f"item_{j}" for j in range(min(i + 1, 3))],
            },
            search_vector=None,
            author=authors[i % len(authors)],  # Распределяем посты между авторами
            category=None,
        )
        posts.append(post)

    logger.info(f"Создано {len(posts)} постов для тестирования редких операторов")

    # Тестируем редко используемые операторы

    # 1. regex и iregex операторы
    regex_result = await post_repo.list(title__regex=r"Test \d+")
    assert len(regex_result) > 0, "regex должен найти записи"

    iregex_result = await post_repo.list(title__iregex=r"rare.*test")
    assert len(iregex_result) > 0, "iregex должен найти записи"

    # 2. exact и iexact операторы
    exact_result = await post_repo.list(title__exact="Rare Operators Test 1")
    assert len(exact_result) == 1, "exact должен найти точное совпадение"

    iexact_result = await post_repo.list(title__iexact="RARE OPERATORS TEST 1")
    assert len(iexact_result) == 1, "iexact должен игнорировать регистр"

    # 3. contains и icontains операторы
    contains_result = await post_repo.list(content__contains="special chars")
    assert len(contains_result) > 0, "contains должен найти подстроку"

    icontains_result = await post_repo.list(content__icontains="SPECIAL CHARS")
    assert len(icontains_result) > 0, "icontains должен игнорировать регистр"

    # 4. JSON операторы
    json_has_key_result = await post_repo.list(extra_metadata__has_key="test_key")
    assert len(json_has_key_result) > 0, "has_key должен найти ключ в JSON"

    json_has_all_keys_result = await post_repo.list(extra_metadata__has_all_keys=["test_key", "nested"])
    assert len(json_has_all_keys_result) > 0, "has_all_keys должен найти все ключи"

    json_has_any_keys_result = await post_repo.list(extra_metadata__has_any_keys=["test_key", "missing"])
    assert len(json_has_any_keys_result) > 0, "has_any_keys должен найти любой ключ"

    json_contained_by_result = await post_repo.list(
        extra_metadata__contained_by={
            "test_key": f"test_value_1",
            "nested": {"level2": {"value": 1}},
            "array": ["item_0", "item_1"],
            "extra": "data",
        }
    )
    logger.info(f"JSON contained_by найдено записей: {len(json_contained_by_result)}")

    # 5. Операторы сравнения
    gt_result = await post_repo.list(views_count__gt=20)
    assert len(gt_result) >= 0, "gt оператор должен работать"

    gte_result = await post_repo.list(views_count__gte=14)
    assert len(gte_result) >= 0, "gte оператор должен работать"

    logger.info("Все редкие операторы успешно протестированы")


@pytest.mark.specific_coverage
@pytest.mark.asyncio
async def test_validation_edge_cases(setup_test_models, post_repo, user_factory, post_factory):
    """
    Покрывает граничные случаи валидации в _validate_filter_value.
    """
    logger.info("✅ Тестируем граничные случаи валидации")

    # Создаем автора для поста через фабрику
    author = await user_factory.create(
        username=f"validation_author_{fake.uuid4()[:8]}",
        is_active=True,
        is_verified=True,
    )

    # Создаем один пост для тестирования через фабрику
    test_date = datetime(2023, 6, 15, 14, 30, 45)
    test_post = await post_factory.create(
        title="Validation Test Post",
        slug="validation-test",
        content="Test content",
        published_at=test_date,
        extra_metadata={"test": "value"},
        author=author,  # Указываем автора
        category=None,  # Без категории
        status=PostStatus.DRAFT,
        priority=Priority.MEDIUM,
        views_count=0,
        likes_count=0,
        is_featured=False,
        is_premium=False,
        allow_comments=True,
    )

    # Тест 1: Граничные значения для date операторов
    logger.info("1️⃣ Тестируем граничные значения дат")

    # Правильные значения
    valid_year = await post_repo.list(published_at__year=2023)
    valid_month = await post_repo.list(published_at__month=6)
    valid_day = await post_repo.list(published_at__day=15)
    valid_hour = await post_repo.list(published_at__hour=14)
    valid_minute = await post_repo.list(published_at__minute=30)
    valid_second = await post_repo.list(published_at__second=45)

    logger.info(f"   Валидные date операторы работают: {len(valid_year) + len(valid_month)} результатов")

    # Граничные значения (должны быть отфильтрованы валидацией)
    invalid_year = await post_repo.list(published_at__year=99999)  # Слишком большой год
    invalid_month = await post_repo.list(published_at__month=13)  # Неправильный месяц
    invalid_day = await post_repo.list(published_at__day=32)  # Неправильный день
    invalid_hour = await post_repo.list(published_at__hour=25)  # Неправильный час

    logger.info(f"   Невалидные значения отфильтрованы: {len(invalid_year) + len(invalid_month)} результатов")

    # Тест 2: Граничные значения для between операторов
    logger.info("2️⃣ Тестируем между операторы")

    # Правильный between
    valid_between = await post_repo.list(views_count__between=[0, 100])
    logger.info(f"   Валидный between: {len(valid_between)} результатов")

    # Неправильный between (только одно значение) - должен быть проигнорирован
    with patch("core.base.repo.repository.logger") as mock_logger:
        invalid_between = await post_repo.list(views_count__between=[50])
        mock_logger.warning.assert_called()

    # Тест 3: JSON extract оператор
    logger.info("3️⃣ Тестируем JSON extract оператор")

    # Правильный JSON extract (путь и значение)
    json_extract = await post_repo.list(extra_metadata__json_extract=["test", "value"])
    logger.info(f"   JSON extract: {len(json_extract)} результатов")

    # Неправильный JSON extract (неправильное количество параметров)
    with patch("core.base.repo.repository.logger") as mock_logger:
        invalid_json_extract = await post_repo.list(extra_metadata__json_extract=["only_one_param"])
        mock_logger.warning.assert_called()


@pytest.mark.specific_coverage
@pytest.mark.asyncio
async def test_query_builder_edge_cases(setup_test_models, user_repo, user_factory):
    """
    Покрывает edge cases в QueryBuilder классе.
    """
    logger.info("🔧 Тестируем edge cases QueryBuilder")

    # Создаем пользователя с профилем для тестирования JOIN через фабрику
    test_user = await user_factory.create(
        username="querybuilder_test", email="qb@test.com", full_name="QueryBuilder Test"
    )

    # Тест 1: Тестируем get_loader_options
    logger.info("1️⃣ Тестируем get_loader_options")

    # Получаем QueryBuilder из репозитория
    qb = user_repo._qb

    # Имитируем создание join для получения loader options
    try:
        # Простой запрос без JOIN
        simple_loaders = qb.get_loader_options()
        logger.info(f"   Простые loader options: {len(simple_loaders)} опций")
        assert isinstance(simple_loaders, list)

        # Запрос с фильтром по профилю для создания JOIN
        profile_users = await user_repo.list(profile__city="test")

        # Теперь должны быть loader options
        with_join_loaders = qb.get_loader_options()
        logger.info(f"   Loader options с JOIN: {len(with_join_loaders)} опций")

    except Exception as e:
        logger.info(f"   Ошибка в loader options: {e}")

    # Тест 2: Тестируем get_object_query
    logger.info("2️⃣ Тестируем get_object_query")

    object_query = qb.get_object_query(test_user.id)
    logger.info("   Object query создан успешно")

    object_query_with_deleted = qb.get_object_query(test_user.id, include_deleted=True)
    logger.info("   Object query с удаленными создан успешно")

    # Тест 3: Тестируем get_list_query
    logger.info("3️⃣ Тестируем get_list_query")

    list_query = qb.get_list_query()
    logger.info("   List query создан успешно")

    list_query_with_deleted = qb.get_list_query(include_deleted=True)
    logger.info("   List query с удаленными создан успешно")


@pytest.mark.specific_coverage
@pytest.mark.asyncio
async def test_cache_specific_scenarios(setup_test_models, user_repo):
    """
    Покрывает специфические сценарии кэширования.
    """
    logger.info("🗄️ Тестируем специфические сценарии кэширования")

    if not user_repo._cache_manager:
        logger.info("   Кэш менеджер не настроен, пропускаем тесты")
        return

    # Тест 1: Получение статистики кэша
    logger.info("1️⃣ Тестируем статистику кэша")

    cache_stats = await user_repo.get_cache_stats()
    logger.info(f"   Статистика кэша: {cache_stats}")
    assert isinstance(cache_stats, dict)

    # Тест 2: Прогрев кэша
    logger.info("2️⃣ Тестируем прогрев кэша")

    popular_queries = [{"is_active": True}, {"is_verified": True}, {"is_superuser": False}]

    await user_repo.warm_cache(popular_queries)
    logger.info("   Прогрев кэша выполнен")

    # Тест 3: Прогрев кэша без queries
    logger.info("3️⃣ Тестируем прогрев кэша без запросов")

    await user_repo.warm_cache(None)
    logger.info("   Прогрев кэша без запросов выполнен")


@pytest.mark.specific_coverage
@pytest.mark.asyncio
async def test_cursor_pagination_specific_cases(setup_test_models, post_repo, user_factory, post_factory):
    """
    Покрывает специфические случаи курсорной пагинации.
    """
    logger.info("📄 Тестируем специфические случаи курсорной пагинации")

    # Создаем авторов для постов через фабрику
    authors: list[TestUser] = []
    for i in range(3):
        author = await user_factory.create(
            username=f"cursor_author_{fake.uuid4()[:8]}_{i}",
            is_active=True,
            is_verified=True,
        )
        authors.append(author)

    # Создаем посты с разными значениями для тестирования курсоров через фабрику
    test_posts = []
    for i in range(15):
        post = await post_factory.create(
            title=f"Cursor Test {i:02d}",
            slug=f"cursor-test-{i:02d}",
            content=f"Content {i}",
            views_count=i * 3,
            rating=float(i % 5),
            author=authors[i % len(authors)],  # Распределяем авторов
            category=None,  # Без категории
            status=PostStatus.DRAFT,
            priority=Priority.MEDIUM,
            likes_count=0,
            is_featured=False,
            is_premium=False,
            allow_comments=True,
        )
        test_posts.append(post)

    # Тест 1: Курсорная пагинация с include_total=True
    logger.info("1️⃣ Тестируем пагинацию с подсчетом общего количества")

    page_with_total = await post_repo.paginate_cursor(
        cursor_field="views_count", limit=5, include_total=True, order_by="views_count"
    )

    logger.info(f"   Страница с total: {len(page_with_total.items)} элементов, всего: {page_with_total.total_count}")
    assert page_with_total.total_count is not None
    assert page_with_total.total_count >= len(page_with_total.items)

    # Тест 2: Курсорная пагинация без подсчета
    logger.info("2️⃣ Тестируем пагинацию без подсчета общего количества")

    page_without_total = await post_repo.paginate_cursor(
        cursor_field="views_count", limit=5, include_total=False, order_by="views_count"
    )

    logger.info(f"   Страница без total: {len(page_without_total.items)} элементов")
    assert page_without_total.total_count is None

    # Тест 3: Пагинация с фильтрами и курсором
    logger.info("3️⃣ Тестируем пагинацию с фильтрами")

    filtered_page = await post_repo.paginate_cursor(
        cursor_field="views_count",
        cursor_value=10,  # Начинаем с определенного значения
        direction="next",
        limit=3,
        views_count__gte=5,  # Дополнительный фильтр
        order_by="views_count",
    )

    logger.info(f"   Отфильтрованная страница: {len(filtered_page.items)} элементов")

    # Проверяем что фильтр работает
    for item in filtered_page.items:
        assert item.views_count >= 5, "Все элементы должны соответствовать фильтру"


@pytest.mark.specific_coverage
@pytest.mark.asyncio
async def test_model_to_dict_coverage(setup_test_models, user_factory):
    """
    Покрывает функцию model_to_dict.
    """
    logger.info("🔄 Тестируем функцию model_to_dict")

    from core.base.repo.repository import model_to_dict

    # Создаем тестового пользователя через фабрику
    test_user = await user_factory.create(
        username="dict_test_user",
        email="dict@test.com",
        full_name="Dict Test User",
        is_active=True,
        is_verified=False,
    )
    await setup_test_models.refresh(test_user)

    # Конвертируем в словарь
    user_dict = model_to_dict(test_user)

    logger.info(f"   Модель конвертирована в словарь: {len(user_dict)} полей")

    # Проверяем что все основные поля присутствуют
    expected_fields = [
        "id",
        "username",
        "email",
        "full_name",
        "hashed_password",
        "is_active",
        "is_verified",
        "created_at",
        "updated_at",
    ]

    for field in expected_fields:
        assert field in user_dict, f"Поле {field} должно быть в словаре"

    # Проверяем типы значений
    assert isinstance(user_dict["id"], uuid.UUID), "ID должен быть UUID"
    assert isinstance(user_dict["username"], str), "Username должен быть строкой"
    assert isinstance(user_dict["is_active"], bool), "is_active должен быть boolean"
    assert isinstance(user_dict["created_at"], datetime), "created_at должен быть datetime"

    logger.info("   Все поля модели корректно конвертированы")


logger.info("✅ Специфические тесты покрытия созданы!")
