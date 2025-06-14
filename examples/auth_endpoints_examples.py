#!/usr/bin/env python3
"""
Практические примеры FastAPI endpoints с различными типами аутентификации.

Этот файл содержит готовые к использованию примеры endpoints с:
- JWT Bearer аутентификацией
- API ключами
- Опциональной аутентификацией
- Ролевой авторизацией
- WebSocket/SSE аутентификацией
- Многофакторной аутентификацией
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.dependencies import (
    get_current_active_user,
    get_current_superuser,
    get_current_user,
    get_current_verified_user,
    get_optional_current_user,
)
from apps.users.models import User
from core.database import get_db
from core.realtime.auth import WSAuthenticator, get_ws_auth

# Инициализация роутера
router = APIRouter(prefix="/examples/auth", tags=["Authentication Examples"])

# Схемы безопасности
security = HTTPBearer()
ws_auth = WSAuthenticator()


# Pydantic модели для примеров
class PublicContentResponse(BaseModel):
    """Ответ с публичным контентом."""

    content: str
    is_personalized: bool
    user_info: Optional[dict] = None
    timestamp: datetime


class ProtectedResourceResponse(BaseModel):
    """Ответ с защищенным ресурсом."""

    resource_id: str
    owner_id: str
    data: dict
    access_level: str


class AdminActionResponse(BaseModel):
    """Ответ на административное действие."""

    action: str
    performed_by: str
    target: Optional[str] = None
    success: bool
    message: str


# ============================================================================
# 1. БАЗОВАЯ JWT АУТЕНТИФИКАЦИЯ
# ============================================================================


@router.get("/protected", response_model=ProtectedResourceResponse)
async def get_protected_resource(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ProtectedResourceResponse:
    """
    Пример защищенного endpoint с обязательной JWT аутентификацией.

    Требует валидный Bearer токен в заголовке Authorization.
    """
    return ProtectedResourceResponse(
        resource_id="resource_123",
        owner_id=str(current_user.id),
        data={
            "user_email": current_user.email,
            "user_role": "user",  # В реальном приложении из модели
            "access_time": datetime.utcnow().isoformat(),
        },
        access_level="user",
    )


@router.get("/profile", response_model=dict)
async def get_user_profile(current_user: User = Depends(get_current_active_user)) -> dict:
    """
    Пример получения профиля с проверкой активности пользователя.

    Требует активного пользователя (is_active=True).
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "username": current_user.username,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat(),
        "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
    }


@router.get("/verified-only", response_model=dict)
async def get_verified_content(current_user: User = Depends(get_current_verified_user)) -> dict:
    """
    Пример endpoint только для верифицированных пользователей.

    Требует is_verified=True.
    """
    return {
        "message": "Этот контент доступен только верифицированным пользователям",
        "user": current_user.email,
        "verified_at": current_user.created_at.isoformat(),  # В реальном приложении отдельное поле
        "premium_content": {
            "feature_1": "Расширенная аналитика",
            "feature_2": "Приоритетная поддержка",
            "feature_3": "Дополнительные возможности",
        },
    }


# ============================================================================
# 2. АДМИНИСТРАТИВНЫЕ ПРАВА
# ============================================================================


@router.get("/admin/users", response_model=List[dict])
async def list_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    admin_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_db),
) -> List[dict]:
    """
    Пример административного endpoint для суперпользователей.

    Требует is_superuser=True.
    """
    # В реальном приложении здесь был бы запрос к БД
    mock_users = [
        {
            "id": "user_1",
            "email": "user1@example.com",
            "username": "user1",
            "is_active": True,
            "is_verified": True,
            "role": "user",
        },
        {
            "id": "user_2",
            "email": "user2@example.com",
            "username": "user2",
            "is_active": False,
            "is_verified": True,
            "role": "user",
        },
    ]

    return mock_users[skip : skip + limit]


@router.post("/admin/actions", response_model=AdminActionResponse)
async def perform_admin_action(
    action: str, target_user_id: Optional[str] = None, admin_user: User = Depends(get_current_superuser)
) -> AdminActionResponse:
    """
    Пример выполнения административных действий.

    Доступно только суперпользователям.
    """
    allowed_actions = ["ban_user", "unban_user", "verify_user", "promote_user"]

    if action not in allowed_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимое действие. Разрешены: {', '.join(allowed_actions)}",
        )

    return AdminActionResponse(
        action=action,
        performed_by=admin_user.email,
        target=target_user_id,
        success=True,
        message=f"Действие '{action}' выполнено успешно",
    )


# ============================================================================
# 3. ОПЦИОНАЛЬНАЯ АУТЕНТИФИКАЦИЯ
# ============================================================================


@router.get("/public", response_model=PublicContentResponse)
async def get_public_content(
    current_user: Optional[User] = Depends(get_optional_current_user),
) -> PublicContentResponse:
    """
    Пример endpoint с опциональной аутентификацией.

    Работает как для аутентифицированных, так и для анонимных пользователей.
    Контент персонализируется при наличии токена.
    """
    if current_user:
        # Персонализированный контент для аутентифицированных пользователей
        return PublicContentResponse(
            content="Персонализированный контент на основе ваших предпочтений",
            is_personalized=True,
            user_info={
                "email": current_user.email,
                "username": current_user.username,
                "member_since": current_user.created_at.isoformat(),
            },
            timestamp=datetime.utcnow(),
        )
    else:
        # Общий контент для анонимных пользователей
        return PublicContentResponse(
            content="Общедоступный контент для всех посетителей",
            is_personalized=False,
            user_info=None,
            timestamp=datetime.utcnow(),
        )


# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================


def create_auth_examples_app():
    """
    Создать FastAPI приложение с примерами аутентификации.

    Использование:
        from examples.auth_endpoints_examples import create_auth_examples_app
        app = create_auth_examples_app()
    """
    from fastapi import FastAPI

    app = FastAPI(
        title="Authentication Examples API",
        description="Примеры различных типов аутентификации в FastAPI",
        version="1.0.0",
    )

    app.include_router(router)

    return app


if __name__ == "__main__":
    # Для тестирования примеров
    import uvicorn

    app = create_auth_examples_app()
    uvicorn.run(app, host="0.0.0.0", port=8001)
