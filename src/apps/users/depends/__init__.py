"""
Dependencies для пользователей.
"""

from .repositories import ProfileRepoDep, UserRepoDep, get_profile_repo, get_user_repo
from .services import ProfileServiceDep, UserServiceDep, get_profile_service, get_user_service
from .users import (  # Type aliases
    ProfileFromPath,
    ProfileFromPathDep,
    PublicProfile,
    PublicProfileDep,
    RequireActiveStatus,
    RequireActiveStatusDep,
    RequireVerified,
    RequireVerifiedDep,
    UserFromPath,
    UserFromPathDep,
    UserWithAccess,
    UserWithAccessDep,
    get_profile_by_user_id,
    get_user_by_id,
)

__all__ = [
    "get_user_service",
    "get_profile_service",
    "UserServiceDep",
    "ProfileServiceDep",
    "get_user_by_id",
    "get_profile_by_user_id",
    "verify_user_access",
    "UserFromPath",
    "ProfileFromPath",
    "RequireVerified",
]
