"""
API роуты для аутентификации.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.models import User
from apps.users.schemas import UserCreate, UserLogin
from core.database import get_db

from .auth_service import auth_service
from .dependencies import get_current_user, get_optional_current_user
from .schemas import LoginResponse, LogoutRequest, RefreshTokenRequest, TokenPair, TokenValidationResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, request: Request, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    """Регистрация нового пользователя.

    Args:
        user_data: Данные для регистрации
        request: HTTP запрос
        db: Сессия базы данных

    Returns:
        Данные пользователя и токены
    """
    # Получаем метаданные запроса
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    # Регистрируем пользователя
    user = await auth_service.register_user(db, user_data=user_data, auto_verify=True)

    # Автоматически входим в систему после регистрации
    login_response = await auth_service.login(
        db, email=user_data.email, password=user_data.password, user_agent=user_agent, ip_address=ip_address
    )

    return login_response


@router.post("/login", response_model=LoginResponse)
async def login(credentials: UserLogin, request: Request, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    """Вход в систему.

    Args:
        credentials: Учетные данные
        request: HTTP запрос
        db: Сессия базы данных

    Returns:
        Данные пользователя и токены
    """
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    return await auth_service.login(
        db, email=credentials.email, password=credentials.password, user_agent=user_agent, ip_address=ip_address
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(
    refresh_data: RefreshTokenRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenPair:
    """Обновление access токена.

    Args:
        refresh_data: Refresh токен
        request: HTTP запрос
        db: Сессия базы данных

    Returns:
        Новая пара токенов
    """
    user_agent = request.headers.get("user-agent")
    ip_address = request.client.host if request.client else None

    return await auth_service.refresh_token(
        db, refresh_token=refresh_data.refresh_token, user_agent=user_agent, ip_address=ip_address
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    logout_data: LogoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    """Выход из системы.

    Args:
        logout_data: Данные для выхода
        db: Сессия базы данных
        current_user: Текущий пользователь (опционально)
    """
    user_id = current_user.id if current_user else None

    await auth_service.logout(
        db, refresh_token=logout_data.refresh_token, user_id=user_id, revoke_all=logout_data.revoke_all
    )


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Выход из всех устройств.

    Args:
        db: Сессия базы данных
        current_user: Текущий пользователь
    """
    await auth_service.logout(db, user_id=current_user.id, revoke_all=True)


@router.get("/validate", response_model=TokenValidationResponse)
async def validate_token(current_user: User | None = Depends(get_optional_current_user)) -> TokenValidationResponse:
    """Проверка валидности токена.

    Args:
        current_user: Текущий пользователь (опционально)

    Returns:
        Результат валидации
    """
    if current_user:
        return TokenValidationResponse(
            valid=True,
            user_id=str(current_user.id),
            email=current_user.email,
            username=current_user.username,
            token_type="access",
        )
    else:
        return TokenValidationResponse(valid=False, error="Invalid or missing token")


@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)) -> dict:
    """Получить информацию о текущем пользователе.

    Args:
        current_user: Текущий пользователь

    Returns:
        Краткая информация о пользователе
    """
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "is_superuser": current_user.is_superuser,
        "created_at": current_user.created_at,
        "last_login_at": current_user.last_login_at,
    }
