"""
Репозиторий пользователей.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from apps.users.models.enums import UserRole, UserStatus
from apps.users.models.user_models import User
from apps.users.schemas.user_schemas import UserCreate, UserUpdate
from core.base.repo.repository import BaseRepository


class UserRepository(BaseRepository[User, Any, Any]):
    """
    Репозиторий для работы с пользователями.

    Наследуется от BaseRepository и добавляет специфичные методы
    для работы с пользователями: поиск по email/username,
    статистика, управление ролями и статусами.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str, include_deleted: bool = False) -> User | None:
        """
        Получить пользователя по email.

        :param email: Email адрес
        :param include_deleted: Включать ли удаленных пользователей
        :return: Пользователь или None
        """
        filters = {"email__iexact": email}
        return await self.get_by(**filters, include_deleted=include_deleted)

    async def get_by_username(self, username: str, include_deleted: bool = False) -> User | None:
        """
        Получить пользователя по имени пользователя.

        :param username: Имя пользователя
        :param include_deleted: Включать ли удаленных пользователей
        :return: Пользователь или None
        """
        filters = {"username__iexact": username}
        return await self.get_by(**filters, include_deleted=include_deleted)

    async def get_by_email_or_username(self, identifier: str, include_deleted: bool = False) -> User | None:
        """
        Получить пользователя по email или username.

        :param identifier: Email или username
        :param include_deleted: Включать ли удаленных пользователей
        :return: Пользователь или None
        """
        # Сначала пробуем по email
        user = await self.get_by_email(identifier, include_deleted=include_deleted)
        if user:
            return user

        # Если не найден, пробуем по username
        return await self.get_by_username(identifier, include_deleted=include_deleted)

    async def email_exists(self, email: str, exclude_user_id: uuid.UUID | None = None) -> bool:
        """
        Проверить существование email.

        :param email: Email адрес
        :param exclude_user_id: ID пользователя для исключения из проверки
        :return: True если email существует
        """
        filters: dict[str, Any] = {"email__iexact": email}
        if exclude_user_id:
            filters["id__ne"] = str(exclude_user_id)

        return await self.exists(**filters)

    async def username_exists(self, username: str, exclude_user_id: uuid.UUID | None = None) -> bool:
        """
        Проверить существование username.

        :param username: Имя пользователя
        :param exclude_user_id: ID пользователя для исключения из проверки
        :return: True если username существует
        """
        filters: dict[str, Any] = {"username__iexact": username}
        if exclude_user_id:
            filters["id__ne"] = str(exclude_user_id)

        return await self.exists(**filters)

    async def get_with_profile(self, user_id: uuid.UUID) -> User | None:
        """
        Получить пользователя с профилем.

        :param user_id: ID пользователя
        :return: Пользователь с загруженным профилем или None
        """
        query = (
            select(User).options(joinedload(User.profile)).where(and_(User.id == user_id, User.deleted_at.is_(None)))
        )

        result = await self._db.execute(query)
        return result.scalar_one_or_none()

    async def get_with_tokens_and_sessions(self, user_id: uuid.UUID) -> User | None:
        """
        Получить пользователя с токенами и сессиями.

        :param user_id: ID пользователя
        :return: Пользователь с загруженными токенами и сессиями или None
        """
        query = (
            select(User)
            .options(selectinload(User.refresh_tokens), selectinload(User.sessions))
            .where(and_(User.id == user_id, User.deleted_at.is_(None)))
        )

        result = await self._db.execute(query)
        return result.scalar_one_or_none()

    async def list_by_role(
        self, role: UserRole, *, offset: int | None = None, limit: int | None = None, include_deleted: bool = False
    ) -> Sequence[User]:
        """
        Получить список пользователей по роли.

        :param role: Роль пользователя
        :param offset: Смещение
        :param limit: Лимит
        :param include_deleted: Включать ли удаленных пользователей
        :return: Список пользователей
        """
        return await self.list(role=role, offset=offset, limit=limit, include_deleted=include_deleted)

    async def list_by_status(
        self, status: UserStatus, *, offset: int | None = None, limit: int | None = None, include_deleted: bool = False
    ) -> Sequence[User]:
        """
        Получить список пользователей по статусу.

        :param status: Статус пользователя
        :param offset: Смещение
        :param limit: Лимит
        :param include_deleted: Включать ли удаленных пользователей
        :return: Список пользователей
        """
        return await self.list(status=status, offset=offset, limit=limit, include_deleted=include_deleted)

    async def search_users(
        self, query: str, *, offset: int | None = None, limit: int | None = None, include_deleted: bool = False
    ) -> Sequence[User]:
        """
        Поиск пользователей по запросу.

        :param query: Поисковый запрос
        :param offset: Смещение
        :param limit: Лимит
        :param include_deleted: Включать ли удаленных пользователей
        :return: Список пользователей
        """
        # Поиск по username, email, first_name, last_name
        search_filters = {
            "or_filters": [
                {"username__icontains": query},
                {"email__icontains": query},
                {"first_name__icontains": query},
                {"last_name__icontains": query},
            ]
        }

        return await self.list_with_complex_filters(
            search_filters, offset=offset, limit=limit, include_deleted=include_deleted
        )

    async def get_active_users_count(self) -> int:
        """
        Получить количество активных пользователей.

        :return: Количество активных пользователей
        """
        return await self.count(is_active=True, status=UserStatus.ACTIVE, include_deleted=False)

    async def get_verified_users_count(self) -> int:
        """
        Получить количество верифицированных пользователей.

        :return: Количество верифицированных пользователей
        """
        return await self.count(is_verified=True, include_deleted=False)

    async def get_new_users_count(self, days: int = 1) -> int:
        """
        Получить количество новых пользователей за период.

        :param days: Количество дней
        :return: Количество новых пользователей
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        return await self.count(created_at__gte=since_date, include_deleted=False)

    async def get_users_stats(self) -> dict[str, Any]:
        """
        Получить статистику пользователей.

        :return: Словарь со статистикой
        """
        stats: dict[str, Any] = {
            "total_users": await self.count(include_deleted=False),
            "active_users": await self.get_active_users_count(),
            "verified_users": await self.get_verified_users_count(),
            "new_users_today": await self.get_new_users_count(1),
            "new_users_week": await self.get_new_users_count(7),
            "new_users_month": await self.get_new_users_count(30),
        }

        # Статистика по ролям
        users_by_role: dict[str, int] = {}
        for role in UserRole:
            count = await self.count(role=role, include_deleted=False)
            users_by_role[role.value] = count
        stats["users_by_role"] = users_by_role

        # Статистика по статусам
        users_by_status: dict[str, int] = {}
        for status in UserStatus:
            count = await self.count(status=status, include_deleted=False)
            users_by_status[status.value] = count
        stats["users_by_status"] = users_by_status

        return stats

    async def get_recently_active_users(self, hours: int = 24, *, limit: int = 100) -> Sequence[User]:
        """
        Получить недавно активных пользователей.

        :param hours: Количество часов
        :param limit: Лимит пользователей
        :return: Список недавно активных пользователей
        """
        since_time = datetime.utcnow() - timedelta(hours=hours)

        return await self.list(
            last_seen_at__gte=since_time, limit=limit, order_by="last_seen_at", include_deleted=False
        )

    async def bulk_update_status(self, user_ids: list[uuid.UUID], status: UserStatus) -> int:
        """
        Массовое обновление статуса пользователей.

        :param user_ids: Список ID пользователей
        :param status: Новый статус
        :return: Количество обновленных пользователей
        """
        if not user_ids:
            return 0

        return await self.bulk_update(
            filters={"id__in": [str(uid) for uid in user_ids]},
            update_data={"status": status, "updated_at": datetime.utcnow()},
        )

    async def bulk_activate_users(self, user_ids: list[uuid.UUID]) -> int:
        """
        Массовая активация пользователей.

        :param user_ids: Список ID пользователей
        :return: Количество активированных пользователей
        """
        if not user_ids:
            return 0

        return await self.bulk_update(
            filters={"id__in": [str(uid) for uid in user_ids]},
            update_data={"is_active": True, "status": UserStatus.ACTIVE, "updated_at": datetime.utcnow()},
        )

    async def bulk_deactivate_users(self, user_ids: list[uuid.UUID]) -> int:
        """
        Массовая деактивация пользователей.

        :param user_ids: Список ID пользователей
        :return: Количество деактивированных пользователей
        """
        if not user_ids:
            return 0

        return await self.bulk_update(
            filters={"id__in": [str(uid) for uid in user_ids]},
            update_data={"is_active": False, "status": UserStatus.SUSPENDED, "updated_at": datetime.utcnow()},
        )

    async def cleanup_inactive_users(self, days: int = 365) -> int:
        """
        Очистка неактивных пользователей.

        :param days: Количество дней неактивности
        :return: Количество удаленных пользователей
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        return await self.bulk_delete(
            filters={
                "and_filters": {"last_seen_at__lt": cutoff_date, "is_verified": False, "status": UserStatus.PENDING}
            },
            soft_delete=True,
        )
