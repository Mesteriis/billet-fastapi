"""
Базовые dependencies для авторизации.
"""

import uuid
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.exceptions import (
    AuthCSRFValidationError,
    AuthInsufficientPermissionsError,
    AuthSessionValidationError,
    AuthTokenValidationError,
    AuthUserInactiveError,
    AuthUserNotFoundError,
    AuthUserNotVerifiedError,
)
from apps.auth.schemas.token_schemas import JWTPayload
from apps.auth.services.jwt_service import JWTService
from core.database import get_db
from core.enums import UserRole
from core.interfaces import UserProtocol, UserServiceProtocol

# Используем TYPE_CHECKING для конкретных типов
if TYPE_CHECKING:
    from apps.users.models.user_models import User
    from apps.users.services.user_service import UserService

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)

# Type aliases for dependencies
DbSession = Annotated[AsyncSession, Depends(get_db)]
BearerToken = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


async def get_jwt_service(db: DbSession) -> JWTService:
    """
    Получить сервис JWT токенов.

    :param db: Сессия базы данных
    :return: Экземпляр JWTService
    """
    from apps.auth.repo.refresh_token_repo import RefreshTokenRepository
    from apps.users.repo.user_repo import UserRepository

    refresh_token_repo = RefreshTokenRepository(db)
    user_repo = UserRepository(db)
    return JWTService(refresh_token_repo, user_repo)


async def get_user_service(db: DbSession) -> "UserService":
    """
    Получить сервис пользователей.

    :param db: Сессия базы данных
    :return: Экземпляр UserService
    """
    # Отложенный импорт для избежания циклических зависимостей
    from apps.users.repo.profile_repo import ProfileRepository
    from apps.users.repo.user_repo import UserRepository
    from apps.users.services.user_service import UserService

    user_repo = UserRepository(db)
    profile_repo = ProfileRepository(db)
    return UserService(user_repo, profile_repo)


async def get_current_token_payload(
    credentials: BearerToken, jwt_service: Annotated[JWTService, Depends(get_jwt_service)]
) -> JWTPayload:
    """
    Получить payload текущего JWT токена.

    :param credentials: Bearer токен
    :param jwt_service: Сервис JWT
    :return: Payload токена
    :raises HTTPException: Если токен невалидный
    """
    if not credentials:
        raise AuthTokenValidationError(message="Authorization token required")

    token_payload = await jwt_service.verify_access_token(credentials.credentials)
    if not token_payload:
        raise AuthTokenValidationError(message="Invalid or expired token")

    return token_payload


async def get_current_user(
    token_payload: Annotated[JWTPayload, Depends(get_current_token_payload)],
    user_service: Annotated["UserService", Depends(get_user_service)],
) -> "User":
    """
    Получить текущего пользователя по JWT токену.

    :param token_payload: Payload JWT токена
    :param user_service: Сервис пользователей
    :return: Текущий пользователь
    :raises HTTPException: Если пользователь не найден
    """
    user = await user_service.get_user_by_id(token_payload.user_id)
    if not user:
        raise AuthUserNotFoundError(message="User not found")

    return user


async def get_current_active_user(current_user: Annotated["User", Depends(get_current_user)]) -> "User":
    """
    Получить текущего активного пользователя.

    :param current_user: Текущий пользователь
    :return: Активный пользователь
    :raises HTTPException: Если пользователь неактивен
    """
    if not current_user.can_login:
        raise AuthUserInactiveError(message="User account is inactive or suspended")

    return current_user


async def get_current_verified_user(current_user: Annotated["User", Depends(get_current_active_user)]) -> "User":
    """
    Получить текущего верифицированного пользователя.

    :param current_user: Текущий активный пользователь
    :return: Верифицированный пользователь
    :raises HTTPException: Если пользователь не верифицирован
    """
    if not current_user.is_verified:
        raise AuthUserNotVerifiedError(message="Email verification required")

    return current_user


def require_role(required_role: UserRole):
    """
    Dependency factory для проверки роли пользователя.

    :param required_role: Требуемая роль
    :return: Dependency function
    """

    async def check_role(current_user: Annotated["User", Depends(get_current_active_user)]) -> "User":
        """
        Проверить роль пользователя.

        :param current_user: Текущий пользователь
        :return: Пользователь с требуемой ролью
        :raises HTTPException: Если недостаточно прав
        """
        if not current_user.has_role(required_role):
            raise AuthInsufficientPermissionsError(message=f"Role {required_role.value} or higher required")

        return current_user

    return check_role


