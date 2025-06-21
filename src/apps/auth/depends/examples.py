"""
Примеры использования dependencies.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from apps.auth.depends import JWTServiceDep, RequireAdmin, get_current_user
from apps.users.depends import UserFromPath, UserServiceDep
from apps.users.models.user_models import User

router = APIRouter()


@router.get("/me")
async def get_current_user_info(current_user: Annotated[User, Depends(get_current_user)]):
    """Получить информацию о текущем пользователе."""
    return current_user


@router.get("/users/{user_id}")
async def get_user_by_id(user: UserFromPath, current_user: Annotated[User, Depends(get_current_user)]):
    """Получить пользователя по ID."""
    return user


@router.delete("/users/{user_id}")
async def delete_user(user: UserFromPath, admin_user: RequireAdmin, user_service: UserServiceDep):
    """Удалить пользователя (только администраторы)."""
    await user_service.delete_user(user.id)
    return {"message": "User deleted successfully"}
