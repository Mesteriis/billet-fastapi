"""
Схемы валидации приложения пользователей.
"""

from .profile_schemas import (
    ProfileBase,
    ProfileCreate,
    ProfilePublicResponse,
    ProfileResponse,
    ProfileSearchFilters,
    ProfileSettingsUpdate,
    ProfilesListResponse,
    ProfileUpdate,
    ProfileUpdateRequest,
)
from .user_schemas import (
    UserAdminUpdate,
    UserBase,
    UserCreate,
    UserCreateRequest,
    UserFilters,
    UserListResponse,
    UserPasswordUpdate,
    UserPublicResponse,
    UserResponse,
    UserRoleUpdateRequest,
    UsersListResponse,
    UserStatsResponse,
    UserStatusUpdateRequest,
    UserUpdate,
    UserUpdateRequest,
)

__all__ = [
    # User schemas
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserPasswordUpdate",
    "UserAdminUpdate",
    "UserResponse",
    "UserPublicResponse",
    "UserListResponse",
    "UserStatsResponse",
    "UserCreateRequest",
    "UserUpdateRequest",
    "UsersListResponse",
    "UserStatusUpdateRequest",
    "UserRoleUpdateRequest",
    "UserFilters",
    # Profile schemas
    "ProfileBase",
    "ProfileCreate",
    "ProfileUpdate",
    "ProfileSettingsUpdate",
    "ProfileResponse",
    "ProfilePublicResponse",
    "ProfileUpdateRequest",
    "ProfilesListResponse",
    "ProfileSearchFilters",
]
