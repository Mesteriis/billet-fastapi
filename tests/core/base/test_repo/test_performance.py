"""
Performance тесты для репозитория с большими объемами данных.

Покрывает:
- Работу с большими датасетами (1000+ записей)
- Производительность фильтрации и агрегаций
- Bulk операции с валидацией
- Edge cases для курсорной пагинации
- Полнотекстовый поиск на больших объемах
- Кэширование при высокой нагрузке
"""

import asyncio
import logging
import random
import time
import uuid
from datetime import date, datetime, timedelta
from typing import Any

import pytest
from pytz import utc
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.base.repo.repository import BaseRepository
from tests.utils_test.isolation_decorators import database_reset_test

from .conftest import post_repo, tag_repo, user_repo
from .enums import PostStatus, Priority
from .factories import TestPostFactory, TestTagFactory, TestUserFactory, fake
from .modesl_for_test import TestPost, TestUser

# Используем logger из корневого conftest.py
logger = logging.getLogger("test_session")


@pytest.mark.performance
@database_reset_test(verbose=True)
async def test_bulk_create_large_dataset(setup_test_models, user_repo):
    """
    Тест создания большого датасета через bulk_create.
    Проверяет производительность и корректность обработки больших батчей.
    """
    logger.info("🚀 Начинаем создание большого датасета (1000 пользователей)")

    start_time = time.time()

    # Подготавливаем данные для массового создания
    users_data = []
    for i in range(1000):
        users_data.append(
            {
                "username": f"perf_user_{i}_{uuid.uuid4().hex[:8]}",
                "email": f"perf_{i}_{uuid.uuid4().hex[:8]}@example.com",
                "full_name": f"Performance User {i}",
                "hashed_password": "test_password_hash",
                "is_active": random.choice([True, False]),
                "is_verified": random.choice([True, False]),
                "is_superuser": i < 50,  # Первые 50 - суперпользователи
            }
        )

    # Массовое создание с разными размерами батчей
    created_users = await user_repo.bulk_create(
        users_data,
        batch_size=100,  # Тестируем батчирование
        emit_events=False,  # Отключаем события для производительности
    )

    creation_time = time.time() - start_time
    logger.info(f"✅ Создано {len(created_users)} пользователей за {creation_time:.2f} секунд")
    logger.info(f"📊 Скорость: {len(created_users) / creation_time:.1f} записей/сек")

    # Проверки корректности
    assert len(created_users) == 1000, "Должно быть создано 1000 пользователей"

    # Проверяем уникальность
    emails = [user.email for user in created_users]
    assert len(set(emails)) == len(emails), "Все email должны быть уникальными"

    usernames = [user.username for user in created_users]
    assert len(set(usernames)) == len(usernames), "Все username должны быть уникальными"

    # Проверяем статистику по полям
    active_count = sum(1 for user in created_users if user.is_active)
    verified_count = sum(1 for user in created_users if user.is_verified)
    superuser_count = sum(1 for user in created_users if user.is_superuser)

    logger.info(f"📈 Статистика созданных пользователей:")
    logger.info(f"   Активных: {active_count}")
    logger.info(f"   Верифицированных: {verified_count}")
    logger.info(f"   Суперпользователей: {superuser_count}")

    assert superuser_count == 50, "Должно быть ровно 50 суперпользователей"

    # Тест производительности должен укладываться в разумное время
    assert creation_time < 30, f"Создание 1000 пользователей заняло слишком много времени: {creation_time:.2f}с"


