"""
Dependencies для сервисов авторизации.
"""

from typing import Annotated

from fastapi import Depends

from apps.auth.depends.repositories import OrbitalTokenRepoDep, RefreshTokenRepoDep, UserSessionRepoDep
from apps.auth.services.jwt_service import JWTService
from apps.auth.services.orbital_service import OrbitalService
from apps.auth.services.session_service import SessionService
from apps.users.depends.repositories import UserRepoDep


async def get_jwt_service(
    refresh_token_repo: RefreshTokenRepoDep,
    user_repo: UserRepoDep,
) -> JWTService:
    """
    Получить сервис JWT токенов.

    :param refresh_token_repo: Репозиторий refresh токенов
    :param user_repo: Репозиторий пользователей
    :return: Экземпляр JWTService
    """
    return JWTService(refresh_token_repo, user_repo)


async def get_orbital_service(
    orbital_token_repo: OrbitalTokenRepoDep,
    user_repo: UserRepoDep,
) -> OrbitalService:
    """
    Получить сервис одноразовых токенов.

    :param orbital_token_repo: Репозиторий orbital токенов
    :param user_repo: Репозиторий пользователей
    :return: Экземпляр OrbitalService
    """
    return OrbitalService(orbital_token_repo, user_repo)


async def get_session_service(
    session_repo: UserSessionRepoDep,
    user_repo: UserRepoDep,
) -> SessionService:
    """
    Получить сервис веб-сессий.

    :param session_repo: Репозиторий пользовательских сессий
    :param user_repo: Репозиторий пользователей
    :return: Экземпляр SessionService
    """
    return SessionService(session_repo, user_repo)


# Type aliases для использования в роутах
JWTServiceDep = Annotated[JWTService, Depends(get_jwt_service)]
OrbitalServiceDep = Annotated[OrbitalService, Depends(get_orbital_service)]
SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
