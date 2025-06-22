"""
Core repository system with modular mixins.
"""

from .cache import CacheManager, cache_result, get_default_cache_manager, set_default_cache_manager
from .events import CreateEvent, DeleteEvent, UpdateEvent

# Миксины
from .mixins import AdvancedMixin, BaseCrudMixin, EnterpriseMixin, EventMixin

# Базовые компоненты
from .query_builder import BASIC_FILTER_OPERATORS, OPERATORS, QueryBuilder

# Готовые репозитории
from .repository import BaseRepository  # для обратной совместимости
from .repository import (
    AdvancedRepository,
    EnterpriseRepository,
    EventDrivenRepository,
    FullRepository,
    SimpleRepository,
)
from .types import AggregationResult, BulkOperationResult, CacheConfig, CacheStats, CursorPaginationResult

# Алиасы для удобства
Repository = SimpleRepository  # для простых случаев
FullFeaturedRepository = FullRepository  # для всех возможностей

__all__ = [
    # Базовые компоненты
    "QueryBuilder",
    "OPERATORS",
    "BASIC_FILTER_OPERATORS",
    "CacheManager",
    "cache_result",
    "get_default_cache_manager",
    "set_default_cache_manager",
    # События
    "CreateEvent",
    "UpdateEvent",
    "DeleteEvent",
    # Типы
    "AggregationResult",
    "CursorPaginationResult",
    "CacheConfig",
    "CacheStats",
    "BulkOperationResult",
    # Миксины
    "BaseCrudMixin",
    "AdvancedMixin",
    "EnterpriseMixin",
    "EventMixin",
    # Готовые репозитории
    "SimpleRepository",
    "AdvancedRepository",
    "EventDrivenRepository",
    "EnterpriseRepository",
    "FullRepository",
    "BaseRepository",
    # Алиасы
    "Repository",
    "FullFeaturedRepository",
]
