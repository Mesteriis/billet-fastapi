"""
Сервис для бизнес-логики профилей пользователей.
"""

import logging
import uuid
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.users.exceptions import ProfileAlreadyExistsError
from apps.users.models.enums import NotificationLevel, UserLanguage, UserTheme
from apps.users.models.user_models import UserProfile
from apps.users.repo.profile_repo import ProfileRepository
from apps.users.schemas.profile_schemas import ProfileCreate, ProfileUpdate

logger = logging.getLogger("users.profile_service")


class ProfileService:
    """
    Сервис для бизнес-логики профилей пользователей.

    Обеспечивает операции с профилями:
    - Создание и обновление профилей
    - Управление настройками интерфейса
    - Управление настройками уведомлений
    - Управление приватностью
    - Поиск и фильтрация профилей
    """

    def __init__(self, profile_repo: ProfileRepository):
        self._profile_repo = profile_repo

    async def create_profile(self, user_id: uuid.UUID, profile_data: ProfileCreate) -> UserProfile:
        """
        Создать профиль пользователя.

        :param user_id: ID пользователя
        :param profile_data: Данные профиля
        :return: Созданный профиль
        """
        logger.info(f"Creating profile for user: {user_id}")

        # Проверяем существование профиля
        existing_profile = await self._profile_repo.get_by_user_id(user_id)
        if existing_profile:
            raise ProfileAlreadyExistsError(user_id=user_id)

        # Создаем данные профиля
        create_data = {
            "user_id": user_id,
            "bio": profile_data.bio,
            "phone": profile_data.phone,
            "birth_date": profile_data.birth_date,
            "location": profile_data.location,
            "website": profile_data.website,
            "timezone": profile_data.timezone or "UTC",
            "language": profile_data.language or UserLanguage.EN,
            "theme": profile_data.theme or UserTheme.LIGHT,
            "notifications_enabled": profile_data.notifications_enabled,
            "notification_level": profile_data.notification_level or NotificationLevel.ALL,
            "email_notifications": profile_data.email_notifications,
            "push_notifications": profile_data.push_notifications,
            "public_profile": profile_data.public_profile,
            "show_email": profile_data.show_email,
            "show_phone": profile_data.show_phone,
        }

        try:
            profile = await self._profile_repo.create(create_data)
            logger.info(f"Profile created successfully for user: {user_id}")
            return profile
        except Exception as e:
            logger.error(f"Failed to create profile for user {user_id}: {e}")
            raise

    async def get_profile_by_user_id(self, user_id: uuid.UUID) -> UserProfile | None:
        """
        Получить профиль пользователя по ID пользователя.

        :param user_id: ID пользователя
        :return: Профиль или None
        """
        return await self._profile_repo.get_by_user_id(user_id)

    async def get_profile_by_id(self, profile_id: uuid.UUID) -> UserProfile | None:
        """
        Получить профиль по ID.

        :param profile_id: ID профиля
        :return: Профиль или None
        """
        return await self._profile_repo.get_by_id(profile_id)

    async def update_profile(self, user_id: uuid.UUID, profile_data: ProfileUpdate) -> UserProfile | None:
        """
        Обновить профиль пользователя.

        :param user_id: ID пользователя
        :param profile_data: Новые данные профиля
        :return: Обновленный профиль
        """
        logger.info(f"Updating profile for user: {user_id}")

        profile = await self._profile_repo.get_by_user_id(user_id)
        if not profile:
            return None

        # Подготавливаем данные для обновления
        update_data = {}

        # Персональная информация
        for field in ["bio", "phone", "birth_date", "location", "website"]:
            value = getattr(profile_data, field, None)
            if value is not None:
                update_data[field] = value

        # Настройки локализации
        for field in ["timezone", "language", "theme"]:
            value = getattr(profile_data, field, None)
            if value is not None:
                update_data[field] = value

        # Настройки уведомлений
        for field in ["notifications_enabled", "notification_level", "email_notifications", "push_notifications"]:
            value = getattr(profile_data, field, None)
            if value is not None:
                update_data[field] = value

        # Настройки приватности
        for field in ["public_profile", "show_email", "show_phone"]:
            value = getattr(profile_data, field, None)
            if value is not None:
                update_data[field] = value

        try:
            updated_profile = await self._profile_repo.update(profile, update_data)
            logger.info(f"Profile updated successfully for user: {user_id}")
            return updated_profile
        except Exception as e:
            logger.error(f"Failed to update profile for user {user_id}: {e}")
            raise

    async def update_interface_settings(
        self,
        user_id: uuid.UUID,
        theme: UserTheme | None = None,
        language: UserLanguage | None = None,
        timezone: str | None = None,
    ) -> bool:
        """
        Обновить настройки интерфейса.

        :param user_id: ID пользователя
        :param theme: Тема интерфейса
        :param language: Язык интерфейса
        :param timezone: Временная зона
        :return: True если настройки обновлены
        """
        profile = await self._profile_repo.get_by_user_id(user_id)
        if not profile:
            return False

        update_data = {}
        if theme is not None:
            update_data["theme"] = theme
        if language is not None:
            update_data["language"] = language
        if timezone is not None:
            update_data["timezone"] = timezone

        if not update_data:
            return True

        try:
            await self._profile_repo.update(profile, update_data)
            logger.info(f"Interface settings updated for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update interface settings for user {user_id}: {e}")
            return False

    async def update_notification_settings(
        self,
        user_id: uuid.UUID,
        notifications_enabled: bool | None = None,
        notification_level: NotificationLevel | None = None,
        email_notifications: bool | None = None,
        push_notifications: bool | None = None,
    ) -> bool:
        """
        Обновить настройки уведомлений.

        :param user_id: ID пользователя
        :param notifications_enabled: Включены ли уведомления
        :param notification_level: Уровень уведомлений
        :param email_notifications: Email уведомления
        :param push_notifications: Push уведомления
        :return: True если настройки обновлены
        """
        profile = await self._profile_repo.get_by_user_id(user_id)
        if not profile:
            return False

        update_data = {}
        if notifications_enabled is not None:
            update_data["notifications_enabled"] = notifications_enabled
        if notification_level is not None:
            update_data["notification_level"] = notification_level
        if email_notifications is not None:
            update_data["email_notifications"] = email_notifications
        if push_notifications is not None:
            update_data["push_notifications"] = push_notifications

        if not update_data:
            return True

        try:
            await self._profile_repo.update(profile, update_data)
            logger.info(f"Notification settings updated for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update notification settings for user {user_id}: {e}")
            return False

    async def update_privacy_settings(
        self,
        user_id: uuid.UUID,
        public_profile: bool | None = None,
        show_email: bool | None = None,
        show_phone: bool | None = None,
    ) -> bool:
        """
        Обновить настройки приватности.

        :param user_id: ID пользователя
        :param public_profile: Публичный ли профиль
        :param show_email: Показывать ли email
        :param show_phone: Показывать ли телефон
        :return: True если настройки обновлены
        """
        profile = await self._profile_repo.get_by_user_id(user_id)
        if not profile:
            return False

        update_data = {}
        if public_profile is not None:
            update_data["public_profile"] = public_profile
        if show_email is not None:
            update_data["show_email"] = show_email
        if show_phone is not None:
            update_data["show_phone"] = show_phone

        if not update_data:
            return True

        try:
            await self._profile_repo.update(profile, update_data)
            logger.info(f"Privacy settings updated for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update privacy settings for user {user_id}: {e}")
            return False

    async def search_public_profiles(
        self, query: str | None = None, location: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[UserProfile]:
        """
        Поиск публичных профилей.

        :param query: Поисковый запрос
        :param location: Фильтр по локации
        :param limit: Лимит результатов
        :param offset: Смещение
        :return: Список профилей
        """
        try:
            profiles = await self._profile_repo.search_public_profiles(
                query=query, location=location, limit=limit, offset=offset
            )
            return list(profiles)
        except Exception as e:
            logger.error(f"Error searching public profiles: {e}")
            return []

    async def get_profile_stats(self) -> dict[str, Any]:
        """
        Получить статистику профилей.

        :return: Статистика профилей
        """
        try:
            return await self._profile_repo.get_profile_stats()
        except Exception as e:
            logger.error(f"Error getting profile stats: {e}")
            return {}

    async def create_default_profile(self, user_id: uuid.UUID) -> UserProfile:
        """
        Создать профиль по умолчанию для пользователя.

        :param user_id: ID пользователя
        :return: Созданный профиль
        """
        logger.info(f"Creating default profile for user: {user_id}")

        default_data = {
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

        try:
            profile = await self._profile_repo.create(default_data)
            logger.info(f"Default profile created for user: {user_id}")
            return profile
        except Exception as e:
            logger.error(f"Failed to create default profile for user {user_id}: {e}")
            raise

    async def delete_profile(self, user_id: uuid.UUID, soft_delete: bool = True) -> bool:
        """
        Удалить профиль пользователя.

        :param user_id: ID пользователя
        :param soft_delete: Мягкое удаление
        :return: True если профиль удален
        """
        logger.info(f"Deleting profile for user: {user_id}")

        profile = await self._profile_repo.get_by_user_id(user_id)
        if not profile:
            return False

        try:
            await self._profile_repo.delete(profile, soft_delete=soft_delete)
            logger.info(f"Profile deleted for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete profile for user {user_id}: {e}")
            return False

    async def get_user_preferences(self, user_id: uuid.UUID) -> dict[str, Any]:
        """
        Получить предпочтения пользователя.

        :param user_id: ID пользователя
        :return: Словарь с предпочтениями
        """
        profile = await self._profile_repo.get_by_user_id(user_id)
        if not profile:
            return {}

        return {
            "interface": {
                "theme": profile.theme.value,
                "language": profile.language.value,
                "timezone": profile.timezone,
            },
            "notifications": {
                "enabled": profile.notifications_enabled,
                "level": profile.notification_level.value,
                "email": profile.email_notifications,
                "push": profile.push_notifications,
            },
            "privacy": {
                "public_profile": profile.public_profile,
                "show_email": profile.show_email,
                "show_phone": profile.show_phone,
            },
        }
