"""
API роуты для пользователей.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.dependencies import get_current_superuser, get_current_user
from apps.users.models import User
from core.database import get_db

from .schemas import UserPasswordChange, UserResponse, UserUpdate
from .service import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Получить свой профиль.

    Args:
        current_user: Текущий пользователь

    Returns:
        Данные текущего пользователя
    """
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_my_profile(
    user_data: UserUpdate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Обновить свой профиль.

    Args:
        user_data: Данные для обновления
        db: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        Обновленные данные пользователя
    """
    return await user_service.update_user(
        db, user_id=current_user.id, user_data=user_data, current_user_id=current_user.id
    )


@router.post("/me/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    password_data: UserPasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Изменить свой пароль.

    Args:
        password_data: Данные для смены пароля
        db: Сессия базы данных
        current_user: Текущий пользователь
    """
    await user_service.change_password(db, user_id=current_user.id, password_data=password_data)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: uuid.UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Получить пользователя по ID.

    Args:
        user_id: ID пользователя
        db: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        Данные пользователя
    """
    user = await user_service.get_user_by_id(db, user_id=user_id)
    if not user:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    return user


@router.get("/", response_model=list[UserResponse])
async def get_users(
    skip: int = Query(default=0, ge=0, description="Количество записей для пропуска"),
    limit: int = Query(default=100, ge=1, le=1000, description="Максимальное количество записей"),
    active_only: bool = Query(default=True, description="Только активные пользователи"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserResponse]:
    """Получить список пользователей.

    Args:
        skip: Количество записей для пропуска
        limit: Максимальное количество записей
        active_only: Только активные пользователи
        db: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        Список пользователей
    """
    return await user_service.get_users(db, skip=skip, limit=limit, active_only=active_only)


@router.get("/search/", response_model=list[UserResponse])
async def search_users(
    q: str = Query(..., min_length=2, description="Поисковый запрос"),
    skip: int = Query(default=0, ge=0, description="Количество записей для пропуска"),
    limit: int = Query(default=100, ge=1, le=1000, description="Максимальное количество записей"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserResponse]:
    """Поиск пользователей.

    Args:
        q: Поисковый запрос
        skip: Количество записей для пропуска
        limit: Максимальное количество записей
        db: Сессия базы данных
        current_user: Текущий пользователь

    Returns:
        Список найденных пользователей
    """
    return await user_service.search_users(db, query=q, skip=skip, limit=limit)


# Админские роуты
@router.put("/{user_id}", response_model=UserResponse)
async def admin_update_user(
    user_id: uuid.UUID,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_superuser),
) -> UserResponse:
    """Админ: обновить пользователя.

    Args:
        user_id: ID пользователя
        user_data: Данные для обновления
        db: Сессия базы данных
        admin: Админ пользователь

    Returns:
        Обновленные данные пользователя
    """
    return await user_service.update_user(db, user_id=user_id, user_data=user_data, current_user_id=admin.id)


@router.post("/{user_id}/deactivate", response_model=UserResponse)
async def admin_deactivate_user(
    user_id: uuid.UUID, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_superuser)
) -> UserResponse:
    """Админ: деактивировать пользователя.

    Args:
        user_id: ID пользователя
        db: Сессия базы данных
        admin: Админ пользователь

    Returns:
        Обновленные данные пользователя
    """
    return await user_service.deactivate_user(db, user_id=user_id, current_user_id=admin.id)


@router.delete("/{user_id}")
async def admin_delete_user(
    user_id: uuid.UUID,
    hard_delete: bool = Query(default=False, description="Полное удаление из БД"),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_superuser),
):
    """Админ: удалить пользователя.

    Args:
        user_id: ID пользователя
        hard_delete: Полное удаление из БД
        db: Сессия базы данных
        admin: Админ пользователь
    """
    await user_service.delete_user(db, user_id=user_id, current_user_id=admin.id, soft_delete=not hard_delete)
