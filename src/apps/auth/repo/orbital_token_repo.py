"""
Репозиторий для работы с одноразовыми токенами (orbital tokens).
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auth.models.auth_models import OrbitalToken
from apps.auth.schemas.token_schemas import OrbitalTokenType
from core.base.repo.repository import BaseRepository


class OrbitalTokenRepository(BaseRepository[OrbitalToken, Any, Any]):
    """
    Репозиторий для работы с одноразовыми токенами.

    Обеспечивает операции с токенами:
    - Создание и валидация токенов
    - Поиск активных токенов
    - Управление состоянием (использование, отзыв)
    - Очистка истекших токенов
    - Статистика по токенам
    """

    def __init__(self, db: AsyncSession):
        super().__init__(OrbitalToken, db)

    async def get_valid_token(
        self,
        token_hash: str,
        token_type: OrbitalTokenType | None = None,
        purpose: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> OrbitalToken | None:
        """
        Получить валидный токен по хешу с дополнительными фильтрами.

        :param token_hash: Хеш токена
        :param token_type: Тип токена (опционально)
        :param purpose: Назначение токена (опционально)
        :param user_id: ID пользователя (опционально)
        :return: Объект токена или None
        """
        filters = [
            self.model.token_hash == token_hash,
            self.model.is_used == False,  # noqa: E712
            self.model.expires_at > datetime.utcnow(),
            self.model.is_deleted == False,  # noqa: E712
        ]

        if token_type:
            filters.append(self.model.token_type == token_type.value)

        if purpose:
            filters.append(self.model.purpose == purpose)

        if user_id:
            filters.append(self.model.user_id == user_id)

        stmt = select(self.model).where(and_(*filters))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def consume_token(self, token_id: uuid.UUID) -> bool:
        """
        Пометить токен как использованный.

        :param token_id: ID токена
        :return: True если токен был помечен как использованный
        """
        stmt = (
            update(self.model)
            .where(
                and_(
                    self.model.id == token_id,
                    self.model.is_used == False,  # noqa: E712
                    self.model.is_deleted == False,  # noqa: E712
                )
            )
            .values(is_used=True, used_at=datetime.utcnow())
        )

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def revoke_user_tokens(
        self, user_id: uuid.UUID, token_type: OrbitalTokenType | None = None, purpose: str | None = None
    ) -> int:
        """
        Отозвать токены пользователя (пометить как использованные).

        :param user_id: ID пользователя
        :param token_type: Тип токенов для отзыва (опционально)
        :param purpose: Назначение токенов для отзыва (опционально)
        :return: Количество отозванных токенов
        """
        filters = [
            self.model.user_id == user_id,
            self.model.is_used == False,  # noqa: E712
            self.model.is_deleted == False,  # noqa: E712
        ]

        if token_type:
            filters.append(self.model.token_type == token_type.value)

        if purpose:
            filters.append(self.model.purpose == purpose)

        stmt = update(self.model).where(and_(*filters)).values(is_used=True, used_at=datetime.utcnow())

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def cleanup_expired_tokens(self) -> int:
        """
        Удалить истекшие токены из БД.

        :return: Количество удаленных токенов
        """
        stmt = delete(self.model).where(self.model.expires_at <= datetime.utcnow())

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def list_active_tokens(
        self, user_id: uuid.UUID, token_type: OrbitalTokenType | None = None, limit: int = 100
    ) -> list[OrbitalToken]:
        """
        Получить список активных токенов пользователя.

        :param user_id: ID пользователя
        :param token_type: Тип токенов (опционально)
        :param limit: Максимальное количество токенов
        :return: Список активных токенов
        """
        filters = [
            self.model.user_id == user_id,
            self.model.is_used == False,  # noqa: E712
            self.model.expires_at > datetime.utcnow(),
            self.model.is_deleted == False,  # noqa: E712
        ]

        if token_type:
            filters.append(self.model.token_type == token_type.value)

        stmt = select(self.model).where(and_(*filters)).order_by(self.model.created_at.desc()).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_active_tokens(self, user_id: uuid.UUID, token_type: OrbitalTokenType | None = None) -> int:
        """
        Подсчитать количество активных токенов пользователя.

        :param user_id: ID пользователя
        :param token_type: Тип токенов (опционально)
        :return: Количество активных токенов
        """
        filters = [
            self.model.user_id == user_id,
            self.model.is_used == False,  # noqa: E712
            self.model.expires_at > datetime.utcnow(),
            self.model.is_deleted == False,  # noqa: E712
        ]

        if token_type:
            filters.append(self.model.token_type == token_type.value)

        stmt = select(func.count(self.model.id)).where(and_(*filters))

        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_user_tokens_stats(self, user_id: uuid.UUID) -> dict[str, Any]:
        """
        Получить статистику токенов пользователя.

        :param user_id: ID пользователя
        :return: Статистика токенов
        """
        # Общая статистика
        total_stmt = select(func.count(self.model.id)).where(
            and_(
                self.model.user_id == user_id,
                self.model.is_deleted == False,  # noqa: E712
            )
        )

        # Активные токены
        active_stmt = select(func.count(self.model.id)).where(
            and_(
                self.model.user_id == user_id,
                self.model.is_used == False,  # noqa: E712
                self.model.expires_at > datetime.utcnow(),
                self.model.is_deleted == False,  # noqa: E712
            )
        )

        # Использованные токены
        used_stmt = select(func.count(self.model.id)).where(
            and_(
                self.model.user_id == user_id,
                self.model.is_used == True,  # noqa: E712
                self.model.is_deleted == False,  # noqa: E712
            )
        )

        # Истекшие токены
        expired_stmt = select(func.count(self.model.id)).where(
            and_(
                self.model.user_id == user_id,
                self.model.is_used == False,  # noqa: E712
                self.model.expires_at <= datetime.utcnow(),
                self.model.is_deleted == False,  # noqa: E712
            )
        )

        # Статистика по типам
        type_stats_stmt = (
            select(
                self.model.token_type,
                func.count(self.model.id).label("count"),
                func.sum(func.cast(self.model.is_used, int)).label("used_count"),
            )
            .where(
                and_(
                    self.model.user_id == user_id,
                    self.model.is_deleted == False,  # noqa: E712
                )
            )
            .group_by(self.model.token_type)
        )

        # Выполняем запросы
        total_result = await self.db.execute(total_stmt)
        active_result = await self.db.execute(active_stmt)
        used_result = await self.db.execute(used_stmt)
        expired_result = await self.db.execute(expired_stmt)
        type_stats_result = await self.db.execute(type_stats_stmt)

        total_count = total_result.scalar() or 0
        active_count = active_result.scalar() or 0
        used_count = used_result.scalar() or 0
        expired_count = expired_result.scalar() or 0

        type_stats = {}
        for row in type_stats_result:
            type_stats[row.token_type] = {
                "total": row.count,
                "used": row.used_count,
                "active": row.count - row.used_count,
            }

        return {
            "total_tokens": total_count,
            "active_tokens": active_count,
            "used_tokens": used_count,
            "expired_tokens": expired_count,
            "by_type": type_stats,
        }

    async def get_tokens_by_purpose(
        self, purpose: str, user_id: uuid.UUID | None = None, active_only: bool = True, limit: int = 100
    ) -> list[OrbitalToken]:
        """
        Получить токены по назначению.

        :param purpose: Назначение токена
        :param user_id: ID пользователя (опционально)
        :param active_only: Только активные токены
        :param limit: Максимальное количество токенов
        :return: Список токенов
        """
        filters = [
            self.model.purpose == purpose,
            self.model.is_deleted == False,  # noqa: E712
        ]

        if user_id:
            filters.append(self.model.user_id == user_id)

        if active_only:
            filters.extend(
                [
                    self.model.is_used == False,  # noqa: E712
                    self.model.expires_at > datetime.utcnow(),
                ]
            )

        stmt = select(self.model).where(and_(*filters)).order_by(self.model.created_at.desc()).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def cleanup_old_used_tokens(self, days_old: int = 30) -> int:
        """
        Удалить старые использованные токены.

        :param days_old: Возраст токенов в днях для удаления
        :return: Количество удаленных токенов
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        stmt = delete(self.model).where(
            and_(
                self.model.is_used == True,  # noqa: E712
                self.model.used_at <= cutoff_date,
            )
        )

        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def find_duplicate_tokens(
        self, user_id: uuid.UUID, token_type: OrbitalTokenType, purpose: str
    ) -> list[OrbitalToken]:
        """
        Найти дублирующиеся активные токены пользователя.

        :param user_id: ID пользователя
        :param token_type: Тип токена
        :param purpose: Назначение токена
        :return: Список дублирующихся токенов
        """
        filters = [
            self.model.user_id == user_id,
            self.model.token_type == token_type.value,
            self.model.purpose == purpose,
            self.model.is_used == False,  # noqa: E712
            self.model.expires_at > datetime.utcnow(),
            self.model.is_deleted == False,  # noqa: E712
        ]

        stmt = (
            select(self.model).where(and_(*filters)).order_by(self.model.created_at.asc())  # Сначала старые
        )

        result = await self.db.execute(stmt)
        tokens = list(result.scalars().all())

        # Возвращаем все кроме последнего (самого нового)
        return tokens[:-1] if len(tokens) > 1 else []
