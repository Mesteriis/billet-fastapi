"""
Приложение пользователей.

Содержит модели, схемы, репозитории и API для работы с пользователями и их профилями.
"""

from . import api, depends, models, repo, schemas, services
from .interfaces import (  # Type aliases
    ProfileData,
    UserActivityData,
    UserAdmin,
    UserAuth,
    UserIdentity,
    UserManagement,
    UserProfileData,
    UserRef,
    UserReference,
    UserSearchResult,
    UserStatistics,
    UserStats,
)

__all__ = [
    "depends",
    "models",
    "schemas",
    "repo",
    "services",
    # Interfaces
    "UserReference",
    "UserIdentity",
    "UserProfileData",
    "UserManagement",
    "UserStatistics",
    "UserSearchResult",
    "UserActivityData",
    # Type aliases
    "UserRef",
    "UserAuth",
    "ProfileData",
    "UserAdmin",
    "UserStats",
]
