"""
Репозиторий профилей пользователей.
"""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from apps.users.models.enums import NotificationLevel, UserLanguage, UserTheme
from apps.users.models.user_models import UserProfile
from core.base.repo.repository import BaseRepository


class ProfileRepository(BaseRepository[UserProfile, Any, Any]):
    """
    Репозиторий для работы с профилями пользователей.

    Наследуется от BaseRepository и добавляет специфичные методы
    для работы с профилями: поиск по пользователю, настройки уведомлений.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(UserProfile, db)

    async def get_by_user_id(self, user_id: uuid.UUID) -> UserProfile | None:
        """
        Получить профиль пользователя по ID пользователя.

        :param user_id: ID пользователя
        :return: Профиль пользователя или None
        """
        return await self.get_by(user_id=user_id)

    async def get_with_user(self, user_id: uuid.UUID) -> UserProfile | None:
        """
        Получить профиль с загруженным пользователем.

        :param user_id: ID пользователя
        :return: Профиль с загруженным пользователем или None
        """
        query = (
            select(UserProfile)
            .options(joinedload(UserProfile.user))
            .where(and_(UserProfile.user_id == user_id, UserProfile.deleted_at.is_(None)))
        )

        result = await self._db.execute(query)
        return result.scalar_one_or_none()

    async def profile_exists(self, user_id: uuid.UUID) -> bool:
        """
        Проверить существование профиля для пользователя.

        :param user_id: ID пользователя
        :return: True если профиль существует
        """
        return await self.exists(user_id=user_id)

    async def create_default_profile(self, user_id: uuid.UUID) -> UserProfile:
        """
        Создать профиль по умолчанию для пользователя.

        :param user_id: ID пользователя
        :return: Созданный профиль
        """
        profile_data = {
            "user_id": user_id,
            "timezone": "UTC",
            "language": UserLanguage.EN,
            "theme": UserTheme.LIGHT,
            "notifications_enabled": True,
            "notification_level": NotificationLevel.ALL,
            "email_notifications": True,
            "push_notifications": True,
            "public_profile": True,
            "show_email": False,
            "show_phone": False,
        }

        return await self.create(profile_data)

    async def list_by_language(
        self, language: UserLanguage, *, offset: int | None = None, limit: int | None = None
    ) -> Sequence[UserProfile]:
        """
        Получить список профилей по языку.

        :param language: Язык интерфейса
        :param offset: Смещение
        :param limit: Лимит
        :return: Список профилей
        """
        return await self.list(language=language, offset=offset, limit=limit, include_deleted=False)

    async def list_by_theme(
        self, theme: UserTheme, *, offset: int | None = None, limit: int | None = None
    ) -> Sequence[UserProfile]:
        """
        Получить список профилей по теме.

        :param theme: Тема интерфейса
        :param offset: Смещение
        :param limit: Лимит
        :return: Список профилей
        """
        return await self.list(theme=theme, offset=offset, limit=limit, include_deleted=False)

    async def list_public_profiles(
        self, *, offset: int | None = None, limit: int | None = None
    ) -> Sequence[UserProfile]:
        """
        Получить список публичных профилей.

        :param offset: Смещение
        :param limit: Лимит
        :return: Список публичных профилей
        """
        return await self.list(public_profile=True, offset=offset, limit=limit, include_deleted=False)

    async def list_with_notifications_enabled(
        self, *, offset: int | None = None, limit: int | None = None
    ) -> Sequence[UserProfile]:
        """
        Получить список профилей с включенными уведомлениями.

        :param offset: Смещение
        :param limit: Лимит
        :return: Список профилей с уведомлениями
        """
        return await self.list(notifications_enabled=True, offset=offset, limit=limit, include_deleted=False)

    async def list_with_email_notifications(
        self, *, offset: int | None = None, limit: int | None = None
    ) -> Sequence[UserProfile]:
        """
        Получить список профилей с включенными email уведомлениями.

        :param offset: Смещение
        :param limit: Лимит
        :return: Список профилей с email уведомлениями
        """
        return await self.list(
            email_notifications=True, notifications_enabled=True, offset=offset, limit=limit, include_deleted=False
        )

    async def search_profiles(
        self, query: str, *, offset: int | None = None, limit: int | None = None, public_only: bool = True
    ) -> Sequence[UserProfile]:
        """
        Поиск профилей по запросу.

        :param query: Поисковый запрос
        :param offset: Смещение
        :param limit: Лимит
        :param public_only: Искать только среди публичных профилей
        :return: Список найденных профилей
        """
        # Поиск по bio, location, website
        search_filters = {
            "or_filters": [
                {"bio__icontains": query},
                {"location__icontains": query},
                {"website__icontains": query},
            ]
        }

        if public_only:
            search_filters["and_filters"] = {"public_profile": True}

        return await self.list_with_complex_filters(search_filters, offset=offset, limit=limit, include_deleted=False)

    async def search_public_profiles(
        self, query: str | None = None, location: str | None = None, limit: int = 50, offset: int = 0
    ) -> Sequence[UserProfile]:
        """
        Поиск публичных профилей по запросу и локации.

        :param query: Поисковый запрос
        :param location: Локация для фильтрации
        :param limit: Лимит результатов
        :param offset: Смещение
        :return: Список найденных публичных профилей
        """
        # Простая реализация - используем существующий метод search_profiles
        return await self.search_profiles(query=query or "", offset=offset, limit=limit, public_only=True)

    async def get_profiles_stats(self) -> dict[str, Any]:
        """
        Получить статистику профилей.

        :return: Словарь со статистикой
        """
        stats: dict[str, Any] = {
            "total_profiles": await self.count(include_deleted=False),
            "public_profiles": await self.count(public_profile=True, include_deleted=False),
            "private_profiles": await self.count(public_profile=False, include_deleted=False),
            "notifications_enabled": await self.count(notifications_enabled=True, include_deleted=False),
            "email_notifications_enabled": await self.count(email_notifications=True, include_deleted=False),
            "push_notifications_enabled": await self.count(push_notifications=True, include_deleted=False),
        }

        # Статистика по языкам
        languages_stats: dict[str, int] = {}
        for language in UserLanguage:
            count = await self.count(language=language, include_deleted=False)
            languages_stats[language.value] = count
        stats["languages"] = languages_stats

        # Статистика по темам
        themes_stats: dict[str, int] = {}
        for theme in UserTheme:
            count = await self.count(theme=theme, include_deleted=False)
            themes_stats[theme.value] = count
        stats["themes"] = themes_stats

        # Статистика по уровням уведомлений
        notification_levels_stats: dict[str, int] = {}
        for level in NotificationLevel:
            count = await self.count(notification_level=level, include_deleted=False)
            notification_levels_stats[level.value] = count
        stats["notification_levels"] = notification_levels_stats

        return stats

    async def bulk_update_language(self, user_ids: list[uuid.UUID], language: UserLanguage) -> int:
        """
        Массовое обновление языка в профилях.

        :param user_ids: Список ID пользователей
        :param language: Новый язык
        :return: Количество обновленных профилей
        """
        if not user_ids:
            return 0

        return await self.bulk_update(
            filters={"user_id__in": [str(uid) for uid in user_ids]}, update_data={"language": language}
        )

    async def bulk_update_theme(self, user_ids: list[uuid.UUID], theme: UserTheme) -> int:
        """
        Массовое обновление темы в профилях.

        :param user_ids: Список ID пользователей
        :param theme: Новая тема
        :return: Количество обновленных профилей
        """
        if not user_ids:
            return 0

        return await self.bulk_update(
            filters={"user_id__in": [str(uid) for uid in user_ids]}, update_data={"theme": theme}
        )

    async def bulk_disable_notifications(self, user_ids: list[uuid.UUID]) -> int:
        """
        Массовое отключение уведомлений в профилях.

        :param user_ids: Список ID пользователей
        :return: Количество обновленных профилей
        """
        if not user_ids:
            return 0

        return await self.bulk_update(
            filters={"user_id__in": [str(uid) for uid in user_ids]},
            update_data={"notifications_enabled": False, "email_notifications": False, "push_notifications": False},
        )

    async def cleanup_incomplete_profiles(self) -> int:
        """
        Очистка неполных профилей без связанного пользователя.

        :return: Количество удаленных профилей
        """
        # Находим профили, у которых нет связанного пользователя
        query = (
            select(UserProfile).outerjoin(UserProfile.user).where(UserProfile.user == None)  # noqa: E711
        )

        result = await self._db.execute(query)
        orphaned_profiles = result.scalars().all()

        if not orphaned_profiles:
            return 0

        orphaned_ids = [str(profile.id) for profile in orphaned_profiles]

        return await self.bulk_delete(
            filters={"id__in": orphaned_ids},
            soft_delete=False,  # Жесткое удаление для очистки
        )
