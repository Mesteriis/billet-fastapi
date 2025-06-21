"""
Dependencies для авторизации.
"""

from .base import (  # Type aliases
    CurrentActiveUserDep,
    CurrentUserDep,
    CurrentVerifiedUserDep,
    OptionalCurrentUserDep,
    RequireAdmin,
    RequireAdminDep,
    RequireDeleteUsersDep,
    RequireManageSystemDep,
    RequireModerator,
    RequireModeratorDep,
    RequireReadUsersDep,
    RequireSuperuserDep,
    RequireUser,
    RequireUserDep,
    RequireVerifiedUser,
    RequireVerifiedUserDep,
    RequireWriteUsersDep,
    get_current_active_user,
    get_current_user,
    get_current_verified_user,
    get_optional_current_user,
)
from .repositories import (
    OrbitalTokenRepoDep,
    RefreshTokenRepoDep,
    UserSessionRepoDep,
    get_orbital_token_repo,
    get_refresh_token_repo,
    get_user_session_repo,
)
from .services import JWTServiceDep, OrbitalServiceDep, SessionServiceDep, get_orbital_service, get_session_service
from .session import (
    CSRFProtected,
    CurrentSession,
    RequiredSession,
    SessionUser,
    get_current_session,
    get_required_session,
    get_user_from_session,
    verify_csrf_token,
)

__all__ = [
    "get_jwt_service",
    "get_user_service",
    "get_current_user",
    "get_current_active_user",
    "RequireUser",
    "RequireAdmin",
    "get_orbital_service",
    "get_session_service",
    "JWTServiceDep",
    "SessionUser",
]
