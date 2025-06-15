"""
Types and dataclasses for BaseRepository system.
"""

from __future__ import annotations

from pydantic.dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from redis.asyncio import Redis # type: ignore[import-untyped]

ModelType = TypeVar("ModelType")


@dataclass
class CacheConfig:
    """
    Configuration for caching system.

    :param redis_client: Redis client instance (optional)
    :param default_ttl: Default time-to-live for cache entries in seconds
    :param key_prefix: Prefix for cache keys
    :param use_redis: Whether to use Redis caching
    :param use_memory: Whether to use in-memory caching as fallback
    """

    redis_client: Any = None
    default_ttl: int = 300
    key_prefix: str = "repo:"
    use_redis: bool = True
    use_memory: bool = True


@dataclass
class AggregationResult:
    """
    Result of aggregation operation.

    :param field_name: Name of the field that was aggregated
    :param count: Count of records
    :param sum: Sum of values
    :param avg: Average of values
    :param min: Minimum value
    :param max: Maximum value
    :param group_by: Grouping information if used
    """

    field_name: str
    count: int | None = None
    sum: float | None = None
    avg: float | None = None
    min: Any = None
    max: Any = None
    group_by: dict[str, Any] | None = None


@dataclass
class CursorPaginationResult(Generic[ModelType]):
    """
    Result of cursor pagination.

    :param items: List of paginated items
    :param next_cursor: Cursor for next page
    :param prev_cursor: Cursor for previous page
    :param has_next: Whether there are more items after current page
    :param has_prev: Whether there are more items before current page
    :param total_count: Total count of items (optional, expensive to calculate)
    """

    items: list[ModelType]
    next_cursor: str | None = None
    prev_cursor: str | None = None
    has_next: bool = False
    has_prev: bool = False
    total_count: int | None = None


@dataclass
class CacheStats:
    """
    Cache statistics.

    :param cache_enabled: Whether caching is enabled
    :param model: Model name
    :param redis_stats: Redis statistics
    :param memory_stats: Memory cache statistics
    """

    cache_enabled: bool
    model: str
    redis_stats: dict[str, Any] | None = None
    memory_stats: dict[str, Any] | None = None


@dataclass
class BulkOperationResult:
    """
    Result of bulk operation.

    :param affected_count: Number of affected records
    :param success: Whether operation was successful
    :param errors: List of errors if any
    :param execution_time: Time taken to execute operation
    """

    affected_count: int
    success: bool = True
    errors: list[str] | None = None
    execution_time: float | None = None
