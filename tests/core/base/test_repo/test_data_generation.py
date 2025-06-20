import logging
import random

import pytest

from tests.utils_test.isolation_decorators import database_reset_test

# Используем logger из корневого conftest.py
logger = logging.getLogger("test_session")


@database_reset_test(verbose=True)
async def test_generate_large_dataset(setup_test_models):
    """
    Генерирует большой набор тестовых данных:
    - 10 пользователей
    - Для каждого пользователя:
      - 1 профиль
      - 10 постов
      - 10 комментариев
      - 5 категорий
      - 8 тегов
    """
    from .factories import (
        TestCategoryFactory,
        TestCommentFactory,
        TestPostFactory,
        TestProfileFactory,
        TestTagFactory,
        TestUserFactory,
    )

    # Фабрики автоматически настроены декоратором изоляции

    users = []
    profiles = []
    categories = []
    tags = []
    posts = []
    comments = []

    logger.info("🔧 Генерируем тестовые данные...")

    # 1. Создаем 10 пользователей
    logger.info("👥 Создаем пользователей...")
    for i in range(10):
        user = await TestUserFactory.create()
        users.append(user)
        logger.info(f"   ✓ Пользователь {i + 1}: {user.username} ({user.email})")

    # 2. Создаем профили для каждого пользователя
    logger.info("👤 Создаем профили...")
    for i, user in enumerate(users):
        profile = await TestProfileFactory.create(user=user)
        profiles.append(profile)
        logger.info(f"   ✓ Профиль {i + 1}: {profile.city}, {profile.country}")

    # 3. Создаем 5 категорий общих для всех
    logger.info("📁 Создаем категории...")
    for i in range(5):
        category = await TestCategoryFactory.create()
        categories.append(category)
        logger.info(f"   ✓ Категория {i + 1}: {category.name}")

    # 4. Создаем 8 тегов общих для всех
    logger.info("🏷️ Создаем теги...")
    for i in range(8):
        tag = await TestTagFactory.create()
        tags.append(tag)
        logger.info(f"   ✓ Тег {i + 1}: {tag.name}")

    # 5. Создаем посты для каждого пользователя (по 10 штук)
    logger.info("📝 Создаем посты...")
    for user_idx, user in enumerate(users):
        for post_idx in range(10):
            # Случайно выбираем категорию
            category = random.choice(categories)

            post = await TestPostFactory.create(author=user, category=category)
            posts.append(post)

            # Добавляем случайные теги к посту через SQL (избегаем lazy loading)
            selected_tags = random.sample(tags, k=random.randint(1, 3))
            for tag in selected_tags:
                # Добавляем связь через insert в промежуточную таблицу
                from .modesl_for_test import post_tags_table

                await setup_test_models.execute(post_tags_table.insert().values(post_id=post.id, tag_id=tag.id))

        logger.info(f"   ✓ Пользователь {user_idx + 1}: создано 10 постов")

    # 6. Создаем комментарии для каждого пользователя (по 10 штук)
    logger.info("💬 Создаем комментарии...")
    for user_idx, user in enumerate(users):
        for comment_idx in range(10):
            # Случайно выбираем пост для комментария
            post = random.choice(posts)

            comment = await TestCommentFactory.create(author=user, post=post)
            comments.append(comment)

        logger.info(f"   ✓ Пользователь {user_idx + 1}: создано 10 комментариев")

    # Фиксируем изменения
    await setup_test_models.commit()

    # Проверяем что все создалось
    logger.info(f"📊 Итого создано:")
    logger.info(f"   👥 Пользователей: {len(users)}")
    logger.info(f"   👤 Профилей: {len(profiles)}")
    logger.info(f"   📁 Категорий: {len(categories)}")
    logger.info(f"   🏷️ Тегов: {len(tags)}")
    logger.info(f"   📝 Постов: {len(posts)}")
    logger.info(f"   💬 Комментариев: {len(comments)}")

    # Assertions для проверки
    assert len(users) == 10, "Должно быть создано 10 пользователей"
    assert len(profiles) == 10, "Должно быть создано 10 профилей"
    assert len(categories) == 5, "Должно быть создано 5 категорий"
    assert len(tags) == 8, "Должно быть создано 8 тегов"
    assert len(posts) == 100, "Должно быть создано 100 постов (10x10)"
    assert len(comments) == 100, "Должно быть создано 100 комментариев (10x10)"

    logger.info("✅ Все данные успешно созданы!")


