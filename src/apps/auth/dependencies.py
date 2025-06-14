"""
Зависимости FastAPI для аутентификации.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from opentelemetry import trace
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.models import User
from core.database import get_db

from .auth_service import auth_service
from .jwt_service import JWTService

tracer = trace.get_tracer(__name__)

# Схема безопасности для Bearer токенов
security = HTTPBearer()


def get_jwt_service() -> JWTService:
    """Получить экземпляр JWT сервиса.

    Эта зависимость позволяет легко подменять JWT сервис в тестах.

    Returns:
        Экземпляр JWT сервиса
    """
    from .jwt_service import jwt_service

    return jwt_service


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> User:
    """Получить текущего пользователя из JWT токена.

    Args:
        credentials: HTTP авторизационные данные
        db: Сессия базы данных
        jwt_service: JWT сервис

    Returns:
        Текущий пользователь

    Raises:
        HTTPException: Если токен невалидный или пользователь не найден
    """
    with tracer.start_as_current_span("auth_dependencies.get_current_user") as span:
        span.set_attribute("token.provided", credentials is not None)

        if not credentials:
            span.set_attribute("error", "No credentials provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Не предоставлены учетные данные",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Используем переданный JWT сервис вместо глобального
        claims = jwt_service.verify_token(credentials.credentials, "access")
        if not claims:
            span.set_attribute("error", "Invalid token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный токен или пользователь не найден",
                headers={"WWW-Authenticate": "Bearer"},
            )

        import uuid

        user = await auth_service.user_repository.get(db, id=uuid.UUID(claims.sub))
        if not user or not user.is_active:
            span.set_attribute("error", "User not found or inactive")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Невалидный токен или пользователь не найден",
                headers={"WWW-Authenticate": "Bearer"},
            )

        span.set_attribute("user.id", str(user.id))
        span.set_attribute("user.email", user.email)
        span.set_attribute("user.is_active", user.is_active)

        return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Получить текущего активного пользователя.

    Args:
        current_user: Текущий пользователь

    Returns:
        Текущий активный пользователь

    Raises:
        HTTPException: Если пользователь неактивен
    """
    with tracer.start_as_current_span("auth_dependencies.get_current_active_user") as span:
        span.set_attribute("user.id", str(current_user.id))
        span.set_attribute("user.is_active", current_user.is_active)

        if not current_user.is_active:
            span.set_attribute("error", "User inactive")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь неактивен")

        return current_user


async def get_current_verified_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Получить текущего верифицированного пользователя.

    Args:
        current_user: Текущий активный пользователь

    Returns:
        Текущий верифицированный пользователь

    Raises:
        HTTPException: Если пользователь не верифицирован
    """
    with tracer.start_as_current_span("auth_dependencies.get_current_verified_user") as span:
        span.set_attribute("user.id", str(current_user.id))
        span.set_attribute("user.is_verified", current_user.is_verified)

        if not current_user.is_verified:
            span.set_attribute("error", "User not verified")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь не верифицирован. Проверьте ваш email."
            )

        return current_user


async def get_current_superuser(current_user: User = Depends(get_current_active_user)) -> User:
    """Получить текущего суперпользователя.

    Args:
        current_user: Текущий активный пользователь

    Returns:
        Текущий суперпользователь

    Raises:
        HTTPException: Если пользователь не является суперпользователем
    """
    with tracer.start_as_current_span("auth_dependencies.get_current_superuser") as span:
        span.set_attribute("user.id", str(current_user.id))
        span.set_attribute("user.is_superuser", current_user.is_superuser)

        if not current_user.is_superuser:
            span.set_attribute("error", "User not superuser")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав доступа")

        return current_user


async def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> User | None:
    """Получить текущего пользователя (опционально).

    Эта зависимость не вызывает исключение если токен не предоставлен или невалидный.
    Используется для эндпоинтов, где аутентификация опциональна.

            Args:
            credentials: HTTP авторизационные данные (опционально)
            db: Сессия базы данных
            jwt_service: JWT сервис

        Returns:
            Текущий пользователь или None
    """
    with tracer.start_as_current_span("auth_dependencies.get_optional_current_user") as span:
        span.set_attribute("token.provided", credentials is not None)

        if not credentials:
            span.set_attribute("result", "no_credentials")
            return None

        try:
            claims = jwt_service.verify_token(credentials.credentials, "access")
            if not claims:
                span.set_attribute("result", "invalid_token")
                return None

            import uuid

            user = await auth_service.user_repository.get(db, id=uuid.UUID(claims.sub))

            if user and user.is_active:
                span.set_attribute("user.id", str(user.id))
                span.set_attribute("user.email", user.email)
                span.set_attribute("result", "user_found")
                return user
            else:
                span.set_attribute("result", "user_not_found_or_inactive")
                return None

        except Exception as e:
            span.set_attribute("error", str(e))
            span.set_attribute("result", "exception")
            return None
