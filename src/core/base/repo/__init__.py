__doc__ = """
BaseRepository and QueryBuilder module for working with SQLAlchemy models

This module provides advanced functionality for database operations:

**Main Features:**
- CRUD operations with automatic events
- Advanced filtering with 40+ operators
- PostgreSQL full-text search (tsvector/tsquery)
- Query caching (Redis + Memory fallback)
- Data aggregations (SUM, AVG, MAX, MIN)
- Cursor pagination for large datasets
- Bulk operations for mass changes
- Automatic cache warming for popular queries
- Event system and logging
- Soft delete support

**Filter Operators:**

*Basic:*
- eq: equals
- ne: not equals
- lt: less than
- lte: less than or equal
- gt: greater than
- gte: greater than or equal

*String:*
- like: LIKE (with % wildcards)
- ilike: case-insensitive LIKE
- startswith: starts with
- istartswith: starts with (case-insensitive)
- endswith: ends with
- iendswith: ends with (case-insensitive)
- exact: exact match
- iexact: exact match (case-insensitive)
- contains: contains substring
- icontains: contains substring (case-insensitive)
- regex: regular expression
- iregex: regular expression (case-insensitive)

*Collections:*
- in: in list of values
- not_in: not in list of values
- between: between two values
- not_between: not between two values

*NULL values:*
- isnull: equals NULL
- isnotnull: not equals NULL

*Date operations:*
- date: equals date (ignores time)
- date_gt: date greater than
- date_gte: date greater than or equal
- date_lt: date less than
- date_lte: date less than or equal
- year: year equals
- month: month equals
- day: day equals
- week: week of year equals
- quarter: quarter equals
- week_day: day of week equals
- hour: hour equals
- minute: minute equals
- second: second equals
- time: time equals (ignores date)

*JSON fields:*
- json_contains: JSON contains value
- json_has_key: JSON has key
- json_has_keys: JSON has all keys
- json_has_any_keys: JSON has any of keys
- json_path: JSON path expression
- json_extract: extract by path

*PostgreSQL full-text search:*
- search: full-text search (Russian language)
- search_phrase: phrase search
- search_websearch: web search
- search_raw: raw tsquery search
- search_rank: search rank
- search_rank_cd: search rank with cover density
- search_en: search in English
- search_simple: simple search

**Usage Example:**

```python
# Create repository with caching
cache_config = CacheConfig(
    redis_client=redis_client,
    default_ttl=600,
    use_redis=True,
    use_memory=True
)
repo = BaseRepository(User, db_session, cache_config)

# Basic CRUD operations
user = await repo.create({"name": "John", "email": "john@example.com"})
users = await repo.list(limit=10, is_active=True)
user = await repo.get(user_id)
updated_user = await repo.update(user, {"name": "Jane"})

# Advanced filtering
users = await repo.list(
    age__between=[18, 65],
    email__endswith="@company.com",
    created_at__date_gte=date(2023, 1, 1),
    name__icontains="john"
)

# Full-text search
search_results = await repo.fulltext_search(
    search_fields=["title", "description"],
    query_text="python fastapi",
    search_type="websearch",
    min_rank=0.1,
    status="published"
)

# Aggregations
stats = await repo.aggregate(
    field="age",
    operations=["count", "avg", "min", "max"],
    group_by="department",
    is_active=True
)

# Cursor pagination
page1 = await repo.paginate_cursor(limit=10)
page2 = await repo.paginate_cursor(
    cursor_value=page1.next_cursor,
    direction="next",
    limit=10
)

# Bulk operations
await repo.bulk_create([
    {"name": "User1", "email": "user1@example.com"},
    {"name": "User2", "email": "user2@example.com"}
])

await repo.bulk_update(
    filters={"department": "old_dept"},
    update_data={"department": "new_dept"}
)

# Complex filtering
complex_users = await repo.list_with_complex_filters({
    "AND": [
        {"age__gte": 18},
        {"OR": [
            {"email__endswith": "@company.com"},
            {"role": "admin"}
        ]}
    ]
})

# Cache management
await repo.invalidate_cache("list:*")  # Clear all list queries
await repo.invalidate_cache()  # Clear all model cache
await repo.warm_cache()  # Warm popular queries
```

**Caching:**

The system supports two-level caching:
1. Redis (priority) - for distributed caching
2. Memory (fallback) - local in-memory cache

Cache is automatically invalidated on data changes (create/update/delete/restore).
Popular queries are automatically warmed based on usage patterns.

**Performance:**

- Cursor pagination is efficient for large datasets
- Full-text search uses PostgreSQL indexes
- Aggregations are performed at database level
- Caching reduces database load
- Bulk operations minimize database round-trips

Author: AVM
Version: 3.1.0 (with bulk operations and cache warming)
Date: 2025
"""

__all__ = [
    "BaseRepository",
    "QueryBuilder",
    "CacheConfig",
    "AggregationResult",
    "CursorPaginationResult",
    "CacheManager",
    "cache_result",
]

from .cache import CacheManager, cache_result
from .repository import BaseRepository, QueryBuilder
from .types import AggregationResult, CacheConfig, CursorPaginationResult
