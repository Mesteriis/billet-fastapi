import pytest



@pytest.mark.asyncio
async def test_crud_operations(user, post_repo, post_create_schema):
    post_data = post_create_schema(
        title="Test Post",
        slug="test-post",
        content="Content",
        author_id=user.id
    )

    # Create
    post = await post_repo.create(post_data)
    assert post.title == "Test Post", "Post title does not match"

    # Read
    found = await post_repo.get(post.id)
    assert found is not None, "Post not found after creation"
    assert found.id == post.id, "Post ID does not match after creation"

    # Update
    updated = await post_repo.update(post, {"title": "Updated"})
    assert updated.title == "Updated", "Post title was not updated correctly"

    # Soft delete
    await post_repo.remove(post.id, soft_delete=True)
    deleted = await post_repo.get(post.id)
    assert deleted is None, "Post was not soft deleted"