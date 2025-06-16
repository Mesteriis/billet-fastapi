from datetime import date

import pytest

from .enums import PostStatus


@pytest.mark.parametrize(
    "filters, description",
    [
        ({"views_count__gt": 100}, "Views count should be greater than 100"),
        ({"rating__between": [3.0, 5.0]}, "Rating should be between 3.0 and 5.0"),
        ({"status__in": [PostStatus.PUBLISHED]}, "Status should be published"),

        ({"title__icontains": "python"}, "Title should contain 'python'"),
        ({"slug__startswith": "tutorial"}, "Slug should start with 'tutorial'"),
        ({"content__regex": r"\b\w+@\w+\.\w+\b"}, "Content should match email regex"),

        ({"published_at__isnull": False}, "Published at should not be null"),
        ({"excerpt__isnotnull": True}, "Excerpt should not be null"),

        ({"published_at__date": date.today()}, "Published at should be today"),
        ({"created_at__year": 2024}, "Created at should be in the year 2024"),
        ({"created_at__month": 12}, "Created at should be in December"),
        ({"published_at__week_day": 1}, "Published at should be on a Monday"),

        ({"metadata__json_has_key": "featured"}, "Metadata should have key 'featured'"),
        ({"seo_data__json_contains": {"robots": "index"}}, "SEO data should contain 'robots': 'index'"),

        ({"author__email__endswith": "@company.com"}, "Author email should end with '@company.com'"),
        ({"category__name": "Technology"}, "Category name should be 'Technology'"),
        ({"comments__is_approved": True}, "Comments should be approved"),
    ]
)
async def test_advanced_filters(post_repo, filters, description):
    result = await post_repo.list(**filters)
    assert isinstance(result, list), f"{description} — Result should be a list"
