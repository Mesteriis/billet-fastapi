async def test_fulltext_search(post_repo):
    results = await post_repo.fulltext_search(
        search_fields=["title", "content"],
        query_text="python fastapi tutorial",
        search_type="websearch",
        language="english",
        min_rank=0.1,
        include_rank=True
    )
    assert isinstance(results, list)