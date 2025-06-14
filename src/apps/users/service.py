"""
Сервис пользователей.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from opentelemetry import trace
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.password_service import password_service
from .repository import UserRepository
from .schemas import UserPasswordChange, UserResponse, UserUpdate

tracer = trace.get_tracer(__name__)


class UserService:
    """Сервис для работы с пользователями."""

    def __init__(self):
        self.repository = UserRepository()

    async def get_user_by_id(self, db: AsyncSession, *, user_id: uuid.UUID) -> UserResponse | None:
        """Получить пользователя по ID.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя

        Returns:
            Данные пользователя или None
        """
        with tracer.start_as_current_span("user_service.get_user_by_id") as span:
            span.set_attribute("user.id", str(user_id))

            user = await self.repository.get(db, id=user_id)
            if not user:
                span.set_attribute("result", "not_found")
                return None

            span.set_attribute("result", "found")
            return UserResponse.model_validate(user)

    async def get_user_by_email(self, db: AsyncSession, *, email: str) -> UserResponse | None:
        """Получить пользователя по email.

        Args:
            db: Сессия базы данных
            email: Email пользователя

        Returns:
            Данные пользователя или None
        """
        with tracer.start_as_current_span("user_service.get_user_by_email") as span:
            span.set_attribute("user.email", email)

            user = await self.repository.get_by_email(db, email=email)
            if not user:
                span.set_attribute("result", "not_found")
                return None

            span.set_attribute("result", "found")
            span.set_attribute("user.id", str(user.id))
            return UserResponse.model_validate(user)

    async def get_user_by_username(self, db: AsyncSession, *, username: str) -> UserResponse | None:
        """Получить пользователя по имени пользователя.

        Args:
            db: Сессия базы данных
            username: Имя пользователя

        Returns:
            Данные пользователя или None
        """
        with tracer.start_as_current_span("user_service.get_user_by_username") as span:
            span.set_attribute("user.username", username)

            user = await self.repository.get_by_username(db, username=username)
            if not user:
                span.set_attribute("result", "not_found")
                return None

            span.set_attribute("result", "found")
            span.set_attribute("user.id", str(user.id))
            return UserResponse.model_validate(user)

    async def get_users(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100, active_only: bool = True
    ) -> list[UserResponse]:
        """Получить список пользователей.

        Args:
            db: Сессия базы данных
            skip: Количество записей для пропуска
            limit: Максимальное количество записей
            active_only: Только активные пользователи

        Returns:
            Список пользователей
        """
        with tracer.start_as_current_span("user_service.get_users") as span:
            span.set_attribute("skip", skip)
            span.set_attribute("limit", limit)
            span.set_attribute("active_only", active_only)

            if active_only:
                users = await self.repository.get_active_users(db, skip=skip, limit=limit)
            else:
                users = await self.repository.get_multi(db, skip=skip, limit=limit)

            span.set_attribute("users.count", len(users))
            return [UserResponse.model_validate(user) for user in users]

    async def search_users(
        self, db: AsyncSession, *, query: str, skip: int = 0, limit: int = 100
    ) -> list[UserResponse]:
        """Поиск пользователей.

        Args:
            db: Сессия базы данных
            query: Поисковый запрос
            skip: Количество записей для пропуска
            limit: Максимальное количество записей

        Returns:
            Список найденных пользователей
        """
        with tracer.start_as_current_span("user_service.search_users") as span:
            span.set_attribute("query", query)
            span.set_attribute("skip", skip)
            span.set_attribute("limit", limit)

            users = await self.repository.search_users(db, query_text=query, skip=skip, limit=limit)

            span.set_attribute("users.found", len(users))
            return [UserResponse.model_validate(user) for user in users]

    async def update_user(
        self, db: AsyncSession, *, user_id: uuid.UUID, user_data: UserUpdate, current_user_id: uuid.UUID | None = None
    ) -> UserResponse:
        """Обновить пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            user_data: Данные для обновления
            current_user_id: ID текущего пользователя (для проверок)

        Returns:
            Обновленные данные пользователя

        Raises:
            HTTPException: Если пользователь не найден или нет прав
        """
        with tracer.start_as_current_span("user_service.update_user") as span:
            span.set_attribute("user.id", str(user_id))
            span.set_attribute("current_user.id", str(current_user_id) if current_user_id else "none")

            user = await self.repository.get(db, id=user_id)
            if not user:
                span.set_attribute("error", "User not found")
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

            # Проверяем права на редактирование
            if current_user_id and current_user_id != user_id:
                current_user = await self.repository.get(db, id=current_user_id)
                if not current_user or not current_user.is_superuser:
                    span.set_attribute("error", "Permission denied")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Недостаточно прав для редактирования этого пользователя",
                    )

            # Проверяем уникальность email если он изменяется
            if user_data.email and user_data.email != user.email:
                if await self.repository.is_email_taken(db, email=user_data.email, exclude_user_id=str(user_id)):
                    span.set_attribute("error", "Email already taken")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь с таким email уже существует"
                    )

            # Проверяем уникальность username если он изменяется
            if user_data.username and user_data.username != user.username:
                if await self.repository.is_username_taken(
                    db, username=user_data.username, exclude_user_id=str(user_id)
                ):
                    span.set_attribute("error", "Username already taken")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь с таким именем уже существует"
                    )

            updated_user = await self.repository.update(db, db_obj=user, obj_in=user_data)
            await db.commit()

            span.set_attribute("update.success", True)
            return UserResponse.model_validate(updated_user)

    async def change_password(self, db: AsyncSession, *, user_id: uuid.UUID, password_data: UserPasswordChange) -> None:
        """Изменить пароль пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            password_data: Данные для смены пароля

        Raises:
            HTTPException: Если пользователь не найден или текущий пароль неверный
        """
        with tracer.start_as_current_span("user_service.change_password") as span:
            span.set_attribute("user.id", str(user_id))

            user = await self.repository.get(db, id=user_id)
            if not user:
                span.set_attribute("error", "User not found")
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

            # Проверяем текущий пароль
            if not password_service.verify_password(password_data.current_password, user.hashed_password):
                span.set_attribute("error", "Invalid current password")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный текущий пароль")

            # Проверяем силу нового пароля
            is_strong, errors = password_service.is_password_strong(password_data.new_password)
            if not is_strong:
                span.set_attribute("error", "Weak new password")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Слабый новый пароль: {', '.join(errors)}"
                )

            # Хешируем новый пароль
            new_hashed_password = password_service.hash_password(password_data.new_password)

            # Обновляем пароль
            await self.repository.update(db, db_obj=user, obj_in={"hashed_password": new_hashed_password})
            await db.commit()

            span.set_attribute("password_change.success", True)

    async def deactivate_user(
        self, db: AsyncSession, *, user_id: uuid.UUID, current_user_id: uuid.UUID
    ) -> UserResponse:
        """Деактивировать пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            current_user_id: ID текущего пользователя

        Returns:
            Обновленные данные пользователя

        Raises:
            HTTPException: Если нет прав или пользователь не найден
        """
        with tracer.start_as_current_span("user_service.deactivate_user") as span:
            span.set_attribute("user.id", str(user_id))
            span.set_attribute("current_user.id", str(current_user_id))

            # Проверяем права
            current_user = await self.repository.get(db, id=current_user_id)
            if not current_user or not current_user.is_superuser:
                span.set_attribute("error", "Permission denied")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для деактивации пользователей"
                )

            user = await self.repository.get(db, id=user_id)
            if not user:
                span.set_attribute("error", "User not found")
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

            # Нельзя деактивировать самого себя
            if user_id == current_user_id:
                span.set_attribute("error", "Cannot deactivate self")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя деактивировать самого себя")

            updated_user = await self.repository.update(db, db_obj=user, obj_in={"is_active": False})
            await db.commit()

            span.set_attribute("deactivate.success", True)
            return UserResponse.model_validate(updated_user)

    async def delete_user(
        self, db: AsyncSession, *, user_id: uuid.UUID, current_user_id: uuid.UUID, soft_delete: bool = True
    ) -> None:
        """Удалить пользователя.

        Args:
            db: Сессия базы данных
            user_id: ID пользователя
            current_user_id: ID текущего пользователя
            soft_delete: Использовать мягкое удаление

        Raises:
            HTTPException: Если нет прав или пользователь не найден
        """
        with tracer.start_as_current_span("user_service.delete_user") as span:
            span.set_attribute("user.id", str(user_id))
            span.set_attribute("current_user.id", str(current_user_id))
            span.set_attribute("soft_delete", soft_delete)

            # Проверяем права
            current_user = await self.repository.get(db, id=current_user_id)
            if not current_user or not current_user.is_superuser:
                span.set_attribute("error", "Permission denied")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав для удаления пользователей"
                )

            # Нельзя удалить самого себя
            if user_id == current_user_id:
                span.set_attribute("error", "Cannot delete self")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя удалить самого себя")

            deleted_user = await self.repository.remove(db, id=user_id, soft_delete=soft_delete)

            if not deleted_user:
                span.set_attribute("error", "User not found")
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

            await db.commit()
            span.set_attribute("delete.success", True)


# Синглтон сервиса
user_service = UserService()
