"""
Репозиторий refresh токенов.
"""

import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from apps.auth.models.auth_models import RefreshToken
from core.base.repo.repository import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken, Any, Any]):
    """
    Репозиторий для работы с refresh токенами.

    Наследуется от BaseRepository и добавляет специфичные методы
    для работы с токенами: поиск по хешу, очистка истекших токенов.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(RefreshToken, db)

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        """
        Получить refresh токен по хешу.

        :param token_hash: Хеш токена
        :return: Refresh токен или None
        """
        return await self.get_by(token_hash=token_hash)

    async def get_by_token_hash_with_user(self, token_hash: str) -> RefreshToken | None:
        """
        Получить refresh токен с загруженным пользователем.

        :param token_hash: Хеш токена
        :return: Refresh токен с пользователем или None
        """
        query = (
            select(RefreshToken)
            .options(joinedload(RefreshToken.user))
            .where(and_(RefreshToken.token_hash == token_hash, RefreshToken.deleted_at.is_(None)))
        )

        result = await self._db.execute(query)
        return result.scalar_one_or_none()

    async def get_valid_token(self, token_hash: str) -> RefreshToken | None:
        """
        Получить валидный (не истекший и не отозванный) токен.

        :param token_hash: Хеш токена
        :return: Валидный токен или None
        """
        now = datetime.utcnow()
        return await self.get_by(token_hash=token_hash, is_revoked=False, expires_at__gt=now)

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        *,
        include_revoked: bool = False,
        include_expired: bool = False,
        offset: int | None = None,
        limit: int | None = None,
    ) -> Sequence[RefreshToken]:
        """
        Получить список токенов пользователя.

        :param user_id: ID пользователя
        :param include_revoked: Включать ли отозванные токены
        :param include_expired: Включать ли истекшие токены
        :param offset: Смещение
        :param limit: Лимит
        :return: Список токенов
        """
        filters: dict[str, Any] = {"user_id": user_id}

        if not include_revoked:
            filters["is_revoked"] = False

        if not include_expired:
            filters["expires_at__gt"] = datetime.utcnow()

        return await self.list(**filters, offset=offset, limit=limit, order_by="created_at", include_deleted=False)

    async def list_active_tokens(
        self, user_id: uuid.UUID | None = None, *, offset: int | None = None, limit: int | None = None
    ) -> Sequence[RefreshToken]:
        """
        Получить список активных токенов.

        :param user_id: ID пользователя (опционально)
        :param offset: Смещение
        :param limit: Лимит
        :return: Список активных токенов
        """
        filters: dict[str, Any] = {"is_revoked": False, "expires_at__gt": datetime.utcnow()}

        if user_id:
            filters["user_id"] = user_id

        return await self.list(**filters, offset=offset, limit=limit, order_by="created_at", include_deleted=False)

    async def count_active_tokens(self, user_id: uuid.UUID) -> int:
        """
        Получить количество активных токенов пользователя.

        :param user_id: ID пользователя
        :return: Количество активных токенов
        """
        return await self.count(
            user_id=user_id, is_revoked=False, expires_at__gt=datetime.utcnow(), include_deleted=False
        )

    async def revoke_token(self, token_hash: str) -> bool:
        """
        Отозвать токен.

        :param token_hash: Хеш токена
        :return: True если токен был отозван
        """
        token = await self.get_by_token_hash(token_hash)
        if not token or token.is_revoked:
            return False

        await self.update(token, {"is_revoked": True})
        return True

    async def revoke_all_user_tokens(self, user_id: uuid.UUID) -> int:
        """
        Отозвать все токены пользователя.

        :param user_id: ID пользователя
        :return: Количество отозванных токенов
        """
        return await self.bulk_update(
            filters={"user_id": user_id, "is_revoked": False}, update_data={"is_revoked": True}
        )

    async def cleanup_expired_tokens(self) -> int:
        """
        Очистка истекших токенов.

        :return: Количество удаленных токенов
        """
        now = datetime.utcnow()

        return await self.bulk_delete(
            filters={"expires_at__lt": now},
            soft_delete=False,  # Жесткое удаление для очистки
        )

    async def cleanup_revoked_tokens(self, days_old: int = 30) -> int:
        """
        Очистка старых отозванных токенов.

        :param days_old: Возраст токенов в днях
        :return: Количество удаленных токенов
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        return await self.bulk_delete(
            filters={"is_revoked": True, "updated_at__lt": cutoff_date},
            soft_delete=False,  # Жесткое удаление для очистки
        )

    async def update_last_used(self, token_hash: str) -> bool:
        """
        Обновить время последнего использования токена.

        :param token_hash: Хеш токена
        :return: True если токен был обновлен
        """
        token = await self.get_by_token_hash(token_hash)
        if not token:
            return False

        await self.update(token, {"last_used_at": datetime.utcnow()})
        return True

    async def get_tokens_stats(self) -> dict[str, Any]:
        """
        Получить статистику токенов.

        :return: Словарь со статистикой
        """
        now = datetime.utcnow()

        stats = {
            "total_tokens": await self.count(include_deleted=False),
            "active_tokens": await self.count(is_revoked=False, expires_at__gt=now, include_deleted=False),
            "revoked_tokens": await self.count(is_revoked=True, include_deleted=False),
            "expired_tokens": await self.count(expires_at__lte=now, include_deleted=False),
            "tokens_created_today": await self.count(
                created_at__gte=now.replace(hour=0, minute=0, second=0, microsecond=0), include_deleted=False
            ),
            "tokens_created_week": await self.count(created_at__gte=now - timedelta(days=7), include_deleted=False),
        }

        return stats

    async def get_user_device_tokens(self, user_id: uuid.UUID, device_fingerprint: str) -> Sequence[RefreshToken]:
        """
        Получить токены пользователя для конкретного устройства.

        :param user_id: ID пользователя
        :param device_fingerprint: Отпечаток устройства
        :return: Список токенов для устройства
        """
        return await self.list(user_id=user_id, device_fingerprint=device_fingerprint, include_deleted=False)

    async def revoke_device_tokens(self, user_id: uuid.UUID, device_fingerprint: str) -> int:
        """
        Отозвать все токены пользователя для конкретного устройства.

        :param user_id: ID пользователя
        :param device_fingerprint: Отпечаток устройства
        :return: Количество отозванных токенов
        """
        return await self.bulk_update(
            filters={"user_id": user_id, "device_fingerprint": device_fingerprint, "is_revoked": False},
            update_data={"is_revoked": True},
        )

    async def get_old_tokens_for_cleanup(self, days: int = 90) -> Sequence[RefreshToken]:
        """
        Получить старые токены для очистки.

        :param days: Возраст токенов в днях
        :return: Список старых токенов
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        return await self.list(created_at__lt=cutoff_date, include_deleted=False)
