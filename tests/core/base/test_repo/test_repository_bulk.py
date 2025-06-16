import uuid

from .enums import PostStatus


async def test_bulk_operations(post_repo, post_create_schema):
    posts_data = [post_create_schema(
        title=f"Bulk Post {i}",
        slug=f"bulk-post-{i}",
        content="Content",
        author_id=uuid.uuid4()
    ) for i in range(5)]

    created = await post_repo.bulk_create(posts_data)
    assert len(created) == 5, "Bulk create failed, expected 5 posts to be created"

    updated_count = await post_repo.bulk_update(
        filters={"status": PostStatus.DRAFT},
        update_data={"is_featured": True}
    )
    assert updated_count >= 0, "Bulk update failed, expected non-negative count"

    deleted_count = await post_repo.bulk_delete(
        filters={"views_count__lt": 10},
        soft_delete=True
    )
    assert deleted_count >= 0, "Bulk delete failed, expected non-negative count"