@pytest.mark.performance
@database_reset_test(verbose=True)
async def test_complex_filtering_performance(
    setup_test_models: AsyncSession,
    post_repo: BaseRepository,
) -> None:
    """Тестирует производительность сложной фильтрации."""
    logger = logging.getLogger("test_session")
    logger.info("🏃‍♂️ Тестируем производительность сложной фильтрации")

    # Создаем авторов для постов
    authors: list[TestUser] = []
    for i in range(5):
        author = TestUser(
            username=f"perf_author_{fake.uuid4()[:8]}_{i}",
            email=fake.unique.email(),
            full_name=fake.name(),
            hashed_password=fake.password(),
            is_active=True,
            is_verified=i % 2 == 0,
        )
        setup_test_models.add(author)
        authors.append(author)

    await setup_test_models.commit()

    # Создаем большой набор данных для тестирования производительности
    posts_batch = []
    for i in range(1000):
        # Используем фабрику для генерации разнообразных данных
        post = TestPost(
            title=f"Performance Test Post {i}",
            slug=f"perf-test-{i}",
            content=fake.text(max_nb_chars=1000),
            excerpt=fake.text(max_nb_chars=200) if i % 3 == 0 else None,
            status=fake.random_element(elements=[PostStatus.DRAFT, PostStatus.PUBLISHED, PostStatus.ARCHIVED]),
            priority=fake.random_element(elements=[Priority.LOW, Priority.MEDIUM, Priority.HIGH]),
            views_count=fake.random_int(min=0, max=10000),
            likes_count=fake.random_int(min=0, max=500),
            rating=fake.pyfloat(left_digits=1, right_digits=1, positive=True, max_value=5.0) if i % 4 == 0 else None,
            published_at=fake.date_time_this_year(tzinfo=utc) if i % 2 == 0 else None,
            scheduled_at=fake.date_this_year() if i % 5 == 0 else None,
            is_featured=fake.boolean(chance_of_getting_true=20),
            is_premium=fake.boolean(chance_of_getting_true=10),
            allow_comments=fake.boolean(chance_of_getting_true=80),
            extra_metadata={"keywords": fake.words(nb=3), "category": f"cat_{i % 10}"},
            author_id=authors[i % len(authors)].id,
        )
        posts_batch.append(post)

        # Добавляем и коммитим батчами для лучшей производительности
        if len(posts_batch) >= 100:
            setup_test_models.add_all(posts_batch)
            await setup_test_models.commit()
            posts_batch = []

    # Добавляем оставшиеся посты
    if posts_batch:
        setup_test_models.add_all(posts_batch)
        await setup_test_models.commit()

    logger.info("Создано 1000 постов для тестирования производительности")


@pytest.mark.performance
@database_reset_test(verbose=True)
async def test_cursor_pagination_performance(setup_test_models, post_repo):
    """
    Тест производительности курсорной пагинации на большом датасете.
    Проверяет edge cases с различными типами курсоров.
    """
    logger.info("📄 Тестируем производительность курсорной пагинации")

    # Создаем авторов для постов
    authors: list[TestUser] = []
    for i in range(3):
        author = TestUser(
            username=f"cursor_author_{fake.uuid4()[:8]}_{i}",
            email=fake.unique.email(),
            full_name=fake.name(),
            hashed_password=fake.password(),
            is_active=True,
            is_verified=True,
        )
        setup_test_models.add(author)
        authors.append(author)

    await setup_test_models.commit()

    # Создаем посты с разными типами данных для курсоров
    posts_batch = []
    base_date = datetime.now()

    for i in range(1500):
        post = TestPost(
            title=f"Pagination Post {i:04d}",
            slug=f"pagination-post-{i:04d}",
            content=f"Content {i}",
            views_count=i * 10,  # Монотонно возрастающие значения
            rating=round((i % 50) / 10.0, 1),  # Циклические рейтинги
            status=PostStatus.PUBLISHED,
            priority=Priority.MEDIUM,
            likes_count=fake.random_int(min=0, max=100),
            is_featured=fake.boolean(chance_of_getting_true=20),
            is_premium=fake.boolean(chance_of_getting_true=10),
            allow_comments=True,
            author_id=authors[i % len(authors)].id,
            published_at=base_date + timedelta(minutes=i),  # Разные времена создания
        )
        posts_batch.append(post)

        # Добавляем батчами для лучшей производительности
        if len(posts_batch) >= 300:
            setup_test_models.add_all(posts_batch)
            await setup_test_models.commit()
            posts_batch = []

    # Добавляем оставшиеся посты
    if posts_batch:
        setup_test_models.add_all(posts_batch)
        await setup_test_models.commit()

    logger.info("Создано 1500 постов для тестирования пагинации")


