async def test_cursor_pagination(post_repo):
    page1 = await post_repo.paginate_cursor(
        cursor_field="created_at",
        limit=20,
        include_total=True
    )

    if page1.next_cursor:
        page2 = await post_repo.paginate_cursor(
            cursor_value=page1.next_cursor,
            direction="next",
            limit=20
        )
        assert page2 is not None, "Page 2 should not be None"