"""
Dependencies для репозиториев авторизации.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.repo import OrbitalTokenRepository, RefreshTokenRepository, UserSessionRepository
from core.database import get_db

# Type alias
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_refresh_token_repo(db: DbSession) -> RefreshTokenRepository:
    """
    Получить репозиторий refresh токенов.

    :param db: Сессия базы данных
    :return: Экземпляр RefreshTokenRepository
    """
    return RefreshTokenRepository(db)


async def get_user_session_repo(db: DbSession) -> UserSessionRepository:
    """
    Получить репозиторий пользовательских сессий.

    :param db: Сессия базы данных
    :return: Экземпляр UserSessionRepository
    """
    return UserSessionRepository(db)


async def get_orbital_token_repo(db: DbSession) -> OrbitalTokenRepository:
    """
    Получить репозиторий orbital токенов.

    :param db: Сессия базы данных
    :return: Экземпляр OrbitalTokenRepository
    """
    return OrbitalTokenRepository(db)


# Type aliases для использования в зависимостях
RefreshTokenRepoDep = Annotated[RefreshTokenRepository, Depends(get_refresh_token_repo)]
UserSessionRepoDep = Annotated[UserSessionRepository, Depends(get_user_session_repo)]
OrbitalTokenRepoDep = Annotated[OrbitalTokenRepository, Depends(get_orbital_token_repo)]
