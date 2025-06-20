"""
Комплексные тесты для достижения 95% покрытия BaseRepository.
"""

import uuid
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pytz import utc
from sqlalchemy.exc import IntegrityError

from core.base.repo.cache import CacheManager, SimpleMemoryCache
from core.base.repo.events import CreateEvent, DeleteEvent, UpdateEvent
from core.base.repo.repository import BaseRepository
from core.base.repo.types import CacheConfig
from tests.utils_test.isolation_decorators import database_reset_test


@pytest.mark.asyncio
async def test_repository_get_by_comprehensive(setup_test_models):
    """Тестирует метод get_by с различными фильтрами и edge cases."""
    from .factories import TestCategoryFactory, TestPostFactory, TestUserFactory
    from .modesl_for_test import TestPost, TestUser

    # Настраиваем фабрики
    for factory in [TestUserFactory, TestPostFactory, TestCategoryFactory]:
        factory._meta.sqlalchemy_session = setup_test_models  # type: ignore

    repo = BaseRepository(TestUser, setup_test_models)  # type: ignore

    # Создаем тестовые данные
    user1 = await TestUserFactory.create(username="user_getby_1", email="get1@test.com", is_verified=True)
    user2 = await TestUserFactory.create(username="user_getby_2", email="get2@test.com", is_verified=False)
    category = await TestCategoryFactory.create(name="GetBy Category")

    post1 = await TestPostFactory.create(
        title="Test Post GetBy", author=user1, category=category, status="published", views_count=100
    )

    await setup_test_models.commit()

    # Тест 1: Поиск по простому полю
    found_user = await repo.get_by(username="user_getby_1")
    assert found_user is not None, "Пользователь должен быть найден по username"
    assert found_user.id == user1.id, "ID найденного пользователя должен совпадать"
    assert found_user.email == "get1@test.com", "Email должен совпадать"

    # Тест 2: Поиск по email (case-insensitive)
    found_user = await repo.get_by(email__iexact="GET1@TEST.COM")
    assert found_user is not None, "Пользователь должен быть найден по email (case-insensitive)"
    assert found_user.username == "user_getby_1", "Username должен совпадать"

    # Тест 3: Поиск по boolean полю
    verified_user = await repo.get_by(is_verified=True)
    assert verified_user is not None, "Должен быть найден верифицированный пользователь"
    assert verified_user.is_verified is True, "Пользователь должен быть верифицирован"

    # Тест 4: Поиск несуществующего объекта
    not_found = await repo.get_by(username="nonexistent_user")
    assert not_found is None, "Несуществующий пользователь не должен быть найден"

    # Тест 5: Поиск с несколькими условиями
    specific_user = await repo.get_by(username="user_getby_1", is_verified=True)
    assert specific_user is not None, "Пользователь должен быть найден по двум условиям"
    assert specific_user.username == "user_getby_1", "Username должен совпадать"
    assert specific_user.is_verified is True, "Верификация должна совпадать"

    # Тест 6: Поиск по связанному объекту (для постов)
    post_repo = BaseRepository(TestPost, setup_test_models)
    found_post = await post_repo.get_by(author__username="user_getby_1")
    assert found_post is not None, "Пост должен быть найден по автору"
    assert found_post.title == "Test Post GetBy", "Заголовок поста должен совпадать"


@pytest.mark.asyncio
async def test_repository_exists_comprehensive(setup_test_models):
    """Тестирует метод exists с различными условиями."""
    from .factories import TestUserFactory
    from .modesl_for_test import TestUser

    TestUserFactory._meta.sqlalchemy_session = setup_test_models  # type: ignore
    repo = BaseRepository(TestUser, setup_test_models)  # type: ignore

    # Создаем тестовые данные
    user = await TestUserFactory.create(username="exists_user", email="exists@test.com")
    deleted_user = await TestUserFactory.create(username="deleted_user", email="deleted@test.com")

    # Мягко удаляем одного пользователя
    deleted_user.soft_delete()
    await setup_test_models.commit()

    # Тест 1: Существующий пользователь
    exists = await repo.exists(username="exists_user")
    assert exists is True, "Существующий пользователь должен быть найден"

    # Тест 2: Несуществующий пользователь
    not_exists = await repo.exists(username="nonexistent")
    assert not_exists is False, "Несуществующий пользователь не должен быть найден"

    # Тест 3: Мягко удаленный пользователь (по умолчанию не должен быть найден)
    deleted_exists = await repo.exists(username="deleted_user")
    assert deleted_exists is False, "Мягко удаленный пользователь не должен быть найден"


