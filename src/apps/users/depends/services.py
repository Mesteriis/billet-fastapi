"""
Dependencies для сервисов пользователей.
"""

from typing import Annotated

from fastapi import Depends

from apps.users.depends.repositories import ProfileRepoDep, UserRepoDep
from apps.users.services.profile_service import ProfileService
from apps.users.services.user_service import UserService


async def get_user_service(
    user_repo: UserRepoDep,
    profile_repo: ProfileRepoDep,
) -> UserService:
    """
    Получить сервис пользователей.

    :param user_repo: Репозиторий пользователей
    :param profile_repo: Репозиторий профилей
    :return: Экземпляр UserService
    """
    return UserService(user_repo, profile_repo)


async def get_profile_service(
    profile_repo: ProfileRepoDep,
) -> ProfileService:
    """
    Получить сервис профилей.

    :param profile_repo: Репозиторий профилей
    :return: Экземпляр ProfileService
    """
    return ProfileService(profile_repo)


# Type aliases для использования в роутах
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]
