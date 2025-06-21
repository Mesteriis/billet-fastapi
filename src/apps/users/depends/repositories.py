"""
Dependencies для репозиториев пользователей.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.repo import ProfileRepository, UserRepository
from core.database import get_db

# Type alias
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_user_repo(db: DbSession) -> UserRepository:
    """
    Получить репозиторий пользователей.

    :param db: Сессия базы данных
    :return: Экземпляр UserRepository
    """
    return UserRepository(db)


async def get_profile_repo(db: DbSession) -> ProfileRepository:
    """
    Получить репозиторий профилей.

    :param db: Сессия базы данных
    :return: Экземпляр ProfileRepository
    """
    return ProfileRepository(db)


# Type aliases для использования в зависимостях
UserRepoDep = Annotated[UserRepository, Depends(get_user_repo)]
ProfileRepoDep = Annotated[ProfileRepository, Depends(get_profile_repo)]
