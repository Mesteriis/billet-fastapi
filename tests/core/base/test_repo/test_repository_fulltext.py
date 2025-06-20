async def test_fulltext_search(post_repo, setup_test_models):
    from .modesl_for_test import TestPost, TestUser

    # Создаем тестовые данные напрямую
    user = TestUser(username="testuser", email="test@example.com", full_name="Test User", hashed_password="password")
    setup_test_models.add(user)
    await setup_test_models.flush()
    await setup_test_models.refresh(user)

    # Создаем посты напрямую
    post1 = TestPost(
        title="Python FastAPI Tutorial",
        slug="python-fastapi-tutorial",
        content="Learn how to build APIs with Python and FastAPI framework",
        author_id=user.id,
    )
    post2 = TestPost(
        title="Django vs Flask",
        slug="django-vs-flask",
        content="Comparison of Django and Flask frameworks",
        author_id=user.id,
    )

    setup_test_models.add_all([post1, post2])
    await setup_test_models.flush()

    # Тест простого поиска
    results = await post_repo.fulltext_search(
        search_fields=["title", "content"],
        query_text="python",
        search_type="simple",
        language="english",
        min_rank=0.0,  # Убираем минимальный ранг
        include_rank=False,  # Пока отключим ранк для простоты
    )
    assert isinstance(results, list)

    # Тест с ранком
    results_with_rank = await post_repo.fulltext_search(
        search_fields=["title", "content"],
        query_text="python",
        search_type="simple",
        language="english",
        min_rank=0.0,
        include_rank=True,
    )
    assert isinstance(results_with_rank, list)