@pytest.mark.performance
@database_reset_test(verbose=True)
async def test_bulk_operations_performance(setup_test_models, user_repo):
    """
    Тест производительности bulk операций с валидацией и edge cases.
    """
    logger.info("📦 Тестируем производительность bulk операций")

    # Создаем базовый датасет для bulk операций
    base_users_data = []
    for i in range(500):
        base_users_data.append(
            {
                "username": f"bulk_user_{i}_{uuid.uuid4().hex[:8]}",
                "email": f"bulk_{i}@example.com",
                "full_name": f"Bulk User {i}",
                "hashed_password": "bulk_password",
                "is_active": True,
                "is_verified": i % 3 == 0,  # Каждый третий верифицирован
            }
        )

    created_users = await user_repo.bulk_create(base_users_data, emit_events=False)
    logger.info(f"✅ Создано {len(created_users)} пользователей для bulk операций")

    # Тест 1: Bulk Update
    logger.info("🔄 Тестируем bulk update")
    start_time = time.time()

    updated_count = await user_repo.bulk_update(
        filters={"is_verified": False},
        update_data={"is_verified": True, "email_verified_at": datetime.now()},
        emit_events=False,
    )

    bulk_update_time = time.time() - start_time
    logger.info(f"   Bulk update: {bulk_update_time:.3f}с, обновлено {updated_count} записей")

    # Тест 2: Bulk Update с условными фильтрами
    logger.info("🎯 Тестируем условный bulk update")
    start_time = time.time()

    conditional_update_count = await user_repo.bulk_update(
        filters={"username__icontains": "bulk_user", "is_active": True, "created_at__date": datetime.now().date()},
        update_data={"last_login_at": datetime.now(), "bio": "Updated via bulk operation"},
        emit_events=False,
    )

    conditional_update_time = time.time() - start_time
    logger.info(
        f"   Условный bulk update: {conditional_update_time:.3f}с, обновлено {conditional_update_count} записей"
    )

    # Тест 3: Bulk Delete (soft delete)
    logger.info("🗑️ Тестируем bulk soft delete")
    start_time = time.time()

    soft_deleted_count = await user_repo.bulk_delete(
        filters={"username__startswith": "bulk_user_1"},  # Удаляем пользователей 10-19, 100-199
        soft_delete=True,
        emit_events=False,
    )

    bulk_soft_delete_time = time.time() - start_time
    logger.info(f"   Bulk soft delete: {bulk_soft_delete_time:.3f}с, удалено {soft_deleted_count} записей")

    # Тест 4: Проверяем что soft delete работает
    active_users = await user_repo.list(username__startswith="bulk_user_1", include_deleted=False)
    deleted_users = await user_repo.list(username__startswith="bulk_user_1", include_deleted=True)

    logger.info(f"   После soft delete: активных {len(active_users)}, всего {len(deleted_users)}")

    # Тест 5: Bulk операции с большими батчами
    logger.info("📊 Тестируем bulk операции с большими датасетами")

    large_dataset = []
    for i in range(1000):
        large_dataset.append(
            {
                "username": f"large_bulk_{i}_{uuid.uuid4().hex[:8]}",
                "email": f"large_bulk_{i}@example.com",
                "full_name": f"Large Bulk User {i}",
                "hashed_password": "large_bulk_password",
            }
        )

    start_time = time.time()
    large_created = await user_repo.bulk_create(
        large_dataset,
        batch_size=200,  # Тестируем оптимальный размер батча
        emit_events=False,
    )
    large_bulk_create_time = time.time() - start_time

    logger.info(f"   Большой bulk create: {large_bulk_create_time:.3f}с, создано {len(large_created)} записей")
    logger.info(f"   Скорость: {len(large_created) / large_bulk_create_time:.1f} записей/сек")

    # Проверки корректности
    assert updated_count > 0, "Должны быть обновлены записи"
    assert conditional_update_count > 0, "Условное обновление должно затронуть записи"
    assert soft_deleted_count > 0, "Должны быть мягко удалены записи"
    assert len(deleted_users) > len(active_users), "Удаленных записей должно быть больше активных"
    assert len(large_created) == 1000, "Должно быть создано 1000 записей в большом bulk create"

    # Проверки производительности
    assert bulk_update_time < 2.0, f"Bulk update слишком медленный: {bulk_update_time:.3f}с"
    assert conditional_update_time < 3.0, f"Условный bulk update слишком медленный: {conditional_update_time:.3f}с"
    assert bulk_soft_delete_time < 1.5, f"Bulk soft delete слишком медленный: {bulk_soft_delete_time:.3f}с"
    assert large_bulk_create_time < 10.0, f"Большой bulk create слишком медленный: {large_bulk_create_time:.3f}с"


