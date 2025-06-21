"""
Репозиторий пользовательских сессий.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from apps.auth.models.auth_models import UserSession
from core.base.repo.repository import BaseRepository


class UserSessionRepository(BaseRepository[UserSession, Any, Any]):
    """
    Репозиторий для работы с пользовательскими сессиями.

    Наследуется от BaseRepository и добавляет специфичные методы
    для работы с сессиями: поиск по session_id, управление активностью.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(UserSession, db)

    async def get_by_session_id(self, session_id: str) -> UserSession | None:
        """
        Получить сессию по session_id.

        :param session_id: ID сессии
        :return: Сессия или None
        """
        return await self.get_by(session_id=session_id)

    async def get_by_session_id_with_user(self, session_id: str) -> UserSession | None:
        """
        Получить сессию с загруженным пользователем.

        :param session_id: ID сессии
        :return: Сессия с пользователем или None
        """
        query = (
            select(UserSession)
            .options(joinedload(UserSession.user))
            .where(and_(UserSession.session_id == session_id, UserSession.deleted_at.is_(None)))
        )

        result = await self._db.execute(query)
        return result.scalar_one_or_none()

    async def get_active_session(self, session_id: str) -> UserSession | None:
        """
        Получить активную (не истекшую) сессию.

        :param session_id: ID сессии
        :return: Активная сессия или None
        """
        now = datetime.utcnow()
        return await self.get_by(session_id=session_id, is_active=True, expires_at__gt=now)

    async def list_by_user(
        self, user_id: uuid.UUID, *, active_only: bool = True, offset: int | None = None, limit: int | None = None
    ) -> Sequence[UserSession]:
        """
        Получить список сессий пользователя.

        :param user_id: ID пользователя
        :param active_only: Только активные сессии
        :param offset: Смещение
        :param limit: Лимит
        :return: Список сессий
        """
        filters: dict[str, Any] = {"user_id": user_id}

        if active_only:
            filters.update({"is_active": True, "expires_at__gt": datetime.utcnow()})

        return await self.list(
            **filters, offset=offset, limit=limit, order_by="last_activity_at", include_deleted=False
        )

    async def list_active_sessions(
        self, *, offset: int | None = None, limit: int | None = None
    ) -> Sequence[UserSession]:
        """
        Получить список всех активных сессий.

        :param offset: Смещение
        :param limit: Лимит
        :return: Список активных сессий
        """
        now = datetime.utcnow()

        return await self.list(
            is_active=True,
            expires_at__gt=now,
            offset=offset,
            limit=limit,
            order_by="last_activity_at",
            include_deleted=False,
        )

    async def count_active_sessions(self, user_id: uuid.UUID | None = None) -> int:
        """
        Получить количество активных сессий.

        :param user_id: ID пользователя (опционально)
        :return: Количество активных сессий
        """
        filters: dict[str, Any] = {"is_active": True, "expires_at__gt": datetime.utcnow()}

        if user_id:
            filters["user_id"] = user_id

        return await self.count(**filters, include_deleted=False)

    async def invalidate_session(self, session_id: str) -> bool:
        """
        Деактивировать сессию.

        :param session_id: ID сессии
        :return: True если сессия была деактивирована
        """
        session = await self.get_by_session_id(session_id)
        if not session or not session.is_active:
            return False

        await self.update(session, {"is_active": False})
        return True

    async def invalidate_all_user_sessions(self, user_id: uuid.UUID, exclude_session_id: str | None = None) -> int:
        """
        Деактивировать все сессии пользователя.

        :param user_id: ID пользователя
        :param exclude_session_id: ID сессии для исключения
        :return: Количество деактивированных сессий
        """
        filters: dict[str, Any] = {"user_id": user_id, "is_active": True}

        if exclude_session_id:
            filters["session_id__ne"] = exclude_session_id

        return await self.bulk_update(filters=filters, update_data={"is_active": False})

    async def update_activity(self, session_id: str) -> bool:
        """
        Обновить время последней активности сессии.

        :param session_id: ID сессии
        :return: True если активность была обновлена
        """
        session = await self.get_by_session_id(session_id)
        if not session:
            return False

        await self.update(session, {"last_activity_at": datetime.utcnow()})
        return True

    async def extend_session(self, session_id: str, minutes: int = 30) -> bool:
        """
        Продлить время действия сессии.

        :param session_id: ID сессии
        :param minutes: Количество минут для продления
        :return: True если сессия была продлена
        """
        session = await self.get_by_session_id(session_id)
        if not session:
            return False

        new_expiry = datetime.utcnow() + timedelta(minutes=minutes)
        await self.update(session, {"expires_at": new_expiry, "last_activity_at": datetime.utcnow()})
        return True

    async def set_session_data(self, session_id: str, key: str, value: Any) -> bool:
        """
        Установить данные в сессии.

        :param session_id: ID сессии
        :param key: Ключ данных
        :param value: Значение
        :return: True если данные были установлены
        """
        session = await self.get_by_session_id(session_id)
        if not session:
            return False

        data = session.data.copy() if session.data else {}
        data[key] = value

        await self.update(session, {"data": data})
        return True

    async def get_session_data(self, session_id: str, key: str, default: Any = None) -> Any:
        """
        Получить данные из сессии.

        :param session_id: ID сессии
        :param key: Ключ данных
        :param default: Значение по умолчанию
        :return: Значение или default
        """
        session = await self.get_by_session_id(session_id)
        if not session or not session.data:
            return default

        return session.data.get(key, default)

    async def clear_session_data(self, session_id: str) -> bool:
        """
        Очистить данные сессии.

        :param session_id: ID сессии
        :return: True если данные были очищены
        """
        session = await self.get_by_session_id(session_id)
        if not session:
            return False

        await self.update(session, {"data": {}})
        return True

    async def cleanup_expired_sessions(self) -> int:
        """
        Очистка истекших сессий.

        :return: Количество удаленных сессий
        """
        now = datetime.utcnow()

        return await self.bulk_delete(
            filters={"expires_at__lt": now},
            soft_delete=False,  # Жесткое удаление для очистки
        )

    async def cleanup_inactive_sessions(self, hours: int = 24) -> int:
        """
        Очистка неактивных сессий.

        :param hours: Количество часов неактивности
        :return: Количество удаленных сессий
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        return await self.bulk_delete(
            filters={"last_activity_at__lt": cutoff_time, "is_active": False},
            soft_delete=False,  # Жесткое удаление для очистки
        )

    async def get_sessions_stats(self) -> dict[str, Any]:
        """
        Получить статистику сессий.

        :return: Словарь со статистикой
        """
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        stats = {
            "total_sessions": await self.count(include_deleted=False),
            "active_sessions": await self.count(is_active=True, expires_at__gt=now, include_deleted=False),
            "inactive_sessions": await self.count(is_active=False, include_deleted=False),
            "expired_sessions": await self.count(expires_at__lte=now, include_deleted=False),
            "sessions_created_today": await self.count(created_at__gte=today_start, include_deleted=False),
            "sessions_created_week": await self.count(created_at__gte=now - timedelta(days=7), include_deleted=False),
        }

        return stats

    async def get_user_sessions_by_ip(self, user_id: uuid.UUID, ip_address: str) -> Sequence[UserSession]:
        """
        Получить сессии пользователя с определенного IP.

        :param user_id: ID пользователя
        :param ip_address: IP адрес
        :return: Список сессий
        """
        return await self.list(user_id=user_id, ip_address=ip_address, include_deleted=False)

    async def get_suspicious_sessions(self, hours: int = 1) -> Sequence[UserSession]:
        """
        Получить подозрительные сессии (множественные входы).

        :param hours: Период в часах для анализа
        :return: Список подозрительных сессий
        """
        since_time = datetime.utcnow() - timedelta(hours=hours)

        # Это упрощенная версия - в реальном проекте нужен более сложный запрос
        return await self.list(created_at__gte=since_time, is_active=True, limit=100, include_deleted=False)

    async def revoke_sessions_by_ip(self, ip_address: str) -> int:
        """
        Отозвать все сессии с определенного IP.

        :param ip_address: IP адрес
        :return: Количество отозванных сессий
        """
        return await self.bulk_update(
            filters={"ip_address": ip_address, "is_active": True}, update_data={"is_active": False}
        )