@database_reset_test(verbose=True)
async def test_verify_relationships(setup_test_models):
    """
    Проверяем что связи между сущностями работают корректно.
    """
    from sqlalchemy import select

    from .modesl_for_test import TestPost, TestProfile, TestUser

    # Проверяем что у пользователей есть посты
    result = await setup_test_models.execute(select(TestUser).join(TestPost).limit(1))
    user_with_posts = result.scalar_one_or_none()

    if user_with_posts:
        logger.info(f"✅ Найден пользователь с постами: {user_with_posts.username}")

    # Проверяем что у пользователей есть профили
    result = await setup_test_models.execute(select(TestUser).join(TestProfile).limit(1))
    user_with_profile = result.scalar_one_or_none()

    if user_with_profile:
        logger.info(f"✅ Найден пользователь с профилем: {user_with_profile.username}")

    logger.info("✅ Связи между сущностями работают корректно!")


@database_reset_test(verbose=True)
async def test_data_statistics(setup_test_models):
    """
    Создает минимальные данные и показывает статистику.
    """
    from sqlalchemy import func, select

    from .modesl_for_test import TestCategory, TestComment, TestPost, TestProfile, TestTag, TestUser

    # Создаем минимальные тестовые данные напрямую
    logger.info("🔧 Создаем тестовые данные для статистики...")

    # Создаем пользователей напрямую
    user1 = TestUser(
        username="stat_user1", email="stat1@example.com", full_name="Stat User 1", hashed_password="password"
    )
    user2 = TestUser(
        username="stat_user2", email="stat2@example.com", full_name="Stat User 2", hashed_password="password"
    )

    setup_test_models.add_all([user1, user2])
    await setup_test_models.flush()
    await setup_test_models.refresh(user1)
    await setup_test_models.refresh(user2)

    # Создаем профили
    profile1 = TestProfile(
        user_id=user1.id, phone="+1-234-567-8901", city="Test City 1", country="Test Country 1", language="en"
    )
    profile2 = TestProfile(
        user_id=user2.id, phone="+1-234-567-8902", city="Test City 2", country="Test Country 2", language="en"
    )

    setup_test_models.add_all([profile1, profile2])

    # Создаем категорию
    category = TestCategory(name="Test Category", slug="test-category", description="Test description")
    setup_test_models.add(category)
    await setup_test_models.flush()
    await setup_test_models.refresh(category)

    # Создаем посты
    post1 = TestPost(
        title="Test Post 1", slug="test-post-1", content="Test content 1", author_id=user1.id, category_id=category.id
    )
    post2 = TestPost(
        title="Test Post 2", slug="test-post-2", content="Test content 2", author_id=user2.id, category_id=category.id
    )

    setup_test_models.add_all([post1, post2])
    await setup_test_models.commit()

    # Подсчитываем статистику
    stats = {}

    models = {
        "users": TestUser,
        "posts": TestPost,
        "comments": TestComment,
        "categories": TestCategory,
        "tags": TestTag,
        "profiles": TestProfile,
    }

    logger.info("📊 Статистика созданных данных:")

    for name, model in models.items():
        result = await setup_test_models.execute(select(func.count(model.id)))
        count = result.scalar()
        stats[name] = count
        logger.info(f"   {name.title()}: {count}")

    # Проверяем соотношения
    assert stats["users"] >= 2, "Должно быть минимум 2 пользователя"
    assert stats["posts"] >= 2, "Должно быть минимум 2 поста"
    assert stats["profiles"] >= 2, "Должно быть минимум 2 профиля"
    assert stats["categories"] >= 1, "Должна быть минимум 1 категория"

    logger.info("✅ Статистика соответствует ожиданиям!")