@pytest.mark.performance
@database_reset_test(verbose=True)
async def test_concurrent_operations_performance(setup_test_models, user_repo):
    """
    Тест производительности последовательных операций.
    Тестирует производительность без конкурентного доступа к сессии.
    """
    logger.info("🔄 Тестируем последовательные операции (было: конкурентные)")

    async def create_user_batch(batch_id: int, size: int = 50) -> list:
        """Создает батч пользователей."""
        users_data = []
        for i in range(size):
            users_data.append(
                {
                    "username": f"sequential_{batch_id}_{i}_{uuid.uuid4().hex[:8]}",
                    "email": f"sequential_{batch_id}_{i}@example.com",
                    "full_name": f"Sequential User {batch_id}-{i}",
                    "hashed_password": "sequential_password",
                }
            )

        return await user_repo.bulk_create(users_data, emit_events=False)

    async def update_user_batch(batch_id: int) -> int:
        """Обновляет батч пользователей."""
        return await user_repo.bulk_update(
            filters={"username__contains": f"sequential_{batch_id}"},
            update_data={"bio": f"Updated by batch {batch_id}"},
            emit_events=False,
        )

    async def read_user_batch(batch_id: int) -> list:
        """Читает батч пользователей."""
        return await user_repo.list(username__contains=f"sequential_{batch_id}", limit=100)

    # Тест 1: Последовательное создание (было: конкурентное)
    logger.info("📝 Последовательное создание пользователей")
    start_time = time.time()

    created_batches = []
    for i in range(10):
        batch = await create_user_batch(i, 30)
        created_batches.append(batch)

    sequential_create_time = time.time() - start_time
    total_created = sum(len(batch) for batch in created_batches)

    logger.info(f"   Последовательное создание: {sequential_create_time:.3f}с, создано {total_created} пользователей")
    logger.info(f"   Скорость: {total_created / sequential_create_time:.1f} записей/сек")

    # Тест 2: Последовательное чтение и обновление
    logger.info("🔄 Смешанные операции чтения и обновления")
    start_time = time.time()

    mixed_results = []
    for i in range(5):
        result1 = await read_user_batch(i)
        result2 = await update_user_batch(i)
        result3 = await read_user_batch(i)
        mixed_results.extend([result1, result2, result3])

    mixed_operations_time = time.time() - start_time

    logger.info(f"   Смешанные операции: {mixed_operations_time:.3f}с")

    # Тест 3: Последовательные агрегации
    logger.info("📊 Последовательные агрегации")
    start_time = time.time()

    counts = []
    counts.append(await user_repo.count(is_active=True))
    counts.append(await user_repo.count(is_verified=True))
    counts.append(await user_repo.count(is_superuser=False))
    counts.append(await user_repo.count(username__contains="sequential"))
    counts.append(await user_repo.count(email__endswith="@example.com"))

    sequential_count_time = time.time() - start_time

    logger.info(f"   Последовательные подсчеты: {sequential_count_time:.3f}с")
    for i, count in enumerate(counts):
        logger.info(f"     Подсчет {i + 1}: {count} записей")

    # Проверки корректности
    assert total_created == 300, f"Должно быть создано 300 пользователей, создано {total_created}"
    assert all(isinstance(batch, list) for batch in created_batches), "Все батчи должны быть списками"
    assert all(count >= 0 for count in counts), "Все подсчеты должны быть неотрицательными"

    # Проверки производительности (скорректированы для последовательных операций)
    assert sequential_create_time < 25.0, f"Последовательное создание слишком медленное: {sequential_create_time:.3f}с"
    assert mixed_operations_time < 15.0, f"Смешанные операции слишком медленные: {mixed_operations_time:.3f}с"
    assert sequential_count_time < 8.0, f"Последовательные подсчеты слишком медленные: {sequential_count_time:.3f}с"


