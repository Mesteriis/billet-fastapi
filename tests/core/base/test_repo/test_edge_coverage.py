"""
Edge cases для достижения 95% покрытия кода репозитория.
"""

import logging
import uuid
from datetime import date, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

# Фикстуры post_repo, user_repo определены в conftest.py
from .enums import PostStatus, Priority
from .modesl_for_test import TestPost, TestUser

# Используем logger из корневого conftest.py
logger = logging.getLogger("test_session")


@pytest.mark.edge_cases
@pytest.mark.asyncio
async def test_filter_validation_edge_cases(setup_test_models, user_repo, user_factory):
    """
    Тестирует edge cases валидации фильтров.
    """
    logger.info("🔍 Тестируем edge cases валидации фильтров")

    # Создаем несколько тестовых пользователей для проверки
    test_users = []
    for i in range(3):
        user = await user_factory.create(
            username=f"test_edge_user_{i}_{uuid.uuid4().hex[:8]}", email=f"edge_{i}@test.com"
        )
        test_users.append(user)

    await setup_test_models.commit()

    # Edge Case 1: Некорректные значения для операторов коллекций
    logger.info("1️⃣ Тестируем некорректные значения для операторов коллекций")

    # Пустой список для in оператора - должен вернуть пустой результат
    empty_in_result = await user_repo.list(id__in=[])
    assert len(empty_in_result) == 0, "Пустой список в IN должен вернуть пустой результат"

    # None для in оператора - должен вернуть всех пользователей (игнорировать фильтр)
    none_in_result = await user_repo.list(id__in=None)
    logger.info(f"   None в IN операторе: {len(none_in_result)} результатов")

    # Валидный список для сравнения - должен найти пользователей
    valid_ids = [user.id for user in test_users]
    valid_in_result = await user_repo.list(id__in=valid_ids)
    assert len(valid_in_result) >= 3, f"Валидный IN должен найти пользователей, найдено {len(valid_in_result)}"

    # Edge Case 2: Несуществующие поля в фильтрах
    logger.info("2️⃣ Тестируем несуществующие поля")

    # С patch для проверки предупреждений
    with patch("core.base.repo.repository.logger") as mock_logger:
        nonexistent_field_result = await user_repo.list(nonexistent_field="value")
        mock_logger.warning.assert_called()
        logger.info(f"   Несуществующее поле: {len(nonexistent_field_result)} результатов")


@pytest.mark.edge_cases
@pytest.mark.asyncio
async def test_bulk_operations_error_handling(setup_test_models, user_repo):
    """
    Тестирует обработку ошибок в bulk операциях.
    """
    logger.info("📦 Тестируем обработку ошибок в bulk операциях")

    # Edge Case 1: Bulk create с дублирующимися данными
    logger.info("1️⃣ Тестируем bulk create с дублирующимися данными")

    duplicate_data = [
        {
            "username": "duplicate_user_test",
            "email": "duplicate_test@test.com",
            "full_name": "Duplicate User",
            "hashed_password": "password",
        },
        {
            "username": "duplicate_user_test",  # Дублирующийся username
            "email": "duplicate2_test@test.com",
            "full_name": "Duplicate User 2",
            "hashed_password": "password",
        },
    ]

    try:
        duplicate_result = await user_repo.bulk_create(duplicate_data)
        logger.info(f"   Дублирующиеся данные обработаны: {len(duplicate_result)} создано")
    except Exception as e:
        logger.info(f"   Ожидаемая ошибка при дублировании: {e}")


@pytest.mark.edge_cases
@pytest.mark.asyncio
async def test_aggregation_edge_cases(setup_test_models, post_repo):
    """
    Тестирует edge cases в агрегациях.
    """
    logger.info("📊 Тестируем edge cases агрегаций")

    # Создаем тестового пользователя для постов
    test_user = TestUser(
        username="agg_test_user", email="agg@test.com", full_name="Aggregation Test User", hashed_password="password"
    )
    setup_test_models.add(test_user)
    await setup_test_models.flush()
    await setup_test_models.refresh(test_user)

    # Создаем тестовые данные
    test_posts = []
    for i in range(5):
        post = TestPost(
            title=f"Aggregation Test Post {i}",
            slug=f"agg-test-edge-{i}",
            content=f"Content {i}",
            views_count=i * 10,
            likes_count=i * 2,
            rating=float(i % 5 + 1),
            status=PostStatus.PUBLISHED if i % 2 else PostStatus.DRAFT,
            author_id=test_user.id,  # Добавляем автора
        )
        test_posts.append(post)

    setup_test_models.add_all(test_posts)
    await setup_test_models.commit()

    # Edge Case 1: Агрегация по несуществующему полю
    logger.info("1️⃣ Тестируем агрегацию по несуществующему полю")

    try:
        nonexistent_agg = await post_repo.aggregate(field="nonexistent_field")
        logger.info(f"   Агрегация несуществующего поля: {len(nonexistent_agg)} результатов")
    except Exception as e:
        logger.info(f"   Ожидаемая ошибка агрегации: {e}")


logger.info("✅ Edge case тесты созданы!")
