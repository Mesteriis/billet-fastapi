from tests.core.base.test_repo.enums import PostStatus


async def test_complex_filtering(post_repo):
    posts = await post_repo.list_with_complex_filters({
        "AND": [
            {"status": PostStatus.PUBLISHED},
            {"OR": [
                {"is_featured": True},
                {"views_count__gte": 1000}
            ]},
            {"NOT": [
                {"author__is_active": False}
            ]}
        ]
    })
    assert isinstance(posts, list)