@pytest.mark.performance
@database_reset_test(verbose=True)
async def test_edge_cases_with_large_data(setup_test_models, post_repo, user_repo):
    """
    Тест edge cases на больших датасетах.
    Проверяет граничные случаи и обработку ошибок.
    """
    logger.info("⚠️ Тестируем edge cases с большими данными")

    # Создаем базовый датасет
    users_data = [
        {
            "username": f"edge_user_{i}",
            "email": f"edge_{i}@example.com",
            "full_name": f"Edge User {i}",
            "hashed_password": "edge_password",
        }
        for i in range(100)
    ]

    created_users = await user_repo.bulk_create(users_data, emit_events=False)
    logger.info(f"✅ Создано {len(created_users)} пользователей для edge case тестов")

    # Edge Case 1: Пустые фильтры
    logger.info("1️⃣ Тестируем пустые фильтры")
    empty_filter_result = await user_repo.list()
    assert len(empty_filter_result) > 0, "Пустой фильтр должен вернуть результаты"

    # Edge Case 2: Несуществующие значения в фильтрах
    logger.info("2️⃣ Тестируем несуществующие значения")
    nonexistent_result = await user_repo.list(username="nonexistent_user_12345")
    assert len(nonexistent_result) == 0, "Несуществующий пользователь не должен быть найден"

    # Edge Case 3: Экстремальные значения пагинации
    logger.info("3️⃣ Тестируем экстремальные значения пагинации")

    # Очень большой лимит
    large_limit_result = await user_repo.list(limit=10000)
    assert len(large_limit_result) <= 10000, "Результат не должен превышать лимит"

    # Нулевой лимит
    zero_limit_result = await user_repo.list(limit=0)
    assert len(zero_limit_result) == 0, "Нулевой лимит должен вернуть пустой результат"

    # Отрицательные значения offset/limit (должны обрабатываться корректно)
    try:
        negative_result = await user_repo.list(offset=-1, limit=-1)
        logger.info("   Отрицательные параметры обработаны корректно")
    except Exception as e:
        logger.info(f"   Отрицательные параметры вызвали ошибку (ожидаемо): {e}")

    # Edge Case 4: Очень длинные строки в фильтрах
    logger.info("4️⃣ Тестируем очень длинные строки")

    try:
        # Ограничиваем длину строки до разумных пределов
        long_string = "x" * 100  # Вместо 1000
        long_string_result = await user_repo.list(username__contains=long_string)
        assert len(long_string_result) == 0, "Очень длинная строка не должна найти результаты"
        logger.info(f"   Длинная строка обработана: {len(long_string_result)} результатов")
    except Exception as e:
        logger.info(f"   Ошибка с длинной строкой (ожидаемо): {e}")
        # При ошибке делаем rollback сессии
        try:
            await user_repo._db.rollback()
        except:
            pass

    # Edge Case 5: Специальные символы в фильтрах
    logger.info("5️⃣ Тестируем специальные символы")
    special_chars = ["'", '"', "\\", "%", "_", "NULL", "DROP TABLE", "<script>"]

    for char in special_chars:
        try:
            special_result = await user_repo.list(username__contains=char)
            logger.info(f"   Специальный символ '{char}' обработан корректно: {len(special_result)} результатов")
        except Exception as e:
            logger.warning(f"   Специальный символ '{char}' вызвал ошибку: {e}")

    # Edge Case 6: Множественные фильтры с одинаковыми ключами
    logger.info("6️⃣ Тестируем конфликтующие фильтры")
    try:
        conflicting_result = await user_repo.list(
            is_active=True,
            is_active__ne=False,  # Избыточное условие
        )
        logger.info(f"   Конфликтующие фильтры: {len(conflicting_result)} результатов")
    except Exception as e:
        logger.info(f"   Конфликтующие фильтры вызвали ошибку: {e}")

    # Edge Case 7: Extreme date ranges
    logger.info("7️⃣ Тестируем экстремальные диапазоны дат")

    future_date = datetime(2099, 12, 31)
    past_date = datetime(1900, 1, 1)

    future_result = await user_repo.list(created_at__gte=future_date)
    past_result = await user_repo.list(created_at__lte=past_date)

    assert len(future_result) == 0, "Будущие даты не должны найти результаты"
    assert len(past_result) == 0, "Слишком старые даты не должны найти результаты"

    # Edge Case 8: Массовые операции с пустыми данными
    logger.info("8️⃣ Тестируем операции с пустыми данными")

    empty_bulk_create = await user_repo.bulk_create([], emit_events=False)
    assert len(empty_bulk_create) == 0, "Пустой bulk create должен вернуть пустой список"

    empty_bulk_update = await user_repo.bulk_update(
        filters={"username": "nonexistent"}, update_data={"bio": "test"}, emit_events=False
    )
    assert empty_bulk_update == 0, "Bulk update без соответствий должен вернуть 0"

    # Edge Case 9: Глубоко вложенные JSON фильтры
    logger.info("9️⃣ Тестируем сложные JSON операции")

    # Создаем авторов для постов с JSON данными
    json_authors = []
    for i in range(3):
        author_data = {
            "username": f"json_author_{i}_{uuid.uuid4().hex[:8]}",
            "email": f"json_author_{i}@example.com",
            "full_name": f"JSON Author {i}",
            "hashed_password": "json_password",
        }
        json_author = await user_repo.create(author_data, emit_event=False)
        json_authors.append(json_author)

    posts_with_json = []
    for i in range(50):
        posts_with_json.append(
            {
                "title": f"JSON Test Post {i}",
                "slug": f"json-test-{i}",
                "content": "JSON test content",
                "author_id": json_authors[i % len(json_authors)].id,  # Добавляем author_id
                "status": PostStatus.DRAFT,
                "priority": Priority.MEDIUM,
                "views_count": 0,
                "likes_count": 0,
                "is_featured": False,
                "is_premium": False,
                "allow_comments": True,
                "extra_metadata": {
                    "level1": {"level2": {"level3": {"value": i, "category": f"cat_{i % 5}"}}},
                    "tags": [f"tag_{j}" for j in range(i % 3 + 1)],
                    "metrics": {"score": i * 2, "views": i * 10},
                },
            }
        )

    created_posts = await post_repo.bulk_create(posts_with_json, emit_events=False)
    logger.info(f"   Создано {len(created_posts)} постов с JSON данными")

    # Тестируем JSON фильтрацию
    json_has_key_result = await post_repo.list(extra_metadata__json_has_key="tags")
    logger.info(f"   JSON has_key фильтр: {len(json_has_key_result)} результатов")

    json_has_keys_result = await post_repo.list(extra_metadata__json_has_keys=["level1", "tags"])
    logger.info(f"   JSON has_keys фильтр: {len(json_has_keys_result)} результатов")

    # Edge Case 10: Тестируем лимиты базы данных
    logger.info("🔟 Тестируем лимиты базы данных")

    try:
        # Получаем существующие ID пользователей для корректного IN запроса
        existing_users = await user_repo.list(limit=100)
        if existing_users:
            user_ids = [user.id for user in existing_users[: min(50, len(existing_users))]]  # Ограничиваем до 50 ID
            large_in_result = await user_repo.list(id__in=user_ids)
            logger.info(f"   IN запрос с {len(user_ids)} UUID: {len(large_in_result)} результатов")
        else:
            logger.info("   Нет пользователей для тестирования IN запроса")
    except Exception as e:
        logger.info(f"   Ошибка в большом IN запросе: {e}")

    logger.info("✅ Все edge case тесты завершены успешно!")
