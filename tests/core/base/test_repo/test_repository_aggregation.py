async def test_aggregations(post_repo):
    stats = await post_repo.aggregate(
        field="views_count",
        operations=["count", "sum", "avg", "max"],
        group_by="status",
        is_featured=True
    )
    assert isinstance(stats, list), "Aggregation result should be a list"