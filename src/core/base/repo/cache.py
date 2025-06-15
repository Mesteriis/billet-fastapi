"""
Caching system for BaseRepository.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from functools import wraps
from typing import Any

logger = logging.getLogger(__name__)

# Попытка импорта Redis (опционально)
try:
    import redis.asyncio as redis
    from redis.asyncio import Redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = None


class SimpleMemoryCache:
    """Simple in-memory cache with TTL support."""

    def __init__(self, default_ttl: int = 300):
        self._cache: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl

    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        if key in self._cache:
            value, expires_at = self._cache[key]
            if time.time() < expires_at:
                return value
            else:
                del self._cache[key]
        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache with TTL."""
        expires_at = time.time() + (ttl or self._default_ttl)
        self._cache[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        self._cache.pop(key, None)

    async def clear(self) -> None:
        """Clear all cache."""
        self._cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        active_entries = sum(1 for _, expires_at in self._cache.values() if expires_at > current_time)

        return {
            "total_entries": len(self._cache),
            "active_entries": active_entries,
            "expired_entries": len(self._cache) - active_entries,
        }


# Global memory cache instance
_memory_cache = SimpleMemoryCache()


class CacheManager:
    """Manages both Redis and memory caching."""

    def __init__(
        self,
        redis_client=None,
        use_redis: bool = True,
        use_memory: bool = True,
        default_ttl: int = 300,
        key_prefix: str = "repo:",
    ):
        self.redis_client = redis_client
        self.use_redis = use_redis and redis_client is not None
        self.use_memory = use_memory
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix

    async def get(self, key: str) -> Any | None:
        """Get value from cache (Redis first, then memory)."""
        full_key = f"{self.key_prefix}{key}"

        # Try Redis first
        if self.use_redis and self.redis_client:
            try:
                cached_data = await self.redis_client.get(full_key)
                if cached_data:
                    return json.loads(cached_data)
            except Exception as e:
                logger.warning(f"Redis cache get error: {e}")

        # Fallback to memory cache
        if self.use_memory:
            try:
                return await _memory_cache.get(full_key)
            except Exception as e:
                logger.warning(f"Memory cache get error: {e}")

        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache (both Redis and memory)."""
        full_key = f"{self.key_prefix}{key}"
        cache_ttl = ttl or self.default_ttl

        # Set in Redis
        if self.use_redis and self.redis_client:
            try:
                await self.redis_client.setex(full_key, cache_ttl, json.dumps(value, default=str))
            except Exception as e:
                logger.warning(f"Redis cache set error: {e}")

        # Set in memory cache
        if self.use_memory:
            try:
                await _memory_cache.set(full_key, value, cache_ttl)
            except Exception as e:
                logger.warning(f"Memory cache set error: {e}")

    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        full_key = f"{self.key_prefix}{key}"

        # Delete from Redis
        if self.use_redis and self.redis_client:
            try:
                await self.redis_client.delete(full_key)
            except Exception as e:
                logger.warning(f"Redis cache delete error: {e}")

        # Delete from memory cache
        if self.use_memory:
            try:
                await _memory_cache.delete(full_key)
            except Exception as e:
                logger.warning(f"Memory cache delete error: {e}")

    async def clear_pattern(self, pattern: str) -> None:
        """Clear cache by pattern."""
        full_pattern = f"{self.key_prefix}{pattern}"

        # Clear Redis by pattern
        if self.use_redis and self.redis_client:
            try:
                keys = await self.redis_client.keys(full_pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                    logger.debug(f"Cleared Redis cache by pattern: {full_pattern}")
            except Exception as e:
                logger.warning(f"Redis cache clear error: {e}")

        # Clear memory cache (simple implementation)
        if self.use_memory and pattern == "*":
            try:
                await _memory_cache.clear()
                logger.debug("Cleared memory cache")
            except Exception as e:
                logger.warning(f"Memory cache clear error: {e}")

    async def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "redis_enabled": self.use_redis,
            "memory_enabled": self.use_memory,
        }

        # Redis stats
        if self.use_redis and self.redis_client:
            try:
                redis_info = await self.redis_client.info("memory")
                stats["redis"] = {
                    "used_memory": redis_info.get("used_memory_human", "N/A"),
                    "connected": True,
                }
            except Exception as e:
                stats["redis"] = {"connected": False, "error": str(e)}

        # Memory cache stats
        if self.use_memory:
            stats["memory"] = _memory_cache.get_stats()

        return stats


def cache_result(ttl: int = 300):
    """
    Decorator for caching query results.

    :param ttl: Time-to-live for cache entry in seconds
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            if not hasattr(self, "_cache_manager") or self._cache_manager is None:
                return await func(self, *args, **kwargs)

            # Generate cache key
            func_name = func.__name__
            model_name = self._model.__name__ if hasattr(self, "_model") else "unknown"

            # Create a cache key from arguments
            cache_data = {
                "args": args,
                "kwargs": {k: v for k, v in kwargs.items() if isinstance(v, (str, int, float, bool, type(None)))},
            }

            cache_key = f"{model_name}:{func_name}:{hashlib.md5(json.dumps(cache_data, sort_keys=True, default=str).encode()).hexdigest()}"

            # Try to get from cache
            cached_result = await self._cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached_result

            # Execute function and cache result
            result = await func(self, *args, **kwargs)

            # Store in cache (only if result is serializable)
            try:
                await self._cache_manager.set(cache_key, result, ttl)
                logger.debug(f"Cache stored for {cache_key}")
            except Exception as e:
                logger.warning(f"Failed to cache result for {cache_key}: {e}")

            return result

        return wrapper

    return decorator


# Global cache manager instance
_default_cache_manager: CacheManager | None = None


def set_default_cache_manager(cache_manager: CacheManager) -> None:
    """Set default cache manager for all repositories."""
    global _default_cache_manager
    _default_cache_manager = cache_manager


def get_default_cache_manager() -> CacheManager | None:
    """Get default cache manager."""
    return _default_cache_manager
