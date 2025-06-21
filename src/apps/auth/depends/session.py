"""
Dependencies для работы с сессиями и cookies.
"""

from typing import Annotated

from fastapi import Cookie, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.exceptions import (
    AuthCSRFValidationError,
    AuthSessionValidationError,
    AuthUserInactiveError,
    AuthUserNotFoundError,
)
from apps.auth.models.auth_models import UserSession
from apps.auth.services.session_service import SessionService
from apps.users.models.user_models import User
from core.database import get_db

# Type alias
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_session_service(db: DbSession) -> SessionService:
    """
    Получить сервис сессий.

    :param db: Сессия базы данных
    :return: Экземпляр SessionService
    """
    return SessionService(db)


async def get_session_id_from_cookie(
    session_id: Annotated[str | None, Cookie(alias="session_id")] = None,
) -> str | None:
    """
    Получить ID сессии из cookie.

    :param session_id: Session ID из cookie
    :return: Session ID или None
    """
    return session_id


async def get_current_session(
    session_id: Annotated[str | None, Depends(get_session_id_from_cookie)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
    request: Request,
) -> UserSession | None:
    """
    Получить текущую сессию пользователя.

    :param session_id: ID сессии из cookie
    :param session_service: Сервис сессий
    :param request: HTTP запрос
    :return: Объект UserSession или None
    """
    if not session_id:
        return None

    # Получаем IP адрес и User-Agent для валидации
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    session = await session_service.validate_session(
        session_id=session_id, ip_address=ip_address, user_agent=user_agent, auto_extend=True
    )

    return session


async def get_required_session(session: Annotated[UserSession | None, Depends(get_current_session)]) -> UserSession:
    """
    Получить обязательную сессию (с ошибкой если отсутствует).

    :param session: Текущая сессия
    :return: Объект UserSession
    :raises HTTPException: Если сессия не найдена
    """
    if not session:
        raise AuthSessionValidationError(message="Valid session required")

    return session


async def get_user_from_session(session: Annotated[UserSession, Depends(get_required_session)]) -> User:
    """
    Получить пользователя из сессии.

    :param session: Текущая сессия
    :return: Пользователь
    :raises HTTPException: Если пользователь не найден
    """
    if not session.user:
        raise AuthUserNotFoundError(message="User not found in session")

    user = session.user

    # Проверяем возможность входа
    if not user.can_login:
        raise AuthUserInactiveError(message="User account is inactive or suspended")

    return user


async def get_csrf_token_from_header(
    csrf_token: Annotated[str | None, Depends(lambda request: request.headers.get("x-csrf-token"))] = None,
) -> str | None:
    """
    Получить CSRF токен из заголовка.

    :param csrf_token: CSRF токен из заголовка X-CSRF-Token
    :return: CSRF токен или None
    """
    return csrf_token


async def verify_csrf_token(
    session: Annotated[UserSession, Depends(get_required_session)],
    csrf_token: Annotated[str | None, Depends(get_csrf_token_from_header)],
    session_service: Annotated[SessionService, Depends(get_session_service)],
) -> bool:
    """
    Верифицировать CSRF токен.

    :param session: Текущая сессия
    :param csrf_token: CSRF токен из заголовка
    :param session_service: Сервис сессий
    :return: True если токен валиден
    :raises HTTPException: Если CSRF токен невалидный
    """
    if not csrf_token:
        raise AuthCSRFValidationError(message="CSRF token required")

    is_valid = await session_service.verify_csrf_token(session.session_id, csrf_token)
    if not is_valid:
        raise AuthCSRFValidationError(message="Invalid CSRF token")

    return True


async def get_optional_user_from_session(
    session: Annotated[UserSession | None, Depends(get_current_session)],
) -> User | None:
    """
    Получить пользователя из сессии опционально (без ошибки).

    :param session: Текущая сессия (может быть None)
    :return: Пользователь или None
    """
    if not session or not session.user:
        return None

    user = session.user

    # Проверяем возможность входа
    if not user.can_login:
        return None

    return user


# Type aliases для использования в роутах
CurrentSession = Annotated[UserSession | None, Depends(get_current_session)]
RequiredSession = Annotated[UserSession, Depends(get_required_session)]
SessionUser = Annotated[User, Depends(get_user_from_session)]
OptionalSessionUser = Annotated[User | None, Depends(get_optional_user_from_session)]
CSRFProtected = Annotated[bool, Depends(verify_csrf_token)]
