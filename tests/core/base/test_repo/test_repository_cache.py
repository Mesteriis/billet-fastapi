from .enums import PostStatus


async def test_cache_operations(post_repo):
    await post_repo.warm_cache([
        {"status": PostStatus.PUBLISHED},
        {"is_featured": True},
        {"limit": 10}
    ])

    stats = await post_repo.get_cache_stats()
    assert isinstance(stats, dict)

    await post_repo.invalidate_cache("posts:*")