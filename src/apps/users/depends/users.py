"""
Dependencies для работы с пользователями.
"""

import uuid
from typing import Annotated

from fastapi import Depends, Path, status

from apps.users.depends.services import ProfileServiceDep, UserServiceDep
from apps.users.exceptions import (
    ProfileAccessValidationError,
    ProfilePrivacyValidationError,
    UserAccessValidationError,
    UserResourceOwnershipError,
    UserStatusValidationError,
    UserVerificationValidationError,
)
from apps.users.models.enums import UserRole, UserStatus
from apps.users.models.user_models import User, UserProfile
from apps.users.services.profile_service import ProfileService
from apps.users.services.user_service import UserService


async def get_user_by_id(
    user_id: Annotated[uuid.UUID, Path(..., description="ID пользователя")], user_service: UserServiceDep
) -> User:
    """
    Получить пользователя по ID из path параметра.

    :param user_id: ID пользователя
    :param user_service: Сервис пользователей
    :return: Пользователь
    :raises HTTPException: Если пользователь не найден
    """
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise UserAccessValidationError(message="User not found")

    return user


async def get_profile_by_user_id(
    user_id: Annotated[uuid.UUID, Path(..., description="ID пользователя")], profile_service: ProfileServiceDep
) -> UserProfile:
    """
    Получить профиль пользователя по ID пользователя.

    :param user_id: ID пользователя
    :param profile_service: Сервис профилей
    :return: Профиль пользователя
    :raises HTTPException: Если профиль не найден
    """
    profile = await profile_service.get_profile_by_user_id(user_id)
    if not profile:
        raise ProfileAccessValidationError(message="User profile not found")

    return profile


def verify_user_access(require_owner_or_admin: bool = True):
    """
    Dependency factory для проверки доступа к данным пользователя.

    :param require_owner_or_admin: Требовать права владельца или админа
    :return: Dependency function
    """

    async def check_access(
        target_user: Annotated[User, Depends(get_user_by_id)],
        current_user: Annotated[User, Depends("apps.auth.depends.base.get_current_active_user")],
    ) -> User:
        """
        Проверить доступ к данным пользователя.

        :param target_user: Целевой пользователь
        :param current_user: Текущий пользователь
        :return: Целевой пользователь
        :raises HTTPException: Если доступ запрещен
        """
        if require_owner_or_admin:
            # Пользователь может получить доступ к своим данным
            if current_user.id == target_user.id:
                return target_user

            # Администраторы имеют доступ ко всем данным
            if current_user.is_admin:
                return target_user

            raise UserResourceOwnershipError(message="Access denied to user resource")

        return target_user

    return check_access


def verify_profile_access(require_public_or_owner: bool = True):
    """
    Dependency factory для проверки доступа к профилю пользователя.

    :param require_public_or_owner: Требовать публичность или права владельца
    :return: Dependency function
    """

    async def check_profile_access(
        profile: Annotated[UserProfile, Depends(get_profile_by_user_id)],
        current_user: Annotated[User | None, Depends("apps.auth.depends.base.get_optional_current_user")] = None,
    ) -> UserProfile:
        """
        Проверить доступ к профилю пользователя.

        :param profile: Профиль пользователя
        :param current_user: Текущий пользователь (опционально)
        :return: Профиль пользователя
        :raises HTTPException: Если доступ запрещен
        """
        if require_public_or_owner:
            # Публичные профили доступны всем
            if profile.public_profile:
                return profile

            # Если пользователь не авторизован и профиль приватный
            if not current_user:
                raise ProfilePrivacyValidationError(message="Private profile access requires authentication")

            # Владелец может видеть свой профиль
            if current_user.id == profile.user_id:
                return profile

            # Администраторы могут видеть все профили
            if current_user.is_admin:
                return profile

            raise ProfilePrivacyValidationError(message="Access denied to private profile")

        return profile

    return check_profile_access


async def get_users_with_role(
    role: UserRole, user_service: UserServiceDep, limit: int = 50, offset: int = 0
) -> list[User]:
    """
    Получить пользователей с определенной ролью.

    :param role: Роль пользователей
    :param user_service: Сервис пользователей
    :param limit: Лимит результатов
    :param offset: Смещение
    :return: Список пользователей
    """
    users = await user_service.search_users(role=role, limit=limit, offset=offset)
    return users


async def get_users_with_status(
    status_filter: UserStatus, user_service: UserServiceDep, limit: int = 50, offset: int = 0
) -> list[User]:
    """
    Получить пользователей с определенным статусом.

    :param status_filter: Статус пользователей
    :param user_service: Сервис пользователей
    :param limit: Лимит результатов
    :param offset: Смещение
    :return: Список пользователей
    """
    users = await user_service.search_users(status=status_filter, limit=limit, offset=offset)
    return users


def require_user_status(required_status: UserStatus):
    """
    Dependency factory для проверки статуса пользователя.

    :param required_status: Требуемый статус
    :return: Dependency function
    """

    async def check_status(
        current_user: Annotated[User, Depends("apps.auth.depends.base.get_current_active_user")],
    ) -> User:
        """
        Проверить статус пользователя.

        :param current_user: Текущий пользователь
        :return: Пользователь с требуемым статусом
        :raises HTTPException: Если статус не соответствует
        """
        if current_user.status != required_status:
            raise UserStatusValidationError(message=f"User status {required_status.value} required")

        return current_user

    return check_status


def require_verified_user():
    """
    Dependency для проверки верификации пользователя.

    :return: Dependency function
    """

    async def check_verified(
        current_user: Annotated[User, Depends("apps.auth.depends.base.get_current_active_user")],
    ) -> User:
        """
        Проверить верификацию пользователя.

        :param current_user: Текущий пользователь
        :return: Верифицированный пользователь
        :raises HTTPException: Если пользователь не верифицирован
        """
        if not current_user.is_verified:
            raise UserVerificationValidationError(message="Email verification required")

        return current_user

    return check_verified


# Готовые dependencies
UserFromPath = Depends(get_user_by_id)
ProfileFromPath = Depends(get_profile_by_user_id)
UserWithAccess = Depends(verify_user_access())
PublicProfile = Depends(verify_profile_access())
RequireVerified = Depends(require_verified_user())
RequireActiveStatus = Depends(require_user_status(UserStatus.ACTIVE))

# Type aliases для использования в роутах
UserFromPathDep = Annotated[User, UserFromPath]
ProfileFromPathDep = Annotated[UserProfile, ProfileFromPath]
UserWithAccessDep = Annotated[User, UserWithAccess]
PublicProfileDep = Annotated[UserProfile, PublicProfile]
RequireVerifiedDep = Annotated[User, RequireVerified]
RequireActiveStatusDep = Annotated[User, RequireActiveStatus]
