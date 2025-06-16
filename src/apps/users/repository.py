"""
Репозиторий пользователей.
"""

from __future__ import annotations

from opentelemetry import trace
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.base import BaseRepository
from .models import User
from .schemas import UserCreate, UserUpdate

tracer = trace.get_tracer(__name__)


class UserRepository(BaseRepository[User, UserCreate, UserUpdate]):
    """Репозиторий для работы с пользователями."""

    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, *, email: str, include_deleted: bool = False) -> User | None:
        """Получить пользователя по email.

        Args:
            db: Сессия базы данных
            email: Email пользователя
            include_deleted: Включать мягко удаленные записи

        Returns:
            Пользователь или None
        """
        with tracer.start_as_current_span("user_repository.get_by_email") as span:
            span.set_attribute("user.email", email)
            span.set_attribute("include_deleted", include_deleted)

            query = select(User).where(User.email == email.lower())

            if not include_deleted:
                query = query.where(User.deleted_at.is_(None))

            result = await db.execute(query)
            user = result.scalar_one_or_none()

            span.set_attribute("user.found", user is not None)
            if user:
                span.set_attribute("user.id", str(user.id))
                span.set_attribute("user.is_active", user.is_active)

            return user

    async def get_by_username(self, db: AsyncSession, *, username: str, include_deleted: bool = False) -> User | None:
        """Получить пользователя по имени пользователя.

        Args:
            db: Сессия базы данных
            username: Имя пользователя
            include_deleted: Включать мягко удаленные записи

        Returns:
            Пользователь или None
        """
        with tracer.start_as_current_span("user_repository.get_by_username") as span:
            span.set_attribute("user.username", username)
            span.set_attribute("include_deleted", include_deleted)

            query = select(User).where(User.username == username.lower())

            if not include_deleted:
                query = query.where(User.deleted_at.is_(None))

            result = await db.execute(query)
            user = result.scalar_one_or_none()

            span.set_attribute("user.found", user is not None)
            if user:
                span.set_attribute("user.id", str(user.id))
                span.set_attribute("user.email", user.email)

            return user

    async def get_active_users(self, db: AsyncSession, *, skip: int = 0, limit: int = 100) -> list[User]:
        """Получить список активных пользователей.

        Args:
            db: Сессия базы данных
            skip: Количество записей для пропуска
            limit: Максимальное количество записей

        Returns:
            Список активных пользователей
        """
        with tracer.start_as_current_span("user_repository.get_active_users") as span:
            span.set_attribute("skip", skip)
            span.set_attribute("limit", limit)

            query = (
                select(User)
                .where(User.is_active == True)
                .where(User.deleted_at.is_(None))
                .order_by(User.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            result = await db.execute(query)
            users = result.scalars().all()

            span.set_attribute("users.count", len(users))
            return list(users)

    async def get_superusers(self, db: AsyncSession, *, skip: int = 0, limit: int = 100) -> list[User]:
        """Получить список суперпользователей.

        Args:
            db: Сессия базы данных
            skip: Количество записей для пропуска
            limit: Максимальное количество записей

        Returns:
            Список суперпользователей
        """
        with tracer.start_as_current_span("user_repository.get_superusers") as span:
            span.set_attribute("skip", skip)
            span.set_attribute("limit", limit)

            query = (
                select(User)
                .where(User.is_superuser == True)
                .where(User.deleted_at.is_(None))
                .order_by(User.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            result = await db.execute(query)
            users = result.scalars().all()

            span.set_attribute("superusers.count", len(users))
            return list(users)

    async def search_users(self, db: AsyncSession, *, query_text: str, skip: int = 0, limit: int = 100) -> list[User]:
        """Поиск пользователей по тексту.

        Args:
            db: Сессия базы данных
            query_text: Текст для поиска
            skip: Количество записей для пропуска
            limit: Максимальное количество записей

        Returns:
            Список найденных пользователей
        """
        with tracer.start_as_current_span("user_repository.search_users") as span:
            span.set_attribute("query_text", query_text)
            span.set_attribute("skip", skip)
            span.set_attribute("limit", limit)

            search_pattern = f"%{query_text.lower()}%"

            query = (
                select(User)
                .where(
                    (User.email.ilike(search_pattern))
                    | (User.username.ilike(search_pattern))
                    | (User.full_name.ilike(search_pattern))
                )
                .where(User.deleted_at.is_(None))
                .order_by(User.created_at.desc())
                .offset(skip)
                .limit(limit)
            )

            result = await db.execute(query)
            users = result.scalars().all()

            span.set_attribute("users.found", len(users))
            return list(users)

    async def is_email_taken(self, db: AsyncSession, *, email: str, exclude_user_id: str | None = None) -> bool:
        """Проверить, занят ли email.

        Args:
            db: Сессия базы данных
            email: Email для проверки
            exclude_user_id: ID пользователя для исключения из проверки

        Returns:
            True если email занят, False если свободен
        """
        with tracer.start_as_current_span("user_repository.is_email_taken") as span:
            span.set_attribute("email", email)
            span.set_attribute("exclude_user_id", exclude_user_id)

            query = select(User).where(User.email == email.lower())

            if exclude_user_id:
                query = query.where(User.id != exclude_user_id)

            result = await db.execute(query)
            user = result.scalar_one_or_none()

            is_taken = user is not None
            span.set_attribute("email.is_taken", is_taken)

            return is_taken

    async def is_username_taken(self, db: AsyncSession, *, username: str, exclude_user_id: str | None = None) -> bool:
        """Проверить, занято ли имя пользователя.

        Args:
            db: Сессия базы данных
            username: Имя пользователя для проверки
            exclude_user_id: ID пользователя для исключения из проверки

        Returns:
            True если имя занято, False если свободно
        """
        with tracer.start_as_current_span("user_repository.is_username_taken") as span:
            span.set_attribute("username", username)
            span.set_attribute("exclude_user_id", exclude_user_id)

            query = select(User).where(User.username == username.lower())

            if exclude_user_id:
                query = query.where(User.id != exclude_user_id)

            result = await db.execute(query)
            user = result.scalar_one_or_none()

            is_taken = user is not None
            span.set_attribute("username.is_taken", is_taken)

            return is_taken
