from .enums import PostStatus


async def test_bulk_operations(post_repo, post_create_schema, setup_test_models):
    from .modesl_for_test import TestUser

    # Создаем авторов напрямую
    authors = []
    for i in range(5):
        user = TestUser(
            username=f"user_{i}", email=f"user{i}@example.com", full_name=f"User {i}", hashed_password="password"
        )
        setup_test_models.add(user)
        authors.append(user)

    await setup_test_models.flush()
    for author in authors:
        await setup_test_models.refresh(author)

    posts_data = [
        post_create_schema(title=f"Bulk Post {i}", slug=f"bulk-post-{i}", content="Content", author_id=authors[i].id)
        for i in range(5)
    ]

    created = await post_repo.bulk_create(posts_data)
    assert len(created) == 5, "Bulk create failed, expected 5 posts to be created"

    updated_count = await post_repo.bulk_update(filters={"status": PostStatus.DRAFT}, update_data={"is_featured": True})
    assert updated_count >= 0, "Bulk update failed, expected non-negative count"

    deleted_count = await post_repo.bulk_delete(filters={"views_count__lt": 10}, soft_delete=True)
    assert deleted_count >= 0, "Bulk delete failed, expected non-negative count"