def require_permissions(required_permissions: list[str]):
    """
    Dependency factory для проверки разрешений пользователя.

    :param required_permissions: Список требуемых разрешений
    :return: Dependency function
    """

    async def check_permissions(
        token_payload: Annotated[JWTPayload, Depends(get_current_token_payload)],
        current_user: Annotated["User", Depends(get_current_active_user)],
    ) -> "User":
        """
        Проверить разрешения пользователя.

        :param token_payload: Payload токена с правами
        :param current_user: Текущий пользователь
        :return: Пользователь с требуемыми правами
        :raises HTTPException: Если недостаточно прав
        """
        user_permissions = token_payload.permissions

        missing_permissions = [perm for perm in required_permissions if perm not in user_permissions]

        if missing_permissions:
            raise AuthInsufficientPermissionsError(message=f"Missing permissions: {', '.join(missing_permissions)}")

        return current_user

    return check_permissions


# Готовые dependencies для различных ролей
RequireUser = Depends(get_current_active_user)
RequireVerifiedUser = Depends(get_current_verified_user)
RequireModerator = Depends(require_role(UserRole.MODERATOR))
RequireAdmin = Depends(require_role(UserRole.ADMIN))
RequireSuperuser = Depends(require_role(UserRole.SUPERUSER))

# Готовые dependencies для различных разрешений
RequireReadUsers = Depends(require_permissions(["read:users"]))
RequireWriteUsers = Depends(require_permissions(["write:users"]))
RequireDeleteUsers = Depends(require_permissions(["delete:users"]))
RequireManageSystem = Depends(require_permissions(["manage:system"]))


async def get_optional_current_user(
    credentials: BearerToken,
    jwt_service: Annotated[JWTService, Depends(get_jwt_service)],
    user_service: Annotated["UserService", Depends(get_user_service)],
) -> "User | None":
    """
    Получить текущего пользователя опционально (без ошибки если токен отсутствует).

    :param credentials: Bearer токен (опционально)
    :param jwt_service: Сервис JWT
    :param user_service: Сервис пользователей
    :return: Пользователь или None
    """
    if not credentials:
        return None

    try:
        token_payload = await jwt_service.verify_access_token(credentials.credentials)
        if not token_payload:
            return None

        user = await user_service.get_user_by_id(token_payload.user_id)
        if not user or not user.can_login:
            return None

        return user
    except Exception:
        return None


def get_user_from_id(user_id: uuid.UUID):
    """
    Dependency factory для получения пользователя по ID из path.

    :param user_id: ID пользователя из path параметра
    :return: Dependency function
    """

    async def get_user(user_service: Annotated["UserService", Depends(get_user_service)]) -> "User":
        """
        Получить пользователя по ID.

        :param user_service: Сервис пользователей
        :return: Пользователь
        :raises HTTPException: Если пользователь не найден
        """
        user = await user_service.get_user_by_id(user_id)
        if not user:
            raise AuthUserNotFoundError(message="User not found")

        return user

    return get_user


async def verify_user_access(
    target_user_id: uuid.UUID, current_user: Annotated["User", Depends(get_current_active_user)]
) -> bool:
    """
    Проверить доступ пользователя к ресурсу другого пользователя.

    :param target_user_id: ID целевого пользователя
    :param current_user: Текущий пользователь
    :return: True если доступ разрешен
    :raises HTTPException: Если доступ запрещен
    """
    # Пользователь может получить доступ к своим данным
    if current_user.id == target_user_id:
        return True

    # Администраторы имеют доступ ко всем данным
    if current_user.is_admin:
        return True

    raise AuthInsufficientPermissionsError(message="Access denied to user resource")


# Type aliases для использования в роутах
CurrentUserDep = Annotated["User", Depends(get_current_user)]
CurrentActiveUserDep = Annotated["User", Depends(get_current_active_user)]
CurrentVerifiedUserDep = Annotated["User", Depends(get_current_verified_user)]
OptionalCurrentUserDep = Annotated["User | None", Depends(get_optional_current_user)]

# Role-based dependencies
RequireUserDep = Annotated["User", RequireUser]
RequireVerifiedUserDep = Annotated["User", RequireVerifiedUser]
RequireModeratorDep = Annotated["User", RequireModerator]
RequireAdminDep = Annotated["User", RequireAdmin]
RequireSuperuserDep = Annotated["User", RequireSuperuser]

# Permission-based dependencies
RequireReadUsersDep = Annotated["User", RequireReadUsers]
RequireWriteUsersDep = Annotated["User", RequireWriteUsers]
RequireDeleteUsersDep = Annotated["User", RequireDeleteUsers]
RequireManageSystemDep = Annotated["User", RequireManageSystem]