@pytest.mark.asyncio
async def test_repository_restore_comprehensive(setup_test_models):
    """Тестирует метод restore с различными сценариями."""
    from .factories import TestUserFactory
    from .modesl_for_test import TestUser

    TestUserFactory._meta.sqlalchemy_session = setup_test_models
    repo = BaseRepository(TestUser, setup_test_models)

    # Создаем и удаляем пользователя
    user = await TestUserFactory.create(username="restore_user", email="restore@test.com")
    user_id = user.id

    # Мягко удаляем
    user.soft_delete()
    await setup_test_models.commit()

    # Тест 1: Восстановление мягко удаленного объекта
    restored_user = await repo.restore(user_id)
    assert restored_user is not None, "Пользователь должен быть восстановлен"
    assert restored_user.deleted_at is None, "deleted_at должно быть None после восстановления"
    assert restored_user.username == "restore_user", "Данные должны остаться неизменными"

    # Тест 2: Попытка восстановить уже активный объект
    already_active = await repo.restore(user_id)
    assert already_active is None, "Уже активный объект не должен быть 'восстановлен'"

    # Тест 3: Попытка восстановить несуществующий объект
    fake_id = uuid.uuid4()
    not_found = await repo.restore(fake_id)
    assert not_found is None, "Несуществующий объект не должен быть найден для восстановления"


@database_reset_test(verbose=True)
async def test_repository_count_comprehensive(setup_test_models):
    """Тестирует метод count с различными фильтрами."""
    from .factories import TestUserFactory
    from .modesl_for_test import TestUser

    # Фабрика автоматически настроена декоратором изоляции
    repo = BaseRepository(TestUser, setup_test_models)

    # Создаем тестовые данные
    await TestUserFactory.create(username="count_user_1", is_verified=True)
    await TestUserFactory.create(username="count_user_2", is_verified=False)
    await TestUserFactory.create(username="count_user_3", is_verified=True)

    deleted_user = await TestUserFactory.create(username="count_deleted", is_verified=True)
    deleted_user.soft_delete()

    await setup_test_models.commit()

    # Тест 1: Общий подсчет (без удаленных)
    total_count = await repo.count()
    assert total_count == 3, f"Должно быть 3 активных пользователя, получено {total_count}"

    # Тест 2: Подсчет с включением удаленных
    total_with_deleted = await repo.count(include_deleted=True)
    assert total_with_deleted == 4, f"Должно быть 4 пользователя всего, получено {total_with_deleted}"

    # Тест 3: Подсчет с фильтрами
    verified_count = await repo.count(is_verified=True)
    assert verified_count == 2, f"Должно быть 2 верифицированных пользователя, получено {verified_count}"


@pytest.mark.asyncio
async def test_repository_validation_errors(setup_test_models):
    """Тестирует обработку ошибок валидации."""
    from .modesl_for_test import TestUser

    repo = BaseRepository(TestUser, setup_test_models)

    # Тест 1: Создание с пустыми данными
    with pytest.raises(ValueError, match="Data for creation cannot be empty"):
        await repo.create({})


@pytest.mark.asyncio
async def test_bulk_operations_comprehensive(setup_test_models):
    """Тестирует bulk операции с edge cases."""
    from .factories import TestUserFactory
    from .modesl_for_test import TestUser

    TestUserFactory._meta.sqlalchemy_session = setup_test_models
    repo = BaseRepository(TestUser, setup_test_models)

    # Тест 1: Bulk create с пустым списком
    empty_result = await repo.bulk_create([])
    assert empty_result == [], "Bulk create с пустым списком должен вернуть пустой список"

    # Тест 2: Bulk update с пустыми данными - создаем отдельных пользователей
    test_users = []
    for i in range(3):
        user = await TestUserFactory.create(
            username=f"bulk_update_user_{i}_{uuid.uuid4().hex[:8]}",  # Уникальное имя
            email=f"bulk_update_{i}@test.com",
        )
        test_users.append(user)

    await setup_test_models.commit()

    # Обновляем каждого пользователя индивидуально уникальными именами
    update_count = 0
    for i, user in enumerate(test_users):
        single_update = await repo.bulk_update(
            {"id": user.id},
            {"username": f"updated_user_{i}_{uuid.uuid4().hex[:8]}"},  # Уникальное новое имя
        )
        update_count += single_update

    assert update_count == 3, f"Должно быть обновлено 3 пользователя, обновлено {update_count}"
